import requests
import time

API_URL = "http://localhost:8000/v1/chat/completions"

def send_chat(messages):
    payload = {
        "model": "glm-5.2-colibri",
        "messages": messages,
        "temperature": 0.0,
        "max_tokens": 128
    }
    start = time.time()
    try:
        response = requests.post(API_URL, json=payload, timeout=3600)
        response.raise_for_status()
        res = response.json()
        ans = res["choices"][0]["message"]["content"]
        dt = time.time() - start
        print(f"[{dt:.1f}s] Assistant: {ans}")
        messages.append({"role": "assistant", "content": ans})
    except Exception as e:
        print(f"Error: {e}")

msgs = [{"role": "user", "content": "2 x 4?"}]
print(f"User: {msgs[0]['content']}")
send_chat(msgs)

msgs.append({"role": "user", "content": "și 3 x 4?"})
print(f"User: {msgs[-1]['content']}")
send_chat(msgs)
