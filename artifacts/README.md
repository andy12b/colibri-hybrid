# Restore artifacts

Small files that take real runtime to regenerate — kept so a reinstall starts warm.

- **`coli_usage`** — copy of `.coli_usage` from the model dir (`D:\glm52_i4\.coli_usage`).
  ~611k accumulated expert selections; fuel for the engine's `PIN=auto` hot-expert
  pinning. On reinstall, drop it back as `<model_dir>/.coli_usage`.
- **`moe_top8_table.bin`** (~195 MB) — the MoE-SpeQ `token→experts` prefetch table.
  Too big for normal git; published as a **GitHub Release asset** on this repo.
  Regenerable via `aggregate_moe*.py` from engine instrumentation, but the release
  download skips that run.
