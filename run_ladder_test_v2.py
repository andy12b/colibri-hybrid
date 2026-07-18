import requests
import time
import sys
import os
import json

if len(sys.argv) < 3:
    print("Usage: python run_ladder_test_v2.py <log_file> <out_file>")
    sys.exit(1)

LOG_FILE = sys.argv[1]
OUT_FILE = sys.argv[2]
API_URL = "http://localhost:8000/v1/chat/completions"

prompts = [
    "Why can hummingbirds hover? Answer in 2-3 sentences.",
    "Write a C function that reverses a string in place.",
    "What is 17 * 23? Show your reasoning briefly."
]

def wait_for_api():
    print("Waiting for API...")
    for _ in range(300):
        try:
            requests.get("http://localhost:8000/health", timeout=1)
            print("API ready!")
            return True
        except requests.RequestException:
            time.sleep(1)
    return False

def count_mtp_acceptance():
    try:
        with open(LOG_FILE, 'r', encoding='utf-8', errors='ignore') as f:
            log = f.read()
            hits = log.count('HIT')
            misses = log.count('miss')
            total = hits + misses
            return hits, total
    except:
        return 0, 0

def run_prompt(p, tag, write_out=True):
    hits_before, total_before = count_mtp_acceptance()
    
    payload = {
        "model": "glm-5.2-colibri",
        "messages": [{"role": "user", "content": p}],
        "temperature": 0.0,
        "max_tokens": 64,
        "stream": True
    }
    start = time.time()
    ttft = 0
    ans = ""
    toks = 0
    
    try:
        resp = requests.post(API_URL, json=payload, timeout=3600, stream=True)
        resp.raise_for_status()
        
        for line in resp.iter_lines():
            if line:
                line = line.decode('utf-8')
                if line.startswith('data: '):
                    data = line[6:]
                    if data == '[DONE]':
                        break
                    try:
                        chunk = json.loads(data)
                        delta = chunk['choices'][0]['delta'].get('content', '')
                        if delta:
                            if ttft == 0:
                                ttft = time.time() - start
                            ans += delta
                            toks += 1
                    except:
                        pass
        
        wall_s = time.time() - start
        toks_per_s = toks / wall_s if wall_s > 0 else 0
        
        time.sleep(0.5)
        hits_after, total_after = count_mtp_acceptance()
        d_hits = hits_after - hits_before
        d_total = total_after - total_before
        acc = (d_hits / d_total * 100) if d_total > 0 else 0
        
        print(f"{tag} | Wall: {wall_s:.1f}s | toks/s: {toks_per_s:.3f} | Acc: {d_hits}/{d_total} ({acc:.1f}%)")
        
        if write_out:
            with open(OUT_FILE, 'a', encoding='utf-8') as f:
                f.write(f"=== {tag} ===\nWall: {wall_s:.1f}s | toks/s: {toks_per_s:.3f} | Acc: {d_hits}/{d_total} ({acc:.1f}%)\n{ans}\n\n")
        
        time.sleep(1)
        return wall_s, toks_per_s, acc
    except Exception as e:
        print(f"Error on {tag}: {e}")
        time.sleep(5)
        return 0, 0, 0

if not wait_for_api():
    sys.exit("API timeout")

print("Running WARMUP test (P1)...")
run_prompt(prompts[0], "WARMUP", write_out=False)

print("Running measured tests...")
for i, p in enumerate(prompts):
    for run in range(3):
        run_prompt(p, f"P{i+1} R{run+1}", write_out=True)
