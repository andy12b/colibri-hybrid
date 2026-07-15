import requests
import time

def test_draft_model_ollama():
    print("Testing Qwen2.5-1.5B via Ollama API...")
    
    OLLAMA_API_URL = "http://localhost:11434/api/generate"
    model_id = "qwen2.5:1.5b"
    prompt = "Please translate the following text to English: 这是一个测试。"
    
    payload = {
        "model": model_id,
        "prompt": prompt,
        "stream": False
    }
    
    start_time = time.time()
    
    try:
        response = requests.post(OLLAMA_API_URL, json=payload, timeout=60)
        response.raise_for_status()
        result = response.json()
        
        gen_time = time.time() - start_time
        print(f"\n[Generation Time]: {gen_time:.2f} seconds")
        print(f"[Model Output]: {result.get('response', '')}")
        print("\n[SUCCESS] The drafting model (Ollama) is working perfectly!")
        
    except requests.exceptions.RequestException as e:
        print(f"\n[ERROR] Connection to Ollama failed: {e}")
        print("Please ensure Ollama is running in the background.")

if __name__ == "__main__":
    test_draft_model_ollama()
