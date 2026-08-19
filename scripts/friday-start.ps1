#Requires -Version 5.1
<#
.SYNOPSIS
    Arranque condicional do F.R.I.D.A.Y-AI no login do Windows.

.DESCRIPTION
    Mostra popup perguntando se o utilizador quer iniciar o FRIDAY.
    Se Sim: inicia LM Studio (se encontrado) e docker compose up -d.
    Se Nao: nao faz nada — servicos pesados ficam offline.
#>

$ErrorActionPreference = "Stop"

# --- Configuracao (ajustar se necessario) ---
$RepoPath = "D:\Repositories\F.R.I.D.A.Y-AI"
$LlmStudioPaths = @(
    "$env:LOCALAPPDATA\Programs\LM Studio\LM Studio.exe",
    "$env:ProgramFiles\LM Studio\LM Studio.exe",
    "${env:ProgramFiles(x86)}\LM Studio\LM Studio.exe"
)

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
    foreach ($path in $LlmStudioPaths) {
        if (Test-Path $path) {
            Write-Host "A iniciar LM Studio: $path"
            Start-Process -FilePath $path
            return $true
        }
    }
    Write-Warning "LM Studio nao encontrado. Inicia manualmente e activa o Local Server."
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

# --- Execucao ---
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
