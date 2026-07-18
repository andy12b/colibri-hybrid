@echo off
rem Varianta ECO (multitasking): --ram 10 lasa ~4-6 GB in plus pentru Edge si
rem restul aplicatiilor — putin mai lent decat "best", dar fara paginare.
rem Foloseste-o cand lucrezi cu multe aplicatii deschise; "best" cand vrei
rem viteza maxima si poti inchide din ele.
set DIRECT=1
set MTP_DEBUG=1
set KVSAVE=0
set PILOT_REAL=1
set PIPE=1
set CTX=1024
set DRAFT=3
set PIN=auto
set COLI_RAM_OVERCOMMIT=1
set ENT_MTP=1
set MOE_SPEQ=1
"D:\project colibri\.venv\Scripts\python.exe" "D:\project_colibri_engine\c\coli" serve --model D:\glm52_i4 --port 8080 --ram 10 > "D:\project colibri\engine_final.log" 2>&1
