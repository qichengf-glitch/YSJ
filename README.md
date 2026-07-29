# YSJ Partners - Financial Research & Strategy Website

A modern Next.js 14 website for YSJ Partners, an independent financial research and strategy studio.

## Tech Stack

- Next.js 14 (App Router)
- TypeScript
- Tailwind CSS
- Client-side language toggle (EN / 中文)

## Getting Started

1. Install dependencies:
```bash
npm install
```

2. Run the development server:
```bash
npm run dev
```

3. Open [http://localhost:3000](http://localhost:3000) in your browser.

## Project Structure

```
/app
  /page.tsx                -> Home page
  /research/page.tsx       -> Research page
  /strategy/page.tsx       -> Strategy page
  /prediction-markets/page.tsx -> Prediction Markets page
  /layout.tsx              -> Root layout
  /globals.css             -> Global styles

/components
  Navbar.tsx               -> Navigation bar
  LanguageToggle.tsx       -> Language switcher
  Section.tsx              -> Reusable section wrapper

/contexts
  LanguageContext.tsx      -> Language state management
```

## Features

- Bilingual support (English / 中文)
- Responsive design
- Modern fintech aesthetic
- Clean, minimal UI with deep blue accent color


## Integrated private services

- Jin10 / prediction-market backend: `jin10_us_dashboard_site` on loopback port 8000.
- CN option VIX backend: `cn_option_vix` on loopback port 8765.
- CN VIX automatic update and repair instructions: `docs/CN_VIX_AUTO_UPDATE.md`.

To repair the VIX database through a specific trading date on the credentialed server:

```bash
./scripts/sync_cn_vix_through.sh 2026-07-23
```
