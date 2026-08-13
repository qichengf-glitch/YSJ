"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  ArrowUpDown,
  BarChart3,
  CalendarClock,
  Filter,
  Search,
  ShieldCheck,
  SlidersHorizontal,
} from "lucide-react";
import type { StockGraderPayload, StockGraderScore } from "@/lib/stock-grader";

type Props = {
  payload: StockGraderPayload;
};

const compactCategory: Record<string, string> = {
  Valuation: "Val",
  Growth: "Growth",
  Profitability: "Prof",
  Financials: "Fin",
  "Business Quality": "Quality",
  Management: "Mgmt",
  Income: "Income",
  "Market Sentiment": "Sent",
  "EPS/Revison Trends": "EPS",
  "Industry/Sector Tailwinds": "Industry",
};

function scoreTone(score: number | null) {
  if (score == null) {
    return "border-[#E7ECF5] bg-white text-[#9AA5BA]";
  }
  if (score >= 8) {
    return "border-emerald-200 bg-emerald-50 text-emerald-700";
  }
  if (score >= 6) {
    return "border-[#D6E4FF] bg-[#EEF2FF] text-[#273B9A]";
  }
  if (score >= 4) {
    return "border-amber-200 bg-amber-50 text-amber-700";
  }
  return "border-rose-200 bg-rose-50 text-rose-700";
}

function confidenceTone(confidence: string) {
  if (confidence === "high") {
    return "bg-emerald-50 text-emerald-700";
  }
  if (confidence === "medium") {
    return "bg-[#EEF2FF] text-[#273B9A]";
  }
  if (confidence === "low") {
    return "bg-amber-50 text-amber-700";
  }
  return "bg-[#F8FAFC] text-[#5B6780]";
}

function categoryScore(score: StockGraderScore, category: string) {
  return score.categories.find((item) => item.category === category)?.score ?? null;
}

