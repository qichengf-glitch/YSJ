# YSJLab Website Content, Feature, and API Log

Last updated: 2026-07-15

This document explains the current YSJLab website structure, public pages, private-access pages, API routes, external dependencies, and deployment/runtime configuration.

## 1. Project Overview

YSJLab is a Next.js 14 App Router website for finance research, strategy, market data, and private internal dashboards.

Core stack:

- Next.js 14 App Router
- React 18
- TypeScript
- Tailwind CSS
- `lucide-react` icons
- Client-side bilingual toggle: English / Chinese

Primary design direction:

- Public site: clean white finance research platform.
- Private area: access-controlled internal dashboard entry.
- Internal dashboards: live monitors, market radar, daily summary, and China option VIX monitor.

## 2. Main Navigation

Implemented in `components/Navbar.tsx`.

Top navigation currently exposes:

- `Home` -> `/`
- `Research` -> `/research`
- `Strategy` -> `/strategy`
- `Prediction Markets` -> `/prediction-markets`
- `Private Access` -> `/access`
- Language toggle -> English / Chinese

On mobile, public links collapse visually and the private access button shortens to `Access`.

Daily Summary, Market Radar, and live monitoring tools are intentionally not listed in public nav. They live behind Private Access.

## 3. Public Pages

### `/`

File: `app/page.tsx`

Purpose:

- Main YSJLab landing page.
- Presents YSJLab as an independent, data-driven finance research platform.
- Provides public entry points into Research, Strategy, Ongoing Thesis, Prediction Markets, and Private Access.

Main sections:

- Hero: "Smarter Research. Better Decisions."
- CTA buttons:
  - Explore All Sections -> `#sections`
  - Our Approach -> `#approach`
  - Private Access -> `/access`
- Value cards:
  - Independent
  - Data-Driven
  - Global
- Public platform cards via `components/FocusCards.tsx`
- Metrics strip
- Private Access CTA panel
- Footer with contact link and `contact@ysjlab.com`

### `/research`

File: `app/research/page.tsx`

Purpose:

- Research hub with three public research routes.

Cards:

- Theoretical Research -> `/research/theoretical-research`
- Ongoing Thesis -> `/research/ongoing-thesis`
- General Market Data & Our Picks -> `/research/market-data`

### `/research/theoretical-research`

File: `app/research/theoretical-research/page.tsx`

Purpose:

- Public index for conceptual and academic-style research.
- Reads `researchPapers` from `data/research.ts`.
- Links to individual article pages under `/research/[slug]`.

Content themes:

- Market microstructure
- Liquidity regimes
- Risk premia
- Cross-asset interactions

### `/research/[slug]`

File: `app/research/[slug]/page.tsx`

Purpose:

- Dynamic research article page.
- Uses paper metadata/content from `data/research.ts`.
- Public route.

### `/research/ongoing-thesis`

File: `app/research/ongoing-thesis/page.tsx`

Purpose:

- Community-style thesis feed.
- Current implementation uses mock thesis posts in the page file.

Features:

- Tabs: For You, Latest, Following
- Sort options: New, Hot, Top windows, Controversial
- Tag filter
- Ticker search
- Composer UI
- Load more button
- Thesis cards with author, tags, tickers, sentiment, score, and comments count

Related components:

- `components/ThesisFilterBar.tsx`
- `components/ThesisComposer.tsx`
- `components/ThesisPostCard.tsx`
- `components/CommentThread.tsx`

### `/research/ongoing-thesis/[id]`

File: `app/research/ongoing-thesis/[id]/page.tsx`

Purpose:

- Dynamic detail page for an ongoing thesis post.
- Public route.

### `/research/market-data`

File: `app/research/market-data/page.tsx`

Purpose:

- Public market overview inside the Research area.
- Shows world market data and "Our Picks".

Features:

- Market Data card
- Our Picks card
- Loaded time indicator

Data/API usage:

- `MarketQuoteTable` calls `/api/markets/quotes`
- Sparkline or related market components can call `/api/markets/spark`

### `/strategy`

File: `app/strategy/page.tsx`

Purpose:

- Public overview of YSJLab strategy categories.

Strategy cards:

- US Options Fundamental-Biased Strategy
- US Options Technical-Biased Strategy
- US Options Multi-Strategy

Current status:

- NAV values are placeholders.
- Holdings are marked "Coming Soon".

### `/prediction-markets`

File: `app/prediction-markets/page.tsx`

