import subprocess
import re
import os

P1 = "Why can hummingbirds hover? Answer in 2-3 sentences."
P2 = "Explicati principiul de functionare al motoarelor cu reactie in detaliu."
P3 = "Write a Python script to scrape a website and extract all image URLs, handling pagination and saving the images locally."

PROMPTS = [P1, P2, P3]

def run_speq(prompt, speq_k):
    env = os.environ.copy()
    env["COLI_ENGINE"] = r"D:\project_colibri_engine\c\glm_test_speq2.exe"
    env["SPEQ_K"] = str(speq_k)
    env["MOE_SPEQ"] = "1"
    env["PILOT_REAL"] = "1"
    env["TEMP"] = "0"
    
    cmd = [
        r"D:\project colibri\.venv\Scripts\python.exe",
        r"D:\project_colibri_engine\c\coli",
        "run", prompt,
        "--model", r"D:\glm52_i4",
        "--ram", "10",
        "--ngen", "33"  # Just 32 tokens to trigger the print at least once!
    ]
    
    proc = subprocess.run(cmd, env=env, capture_output=True, text=True)
    out = proc.stdout + "\n" + proc.stderr
    
    # [SPEQ] enq:123 cached:10 hit:5 evicted:2
    enq, cached, hit, evicted = 0, 0, 0, 0
    # we take the last occurrence if there are multiple
    for line in out.splitlines():
        if "[SPEQ]" in line:
            m = re.search(r"enq:(\d+)\s+cached:(\d+)\s+hit:(\d+)\s+evicted:(\d+)", line)
            if m:
                enq = int(m.group(1))
                cached = int(m.group(2))
                hit = int(m.group(3))
                evicted = int(m.group(4))
                
    tok_s = 0.0
    tok_match = re.search(r'([\d\.]+)\s*tok/s', out)
    if tok_match:
        tok_s = float(tok_match.group(1))

    return tok_s, enq, cached, hit, evicted

results = []

for idx, prompt in enumerate(PROMPTS):
    p_name = f"P{idx+1}"
    print(f"\n--- Testing {p_name} ---")
    
    for k in [1, 2]:
        print(f"Running SPEQ_K={k}...", flush=True)
        tok_s, enq, cached, hit, evicted = run_speq(prompt, k)
        print(f"  -> {tok_s} tok/s | enq: {enq}, cached: {cached}, hit: {hit}, evicted: {evicted}", flush=True)
        results.append(f"| {p_name} | K={k} | {tok_s:.3f} | {enq} | {cached} | {hit} | {evicted} |")

print("\n=== FINAL RESULTS T24 ===")
print("| Prompt | K | Speed (tok/s) | Enqueued | Cached | Hit | Evicted |")
print("|---|---|---|---|---|---|---|")
for r in results:
    print(r)
