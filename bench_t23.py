import subprocess
import re
import statistics
import os

P1 = "Why can hummingbirds hover? Answer in 2-3 sentences."
P3 = "What is 17 * 23? Show your reasoning briefly."

CONFIGS = {
    "A (baseline)": {"ENT_TH0": "0.3", "ENT_TH1": "0.6", "ENT_TH2": "0.85"},
    "B (speculativ)": {"ENT_TH0": "0.2", "ENT_TH1": "0.5", "ENT_TH2": "0.75"},
    "C (conservator)": {"ENT_TH0": "0.4", "ENT_TH1": "0.7", "ENT_TH2": "0.9"}
}

def run_prompt(prompt, env_updates):
    env = os.environ.copy()
    env["COLI_ENGINE"] = r"D:\project_colibri_engine\c\glm_test_ent.exe"
    env["ENT_MTP"] = "1"
    env["MOE_SPEQ"] = "1"
    env["DRAFT"] = "3"
    env["PILOT_REAL"] = "1"
    env["TEMP"] = "0"
    env["MTP_DEBUG"] = "1"
    for k, v in env_updates.items():
        env[k] = v

    cmd = [
        r"D:\project colibri\.venv\Scripts\python.exe",
        r"D:\project_colibri_engine\c\coli",
        "run", prompt,
        "--model", r"D:\glm52_i4",
        "--ram", "10",
        "--ngen", "33"
    ]
    
    proc = subprocess.run(cmd, env=env, capture_output=True, text=True)
    out = proc.stdout + "\n" + proc.stderr
    
    tok_s = 0.0
    tok_match = re.search(r'([\d\.]+)\s*tok/s', out)
    if tok_match:
        tok_s = float(tok_match.group(1))
        
    p1, p2, p3 = 0, 0, 0
    mtp_match = re.search(r'\[mtpdbg\].*?acc_pos:\s*p1=(\d+)\s+p2=(\d+)\s+p3=(\d+)', out)
    if mtp_match:
        p1 = int(mtp_match.group(1))
        p2 = int(mtp_match.group(2))
        p3 = int(mtp_match.group(3))
        
    rate_match = re.search(r'\[mtpdbg\].*?rate:\s*([\d\.]+)%', out)
    rate = float(rate_match.group(1)) if rate_match else 0.0

    return tok_s, p1, p2, p3, rate

results = []

for prompt_idx, prompt in enumerate([P1, P3]):
    p_name = f"P{prompt_idx*2+1}"
    print(f"\n--- Testing {p_name} ---", flush=True)
    
    config_data = {cfg: {"tok_s": [], "p1": [], "p2": [], "p3": [], "rate": []} for cfg in CONFIGS}
    
    for iteration in range(1):
        for cfg_name, cfg_env in CONFIGS.items():
            print(f"Run {iteration} for {cfg_name}...", flush=True)
            tok_s, p1, p2, p3, rate = run_prompt(prompt, cfg_env)
            print(f"  -> {tok_s} tok/s, rate: {rate}%, p1: {p1}, p2: {p2}, p3: {p3}", flush=True)
            config_data[cfg_name]["tok_s"].append(tok_s)
            config_data[cfg_name]["p1"].append(p1)
            config_data[cfg_name]["p2"].append(p2)
            config_data[cfg_name]["p3"].append(p3)
            config_data[cfg_name]["rate"].append(rate)
                
    for cfg_name, data in config_data.items():
        med_tok_s = statistics.median(data["tok_s"])
        med_p1 = statistics.median(data["p1"])
        med_p2 = statistics.median(data["p2"])
        med_p3 = statistics.median(data["p3"])
        med_rate = statistics.median(data["rate"])
        results.append(f"| {p_name} | {cfg_name} | {med_tok_s:.3f} tok/s | {med_rate:.1f}% | {med_p1} | {med_p2} | {med_p3} |")
        
print("\n=== FINAL RESULTS ===")
print("| Prompt | Config | Speed | MTP Acc | P1 | P2 | P3 |")
print("|---|---|---|---|---|---|---|")
for r in results:
    print(r)
