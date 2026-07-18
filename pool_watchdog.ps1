param([double]$KillGB = 12.0, [double]$MinAvailGB = 2.0, [int]$IntervalSec = 30, [int]$Breaches = 2)
$dir = "D:\project colibri"
$log = Join-Path $dir "pool_log.csv"
$abort = Join-Path $dir "pool_ABORT.txt"
if (Test-Path $abort) { Remove-Item $abort -Force }
"time,pool_gb,avail_ram_gb,glm_rss_gb" | Out-File $log -Encoding utf8
$breach = 0
while ($true) {
    $pool  = (Get-Counter '\Memory\Pool Nonpaged Bytes').CounterSamples[0].CookedValue / 1GB
    $avail = (Get-Counter '\Memory\Available MBytes').CounterSamples[0].CookedValue / 1024
    $glm = Get-Process glm -ErrorAction SilentlyContinue
    $rss = 0.0
    if ($glm) { $rss = ($glm | Measure-Object WorkingSet64 -Sum).Sum / 1GB }
    $line = "{0},{1},{2},{3}" -f (Get-Date).ToString('HH:mm:ss'), [math]::Round($pool,2), [math]::Round($avail,2), [math]::Round($rss,2)
    $line | Out-File $log -Append -Encoding utf8
    if ($pool -gt $KillGB -or $avail -lt $MinAvailGB) {
        $breach++
        if ($breach -lt $Breaches) { Start-Sleep -Seconds $IntervalSec; continue }
        $reason = if ($pool -gt $KillGB) { "pool $([math]::Round($pool,2)) GB > $KillGB GB" } else { "available RAM $([math]::Round($avail,2)) GB < $MinAvailGB GB" }
        "$((Get-Date).ToString('HH:mm:ss')) ABORT: $reason" | Out-File $abort -Encoding utf8
        Get-Process glm -ErrorAction SilentlyContinue | Stop-Process -Force -Confirm:$false
        Get-NetTCPConnection -LocalPort 8080 -State Listen -ErrorAction SilentlyContinue | ForEach-Object {
            Stop-Process -Id $_.OwningProcess -Force -Confirm:$false -ErrorAction SilentlyContinue
        }
        break
    }
    $breach = 0
    Start-Sleep -Seconds $IntervalSec
}
