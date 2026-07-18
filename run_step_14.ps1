Write-Host "Starting Engine (14)..."
$engineProc = Start-Process "cmd.exe" -ArgumentList "/c `"start_engine_ladder_11_14.cmd`"" -WindowStyle Hidden -PassThru
Write-Host "Starting Middleware..."
$muxProc = Start-Process "cmd.exe" -ArgumentList "/c `"start_middleware.cmd`"" -WindowStyle Hidden -PassThru

Write-Host "Running tests..."
python run_ladder_test_v2.py "D:\project colibri\engine_test_ladder_11_14.log" "D:\project colibri\outputs_14.txt" > "D:\project colibri\results_14.txt"

Write-Host "Stopping processes..."
Get-Process | Where-Object { $_.Name -like "*glm*" -or $_.Name -like "*python*" } | Stop-Process -Force -ErrorAction SilentlyContinue
Write-Host "Step 14 complete."
