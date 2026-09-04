"use client";

import { useEffect, useMemo, useState } from "react";
import {
  Activity,
  BarChart3,
  Database,
  RefreshCw,
  Search,
  Server,
  Table2,
} from "lucide-react";
import QuantModuleHeader from "@/components/QuantModuleHeader";

type Summary = {
  status: string;
  latest_ts: string | null;
  minute: { min_date: string | null; max_date: string | null; dates: number; symbols: number; rows: number };
  daily: { min_date: string | null; max_date: string | null; dates: number; symbols: number; rows: number };
};

type LatestRow = {
  symbol: string;
  datetime: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  amount: number;
};

function number(value: number | null | undefined) {
  if (value == null || Number.isNaN(value)) {
    return "-";
  }
  return new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 }).format(value);
}

function price(value: number | null | undefined) {
  if (value == null || Number.isNaN(value)) {
    return "-";
  }
  return value.toFixed(value > 100 ? 2 : 3);
}

async function fetchJson<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, { ...init, cache: "no-store" });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export default function AShareDataDashboard() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [latest, setLatest] = useState<LatestRow[]>([]);
  const [query, setQuery] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const filtered = useMemo(() => {
    const needle = query.trim().toUpperCase();
    if (!needle) {
      return latest;
    }
    return latest.filter((row) => row.symbol.includes(needle));
  }, [latest, query]);

  async function load() {
    setLoading(true);
    setError("");
    try {
      const [nextSummary, nextLatest] = await Promise.all([
        fetchJson<Summary>("/api/a-share-data/summary"),
        fetchJson<{ data: LatestRow[] }>("/api/a-share-data/latest?limit=120"),
      ]);
      setSummary(nextSummary);
      setLatest(nextLatest.data);
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "Market data API unavailable.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  const cards = [
    {
      label: "1-Minute Store",
      value: summary ? number(summary.minute.rows) : "-",
      detail: summary ? `${summary.minute.symbols} symbols · ${summary.minute.dates} dates` : "Waiting for ClickHouse",
      icon: Activity,
    },
    {
      label: "Daily Store",
      value: summary ? number(summary.daily.rows) : "-",
      detail: summary ? `${summary.daily.symbols} symbols · ${summary.daily.dates} dates` : "Waiting for ClickHouse",
      icon: BarChart3,
    },
    {
      label: "Latest Minute",
      value: summary?.latest_ts?.slice(0, 16) ?? "-",
      detail: "Asia/Shanghai exchange time",
      icon: Database,
    },
  ];

  return (
    <main className="min-h-screen bg-[#FBFAF7] text-[#111827]">
      <QuantModuleHeader
        title="A-Share Data Panel"
        subtitle="ClickHouse-backed China equity bars for monitoring panels and backtests."
        icon={<Server className="h-5 w-5" />}
        meta={
          <span className="inline-flex h-10 items-center gap-2 border border-[#D7B46A]/50 bg-[#FFFDF8]/8 px-4 text-xs font-black uppercase tracking-[0.16em] text-[#F0D694]">
            <Database className="h-4 w-4" />
            ClickHouse
          </span>
        }
        actions={
          <button
            type="button"
            onClick={() => void load()}
            className="inline-flex h-10 items-center gap-2 bg-[#D7B46A] px-4 text-xs font-black uppercase tracking-[0.16em] text-[#111827] transition hover:bg-[#E5C984]"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </button>
        }
      />

      <section className="mx-auto max-w-[1800px] px-5 py-6 sm:px-8 lg:px-10">
        {error ? (
          <div className="mb-5 border border-rose-200 bg-rose-50 px-4 py-3 text-sm font-semibold text-rose-700">
            {error}
          </div>
        ) : null}

        <div className="grid gap-4 lg:grid-cols-3">
          {cards.map((card) => {
            const Icon = card.icon;
            return (
              <article
                key={card.label}
                className="border border-[#E6DDCD] bg-[#FFFDF8]/90 p-5 shadow-[0_18px_44px_rgba(78,56,21,0.08)]"
              >
                <div className="flex items-center justify-between gap-4">
                  <div className="text-xs font-black uppercase tracking-[0.18em] text-[#8A6A2F]">{card.label}</div>
                  <span className="inline-flex h-10 w-10 items-center justify-center bg-[#111827] text-[#D7B46A]">
                    <Icon className="h-5 w-5" />
                  </span>
                </div>
                <div className="mt-5 text-3xl font-black text-[#111827]">{card.value}</div>
                <div className="mt-2 text-sm font-semibold text-[#5B6472]">{card.detail}</div>
              </article>
            );
          })}
        </div>

        <section className="mt-5 border border-[#E6DDCD] bg-[#FFFDF8]/90 shadow-[0_18px_44px_rgba(78,56,21,0.08)]">
          <div className="flex flex-col gap-4 border-b border-[#E6DDCD] p-5 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <div className="inline-flex items-center gap-2 text-xs font-black uppercase tracking-[0.18em] text-[#8A6A2F]">
                <Table2 className="h-4 w-4" />
                Latest A-Share Minute Snapshot
              </div>
              <h2 className="mt-2 text-2xl font-black text-[#111827]">Top turnover symbols</h2>
            </div>
            <label className="relative block w-full lg:w-[360px]">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[#8A6A2F]" />
              <input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Filter symbol, e.g. 600519.SH"
                className="h-11 w-full border border-[#E6DDCD] bg-[#FBFAF7] pl-10 pr-3 text-sm font-semibold outline-none transition focus:border-[#D7B46A] focus:ring-2 focus:ring-[#D7B46A]/25"
              />
            </label>
          </div>

          <div className="overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead className="bg-[#F8F1E3] text-xs font-black uppercase tracking-[0.12em] text-[#8A6A2F]">
                <tr>
                  <th className="px-5 py-3">Symbol</th>
                  <th className="px-5 py-3">Time</th>
                  <th className="px-5 py-3 text-right">Open</th>
                  <th className="px-5 py-3 text-right">High</th>
                  <th className="px-5 py-3 text-right">Low</th>
                  <th className="px-5 py-3 text-right">Close</th>
                  <th className="px-5 py-3 text-right">Volume</th>
                  <th className="px-5 py-3 text-right">Amount</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#E6DDCD]">
                {filtered.map((row) => (
                  <tr key={row.symbol} className="hover:bg-[#FBFAF7]">
                    <td className="px-5 py-3 font-black text-[#111827]">{row.symbol}</td>
                    <td className="px-5 py-3 font-semibold text-[#5B6472]">{row.datetime}</td>
                    <td className="px-5 py-3 text-right font-semibold">{price(row.open)}</td>
                    <td className="px-5 py-3 text-right font-semibold text-rose-700">{price(row.high)}</td>
                    <td className="px-5 py-3 text-right font-semibold text-emerald-700">{price(row.low)}</td>
                    <td className="px-5 py-3 text-right font-black">{price(row.close)}</td>
                    <td className="px-5 py-3 text-right font-semibold text-[#5B6472]">{number(row.volume)}</td>
                    <td className="px-5 py-3 text-right font-semibold text-[#5B6472]">{number(row.amount)}</td>
                  </tr>
                ))}
                {!filtered.length ? (
                  <tr>
                    <td colSpan={8} className="px-5 py-12 text-center text-sm font-semibold text-[#7B879C]">
                      {loading ? "Loading ClickHouse snapshot..." : "No rows returned."}
                    </td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </div>
        </section>
      </section>
    </main>
  );
}
