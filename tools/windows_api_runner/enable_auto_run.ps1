param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('EV-01','EV-02','EV-03','EV-04','EV-05','EV-06','EV-07','EV-08-LR')]
    [string[]]$AllowedCaseIds,
    [ValidateRange(1,100)]
    [int]$MaxRequestsPerUtcDay = 1
)
$ErrorActionPreference = 'Stop'
$policyPath = Join-Path $env:LOCALAPPDATA 'SupplyChainCopilot\auto_run_policy.json'
if (-not (Test-Path $policyPath)) { throw 'Run bootstrap_worker.ps1 first.' }
$phrase = Read-Host 'Type ENABLE LOCAL INPUT TOKEN COUNT AUTO-RUN to confirm this local policy change'
if ($phrase -cne 'ENABLE LOCAL INPUT TOKEN COUNT AUTO-RUN') {
    throw 'Auto-run policy was not changed.'
}
$policy = [ordered]@{
    schema_version = 1
    enabled = $true
    allowed_operations = @('input_token_count')
    allowed_models = @('gpt-6-luna')
    allowed_case_ids = @($AllowedCaseIds | Sort-Object -Unique)
    max_requests_per_utc_day = $MaxRequestsPerUtcDay
    max_request_bytes = 1048576
    max_payload_bytes = 786432
}
$tempPath = "$policyPath.tmp"
$json = $policy | ConvertTo-Json -Depth 4
[System.IO.File]::WriteAllText($tempPath, $json, [System.Text.UTF8Encoding]::new($false))
Move-Item -Force $tempPath $policyPath
Write-Output "Auto-run enabled for the selected Case IDs. Policy remains local at $policyPath."
