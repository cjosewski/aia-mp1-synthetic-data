param(
    [Parameter(Mandatory = $true)][int]$ProcessId,
    [Parameter(Mandatory = $true)][int]$LocalPort
)
$ErrorActionPreference = 'Stop'
if ($ProcessId -le 1 -or $LocalPort -lt 1 -or $LocalPort -gt 65535) { throw 'Invalid tunnel identity' }
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class NativeArgv {
  [DllImport("shell32.dll", SetLastError=true, CharSet=CharSet.Unicode)]
  public static extern IntPtr CommandLineToArgvW(string commandLine, out int count);
  [DllImport("kernel32.dll", SetLastError=true)]
  public static extern IntPtr LocalFree(IntPtr memory);
}
'@
$process = Get-CimInstance Win32_Process -Filter "ProcessId = $ProcessId"
if ($null -eq $process -or [string]::IsNullOrWhiteSpace($process.CommandLine)) { throw 'Tunnel process is absent' }
$listeners = @(Get-NetTCPConnection -State Listen -LocalPort $LocalPort -ErrorAction Stop |
  Where-Object { $_.LocalAddress -eq '127.0.0.1' })
if ($listeners.Count -ne 1 -or [int]$listeners[0].OwningProcess -ne $ProcessId) { throw 'Tunnel listener owner differs' }
$count = 0
$pointer = [NativeArgv]::CommandLineToArgvW($process.CommandLine, [ref]$count)
if ($pointer -eq [IntPtr]::Zero -or $count -lt 2) { throw 'Cannot inspect tunnel arguments' }
try {
  $argv = @(
    for ($index = 0; $index -lt $count; $index++) {
      $value = [Runtime.InteropServices.Marshal]::ReadIntPtr($pointer, $index * [IntPtr]::Size)
      [Runtime.InteropServices.Marshal]::PtrToStringUni($value)
    }
  )
} finally {
  [void][NativeArgv]::LocalFree($pointer)
}
[pscustomobject]@{
  pid = [int]$process.ProcessId
  listener_pid = [int]$listeners[0].OwningProcess
  executable = [string]$process.ExecutablePath
  argv = @($argv)
  started = $process.CreationDate.ToUniversalTime().ToString('o')
} | ConvertTo-Json -Depth 4 -Compress
