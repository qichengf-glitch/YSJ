"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  BarChart3,
  Clock3,
  DatabaseZap,
  Filter,
  LineChart,
  RefreshCw,
  Search,
  Signal,
  TrendingDown,
  TrendingUp,
  Users,
} from "lucide-react";

type BucketKey = "all" | "rates_usd" | "geo_commodities";

type AssetImpact = {
  assets?: string[];
  bias?: Record<string, string>;
  reason?: string;
};

type PredictionMarket = {
  condition_id: string;
  bucket: string;
  bucket_label: string;
  bucket_subtitle?: string;
  event_title?: string;
  question: string;
  prob_pct: number | null;
  change_7d_pp: number | null;
  change_1d_pp: number | null;
  change_1mo_pp: number | null;
  bid_pct: number | null;
  ask_pct: number | null;
  spread_pp: number | null;
  volume_7d: number | null;
  volume_24h: number | null;
  volume_spike_ratio: number | null;
  volume_10d_avg?: number | null;
  volume_baseline_days?: number | null;
  volume_baseline_source?: string;
  liquidity: number | null;
  signal_type: string;
  signal_score: number | null;
  asset_impact?: AssetImpact;
  fetched_at?: string;
  history?: Array<{ time: string; price: number; prob_pct: number }>;
  whale_holders?: WhaleHolder[];
};

type WhaleHolder = {
  name: string;
  address: string;
  outcome: string;
  value: number;
  yes_value: number;
  no_value: number;
  win_rate: number;
  days_held_label?: string;
  max_delta_24h?: number | null;
  max_delta_10d?: number | null;
};

type Overview = {
  fetched_at?: string | null;
  market_count: number;
  bucket_summary: Array<{
    bucket: string;
    label: string;
    subtitle: string;
    market_count: number;
    volume_sum: number;
    avg_change_pp: number;
    weighted_change_pp: number;
  }>;
  top_movers_up: PredictionMarket[];
  top_movers_down: PredictionMarket[];
  volume_leaders: PredictionMarket[];
};

type WhaleDaily = {
  events_traded_24h: Array<{
    condition_id: string;
    bucket: string;
    event_title?: string;
    question: string;
    volume_24h?: number | null;
    volume_spike_ratio?: number | null;
    volume_10d_avg?: number | null;
    volume_baseline_source?: string;
  }>;
  top_traders_24h: Array<{
    name: string;
    address: string;
    condition_id: string;
    question: string;
    event_title?: string;
    bucket: string;
    outcome: string;
    value: number;
    delta_24h?: number | null;
    max_delta_10d?: number | null;
    win_rate: number;
  }>;
};

type DashboardState = {
  overview: Overview | null;
  markets: PredictionMarket[];
  whales: WhaleDaily | null;
};

const emptyState: DashboardState = {
  overview: null,
  markets: [],
  whales: null,
};

function pct(value: number | null | undefined, digits = 1) {
  if (value == null || Number.isNaN(value)) {
    return "-";
  }
  return `${value.toFixed(digits)}%`;
}

