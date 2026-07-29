param(
  [string]$Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path,
  [string]$WebHost = "127.0.0.1",
  [int]$WebPort = 3000,
  [int]$Jin10Port = 8000,
  [int]$VixPort = 8765
)

$ErrorActionPreference = "Stop"

function Import-DotEnv {
  param([string]$Path)
  if (-not (Test-Path $Path)) { return }
  Get-Content $Path | ForEach-Object {
    $line = $_.Trim()
    if (-not $line -or $line.StartsWith("#")) { return }
    $idx = $line.IndexOf("=")
    if ($idx -lt 1) { return }
    $key = $line.Substring(0, $idx).Trim()
    $value = $line.Substring($idx + 1).Trim().Trim('"').Trim("'")
    [Environment]::SetEnvironmentVariable($key, $value, "Process")
  }
}

function Require-ProductionSecrets {
  $passcode = [Environment]::GetEnvironmentVariable("YSJ_ACCESS_PASSCODE", "Process")
  $secret = [Environment]::GetEnvironmentVariable("YSJ_ACCESS_SECRET", "Process")
  if ([string]::IsNullOrWhiteSpace($passcode) -or $passcode -eq "CHANGE_ME") {
    throw "Set YSJ_ACCESS_PASSCODE in .env before hosting publicly."
  }
  if ([string]::IsNullOrWhiteSpace($secret) -or $secret.StartsWith("CHANGE_ME")) {
    throw "Set YSJ_ACCESS_SECRET in .env before hosting publicly."
  }
}

function Get-EnvOrDefault {
  param(
    [string]$Name,
    [string]$Default
  )
  $value = [Environment]::GetEnvironmentVariable($Name, "Process")
  if ([string]::IsNullOrWhiteSpace($value)) { return $Default }
  return $value
}

function Start-ManagedProcess {
  param(
    [string]$Name,
    [string]$FilePath,
    [string[]]$Arguments,
    [string]$WorkingDirectory,
    [string]$LogPath,
    [string]$RunDir
  )

  while ($true) {
    $timestamp = Get-Date -Format o
    Add-Content -Path $LogPath -Value "[$timestamp] starting $Name"
    $outLog = [System.IO.Path]::ChangeExtension($LogPath, ".out.log")
    $errLog = [System.IO.Path]::ChangeExtension($LogPath, ".err.log")
    $proc = Start-Process -FilePath $FilePath `
      -ArgumentList $Arguments `
      -WorkingDirectory $WorkingDirectory `
      -RedirectStandardOutput $outLog `
      -RedirectStandardError $errLog `
      -NoNewWindow `
      -PassThru
    Set-Content -Path (Join-Path $RunDir "$Name.pid") -Value $proc.Id
    $proc.WaitForExit()
    $timestamp = Get-Date -Format o
    Add-Content -Path $LogPath -Value "[$timestamp] $Name exited code=$($proc.ExitCode); restarting in 5 seconds"
    Start-Sleep -Seconds 5
  }
}

Set-Location $Root
$script:RunDir = Join-Path $Root "run"
$logDir = Join-Path $Root "logs"
New-Item -ItemType Directory -Force -Path $script:RunDir, $logDir | Out-Null

Import-DotEnv (Join-Path $Root ".env")
Require-ProductionSecrets

[Environment]::SetEnvironmentVariable("NODE_ENV", "production", "Process")
if (-not [Environment]::GetEnvironmentVariable("DATABASE_PATH", "Process")) {
  [Environment]::SetEnvironmentVariable("DATABASE_PATH", ".\data\us_dashboard.db", "Process")
}
if (-not [Environment]::GetEnvironmentVariable("CN_VIX_DB", "Process")) {
  [Environment]::SetEnvironmentVariable("CN_VIX_DB", (Join-Path $Root "cn_option_vix\data\live_vix.sqlite"), "Process")
}
[Environment]::SetEnvironmentVariable("DASHBOARD_HOST", "127.0.0.1", "Process")
[Environment]::SetEnvironmentVariable("DASHBOARD_PORT", "$VixPort", "Process")
[Environment]::SetEnvironmentVariable("CN_VIX_LOG_DIR", (Join-Path $logDir "cn_vix_dashboard"), "Process")
[Environment]::SetEnvironmentVariable("PATH", "$Root\cn_option_vix\.venv\Scripts;$Root\jin10_us_dashboard_site\.venv\Scripts;$env:PATH", "Process")

