# Commit escrow v2: holds a large UNTOUCHED committed block so the auto-managed pagefile
# stays extended (commit limit stays high), then releases 512MB chunks whenever free
# commit drops below FloorGB, so the engine never hits the commit wall.
# Untouched commit costs zero physical RAM.
param([int]$TargetGB = 14, [double]$FloorGB = 2.5, [int]$ChunkMB = 512)
Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
public static class VA2 {
    [DllImport("kernel32.dll", SetLastError=true)]
    public static extern IntPtr VirtualAlloc(IntPtr addr, UIntPtr size, uint type, uint prot);
    [DllImport("kernel32.dll", SetLastError=true)]
    public static extern bool VirtualFree(IntPtr addr, UIntPtr size, uint type);
}
"@
$dir = "D:\project colibri"
$readyFile = Join-Path $dir "escrow_ready.txt"
$abortFile = Join-Path $dir "pool_ABORT.txt"
if (Test-Path $readyFile) { Remove-Item $readyFile -Force }
$chunk = [UIntPtr]([uint64]$ChunkMB * 1MB)
$held = New-Object System.Collections.ArrayList

function Get-FreeCommitGB {
    $os = Get-CimInstance Win32_OperatingSystem
    return [math]::Round($os.FreeVirtualMemory / 1MB, 2)
}

$n = [int]($TargetGB * 1024 / $ChunkMB)
for ($i = 0; $i -lt $n; $i++) {
    $p = [VA2]::VirtualAlloc([IntPtr]::Zero, $chunk, 0x3000, 0x04)
    if ($p -eq [IntPtr]::Zero) {
        Start-Sleep -Milliseconds 800
        $p = [VA2]::VirtualAlloc([IntPtr]::Zero, $chunk, 0x3000, 0x04)
        if ($p -eq [IntPtr]::Zero) { break }
    }
    [void]$held.Add($p)
    Start-Sleep -Milliseconds 100
}
"HOLD: committed $($held.Count) chunks ($([math]::Round($held.Count*$ChunkMB/1024,1)) GB), free commit $(Get-FreeCommitGB) GB"
"ready" | Out-File $readyFile -Encoding ascii

$deadline = (Get-Date).AddHours(2)
while ($held.Count -gt 0 -and (Get-Date) -lt $deadline) {
    if (Test-Path $abortFile) { break }
    $freeCommit = Get-FreeCommitGB
    $released = 0
    while ($freeCommit -lt $FloorGB -and $released -lt 6 -and $held.Count -gt 0) {
        $p = $held[0]; $held.RemoveAt(0)
        [void][VA2]::VirtualFree($p, [UIntPtr]::Zero, 0x8000)
        $released++; $freeCommit += $ChunkMB / 1024
    }
    if ($released -gt 0) {
        "$((Get-Date).ToString('HH:mm:ss')) released $released; left $($held.Count); freeCommit $(Get-FreeCommitGB) GB"
    }
    Start-Sleep -Seconds 1
}
"ESCROW_DONE left=$($held.Count)"
