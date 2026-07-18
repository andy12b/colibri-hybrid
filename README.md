# Colibri Hybrid — running a 744B MoE LLM from SSD on a laptop

Experiments, optimizations, and **honest findings** built on top of the excellent
[JustVugg/colibri](https://github.com/JustVugg/colibri) engine — which streams a
**744B-parameter GLM-5.2 Mixture-of-Experts** model from NVMe, one expert at a
time, so it runs on machines with far less RAM than the model's size.

This repo is the **pipeline + research** half of the project. The matching **engine
changes** live on a fork branch:
👉 **[`andy12b/colibri` @ branch `entmtp-speq`](https://github.com/andy12b/colibri/tree/entmtp-speq)**

> **Status:** paused / archived. The author has stepped back to let the underlying
> tech mature. Everything here is public so it can help someone else and so it can
> be re-created later. Contributions and questions welcome.

---

## TL;DR — what actually worked (and what didn't)

The bottleneck for a disk-streamed MoE is **not drafting speculative tokens — it is
verification**: every token the model *rejects* still costs a full 744B forward pass
(hundreds of random expert reads from SSD). So the winning moves reduce *wasted*
verification, not raw draft speed.

### ✅ What won (measured, lossless, promoted into the engine)

| Technique | What it does | Result |
|---|---|---|
| **EntMTP** — entropy-gated speculation depth | Picks *how many* draft tokens to verify per round from the MTP head's confidence (top-1 prob). Low confidence → speculate less; high → deeper. Lossless by construction (you choose *how much* to speculate, not *what* to accept). | **+15–19%** throughput vs static depth, quality gate identical |
| **MoE-SpeQ** — expert prefetch from drafts | Maps each speculative MTP draft token → its likely experts (via a `token→experts` table built from instrumentation) and prefetches them before verification. | **62.7%** miss-coverage (top-8 table); combined engine = **0.151 tok/s, +19%** |

Quality was gated on every change with a 20-prompt eval (`quality_eval.py`) — the
promoted engine passed **19/20** (the one "fail" is an accepted docstring-format
artifact, not a correctness regression).

### ❌ What was tried and rejected (negative results — the useful part)

| Idea | Why it seemed good | What the measurement showed |
|---|---|---|
| **GPU draft model over IPC shared memory** | A small GLM-family draft model on the RTX 5060, feeding proposals into the engine via `Local\ColibriDraftShm` (zero HTTP). | **Loses to the engine's native MTP head.** First-draft acceptance 45.5% (GPU draft) vs **60%** (MTP conditioned on the full 744B hidden state). Every rejected GPU draft is pure verification tax. |
| **Chinese-compression pipeline** | GLM "reasons" densely in Chinese, a GPU model expands to English → fewer tokens. | On the int4 colibri conversion, the same content cost **more** tokens in Chinese (~1.5 chars/token vs ~6.3 for English). Net loss. |
| `EXPERT_BUDGET`, naïve int2, mmap on Windows | Various "free speedups" from old docs. | All quarantined upstream / measured worse — they wreck quality or RSS. |

> ⚠️ **If you find this repo:** the earlier version of this README advertised
> "~6 tok/s, 60–120× speedup" from the GPU-draft/IPC path. **That was a hypothesis,
> not a measured result — and it turned out to be false.** The honest number on this
> hardware is ~**0.15 tok/s** for the 744B model, with EntMTP+SpeQ giving a **+19%**
> lossless improvement over the engine's own strong MTP baseline. Kept here so nobody
> repeats the dead ends.

---

## The hardware this ran on

A single consumer gaming **laptop** — the whole point is that 744B runs at all:

- **GPU:** NVIDIA RTX 5060 Laptop, 8 GB VRAM
- **RAM:** 32 GB DDR5 (engine auto-sizes to ~12.6 GB working set)
- **Storage:** NVMe Gen4 SSD — the model lives here (**~364 GB**, GLM-5.2 int4) and is
  streamed expert-by-expert during inference
- **OS:** Windows 11

I/O is everything: the engine does hundreds of random 4–64 KB reads per token. Faster
random-read NVMe ≈ faster inference.

---

## Architecture

```
                    ┌─────────────────────────────────────────┐
   Web UI  ───────► │  middleware.py  (FastAPI, port 8000)     │
  (React/Vite)      │  • SSE per-token streaming relay          │
                    │  • temp-0 default, /ipc-stats telemetry   │
                    └───────────────────┬──────────────────────┘
                                        │  OpenAI-compatible HTTP
                    ┌───────────────────▼──────────────────────┐
                    │  colibri engine  (glm.exe, port 8080)     │
                    │  • GLM-5.2 744B MoE, experts streamed      │
                    │    from NVMe                               │
                    │  • MTP head speculative decoding           │
                    │  • EntMTP  (dynamic depth)   [ENT_MTP=1]   │
                    │  • MoE-SpeQ (expert prefetch) [MOE_SPEQ=1] │
                    └────────────────────────────────────────────┘
```

- **Engine** (the `glm.c` changes) → [fork branch `entmtp-speq`](https://github.com/andy12b/colibri/tree/entmtp-speq)
- **Pipeline** (this repo) → middleware, web UI wiring, orchestration, benchmarks, research

---

## Reinstall / setup from scratch

For future-me or anyone reproducing it. Order matters.

### 1. Get the model (~364 GB)
The engine needs a GLM-5.2 int4 snapshot (here it lived at `D:\glm52_i4`). This is
produced from the original GLM-5.2 weights using colibri's conversion tooling — see the
[upstream colibri README](https://github.com/JustVugg/colibri) for the current, canonical
download + conversion steps. **It is not stored in git** (way over GitHub's limits).

### 2. Build the engine (with the EntMTP + MoE-SpeQ work)
```bash
git clone https://github.com/andy12b/colibri.git
cd colibri
git checkout entmtp-speq
# Build the C engine (Windows: MinGW GCC / WinLibs; see c/Makefile).
# Put temp dirs on a drive with space; produces c/glm.exe
make -C c
```
MoE-SpeQ also needs the `token→experts` table (`moe_top8_table.bin`, ~195 MB) — it is
regenerated by the instrumentation scripts in this repo (`aggregate_moe*.py`), not
committed.

### 3. Get this pipeline
```bash
git clone https://github.com/andy12b/colibri-hybrid.git
cd colibri-hybrid
python -m venv .venv && .venv\Scripts\activate
pip install fastapi uvicorn httpx llama-cpp-python   # see imports in middleware.py
```

### 4. Run the stack
```bash
start_engine_eco.cmd      # engine on :8080 (ENT_MTP=1 MOE_SPEQ=1, --ram 10)
start_middleware.cmd      # middleware on :8000
# web UI: cd web && npm install && npm run dev   (in the engine repo)
```
> Note: `run.bat` in this repo is **outdated** (it wires the rejected GPU-draft path).
> Use the `start_engine_*.cmd` / `start_middleware.cmd` starters.

### Test protocol (if you benchmark)
- **Temperature 0 is mandatory** — any temp > 0 tanks measured acceptance via rejection sampling.
- Metric: `tok/s = completion_tokens / wall_seconds`, median of 3 runs + 1 discarded warmup.
- A/B comparisons must be **interleaved in one engine session** (Windows throttles
  background processes — separate runs measure the throttle, not the algorithm).

---

## What's in here

- `middleware.py` — FastAPI relay (SSE streaming, telemetry, CJK-gated translation fallback)
- `quality_eval.py` / `quality_eval.jsonl` — the automated quality gate (run on every change)
- `aggregate_moe*.py` — build the MoE-SpeQ `token→experts` table from engine instrumentation
- `start_engine_*.cmd`, `start_middleware.cmd` — validated launchers
- `AI_HANDOFF.md`, `TASKS_FOR_GEMINI.md`, `GEMINI_REPORT.md` — the running log of a
  two-AI orchestration (Claude planned/verified, Gemini executed) that produced most of
  the round-2/round-3 work
- `upgrade_ladder_results.md`, `research_*.json*` — benchmark ladders and research notes

---

## Credits

- **Engine & the hard part:** [JustVugg/colibri](https://github.com/JustVugg/colibri) (Apache 2.0) — running 744B from SSD is their achievement.
- **EntMTP / MoE-SpeQ / pipeline / measurements:** this project. See discussion
  [#207](https://github.com/JustVugg/colibri/discussions) upstream for the datapoint report.

License: code here follows upstream (Apache 2.0) where derived; research notes are shared freely.
