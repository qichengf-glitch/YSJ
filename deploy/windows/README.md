# YSJLab Windows 11 self-hosting runbook

This runbook hosts YSJLab from one Windows 11 Pro PC while keeping the PC off the public Internet. Public traffic should enter through Cloudflare Tunnel and reach only `http://127.0.0.1:3000`.

## Target layout

```text
Public visitors
  -> Cloudflare DNS / HTTPS / WAF
  -> Cloudflare Tunnel outbound connection
  -> Windows PC localhost:3000 Next.js
       -> localhost:8000 Jin10 FastAPI
       -> localhost:8765 CN VIX FastAPI
```

Do not forward router ports 3000, 8000, 8765, 80, or 443 to the PC.

## 1. Prepare Windows

Install:

- Git for Windows
- Node.js LTS
- Python 3.11, with "Add python.exe to PATH" enabled
- cloudflared

Create a folder such as:

```powershell
C:\YSJ\YSJ
```

Clone or copy this repository into that folder.

## 2. Install app dependencies

Open PowerShell in the repository folder:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
.\deploy\windows\setup-windows.ps1
```

Edit `.env` before public hosting. Required production values:

```text
YSJ_ACCESS_PASSCODE=<private website passcode>
YSJ_ACCESS_SECRET=<long random secret>
JIN10_SECRET_KEY=<Jin10 API key>
RQDATA_URI=<RiceQuant URI>
```

For Windows self-hosting, keep backend URLs local:

```text
MARKET_RADAR_BACKEND_URL=http://127.0.0.1:8000
CN_VIX_BACKEND_URL=http://127.0.0.1:8765
VIX_DASHBOARD_PUBLIC_URL=/api/cn-option-vix-dashboard/index.html
NEXT_PUBLIC_VIX_DASHBOARD_URL=
```

## 3. Start locally

```powershell
.\deploy\windows\ysj-supervisor.ps1
```

In another PowerShell window:

```powershell
.\deploy\windows\status-windows.ps1
```

Open:

```text
http://127.0.0.1:3000
```

## 4. Lock down inbound access

Run PowerShell as Administrator:

```powershell
.\deploy\windows\firewall-localhost-only.ps1
```

This blocks direct inbound access to ports 3000, 8000, and 8765. Cloudflare Tunnel still works because it connects outbound and talks to localhost.

## 5. Publish through Cloudflare Tunnel

Cloudflare's documented Windows service flow is:

```cmd
cloudflared.exe service install <TUNNEL_TOKEN>
```

Use the Cloudflare dashboard to create a tunnel and public hostname. Route the hostname to:

```text
http://127.0.0.1:3000
```

If using a locally managed tunnel, adapt `cloudflared-config.yml.example` and validate:

```cmd
C:\Cloudflared\bin\cloudflared.exe tunnel ingress validate
```

Then run Cloudflare's service install/start steps as Administrator.

## 6. Start after login

Run PowerShell as Administrator:

```powershell
.\deploy\windows\install-startup-task.ps1
```

Cloudflare Tunnel should also be installed as a Windows service.

This task starts after the configured Windows user logs in. For unattended startup before login, use a dedicated Windows service wrapper or a Task Scheduler entry configured with stored service-account credentials.

## 7. Backups

Run manually:

```powershell
.\deploy\windows\backup-windows.ps1
```

Recommended: create a daily Task Scheduler job for this script and sync the resulting `backups` folder to an external drive or private cloud storage.

## Security baseline

- Keep Windows activated and patched.
- Use a dedicated non-admin Windows account for routine operation.
- Do not expose backend ports or router port forwarding.
- Do not store `.env` in GitHub or shared folders.
- Use a long random `YSJ_ACCESS_SECRET`.
- Use Cloudflare WAF/rate limiting for the public hostname.
- Keep RDP disabled from the Internet. If remote desktop is required, protect it with a VPN or Cloudflare Zero Trust, not router port forwarding.
