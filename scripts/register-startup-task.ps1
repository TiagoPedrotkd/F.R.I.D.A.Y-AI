#Requires -RunAsAdministrator
#Requires -Version 5.1
<#
.SYNOPSIS
    Regista tarefa no Task Scheduler para arranque condicional do FRIDAY no login.

.DESCRIPTION
    Executar uma vez como Administrador:
        powershell -ExecutionPolicy Bypass -File scripts\register-startup-task.ps1

    Para remover:
        Unregister-ScheduledTask -TaskName FRIDAY-AI-Startup -Confirm:$false
#>

$ErrorActionPreference = "Stop"

$TaskName = "FRIDAY-AI-Startup"
$RepoPath = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$ScriptPath = Join-Path $RepoPath "scripts\friday-start.ps1"

if (-not (Test-Path $ScriptPath)) {
    Write-Error "Script nao encontrado: $ScriptPath"
}

$ArgumentList = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File ""$ScriptPath"""

$Action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $ArgumentList

$Trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME

$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 10)

$Principal = New-ScheduledTaskPrincipal `
    -UserId $env:USERNAME `
    -LogonType Interactive `
    -RunLevel Limited

$existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existing) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "Tarefa existente removida."
}

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Principal $Principal `
    -Description "Arranque condicional FRIDAY-AI - pergunta no login se iniciar servicos." | Out-Null

Write-Host "Tarefa registada com sucesso: $TaskName"
Write-Host "Executa no login de: $env:USERNAME"
Write-Host ""
Write-Host "Para testar agora:"
Write-Host "  powershell -ExecutionPolicy Bypass -File $ScriptPath"
Write-Host ""
Write-Host "Para remover:"
Write-Host "  Unregister-ScheduledTask -TaskName $TaskName -Confirm:`$false"
