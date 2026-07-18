# Force system-managed pagefile growth by committing (NOT touching) memory in chunks.
# Commit charge forces Windows to extend the pagefile; on exit the charge drops but
# the extended pagefile (and thus the higher commit limit) persists until reboot.
param([int]$TargetGB = 14, [int]$ChunkMB = 512)
Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
public static class VA {
    [DllImport("kernel32.dll", SetLastError=true)]
    public static extern IntPtr VirtualAlloc(IntPtr addr, UIntPtr size, uint type, uint prot);
}
"@
$MEM_RESERVE_COMMIT = 0x3000  # MEM_COMMIT | MEM_RESERVE
$PAGE_READWRITE = 0x04
$chunk = [UIntPtr]([uint64]$ChunkMB * 1MB)
$got = 0
while ($got -lt $TargetGB * 1024) {
    $p = [VA]::VirtualAlloc([IntPtr]::Zero, $chunk, $MEM_RESERVE_COMMIT, $PAGE_READWRITE)
    if ($p -eq [IntPtr]::Zero) {
        Start-Sleep -Milliseconds 800   # give smss time to extend the pagefile, retry
        $p = [VA]::VirtualAlloc([IntPtr]::Zero, $chunk, $MEM_RESERVE_COMMIT, $PAGE_READWRITE)
        if ($p -eq [IntPtr]::Zero) { break }
    }
    $got += $ChunkMB
    if ($got % 2048 -eq 0) {
        $os = Get-CimInstance Win32_OperatingSystem
        "committed $([math]::Round($got/1024,1)) GB; limit $([math]::Round($os.TotalVirtualMemorySize/1MB,1)) GB"
    }
    Start-Sleep -Milliseconds 150
}
$os = Get-CimInstance Win32_OperatingSystem
"FINAL: committed $([math]::Round($got/1024,1)) GB; CommitLimit $([math]::Round($os.TotalVirtualMemorySize/1MB,1)) GB"
# exit releases everything; extended pagefile persists
