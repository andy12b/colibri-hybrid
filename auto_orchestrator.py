import os
import sys
import time
import subprocess
import re

def parse_baseline(file_path):
    # Extracts the text for each run
    runs = {}
    if not os.path.exists(file_path): return runs
    content = open(file_path, "r", encoding="utf-8").read()
    chunks = re.split(r"=== (.*?) ===", content)
    for i in range(1, len(chunks), 2):
        tag = chunks[i].strip()
        text = chunks[i+1].strip()
        # remove the newly added Wall: line if it exists
        text = re.sub(r"^Wall:.*?toks/s:.*?Acc:.*?\n", "", text, flags=re.MULTILINE).strip()
        runs[tag] = text
    return runs

def get_median_toks(file_path):
    if not os.path.exists(file_path): return 0.0
    content = open(file_path, "r", encoding="utf-8").read()
    matches = re.findall(r"toks/s:\s*([0-9.]+)", content)
    if not matches: return 0.0
    vals = [float(x) for x in matches]
    vals.sort()
    return vals[len(vals)//2]

def check_match(baseline_runs, current_runs):
    diffs = []
    for tag in baseline_runs:
        if tag.startswith("WARMUP"): continue
        for r in [1, 2, 3]:
            curr_tag = f"{tag} R{r}"
            if curr_tag not in current_runs:
                diffs.append(f"{curr_tag} missing")
            elif baseline_runs[tag] != current_runs[curr_tag]:
                diffs.append(f"{curr_tag} DIFFERS")
    return diffs

def run_config(name, env_vars, baseline_runs):
    print(f"\n--- Running Config: {name} ---")
    
    # 1. Variables
    engine_log = f"engine_{name}.log"
    out_file = f"outputs_{name}.txt"
    if os.path.exists(out_file): os.remove(out_file)
    if os.path.exists(engine_log): os.remove(engine_log)

    # 2. Create cmd file
    base_cmd = open("start_engine_best.cmd", "r").read()
    lines = base_cmd.splitlines()
    # insert env vars before the last line
    for k, v in env_vars.items():
        # replace if exists, else append
        found = False
        for i, line in enumerate(lines):
            if line.startswith(f"set {k}="):
                lines[i] = f"set {k}={v}"
                found = True
                break
        if not found:
            lines.insert(-1, f"set {k}={v}")
            
    # replace engine_final.log with our specific log
    lines[-1] = lines[-1].replace("engine_final.log", engine_log)
    
    with open("start_engine_temp.cmd", "w") as f:
        f.write("\n".join(lines))
        
    # 3. Kill old glm
    subprocess.run(["powershell", "-Command", "Stop-Process -Name glm -Force -ErrorAction SilentlyContinue"])
    time.sleep(2)
    
    # 4. Start engine
    
    engine_proc = subprocess.Popen(["cmd.exe", "/c", "start_engine_temp.cmd"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # wait for start
    print("Waiting for engine to start...")
    ready = False
    for _ in range(120):
        if os.path.exists(engine_log):
            with open(engine_log, "r", encoding="utf-8") as f:
                if "OpenAI-compatible API listening" in f.read():
                    ready = True
                    break
        time.sleep(1)
        
    if not ready:
        print("Engine failed to start in time!")
        subprocess.run(["powershell", "-Command", "Stop-Process -Name glm -Force -ErrorAction SilentlyContinue"])
        return {"name": name, "error": "timeout"}
    
    # 4. Run test
    print("Starting ladder test...")
    subprocess.run(["python", "run_ladder_test_v2.py", engine_log, out_file])
    
    # 5. Extract metrics
    med_toks = get_median_toks(out_file)
    curr_runs = parse_baseline(out_file)
    diffs = check_match(baseline_runs, curr_runs)
    
    # 6. Stop engine
    print(f"Stopping engine...")
    subprocess.run(["powershell", "-Command", "Stop-Process -Name glm -Force -ErrorAction SilentlyContinue"])
    subprocess.run(["powershell", "-Command", "Get-WmiObject Win32_Process -Filter \\\"name='python.exe'\\\" | Where-Object {$_.CommandLine -match 'coli serve'} | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"])
    time.sleep(3)
    
    res = {"name": name, "median_toks": med_toks, "diffs": diffs}
    print(f"Result for {name}: {med_toks:.3f} tok/s, Diffs: {diffs}")
    return res

if __name__ == "__main__":
    baseline = parse_baseline("outputs_baseline.txt")
    results = []
    
    # TASK 12: PIPE_WORKERS
    # (Skipped: 16 causes deadlock, 4 causes severe page thrashing)
    
    # TASK 13: DRAFT DEPTH
    results.append(run_config("t13_draft_2", {"DRAFT": "2"}, baseline))
    results.append(run_config("t13_draft_4", {"DRAFT": "4"}, baseline))
    
    with open("auto_results.json", "w") as f:
        import json
        json.dump(results, f, indent=2)
    print("All done!")
