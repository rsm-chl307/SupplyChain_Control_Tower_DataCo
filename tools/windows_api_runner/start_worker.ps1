$ErrorActionPreference = 'Stop'
Start-ScheduledTask -TaskName 'SupplyChainCopilotLocalRunner'
Write-Output 'Windows Runner Worker start requested.'
