param(
    [string]$ContainerName = 'codex-sandbox-lab-005',
    [string]$RepositoryPath = '/workspace/SupplyChain_Control_Tower_DataCo',
    [string]$RunnerRoot = 'C:\SupplyChainCopilot\runner',
    [string]$ExpectedContainerExchange = '/workspace/SupplyChain_Control_Tower_DataCo/tmp/windows_runner_exchange'
)
$ErrorActionPreference = 'Stop'

# PowerShell 5.1-compatible, fail-closed deployer. It never reads Credential
# Manager and never copies or changes Auto-Run policy or exchange contents.
function Invoke-DockerChecked {
    param([Parameter(Mandatory=$true)][string[]]$DockerArgs)
    $output = & docker.exe @DockerArgs 2>&1
    if ($LASTEXITCODE -ne 0) { throw "Docker command failed: docker $($DockerArgs -join ' ')" }
    return $output
}
function Assert-TaskPrincipal {
    param($Principal)
    $expectedUser = "$env:USERDOMAIN\$env:USERNAME"
    $expectedSid = [System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value
    $actualUser = [string]$Principal.UserId
    $actualLogon = [string]$Principal.LogonType
    $actualRunLevel = [string]$Principal.RunLevel
    $actualSid = 'UNRESOLVED'
    try {
        if ($actualUser -match '^S-1-') { $actualSid = $actualUser }
        else {
            $account = New-Object -TypeName System.Security.Principal.NTAccount -ArgumentList $actualUser
            $actualSid = $account.Translate([System.Security.Principal.SecurityIdentifier]).Value
        }
    } catch { $actualSid = 'UNRESOLVED' }
    if ($actualSid -ne $expectedSid -or
        @('Interactive','InteractiveToken') -notcontains $actualLogon -or
        @('Limited','LeastPrivilege') -notcontains $actualRunLevel) {
        throw "Worker Task principal mismatch: actual UserId=$actualUser SID=$actualSid LogonType=$actualLogon RunLevel=$actualRunLevel; expected UserId=$expectedUser SID=$expectedSid LogonType=Interactive/InteractiveToken RunLevel=Limited/LeastPrivilege."
    }
}

if ($PSVersionTable.PSVersion.Major -lt 5) { throw 'Windows PowerShell 5.1 or later is required.' }
if (-not (Get-Command py.exe -ErrorAction SilentlyContinue)) { throw 'Python launcher py.exe is required.' }
if (-not (Get-Command docker.exe -ErrorAction SilentlyContinue)) { throw 'Docker CLI is required.' }
if ([string]::IsNullOrWhiteSpace($env:LOCALAPPDATA)) { throw 'LOCALAPPDATA is unavailable.' }
$version = (& py.exe -3 --version 2>&1 | Out-String).Trim()
if ($LASTEXITCODE -ne 0 -or $version -notmatch '^Python 3\.(\d+)') { throw 'Python 3 could not be verified.' }
if ([int]$Matches[1] -lt 10) { throw "Python 3.10 or later is required; found $version." }

$running = (Invoke-DockerChecked @('inspect','--format','{{.State.Running}}',$ContainerName) | Out-String).Trim()
if ($running -ne 'true') { throw "Container $ContainerName is not running; nothing was deployed." }
Invoke-DockerChecked @('exec',$ContainerName,'test','-d',$RepositoryPath) | Out-Null
$sourceRoot = "$RepositoryPath/tools/windows_api_runner"
Invoke-DockerChecked @('exec',$ContainerName,'test','-f',"$sourceRoot/source-manifest.json") | Out-Null
Invoke-DockerChecked @('exec',$ContainerName,'test','-d',$ExpectedContainerExchange) | Out-Null

$taskName = 'SupplyChainCopilotLocalRunner'
$launcher = Join-Path $RunnerRoot 'tools\windows_api_runner\worker_task.ps1'
$expectedArgs = "-NoProfile -NonInteractive -ExecutionPolicy Bypass -File `"$launcher`" -RunnerRoot `"$RunnerRoot`" -ContainerName $ContainerName -ContainerExchange $ExpectedContainerExchange"
$task = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($task) {
    $action = @($task.Actions)[0]
    $expectedWorking = (Resolve-Path -LiteralPath $RunnerRoot -ErrorAction SilentlyContinue).Path
    if ($action.Execute -ne 'powershell.exe' -or $action.Arguments -ne $expectedArgs -or
        -not $expectedWorking -or $action.WorkingDirectory -ne $expectedWorking) {
        throw 'Existing Task Scheduler action differs from the expected Runner. No task or files were changed.'
    }
    Assert-TaskPrincipal $task.Principal
}

$stateRoot = Join-Path $env:LOCALAPPDATA 'SupplyChainCopilot'
$policyPath = Join-Path $stateRoot 'auto_run_policy.json'
if (Test-Path -LiteralPath $policyPath) {
    try { $policy = Get-Content -Raw -LiteralPath $policyPath | ConvertFrom-Json }
    catch { throw 'Auto-Run policy is unreadable; it was not changed.' }
    if ($policy.enabled -ne $false) { throw 'Auto-Run is not disabled; deployment stopped without changing policy.' }
}
$statePath = Join-Path $stateRoot 'runner_state.sqlite3'
$runnerPackage = Join-Path $RunnerRoot 'tools\windows_api_runner'
if (-not (Test-Path -LiteralPath $RunnerRoot -PathType Container)) {
    throw "Runner root must already exist: $RunnerRoot"
}
if (-not (Test-Path -LiteralPath $runnerPackage -PathType Container)) {
    throw "Existing Runner package is missing at $runnerPackage; deployment requires an inspected installation."
}
$wasRunning = $task -and $task.State.ToString() -eq 'Running'

$id = [guid]::NewGuid().ToString('N')
$workRoot = Join-Path $env:TEMP "P5RunnerDeploy_$id"
$stageRoot = Join-Path $workRoot 'stage'
$backupRoot = Join-Path $env:LOCALAPPDATA "SupplyChainCopilot\backups\$id"
$stagePackage = Join-Path $stageRoot 'tools\windows_api_runner'
New-Item -ItemType Directory -Path $stagePackage,$backupRoot -Force | Out-Null
try {
    $manifestPath = Join-Path $stagePackage 'source-manifest.json'
    Invoke-DockerChecked @('cp',"${ContainerName}:${sourceRoot}/source-manifest.json",$manifestPath) | Out-Null
    $containerManifestLine = (Invoke-DockerChecked @('exec',$ContainerName,'sha256sum',"$sourceRoot/source-manifest.json") | Out-String).Trim()
    $containerManifestHash = ($containerManifestLine -split '\s+')[0].ToLowerInvariant()
    $stagedManifestHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $manifestPath).Hash.ToLowerInvariant()
    if ($containerManifestHash -notmatch '^[0-9a-f]{64}$' -or $stagedManifestHash -ne $containerManifestHash) {
        throw 'Source manifest transfer SHA-256 verification failed.'
    }
    $manifest = Get-Content -Raw -LiteralPath $manifestPath | ConvertFrom-Json
    if ($manifest.schema_version -ne 1 -or -not $manifest.files -or $manifest.files.Count -lt 1) {
        throw 'Container source manifest is invalid.'
    }
    $scriptHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $PSCommandPath).Hash.ToLowerInvariant()
    if ($scriptHash -ne $manifest.deployment_script_sha256) {
        throw 'Deployment script does not match the Container source manifest.'
    }
    $entries = @($manifest.files)
    $seen = @{}
    foreach ($entry in $entries) {
        $relative = [string]$entry.path
        if ([string]::IsNullOrWhiteSpace($relative) -or $relative -match '(^/|(^|/)\.\.(\/|$)|\\|:)' -or $seen.ContainsKey($relative)) {
            throw 'Source manifest contains an unsafe or duplicate path.'
        }
        if ($entry.sha256 -notmatch '^[0-9a-f]{64}$') { throw "Invalid source hash for $relative" }
        $seen[$relative] = $true
        $destination = Join-Path $stagePackage ($relative -replace '/', '\')
        New-Item -ItemType Directory -Path (Split-Path -Parent $destination) -Force | Out-Null
        Invoke-DockerChecked @('cp',"${ContainerName}:${sourceRoot}/$relative",$destination) | Out-Null
        if (-not (Test-Path -LiteralPath $destination -PathType Leaf)) { throw "Missing source file: $relative" }
        $actual = (Get-FileHash -Algorithm SHA256 -LiteralPath $destination).Hash.ToLowerInvariant()
        if ($actual -ne $entry.sha256) { throw "Staged source SHA-256 mismatch: $relative" }
    }
    # Display intended changes without exposing file contents.
    foreach ($entry in $entries) {
        $target = Join-Path $runnerPackage ($entry.path -replace '/', '\')
        $disposition = if (Test-Path -LiteralPath $target -PathType Leaf) { 'UPDATE/COMPARE' } else { 'ADD' }
        Write-Output "$disposition $($entry.path) sha256=$($entry.sha256)"
    }
    Get-ChildItem -LiteralPath $runnerPackage -Force -Recurse -File | ForEach-Object {
        $relative = $_.FullName.Substring($runnerPackage.Length).TrimStart('\').Replace('\','/')
        if (-not $seen.ContainsKey($relative)) { Write-Output "PRESERVE-IN-BACKUP $relative" }
    }
    if (Test-Path -LiteralPath $policyPath) { Write-Output 'PRESERVE auto_run_policy.json (disabled)' }
    else { Write-Output 'PRESERVE policy state (file absent; absent policy denies dispatch)' }
    if (Test-Path -LiteralPath $statePath) { Write-Output 'BACKUP runner_state.sqlite3 using SQLite online backup (WAL-aware)' }
    else { Write-Output 'PRESERVE runner state (no existing SQLite file)' }

    # Back up Runner files/configuration and task definition before any switch.
    Copy-Item -LiteralPath $runnerPackage -Destination (Join-Path $backupRoot 'windows_api_runner') -Recurse
    if (Test-Path -LiteralPath $policyPath) { Copy-Item -LiteralPath $policyPath -Destination (Join-Path $backupRoot 'auto_run_policy.json') }
    if ($task) {
        Export-ScheduledTask -TaskName $taskName | Set-Content -LiteralPath (Join-Path $backupRoot 'task.xml') -Encoding UTF8
    }
    if (Test-Path -LiteralPath $statePath) {
        $backupState = Join-Path $backupRoot 'runner_state.sqlite3'
        & py.exe -3 (Join-Path $stagePackage 'backup_runner_state.py') --source $statePath --destination $backupState | Out-Null
        if ($LASTEXITCODE -ne 0) { throw 'WAL-aware Runner SQLite snapshot/schema validation failed; deployment stopped.' }
    }

    # No target changes occur until every manifest file and backup validates.
    if ($wasRunning) {
        Stop-ScheduledTask -TaskName $taskName
        $stopDeadline = (Get-Date).AddSeconds(30)
        do {
            $stoppedTask = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
            if ($stoppedTask -and $stoppedTask.State.ToString() -ne 'Running') { break }
            Start-Sleep -Milliseconds 500
        } while ((Get-Date) -lt $stopDeadline)
        if (-not $stoppedTask -or $stoppedTask.State.ToString() -eq 'Running') {
            Start-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
            throw 'Verified Worker did not stop; deployment files remain unchanged.'
        }
    }
    $oldPackage = Join-Path $backupRoot 'active_old_package'
    $packageMoved = $false
    try {
        Move-Item -LiteralPath $runnerPackage -Destination $oldPackage
        $packageMoved = $true
        Copy-Item -LiteralPath $stagePackage -Destination $runnerPackage -Recurse
        foreach ($entry in $entries) {
            $target = Join-Path $runnerPackage ($entry.path -replace '/', '\')
            $actual = (Get-FileHash -Algorithm SHA256 -LiteralPath $target).Hash.ToLowerInvariant()
            if ($actual -ne $entry.sha256) { throw "Installed SHA-256 mismatch: $($entry.path)" }
        }
        Copy-Item -LiteralPath $manifestPath -Destination (Join-Path $runnerPackage 'source-manifest.json') -Force
        Push-Location $RunnerRoot
        try {
            & py.exe -3 -c 'import tools.windows_api_runner.api_runner, tools.windows_api_runner.auto_run_policy, tools.windows_api_runner.worker'
            if ($LASTEXITCODE -ne 0) { throw 'Deployed Runner import failed.' }
            & py.exe -3 -m tools.windows_api_runner.worker --help | Out-Null
            if ($LASTEXITCODE -ne 0) { throw 'Deployed Worker CLI check failed.' }
        } finally { Pop-Location }

        if (-not $task) {
            & (Join-Path $runnerPackage 'bootstrap_worker.ps1') -RunnerRoot $RunnerRoot `
                -ContainerName $ContainerName -ContainerExchange $ExpectedContainerExchange
        } else {
            & (Join-Path $runnerPackage 'start_worker.ps1')
        }
        $deadline = (Get-Date).AddSeconds(30)
        do {
            $installedTask = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
            if ($installedTask -and $installedTask.State.ToString() -eq 'Running') { break }
            Start-Sleep -Milliseconds 500
        } while ((Get-Date) -lt $deadline)
        if (-not $installedTask -or $installedTask.State.ToString() -ne 'Running') {
            $taskInfo = Get-ScheduledTaskInfo -TaskName $taskName -ErrorAction SilentlyContinue
            $taskResult = if ($taskInfo) { $taskInfo.LastTaskResult } else { 'unavailable' }
            throw "Worker task exited or did not start; LastTaskResult=$taskResult; logs=$stateRoot\logs\worker.stdout.log, $stateRoot\logs\worker.stderr.log, $stateRoot\logs\worker.lifecycle.log"
        }
        Start-Sleep -Seconds 2
        $installedTask = Get-ScheduledTask -TaskName $taskName -ErrorAction Stop
        if ($installedTask.State.ToString() -ne 'Running') {
            $taskInfo = Get-ScheduledTaskInfo -TaskName $taskName -ErrorAction SilentlyContinue
            $taskResult = if ($taskInfo) { $taskInfo.LastTaskResult } else { 'unavailable' }
            throw "Worker exited during startup; LastTaskResult=$taskResult; logs=$stateRoot\logs\worker.stdout.log, $stateRoot\logs\worker.stderr.log, $stateRoot\logs\worker.lifecycle.log"
        }
        $installedAction = @($installedTask.Actions)[0]
        $expectedWorking = (Resolve-Path -LiteralPath $RunnerRoot).Path
        if ($installedAction.Execute -ne 'powershell.exe' -or $installedAction.Arguments -ne $expectedArgs -or
            $installedAction.WorkingDirectory -ne $expectedWorking) {
            throw 'Worker Task action changed or does not match the deployed Runner.'
        }
        Assert-TaskPrincipal $installedTask.Principal
        $status = (& (Join-Path $runnerPackage 'status_worker.ps1') 2>&1 | Out-String)
        if ($status -notmatch 'Auto-run enabled: False') { throw 'Worker status did not verify Auto-Run disabled.' }
        Write-Output $status
        if (Test-Path -LiteralPath $policyPath) {
            $postPolicy = Get-Content -Raw -LiteralPath $policyPath | ConvertFrom-Json
            if ($postPolicy.enabled -ne $false) { throw 'Auto-Run policy changed during deployment.' }
        }
    } catch {
        $rollbackTask = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
        if ($rollbackTask -and $rollbackTask.State.ToString() -eq 'Running') {
            Stop-ScheduledTask -TaskName $taskName
            $rollbackDeadline = (Get-Date).AddSeconds(30)
            do {
                $rollbackTask = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
                if (-not $rollbackTask -or $rollbackTask.State.ToString() -ne 'Running') { break }
                Start-Sleep -Milliseconds 500
            } while ((Get-Date) -lt $rollbackDeadline)
            if ($rollbackTask -and $rollbackTask.State.ToString() -eq 'Running') {
                throw 'Rollback stopped: Worker could not be stopped safely; backup retained.'
            }
        }
        if ($packageMoved) {
            if (Test-Path -LiteralPath $runnerPackage) { Remove-Item -LiteralPath $runnerPackage -Recurse -Force }
            Move-Item -LiteralPath $oldPackage -Destination $runnerPackage
        }
        if (-not $task -and $rollbackTask) {
            $registeredAction = @($rollbackTask.Actions)[0]
            if ($registeredAction.Execute -eq 'powershell.exe' -and $registeredAction.Arguments -eq $expectedArgs) {
                Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
            }
        } elseif ($wasRunning) {
            Start-ScheduledTask -TaskName $taskName
        }
        throw
    }
    Write-Output "DEPLOYMENT PASS; backup=$backupRoot"
    Write-Output 'Auto-Run policy was not changed; Credential Manager was not accessed; exchange requests/responses were not touched.'
    Write-Output 'Worker Task is running with Auto-Run disabled; no Credential Manager operation was performed.'
} finally {
    if (Test-Path -LiteralPath $workRoot) { Remove-Item -LiteralPath $workRoot -Recurse -Force }
}
