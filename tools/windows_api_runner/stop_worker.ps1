$ErrorActionPreference = 'Stop'
Stop-ScheduledTask -TaskName 'SupplyChainCopilotLocalRunner'
Write-Output 'Windows Runner Worker stop requested.'
