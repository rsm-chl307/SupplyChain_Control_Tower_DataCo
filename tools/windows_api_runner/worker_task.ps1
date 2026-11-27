param(
    [string]$RunnerRoot = 'C:\SupplyChainCopilot\runner',
    [string]$ContainerName = 'codex-sandbox-lab-005',
    [string]$ContainerExchange = '/workspace/SupplyChain_Control_Tower_DataCo/tmp/windows_runner_exchange'
)
$ErrorActionPreference = 'Stop'
$logRoot = Join-Path $env:LOCALAPPDATA 'SupplyChainCopilot\logs'
$stdoutPath = Join-Path $logRoot 'worker.stdout.log'
$stderrPath = Join-Path $logRoot 'worker.stderr.log'
$lifecyclePath = Join-Path $logRoot 'worker.lifecycle.log'
try {
    New-Item -ItemType Directory -Path $logRoot -Force | Out-Null
    Add-Content -LiteralPath $lifecyclePath -Value "$(Get-Date -Format o) START"
    Set-Location -LiteralPath $RunnerRoot
    # Windows PowerShell 5.1 can promote native stderr to a terminating error
    # under Stop, obscuring the actual Python exit code. Preserve it explicitly.
    $previousErrorAction = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        & py.exe -3 -m tools.windows_api_runner.worker --container $ContainerName `
            --container-exchange $ContainerExchange 1>> $stdoutPath 2>> $stderrPath
        $exitCode = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $previousErrorAction
    }
    if ($null -eq $exitCode) { $exitCode = 2 }
} catch {
    # Do not persist exception text: it may contain sensitive process data.
    $exitCode = 2
    if (Test-Path -LiteralPath $logRoot) {
        Add-Content -LiteralPath $stderrPath -Value "$(Get-Date -Format o) LAUNCH_ERROR $($_.Exception.GetType().Name)"
    }
} finally {
    if (Test-Path -LiteralPath $logRoot) {
        Add-Content -LiteralPath $lifecyclePath -Value "$(Get-Date -Format o) EXIT code=$exitCode"
    }
}
exit $exitCode
