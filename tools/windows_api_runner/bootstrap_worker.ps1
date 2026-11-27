param(
    [string]$RunnerRoot = 'C:\SupplyChainCopilot\runner',
    [string]$ContainerName = 'codex-sandbox-lab-005',
    [string]$ContainerExchange = '/workspace/SupplyChain_Control_Tower_DataCo/tmp/windows_runner_exchange'
)
$ErrorActionPreference = 'Stop'

if (-not (Test-Path (Join-Path $RunnerRoot 'tools\windows_api_runner\worker.py'))) {
    throw "Runner package not found at $RunnerRoot. Copy the standalone package first."
}
if (-not (Get-Command py.exe -ErrorAction SilentlyContinue)) {
    throw 'The Python launcher py.exe is required.'
}
if (-not (Get-Command docker.exe -ErrorAction SilentlyContinue)) {
    throw 'Docker CLI is required in the signed-in Windows user session.'
}

$stateRoot = Join-Path $env:LOCALAPPDATA 'SupplyChainCopilot'
$exchangeRoot = 'C:\SupplyChainCopilot\api_exchange'
@($stateRoot, (Join-Path $exchangeRoot 'requests'),
  (Join-Path $exchangeRoot 'responses'), (Join-Path $stateRoot 'logs')) |
    ForEach-Object { New-Item -ItemType Directory -Force -Path $_ | Out-Null }
$policyPath = Join-Path $stateRoot 'auto_run_policy.json'
if (Test-Path $policyPath) {
    try { $policy = Get-Content -Raw $policyPath | ConvertFrom-Json }
    catch { throw 'Existing local Auto-Run policy is unreadable; it was not changed.' }
    if ($policy.enabled -ne $false) {
        throw 'Auto-Run policy must already be disabled; bootstrap will not change it.'
    }
}

$taskName = 'SupplyChainCopilotLocalRunner'
$launcher = Join-Path $RunnerRoot 'tools\windows_api_runner\worker_task.ps1'
if (-not (Test-Path -LiteralPath $launcher -PathType Leaf)) { throw 'Worker task launcher is missing.' }
$arguments = "-NoProfile -NonInteractive -ExecutionPolicy Bypass -File `"$launcher`" -RunnerRoot `"$RunnerRoot`" -ContainerName $ContainerName -ContainerExchange $ContainerExchange"
$action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument $arguments -WorkingDirectory $RunnerRoot
$trigger = New-ScheduledTaskTrigger -AtLogOn -User "$env:USERDOMAIN\$env:USERNAME"
$settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -StartWhenAvailable
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" `
    -LogonType Interactive -RunLevel Limited
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger `
    -Settings $settings -Principal $principal `
    -Description 'Local Input Token Count Worker; policy remains disabled until explicitly enabled.' `
    -Force | Out-Null
Start-ScheduledTask -TaskName $taskName
Write-Output "Task installed and started: $taskName"
Write-Output "Auto-run policy: $(if (Test-Path $policyPath) { 'disabled' } else { 'not present; missing policy denies dispatch' }). No policy file was created or changed."
