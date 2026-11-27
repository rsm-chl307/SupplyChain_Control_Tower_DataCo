$ErrorActionPreference = 'Stop'
$policyPath = Join-Path $env:LOCALAPPDATA 'SupplyChainCopilot\auto_run_policy.json'
if (-not (Test-Path $policyPath)) { throw 'Auto-run policy file is missing.' }
$policy = Get-Content -Raw $policyPath | ConvertFrom-Json
$policy.enabled = $false
$tempPath = "$policyPath.tmp"
$json = $policy | ConvertTo-Json -Depth 4
[System.IO.File]::WriteAllText($tempPath, $json, [System.Text.UTF8Encoding]::new($false))
Move-Item -Force $tempPath $policyPath
Write-Output 'Auto-run disabled.'