Purpose:

- Public placeholder page for prediction markets.

Current status:

- Coming soon.
- Text describes future probabilistic forecasting work.

### `/contact`

File: `app/contact/page.tsx`

Purpose:

- Public contact page.

Features:

- Name, email, subject, and message fields
- Client-side validation
- Generates a `mailto:contact@ysjlab.com` draft
- Does not send data to a backend server

### `/market`

File: `app/(dashboard)/market/page.tsx`

Purpose:

- Markets overview dashboard route.
- Similar to `/research/market-data`.

Features:

- Market data table
- Our Picks panel

Current note:

- This route is grouped under `app/(dashboard)` and is public unless separately protected later.

### `/easy-access`

File: `app/easy-access/page.tsx`

Purpose:

- Redirects to `/market-radar`.

Current behavior:

- Because `/market-radar` is protected, unauthenticated users are redirected to `/access`.

## 4. Private Access System

### `/access`

Files:

- `app/access/page.tsx`
- `app/access/AccessPortal.tsx`
- `lib/access.ts`
- `app/api/access/login/route.ts`
- `app/api/access/logout/route.ts`

Purpose:

- Gate internal dashboards behind a simple passcode login.

Default local passcode:

```text
0000
```

Cookie:

```text
ysj_access
```

Session length:

```text
12 hours
```

Security model:

- Login creates an HMAC-signed token.
- Token is stored in an HTTP-only cookie.
- Cookie uses `sameSite: lax`.
- Cookie is `secure` in production.
- Token is verified server-side for protected pages.

Private Access cards:

- CN Option VIX Monitor -> `/cn-option-vix`
- Market Radar -> `/market-radar`
- Daily Summary -> `/daily-summary`

Important:

- This is a lightweight access gate, not a full user account system.
- For production with multiple users, consider replacing it with proper auth if user-level permissions or audit trails are needed.

## 5. Protected Internal Pages

### `/cn-option-vix`

Files:

- `app/cn-option-vix/page.tsx`
- `app/cn-option-vix/CnOptionVixPage.tsx`

Protection:

- Server checks `ysj_access` cookie.
- If invalid or missing, redirects to `/access`.

Purpose:

- Internal page for the China Option VIX Monitor.
- Wraps and documents the external/local `cn_option_vix` FastAPI dashboard.

Default iframe target:

```text
http://127.0.0.1:8765
```

Can be overridden with:

```text
NEXT_PUBLIC_VIX_DASHBOARD_URL
```

Content shown:

- CN Option VIX Monitor overview
- Open live dashboard button
- Embedded iframe
- Coverage groups
- Imported script explanations
- Local run workflow
- Data model explanation

Explained source scripts:

- `history.py`: pulls historical RiceQuant option contracts, settlements, and dominant series.
- `vix_history.py`: computes historical 30-day model-free VIX and group aggregates.
- `5day5min.py`: pulls recent five-trading-day 5-minute option data.
- `vix dashboard.py`: generates a standalone VIX dashboard HTML.

Related external project:

```text
/Users/qichengfu/Desktop/cn_option_vix
```

The `cn_option_vix` web app exposes its own API:

- `GET /api/config`
- `GET /api/latest`
- `GET /api/series?resolution=5m`
- `GET /api/series?resolution=halfday`
- `GET /api/averages`
- `GET /api/status`
- `GET /api/quality`
- `GET /healthz`

Those endpoints belong to the FastAPI service on port `8765`, not the YSJ Next.js app.

### `/market-radar`

File: `app/market-radar/page.tsx`

Protection:

- Server checks `ysj_access` cookie.
- If invalid or missing, redirects to `/access`.

Purpose:

- Internal US event intelligence dashboard.
- Embeds the static dashboard:

```text
public/market-radar/index.html
```

Internal frontend assets:

- `public/market-radar/index.html`
- `public/market-radar/app.js`
- `public/market-radar/styles.css`

Backend proxy:

- Next route `/api/market-radar/[...path]`
- Proxies to `MARKET_RADAR_BACKEND_URL`
- Default backend:

```text
http://127.0.0.1:8000
```

### `/daily-summary`

Files:

- `app/daily-summary/page.tsx`
- `app/daily-summary/DailySummaryFrame.tsx`

Protection:

- Server checks `ysj_access` cookie.
- If invalid or missing, redirects to `/access`.

Purpose:

- Internal daily cross-asset market summary.
- Uses an iframe that switches based on current language.

