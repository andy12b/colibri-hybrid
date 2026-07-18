# Benchmark candidat final: glm_test_final.exe cu ENT_MTP=1 + MOE_SPEQ=1
# Compact: 1 warmup aruncat + 4 masurate (M1-M4 din T17, aceleasi conditii).
# Comparatie: T17 EntMTP-only mediana 0.146 tok/s, static 0.127 tok/s.
import subprocess, time, requests, os, sys

ENGINE_LOG = r"D:\project colibri\engine_test_final.log"
env = os.environ.copy()
env.update({
    "COLI_ENGINE": r"D:\project_colibri_engine\c\glm_test_final.exe",
    "DIRECT": "1", "MTP_DEBUG": "1", "KVSAVE": "0",
    "PILOT_REAL": "1", "PIPE": "1", "CTX": "1024", "DRAFT": "3",
    "PIN": "auto", "COLI_RAM_OVERCOMMIT": "1",
    "ENT_MTP": "1", "MOE_SPEQ": "1",
})

logf = open(ENGINE_LOG, "w")
server = subprocess.Popen(
    [sys.executable, "c/coli", "serve", "--model", "D:\\glm52_i4",
     "--port", "8080", "--ram", "12"],
    env=env, cwd=r"D:\project_colibri_engine",
    stdout=logf, stderr=subprocess.STDOUT,
)

print("Astept motorul candidat (max 240s)...", flush=True)
up = False
for _ in range(120):
    time.sleep(2)
    try:
        if requests.get("http://127.0.0.1:8080/health", timeout=2).ok:
            up = True
            break
    except Exception:
        pass
if not up:
    print("EROARE: candidatul nu a pornit — vezi " + ENGINE_LOG, flush=True)
    server.terminate()
    sys.exit(1)
print("Candidat pornit (ENT_MTP=1 MOE_SPEQ=1). 1 warmup + 4 masurate...", flush=True)

prompts = [
    ("WARMUP", "Say hello."),
    ("M1", "Descrie un algoritm de sortare."),
    ("M2", "Cum functioneaza spec_decode?"),
    ("M3", "Scrie o poezie scurta despre iarna."),
    ("M4", "Explica teoria relativitatii."),
]

for label, p in prompts:
    t0 = time.time()
    try:
        r = requests.post(
            "http://127.0.0.1:8080/v1/chat/completions",
            json={"model": "glm-5.2-colibri",
                  "messages": [{"role": "user", "content": p}],
                  "max_tokens": 100, "temperature": 0.0},
            timeout=1200,
        )
        dt = time.time() - t0
        if r.ok:
            tok = r.json().get("usage", {}).get("completion_tokens", 0)
            print(f"[{label}] wall={dt:.1f}s tokens={tok} tok/s={tok/dt:.3f}", flush=True)
        else:
            print(f"[{label}] HTTP {r.status_code}: {r.text[:200]}", flush=True)
    except Exception as e:
        print(f"[{label}] EROARE: {e}", flush=True)

print("Gata. Opresc candidatul...", flush=True)
server.terminate()
time.sleep(3)
subprocess.run(["taskkill", "/F", "/IM", "glm_test_final.exe"], capture_output=True)
logf.close()
print("BENCHMARK CANDIDAT COMPLET.", flush=True)
