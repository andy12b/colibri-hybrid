# Dump top nonpaged pool consumers by tag via NtQuerySystemInformation(SystemPoolTagInformation).
# No WDK/poolmon needed. Output: tag, nonpaged bytes, alloc-free delta.
param([int]$Top = 15)
Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
public static class PoolQ {
    [DllImport("ntdll.dll")]
    public static extern int NtQuerySystemInformation(int cls, IntPtr info, int len, out int retLen);
}
"@
$cls = 22  # SystemPoolTagInformation
$size = 1MB
while ($true) {
    $buf = [Runtime.InteropServices.Marshal]::AllocHGlobal($size)
    $ret = 0
    $status = [PoolQ]::NtQuerySystemInformation($cls, $buf, $size, [ref]$ret)
    if ($status -eq 0) { break }
    [Runtime.InteropServices.Marshal]::FreeHGlobal($buf)
    if ($status -eq -1073741820) { $size = $size * 2; continue }  # STATUS_INFO_LENGTH_MISMATCH
    throw "NtQuerySystemInformation failed: 0x$($status.ToString('X8'))"
}
$count = [Runtime.InteropServices.Marshal]::ReadInt32($buf, 0)
$entrySize = 40  # x64: Tag(4)+PagedAllocs(4)+PagedFrees(4)+PagedUsed(8)+NpAllocs(4)+NpFrees(4)+NpUsed(8)+pad
$base = 8
$rows = for ($i = 0; $i -lt $count; $i++) {
    $off = $base + $i * $entrySize
    $tagBytes = New-Object byte[] 4
    [Runtime.InteropServices.Marshal]::Copy([IntPtr]::Add($buf, $off), $tagBytes, 0, 4)
    $tag = -join ($tagBytes | ForEach-Object { if ($_ -ge 32 -and $_ -le 126) { [char]$_ } else { '.' } })
    $npAllocs = [Runtime.InteropServices.Marshal]::ReadInt32($buf, $off + 24)
    $npFrees  = [Runtime.InteropServices.Marshal]::ReadInt32($buf, $off + 28)
    $npUsed   = [Runtime.InteropServices.Marshal]::ReadInt64($buf, $off + 32)
    if ($npUsed -gt 0) {
        [PSCustomObject]@{ Tag = $tag; NonPagedMB = [math]::Round($npUsed / 1MB, 1); Outstanding = $npAllocs - $npFrees }
    }
}
[Runtime.InteropServices.Marshal]::FreeHGlobal($buf)
$rows | Sort-Object NonPagedMB -Descending | Select-Object -First $Top | Format-Table -AutoSize
