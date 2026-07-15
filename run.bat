@echo off
echo Starting Colibri Full Stack Environment (OPTIMIZED)
echo ===============================================

echo [1/4] Starting GPU Draft Server (IPC Shared Memory)...
start "Colibri GPU Draft Server" cmd /c "cd /d D:\"project colibri\" && .venv\Scripts\python.exe draft_gpu_shm.py"

echo [2/4] Waiting 5s for Draft Server to initialize SHM...
powershell -Command "Start-Sleep -Seconds 5"
echo [3/4] Starting GLM-5.2 Colibri Engine Server on port 8080...
echo       (OPT2: PILOT=1 PIPE=1 expert prefetch + overlap enabled)
set PILOT=1
set PIPE=1
set DRAFT=32
start "Colibri GLM Engine" "D:\project colibri\.venv\Scripts\python.exe" "D:\project_colibri_engine\c\coli" serve --model D:\glm52_i4 --port 8080

echo [4/4] Starting FastAPI Middleware on port 8000...
call ".venv\Scripts\activate.bat"
python middleware.py

pause
