param(
    [ValidateRange(0, 600000)][int]$ShuffleMs = 3000,
    [string]$ModelPath = 'models/Qwen2.5-3B-Instruct-Q4_K_M.gguf',
    [int]$Threads = 6,
    [int]$Port = 8080,
    [int]$FallbackMs = 0,
    [ValidateSet('desktop', 'basic')][string]$Profile = 'desktop'
)
$ErrorActionPreference = 'Stop'
& (Join-Path $PSScriptRoot 'run-local.ps1') -Engine llm -ModelPath $ModelPath -Threads $Threads -ContextSize 4096 -Port $Port -FallbackMs $FallbackMs -Profile $Profile -ShuffleMs $ShuffleMs
