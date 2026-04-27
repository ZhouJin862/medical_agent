Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue | ForEach-Object {
    $pid = $_.OwningProcess
    $process = Get-Process -Id $pid -ErrorAction SilentlyContinue
    [PSCustomObject]@{
        PID = $pid
        Name = $process.ProcessName
        Path = $process.Path
        CommandLine = (Get-WmiObject Win32_Process -Filter "ProcessId=$pid").CommandLine
    }
} | Format-List
