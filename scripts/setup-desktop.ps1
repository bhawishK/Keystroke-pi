$ErrorActionPreference = 'Stop'
Set-Location (Split-Path -Parent $PSScriptRoot)
if (-not (Test-Path .venv/Scripts/hf.exe)) {
    throw 'Run scripts/setup-local.ps1 first to install Python dependencies and the runtime.'
}
& ./.venv/Scripts/hf.exe download bartowski/Qwen2.5-3B-Instruct-GGUF Qwen2.5-3B-Instruct-Q4_K_M.gguf --local-dir models
if ($LASTEXITCODE -ne 0) { throw 'Desktop model download failed.' }
Write-Host 'Ready. Run: powershell -ExecutionPolicy Bypass -File scripts/run-desktop.ps1'
