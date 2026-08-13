"use client";

import { FormEvent, useMemo, useState } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  CheckCircle2,
  LockKeyhole,
  RotateCcw,
  Save,
  Search,
  ShieldCheck,
  Trash2,
} from "lucide-react";
import type { StockGraderPayload, StockGraderScore } from "@/lib/stock-grader";
import type { StockGraderOverrideRecord } from "@/lib/stock-grader-overrides";

type Props = {
  initialPayload: StockGraderPayload;
  initialIsAdmin: boolean;
  isConfigured: boolean;
};

const editableCategories = [
  { key: "business_quality", display: "Business Quality" },
  { key: "income", display: "Income" },
  { key: "market_sentiment", display: "Market Sentiment" },
  { key: "industry", display: "Industry/Sector Tailwinds" },
];

function overrideId(ticker: string, categoryKey: string) {
  return `${ticker.toUpperCase()}:${categoryKey}`;
}

function categoryFor(score: StockGraderScore | undefined, categoryKey: string) {
  return score?.categories.find((category) => category.categoryKey === categoryKey);
}

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

export default function StockGraderAdminConsole({
  initialPayload,
  initialIsAdmin,
  isConfigured,
}: Props) {
  const [payload, setPayload] = useState(initialPayload);
  const [isAdmin, setIsAdmin] = useState(initialIsAdmin);
  const [passcode, setPasscode] = useState("");
  const [query, setQuery] = useState("");
  const [selectedTicker, setSelectedTicker] = useState(initialPayload.scores[0]?.ticker ?? "");
  const [categoryKey, setCategoryKey] = useState(editableCategories[0].key);
  const [score, setScore] = useState(5);
  const [confidence, setConfidence] = useState<"low" | "medium" | "high">("medium");
  const [author, setAuthor] = useState("Admin");
  const [note, setNote] = useState("");
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const selected = payload.scores.find((item) => item.ticker === selectedTicker);

  const overrideMap = useMemo(
    () =>
      new Map(
        payload.overrides.map((override) => [
          overrideId(override.ticker, override.categoryKey),
          override,
        ])
      ),
    [payload.overrides]
  );

  const filteredScores = useMemo(() => {
    const q = query.trim().toUpperCase();
    return payload.scores.filter((item) => !q || item.ticker.includes(q));
  }, [payload.scores, query]);

  function loadOverride(override: StockGraderOverrideRecord) {
    setSelectedTicker(override.ticker);
    setCategoryKey(override.categoryKey);
    setScore(override.score);
    setConfidence(override.confidence);
    setAuthor(override.author || "Admin");
    setNote(override.note);
    setStatus("");
    setError("");
  }

  function loadSystemValue(nextCategoryKey = categoryKey) {
    const category = categoryFor(selected, nextCategoryKey);
    setScore(category?.systemScore ?? category?.score ?? 5);
    setConfidence("medium");
    setNote("");
  }

  function handleCategoryChange(nextCategoryKey: string) {
    setCategoryKey(nextCategoryKey);
    const existing = overrideMap.get(overrideId(selectedTicker, nextCategoryKey));
    if (existing) {
      loadOverride(existing);
      return;
    }
    const category = categoryFor(selected, nextCategoryKey);
    setScore(category?.systemScore ?? 5);
    setConfidence("medium");
    setNote("");
  }

  function handleTickerChange(ticker: string) {
    setSelectedTicker(ticker);
    const existing = overrideMap.get(overrideId(ticker, categoryKey));
    if (existing) {
      loadOverride(existing);
      return;
    }
    const nextScore = payload.scores.find((item) => item.ticker === ticker);
    const category = categoryFor(nextScore, categoryKey);
    setScore(category?.systemScore ?? 5);
    setConfidence("medium");
    setNote("");
    setStatus("");
    setError("");
  }

  async function handleLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSubmitting(true);
    setError("");
    const response = await fetch("/api/stock-grader/admin/session", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ passcode }),
    });
    setIsSubmitting(false);
    if (!response.ok) {
      setError(response.status === 503 ? "Admin passcode is not configured." : "Invalid admin passcode.");
      return;
    }
    setIsAdmin(true);
    setPasscode("");
  }

  async function saveOverride(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSubmitting(true);
    setStatus("");
    setError("");
    const response = await fetch("/api/stock-grader/admin/overrides", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        ticker: selectedTicker,
        categoryKey,
        score,
        confidence,
        author,
        note,
      }),
    });
    const body = await response.json().catch(() => ({}));
    setIsSubmitting(false);
    if (!response.ok) {
      setError(body.detail || "Could not save override.");
      return;
    }
    setPayload(body.payload);
    setStatus("Override saved. Public Stock Grader now shows the manual value.");
  }

  async function deleteOverride(target?: StockGraderOverrideRecord) {
    const ticker = target?.ticker || selectedTicker;
    const key = target?.categoryKey || categoryKey;
    setIsSubmitting(true);
    setStatus("");
    setError("");
    const response = await fetch("/api/stock-grader/admin/overrides", {
      method: "DELETE",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ticker, categoryKey: key, actor: author }),
    });
    const body = await response.json().catch(() => ({}));
    setIsSubmitting(false);
    if (!response.ok) {
      setError(body.detail || "Could not delete override.");
      return;
    }
    setPayload(body.payload);
    if (!target || (target.ticker === selectedTicker && target.categoryKey === categoryKey)) {
      loadSystemValue(key);
    }
    setStatus("Override removed. Public Stock Grader now falls back to the system score.");
  }

  if (!isAdmin) {
    return (
      <main className="min-h-screen bg-[linear-gradient(180deg,#FFFFFF_0%,#F8FAFC_100%)] px-6 py-10 text-[#18233A]">
        <section className="mx-auto max-w-md rounded-2xl border border-[#E7ECF5] bg-white p-6 shadow-[0_18px_45px_rgba(39,59,154,0.10)]">
          <Link href="/stock-grader" className="mb-6 inline-flex items-center gap-2 text-sm font-bold text-[#4F63F6]">
            <ArrowLeft className="h-4 w-4" />
            Stock Grader
          </Link>
          <div className="mb-5 inline-flex h-11 w-11 items-center justify-center rounded-xl bg-[#EEF2FF] text-[#4F63F6]">
            <LockKeyhole className="h-5 w-5" />
          </div>
          <h1 className="text-2xl font-black">Admin Override Console</h1>
          <p className="mt-2 text-sm leading-6 text-[#5B6780]">
            Edit only discretionary Stock Grader categories. Each ticker/category keeps one active override.
          </p>
          {!isConfigured ? (
            <div className="mt-5 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm font-semibold text-amber-800">
              Set STOCK_GRADER_ADMIN_PASSCODE before using this console.
            </div>
          ) : (
            <form onSubmit={handleLogin} className="mt-5 space-y-4">
              <input
                type="password"
                value={passcode}
                onChange={(event) => setPasscode(event.target.value)}
                placeholder="Admin passcode"
                className="h-11 w-full rounded-xl border border-[#E7ECF5] bg-[#F8FAFC] px-3 text-sm font-semibold outline-none focus:border-[#A8B2FF] focus:ring-2 focus:ring-[#A8B2FF]/25"
                required
              />
              {error ? <p className="text-sm font-semibold text-rose-600">{error}</p> : null}
              <button
                type="submit"
                disabled={isSubmitting}
                className="inline-flex h-11 w-full items-center justify-center rounded-full bg-[#4F63F6] px-5 text-sm font-bold text-white transition hover:bg-[#273B9A] disabled:opacity-60"
              >
                {isSubmitting ? "Verifying..." : "Enter Admin"}
              </button>
            </form>
          )}
        </section>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-[linear-gradient(180deg,#FFFFFF_0%,#F8FAFC_100%)] text-[#18233A]">
      <section className="mx-auto max-w-7xl px-5 py-6 sm:px-8 lg:px-12">
        <div className="flex flex-col gap-5 border-b border-[#E7ECF5] pb-6 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <Link href="/stock-grader" className="mb-5 inline-flex items-center gap-2 text-sm font-bold text-[#4F63F6]">
              <ArrowLeft className="h-4 w-4" />
              Stock Grader
            </Link>
            <div className="inline-flex items-center gap-2 rounded-full border border-[#E7ECF5] bg-white px-4 py-2 text-xs font-bold uppercase tracking-[0.18em] text-[#4F63F6]">
              <ShieldCheck className="h-3.5 w-3.5" />
              Admin Override Layer
            </div>
            <h1 className="mt-4 text-3xl font-black leading-tight sm:text-4xl">Discretionary Review Queue</h1>
          </div>
          <div className="grid grid-cols-3 gap-3">
            <div className="rounded-xl border border-[#E7ECF5] bg-white px-4 py-3">
              <div className="text-[10px] font-bold uppercase tracking-[0.14em] text-[#9AA5BA]">Active</div>
              <div className="mt-1 text-xl font-black">{payload.summary.manualOverrideCount}</div>
            </div>
            <div className="rounded-xl border border-[#E7ECF5] bg-white px-4 py-3">
              <div className="text-[10px] font-bold uppercase tracking-[0.14em] text-[#9AA5BA]">Tickers</div>
              <div className="mt-1 text-xl font-black">{payload.summary.manualTickerCount}</div>
            </div>
            <div className="rounded-xl border border-[#E7ECF5] bg-white px-4 py-3">
              <div className="text-[10px] font-bold uppercase tracking-[0.14em] text-[#9AA5BA]">Report</div>
              <div className="mt-1 text-sm font-black">{payload.latestFullScoreDate ?? "-"}</div>
            </div>
          </div>
        </div>

        <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-[280px_minmax(0,1fr)_360px]">
          <aside className="rounded-2xl border border-[#E7ECF5] bg-white p-4 shadow-[0_18px_45px_rgba(39,59,154,0.08)]">
            <label className="relative block">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[#9AA5BA]" />
              <input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Search ticker"
                className="h-11 w-full rounded-xl border border-[#E7ECF5] bg-[#F8FAFC] pl-10 pr-3 text-sm font-semibold outline-none focus:border-[#A8B2FF] focus:ring-2 focus:ring-[#A8B2FF]/25"
              />
            </label>
            <div className="mt-4 max-h-[680px] space-y-2 overflow-y-auto pr-1">
              {filteredScores.map((item) => (
                <button
                  key={item.ticker}
                  type="button"
                  onClick={() => handleTickerChange(item.ticker)}
                  className={`flex w-full items-center justify-between rounded-xl border px-3 py-2 text-left transition ${
                    selectedTicker === item.ticker
                      ? "border-[#A8B2FF] bg-[#EEF2FF]"
                      : "border-[#E7ECF5] bg-[#F8FAFC] hover:bg-white"
                  }`}
                >
                  <span>
                    <span className="block text-sm font-black">{item.ticker}</span>
                    <span className="block text-[11px] font-semibold text-[#7B879C]">
                      {item.hasManualOverride ? "Manual override" : "System score"}
                    </span>
                  </span>
                  <span className={`rounded-lg border px-2 py-1 text-xs font-black ${scoreTone(item.composite0To10)}`}>
                    {item.composite0To10?.toFixed(1) ?? "-"}
                  </span>
                </button>
              ))}
            </div>
          </aside>

          <section className="rounded-2xl border border-[#E7ECF5] bg-white p-4 shadow-[0_18px_45px_rgba(39,59,154,0.08)]">
            <div className="flex items-start justify-between gap-3 border-b border-[#E7ECF5] pb-4">
              <div>
                <div className="text-[10px] font-bold uppercase tracking-[0.16em] text-[#A8B2FF]">Selected</div>
                <div className="mt-1 text-3xl font-black">{selected?.ticker ?? "-"}</div>
                <div className="mt-1 text-xs font-semibold text-[#5B6780]">{selected?.archetype}</div>
              </div>
              <span className={`rounded-xl border px-3 py-2 text-lg font-black ${scoreTone(selected?.composite0To10 ?? null)}`}>
                {selected?.composite0To10?.toFixed(1) ?? "-"}
              </span>
            </div>

            <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2">
              {editableCategories.map((item) => {
                const category = categoryFor(selected, item.key);
                const active = overrideMap.get(overrideId(selectedTicker, item.key));
                return (
                  <button
                    key={item.key}
                    type="button"
                    onClick={() => handleCategoryChange(item.key)}
                    className={`rounded-xl border p-4 text-left transition ${
                      categoryKey === item.key
                        ? "border-[#A8B2FF] bg-[#EEF2FF]"
                        : "border-[#E7ECF5] bg-[#F8FAFC] hover:bg-white"
                    }`}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <div className="text-sm font-black">{item.display}</div>
                        <div className="mt-1 text-xs font-semibold text-[#7B879C]">
                          {active ? "Manual active" : "System baseline"}
                        </div>
                      </div>
                      <span className={`rounded-lg border px-2 py-1 text-sm font-black ${scoreTone(category?.score ?? null)}`}>
                        {category?.score ?? "-"}
                      </span>
                    </div>
                    {active ? <p className="mt-3 line-clamp-2 text-xs leading-5 text-[#5B6780]">{active.note}</p> : null}
                  </button>
                );
              })}
            </div>

            <form onSubmit={saveOverride} className="mt-5 rounded-2xl border border-[#E7ECF5] bg-[#F8FAFC] p-4">
              <div className="grid grid-cols-1 gap-3 md:grid-cols-4">
                <label className="block">
                  <span className="text-xs font-bold uppercase tracking-[0.12em] text-[#7B879C]">Category</span>
                  <select
                    value={categoryKey}
                    onChange={(event) => handleCategoryChange(event.target.value)}
                    className="mt-2 h-11 w-full rounded-xl border border-[#E7ECF5] bg-white px-3 text-sm font-semibold outline-none focus:border-[#A8B2FF]"
                  >
                    {editableCategories.map((item) => (
                      <option key={item.key} value={item.key}>
                        {item.display}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="block">
                  <span className="text-xs font-bold uppercase tracking-[0.12em] text-[#7B879C]">Score</span>
                  <input
                    type="number"
                    min={1}
                    max={10}
                    step={1}
                    value={score}
                    onChange={(event) => setScore(Number(event.target.value))}
                    className="mt-2 h-11 w-full rounded-xl border border-[#E7ECF5] bg-white px-3 text-sm font-semibold outline-none focus:border-[#A8B2FF]"
                  />
                </label>
                <label className="block">
                  <span className="text-xs font-bold uppercase tracking-[0.12em] text-[#7B879C]">Confidence</span>
                  <select
                    value={confidence}
                    onChange={(event) => setConfidence(event.target.value as "low" | "medium" | "high")}
                    className="mt-2 h-11 w-full rounded-xl border border-[#E7ECF5] bg-white px-3 text-sm font-semibold outline-none focus:border-[#A8B2FF]"
                  >
                    <option value="low">low</option>
                    <option value="medium">medium</option>
                    <option value="high">high</option>
                  </select>
                </label>
                <label className="block">
                  <span className="text-xs font-bold uppercase tracking-[0.12em] text-[#7B879C]">Author</span>
                  <input
                    value={author}
                    onChange={(event) => setAuthor(event.target.value)}
                    className="mt-2 h-11 w-full rounded-xl border border-[#E7ECF5] bg-white px-3 text-sm font-semibold outline-none focus:border-[#A8B2FF]"
                  />
                </label>
              </div>
              <label className="mt-3 block">
                <span className="text-xs font-bold uppercase tracking-[0.12em] text-[#7B879C]">Reason / analyst note</span>
                <textarea
                  value={note}
                  onChange={(event) => setNote(event.target.value)}
                  rows={5}
                  placeholder="Why should this category override the system baseline?"
                  className="mt-2 w-full rounded-xl border border-[#E7ECF5] bg-white px-3 py-3 text-sm font-semibold leading-6 outline-none focus:border-[#A8B2FF]"
                />
              </label>
              <div className="mt-4 flex flex-col gap-3 sm:flex-row">
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="inline-flex h-11 items-center justify-center gap-2 rounded-full bg-[#4F63F6] px-5 text-sm font-bold text-white transition hover:bg-[#273B9A] disabled:opacity-60"
                >
                  <Save className="h-4 w-4" />
                  Save Override
                </button>
                <button
                  type="button"
                  onClick={() => deleteOverride()}
                  disabled={isSubmitting}
                  className="inline-flex h-11 items-center justify-center gap-2 rounded-full border border-[#E7ECF5] bg-white px-5 text-sm font-bold text-[#5B6780] transition hover:border-rose-200 hover:text-rose-700 disabled:opacity-60"
                >
                  <RotateCcw className="h-4 w-4" />
                  Revert to System
                </button>
              </div>
              {status ? (
                <p className="mt-3 flex items-center gap-2 text-sm font-semibold text-emerald-700">
                  <CheckCircle2 className="h-4 w-4" />
                  {status}
                </p>
              ) : null}
              {error ? <p className="mt-3 text-sm font-semibold text-rose-600">{error}</p> : null}
            </form>
          </section>

          <aside className="rounded-2xl border border-[#E7ECF5] bg-white p-4 shadow-[0_18px_45px_rgba(39,59,154,0.08)]">
            <div className="mb-3 text-sm font-black">Active Override Cards</div>
            <div className="max-h-[760px] space-y-3 overflow-y-auto pr-1">
              {payload.overrides.length ? (
                payload.overrides.map((override) => (
                  <div key={overrideId(override.ticker, override.categoryKey)} className="rounded-xl border border-[#E7ECF5] bg-[#F8FAFC] p-3">
                    <div className="flex items-start justify-between gap-3">
                      <button type="button" onClick={() => loadOverride(override)} className="min-w-0 text-left">
                        <div className="text-sm font-black">
                          {override.ticker} · {override.category}
                        </div>
                        <div className="mt-1 text-[11px] font-semibold text-[#7B879C]">
                          {override.author} · {override.updatedAt.slice(0, 10)}
                        </div>
                      </button>
                      <span className={`rounded-lg border px-2 py-1 text-sm font-black ${scoreTone(override.score)}`}>
                        {override.score}
                      </span>
                    </div>
                    <p className="mt-2 line-clamp-3 text-xs leading-5 text-[#5B6780]">{override.note}</p>
                    <button
                      type="button"
                      onClick={() => deleteOverride(override)}
                      className="mt-3 inline-flex items-center gap-1 text-xs font-bold text-rose-600 transition hover:text-rose-800"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                      Delete card
                    </button>
                  </div>
                ))
              ) : (
                <div className="rounded-xl bg-[#F8FAFC] p-4 text-sm font-semibold text-[#7B879C]">
                  No manual overrides yet.
                </div>
              )}
            </div>
          </aside>
        </div>
      </section>
    </main>
  );
}
