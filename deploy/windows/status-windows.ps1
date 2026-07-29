param(
  [string]$Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
)

$ErrorActionPreference = "Continue"
$runDir = Join-Path $Root "run"

foreach ($name in @("jin10", "cn_vix_web", "cn_vix_collector", "cn_vix_repair", "ysj_web")) {
  $pidPath = Join-Path $runDir "$name.pid"
  if (Test-Path $pidPath) {
    $pidValue = (Get-Content $pidPath -ErrorAction SilentlyContinue | Select-Object -First 1)
    $proc = Get-Process -Id $pidValue -ErrorAction SilentlyContinue
    if ($proc) {
      Write-Host "$name: RUNNING pid=$pidValue"
    } else {
      Write-Host "$name: STOPPED stale_pid=$pidValue"
    }
  } else {
    Write-Host "$name: NO_PID"
  }
}

Write-Host ""
Write-Host "Jin10 health:"
try { Invoke-RestMethod -TimeoutSec 3 http://127.0.0.1:8000/api/health | ConvertTo-Json -Depth 6 } catch { Write-Host $_.Exception.Message }
Write-Host ""
Write-Host "CN VIX health:"
try { Invoke-RestMethod -TimeoutSec 3 http://127.0.0.1:8765/healthz | ConvertTo-Json -Depth 6 } catch { Write-Host $_.Exception.Message }
Write-Host ""
Write-Host "Next.js:"
try { (Invoke-WebRequest -UseBasicParsing -TimeoutSec 3 http://127.0.0.1:3000/).StatusCode } catch { Write-Host $_.Exception.Message }
