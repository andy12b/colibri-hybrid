# T17 EntMTP interleaved A/B — versiunea corectata de Claude
# Fixuri fata de v1: temperature=0 obligatoriu; configul castigator complet
# (PILOT_REAL/PIPE/PIN/ram 12/overcommit); 2 prompturi de incalzire aruncate
# (paritatile se pastreaza echilibrate: 3 masuratori per brat); cleanup complet.
import subprocess, time, requests, os, sys

ENGINE_LOG = r"D:\project colibri\engine_test_t17.log"
env = os.environ.copy()
env.update({
    "COLI_ENGINE": r"D:\project_colibri_engine\c\glm_test.exe",
    "DIRECT": "1", "MTP_DEBUG": "1", "KVSAVE": "0",
    "PILOT_REAL": "1", "PIPE": "1", "CTX": "1024", "DRAFT": "3",
    "PIN": "auto", "COLI_RAM_OVERCOMMIT": "1",
})

logf = open(ENGINE_LOG, "w")
server = subprocess.Popen(
    [sys.executable, "c/coli", "serve", "--model", "D:\\glm52_i4",
     "--port", "8080", "--ram", "12"],
    env=env, cwd=r"D:\project_colibri_engine",
    stdout=logf, stderr=subprocess.STDOUT,
)

print("Astept motorul (max 180s)...", flush=True)
up = False
for _ in range(90):
    time.sleep(2)
    try:
        if requests.get("http://127.0.0.1:8080/health", timeout=2).ok:
            up = True
            break
    except Exception:
        pass
if not up:
    print("EROARE: motorul nu a pornit — vezi " + ENGINE_LOG, flush=True)
    server.terminate()
    sys.exit(1)
print("Motor pornit. Rulez 2 warmup (aruncate) + 6 masurate...", flush=True)

prompts = [
    ("WARMUP-A", "Say hello."),
    ("WARMUP-B", "Say goodbye."),
    ("M1", "Descrie un algoritm de sortare."),
    ("M2", "Cum functioneaza spec_decode?"),
    ("M3", "Scrie o poezie scurta despre iarna."),
    ("M4", "Explica teoria relativitatii."),
    ("M5", "Care este reteta pentru clatite?"),
    ("M6", "Enumera planetele sistemului solar."),
]
# Paritate request in glm_test.exe: request 1,3,5,7 = un brat; 2,4,6,8 = celalalt.
# Warmup-urile consuma paritatile 1-2, deci M1..M6 raman echilibrate 3/3.

for label, p in prompts:
    t0 = time.time()
    try:
        r = requests.post(
            "http://127.0.0.1:8080/v1/chat/completions",
            json={"model": "glm-5.2-colibri",
                  "messages": [{"role": "user", "content": p}],
                  "max_tokens": 100, "temperature": 0.0},
            timeout=900,
        )
        dt = time.time() - t0
        if r.ok:
            tok = r.json().get("usage", {}).get("completion_tokens", 0)
            print(f"[{label}] wall={dt:.1f}s tokens={tok} tok/s={tok/dt:.3f}", flush=True)
        else:
            print(f"[{label}] HTTP {r.status_code}: {r.text[:200]}", flush=True)
    except Exception as e:
        print(f"[{label}] EROARE: {e}", flush=True)

print("Gata. Opresc serverul...", flush=True)
server.terminate()
time.sleep(3)
subprocess.run(["taskkill", "/F", "/IM", "glm_test.exe"],
               capture_output=True)
logf.close()
print("BENCHMARK COMPLET.", flush=True)
