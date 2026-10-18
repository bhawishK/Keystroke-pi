param(
    [ValidateSet('llm', 'random')][string]$Engine = 'llm',
    [int]$FallbackMs = 0,
    [string]$ModelPath = 'models/SmolLM2-360M-Instruct-Q4_K_M.gguf',
    [ValidateRange(1, 64)][int]$Threads = 4,
    [ValidateRange(1024, 32768)][int]$ContextSize = 2048,
    [ValidateSet('basic', 'desktop')][string]$Profile = 'basic',
    [int]$Port = 8080
)
$ErrorActionPreference = 'Stop'
$project = Split-Path -Parent $PSScriptRoot
Set-Location $project
$python = Join-Path $project '.venv/Scripts/python.exe'
if (-not (Test-Path $python)) { throw 'Run scripts/setup-local.ps1 first.' }
$serverProcess = $null
try {
    if ($Engine -eq 'llm') {
        $model = (Resolve-Path -LiteralPath $ModelPath).Path
        $server = Join-Path $project '.runtime/llama/llama-server.exe'
        if (-not (Test-Path $server)) { throw 'Local inference runtime is missing. Run setup-local.ps1.' }
        # Refuse an occupied port: never accidentally send text to another service.
        $probe = New-Object System.Net.Sockets.TcpClient
        try { $probe.Connect('127.0.0.1', $Port); $occupied = $true }
        catch { $occupied = $false }
        finally { $probe.Dispose() }
        if ($occupied) { throw "Port $Port is occupied. Stop that service or use -Port." }
        $serverProcess = Start-Process -FilePath $server -ArgumentList @(
            '-m', ('"' + $model + '"'), '--host', '127.0.0.1', '--port', $Port,
            '-c', $ContextSize, '-t', $Threads, '-np', '1'
        ) -WindowStyle Hidden -RedirectStandardOutput .runtime/server.out.log -RedirectStandardError .runtime/server.err.log -PassThru
        $deadline = (Get-Date).AddSeconds(120)
        $ready = $false
        while ((Get-Date) -lt $deadline) {
            if ($serverProcess.HasExited) { throw 'Model server exited. See .runtime/server.err.log.' }
            try {
                $health = Invoke-RestMethod "http://127.0.0.1:$Port/health" -TimeoutSec 1
                if ($health.status -eq 'ok') { $ready = $true; break }
            } catch { }
            Start-Sleep -Milliseconds 250
        }
        if (-not $ready) { throw 'Model loading timed out. See .runtime/server.err.log.' }
    }
    & $python src/main.py --window --engine $Engine --fallback-ms $FallbackMs --llm-profile $Profile --endpoint "http://127.0.0.1:$Port/v1/chat/completions"
    if ($LASTEXITCODE -ne 0) { throw "Application exited with code $LASTEXITCODE" }
} finally {
    if ($serverProcess -and -not $serverProcess.HasExited) {
        Stop-Process -Id $serverProcess.Id
    }
}
