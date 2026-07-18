import requests
import time
import sys
import os

API_URL = "http://localhost:8000/v1/chat/completions"
LOG_FILE = "d:\\project colibri\\engine_test_ladder_step6.log"
OUT_FILE = "d:\\project colibri\\outputs_step6.txt"

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

if not wait_for_api():
    sys.exit("API timeout")

print("Running baseline test...")
for i, p in enumerate(prompts):
    for run in range(3):
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
                        import json
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
            
            dt = time.time() - start
            tps = toks / dt if dt > 0 else 0
            
            time.sleep(0.5)
            hits_after, total_after = count_mtp_acceptance()
            d_hits = hits_after - hits_before
            d_total = total_after - total_before
            acc = (d_hits / d_total * 100) if d_total > 0 else 0
            
            print(f"P{i+1} R{run+1} | Time: {dt:.1f}s | TTFT: {ttft:.1f}s | TPS: {tps:.2f} | Acc: {d_hits}/{d_total} ({acc:.1f}%) | Out: {ans[:40].replace(chr(10), ' ')}...")
            
            # Write full output to file for comparison
            with open(OUT_FILE, 'a', encoding='utf-8') as f:
                f.write(f"=== P{i+1} R{run+1} ===\n{ans}\n\n")
            
            time.sleep(1)
        except Exception as e:
            print(f"Error on P{i+1} R{run+1}: {e}")
            time.sleep(5)
