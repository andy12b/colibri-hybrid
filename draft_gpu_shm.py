"""Colibri GPU Draft Server — in-process llama.cpp edition.

Chain:  glm.c --SHM(<1ms)--> this process [llama.cpp, GLM-4 GGUF resident in VRAM]

Replaces the old Ollama HTTP path: no HTTP, no cold start (model pinned in VRAM
for the lifetime of this process), and draft tokens are re-encoded with the
GLM-5.2 tokenizer using strict boundary alignment so the first draft token
actually continues the engine's context (the old decode->generate->encode
roundtrip broke token boundaries and killed acceptance).
"""
import os
import sys
import json
import struct
import time
from multiprocessing import shared_memory
import ctypes
from ctypes import wintypes

# llama.cpp's DLL loader (winmode=RTLD_GLOBAL) resolves CUDA deps via PATH only,
# so add_dll_directory alone is not enough.
_SP = os.path.join(sys.prefix, "Lib", "site-packages")
_NV_DIRS = [os.path.join(_SP, "nvidia", s, "bin") for s in ("cuda_runtime", "cublas", "cuda_nvrtc")]
os.environ["PATH"] = os.pathsep.join(d for d in _NV_DIRS if os.path.isdir(d)) + os.pathsep + os.environ["PATH"]

from llama_cpp import Llama
from transformers import PreTrainedTokenizerFast

# ctypes definitions for Windows Events
kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)

CreateEvent = kernel32.CreateEventA
CreateEvent.restype = wintypes.HANDLE
CreateEvent.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.BOOL, wintypes.LPCSTR]

SetEvent = kernel32.SetEvent
SetEvent.restype = wintypes.BOOL
SetEvent.argtypes = [wintypes.HANDLE]

WaitForSingleObject = kernel32.WaitForSingleObject
WaitForSingleObject.restype = wintypes.DWORD
WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]

WAIT_OBJECT_0 = 0
INFINITE = 0xFFFFFFFF

# SHM Layout (must match SharedDraftMemory in glm.c):
# state(4) + ctx_len(4) + ctx_tokens(4096*4) + draft_len(4) + draft_tokens(128*4)
SHM_NAME = "ColibriDraftShm"
CTX_CAP = 4096
DRAFT_CAP = 128
SHM_SIZE = 4 + 4 + (CTX_CAP * 4) + 4 + (DRAFT_CAP * 4)
OFF_CTX_LEN = 4
OFF_CTX = 8
OFF_DRAFT_LEN = OFF_CTX + CTX_CAP * 4
OFF_DRAFT = OFF_DRAFT_LEN + 4

TOKENIZER_PATH = os.environ.get("COLI_TARGET_TOKENIZER", "D:/glm52_i4/tokenizer.json")
MAX_DRAFTS = int(os.environ.get("DRAFT", "32"))
# Draft prompt window: only the tail of the context feeds the draft model
# (recent context is what matters for imitation; keeps prompt eval cheap).
PROMPT_TAIL_TOKENS = int(os.environ.get("DRAFT_PROMPT_TAIL", "3072"))


def resolve_draft_gguf() -> str:
    """Env override, else the glm4 GGUF blob already in Ollama's store."""
    p = os.environ.get("COLI_DRAFT_GGUF")
    if p:
        return p
    manifest = os.path.expanduser(
        "~/.ollama/models/manifests/registry.ollama.ai/library/glm4/latest")
    with open(manifest, encoding="utf-8") as f:
        m = json.load(f)
    digest = next(l["digest"] for l in m["layers"]
                  if l["mediaType"] == "application/vnd.ollama.image.model")
    return os.path.expanduser("~/.ollama/models/blobs/" + digest.replace(":", "-"))


print("Loading GLM-5.2 tokenizer...")
tok52 = PreTrainedTokenizerFast(tokenizer_file=TOKENIZER_PATH)

gguf = resolve_draft_gguf()
print(f"Loading draft model into VRAM: {gguf}")
t0 = time.time()
llm = Llama(model_path=gguf, n_gpu_layers=-1, n_ctx=CTX_CAP, verbose=False)
print(f"Draft model loaded in {time.time()-t0:.1f}s")

