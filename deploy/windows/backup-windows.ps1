param(
  [string]$Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path,
  [string]$BackupRoot = (Join-Path $Root "backups")
)

$ErrorActionPreference = "Stop"
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$target = Join-Path $BackupRoot $stamp
New-Item -ItemType Directory -Force -Path $target | Out-Null

$items = @(
  @{ Source = Join-Path $Root ".env"; Name = "env.txt" },
  @{ Source = Join-Path $Root "jin10_us_dashboard_site\data\us_dashboard.db"; Name = "us_dashboard.db" },
  @{ Source = Join-Path $Root "cn_option_vix\data\live_vix.sqlite"; Name = "live_vix.sqlite" }
)

foreach ($item in $items) {
  if (Test-Path $item.Source) {
    Copy-Item $item.Source (Join-Path $target $item.Name) -Force
  }
}

Compress-Archive -Path (Join-Path $target "*") -DestinationPath "$target.zip" -Force
Write-Host "Backup created: $target.zip"
