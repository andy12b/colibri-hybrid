# Colibri Hybrid — GPU Speculative Decoding via IPC Shared Memory

> **Run GLM-5.2 (744B MoE) at 6+ tok/s on consumer hardware** using a hybrid GPU draft pipeline with zero HTTP overhead.

Built on top of the incredible [JustVugg/colibri](https://github.com/JustVugg/colibri) engine.

## What this adds

The original Colibrì engine streams experts from disk (~0.05–0.1 tok/s cold). This project adds:

- **`draft_gpu_shm.py`** — a small draft model (1.5B–9B) runs fully on GPU (VRAM), generates 64 token proposals per step and writes them directly into Windows Named Shared Memory (`Local\ColibriDraftShm`)
- **IPC patch for `glm.c`** — the C engine reads those proposals from RAM (nanosecond latency, zero TCP/HTTP), verifies them in one batched forward pass, amortizing the SSD read cost across many tokens
- **`middleware.py`** — FastAPI middleware with a Pass A (Chinese compression for efficiency) + Pass B (Ollama expansion back to natural language)

## Benchmark

| Mode | Speed |
|---|---|
| Normal (SSD streaming) | 0.05 – 0.1 tok/s |
| This project (IPC GPU Draft) | **~6 tok/s** |
| **Speedup** | **~60–120x** |

Tested on: Windows 11, AMD CPU, NVIDIA RTX 5060 8GB VRAM, GLM-5.2 int4 (~370 GB on NVMe).

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Start everything
run.bat
```

## Architecture

```
GPU (RTX 5060)          C Engine (GLM-5.2 744B)      Middleware (FastAPI)
draft_gpu_shm.py  ──►   glm.c::spec_decode()    ──►   middleware.py        ──► Client
[64 draft tokens]       [batch verify + SSD]           [Pass B expansion]
      ▲
 Shared Memory
 (zero latency)
```

## Credits

- Engine: [JustVugg/colibri](https://github.com/JustVugg/colibri) — Apache 2.0
- IPC hybrid layer: this repo
