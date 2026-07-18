import subprocess
import time
import requests
import json
import os

print("Starting server for EntMTP Benchmark (Interleaved A/B)...")
env = os.environ.copy()
env["COLI_ENGINE"] = r"D:\project_colibri_engine\c\glm_test.exe"

server = subprocess.Popen(
    ["python", "c/coli", "serve", "D:\\glm52_i4", "--port", "8080", "--cap", "1"],
    env=env,
    cwd=r"D:\project_colibri_engine",
    creationflags=subprocess.CREATE_NEW_CONSOLE # Try to give it its own normal priority console
)

time.sleep(15)
print("Server should be ready. Running 6 interleaved prompts...")

prompts = [
    "Descrie un algoritm de sortare.",
    "Cum functioneaza spec_decode?",
    "Scrie o poezie scurta despre iarna.",
    "Explica teoria relativitatii.",
    "Care este reteta pentru clatite?",
    "Enumera planetele sistemului solar."
]

for i, p in enumerate(prompts):
    # Interleaved: Prompt 1 -> use_ent_mtp=1, Prompt 2 -> use_ent_mtp=0 (based on prompt_count % 2 in glm.c)
    print(f"\n--- Prompt {i+1}/6 ---")
    t0 = time.time()
    try:
        response = requests.post(
            "http://127.0.0.1:8080/v1/chat/completions",
            json={
                "model": "glm-5.2-colibri",
                "messages": [{"role": "user", "content": p}],
                "max_tokens": 100
            },
            timeout=600
        )
        dt = time.time() - t0
        if response.status_code == 200:
            tokens = response.json()["usage"]["completion_tokens"]
            print(f"Time: {dt:.2f}s | Tokens: {tokens} | tok/s: {tokens/dt:.2f}")
        else:
            print(f"Error {response.status_code}: {response.text}")
    except Exception as e:
        print(f"Request failed: {e}")

print("Done. Killing server...")
server.terminate()
