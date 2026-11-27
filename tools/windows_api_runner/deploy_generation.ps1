param(
    [string]$ContainerName = 'codex-sandbox-lab-005',
    [string]$RepositoryPath = '/workspace/SupplyChain_Control_Tower_DataCo',
    [string]$RunnerRoot = 'C:\SupplyChainCopilot\runner'
)
$ErrorActionPreference = 'Stop'

# Generation-only deployment. Count Worker files, Task, state, policy, and
# exchange are read-only throughout this operation.
function Invoke-DockerChecked {
    param([Parameter(Mandatory=$true)][string[]]$DockerArgs)
    $output = & docker.exe @DockerArgs 2>&1
    if ($LASTEXITCODE -ne 0) { throw "Docker command failed: docker $($DockerArgs -join ' ')" }
    return $output
}

if ($PSVersionTable.PSVersion.Major -lt 5) { throw 'Windows PowerShell 5.1 or later is required.' }
if (-not (Get-Command docker.exe -ErrorAction SilentlyContinue)) { throw 'Docker CLI is required.' }
if (-not (Get-Command py.exe -ErrorAction SilentlyContinue)) { throw 'Python launcher is required.' }
$generationDependency = (& py.exe -3 -c 'import cryptography; print(cryptography.__version__)' 2>$null | Out-String).Trim()
if ($LASTEXITCODE -ne 0 -or $generationDependency -ne '46.0.7') {
    throw 'Generation dependency cryptography==46.0.7 is required before deployment.'
}
if ((Invoke-DockerChecked @('inspect','--format','{{.State.Running}}',$ContainerName) | Out-String).Trim() -ne 'true') {
    throw 'Existing Container is not running.'
}
Invoke-DockerChecked @('exec',$ContainerName,'test','-d',$RepositoryPath) | Out-Null
$sourceRoot = "$RepositoryPath/tools/windows_api_runner"
Invoke-DockerChecked @('exec',$ContainerName,'test','-f',"$sourceRoot/source-manifest.json") | Out-Null
$runnerPackage = Join-Path $RunnerRoot 'tools\windows_api_runner'
if (-not (Test-Path -LiteralPath $runnerPackage -PathType Container)) { throw 'Installed Runner package is missing.' }
$policyPath = Join-Path $env:LOCALAPPDATA 'SupplyChainCopilot\auto_run_policy.json'
if (Test-Path -LiteralPath $policyPath) {
    $policy = Get-Content -Raw -LiteralPath $policyPath | ConvertFrom-Json
    if ($policy.enabled -ne $false) { throw 'Auto-Run must remain disabled.' }
}

$generationFiles = @('external_issuer.py','generation_authorization.py','generation_host.py',
    'generation_key_setup.py','generation_owner.py','generation_permit.py',
    'requirements-generation.txt','deploy_generation.ps1')