English iframe:

```text
public/daily-summary/latest-en.html
```

Chinese iframe:

```text
public/daily-summary/latest-zh.html
```

Fallback/static file:

```text
public/daily-summary/latest.html
```

## 6. Next.js API Routes

### `POST /api/access/login`

File: `app/api/access/login/route.ts`

Purpose:

- Validate Private Access passcode.
- Set signed `ysj_access` cookie.

Request body:

```json
{
  "passcode": "0000"
}
```

Success response:

```json
{
  "ok": true
}
```

Failure response:

```json
{
  "ok": false,
  "message": "Invalid access code."
}
```

Failure status:

```text
401
```

### `POST /api/access/logout`

File: `app/api/access/logout/route.ts`

Purpose:

- Clear the `ysj_access` cookie.

Success response:

```json
{
  "ok": true
}
```

### `GET /api/markets/quotes`

File: `app/api/markets/quotes/route.ts`

Purpose:

- Fetch world market quote snapshots from Yahoo Finance.
- Used by `MarketQuoteTable`.

External source:

```text
https://query1.finance.yahoo.com/v7/finance/quote
```

Regions:

- Americas: `^GSPC`, `^IXIC`, `^DJI`, `^RUT`, `^VIX`, `DX-Y.NYB`
- Europe: `^GDAXI`, `^FTSE`, `^FCHI`, `^STOXX50E`
- Asia: `^N225`, `^HSI`, `^KS11`, `000001.SS`, `^AXJO`

Caching:

- In-memory cache: 60 seconds
- Response header: `Cache-Control: public, max-age=30`
- On fetch failure, returns static mock data so local development keeps working.

Response shape:

```ts
{
  updatedAt: number;
  groups: {
    region: string;
    items: {
      symbol: string;
      name: string;
      price: number;
      change: number;
      changePct: number;
    }[];
  }[];
}
```

### `GET /api/markets/spark?symbols=...`

File: `app/api/markets/spark/route.ts`

Purpose:

- Fetch 1-day, 5-minute close series for requested Yahoo Finance symbols.
- Used for small sparkline charts.

Query parameter:

```text
symbols=^GSPC,^IXIC,^DJI
```

External source:

```text
https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=1d&interval=5m&includePrePost=false
```

Caching:

- In-memory cache: 5 minutes
- Max points per symbol: 40
- Fetch concurrency: 4 symbols at a time

Missing symbols response:

```json
{
  "error": "Missing symbols"
}
```

Missing symbols status:

```text
400
```

Success response shape:

```ts
{
  updatedAt: number;
  series: Record<string, number[]>;
}
```

### `/api/market-radar/[...path]`

File: `app/api/market-radar/[...path]/route.ts`

Supported methods:

- `GET`
- `POST`
- `PUT`
- `PATCH`
- `DELETE`
- `OPTIONS`

Purpose:

- Proxy Market Radar frontend calls to the external/local Market Radar backend.

Target backend:

```text
MARKET_RADAR_BACKEND_URL || http://127.0.0.1:8000
```

Example:

```text
GET /api/market-radar/events?date=...
```

Proxies to:

```text
http://127.0.0.1:8000/api/events?date=...
```

Unavailable backend response:

```json
{
  "detail": "Market Radar backend is not reachable. Start the FastAPI service in jin10_us_dashboard_site_v6_5, or set MARKET_RADAR_BACKEND_URL.",
  "error": "..."
}
```

Unavailable backend status:

```text
502
```

## 7. External Services and Data Sources

### Yahoo Finance

Used by:

- `/api/markets/quotes`
- `/api/markets/spark`

Purpose:

- Public market quote and intraday chart data.

Runtime note:

- If network calls fail, quotes route falls back to mock data.

### RiceQuant / RQData

Used by:

- `cn_option_vix` project
- metal option VIX scripts from Desktop

Environment variable:

```text
RQDATA_URI
```

Important:

- The YSJ Next.js app does not directly call RQData.
- RQData is used by separate Python collectors/scripts.
- Do not commit the real `RQDATA_URI` value to git or public docs.

### CN Option VIX FastAPI Service

Default URL:

```text
http://127.0.0.1:8765
```

YSJ env override:

```text
NEXT_PUBLIC_VIX_DASHBOARD_URL
```

Run command:

```bash
cd /Users/qichengfu/Desktop/YSJ
bash cn_option_vix/scripts/run_live_dashboard.sh
```