function signedPct(value: number | null | undefined, digits = 1) {
  if (value == null || Number.isNaN(value)) {
    return "-";
  }
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(digits)} pp`;
}

function money(value: number | null | undefined) {
  if (value == null || Number.isNaN(value)) {
    return "-";
  }
  if (Math.abs(value) >= 1_000_000) {
    return `$${(value / 1_000_000).toFixed(1)}M`;
  }
  if (Math.abs(value) >= 1_000) {
    return `$${(value / 1_000).toFixed(0)}K`;
  }
  return `$${value.toFixed(0)}`;
}

function compactDate(value?: string | null) {
  if (!value) {
    return "No sync yet";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function changeTone(value: number | null | undefined) {
  if (value == null || Math.abs(value) < 0.01) {
    return "text-[#7B879C]";
  }
  return value > 0 ? "text-emerald-700" : "text-rose-700";
}

function bucketTone(bucket: string) {
  if (bucket === "rates_usd") {
    return "border-[#D6E4FF] bg-[#EEF2FF] text-[#273B9A]";
  }
  if (bucket === "geo_commodities") {
    return "border-amber-200 bg-amber-50 text-amber-700";
  }
  return "border-[#E7ECF5] bg-[#F8FAFC] text-[#5B6780]";
}

function signalTone(signal: string) {
  if (signal.includes("重定价") || signal.includes("反转")) {
    return "bg-[#EEF2FF] text-[#273B9A]";
  }
  if (signal.includes("拥挤")) {
    return "bg-amber-50 text-amber-700";
  }
  if (signal.includes("低")) {
    return "bg-[#F8FAFC] text-[#7B879C]";
  }
  return "bg-emerald-50 text-emerald-700";
}

async function fetchJson<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    ...init,
    cache: "no-store",
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

function MiniHistory({ market }: { market: PredictionMarket }) {
  const points = market.history ?? [];
  if (points.length < 2) {
    return <div className="h-16 rounded-xl border border-dashed border-[#E7ECF5] bg-[#F8FAFC]" />;
  }
  const width = 240;
  const height = 64;
  const values = points.map((point) => point.prob_pct ?? point.price * 100);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = Math.max(1, max - min);
  const path = values
    .map((value, index) => {
      const x = (index / Math.max(1, values.length - 1)) * width;
      const y = height - ((value - min) / span) * (height - 8) - 4;
      return `${index === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="h-16 w-full">
      <path d={path} fill="none" stroke="#4F63F6" strokeWidth="3" strokeLinecap="round" />
    </svg>
  );
}

