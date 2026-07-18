import re
import os
import sys
import glob
import json
import time
import logging
import threading
import subprocess
import requests

# llama.cpp's DLL loader resolves CUDA deps via PATH only (same shim as
# draft_gpu_shm.py) — must run before any llama_cpp import.
_SP = os.path.join(sys.prefix, "Lib", "site-packages")
_NV_DIRS = [os.path.join(_SP, "nvidia", s, "bin") for s in ("cuda_runtime", "cublas", "cuda_nvrtc")]
os.environ["PATH"] = os.pathsep.join(d for d in _NV_DIRS if os.path.isdir(d)) + os.pathsep + os.environ["PATH"]
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
    # Default 0: temp >0 prabuseste acceptarea MTP (rejection sampling) — nu
    # vrem 0.7 strecurat cand clientul omite campul.
    temperature: Optional[float] = 0.0
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

# --- In-process llama.cpp translator (preferred over the Ollama service) -----
# Lazy: nothing is loaded until the first CJK output actually needs translating,
# so the middleware costs zero VRAM/RAM extra in the (usual) English/Romanian case.
TRANSLATE_GGUF = os.environ.get("TRANSLATE_GGUF", "")

_local_llm = {"llm": None, "failed": False}
_llm_lock = threading.Lock()


def _resolve_qwen_gguf() -> str:
    """Env override, else the qwen2.5:1.5b GGUF blob already in Ollama's store."""
    if TRANSLATE_GGUF:
        return TRANSLATE_GGUF
    manifest = os.path.expanduser(
        "~/.ollama/models/manifests/registry.ollama.ai/library/qwen2.5/1.5b")
    with open(manifest, encoding="utf-8") as f:
        m = json.load(f)
    digest = next(l["digest"] for l in m["layers"]
                  if l["mediaType"] == "application/vnd.ollama.image.model")
    return os.path.expanduser("~/.ollama/models/blobs/" + digest.replace(":", "-"))


def _get_local_llm():
    with _llm_lock:
        if _local_llm["llm"] is not None or _local_llm["failed"]:
            return _local_llm["llm"]
        try:
            t0 = time.time()
            from llama_cpp import Llama
            path = _resolve_qwen_gguf()
            logger.info(f"Loading translation model into VRAM: {path}")
            _local_llm["llm"] = Llama(model_path=path, n_gpu_layers=-1, n_ctx=2048, verbose=False)
            logger.info(f"Translation model loaded in {time.time()-t0:.1f}s")
        except Exception as e:
            logger.error(f"Local llama.cpp translator unavailable ({e}); falling back to Ollama.")
            _local_llm["failed"] = True
        return _local_llm["llm"]


def translate_local(text: str) -> Optional[str]:
    """ZH->EN via in-process llama.cpp (qwen2.5-1.5b, full GPU offload).

    Returns None when unavailable/failed so the caller can fall back to Ollama.
    qwen2.5 is ChatML — the prompt is built manually so we don't depend on the
    GGUF blob carrying a chat template.
    """
    llm = _get_local_llm()
    if llm is None:
        return None
    prompt = (
        "<|im_start|>system\nYou are a translator. Translate the user's text to English. "
        "Keep formatting and [CODE_BLOCK_PLACEHOLDER] markers intact. "
        "Output only the translation.<|im_end|>\n"
        f"<|im_start|>user\n{text}<|im_end|>\n<|im_start|>assistant\n"
    )
    try:
        out = llm(prompt, max_tokens=1024, temperature=0.0, stop=["<|im_end|>"])
        result = out["choices"][0]["text"].strip()
        return result or None
    except Exception as e:
        logger.error(f"Local translation failed: {e}")
        return None


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
    
    # Translate only when the output actually contains Chinese — otherwise
    # qwen would "translate" English/Romanian answers and distort them.
    if not re.search("[一-鿿]", text_only):
        return raw_output
    # Send the non-code text to be translated by the GPU model:
    # in-process llama.cpp first (no background service), Ollama as fallback.
    translated_text = translate_local(text_only)
    if translated_text is None:
        if not ollama_available():
            logger.warning("No local translator and Ollama unreachable — returning raw output.")
            return raw_output
        translated_text = translate_on_gpu(text_only)
    
    # Re-insert the pristine code blocks
    for code in code_blocks:
        translated_text = translated_text.replace('[CODE_BLOCK_PLACEHOLDER]', code, 1)
        
    return translated_text

