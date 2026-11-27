# Read-only native Windows trial preflight. Run from the repository root.
param([string]$Python = "py")
$ErrorActionPreference = "Stop"
if ($env:OS -ne "Windows_NT") { throw "Native Windows is required" }
if (-not (Test-Path "tools/windows_api_runner/api_runner.py")) { throw "Run from repository root" }
$stamp = Get-Date -Format "yyyyMMddTHHmmss"
$out = Join-Path $env:TEMP "supplychain-trial-preflight-$stamp.txt"
$version = & $Python -3.12 -c "import sys; print(sys.version); print(sys.executable)" 2>&1
if ($LASTEXITCODE -ne 0) { throw "Python 3.12 preflight failed" }
$git = git rev-parse HEAD
if ($LASTEXITCODE -ne 0) { throw "Git commit preflight failed" }
$status = git status --short
if ($LASTEXITCODE -ne 0) { throw "Git worktree preflight failed" }
$budget = Join-Path $env:LOCALAPPDATA "SupplyChainCopilot/trial_budget.sqlite3"
$budgetState = if (Test-Path $budget) { "PRESENT (contents not displayed)" } else { "MISSING; real dispatch must remain blocked" }
$sqlite = & $Python -3.12 -c "import sqlite3; print('SQLite:', sqlite3.sqlite_version); print('Thread safety:', sqlite3.threadsafety)" 2>&1
if ($LASTEXITCODE -ne 0) { throw "SQLite preflight failed" }
$integrity = if (Test-Path $budget) {
    $result = & $Python -3.12 -c "import sqlite3,sys,pathlib; c=sqlite3.connect(pathlib.Path(sys.argv[1]).as_uri()+'?mode=ro',uri=True); result=c.execute('PRAGMA integrity_check').fetchone()[0]; print('Trial DB integrity:',result); c.close(); sys.exit(0 if result=='ok' else 1)" $budget 2>&1
    if ($LASTEXITCODE -ne 0) { throw "Trial DB integrity preflight failed" }
    $result
} else { "SKIPPED (no budget DB)" }
$lock = & $Python -3.12 -c "from tools.windows_api_runner.api_runner import REAL_TOKEN_COUNT_DISPATCH_LOCKED; from tools.windows_api_runner.generation_host import REAL_GENERATION_DISPATCH_LOCKED; print('Count locked:', REAL_TOKEN_COUNT_DISPATCH_LOCKED); print('Generation locked:', REAL_GENERATION_DISPATCH_LOCKED)" 2>&1
if ($LASTEXITCODE -ne 0) { throw "Dispatch lock preflight failed" }
@(
    "Windows native P5 preflight: $stamp",
    "Repository: $(Get-Location)",
    "Commit: $git",
    "Python 3.12:", $version,
    "Budget store: $budgetState",
    "SQLite:", $sqlite, $integrity,
    "Locks:", $lock,
    "Working tree (paths only):", $status
) | Out-File -FilePath $out -Encoding utf8
Write-Output "Preflight saved: $out"
Write-Output "Review output for private paths before sharing. No credential values were read."
