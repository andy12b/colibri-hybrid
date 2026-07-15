import re
import json
import time
import logging
import requests
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional

# Basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Colibri-Middleware")

app = FastAPI(
    title="Colibri Hybrid GPU Middleware",
    description="IPC Shared Memory speculative decoding accelerator for GLM-5.2 (744B MoE)",
    version="1.1.0"
)

# Enable CORS for frontend accessibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Message(BaseModel):
    role: str
    content: str

class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[Message]
    temperature: Optional[float] = 0.7
    max_completion_tokens: Optional[int] = None
    max_tokens: Optional[int] = None
    stream: Optional[bool] = False

OLLAMA_API_URL = "http://localhost:11434/api/generate"
OLLAMA_TAGS_URL = "http://localhost:11434/api/tags"
DRAFT_MODEL = "qwen2.5:1.5b"

_ollama_check = {"ts": 0.0, "ok": False}

def ollama_available() -> bool:
    """1s probe, cached 30s — avoids a 60s hang per request when Ollama is down."""
    now = time.time()
    if now - _ollama_check["ts"] < 30:
        return _ollama_check["ok"]
    try:
        _ollama_check["ok"] = requests.get(OLLAMA_TAGS_URL, timeout=1).ok
    except Exception:
        _ollama_check["ok"] = False
    _ollama_check["ts"] = now
    return _ollama_check["ok"]

def translate_on_gpu(text: str) -> str:
    """
    Calls the local Ollama instance running Qwen2.5-1.5B to expand and translate the Chinese output 
    into English/Romanian using the 8GB RTX 5060.
    """
    logger.info(f"Translating block on GPU using Ollama ({DRAFT_MODEL})...")
    
    prompt = f"Please translate the following text to English (keep formatting intact):\n\n{text}"
    
    payload = {
        "model": DRAFT_MODEL,
        "prompt": prompt,
        "stream": False
    }
    
    try:
        response = requests.post(OLLAMA_API_URL, json=payload, timeout=60)
        response.raise_for_status()
        return response.json().get("response", "")
    except Exception as e:
        logger.error(f"Ollama translation failed: {e}")
        return f"[TRANSLATION FAILED] {text}"

def process_glm_output(raw_output: str) -> str:
    """
    Core function:
    1. Extracts code blocks (```...```)
    2. Sends ONLY the text for translation
    3. Reassembles the code blocks back in place
    """
    # Regex to find code blocks (including the backticks)
    code_blocks = re.findall(r'```.*?```', raw_output, re.DOTALL)
    
    # Replace code blocks with a placeholder to keep text structure
    text_only = re.sub(r'```.*?```', '[CODE_BLOCK_PLACEHOLDER]', raw_output, flags=re.DOTALL)
    
    # Send the non-code text to be translated by the GPU model
    if not ollama_available():
        logger.warning("Ollama unreachable — skipping GPU translation step.")
        return raw_output
    translated_text = translate_on_gpu(text_only)
    
    # Re-insert the pristine code blocks
    for code in code_blocks:
        translated_text = translated_text.replace('[CODE_BLOCK_PLACEHOLDER]', code, 1)
        
    return translated_text

@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    """
    OpenAI compatible endpoint that intercepts the request and handles it.
    """
    logger.info(f"Received request for model: {request.model}")
    
    # OPT3: Language-agnostic system prompt — respond in same language as user,
    # but stay ultra-concise so GLM-5.2 generates fewer tokens per idea.
    # (Chinese/dense output still benefits from MTP head at int8 acceptance rates)
    system_prompt_content = (
        "Be ultra-concise. Respond in the same language the user uses. "
        "For code, write it directly without extra commentary. "
        "Every word must carry information — no filler."
    )
    
    messages = [{"role": "system", "content": system_prompt_content}]
    messages.extend([{"role": m.role, "content": m.content} for m in request.messages])
    
    # Query the real GLM-5.2 engine running on port 8080
    max_tokens = request.max_completion_tokens or request.max_tokens
    glm_payload = {
        "model": "glm-5.2-colibri",
        "messages": messages,
        "temperature": request.temperature,
        **({"max_completion_tokens": max_tokens} if max_tokens else {}),
    }
    engine_failed = False
    try:
        t0 = time.time()
        glm_response = requests.post("http://localhost:8080/v1/chat/completions", json=glm_payload, timeout=900)
        glm_response.raise_for_status()
        body = glm_response.json()
        real_glm_output = body["choices"][0]["message"]["content"]
        usage = body.get("usage")
        logger.info(f"GLM-5.2 responded in {time.time()-t0:.2f}s ({len(real_glm_output)} chars)")
    except Exception as e:
        logger.error(f"Failed to query GLM engine: {e}")
        real_glm_output = "Ne pare rău, conexiunea cu motorul GLM-5.2 a eșuat. Verifică dacă glm.exe serve rulează pe portul 8080."
        usage = None
        engine_failed = True

    # Process and translate on the GPU (Etapa B) — skip on engine failure
    final_output = real_glm_output if engine_failed else process_glm_output(real_glm_output)

    created = int(time.time())
    completion_id = f"chatcmpl-colibri-{created}"

    if request.stream:
        # The web UI requests SSE (stream: true) and parses "data:" frames.
        def sse():
            chunk = {
                "id": completion_id, "object": "chat.completion.chunk", "created": created,
                "model": request.model,
                "choices": [{"index": 0, "delta": {"role": "assistant", "content": final_output}, "finish_reason": None}],
            }
            yield f"data: {json.dumps(chunk)}\n\n"
            finish = {
                "id": completion_id, "object": "chat.completion.chunk", "created": created,
                "model": request.model,
                "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
                **({"usage": usage} if usage else {}),
            }
            yield f"data: {json.dumps(finish)}\n\n"
            yield "data: [DONE]\n\n"
        return StreamingResponse(sse(), media_type="text/event-stream")

    return {
        "id": completion_id,
        "object": "chat.completion",
        "created": created,
        "model": request.model,
        "choices": [{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": final_output,
            },
            "finish_reason": "stop"
        }],
        **({"usage": usage} if usage else {}),
    }


@app.get("/v1/models")
def list_models():
    """OpenAI compatible endpoint for listing models."""
    return {
        "object": "list",
        "data": [{
            "id": "glm-5.2-colibri",
            "object": "model",
            "created": 1677610602,
            "owned_by": "colibri"
        }]
    }

@app.get("/health")
def health():
    """Quick liveness check — useful for monitoring and run.bat startup wait."""
    return {"status": "ok", "engine": "colibri-hybrid", "version": "1.1.0"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

