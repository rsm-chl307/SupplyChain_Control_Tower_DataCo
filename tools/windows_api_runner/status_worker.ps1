$ErrorActionPreference = 'Stop'
$task = Get-ScheduledTask -TaskName 'SupplyChainCopilotLocalRunner' -ErrorAction SilentlyContinue
if (-not $task) {
    Write-Output 'Worker task: NOT INSTALLED'
    exit 1
}
$info = Get-ScheduledTaskInfo -TaskName 'SupplyChainCopilotLocalRunner'
$policyPath = Join-Path $env:LOCALAPPDATA 'SupplyChainCopilot\auto_run_policy.json'
$enabled = $false
if (Test-Path $policyPath) {
    try {
        $policy = Get-Content -Raw $policyPath | ConvertFrom-Json
        $enabled = [bool]$policy.enabled
    }
    catch { $enabled = $false }
}
Write-Output "Task state: $($task.State)"
Write-Output "Auto-run enabled: $enabled"
Write-Output "Last run: $($info.LastRunTime)"
Write-Output "Last result: $($info.LastTaskResult)"
