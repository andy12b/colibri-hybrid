@echo off
rem Porneste middleware-ul FastAPI pe portul 8000 (cu fix-ul sync + gate CJK)
cd /d "D:\project colibri"
".venv\Scripts\python.exe" middleware.py > "D:\project colibri\middleware_conv1.log" 2>&1
