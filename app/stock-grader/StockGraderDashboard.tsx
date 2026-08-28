"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import {
  ArrowUpDown,
  BarChart3,
  CalendarClock,
  Filter,
  Search,
  ShieldCheck,
  SlidersHorizontal,
} from "lucide-react";
import type { StockGraderPayload, StockGraderScore } from "@/lib/stock-grader";
import QuantModuleHeader from "@/components/QuantModuleHeader";

type Props = {
  payload: StockGraderPayload;
};

const categoryColumns = [
  { key: "valuation", label: "Val" },
  { key: "growth", label: "Growth" },
  { key: "profitability", label: "Prof" },
  { key: "financials", label: "Fin" },
  { key: "business_quality", label: "Quality" },
  { key: "management", label: "Mgmt" },
  { key: "income", label: "Income" },
  { key: "market_sentiment", label: "Sent" },
  { key: "eps_revisions", label: "EPS" },
  { key: "industry", label: "Industry" },
];

function scoreTone(score: number | null) {
  if (score == null) {
    return "border-[#E7ECF5] bg-white text-[#9AA5BA]";
  }
  if (score >= 8) {
    return "border-emerald-200 bg-emerald-50 text-emerald-700";
  }
  if (score >= 6) {
    return "border-[#D7B46A] bg-[#F8F1E3] text-[#5F4820]";
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
    return "bg-[#F8F1E3] text-[#5F4820]";
  }
  if (confidence === "low") {
    return "bg-amber-50 text-amber-700";
  }
  return "bg-[#F8FAFC] text-[#5B6780]";
}

function categoryFor(score: StockGraderScore, categoryKey: string) {
  return score.categories.find((item) => item.categoryKey === categoryKey);
}

