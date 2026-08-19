#Requires -Version 5.1
<#
.SYNOPSIS
    Encontra o caminho do LM Studio.exe e sugere config para friday-config.ps1.
#>

Write-Host "=== Procurar LM Studio ===" -ForegroundColor Cyan

$found = @()

$candidates = @(
    "D:\Models\LM_STUDIO\Bionic\Bionic.exe",
    "$env:LOCALAPPDATA\Programs\LM Studio\LM Studio.exe",
    "$env:LOCALAPPDATA\LM Studio\LM Studio.exe",
    "$env:ProgramFiles\LM Studio\LM Studio.exe",
    "${env:ProgramFiles(x86)}\LM Studio\LM Studio.exe"
)

foreach ($path in $candidates) {
    if (Test-Path $path) { $found += $path }
}

$uninstallKeys = @(
    "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*",
    "HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*",
    "HKLM:\Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*"
)

foreach ($key in $uninstallKeys) {
    Get-ItemProperty $key -ErrorAction SilentlyContinue |
        Where-Object { $_.DisplayName -like "*LM Studio*" -or $_.DisplayName -like "*Bionic*" } |
        ForEach-Object {
            if ($_.DisplayIcon) {
                $icon = ($_.DisplayIcon -split ",")[0].Trim('"')
                if ((Test-Path $icon) -and ($found -notcontains $icon)) { $found += $icon }
            }
            if ($_.InstallLocation) {
                $exe = Join-Path $_.InstallLocation.Trim('"') "LM Studio.exe"
                if ((Test-Path $exe) -and ($found -notcontains $exe)) { $found += $exe }
            }
        }
}

if ($found.Count -eq 0) {
    Write-Host "LM Studio nao encontrado automaticamente." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Copia o caminho do executavel manualmente:"
    Write-Host "  1. Clique direito no atalho LM Studio -> Propriedades -> Destino"
    Write-Host "  2. copy scripts\friday-config.ps1.example scripts\friday-config.ps1"
    Write-Host "  3. Cola o caminho em `$LmStudioExe"
    exit 1
}

Write-Host "Encontrado:" -ForegroundColor Green
$found | ForEach-Object { Write-Host "  $_" }

$best = $found[0]
Write-Host ""
Write-Host "Adiciona a scripts/friday-config.ps1:" -ForegroundColor Cyan
Write-Host ('$LmStudioExe = "' + $best + '"')
