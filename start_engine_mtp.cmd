@echo off
rem Porneste motorul colibri cu configul validat MTP-only (16 iulie 2026)
rem MTP e mai bun decat draftul GPU (60%% vs 45.5%%) - nu porni draft_gpu_shm.py
set DIRECT=1
set MTP_DEBUG=1
set KVSAVE=0
set PILOT=0
set PIPE=0
set CTX=1024
rem Promovate 2026-07-18 (gate calitate 19/20 identic cu baseline, +19% viteza):
set ENT_MTP=1
set MOE_SPEQ=1
"D:\project colibri\.venv\Scripts\python.exe" "D:\project_colibri_engine\c\coli" serve --model D:\glm52_i4 --port 8080 --ram 12 > "D:\project colibri\engine_test_conv1.log" 2>&1