export default function StockGraderDashboard({ payload }: Props) {
  const [query, setQuery] = useState("");
  const [archetype, setArchetype] = useState("All");
  const [minimumScore, setMinimumScore] = useState(0);
  const [sortMode, setSortMode] = useState<"book" | "high" | "low">("book");
  const [selectedTicker, setSelectedTicker] = useState(payload.scores[0]?.ticker ?? "");

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
    <main className="min-h-screen bg-[radial-gradient(circle_at_top_left,rgba(215,180,106,0.16),transparent_30%),linear-gradient(180deg,#FBFAF7_0%,#F5EFE4_100%)] text-[#111827]">
      <QuantModuleHeader
        title="Stock Grader"
        subtitle="US equity fundamental scores, category reasons, and weekly review queue."
        icon={<BarChart3 className="h-5 w-5" />}
        meta={
          <div className="flex flex-wrap items-center gap-2 text-xs font-black uppercase tracking-[0.12em] text-[#F0D694]">
            <span className="inline-flex h-9 items-center gap-2 border border-[#D7B46A]/45 bg-white/8 px-3">
              <CalendarClock className="h-4 w-4" />
              Weekly / review
            </span>
            <span className="inline-flex h-9 items-center gap-2 border border-[#D7B46A]/45 bg-white/8 px-3">
              As of {payload.latestFullScoreDate ?? "No report"}
            </span>
          </div>
        }
        actions={
          <Link
            href="/stock-grader/admin"
            className="inline-flex h-9 items-center gap-2 bg-[#D7B46A] px-3 text-xs font-black uppercase tracking-[0.12em] text-[#111827] transition hover:bg-[#E5C984]"
          >
            <ShieldCheck className="h-4 w-4" />
            Admin Review
          </Link>
        }
      />
      <section className="mx-auto max-w-7xl px-5 py-6 sm:px-8 lg:px-12">
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <div className="border border-[#E6DDCD] bg-[#FFFDF8]/84 px-4 py-3 shadow-[0_14px_34px_rgba(78,56,21,0.06)] backdrop-blur-xl">
              <div className="text-[10px] font-bold uppercase tracking-[0.14em] text-[#9AA5BA]">Tickers</div>
              <div className="mt-1 text-xl font-black">{payload.summary.tickerCount}</div>
            </div>
            <div className="border border-[#E6DDCD] bg-[#FFFDF8]/84 px-4 py-3 shadow-[0_14px_34px_rgba(78,56,21,0.06)] backdrop-blur-xl">
              <div className="text-[10px] font-bold uppercase tracking-[0.14em] text-[#9AA5BA]">Avg</div>
              <div className="mt-1 text-xl font-black">
                {payload.summary.averageComposite?.toFixed(2) ?? "-"}
              </div>
            </div>
            <div className="border border-[#E6DDCD] bg-[#FFFDF8]/84 px-4 py-3 shadow-[0_14px_34px_rgba(78,56,21,0.06)] backdrop-blur-xl">
              <div className="text-[10px] font-bold uppercase tracking-[0.14em] text-[#9AA5BA]">Manual</div>
              <div className="mt-1 text-xl font-black">{payload.summary.manualOverrideCount}</div>
            </div>
            <div className="border border-[#E6DDCD] bg-[#FFFDF8]/84 px-4 py-3 shadow-[0_14px_34px_rgba(78,56,21,0.06)] backdrop-blur-xl">
              <div className="text-[10px] font-bold uppercase tracking-[0.14em] text-[#9AA5BA]">As Of</div>
              <div className="mt-1 text-sm font-black">{payload.latestFullScoreDate ?? "No report"}</div>
            </div>
        </div>

        <div className="mt-6 grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1fr)_340px]">
          <section className="min-w-0 border border-[#E6DDCD] bg-[#FFFDF8]/88 shadow-[0_18px_45px_rgba(78,56,21,0.08)] backdrop-blur-xl">
            <div className="grid grid-cols-1 gap-3 border-b border-[#E6DDCD] p-4 md:grid-cols-[minmax(180px,1fr)_220px_160px_160px]">
              <label className="relative block">
                <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[#9AA5BA]" />
                <input
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  placeholder="Search ticker"
                  className="h-11 w-full border border-[#E6DDCD] bg-white/80 pl-10 pr-3 text-sm font-semibold outline-none transition focus:border-[#D7B46A] focus:ring-2 focus:ring-[#D7B46A]/25"
                />
              </label>
              <label className="relative block">
                <Filter className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[#9AA5BA]" />
                <select
                  value={archetype}
                  onChange={(event) => setArchetype(event.target.value)}
                  className="h-11 w-full border border-[#E6DDCD] bg-white/80 pl-10 pr-3 text-sm font-semibold outline-none transition focus:border-[#D7B46A] focus:ring-2 focus:ring-[#D7B46A]/25"
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
                  className="h-11 w-full border border-[#E6DDCD] bg-white/80 pl-10 pr-3 text-sm font-semibold outline-none transition focus:border-[#D7B46A] focus:ring-2 focus:ring-[#D7B46A]/25"
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
                  className="h-11 w-full border border-[#E6DDCD] bg-white/80 pl-10 pr-3 text-sm font-semibold outline-none transition focus:border-[#D7B46A] focus:ring-2 focus:ring-[#D7B46A]/25"
                >
                  <option value="book">Workbook order</option>
                  <option value="high">Score high</option>
                  <option value="low">Score low</option>
                </select>
              </label>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full min-w-[780px] table-fixed border-collapse text-left text-sm">
                <colgroup>
                  <col className="w-[74px]" />
                  <col className="w-[116px]" />
                  <col className="w-[58px]" />
                  {categoryColumns.map((category) => (
                    <col key={category.key} className="w-[50px]" />
                  ))}
                </colgroup>
                <thead>
                  <tr className="border-b border-[#E6DDCD] bg-[#F8F1E3] text-[10px] uppercase tracking-[0.14em] text-[#8A6A2F]">
                    <th className="px-3 py-3">Ticker</th>
                    <th className="px-2 py-3">Type</th>
                    <th className="px-2 py-3 text-center">Total</th>
                    {categoryColumns.map((category) => (
                      <th key={category.key} className="px-1 py-3 text-center">
                        {category.label}
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
                        selected?.ticker === score.ticker ? "bg-[#F8F1E3]" : ""
                      }`}
                    >
                      <td className="px-3 py-3">
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
                      <td className="truncate px-2 py-3 text-[11px] font-semibold text-[#5B6780]" title={score.archetype}>
                        {score.archetype}
                      </td>
                      <td className="px-2 py-3 text-center">
                        <span
                          className={`inline-flex h-8 min-w-11 items-center justify-center rounded-lg border px-2 font-black ${scoreTone(
                            score.composite0To10
                          )}`}
                        >
                          {score.composite0To10?.toFixed(1) ?? "-"}
                        </span>
                      </td>
                      {categoryColumns.map((category) => {
                        const categoryScore = categoryFor(score, category.key);
                        const value = categoryScore?.score ?? null;
                        return (
                          <td key={category.key} className="px-1 py-3 text-center">
                            <span
                              className={`inline-flex h-7 min-w-8 items-center justify-center rounded-md border px-1.5 text-xs font-black ${scoreTone(
                                value
                              )}`}
                            >
                              {value ?? "-"}
                            </span>
                            {categoryScore?.isManual ? (
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

          <aside className="border border-[#E6DDCD] bg-[#FFFDF8]/88 p-4 shadow-[0_18px_45px_rgba(78,56,21,0.08)] backdrop-blur-xl xl:sticky xl:top-24 xl:max-h-[calc(100vh-7rem)] xl:overflow-y-auto">
            {selected ? (
              <>
                <div className="flex items-start justify-between gap-3 border-b border-[#E7ECF5] pb-4">
                  <div>
                    <div className="text-[10px] font-bold uppercase tracking-[0.16em] text-[#8A6A2F]">
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
                    className={`inline-flex h-12 min-w-14 items-center justify-center border px-3 text-lg font-black ${scoreTone(
                      selected.composite0To10
                    )}`}
                  >
                    {selected.composite0To10?.toFixed(1) ?? "-"}
                  </span>
                </div>

                <div className="mt-4 flex items-center gap-2 bg-white/70 px-3 py-2 text-xs font-bold text-[#5B6780]">
                  <CalendarClock className="h-4 w-4 text-[#8A6A2F]" />
                  {payload.latestFullScoreDate ?? "No report date"}
                </div>

                <div className="mt-4 space-y-3">
                  {selected.categories.map((category) => (
                    <div key={category.category} className="border border-[#E6DDCD] bg-white/70 p-3">
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
                          <summary className="cursor-pointer font-bold text-[#8A6A2F]">System rationale</summary>
                          <p className="mt-2 leading-5">{category.systemReasonText}</p>
                        </details>
                      ) : null}
                    </div>
                  ))}
                </div>
              </>
            ) : (
              <div className="flex min-h-80 items-center justify-center bg-white/70 text-sm font-bold text-[#9AA5BA]">
                No scores available
              </div>
            )}
          </aside>
        </div>

        {payload.updates.length ? (
          <section className="mt-6 border border-[#E6DDCD] bg-[#FFFDF8]/88 p-4 shadow-[0_18px_45px_rgba(78,56,21,0.08)] backdrop-blur-xl">
            <div className="mb-3 flex items-center gap-2 text-sm font-black text-[#18233A]">
              <ShieldCheck className="h-4 w-4 text-[#8A6A2F]" />
              Latest Changes
            </div>
            <div className="space-y-2">
              {payload.updates.slice(0, 8).map((update, index) => (
                <div key={`${update.ticker}-${update.category}-${index}`} className="bg-white/70 p-3">
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