@app.post("/v1/chat/completions")
def chat_completions(request: ChatCompletionRequest):
    # Sync (not async) on purpose: the blocking requests.post to the engine can
    # take minutes; as a sync handler FastAPI runs it in a worker thread, so
    # /health and /ipc-stats stay responsive during generation.
    """
    OpenAI compatible endpoint that intercepts the request and handles it.
    """
    logger.info(f"Received request for model: {request.model}")
    
    # OPT3: Language-agnostic system prompt — respond in same language as user,
    # but stay ultra-concise so GLM-5.2 generates fewer tokens per idea.
    # (Chinese/dense output still benefits from MTP head at int8 acceptance rates)
    system_prompt_content = (
        "You are colibri, running the GLM model (by Zhipu AI) locally on the "
        "user's computer. Never claim to be made by Google, OpenAI or others. "
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
    if request.stream:
        # Releu SSE transparent: tokenii curg de la motor direct in UI, in timp
        # real (motorul openai_server.py emite chunk-uri OpenAI native).
        # Gate-ul de traducere CJK nu se aplica mid-stream (raspunsul e deja
        # afisat); calea non-stream pastreaza traducerea completa.
        def sse_proxy():
            try:
                with requests.post(
                    "http://localhost:8080/v1/chat/completions",
                    json={**glm_payload, "stream": True,
                          "stream_options": {"include_usage": True}},
                    # (connect, read intre chunk-uri). 900s: prefill-ul rece nu
                    # emite nimic minute bune — 300s taia cererea (eroarea din
                    # 18 iul) si abortul poate intepeni mux-ul.
                    stream=True, timeout=(10, 900),
                ) as r:
                    r.raise_for_status()
                    # chunk_size=1: iter_lines cu buffer default (512B) tine
                    # tokenii mici in buffer pana se umple — adio streaming.
                    for raw in r.iter_lines(chunk_size=1, decode_unicode=True):
                        if raw:
                            yield raw + "\n\n"
            except Exception as e:
                logger.error(f"Streaming from engine failed: {e}")
                created = int(time.time())
                cid = f"chatcmpl-colibri-{created}"
                err_chunk = {
                    "id": cid, "object": "chat.completion.chunk", "created": created,
                    "model": request.model,
                    "choices": [{"index": 0, "delta": {"role": "assistant", "content":
                        "Ne pare rău, conexiunea cu motorul GLM-5.2 a eșuat. "
                        "Verifică dacă engine-ul rulează pe portul 8080."},
                        "finish_reason": None}],
                }
                fin = {"id": cid, "object": "chat.completion.chunk", "created": created,
                       "model": request.model,
                       "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]}
                yield f"data: {json.dumps(err_chunk)}\n\n"
                yield f"data: {json.dumps(fin)}\n\n"
                yield "data: [DONE]\n\n"
        return StreamingResponse(sse_proxy(), media_type="text/event-stream")

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

_gpu_cache = {"ts": 0.0, "data": None}


@app.get("/gpu")
def gpu_info():
    """GPU-ul via nvidia-smi (motorul e CPU-only si raporteaza 0 GPU-uri).

    Cache 5s ca sa nu lansam un proces la fiecare poll al UI-ului.
    """
    now = time.time()
    if _gpu_cache["data"] is not None and now - _gpu_cache["ts"] < 5:
        return _gpu_cache["data"]
    data = {"available": False}
    try:
        out = subprocess.run(
            ["nvidia-smi",
             "--query-gpu=name,memory.total,memory.used,utilization.gpu",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=4)
        line = out.stdout.strip().splitlines()[0] if out.returncode == 0 and out.stdout.strip() else ""
        if line:
            name, mt, mu, ut = [f.strip() for f in line.split(",")]
            data = {"available": True, "name": name,
                    "vram_total_mb": int(float(mt)), "vram_used_mb": int(float(mu)),
                    "util_pct": int(float(ut))}
    except Exception:
        pass
    _gpu_cache["ts"] = now
    _gpu_cache["data"] = data
    return data


@app.get("/health")
def health():
    """Quick liveness check — useful for monitoring and run.bat startup wait."""
    return {"status": "ok", "engine": "colibri-hybrid", "version": "1.1.0"}


# --- Live draft/acceleration stats, parsed from the engine's stderr log -------
_HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE_LOG = os.environ.get("ENGINE_LOG", "")

_MTPDBG_RE = re.compile(r"\[mtpdbg\] draft0=(\d+) verified=(\d+) (HIT|miss)")
_IPC_RE = re.compile(r"\[IPC\] rounds=(\d+) acceptance (\d+)% \((\d+)/(\d+)\) \| avg wait (\d+) ms \| empty=(\d+)")
_PREFILL_RE = re.compile(r"\[prefill\] layer (\d+)/(\d+).*?(\d+) token")
_DRAFT_RE = re.compile(r"speculative decoding \(draft=(\d+)\)")


def _engine_log_path() -> Optional[str]:
    if ENGINE_LOG and os.path.exists(ENGINE_LOG):
        return ENGINE_LOG
    candidates = glob.glob(os.path.join(_HERE, "engine_test_*.log"))
    return max(candidates, key=os.path.getmtime) if candidates else None


@app.get("/ipc-stats")
def ipc_stats():
    """Draft/acceleration telemetry for the web UI, read from the engine log.

    first_token = per-round acceptance of the first draft token ([mtpdbg],
    needs MTP_DEBUG=1 on the engine); ipc = the engine's aggregate [IPC]
    counters, printed every 64 rounds; prefill = last verify-batch progress.
    """
    path = _engine_log_path()
    if not path:
        return {"available": False}
    try:
        with open(path, "rb") as f:
            f.seek(0, 2)
            size = f.tell()
            f.seek(max(0, size - 512 * 1024))
            text = f.read().decode("utf-8", "replace")
    except OSError:
        return {"available": False}

    hits = total = 0
    last_hit = None
    for m in _MTPDBG_RE.finditer(text):
        total += 1
        last_hit = m.group(3) == "HIT"
        if last_hit:
            hits += 1

    ipc = prefill = None
    for ipc in _IPC_RE.finditer(text):
        pass
    for prefill in _PREFILL_RE.finditer(text):
        pass
    draft_m = _DRAFT_RE.search(text)

    return {
        "available": True,
        "log": os.path.basename(path),
        "updated": os.path.getmtime(path),
        "draft_n": int(draft_m.group(1)) if draft_m else None,
        "first_token": {
            "hits": hits,
            "total": total,
            "pct": round(100.0 * hits / total, 1) if total else None,
            "last_hit": last_hit,
        },
        "ipc": {
            "rounds": int(ipc.group(1)),
            "acceptance_pct": int(ipc.group(2)),
            "accepted": int(ipc.group(3)),
            "proposed": int(ipc.group(4)),
            "avg_wait_ms": int(ipc.group(5)),
            "empty": int(ipc.group(6)),
        } if ipc else None,
        "prefill": {
            "layer": int(prefill.group(1)),
            "layers": int(prefill.group(2)),
            "batch": int(prefill.group(3)),
        } if prefill else None,
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

