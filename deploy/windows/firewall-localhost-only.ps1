$ErrorActionPreference = "Stop"

Write-Host "Creating conservative inbound firewall rules."
Write-Host "This keeps YSJ app ports private. Cloudflare Tunnel reaches them through localhost."

foreach ($port in @(3000, 8000, 8765)) {
  $ruleName = "YSJLab block direct inbound TCP $port"
  if (Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue) {
    Remove-NetFirewallRule -DisplayName $ruleName
  }
  New-NetFirewallRule `
    -DisplayName $ruleName `
    -Direction Inbound `
    -Action Block `
    -Protocol TCP `
    -LocalPort $port `
    -Profile Any | Out-Null
}

Write-Host "Done. Do not expose ports 3000, 8000, or 8765 on the router."
