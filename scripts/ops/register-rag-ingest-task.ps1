# Register weekly RAG ingest (Task Scheduler). Run once as Admin.
# Usage: powershell -ExecutionPolicy Bypass -File scripts\register-rag-ingest-task.ps1

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$Script = Join-Path $Root "scripts\training\rag_ingest_repo.ps1"
$TaskName = "FRIDAY-AI-RAG-Ingest"

$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$Script`"" `
    -WorkingDirectory $Root
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At 3am
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Force | Out-Null
Write-Host "Registered task $TaskName (Sunday 03:00) -> $Script"
