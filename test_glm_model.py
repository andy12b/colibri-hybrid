import requests
import time

def test_glm_model():
    print("Testing GLM-4 (9B) via Ollama API...")
    
    OLLAMA_API_URL = "http://localhost:11434/api/generate"
    model_id = "glm4"
    
    # Simple coding task to see if GLM-4 is responding properly
    prompt = "Scrie o funcție Python scurtă care calculează factorialul unui număr. Returnează doar codul în markdown, te rog."
    
    payload = {
        "model": model_id,
        "prompt": prompt,
        "stream": False
    }
    
    start_time = time.time()
    
    try:
        response = requests.post(OLLAMA_API_URL, json=payload, timeout=120)
        response.raise_for_status()
        result = response.json()
        
        gen_time = time.time() - start_time
        print(f"\n[Generation Time]: {gen_time:.2f} seconds")
        print(f"[Model Output]:\n{result.get('response', '')}")
        print("\n[SUCCESS] The GLM-4 primary model is working perfectly on your hardware!")
        
    except requests.exceptions.RequestException as e:
        print(f"\n[ERROR] Connection to Ollama or model inference failed: {e}")

if __name__ == "__main__":
    test_glm_model()