print("Warming up (CUDA PTX JIT for Blackwell)...")
t0 = time.time()
llm("warmup", max_tokens=8, temperature=0.0)
llm.reset()
print(f"Warmup done in {time.time()-t0:.1f}s — steady-state speed from here on.")

stats = {"rounds": 0, "tokens": 0, "mismatch": 0, "gen_s": 0.0, "empty": 0}


def generate_drafts(ctx_tokens: list[int], max_drafts: int) -> list[int]:
    """Draft continuation of ctx_tokens (GLM-5.2 ids), boundary-aligned.

    1. decode full context with the GLM-5.2 tokenizer
    2. draft model continues the text (greedy — lossless verify expects a
       deterministic q distribution)
    3. re-encode context_text + generated_text with the GLM-5.2 tokenizer and
       require the context ids to reproduce exactly as a prefix; the remainder
       is the draft. A shifted boundary would make the engine verify tokens
       that don't continue its KV state -> guaranteed rejection.
    """
    ctx_text = tok52.decode(ctx_tokens, skip_special_tokens=False)
    if PROMPT_TAIL_TOKENS and len(ctx_tokens) > PROMPT_TAIL_TOKENS:
        prompt = tok52.decode(ctx_tokens[-PROMPT_TAIL_TOKENS:], skip_special_tokens=False)
    else:
        prompt = ctx_text

    out = llm(prompt, max_tokens=int(max_drafts * 1.3) + 4,
              temperature=0.0, top_k=1)
    gen_text = out["choices"][0]["text"]
    if not gen_text:
        return []

    full = tok52.encode(ctx_text + gen_text, add_special_tokens=False)
    n = len(ctx_tokens)
    if len(full) <= n or full[:n] != ctx_tokens:
        stats["mismatch"] += 1
        return []
    return full[n:n + max_drafts]


def run_draft_server():
    try:
        shm = shared_memory.SharedMemory(name=SHM_NAME, create=True, size=SHM_SIZE)
        print(f"Created new shared memory: {SHM_NAME}")
    except FileExistsError:
        shm = shared_memory.SharedMemory(name=SHM_NAME, create=False)
        print(f"Attached to existing shared memory: {SHM_NAME}")
    buffer = shm.buf

    hEvent_C_Ready = CreateEvent(None, False, False, b"Local\\Colibri_C_Ready")
    hEvent_GPU_Ready = CreateEvent(None, False, False, b"Local\\Colibri_GPU_Ready")

    print(f"GPU Draft Server ready (in-process llama.cpp, {MAX_DRAFTS} drafts/round).")

    try:
        while True:
            res = WaitForSingleObject(hEvent_C_Ready, INFINITE)
            if res != WAIT_OBJECT_0:
                continue

            ctx_len = struct.unpack_from('<i', buffer, OFF_CTX_LEN)[0]
            draft_tokens = []
            if 0 < ctx_len <= CTX_CAP:
                ctx = list(struct.unpack_from(f'<{ctx_len}i', buffer, OFF_CTX))
                t0 = time.time()
                try:
                    draft_tokens = generate_drafts(ctx, MAX_DRAFTS)
                except Exception as e:
                    print(f"Draft generation error: {e}")
                stats["gen_s"] += time.time() - t0

            n = min(len(draft_tokens), DRAFT_CAP)
            if n:
                struct.pack_into(f'<{n}i', buffer, OFF_DRAFT, *draft_tokens[:n])
            else:
                stats["empty"] += 1
            struct.pack_into('<i', buffer, OFF_DRAFT_LEN, n)

            SetEvent(hEvent_GPU_Ready)

            stats["rounds"] += 1
            stats["tokens"] += n
            if stats["rounds"] % 16 == 0:
                r = stats["rounds"]
                print(f"[draft] rounds={r} tokens={stats['tokens']} "
                      f"avg_gen={stats['gen_s']/r*1000:.0f}ms "
                      f"boundary_mismatch={stats['mismatch']} empty={stats['empty']}")
    except KeyboardInterrupt:
        print("Shutting down draft server.")
    finally:
        shm.close()


if __name__ == "__main__":
    run_draft_server()
