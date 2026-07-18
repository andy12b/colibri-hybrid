# Trim working sets of all accessible processes (EmptyWorkingSet). Non-destructive:
# pages go to standby/pagefile and page back on demand. Frees RAM ahead of engine start.
param([string[]]$Exclude = @())
Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
public static class WS {
    [DllImport("psapi.dll", SetLastError=true)]
    public static extern bool EmptyWorkingSet(IntPtr hProcess);
}
"@
$before = (Get-Counter '\Memory\Available MBytes').CounterSamples[0].CookedValue / 1024
$ok = 0; $fail = 0
foreach ($p in Get-Process) {
    if ($p.Name -in @('Idle','System','Secure System','Registry','Memory Compression','csrss','smss','wininit')) { continue }
    if ($p.Name -in $Exclude) { continue }
    try {
        if ([WS]::EmptyWorkingSet($p.Handle)) { $ok++ } else { $fail++ }
    } catch { $fail++ }
}
Start-Sleep -Seconds 3
$after = (Get-Counter '\Memory\Available MBytes').CounterSamples[0].CookedValue / 1024
"trimmed $ok processes ($fail inaccessible); avail $([math]::Round($before,2)) -> $([math]::Round($after,2)) GB"