export default function PredictionMarketDashboard() {
  const [state, setState] = useState<DashboardState>(emptyState);
  const [query, setQuery] = useState("");
  const [bucket, setBucket] = useState<BucketKey>("all");
  const [sortMode, setSortMode] = useState<"volume" | "move" | "signal" | "spike">("volume");
  const [selectedId, setSelectedId] = useState("");
  const [selectedDetail, setSelectedDetail] = useState<PredictionMarket | null>(null);
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [error, setError] = useState("");

  async function loadData(nextBucket = bucket) {
    setLoading(true);
    setError("");
    try {
      const [overview, markets, whales] = await Promise.all([
        fetchJson<Overview>("/api/prediction-markets/overview"),
        fetchJson<{ data: PredictionMarket[] }>(
          `/api/prediction-markets/markets?bucket=${nextBucket}&limit=500`
        ),
        fetchJson<WhaleDaily>(`/api/prediction-markets/whales/daily?bucket=${nextBucket}`).catch(
          () => null
        ),
      ]);
      const nextState = {
        overview,
        markets: markets.data ?? [],
        whales,
      };
      setState(nextState);
      setSelectedId((current) => current || nextState.markets[0]?.condition_id || "");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load Prediction Market data.");
    } finally {
      setLoading(false);
    }
  }

  async function syncData() {
    setSyncing(true);
    setError("");
    try {
      await fetchJson("/api/prediction-markets/sync?min_prob=0.10&min_volume=10000&max_pages=15&fetch_history=true", {
        method: "POST",
      });
      await fetchJson("/api/prediction-markets/sync-whales", {
        method: "POST",
      }).catch(() => null);
      await loadData(bucket);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Prediction Market sync failed.");
    } finally {
      setSyncing(false);
    }
  }

  useEffect(() => {
    loadData(bucket);
    const timer = window.setInterval(() => loadData(bucket), 5 * 60 * 1000);
    return () => window.clearInterval(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [bucket]);

  useEffect(() => {
    if (!selectedId) {
      setSelectedDetail(null);
      return;
    }
    setDetailLoading(true);
    fetchJson<PredictionMarket>(`/api/prediction-markets/market/${encodeURIComponent(selectedId)}`)
      .then(setSelectedDetail)
      .catch(() => {
        setSelectedDetail(state.markets.find((market) => market.condition_id === selectedId) ?? null);
      })
      .finally(() => setDetailLoading(false));
  }, [selectedId, state.markets]);

  const filteredMarkets = useMemo(() => {
    const q = query.trim().toLowerCase();
    const rows = state.markets.filter((market) => {
      if (!q) {
        return true;
      }
      return `${market.event_title ?? ""} ${market.question} ${market.bucket_label}`
        .toLowerCase()
        .includes(q);
    });
    const sorted = [...rows];
    if (sortMode === "move") {
      sorted.sort(
        (a, b) => Math.abs(b.change_7d_pp ?? 0) - Math.abs(a.change_7d_pp ?? 0)
      );
    } else if (sortMode === "signal") {
      sorted.sort((a, b) => (b.signal_score ?? 0) - (a.signal_score ?? 0));
    } else if (sortMode === "spike") {
      sorted.sort((a, b) => (b.volume_spike_ratio ?? 0) - (a.volume_spike_ratio ?? 0));
    } else {
      sorted.sort((a, b) => (b.volume_7d ?? 0) - (a.volume_7d ?? 0));
    }
    return sorted;
  }, [query, sortMode, state.markets]);

  const selected =
    selectedDetail ??
    state.markets.find((market) => market.condition_id === selectedId) ??
    filteredMarkets[0] ??
    null;

  const overview = state.overview;
  const topUp = overview?.top_movers_up?.[0];
  const topDown = overview?.top_movers_down?.[0];
  const topSpike = overview?.volume_leaders?.[0];
  const spikeWatchMarkets =
    overview?.volume_leaders?.length ? overview.volume_leaders : topSpike ? [topSpike] : [];

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
              Quant Monitor
            </Link>
            <div className="inline-flex items-center gap-2 rounded-full border border-[#E7ECF5] bg-white px-4 py-2 text-xs font-bold uppercase tracking-[0.18em] text-[#4F63F6]">
              <Signal className="h-3.5 w-3.5" />
              Polymarket Macro Feed
            </div>
            <h1 className="mt-4 text-3xl font-black leading-tight text-[#18233A] sm:text-4xl">
              Prediction Market
            </h1>
          </div>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <div className="rounded-xl border border-[#E7ECF5] bg-white px-4 py-3">
              <div className="text-[10px] font-bold uppercase tracking-[0.14em] text-[#9AA5BA]">Markets</div>
              <div className="mt-1 text-xl font-black">{overview?.market_count ?? "-"}</div>
            </div>
            <div className="rounded-xl border border-[#E7ECF5] bg-white px-4 py-3">
              <div className="text-[10px] font-bold uppercase tracking-[0.14em] text-[#9AA5BA]">Top Up</div>
              <div className={`mt-1 text-xl font-black ${changeTone(topUp?.change_7d_pp)}`}>
                {signedPct(topUp?.change_7d_pp)}
              </div>
            </div>
            <div className="rounded-xl border border-[#E7ECF5] bg-white px-4 py-3">
              <div className="text-[10px] font-bold uppercase tracking-[0.14em] text-[#9AA5BA]">Top Down</div>
              <div className={`mt-1 text-xl font-black ${changeTone(topDown?.change_7d_pp)}`}>
                {signedPct(topDown?.change_7d_pp)}
              </div>
            </div>
            <div className="rounded-xl border border-[#E7ECF5] bg-white px-4 py-3">
              <div className="flex items-center gap-1 text-[10px] font-bold uppercase tracking-[0.14em] text-[#9AA5BA]">
                <Clock3 className="h-3 w-3" />
                Synced
              </div>
              <div className="mt-1 text-sm font-black">{compactDate(overview?.fetched_at)}</div>
            </div>
          </div>
        </div>

        <div className="mt-5 grid grid-cols-1 gap-4 lg:grid-cols-3">
          {(overview?.bucket_summary ?? []).map((item) => (
            <button
              key={item.bucket}
              type="button"
              onClick={() => setBucket(item.bucket as BucketKey)}
              className={`rounded-2xl border bg-white p-4 text-left transition hover:border-[#A8B2FF] ${
                bucket === item.bucket ? "border-[#A8B2FF] shadow-[0_16px_36px_rgba(79,99,246,0.10)]" : "border-[#E7ECF5]"
              }`}
            >
              <div className="flex items-center justify-between gap-3">
                <span className={`rounded-full border px-2.5 py-1 text-xs font-black ${bucketTone(item.bucket)}`}>
                  {item.label}
                </span>
                <span className="text-xs font-bold text-[#7B879C]">{item.market_count} markets</span>
              </div>
              <p className="mt-3 min-h-10 text-sm font-semibold leading-5 text-[#5B6780]">{item.subtitle}</p>
              <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
                <div>
                  <div className="text-[10px] font-bold uppercase tracking-[0.14em] text-[#9AA5BA]">7D Volume</div>
                  <div className="mt-1 text-lg font-black">{money(item.volume_sum)}</div>
                </div>
                <div>
                  <div className="text-[10px] font-bold uppercase tracking-[0.14em] text-[#9AA5BA]">Weighted Move</div>
                  <div className={`mt-1 text-lg font-black ${changeTone(item.weighted_change_pp)}`}>
                    {signedPct(item.weighted_change_pp)}
                  </div>
                </div>
              </div>
            </button>
          ))}
          <button
            type="button"
            onClick={() => setBucket("all")}
            className={`rounded-2xl border bg-white p-4 text-left transition hover:border-[#A8B2FF] ${
              bucket === "all" ? "border-[#A8B2FF] shadow-[0_16px_36px_rgba(79,99,246,0.10)]" : "border-[#E7ECF5]"
            }`}
          >
            <div className="flex items-center justify-between gap-3">
              <span className="rounded-full border border-[#E7ECF5] bg-[#F8FAFC] px-2.5 py-1 text-xs font-black text-[#5B6780]">
                All Macro
              </span>
              <BarChart3 className="h-4 w-4 text-[#4F63F6]" />
            </div>
            <p className="mt-3 min-h-10 text-sm font-semibold leading-5 text-[#5B6780]">
              Combined rates, USD, geopolitical, commodity, and macro risk markets.
            </p>
            <div className="mt-4 text-lg font-black">{overview?.market_count ?? 0} active markets</div>
          </button>
        </div>

        {error ? (
          <div className="mt-5 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm font-semibold text-rose-700">
            {error}
          </div>
        ) : null}

        <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,1fr)_390px]">
          <section className="min-w-0 rounded-2xl border border-[#E7ECF5] bg-white shadow-[0_18px_45px_rgba(39,59,154,0.08)]">
            <div className="grid grid-cols-1 gap-3 border-b border-[#E7ECF5] p-4 md:grid-cols-[minmax(180px,1fr)_180px_160px_150px]">
              <label className="relative block">
                <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[#9AA5BA]" />
                <input
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  placeholder="Search event or question"
                  className="h-11 w-full rounded-xl border border-[#E7ECF5] bg-[#F8FAFC] pl-10 pr-3 text-sm font-semibold outline-none transition focus:border-[#A8B2FF] focus:ring-2 focus:ring-[#A8B2FF]/25"
                />
              </label>
              <label className="relative block">
                <Filter className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[#9AA5BA]" />
                <select
                  value={bucket}
                  onChange={(event) => setBucket(event.target.value as BucketKey)}
                  className="h-11 w-full rounded-xl border border-[#E7ECF5] bg-[#F8FAFC] pl-10 pr-3 text-sm font-semibold outline-none transition focus:border-[#A8B2FF] focus:ring-2 focus:ring-[#A8B2FF]/25"
                >
                  <option value="all">All buckets</option>
                  <option value="rates_usd">Rates / USD</option>
                  <option value="geo_commodities">Geo / Commodities</option>
                </select>
              </label>
              <label className="relative block">
                <LineChart className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[#9AA5BA]" />
                <select
                  value={sortMode}
                  onChange={(event) => setSortMode(event.target.value as "volume" | "move" | "signal" | "spike")}
                  className="h-11 w-full rounded-xl border border-[#E7ECF5] bg-[#F8FAFC] pl-10 pr-3 text-sm font-semibold outline-none transition focus:border-[#A8B2FF] focus:ring-2 focus:ring-[#A8B2FF]/25"
                >
                  <option value="volume">7D volume</option>
                  <option value="move">7D move</option>
                  <option value="signal">Signal score</option>
                  <option value="spike">Volume spike</option>
                </select>
              </label>
              <button
                type="button"
                onClick={syncData}
                disabled={syncing}
                className="inline-flex h-11 items-center justify-center gap-2 rounded-xl bg-[#18233A] px-4 text-sm font-black text-white transition hover:bg-[#273B9A] disabled:cursor-not-allowed disabled:opacity-60"
              >
                <RefreshCw className={`h-4 w-4 ${syncing ? "animate-spin" : ""}`} />
                {syncing ? "Syncing" : "Sync"}
              </button>
            </div>

            <div className="overflow-x-auto">
              <table className="min-w-[980px] w-full border-collapse text-left text-sm">
                <thead>
                  <tr className="border-b border-[#E7ECF5] bg-[#F8FAFC] text-[10px] uppercase tracking-[0.14em] text-[#7B879C]">
                    <th className="w-[38%] px-4 py-3">Market</th>
                    <th className="px-3 py-3">Bucket</th>
                    <th className="px-3 py-3 text-right">Probability</th>
                    <th className="px-3 py-3 text-right">7D Move</th>
                    <th className="px-3 py-3 text-right">24H Vol</th>
                    <th className="px-3 py-3 text-right">Signal</th>
                  </tr>
                </thead>
                <tbody>
                  {loading ? (
                    <tr>
                      <td colSpan={6} className="px-4 py-8 text-center text-sm font-semibold text-[#7B879C]">
                        Loading Prediction Market data...
                      </td>
                    </tr>
                  ) : filteredMarkets.length ? (
                    filteredMarkets.map((market) => (
                      <tr
                        key={market.condition_id}
                        onClick={() => setSelectedId(market.condition_id)}
                        className={`cursor-pointer border-b border-[#EEF2F7] transition hover:bg-[#F8FAFC] ${
                          selected?.condition_id === market.condition_id ? "bg-[#EEF2FF]" : ""
                        }`}
                      >
                        <td className="px-4 py-3">
                          <div className="line-clamp-2 font-black text-[#18233A]">{market.question}</div>
                          <div className="mt-1 line-clamp-1 text-xs font-semibold text-[#7B879C]">
                            {market.event_title || "Polymarket"}
                          </div>
                        </td>
                        <td className="px-3 py-3">
                          <span className={`inline-flex rounded-full border px-2 py-1 text-[11px] font-black ${bucketTone(market.bucket)}`}>
                            {market.bucket_label}
                          </span>
                        </td>
                        <td className="px-3 py-3 text-right text-lg font-black">{pct(market.prob_pct)}</td>
                        <td className={`px-3 py-3 text-right font-black ${changeTone(market.change_7d_pp)}`}>
                          {signedPct(market.change_7d_pp)}
                        </td>
                        <td className="px-3 py-3 text-right">
                          <div className="font-black">{money(market.volume_24h)}</div>
                          <div className="text-[11px] font-semibold text-[#7B879C]">
                            {market.volume_spike_ratio ? `${market.volume_spike_ratio.toFixed(1)}x` : "no spike"}
                          </div>
                        </td>
                        <td className="px-3 py-3 text-right">
                          <span className={`inline-flex rounded-full px-2 py-1 text-[11px] font-black ${signalTone(market.signal_type)}`}>
                            {market.signal_type || "观察"}
                          </span>
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={6} className="px-4 py-8 text-center text-sm font-semibold text-[#7B879C]">
                        No matching markets. Run Sync after the backend starts if this is a fresh deploy.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </section>

          <aside className="rounded-2xl border border-[#E7ECF5] bg-white p-4 shadow-[0_18px_45px_rgba(39,59,154,0.08)]">
            {selected ? (
              <div>
                <div className="flex items-start justify-between gap-3 border-b border-[#E7ECF5] pb-4">
                  <div>
                    <div className="text-[10px] font-bold uppercase tracking-[0.16em] text-[#9AA5BA]">Selected</div>
                    <h2 className="mt-2 text-lg font-black leading-6">{selected.question}</h2>
                  </div>
                  {detailLoading ? <RefreshCw className="h-4 w-4 animate-spin text-[#4F63F6]" /> : null}
                </div>

                <div className="mt-4 grid grid-cols-2 gap-3">
                  <div className="rounded-xl border border-[#E7ECF5] bg-[#F8FAFC] p-3">
                    <div className="text-[10px] font-bold uppercase tracking-[0.14em] text-[#9AA5BA]">Now</div>
                    <div className="mt-1 text-2xl font-black">{pct(selected.prob_pct)}</div>
                  </div>
                  <div className="rounded-xl border border-[#E7ECF5] bg-[#F8FAFC] p-3">
                    <div className="text-[10px] font-bold uppercase tracking-[0.14em] text-[#9AA5BA]">7D</div>
                    <div className={`mt-1 text-2xl font-black ${changeTone(selected.change_7d_pp)}`}>
                      {signedPct(selected.change_7d_pp)}
                    </div>
                  </div>
                  <div className="rounded-xl border border-[#E7ECF5] bg-[#F8FAFC] p-3">
                    <div className="text-[10px] font-bold uppercase tracking-[0.14em] text-[#9AA5BA]">Bid / Ask</div>
                    <div className="mt-1 text-lg font-black">
                      {pct(selected.bid_pct)} / {pct(selected.ask_pct)}
                    </div>
                  </div>
                  <div className="rounded-xl border border-[#E7ECF5] bg-[#F8FAFC] p-3">
                    <div className="text-[10px] font-bold uppercase tracking-[0.14em] text-[#9AA5BA]">Liquidity</div>
                    <div className="mt-1 text-lg font-black">{money(selected.liquidity)}</div>
                  </div>
                </div>

                <div className="mt-4 rounded-xl border border-[#E7ECF5] bg-white p-3">
                  <div className="mb-2 flex items-center justify-between">
                    <div className="flex items-center gap-2 text-sm font-black">
                      <LineChart className="h-4 w-4 text-[#4F63F6]" />
                      Probability History
                    </div>
                    <div className="text-xs font-bold text-[#7B879C]">7D</div>
                  </div>
                  <MiniHistory market={selected} />
                </div>

                <div className="mt-4 rounded-xl border border-[#E7ECF5] bg-white p-3">
                  <div className="flex items-center gap-2 text-sm font-black">
                    <DatabaseZap className="h-4 w-4 text-[#4F63F6]" />
                    Asset Readthrough
                  </div>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {(selected.asset_impact?.assets ?? []).map((asset) => (
                      <span key={asset} className="rounded-full bg-[#F8FAFC] px-2.5 py-1 text-xs font-black text-[#5B6780]">
                        {asset}: {selected.asset_impact?.bias?.[asset] ?? "观察"}
                      </span>
                    ))}
                  </div>
                  <p className="mt-3 text-sm font-semibold leading-6 text-[#5B6780]">
                    {selected.asset_impact?.reason ?? "No asset impact note available."}
                  </p>
                </div>

                <div className="mt-4 rounded-xl border border-[#E7ECF5] bg-white p-3">
                  <div className="mb-3 flex items-center justify-between">
                    <div className="flex items-center gap-2 text-sm font-black">
                      <Users className="h-4 w-4 text-[#4F63F6]" />
                      Tracked Holders
                    </div>
                    <span className="text-xs font-bold text-[#7B879C]">
                      {(selected.whale_holders ?? []).length || 0}
                    </span>
                  </div>
                  <div className="space-y-2">
                    {(selected.whale_holders ?? []).length ? (
                      selected.whale_holders?.map((holder) => (
                        <div key={`${holder.address}-${holder.outcome}`} className="rounded-lg bg-[#F8FAFC] p-3">
                          <div className="flex items-center justify-between gap-3">
                            <div className="min-w-0">
                              <div className="truncate text-sm font-black">{holder.name}</div>
                              <div className="text-xs font-semibold text-[#7B879C]">{holder.outcome} · {holder.days_held_label ?? "-"}</div>
                            </div>
                            <div className="text-right">
                              <div className="text-sm font-black">{money(holder.value)}</div>
                              <div className="text-xs font-semibold text-[#7B879C]">{pct(holder.win_rate, 0)} win</div>
                            </div>
                          </div>
                        </div>
                      ))
                    ) : (
                      <div className="rounded-lg bg-[#F8FAFC] p-3 text-sm font-semibold text-[#7B879C]">
                        No tracked holder snapshot for this market yet.
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ) : (
              <div className="rounded-xl border border-dashed border-[#E7ECF5] p-5 text-sm font-semibold text-[#7B879C]">
                Select a market to inspect probability, impact, and holder detail.
              </div>
            )}
          </aside>
        </div>

        <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-3">
          <section className="rounded-2xl border border-[#E7ECF5] bg-white p-4">
            <div className="flex items-center gap-2 text-sm font-black">
              <TrendingUp className="h-4 w-4 text-emerald-700" />
              Largest Up Repricing
            </div>
            <div className="mt-3 space-y-3">
              {(overview?.top_movers_up ?? []).map((market) => (
                <button
                  key={market.condition_id}
                  type="button"
                  onClick={() => setSelectedId(market.condition_id)}
                  className="w-full rounded-xl bg-[#F8FAFC] p-3 text-left transition hover:bg-[#EEF2FF]"
                >
                  <div className="line-clamp-2 text-sm font-black">{market.question}</div>
                  <div className="mt-2 text-sm font-black text-emerald-700">{signedPct(market.change_7d_pp)}</div>
                </button>
              ))}
            </div>
          </section>
          <section className="rounded-2xl border border-[#E7ECF5] bg-white p-4">
            <div className="flex items-center gap-2 text-sm font-black">
              <TrendingDown className="h-4 w-4 text-rose-700" />
              Largest Down Repricing
            </div>
            <div className="mt-3 space-y-3">
              {(overview?.top_movers_down ?? []).map((market) => (
                <button
                  key={market.condition_id}
                  type="button"
                  onClick={() => setSelectedId(market.condition_id)}
                  className="w-full rounded-xl bg-[#F8FAFC] p-3 text-left transition hover:bg-[#EEF2FF]"
                >
                  <div className="line-clamp-2 text-sm font-black">{market.question}</div>
                  <div className="mt-2 text-sm font-black text-rose-700">{signedPct(market.change_7d_pp)}</div>
                </button>
              ))}
            </div>
          </section>
          <section className="rounded-2xl border border-[#E7ECF5] bg-white p-4">
            <div className="flex items-center gap-2 text-sm font-black">
              <Signal className="h-4 w-4 text-[#4F63F6]" />
              Volume Spike Watch
            </div>
            <div className="mt-3 space-y-3">
              {spikeWatchMarkets.slice(0, 3).map((market) => (
                <button
                  key={market.condition_id}
                  type="button"
                  onClick={() => setSelectedId(market.condition_id)}
                  className="w-full rounded-xl bg-[#F8FAFC] p-3 text-left transition hover:bg-[#EEF2FF]"
                >
                  <div className="line-clamp-2 text-sm font-black">{market.question}</div>
                  <div className="mt-2 text-sm font-black text-[#273B9A]">
                    {market.volume_spike_ratio ? `${market.volume_spike_ratio.toFixed(1)}x` : "No local baseline"} · {money(market.volume_24h)}
                  </div>
                </button>
              ))}
            </div>
          </section>
        </div>

        {state.whales?.top_traders_24h?.length ? (
          <section className="mt-4 rounded-2xl border border-[#E7ECF5] bg-white p-4">
            <div className="flex items-center gap-2 text-sm font-black">
              <Users className="h-4 w-4 text-[#4F63F6]" />
              Tracked Wallet Activity
            </div>
            <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-3">
              {state.whales.top_traders_24h.map((trader) => (
                <button
                  key={`${trader.address}-${trader.condition_id}`}
                  type="button"
                  onClick={() => setSelectedId(trader.condition_id)}
                  className="rounded-xl bg-[#F8FAFC] p-3 text-left transition hover:bg-[#EEF2FF]"
                >
                  <div className="flex items-center justify-between gap-3">
                    <div className="min-w-0">
                      <div className="truncate text-sm font-black">{trader.name}</div>
                      <div className="text-xs font-semibold text-[#7B879C]">{trader.outcome} · {pct(trader.win_rate, 0)} win</div>
                    </div>
                    <div className="text-right text-sm font-black">{money(trader.value)}</div>
                  </div>
                  <div className="mt-2 line-clamp-2 text-xs font-semibold leading-5 text-[#5B6780]">
                    {trader.question}
                  </div>
                </button>
              ))}
            </div>
          </section>
        ) : null}
      </section>
    </main>
  );
}
