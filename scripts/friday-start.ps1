#Requires -Version 5.1
<#
.SYNOPSIS
    Arranque condicional do F.R.I.D.A.Y-AI no login do Windows.

.DESCRIPTION
    Mostra popup perguntando se o utilizador quer iniciar o FRIDAY.
    Se Sim: inicia LM Studio (se encontrado) e docker compose up -d.
    Se Nao: nao faz nada — servicos pesados ficam offline.

    Config local: scripts/friday-config.ps1 (copiar de friday-config.ps1.example)
#>

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ConfigPath = Join-Path $ScriptDir "friday-config.ps1"
$RepoPath = "D:\Repositories\F.R.I.D.A.Y-AI"
$LmStudioExe = $env:LM_STUDIO_EXE

if (Test-Path $ConfigPath) {
    . $ConfigPath
}

function Resolve-LmStudioPath {
    if ($LmStudioExe -and (Test-Path $LmStudioExe)) {
        return $LmStudioExe
    }

    $candidates = @(
        "$env:LOCALAPPDATA\Programs\LM Studio\LM Studio.exe",
        "D:\Models\LM_STUDIO\Bionic\Bionic.exe",
        "$env:LOCALAPPDATA\LM Studio\LM Studio.exe",
        "$env:ProgramFiles\LM Studio\LM Studio.exe",
        "${env:ProgramFiles(x86)}\LM Studio\LM Studio.exe",
        "$env:USERPROFILE\AppData\Local\Programs\lm-studio\LM Studio.exe"
    )

    foreach ($path in $candidates) {
        if (Test-Path $path) { return $path }
    }

    $uninstallKeys = @(
        "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*",
        "HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*",
        "HKLM:\Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*"
    )

    foreach ($key in $uninstallKeys) {
        $apps = Get-ItemProperty $key -ErrorAction SilentlyContinue |
            Where-Object { $_.DisplayName -like "*LM Studio*" -or $_.DisplayName -like "*Bionic*" }
        foreach ($app in $apps) {
            if ($app.DisplayIcon) {
                $icon = ($app.DisplayIcon -split ",")[0].Trim('"')
                if ($icon -like "*.exe" -and (Test-Path $icon)) { return $icon }
            }
            if ($app.InstallLocation) {
                $exe = Join-Path $app.InstallLocation.Trim('"') "LM Studio.exe"
                if (Test-Path $exe) { return $exe }
                $bionic = Join-Path $app.InstallLocation.Trim('"') "Bionic.exe"
                if (Test-Path $bionic) { return $bionic }
            }
        }
    }

    return $null
}

function Show-FridayPrompt {
    Add-Type -AssemblyName System.Windows.Forms
    $result = [System.Windows.Forms.MessageBox]::Show(
        "Queres iniciar o F.R.I.D.A.Y-AI?`n`nIsto vai iniciar o LM Studio e os servicos Docker.",
        "F.R.I.D.A.Y-AI",
        [System.Windows.Forms.MessageBoxButtons]::YesNo,
        [System.Windows.Forms.MessageBoxIcon]::Question
    )
    return $result -eq [System.Windows.Forms.DialogResult]::Yes
}

function Start-LmStudio {
    $path = Resolve-LmStudioPath
    if ($path) {
        Write-Host "A iniciar LM Studio: $path"
        Start-Process -FilePath $path
        return $true
    }
    Write-Warning @"
LM Studio nao encontrado automaticamente.
Define o caminho em scripts/friday-config.ps1 (copiar de friday-config.ps1.example)
ou variavel de ambiente LM_STUDIO_EXE.
Inicia manualmente e activa o Local Server na porta 1234.
"@
    return $false
}

function Start-FridayServices {
    if (-not (Test-Path $RepoPath)) {
        Write-Error "Repo nao encontrado: $RepoPath"
        return $false
    }

    Set-Location $RepoPath

    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        Write-Error "Docker nao encontrado no PATH. Instala Docker Desktop."
        return $false
    }

    Write-Host "A iniciar servicos Docker..."
    docker compose up -d --build
    return $LASTEXITCODE -eq 0
}

if (Show-FridayPrompt) {
    Start-LmStudio | Out-Null
    Start-Sleep -Seconds 3
    if (Start-FridayServices) {
        Write-Host "FRIDAY-AI iniciado com sucesso."
    } else {
        Write-Error "Falha ao iniciar servicos Docker."
    }
} else {
    Write-Host "FRIDAY-AI nao iniciado (escolha do utilizador)."
}