$jin10Python = Join-Path $Root "jin10_us_dashboard_site\.venv\Scripts\python.exe"
$vixPython = Join-Path $Root "cn_option_vix\.venv\Scripts\python.exe"
$npm = (Get-Command npm -ErrorAction Stop).Source
if (-not (Test-Path $jin10Python)) { throw "Missing Jin10 venv. Run setup-windows.ps1 first." }
if (-not (Test-Path $vixPython)) { throw "Missing CN VIX venv. Run setup-windows.ps1 first." }
if (-not (Test-Path (Join-Path $Root ".next"))) {
  throw "Missing Next.js production build. Run setup-windows.ps1 first."
}

Write-Host "Starting YSJ services. Leave this window open, or install the startup task."
Write-Host "Only Cloudflare Tunnel should publish http://127.0.0.1:$WebPort to the internet."

$jobs = @()
$jobs += Start-Job -Name "jin10" -ScriptBlock ${function:Start-ManagedProcess} -ArgumentList @(
  "jin10",
  $jin10Python,
  @("-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "$Jin10Port"),
  (Join-Path $Root "jin10_us_dashboard_site"),
  (Join-Path $logDir "jin10.log"),
  $script:RunDir
)

$jobs += Start-Job -Name "cn_vix_web" -ScriptBlock ${function:Start-ManagedProcess} -ArgumentList @(
  "cn_vix_web",
  $vixPython,
  @("-m", "uvicorn", "cn_option_vix.web.app:app", "--host", "127.0.0.1", "--port", "$VixPort"),
  $Root,
  (Join-Path $logDir "cn_vix_web.log"),
  $script:RunDir
)

if ([Environment]::GetEnvironmentVariable("RQDATA_URI", "Process") -or [Environment]::GetEnvironmentVariable("RQDATAC_URI", "Process")) {
  & $vixPython -m cn_option_vix.pipeline.sync_missing_5m `
    --db ([Environment]::GetEnvironmentVariable("CN_VIX_DB", "Process")) `
    --reserve-mib (Get-EnvOrDefault "CN_VIX_BACKFILL_RESERVE_MIB" "64") `
    --lookback-trading-days (Get-EnvOrDefault "CN_VIX_CATCHUP_LOOKBACK_TRADING_DAYS" "10") `
    --best-effort

  $jobs += Start-Job -Name "cn_vix_collector" -ScriptBlock ${function:Start-ManagedProcess} -ArgumentList @(
    "cn_vix_collector",
    $vixPython,
    @("-m", "cn_option_vix.pipeline.monitor_live_5m", "--db", [Environment]::GetEnvironmentVariable("CN_VIX_DB", "Process")),
    $Root,
    (Join-Path $logDir "cn_vix_collector.log"),
    $script:RunDir
  )
  $jobs += Start-Job -Name "cn_vix_repair" -ScriptBlock ${function:Start-ManagedProcess} -ArgumentList @(
    "cn_vix_repair",
    $vixPython,
    @("-m", "cn_option_vix.pipeline.monitor_repair", "--db", [Environment]::GetEnvironmentVariable("CN_VIX_DB", "Process"), "--reserve-mib", (Get-EnvOrDefault "CN_VIX_BACKFILL_RESERVE_MIB" "64"), "--lookback-trading-days", (Get-EnvOrDefault "CN_VIX_CATCHUP_LOOKBACK_TRADING_DAYS" "10"), "--no-startup"),
    $Root,
    (Join-Path $logDir "cn_vix_repair.log"),
    $script:RunDir
  )
} else {
  Write-Warning "RQDATA_URI is empty. CN VIX will serve existing SQLite data only."
}

$jobs += Start-Job -Name "ysj_web" -ScriptBlock ${function:Start-ManagedProcess} -ArgumentList @(
  "ysj_web",
  $npm,
  @("run", "start", "--", "--hostname", $WebHost, "--port", "$WebPort"),
  $Root,
  (Join-Path $logDir "ysj_web.log"),
  $script:RunDir
)

Wait-Job $jobs
