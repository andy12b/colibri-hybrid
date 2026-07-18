@echo off
set DIRECT=1
set MTP_DEBUG=1
set KVSAVE=0
set PILOT_REAL=1
set PIPE=1
set CTX=1024
set DRAFT=3
set PIN=auto
set CACHE_ROUTE=1
set ROUTE_J=2
set ROUTE_M=12
set COLI_RAM_OVERCOMMIT=1
"D:\project colibri\.venv\Scripts\python.exe" "D:\project_colibri_engine\c\coli" serve --model D:\glm52_i4 --port 8080 --ram 12 > "D:\project colibri\engine_test_ladder_step6.log" 2>&1
