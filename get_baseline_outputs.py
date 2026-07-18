import requests
import json

API_URL = "http://localhost:8000/v1/chat/completions"
OUT_FILE = "d:\\project colibri\\outputs_baseline.txt"

prompts = [
    "Why can hummingbirds hover? Answer in 2-3 sentences.",
    "Write a C function that reverses a string in place.",
    "What is 17 * 23? Show your reasoning briefly."
]

import time

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

if not wait_for_api():
    import sys
    sys.exit("API timeout")

with open(OUT_FILE, "w", encoding="utf-8") as f:
    for i, p in enumerate(prompts):
        print(f"Generating P{i+1}...")
        payload = {
            "model": "glm-5.2-colibri",
            "messages": [{"role": "user", "content": p}],
            "temperature": 0.0,
            "max_tokens": 64
        }
        resp = requests.post(API_URL, json=payload, timeout=3600)
        ans = resp.json()['choices'][0]['message']['content']
        f.write(f"=== P{i+1} ===\n{ans}\n\n")
        print(f"Done P{i+1}.")
