import requests
import time

def test_hybrid_speed():
    print("Testing Colibri Hybrid Architecture (Middleware on port 8000)...")
    
    API_URL = "http://localhost:8000/v1/chat/completions"
    
    prompt = "Salut, scrie-mi 2 propozitii despre AI."
    
    payload = {
        "model": "glm-5.2-colibri",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.0
    }
    
    start_time = time.time()
    
    try:
        response = requests.post(API_URL, json=payload, timeout=3600)
        response.raise_for_status()
        result = response.json()
        
        gen_time = time.time() - start_time
        
        # Calculate tokens per second roughly
        output_text = result["choices"][0]["message"]["content"]
        # Very rough estimate: 1 word ~ 1.3 tokens
        estimated_tokens = len(output_text.split()) * 1.3
        tps = estimated_tokens / gen_time if gen_time > 0 else 0
        
        print(f"\n[Generation Time]: {gen_time:.2f} seconds")
        print(f"[Estimated Speed]: {tps:.2f} tokens/second")
        print(f"[Model Output]:\n{output_text}")
        print("\n[SUCCESS] The Hybrid Pipeline is responsive!")
        
    except requests.exceptions.RequestException as e:
        print(f"\n[ERROR] Connection to Middleware failed: {e}")
        print("Please ensure uvicorn middleware:app --port 8000 is running.")

if __name__ == "__main__":
    test_hybrid_speed()
