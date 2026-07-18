# Draft reply for github.com/JustVugg/colibri — discussion #207
# (post as andy12b; review before posting)

---

**Follow-up with the promised numbers: you were right — MTP wins.**

I finished the hybrid GPU-draft experiment and measured both arms honestly on the same machine (Windows 11, 32 GB RAM, GLM-5.2 int4 served from NVMe, RTX 5060 8 GB).

**Setup**
- Draft model: GLM-4 (GGUF via llama.cpp, in-process, ~5.4 GB VRAM) — GLM-family for vocab alignment; drafts are re-encoded with the GLM-5.2 tokenizer with word-boundary alignment.
- Bridge: Windows named shared memory directly into `spec_decode` in the C engine (no HTTP hop), single-slot serve_mux path, `DRAFT=3`.
- Protocol: serve mode, temperature 0 (greedy), natural-English prompts, warm setup, acceptance guard disabled (`IPC_MIN_ACC=0`) so the number is unfiltered. A shared-memory probe confirmed the verified drafts really came from the GPU (context written by the engine, `draft_length=3` answered), not from MTP fallback.

**Results — first-draft-token acceptance:**

| Draft source | Acceptance | tok/forward |
|---|---|---|
| Native MTP head (baseline) | 24/40 = **60%** | **2.0** |
| GPU GLM-4 via shared-memory IPC | 20/44 = **45.5%** | 1.82 |

Estimated all-position acceptance for the GPU draft: ~27% (≈36/132). Output quality identical and coherent in both arms.

**Conclusion:** empirically confirms your prediction. The MTP head, conditioned on the full 744B hidden state, beats an external vocab-aligned draft even with the vocabulary problem solved — and since every rejected token is a full-verification tax, the GPU draft is net negative on this configuration.

Caveats: one prompt class, 44 verify rounds in the IPC arm, and the tokenizer re-encoding step can clip acceptance at word boundaries. I'd treat 45.5% as an upper-middle estimate, not a precise figure.

**Two incidental findings from the instrumentation, possibly useful upstream:**

1. **Stale `.coli_kv` poisoning:** a KV snapshot written by a (locally patched, buggy) build was silently reloaded at every serve start (`serve_ctx_init` → `kv_disk_load`) and drove MTP acceptance to 0% until the file was deleted. A version/build stamp in the snapshot header — or a checksum — would turn a very confusing debugging session into a clear error.
2. While wiring the IPC path I hit and fixed three bugs on the serve-mux `S==1` spec-decode path in my local tree: (a) the pending token was re-forwarded at the wrong position, duplicating the first emitted token; (b) when the token budget was hit exactly, `mux_done` was never called → infinite forward loop; (c) missing `kv_bind` on the active slot. Happy to fork and open a PR with these plus the shared-memory IPC path if you want them — even with the draft experiment being a negative result, the fixes stand on their own.

Bonus negative datapoint: I also A/B-tested the "answer in dense Chinese, expand back on GPU" idea. On this int4 conversion the same content cost **62 tokens in Chinese vs 54 in English** (~1.5 chars/token on ZH), with slightly lower MTP acceptance (55% vs 60%) — so no output-compression win either. The real wins on my box remain: MTP + concise-output prompting + warm KV cache.

Thanks again for the pointers in this thread — the "verification is the bottleneck" framing is exactly what the numbers show.
