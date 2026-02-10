"use client";

import { useMemo, useState } from "react";
import { RefreshCw } from "lucide-react";

type Horizon = "Short" | "Medium" | "Long";
type Conviction = "Low" | "Medium" | "High";

type PickItem = {
  symbol: string;
  name: string;
  thesisTag: string;
  horizon: Horizon;
  conviction: Conviction;
  note: string;
};

const CANDIDATE_PICKS: PickItem[] = [
  {
    symbol: "AAPL",
    name: "Apple Inc.",
    thesisTag: "Large-cap Tech",
    horizon: "Medium",
    conviction: "Medium",
    note: "Balance of hardware ecosystem and services margin.",
  },
  {
    symbol: "MSFT",
    name: "Microsoft Corp.",
    thesisTag: "Cloud / Productivity",
    horizon: "Long",
    conviction: "High",
    note: "Strategic exposure to cloud, AI infrastructure, and enterprise spend.",
  },
  {
    symbol: "NVDA",
    name: "NVIDIA Corp.",
    thesisTag: "AI Infrastructure",
    horizon: "Medium",
    conviction: "High",
    note: "Key beneficiary of accelerated computing and training demand.",
  },
  {
    symbol: "SPY",
    name: "S&P 500 ETF",
    thesisTag: "US Beta",
    horizon: "Long",
    conviction: "Medium",
    note: "Core exposure for benchmark-aware portfolios.",
  },
  {
    symbol: "QQQ",
    name: "NASDAQ 100 ETF",
    thesisTag: "Growth Tilt",
    horizon: "Medium",
    conviction: "Medium",
    note: "Concentrated exposure to secular growth franchises.",
  },
  {
    symbol: "TLT",
    name: "20+ Year Treasury ETF",
    thesisTag: "Duration",
    horizon: "Medium",
    conviction: "Low",
    note: "Rates hedge in late-cycle growth-slowing scenarios.",
  },
  {
    symbol: "GLD",
    name: "Gold Trust",
    thesisTag: "Macro Hedge",
    horizon: "Long",
    conviction: "Medium",
    note: "Diversifier against policy error and tail events.",
  },
  {
    symbol: "BTC-USD",
    name: "Bitcoin",
    thesisTag: "Digital Asset",
    horizon: "Long",
    conviction: "Low",
    note: "High-volatility expression of digital scarcity thesis.",
  },
  {
    symbol: "XLV",
    name: "Health Care ETF",
    thesisTag: "Defensive Growth",
    horizon: "Medium",
    conviction: "Medium",
    note: "Stable cash flows, secular demographics tailwinds.",
  },
  {
    symbol: "XLF",
    name: "Financials ETF",
    thesisTag: "Rate Sensitive",
    horizon: "Medium",
    conviction: "Low",
    note: "Beneficiary of steeper curves, but credit risk must be monitored.",
  },
  {
    symbol: "SMH",
    name: "Semiconductor ETF",
    thesisTag: "Cyclical Growth",
    horizon: "Medium",
    conviction: "Medium",
    note: "Broader way to express semi-cycle beyond single names.",
  },
  {
    symbol: "XLE",
    name: "Energy ETF",
    thesisTag: "Commodity Exposure",
    horizon: "Short",
    conviction: "Low",
    note: "Tactical tool for supply-demand imbalances in energy.",
  },
  {
    symbol: "HYG",
    name: "High Yield Bond ETF",
    thesisTag: "Credit Risk",
    horizon: "Medium",
    conviction: "Low",
    note: "Spread compression vehicle; sensitive to liquidity regimes.",
  },
  {
    symbol: "LQD",
    name: "Investment Grade ETF",
    thesisTag: "Credit Quality",
    horizon: "Medium",
    conviction: "Medium",
    note: "Higher-quality credit carry relative to sovereigns.",
  },
  {
    symbol: "ARKK",
    name: "Innovation ETF",
    thesisTag: "High Beta",
    horizon: "Short",
    conviction: "Low",
    note: "Tactical exposure to speculative growth factor.",
  },
  {
    symbol: "META",
    name: "Meta Platforms",
    thesisTag: "Digital Ads",
    horizon: "Medium",
    conviction: "Medium",
    note: "Margin leverage from cost discipline and ad market normalization.",
  },
  {
    symbol: "AMZN",
    name: "Amazon.com",
    thesisTag: "E-commerce / Cloud",
    horizon: "Long",
    conviction: "Medium",
    note: "Operating leverage in North America + AWS optionality.",
  },
  {
    symbol: "GOOGL",
    name: "Alphabet Inc.",
    thesisTag: "Search / AI",
    horizon: "Long",
    conviction: "Medium",
    note: "Balanced exposure to search, cloud, and emerging AI products.",
  },
  {
    symbol: "TSLA",
    name: "Tesla Inc.",
    thesisTag: "EV / Optionality",
    horizon: "Long",
    conviction: "Low",
    note: "Equity duration and volatility remain high; position sizing critical.",
  },
  {
    symbol: "BRK.B",
    name: "Berkshire Hathaway",
    thesisTag: "Compounder",
    horizon: "Long",
    conviction: "Medium",
    note: "Diversified cash-generative platform with embedded option value.",
  },
  {
    symbol: "EEM",
    name: "Emerging Markets ETF",
    thesisTag: "EM Beta",
    horizon: "Long",
    conviction: "Low",
    note: "Macro and FX-sensitive; best used within a broader allocation.",
  },
  {
    symbol: "FXI",
    name: "China Large-Cap ETF",
    thesisTag: "China Equity",
    horizon: "Medium",
    conviction: "Low",
    note: "Policy path and earnings visibility remain key swing factors.",
  },
  {
    symbol: "IEF",
    name: "7-10 Year Treasury ETF",
    thesisTag: "Intermediate Duration",
    horizon: "Medium",
    conviction: "Medium",
    note: "Compromise between rate sensitivity and carry.",
  },
  {
    symbol: "USO",
    name: "US Oil Fund",
    thesisTag: "Crude Oil",
    horizon: "Short",
    conviction: "Low",
    note: "Curve structure and roll yield critical for P&L.",
  },
];

