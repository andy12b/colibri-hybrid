# Upgrade Ladder Results

Acest document înregistrează rezultatele măsurătorilor și testelor efectuate în timpul procesului de upgrade către upstream pentru proiectul Colibri.

## 1. Cercetare și Verificări Pre-Upgrade
- **Upstream benchmarks (#208 & #209)**: Au fost revizuite direcțiile recomandate de upstream, în special optimizările de I/O și caching.
- **MTP Head Quantization**: Modelul curent `D:\glm52_i4` folosește `fp8` pentru weight config (`config.json`). Faptul că avem ~60% acceptance la baseline confirmă că folosim versiunea cu `int8`/`fp8` a capului MTP (și nu versiunea defectă `int4` care dă 0-4%).
- **MoE Speculative Decoding / Prefetching Papers**: Am identificat metode complet *lossless* aplicabile (PreScope, DALI - layer-ahead prefetching, EAGLE-3). Metodele hibride și I/O optimization pe Windows (IoRing / 25H2 nvme native driver) pot dubla IOPS. Nu propunem editări pe registry (IoRing) fără aprobarea user-ului, rămânem pe optimizările din codul engine-ului.

## 2. Configurații și Rezultate

### Rularea Baseline (Test Ladder Oficial)
*Configurație:* DIRECT=1 MTP_DEBUG=1 KVSAVE=0 PILOT=0 PIPE=0 CTX=1024 DRAFT=3 --ram 12
*Rezultate (mediana din 3 rulări pe 3 prompturi fixe):*
- P1 (Hummingbirds): TTFT ~453.6s, Acceptance ~66.7%
- P2 (C String): TTFT ~506.4s, Acceptance ~82.1%
- P3 (Math 17*23): TTFT ~294.2s, Acceptance ~87.5%
*Anomalii/Note:* Răspunsurile sunt corecte. [mtpdbg] se înregistrează cu succes în stderr-ul engine-ului odată ce output-ul generat e de dimensiune mai mare (nu doar un token cum făcea vechiul sanity test). Baseline verificat! Ținta de acceptance de ~60% a fost depășită.

### Treapta 1: PILOT_REAL=1
*Configurație:* DIRECT=1 MTP_DEBUG=1 KVSAVE=0 PILOT_REAL=1 PIPE=0 CTX=1024 DRAFT=3 --ram 12
*Rezultate:*
- P1: TTFT 468.9s (-3% față de baseline)
- P2: TTFT 516.0s (-2% față de baseline)
- P3: TTFT 298.0s (-1% față de baseline)
*Note:* Sporul de +11% așteptat upstream nu s-a materializat (posibil din lipsa suprapunerii cu PIPE=1). Hit rate-ul și logul explicit de prefetch (`PILOT_REAL: ...`) sunt invizibile în contextul arhitecturii middleware (sunt printate la stdout/cli, consumate de openai_server.py).

### Treapta 2: + PIPE=1
*Configurație:* DIRECT=1 MTP_DEBUG=1 KVSAVE=0 PILOT_REAL=1 PIPE=1 CTX=1024 DRAFT=3 --ram 12
*Rezultate:*
- P1: TTFT 419.3s (+10.6% vs Step 1, +7.5% vs Baseline)
- P2: TTFT 460.6s (+10.7% vs Step 1, +9.0% vs Baseline)
- P3: TTFT 269.0s (+9.7% vs Step 1, +8.5% vs Baseline)
*Note:* Suprapunerea I/O cu calculul (PIPE=1) funcționează optim. Împreună cu PILOT_REAL, oferă un spor total de 8.5-9% pe Windows. (În upstream, PIPE=1 a devenit default-ul pe Win32).

### Treapta 3: OMP Tuning (coli launcher)
*Configurație:* OMP_WAIT_POLICY=active, GOMP_SPINCOUNT=200000, OMP_DYNAMIC=FALSE, OMP_NUM_THREADS=10 (nuclee fizice).
*Rezultate:* Idem Treapta 2 (TTFT 419s / 460s / 269s)
*Note:* Acest tuning a fost deja activ din oficiu fiindcă folosim frontend-ul `coli`, care auto-injectează acest env pe Windows pentru libgomp. Performanța robustă înregistrată deja include aceste beneficii.

### Treapta 4: PIN=auto
*Configurație:* DIRECT=1 MTP_DEBUG=1 KVSAVE=0 PILOT_REAL=1 PIPE=1 CTX=1024 DRAFT=3 PIN=auto --ram 12
*Rezultate:*
- P1: TTFT 361.4s (+13.8% vs Step 3, +20.3% vs Baseline)
- P2: TTFT 417.9s (+9.3% vs Step 3, +17.5% vs Baseline)
- P3: TTFT 242.2s (+10.0% vs Step 3, +17.7% vs Baseline)
*Note:* Pinning-ul (0 VRAM + 528 RAM expert = 10.0 GB warm) oferă cel mai consistent spor de performanță pe Windows, eliminând page-faulturile reci pentru cei mai accesați experți (conform istoric 611k selecții). Cumulat cu `PIPE=1` și `PILOT_REAL=1`, câștigul total este de ~18-20% față de baseline.

### Treapta 5: CACHE_ROUTE=1 (Experiment)
*Configurație:* DIRECT=1 MTP_DEBUG=1 KVSAVE=0 PILOT_REAL=1 PIPE=1 CTX=1024 DRAFT=3 PIN=auto CACHE_ROUTE=1 ROUTE_J=2 ROUTE_M=12 COLI_RAM_OVERCOMMIT=1 --ram 12
*Rezultate:*
- P1: TTFT 398.5s (Acceptance scăzut la 56.2%)
- P2: TTFT 405.8s (Acceptance 82.1%)
- P3: TTFT 232.1s (Acceptance 86.7%)
*Note:* **[OUTPUT DIFERIT]**. Implementarea CACHE_ROUTE produce alterații în output-ul final (temperature=0), făcându-l complet nedeterminist. La prompt-ul C, modelul generează un alt algoritm (folosind strlen). Acceptance-ul MTP scade la P1 pentru că drafturile diverg. Experimentul confirmă o reducere a costului (timpi ușor mai buni la P2/P3), dar sacrificiul de calitate este semnificativ. Optimizarea va fi lăsată pe OPRIT.

Următorul pas: Starterul final.


## [CLAUDE] TASK 17 � VERDICT BENCHMARK EntMTP (rulat de Claude, foreground)
- Protocol: interleaved A/B in aceeasi sesiune glm_test.exe, temp 0, max 100
  tokeni, 2 warmup aruncate, config complet (PILOT_REAL+PIPE+PIN=auto+ram12).
- Paritate confirmata din cod+log: impare=EntMTP, pare=static DRAFT=3.
- REZULTAT: EntMTP 0.146/0.165/0.134 (mediana 0.146 tok/s) vs static
  0.125/0.134/0.127 (mediana 0.127) = +15% PENTRU EntMTP, consistent
  (fiecare rulare EntMTP > rularile statice vecine). 290 runde [mtpdbg] in
  engine_test_t17.log pentru analiza fina ulterioara.
- DECIZIE: EntMTP e CANDIDAT DE PROMOVARE in glm.exe � decizia finala la
  user, pe aceste cifre. glm.exe ramane neatins pana atunci.
- Gemini: poti folosi acum portul 8080/glm_test.exe pentru T18 cand e gata.
