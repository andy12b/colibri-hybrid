# RESEARCH FINDINGS (Claude, 2026-07-17) — claim-uri NEVERIFICATE din research-ul cu agenti
# Verificarea adversariala NU a rulat (limita de tokens) — VERIFICA fiecare claim la sursa inainte sa actionezi pe el.
# Brut complet: research_final_2026-07-17.json; cautarile initiale: research_salvage_2026-07-16.jsonl

## Claim 1
- Sursa: https://github.com/JustVugg/colibri
- Colibri's PILOT env knob enables router-lookahead disk prefetch: the next layer's expert routing is ~71.6% predictable from the current layer's post-attention state, and a dedicated I/O thread prefetches those experts while the current layer computes â€” directly targeting the expert-loading-from-disk bottleneck the user measured.

## Claim 2
- Sursa: https://github.com/JustVugg/colibri
- A 2026-07-10 upstream change fixed expert-cache auto-sizing so the engine now raises the LRU cap to fill the --ram budget instead of only lowering it; before this fix, large-RAM machines used the same cache size as 16 GB systems â€” a turn-on-now (pull-and-rebuild) win for the user's 32 GB machine if their build predates it.

## Claim 3
- Sursa: https://github.com/JustVugg/colibri
- The engine auto-learns hot experts across sessions: it records actual routing frequencies to a .coli_usage file and at startup automatically pins the hottest experts in spare RAM (controlled via PIN/PIN_GB/AUTOPIN/REPIN knobs); community benchmarks attribute measurable hit-rate gains to this (e.g., Framework 13 reaching 66% expert hit with auto-learned pinning).

## Claim 4
- Sursa: https://github.com/JustVugg/colibri
- MTP speculative decoding only works with an int8-quantized MTP head â€” the original model's int4 heads yield ~0% draft acceptance with silent failure, while a correctly configured int8 head gives 39-59% acceptance; additionally, on a cold cache speculation increases expert loads from ~660 to ~1100 per token and can be a net time loss until the cache warms, and speculation is lossless in exact arithmetic but not byte-identical to non-speculative greedy in practice.

## Claim 5
- Sursa: https://github.com/JustVugg/colibri/blob/main/docs/experiments/glm52-6x5090-2026-07-12.md
- In colibri's MTP speculative decoding on GLM-5.2, the positions of a verify batch route to mostly different experts, so expert compute time scales near-linearly with speculation batch size (80ms at S=1, 168ms at S=2, 306ms at S=4) â€” meaning deeper speculation multiplies expert work rather than amortizing it.

## Claim 6
- Sursa: https://github.com/JustVugg/colibri/blob/main/docs/experiments/glm52-6x5090-2026-07-12.md
- On the full-residency 6x5090 setup, MTP speculation reduced net throughput at every draft depth tested despite high acceptance rates (draft=1: 79% acceptance but 6.79â†’6.45 tok/s, -5%; draft=2: 64% acceptance, -17%; draft=3: 69% acceptance, -10%), and the maintainer's recommended setting is DRAFT=0 when experts are fully resident.

## Claim 7
- Sursa: https://github.com/JustVugg/colibri/discussions/209
- Speculative (MTP) verification in colibri can silently lose acceptance rate because the verifier does not reproduce the drafter's routing state; three independent bug reports share this root cause, with measured MTP acceptance collapses from 33% to 4% and from 38% to 21%, and a proposed fix is enforcing state-independent expert routing within draft/verify pairs.

