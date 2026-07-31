param(
  [string]$Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
)

$runDir = Join-Path $Root "run"
foreach ($name in @("ysj_web", "cn_vix_repair", "cn_vix_collector", "cn_vix_web", "jin10")) {
  $pidPath = Join-Path $runDir "$name.pid"
  if (-not (Test-Path $pidPath)) {
    Write-Host "$name: no pid file"
    continue
  }
  $pidValue = Get-Content $pidPath | Select-Object -First 1
  $proc = Get-Process -Id $pidValue -ErrorAction SilentlyContinue
  if ($proc) {
    Stop-Process -Id $pidValue -Force
    Write-Host "$name stopped"
  } else {
    Write-Host "$name was not running"
  }
  Remove-Item $pidPath -Force -ErrorAction SilentlyContinue
}
