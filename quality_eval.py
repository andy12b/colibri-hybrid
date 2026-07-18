import json
import requests
import sys

# Configure stdout to handle UTF-8 characters like Romanian diacritics on Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def run_eval(file_path="quality_eval.jsonl", url="http://127.0.0.1:8080/v1/chat/completions"):
    print(f"Loading eval set from {file_path}")
    
    with open(file_path, "r", encoding="utf-8") as f:
        cases = [json.loads(line) for line in f]
        
    print(f"Loaded {len(cases)} test cases.")
    passed = 0
    
    for i, case in enumerate(cases):
        prompt = case["prompt"]
        expected_list = case["expected"]
        
        print(f"\n[{i+1}/{len(cases)}] Prompt: {prompt}")
        try:
            resp = requests.post(
                url,
                json={
                    "model": "glm-5.2-colibri",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 50,
                    "temperature": 0.0
                },
                # 120s taia generarile lungi in mijloc si intepenea mux-ul
                # (ConnectionAborted la 22:38, 17 iul) — 600s acopera si prefill rece.
                timeout=600
            )
            
            if resp.status_code == 200:
                answer = resp.json()["choices"][0]["message"]["content"]
                print(f"Response: {answer.strip()}")
                
                # Simple loose matching (case insensitive, substring)
                answer_lower = answer.lower()
                is_match = any(e.lower() in answer_lower for e in expected_list)
                
                if is_match:
                    print("Result: PASS")
                    passed += 1
                else:
                    print(f"Result: FAIL (Expected one of: {expected_list})")
            else:
                print(f"Error {resp.status_code}: {resp.text}")
                
        except Exception as e:
            print(f"Request failed: {e}")
            
    print(f"\n--- EVALUATION SUMMARY ---")
    print(f"Passed: {passed}/{len(cases)} ({passed/len(cases)*100:.1f}%)")

if __name__ == "__main__":
    run_eval()