## Claim 8
- Sursa: https://github.com/JustVugg/colibri/discussions/209
- Int2 quantization of streamed experts (which would roughly halve the disk bytes per token, the user's stated bottleneck) is not viable naively â€” naive int2 conversion produces ~45â€“60% error â€” and requires an incoherence-rotation-aware converter pass plus A/B quality testing to be quality-neutral (tracked as issue #81).

## Claim 9
- Sursa: https://huggingface.co/mateogrgic/GLM-5.2-colibri-int4-with-int8-mtp
- Quantizing the GLM-5.2 MTP (multi-token-prediction) heads to int4 degrades speculative-decoding acceptance so badly that they are practically unusable; keeping the heads at int8 restores usable acceptance.

## Claim 10
- Sursa: https://huggingface.co/mateogrgic/GLM-5.2-colibri-int4-with-int8-mtp
- Int8 MTP heads enable native speculative decoding in colibri and deliver a major overall inference speedup versus running without a working MTP head â€” though the card gives no numbers (no tok/s, no acceptance %, no perplexity).

## Claim 11
- Sursa: https://arxiv.org/html/2511.14102v1
- A 4-bit quantized copy of an MoE model predicts the full-precision model's top-4 expert routing decisions with ~90.9% accuracy, so a cheap quantized draft pass can serve as an expert-prefetch oracle â€” directly relevant to colibri, where expert loading from NVMe (not drafting) is the bottleneck and predicted experts could be prefetched during the previous token's I/O window.

## Claim 12
- Sursa: https://arxiv.org/html/2511.14102v1
- MoE-SpeQ's speculative expert prefetching (Expert Lookahead Buffer + hierarchical entropy-aware caching in three phases) achieves expert-cache hit rates above 96% under 16-32 GB memory budgets â€” i.e., proactive prediction-driven prefetch nearly eliminates on-demand expert fetches, versus a reactive per-layer LRU cache like colibri's.

## Claim 13
- Sursa: https://arxiv.org/html/2511.14102v1
- The method is lossless in output quality: only the draft is INT4 (with non-expert parameters and shared experts kept in FP16), while every emitted token is verified by a single forward pass of the full-precision target model â€” the same verify-with-target guarantee colibri's native MTP already relies on, so the technique stacks without quality risk.

## Claim 14
- Sursa: https://arxiv.org/pdf/2508.21706
- Speculative decoding can be used specifically to hide MoE expert-offloading latency, and the SpecMoEOff system achieves up to 2.5x decode throughput over state-of-the-art MoE offloading techniques by enlarging the expert workload per transfer.

## Claim 15
- Sursa: https://arxiv.org/pdf/2508.21706
- The core mechanism is that verifying multiple draft tokens per target forward pass amortizes expert transfer cost, because the increased per-transfer workload matches the underutilized-GPU regime of MoE offloading â€” the same regime as colibri, where expert loading (not drafting) dominates each forward pass.

## Claim 16
- Sursa: https://arxiv.org/pdf/2605.00342
- Tree-based speculative decoding's advantage weakens on sparse MoE models because different draft branches activate different experts, so the union of activated experts grows with the draft tree and target-side verification cost rises substantially â€” directly analogous to colibri, where each extra activated expert is an extra NVMe load during the 744B verification pass.

## Claim 17
- Sursa: https://arxiv.org/pdf/2605.00342
- EVICT is a training-free, hyperparameter-free, and LOSSLESS adaptive verification method that truncates the draft tree before target verification, keeping only the cost-effective prefix (estimated acceptance benefit vs offline-profiled verification cost) â€” an implementable idea for colibri: budget MTP speculation depth by expected expert-load cost rather than fixed depth.

## Claim 18
- Sursa: https://arxiv.org/pdf/2605.00342
- EVICT cuts the number of activated experts during verification substantially (the paper body reports a 32.5% average reduction) while sacrificing only a modest fraction of mean accepted tokens (e.g., 3.09 vs EAGLE-3's 3.65 on Qwen3-30B-A3B) â€” i.e., in MoE spec decoding, trading a little acceptance length for far fewer expert activations is net-positive, which for colibri translates to fewer disk reads per accepted token.

## Claim 19
- Sursa: https://dl.acm.org/doi/10.1145/3774904.3792218
- A subset of a MoE model's own routed experts can serve as the draft model for speculative decoding (self-speculation), generating draft tokens with fewer experts that are then verified by the full expert routing â€” no separate draft network needed.

## Claim 20
- Sursa: https://dl.acm.org/doi/10.1145/3774904.3792218
- Under adaptive verification, SS-MoE achieves a 3.72x decoding speedup over state-of-the-art expert-offloading methods, but accuracy is only 'nearly lossless' (not strictly lossless) in that mode.

## Claim 21
- Sursa: https://dl.acm.org/doi/10.1145/3774904.3792218
- SS-MoE's conservative verification mode preserves model accuracy exactly while still decoding faster than the 4-bit quantized version of the same model â€” i.e., a strictly quality-preserving configuration exists.

## Claim 22
- Sursa: https://arxiv.org/pdf/2606.27550
- EntMTP is a training-free inference-time scheduler that dynamically switches the speculative-decoding tree topology (and thus speculation depth) based on a running estimate of local generation entropy, instead of the static tree used by existing MTP-head models.

## Claim 23
- Sursa: https://arxiv.org/pdf/2606.27550
- EntMTP is a lossless acceleration method: it does not fine-tune the base model or relax the standard acceptance condition, and measured continuation perplexity stays within 0.022 nats of the Hydra baseline.

## Claim 24
- Sursa: https://arxiv.org/pdf/2602.16052
- In MoE models, speculative decoding verification with draft trees activates far more unique experts per layer than autoregressive decoding, and this expert-loading blow-up (memory/bandwidth pressure) is what erodes speculative-decoding speedups â€” e.g. a 127-token draft tree activates 54 of 64 experts per layer on OLMoE-1B-7B. This directly matches colibri's measured situation where verification (expert loading from NVMe), not drafting, is the bottleneck.

## Claim 25
- Sursa: https://arxiv.org/pdf/2602.16052
- MoE-Spec is a training-free, verification-time technique: it enforces a fixed expert capacity budget B per layer by aggregating routing probabilities across all drafted tokens and loading only the top-B experts, with dropped experts handled by truncation (zero contribution) or substitution (rerouting to the highest-scoring available experts). Being training-free and verification-side, it is in principle implementable in colibri's C expert-streaming path.

