# YSJLab - Quantitative Market Monitoring Workspace

A modern Next.js 14 workspace for internal quantitative research, market monitoring, research notes, and controlled dashboard access.

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
  /research/ongoing-thesis -> Ongoing thesis page
  /access                  -> Quant Monitor access page
  /cn-option-vix           -> CN Option VIX module
  /prediction-markets/page.tsx -> Prediction Market module
  /stock-grader            -> Stock Grader module
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
- YSJ Capital-inspired visual system
- Controlled access for internal monitoring modules
