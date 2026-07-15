import socket
import struct
import json
import requests
import threading
from transformers import PreTrainedTokenizerFast

TOKENIZER_PATH = "D:/glm52_i4/tokenizer.json"
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "glm4"
PORT = 8001

print("Loading tokenizer...")
tokenizer = PreTrainedTokenizerFast(tokenizer_file=TOKENIZER_PATH)
print("Tokenizer loaded.")

def handle_client(conn):
    try:
        while True:
            # Read length of token history (4 bytes)
            raw_len = conn.recv(4)
            if not raw_len: break
            n_tokens = struct.unpack('<I', raw_len)[0]
            if n_tokens == 0: continue
            
            # Read tokens
            tokens_data = conn.recv(n_tokens * 4)
            if not tokens_data or len(tokens_data) < n_tokens * 4: break
            tokens = struct.unpack(f'<{n_tokens}i', tokens_data)
            
            # Read how many drafts to generate
            raw_drafts = conn.recv(4)
            if not raw_drafts: break
            n_drafts = struct.unpack('<I', raw_drafts)[0]
            
            # Decode context
            context_text = tokenizer.decode(tokens)
            
            # Ask Ollama for n_drafts words
            payload = {
                "model": MODEL,
                "prompt": context_text,
                "options": {
                    "num_predict": n_drafts * 2, # Generate a bit more to ensure we have enough tokens
                    "temperature": 0.0,
                    "top_k": 1,
                    "num_ctx": 4096
                },
                "stream": False,
                "raw": True
            }
            try:
                resp = requests.post(OLLAMA_URL, json=payload, timeout=5)
                resp.raise_for_status()
                gen_text = resp.json().get("response", "")
            except Exception as e:
                print(f"Ollama error: {e}")
                gen_text = ""
            
            if gen_text:
                # Encode generated text back into GLM-5.2 tokens
                draft_tokens = tokenizer.encode(gen_text)
                if len(draft_tokens) > n_drafts:
                    draft_tokens = draft_tokens[:n_drafts]
            else:
                draft_tokens = []
            
            # Send back number of drafted tokens
            conn.sendall(struct.pack('<I', len(draft_tokens)))
            # Send tokens
            if draft_tokens:
                conn.sendall(struct.pack(f'<{len(draft_tokens)}i', *draft_tokens))
    except Exception as e:
        print(f"Client connection error: {e}")
    finally:
        conn.close()

def main():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('127.0.0.1', PORT))
    s.listen(5)
    print(f"GPU Draft server listening on port {PORT}")
    while True:
        conn, addr = s.accept()
        threading.Thread(target=handle_client, args=(conn,), daemon=True).start()

if __name__ == "__main__":
    main()