export default function StockGraderDashboard({ payload }: Props) {
  const [query, setQuery] = useState("");
  const [archetype, setArchetype] = useState("All");
  const [minimumScore, setMinimumScore] = useState(0);
  const [sortMode, setSortMode] = useState<"book" | "high" | "low">("book");
  const [selectedTicker, setSelectedTicker] = useState(payload.scores[0]?.ticker ?? "");

  const categories = useMemo(() => {
    const first = payload.scores[0];
    return first?.categories.map((category) => category.category) ?? [];
  }, [payload.scores]);

  const archetypes = useMemo(
    () => ["All", ...Array.from(new Set(payload.scores.map((score) => score.archetype))).sort()],
    [payload.scores]
  );

  const filteredScores = useMemo(() => {
    const q = query.trim().toUpperCase();
    const rows = payload.scores.filter((score) => {
      const matchesQuery = !q || score.ticker.includes(q);
      const matchesArchetype = archetype === "All" || score.archetype === archetype;
      const matchesScore = (score.composite0To10 ?? 0) >= minimumScore;
      return matchesQuery && matchesArchetype && matchesScore;
    });

    if (sortMode === "high") {
      return [...rows].sort((a, b) => (b.composite0To10 ?? -1) - (a.composite0To10 ?? -1));
    }
    if (sortMode === "low") {
      return [...rows].sort((a, b) => (a.composite0To10 ?? 99) - (b.composite0To10 ?? 99));
    }
    return rows;
  }, [archetype, minimumScore, payload.scores, query, sortMode]);

  const selected =
    payload.scores.find((score) => score.ticker === selectedTicker) ?? filteredScores[0] ?? payload.scores[0];

  return (
    <main className="min-h-screen bg-[linear-gradient(180deg,#FFFFFF_0%,#F8FAFC_100%)] text-[#18233A]">
      <section className="mx-auto max-w-7xl px-5 py-6 sm:px-8 lg:px-12">
        <div className="flex flex-col gap-5 border-b border-[#E7ECF5] pb-6 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <Link
              href="/access"
              className="mb-5 inline-flex items-center gap-2 text-sm font-bold text-[#4F63F6] transition hover:text-[#273B9A]"
            >
              <ArrowLeft className="h-4 w-4" />
              Private Access
            </Link>
            <Link
              href="/stock-grader/admin"
              className="mb-5 ml-4 inline-flex items-center gap-2 text-sm font-bold text-[#5B6780] transition hover:text-[#4F63F6]"
            >
              <ShieldCheck className="h-4 w-4" />
              Admin Review
            </Link>
            <div className="inline-flex items-center gap-2 rounded-full border border-[#E7ECF5] bg-white px-4 py-2 text-xs font-bold uppercase tracking-[0.18em] text-[#4F63F6]">
              <BarChart3 className="h-3.5 w-3.5" />
              Stock Grader
            </div>
            <h1 className="mt-4 text-3xl font-black leading-tight text-[#18233A] sm:text-4xl">
              US Equity Fundamental Scores
            </h1>
          </div>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <div className="rounded-xl border border-[#E7ECF5] bg-white px-4 py-3">
              <div className="text-[10px] font-bold uppercase tracking-[0.14em] text-[#9AA5BA]">Tickers</div>
              <div className="mt-1 text-xl font-black">{payload.summary.tickerCount}</div>
            </div>
            <div className="rounded-xl border border-[#E7ECF5] bg-white px-4 py-3">
              <div className="text-[10px] font-bold uppercase tracking-[0.14em] text-[#9AA5BA]">Avg</div>
              <div className="mt-1 text-xl font-black">
                {payload.summary.averageComposite?.toFixed(2) ?? "-"}
              </div>
            </div>
            <div className="rounded-xl border border-[#E7ECF5] bg-white px-4 py-3">
              <div className="text-[10px] font-bold uppercase tracking-[0.14em] text-[#9AA5BA]">Manual</div>
              <div className="mt-1 text-xl font-black">{payload.summary.manualOverrideCount}</div>
            </div>
            <div className="rounded-xl border border-[#E7ECF5] bg-white px-4 py-3">
              <div className="text-[10px] font-bold uppercase tracking-[0.14em] text-[#9AA5BA]">As Of</div>
              <div className="mt-1 text-sm font-black">{payload.latestFullScoreDate ?? "No report"}</div>
            </div>
          </div>
        </div>

        <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,1fr)_360px]">
          <section className="min-w-0 rounded-2xl border border-[#E7ECF5] bg-white shadow-[0_18px_45px_rgba(39,59,154,0.08)]">
            <div className="grid grid-cols-1 gap-3 border-b border-[#E7ECF5] p-4 md:grid-cols-[minmax(180px,1fr)_220px_160px_160px]">
              <label className="relative block">
                <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[#9AA5BA]" />
                <input
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  placeholder="Search ticker"
                  className="h-11 w-full rounded-xl border border-[#E7ECF5] bg-[#F8FAFC] pl-10 pr-3 text-sm font-semibold outline-none transition focus:border-[#A8B2FF] focus:ring-2 focus:ring-[#A8B2FF]/25"
                />
              </label>
              <label className="relative block">
                <Filter className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[#9AA5BA]" />
                <select
                  value={archetype}
                  onChange={(event) => setArchetype(event.target.value)}
                  className="h-11 w-full rounded-xl border border-[#E7ECF5] bg-[#F8FAFC] pl-10 pr-3 text-sm font-semibold outline-none transition focus:border-[#A8B2FF] focus:ring-2 focus:ring-[#A8B2FF]/25"
                >
                  {archetypes.map((item) => (
                    <option key={item} value={item}>
                      {item}
                    </option>
                  ))}
                </select>
              </label>
              <label className="relative block">
                <SlidersHorizontal className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[#9AA5BA]" />
                <select
                  value={minimumScore}
                  onChange={(event) => setMinimumScore(Number(event.target.value))}
                  className="h-11 w-full rounded-xl border border-[#E7ECF5] bg-[#F8FAFC] pl-10 pr-3 text-sm font-semibold outline-none transition focus:border-[#A8B2FF] focus:ring-2 focus:ring-[#A8B2FF]/25"
                >
                  <option value={0}>All scores</option>
                  <option value={8}>8+</option>
                  <option value={6}>6+</option>
                  <option value={4}>4+</option>
                </select>
              </label>
              <label className="relative block">
                <ArrowUpDown className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[#9AA5BA]" />
                <select
                  value={sortMode}
                  onChange={(event) => setSortMode(event.target.value as "book" | "high" | "low")}
                  className="h-11 w-full rounded-xl border border-[#E7ECF5] bg-[#F8FAFC] pl-10 pr-3 text-sm font-semibold outline-none transition focus:border-[#A8B2FF] focus:ring-2 focus:ring-[#A8B2FF]/25"
                >
                  <option value="book">Workbook order</option>
                  <option value="high">Score high</option>
                  <option value="low">Score low</option>
                </select>
              </label>
            </div>

            <div className="overflow-x-auto">
              <table className="min-w-[980px] w-full border-collapse text-left text-sm">
                <thead>
                  <tr className="border-b border-[#E7ECF5] bg-[#F8FAFC] text-[10px] uppercase tracking-[0.14em] text-[#7B879C]">
                    <th className="w-28 px-4 py-3">Ticker</th>
                    <th className="w-48 px-3 py-3">Archetype</th>
                    <th className="w-24 px-3 py-3">Total</th>
                    {categories.map((category) => (
                      <th key={category} className="px-2 py-3 text-center">
                        {compactCategory[category] ?? category}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {filteredScores.map((score) => (
                    <tr
                      key={score.ticker}
                      onClick={() => setSelectedTicker(score.ticker)}
                      className={`cursor-pointer border-b border-[#EEF2F7] transition hover:bg-[#F8FAFC] ${
                        selected?.ticker === score.ticker ? "bg-[#EEF2FF]" : ""
                      }`}
                    >
                      <td className="px-4 py-3">
                        <div className="font-black text-[#18233A]">{score.ticker}</div>
                        <div
                          className={`mt-1 inline-flex rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-[0.10em] ${
                            score.hasManualOverride
                              ? "bg-amber-50 text-amber-700"
                              : "bg-[#F8FAFC] text-[#7B879C]"
                          }`}
                        >
                          {score.hasManualOverride ? "Manual" : "System"}
                        </div>
                      </td>
                      <td className="px-3 py-3 text-xs font-semibold text-[#5B6780]">{score.archetype}</td>
                      <td className="px-3 py-3">
                        <span
                          className={`inline-flex h-8 min-w-12 items-center justify-center rounded-lg border px-2 font-black ${scoreTone(
                            score.composite0To10
                          )}`}
                        >
                          {score.composite0To10?.toFixed(1) ?? "-"}
                        </span>
                      </td>
                      {categories.map((category) => {
                        const value = categoryScore(score, category);
                        return (
                          <td key={category} className="px-2 py-3 text-center">
                            <span
                              className={`inline-flex h-7 min-w-8 items-center justify-center rounded-md border px-1.5 text-xs font-black ${scoreTone(
                                value
                              )}`}
                            >
                              {value ?? "-"}
                            </span>
                            {score.categories.find((item) => item.category === category)?.isManual ? (
                              <span className="ml-1 inline-flex h-1.5 w-1.5 rounded-full bg-amber-500 align-middle" />
                            ) : null}
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <aside className="rounded-2xl border border-[#E7ECF5] bg-white p-4 shadow-[0_18px_45px_rgba(39,59,154,0.08)]">
            {selected ? (
              <>
                <div className="flex items-start justify-between gap-3 border-b border-[#E7ECF5] pb-4">
                  <div>
                    <div className="text-[10px] font-bold uppercase tracking-[0.16em] text-[#A8B2FF]">
                      Selected
                    </div>
                    <div className="mt-1 text-3xl font-black">{selected.ticker}</div>
                    <div className="mt-1 text-xs font-semibold text-[#5B6780]">{selected.archetype}</div>
                    <div
                      className={`mt-2 inline-flex rounded-full px-2 py-1 text-[10px] font-bold uppercase tracking-[0.12em] ${
                        selected.hasManualOverride
                          ? "bg-amber-50 text-amber-700"
                          : "bg-[#F8FAFC] text-[#7B879C]"
                      }`}
                    >
                      {selected.hasManualOverride ? "Manual override active" : "System scores only"}
                    </div>
                  </div>
                  <span
                    className={`inline-flex h-12 min-w-14 items-center justify-center rounded-xl border px-3 text-lg font-black ${scoreTone(
                      selected.composite0To10
                    )}`}
                  >
                    {selected.composite0To10?.toFixed(1) ?? "-"}
                  </span>
                </div>

                <div className="mt-4 flex items-center gap-2 rounded-xl bg-[#F8FAFC] px-3 py-2 text-xs font-bold text-[#5B6780]">
                  <CalendarClock className="h-4 w-4 text-[#4F63F6]" />
                  {payload.latestFullScoreDate ?? "No report date"}
                </div>

                <div className="mt-4 space-y-3">
                  {selected.categories.map((category) => (
                    <div key={category.category} className="rounded-xl border border-[#E7ECF5] bg-[#F8FAFC] p-3">
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <div className="text-sm font-black text-[#18233A]">{category.category}</div>
                          <div className="mt-1 flex items-center gap-2 text-[11px] font-bold">
                            <span className={`rounded-full px-2 py-1 ${confidenceTone(category.confidence)}`}>
                              {category.confidence}
                            </span>
                            <span
                              className={`rounded-full px-2 py-1 ${
                                category.isManual ? "bg-amber-50 text-amber-700" : "bg-white text-[#5B6780]"
                              }`}
                            >
                              {category.isManual ? "manual" : "system"}
                            </span>
                          </div>
                        </div>
                        <span
                          className={`inline-flex h-9 min-w-10 items-center justify-center rounded-lg border px-2 font-black ${scoreTone(
                            category.score
                          )}`}
                        >
                          {category.score ?? "-"}
                        </span>
                      </div>
                      {category.isManual ? (
                        <div className="mt-3 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs font-semibold text-amber-800">
                          System score {category.systemScore ?? "-"} changed to {category.score ?? "-"} by{" "}
                          {category.override?.author || "Admin"} on {category.override?.updatedAt.slice(0, 10)}.
                        </div>
                      ) : null}
                      <p className="mt-3 line-clamp-3 text-xs leading-5 text-[#5B6780]">{category.reasonText}</p>
                      {category.isManual && category.systemReasonText ? (
                        <details className="mt-2 text-xs text-[#7B879C]">
                          <summary className="cursor-pointer font-bold text-[#4F63F6]">System rationale</summary>
                          <p className="mt-2 leading-5">{category.systemReasonText}</p>
                        </details>
                      ) : null}
                    </div>
                  ))}
                </div>
              </>
            ) : (
              <div className="flex min-h-80 items-center justify-center rounded-xl bg-[#F8FAFC] text-sm font-bold text-[#9AA5BA]">
                No scores available
              </div>
            )}
          </aside>
        </div>

        {payload.updates.length ? (
          <section className="mt-6 rounded-2xl border border-[#E7ECF5] bg-white p-4 shadow-[0_18px_45px_rgba(39,59,154,0.08)]">
            <div className="mb-3 flex items-center gap-2 text-sm font-black text-[#18233A]">
              <ShieldCheck className="h-4 w-4 text-[#4F63F6]" />
              Latest Changes
            </div>
            <div className="space-y-2">
              {payload.updates.slice(0, 8).map((update, index) => (
                <div key={`${update.ticker}-${update.category}-${index}`} className="rounded-xl bg-[#F8FAFC] p-3">
                  <div className="text-sm font-black">
                    {update.ticker} {update.category} {update.oldScore ?? "-"} to {update.newScore ?? "-"}
                  </div>
                  <p className="mt-1 text-xs leading-5 text-[#5B6780]">{update.reasonText}</p>
                </div>
              ))}
            </div>
          </section>
        ) : null}
      </section>
    </main>
  );
}
