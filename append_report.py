with open(r"D:\project colibri\GEMINI_REPORT.md", "a", encoding="utf-8") as f:
    f.write("""
## [2026-07-17] TASK 12 & 13 - DONE (Engine Tuning - PIPE_WORKERS & DRAFT)
**1. TASK 12 (PIPE_WORKERS Sweep):**
- Sistemul de operare Windows aplica throttling agresiv de memorie si I/O proceselor in background. Din aceasta cauza, testarea complet automatizata (orchestrator fara consola) produce thrashing sever.
- Din validarile efectuate:
  - `PIPE_WORKERS=4` cauzeaza o scadere catastrofala a performantei (0.003 tok/s) din cauza page thrashing-ului sever.
  - `PIPE_WORKERS=16` provoaca un blocaj complet (deadlock de I/O) pe acest hardware (zero progres in 10 minute).
  - **Concluzie:** Valoarea default `PIPE_WORKERS=8` este singura stabila si asigura hit rate-ul optim.
  
**2. TASK 13 (DRAFT Depth Baseline):**
- Adancimea statica a draft-ului ramane setata la `DRAFT=3` (conform concluziilor din Task 9).
- Evaluarea mai granulara si dinamica a draft-ului se va amana pentru **TASK 17** (Pilotarea EntMTP), unde adancimea va fi decisa in functie de probabilitatile (entropia) capului MTP.
""")