Render deployment:

```text
Service type: Web Service
Runtime: Python 3
Root Directory: leave blank
Build Command: pip install -r cn_option_vix/requirements.txt
Start Command: bash cn_option_vix/scripts/run_render_dashboard.sh
Disk Mount Path: /var/data
```

Render environment:

```text
RQDATA_URI=<RiceQuant URI>
CN_VIX_DB=/var/data/live_vix.sqlite
```

### Market Radar Backend

Default URL:

```text
http://127.0.0.1:8000
```

YSJ env override:

```text
MARKET_RADAR_BACKEND_URL
```

## 8. Environment Variables

### YSJ Next.js App

```text
YSJ_ACCESS_PASSCODE
```

Overrides the Private Access passcode. Default local value is `0000`.

```text
YSJ_ACCESS_SECRET
```

Secret used to sign access cookies. If omitted, `YSJ_ACCESS_PASSCODE` is used as a fallback; otherwise a local default is used.

```text
NEXT_PUBLIC_VIX_DASHBOARD_URL
```

Public browser-side URL for the CN Option VIX dashboard iframe. Default is `http://127.0.0.1:8765`.

```text
MARKET_RADAR_BACKEND_URL
```

Server-side backend URL used by `/api/market-radar/[...path]`. Default is `http://127.0.0.1:8000`.

### Python Data Services

```text
RQDATA_URI
```

RiceQuant API connection string. Required by RQData-based Python collectors.

## 9. Static Assets

Public landing and card illustrations:

- `public/assets/hero-ysjlab-team.png`
- `public/assets/research-icon.png`
- `public/assets/strategy-icon.png`
- `public/assets/ongoing-thesis-icon.png`
- `public/assets/prediction-markets-icon.png`
- `public/assets/private-dashboard-icon.png`
- `public/assets/private-radar-icon.png`

Daily Summary HTML:

- `public/daily-summary/latest-en.html`
- `public/daily-summary/latest-zh.html`
- `public/daily-summary/latest.html`

Market Radar static frontend:

- `public/market-radar/index.html`
- `public/market-radar/app.js`
- `public/market-radar/styles.css`

Research PDFs:

- `public/papers/*.pdf`

Legacy hero media:

- `public/ysj-hero.html`
- `public/ysj-hero.mp4`

## 10. Local Development

Install:

```bash
npm install
```

Run:

```bash
npm run dev -- -p 3000
```

Build:

```bash
npm run build
```

Start production build:

```bash
npm run start
```

If port `3000` is unavailable locally, use another port:

```bash
npm run dev -- -p 3020
```

## 11. Deployment Notes

For Render or another hosting provider:

Required build command:

```bash
npm install && npm run build
```

Start command:

```bash
npm run start
```

Important environment variables to set:

```text
YSJ_ACCESS_PASSCODE=0000
YSJ_ACCESS_SECRET=<strong random secret>
NEXT_PUBLIC_VIX_DASHBOARD_URL=<deployed CN VIX dashboard URL>
MARKET_RADAR_BACKEND_URL=<deployed Market Radar backend URL>
```

Do not place `RQDATA_URI` in the YSJ Next.js app unless the Next app itself starts calling RQData. Keep RQData credentials in the Python collector/backend service environment.

## 12. Current Functional Boundaries

Public:

- Home
- Research hub
- Theoretical research
- Ongoing thesis
- Market data & our picks
- Strategy
- Prediction markets placeholder
- Contact
- `/market` overview

Private:

- `/access`
- `/cn-option-vix`
- `/market-radar`
- `/daily-summary`

Backend/API:

- Private Access login/logout
- Yahoo market quote proxy/fetcher
- Yahoo sparkline fetcher
- Market Radar backend proxy

External services:

- CN Option VIX FastAPI service
- Market Radar backend
- RiceQuant Python collectors
- Yahoo Finance public quote/chart endpoints

## 13. Known Follow-Ups

- Replace mock thesis data with a persistent backend or CMS if Ongoing Thesis becomes real user content.
- Replace placeholder strategy NAV/holdings with actual strategy data.
- Replace lightweight passcode access with account-based authentication if audit trails or per-user access are needed.
- Deploy CN Option VIX backend separately and set `NEXT_PUBLIC_VIX_DASHBOARD_URL`.
- Deploy Market Radar backend separately and set `MARKET_RADAR_BACKEND_URL`.
- Keep real API credentials out of git and markdown docs.
