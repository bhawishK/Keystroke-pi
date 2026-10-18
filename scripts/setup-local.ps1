param([string]$PythonExe = "python")
$ErrorActionPreference = "Stop"
$project = Split-Path -Parent $PSScriptRoot
Set-Location $project
function Check-Exit([string]$Step) {
    if ($LASTEXITCODE -ne 0) { throw "$Step failed ($LASTEXITCODE)" }
}
& $PythonExe -m venv .venv
Check-Exit "Creating virtual environment"
$python = Join-Path $project '.venv/Scripts/python.exe'
& $python -m pip install -r requirements-pi.txt huggingface_hub
Check-Exit "Installing dependencies"
New-Item -ItemType Directory -Force .runtime, models | Out-Null
$server = Join-Path $project '.runtime/llama/llama-server.exe'
if (-not (Test-Path $server)) {
    $release = Invoke-RestMethod 'https://api.github.com/repos/ggml-org/llama.cpp/releases/latest'
    $asset = $release.assets | Where-Object name -Match 'bin-win-cpu-x64.zip$' | Select-Object -First 1
    if (-not $asset) {
        $pointer = $release.assets | Where-Object name -EQ 'nightly-tag.txt' | Select-Object -First 1
        if (-not $pointer) { throw 'No Windows CPU asset or release pointer found.' }
        $response = Invoke-WebRequest $pointer.browser_download_url -UseBasicParsing
        $tag = if ($response.Content -is [byte[]]) {
            [System.Text.Encoding]::UTF8.GetString($response.Content).Trim()
        } else { $response.Content.Trim() }
        $release = Invoke-RestMethod "https://api.github.com/repos/ggml-org/llama.cpp/releases/tags/$tag"
        $asset = $release.assets | Where-Object name -Match 'bin-win-cpu-x64.zip$' | Select-Object -First 1
    }
    if (-not $asset) { throw 'No supported Windows x64 CPU runtime found.' }
    Invoke-WebRequest $asset.browser_download_url -OutFile .runtime/llama.zip -UseBasicParsing
    Expand-Archive -LiteralPath .runtime/llama.zip -DestinationPath .runtime/llama -Force
    $release.tag_name | Set-Content .runtime/llama-version.txt
}
& ./.venv/Scripts/hf.exe download bartowski/SmolLM2-360M-Instruct-GGUF SmolLM2-360M-Instruct-Q4_K_M.gguf --local-dir models
Check-Exit "Downloading model"
Write-Host 'Ready. Run: powershell -ExecutionPolicy Bypass -File scripts/run-local.ps1'