function pickRandomItems(source: PickItem[], count: number): PickItem[] {
  const indices = [...source.keys()];
  for (let i = indices.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1));
    [indices[i], indices[j]] = [indices[j], indices[i]];
  }
  return indices.slice(0, count).map((idx) => source[idx]);
}

export function OurPicksPanel() {
  const initialPicks = useMemo(
    () => pickRandomItems(CANDIDATE_PICKS, 10),
    []
  );
  const [picks, setPicks] = useState<PickItem[]>(initialPicks);

  const refresh = () => {
    setPicks(pickRandomItems(CANDIDATE_PICKS, 10));
  };

  const chipColorForConviction = (conviction: Conviction) => {
    switch (conviction) {
      case "High":
        return "bg-emerald-50 text-emerald-700 border-emerald-200";
      case "Medium":
        return "bg-amber-50 text-amber-700 border-amber-200";
      case "Low":
      default:
        return "bg-slate-50 text-slate-700 border-slate-200";
    }
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between text-sm text-gray-600">
        <p>
          Rotating, illustrative list of instruments we monitor across themes.
        </p>
        <button
          type="button"
          onClick={refresh}
          className="inline-flex items-center gap-1 rounded-full border border-gray-300 bg-white px-2.5 py-1 text-xs font-medium text-gray-700 hover:border-primary hover:text-primary focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
        >
          <RefreshCw className="h-3.5 w-3.5" />
          <span>Refresh picks</span>
        </button>
      </div>

      <div className="divide-y divide-gray-200 rounded-lg border border-gray-200 bg-white/70">
        {picks.map((item) => (
          <div key={item.symbol} className="px-4 py-3">
            <div className="flex items-baseline justify-between gap-3">
              <div>
                <div className="font-mono text-sm font-medium text-gray-900">
                  {item.symbol.replace(/^\^/, "")}
                </div>
                <div className="text-xs text-gray-600 mt-0.5">{item.name}</div>
              </div>
              <div className="text-xs text-gray-500 text-right max-w-[200px]">
                {item.note}
              </div>
            </div>
            <div className="mt-2 flex flex-wrap items-center gap-2">
              <span className="inline-flex items-center rounded-full bg-gray-100 px-2.5 py-1 text-xs font-medium text-gray-700">
                {item.thesisTag}
              </span>
              <span className="inline-flex items-center rounded-full bg-gray-900 px-2.5 py-1 text-xs font-medium text-white">
                {item.horizon} horizon
              </span>
              <span
                className={`inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-medium ${chipColorForConviction(
                  item.conviction
                )}`}
              >
                {item.conviction} conviction
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

