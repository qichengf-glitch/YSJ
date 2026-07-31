param(
  [string]$Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
)

$ErrorActionPreference = "Stop"

function Get-PythonCommand {
  $candidates = @(
    @{ File = "py"; Args = @("-3.11") },
    @{ File = "py"; Args = @("-3") },
    @{ File = "python"; Args = @() },
    @{ File = "python3"; Args = @() }
  )

  foreach ($candidate in $candidates) {
    $cmd = Get-Command $candidate.File -ErrorAction SilentlyContinue
    if (-not $cmd) { continue }
    try {
      & $candidate.File @($candidate.Args) -c "import sys; raise SystemExit(0 if (3,10) <= sys.version_info[:2] <= (3,12) else 1)"
      if ($LASTEXITCODE -eq 0) { return $candidate }
    } catch {
      continue
    }
  }
  throw "Python 3.10-3.12 is required. Install Python 3.11 and re-run this script."
}

function Invoke-Python {
  param(
    [hashtable]$PythonCommand,
    [string[]]$Arguments
  )
  & $PythonCommand.File @($PythonCommand.Args) @Arguments
  if ($LASTEXITCODE -ne 0) {
    throw "Python command failed: $($PythonCommand.File) $($PythonCommand.Args -join ' ') $($Arguments -join ' ')"
  }
}

Set-Location $Root

if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
  throw "Node.js is required. Install the current LTS release, then re-run this script."
}
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
  throw "npm is required. Install Node.js LTS, then re-run this script."
}

$python = Get-PythonCommand

Write-Host "[1/5] Installing Next.js dependencies"
npm ci
if ($LASTEXITCODE -ne 0) { throw "npm ci failed." }

Write-Host "[2/5] Creating Jin10 Python environment"
Invoke-Python $python @("-m", "venv", (Join-Path $Root "jin10_us_dashboard_site\.venv"))
& (Join-Path $Root "jin10_us_dashboard_site\.venv\Scripts\python.exe") -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw "Jin10 pip upgrade failed." }
& (Join-Path $Root "jin10_us_dashboard_site\.venv\Scripts\python.exe") -m pip install -r (Join-Path $Root "jin10_us_dashboard_site\requirements.txt")
if ($LASTEXITCODE -ne 0) { throw "Jin10 dependency install failed." }

Write-Host "[3/5] Creating CN VIX Python environment"
Invoke-Python $python @("-m", "venv", (Join-Path $Root "cn_option_vix\.venv"))
& (Join-Path $Root "cn_option_vix\.venv\Scripts\python.exe") -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw "CN VIX pip upgrade failed." }
& (Join-Path $Root "cn_option_vix\.venv\Scripts\python.exe") -m pip install -r (Join-Path $Root "cn_option_vix\requirements.txt")
if ($LASTEXITCODE -ne 0) { throw "CN VIX dependency install failed." }

Write-Host "[4/5] Preparing .env"
$envPath = Join-Path $Root ".env"
if (-not (Test-Path $envPath)) {
  Copy-Item (Join-Path $Root ".env.example") $envPath
  Write-Host "Created .env. Edit it before public hosting."
}

Write-Host "[5/5] Building Next.js production bundle"
npm run build
if ($LASTEXITCODE -ne 0) { throw "Next.js build failed." }

Write-Host "Setup complete. Edit .env, then run deploy\windows\ysj-supervisor.ps1."
