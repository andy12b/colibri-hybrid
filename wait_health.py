import requests
import time
print("Waiting for API...")
for _ in range(300):
    try:
        resp = requests.get("http://localhost:8000/health", timeout=1)
        if resp.status_code == 200:
            print("API ready!")
            break
    except Exception:
        time.sleep(1)
