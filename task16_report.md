## [2026-07-17] TASK 16 - DONE (Verificarea celor 25 de claim-uri de research)
**Verdict pe Prioritățile Maxime:**

1. **Modelul HuggingFace (`mateogrgic/GLM-5.2-colibri-int4-with-int8-mtp`)**:
   - **Confirmare**: DA, modelul conține capul MTP în format int8. Dimensiunea totală este de ~370 GB (140 safetensors de 2.6GB + 3 fișiere MTP masive).
   - **Compatibilitate și Acțiune**: Faptul că local obținem deja ~60% acceptance confirmă că `D:\glm52_i4` ALREADY conține capul MTP corect în format fp8/int8 (nu cel defect int4 care ar fi dat ~0% acceptance). Prin urmare, **NU este nevoie să descărcăm nimic**, modelul nostru e deja optimizat.

2. **Metodele Training-Free/Lossless pentru Speculație MoE**:
   - **MoE-Spec** (Claim 24/25): Impune un buget fix de experți `B` per layer la verificarea drafturilor, renunțând la experții cu probabilitate mică din batch. **Foarte implementabil** direct în `c/glm.c` la nivelul `moe()`, cu risc de calitate minor (poate folosi și substitutul la următorul cel mai bun expert).
   - **EntMTP** (Claim 22/23): Modifică dinamic adâncimea speculației (`DRAFT`) în funcție de entropia (încrederea) generării. **Foarte implementabil** (doar logică de prag pe logiții modelului de bază), efort mic, 100% lossless.
   - **EVICT** (Claim 17/18): Trunchiază arborele de draft înainte de verificare pe baza costului de experți. Greu de implementat nativ fără un pre-predictor de experți (oracol).
   - **SS-MoE** (Claim 19/21): Self-speculation prin reducerea experților rutați. Redondant cu MTP-ul existent în GLM-5.2 și greu de integrat curat.

3. **Discussions #209 și CACHE_ROUTE**:
   - **Legătura**: Pierderea masivă de acceptance rate raportată upstream (38% -> 21%) din cauza "rutării nedeterministe" are **exact aceeași cauză** cu rezultatul nostru prost de la `CACHE_ROUTE` (66.7% -> 56.2%). Când rutarea devine dependentă de starea cache-ului, pass-ul de verificare nu mai pică pe aceiași experți pe care i-ar fi ales modelul la o trecere normală, stricând potrivirea cu draft-ul produs independent de MTP.
   - **Acțiune**: Este clar o problemă de "state-dependent routing". Merită absolut raportată upstream sub formă de issue sau răspuns în #209.

**Top 3 Acțiuni Concrete (Efort și Risc):**
1. **Pilotarea EntMTP** (Ajustarea dinamică a `DRAFT` pe baza probabilității top-1 la prefill/decode). *Efort: Mic. Risc de calitate: Nul.*
2. **Pilotarea MoE-Spec** (Limitarea la max `B` experți unici per apel `moe()` pe batch-ul de verificare). *Efort: Mediu (modificări în routerul din `glm.c`). Risc de calitate: Mediu.*
3. **Raportarea upstream** a legăturii dintre `CACHE_ROUTE` și colapsul MTP acceptance din cauza rutării dependente de stare. *Efort: Foarte mic. Risc: Nul.*
