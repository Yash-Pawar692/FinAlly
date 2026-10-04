# Stops FinAlly via docker compose (Windows). Does not remove .\db — data persists.
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

docker compose down

Write-Host "FinAlly stopped. Your data in .\db is preserved."
