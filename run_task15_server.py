import subprocess
import os
import time
import requests
import json

prompts = [
    "P1: Cum funcționează un motor MoE?",
    "P2: Write a Python script to compute the Fibonacci sequence.",
    "P3: Explain speculative decoding in large language models.",
    "Ce este fotosinteza?",
    "Write a C program to reverse a string.",
    "Define 'entropy' in the context of information theory.",
    "Cum se prepară mămăliga?",
    "Can you write a regex for an email address?",
    "Explique-moi la relativité restreinte.",
    "Write a SQL query to find the second highest salary."
]

env = os.environ.copy()
env["COLI_ENGINE"] = r"D:\project_colibri_engine\c\glm_test.exe"
env["COLI_RAM_OVERCOMMIT"] = "1"
env["PIN"] = "auto"
env["DRAFT"] = "3"

print("Starting glm_test.exe server...")
server = subprocess.Popen(
    [r"D:\project colibri\.venv\Scripts\python.exe", r"D:\project_colibri_engine\c\coli", "serve", "--model", r"D:\glm52_i4", "--ram", "12", "--port", "8080"],
    env=env,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True
)

# Wait for server to start
print("Waiting for server to become ready...")
ready = False
for line in server.stdout:
    print("[SERVER]", line.strip())
    if "OpenAI-compatible API listening" in line or "Uvicorn running" in line or "listening on" in line.lower():
        ready = True
        break
    if server.poll() is not None:
        print("Server died prematurely.")
        break

if not ready:
    print("Failed to start server.")
    server.kill()
    sys.exit(1)

print("Server is ready. Sending prompts...")

for i, p in enumerate(prompts):
    print(f"\\n--- Prompt {i+1}/{len(prompts)} ---")
    try:
        t0 = time.time()
        response = requests.post(
            "http://127.0.0.1:8080/v1/chat/completions",
            json={
                "model": "glm-5.2-colibri",
                "messages": [{"role": "user", "content": p}],
                "max_tokens": 150
            },
            timeout=300
        )
        if response.status_code == 200:
            result = response.json()
            print(f"Response in {time.time()-t0:.2f}s:")
            print(result['choices'][0]['message']['content'][:200] + "...")
        else:
            print(f"Error {response.status_code}: {response.text}")
    except Exception as e:
        print(f"Error: {e}")

print("Done. Killing server...")
server.kill()