$job = [guid]::NewGuid().ToString('N')
$stage = Join-Path $env:TEMP "P5GenerationStage_$job"
$backup = Join-Path $env:LOCALAPPDATA "SupplyChainCopilot\backups\generation_$job"
New-Item -ItemType Directory -Path $stage,$backup -Force | Out-Null
$manifestPath = Join-Path $stage 'source-manifest.json'
$created = New-Object System.Collections.ArrayList
$replaced = New-Object System.Collections.ArrayList
$manifestChanged = $false
try {
    Invoke-DockerChecked @('cp',"${ContainerName}:${sourceRoot}/source-manifest.json",$manifestPath) | Out-Null
    $sourceHash = (Invoke-DockerChecked @('exec',$ContainerName,'sha256sum',"$sourceRoot/source-manifest.json") | Out-String).Trim().Split(' ')[0].ToLowerInvariant()
    if ($sourceHash -notmatch '^[0-9a-f]{64}$' -or
        (Get-FileHash -Algorithm SHA256 -LiteralPath $manifestPath).Hash.ToLowerInvariant() -ne $sourceHash) {
        throw 'Source manifest transfer digest mismatch.'
    }
    $manifest = Get-Content -Raw -LiteralPath $manifestPath | ConvertFrom-Json
    if ($manifest.schema_version -ne 1) { throw 'Unsupported source manifest.' }
    $entries = @($manifest.files)
    $existingManifest = Join-Path $runnerPackage 'source-manifest.json'
    $previousHashes = @{}
    if (Test-Path -LiteralPath $existingManifest -PathType Leaf) {
        $previousManifest = Get-Content -Raw -LiteralPath $existingManifest | ConvertFrom-Json
        if ($previousManifest.schema_version -ne 1) { throw 'Installed source manifest is invalid.' }
        foreach ($oldEntry in @($previousManifest.files)) {
            $oldPath = [string]$oldEntry.path
            if ([string]::IsNullOrWhiteSpace($oldPath) -or
                $oldPath -match '(^/|(^|/)\.\.(\/|$)|\\|:)' -or
                $previousHashes.ContainsKey($oldPath) -or
                $oldEntry.sha256 -notmatch '^[0-9a-f]{64}$') {
                throw 'Installed source manifest is unsafe or duplicated.'
            }
            $previousHashes[$oldPath] = $oldEntry.sha256
        }
    }
    $seen = @{}
    foreach ($entry in $entries) {
        $relative = [string]$entry.path
        if ([string]::IsNullOrWhiteSpace($relative) -or
            $relative -match '(^/|(^|/)\.\.(\/|$)|\\|:)' -or
            $seen.ContainsKey($relative) -or $entry.sha256 -notmatch '^[0-9a-f]{64}$') {
            throw 'Unsafe or duplicate source manifest entry.'
        }
        $seen[$relative] = $entry.sha256
        $installed = Join-Path $runnerPackage ($relative -replace '/', '\')
        if ($generationFiles -contains $relative) {
            if (Test-Path -LiteralPath $installed -PathType Leaf) {
                $installedHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $installed).Hash.ToLowerInvariant()
                if ($installedHash -ne $entry.sha256 -and
                    (-not $previousHashes.ContainsKey($relative) -or
                     $installedHash -ne $previousHashes[$relative])) {
                    throw "Existing Generation file differs; no overwrite: $relative"
                }
            }
        } elseif ($relative -ne 'README.md') {
            if (-not (Test-Path -LiteralPath $installed -PathType Leaf) -or
                (Get-FileHash -Algorithm SHA256 -LiteralPath $installed).Hash.ToLowerInvariant() -ne $entry.sha256) {
                throw "Installed Count Runner file differs; no deployment: $relative"
            }
        }
    }
    foreach ($relative in $generationFiles) {
        if (-not $seen.ContainsKey($relative)) { throw "Generation manifest entry missing: $relative" }
        $staged = Join-Path $stage $relative
        Invoke-DockerChecked @('cp',"${ContainerName}:${sourceRoot}/$relative",$staged) | Out-Null
        if ((Get-FileHash -Algorithm SHA256 -LiteralPath $staged).Hash.ToLowerInvariant() -ne $seen[$relative]) {
            throw "Generation source digest mismatch: $relative"
        }
    }
    if ((Get-FileHash -Algorithm SHA256 -LiteralPath $PSCommandPath).Hash.ToLowerInvariant() -ne $seen['deploy_generation.ps1']) {
        throw 'Generation deployer does not match the source manifest.'
    }
    if (Test-Path -LiteralPath $existingManifest -PathType Leaf) {
        Copy-Item -LiteralPath $existingManifest -Destination (Join-Path $backup 'source-manifest.json')
    }
    # Stage and verify every Generation file before changing the installed package.
    foreach ($relative in $generationFiles) {
        $installed = Join-Path $runnerPackage $relative
        if (-not (Test-Path -LiteralPath $installed -PathType Leaf)) {
            [System.IO.File]::Copy((Join-Path $stage $relative), $installed, $false)
            [void]$created.Add($installed)
        } elseif ((Get-FileHash -Algorithm SHA256 -LiteralPath $installed).Hash.ToLowerInvariant() -ne $seen[$relative]) {
            $oldCopy = Join-Path $backup $relative
            Copy-Item -LiteralPath $installed -Destination $oldCopy
            [void]$replaced.Add([pscustomobject]@{ Installed = $installed; Backup = $oldCopy })
            Copy-Item -LiteralPath (Join-Path $stage $relative) -Destination $installed -Force
        }
        if ((Get-FileHash -Algorithm SHA256 -LiteralPath $installed).Hash.ToLowerInvariant() -ne $seen[$relative]) {
            throw "Installed Generation digest mismatch: $relative"
        }
    }
    $manifestChanged = $true
    Copy-Item -LiteralPath $manifestPath -Destination $existingManifest -Force
    if ((Get-FileHash -Algorithm SHA256 -LiteralPath $existingManifest).Hash.ToLowerInvariant() -ne $sourceHash) {
        throw 'Installed source manifest digest mismatch.'
    }
    Push-Location $RunnerRoot
    try {
        & py.exe -3 -m tools.windows_api_runner.generation_host --help | Out-Null
        if ($LASTEXITCODE -ne 0) { throw 'Generation CLI import/help failed.' }
    } finally { Pop-Location }
    Write-Output "GENERATION_DEPLOYMENT_PASS files=$($generationFiles.Count) backup=$backup"
    Write-Output 'Count Worker files and Task were not changed; Auto-Run and Runner SQLite were not touched.'
} catch {
    if ($manifestChanged) {
        $previous = Join-Path $backup 'source-manifest.json'
        if (Test-Path -LiteralPath $previous) { Copy-Item -LiteralPath $previous -Destination $existingManifest -Force }
        elseif (Test-Path -LiteralPath $existingManifest) { Remove-Item -LiteralPath $existingManifest -Force }
    }
    foreach ($path in $created) {
        if (Test-Path -LiteralPath $path -PathType Leaf) { Remove-Item -LiteralPath $path -Force }
    }
    foreach ($item in $replaced) {
        Copy-Item -LiteralPath $item.Backup -Destination $item.Installed -Force
    }
    throw
}
