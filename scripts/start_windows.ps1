# Starts FinAlly via docker compose (Windows). Safe to run multiple times.
param(
    [switch]$Build
)

$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

if ($Build) {
    docker compose up -d --build
} else {
    docker compose up -d
}

Write-Host ""
Write-Host "FinAlly is starting at http://localhost:8000"
Write-Host "Run 'docker compose logs -f' to follow logs, or scripts\stop_windows.ps1 to stop."

Start-Process "http://localhost:8000"
