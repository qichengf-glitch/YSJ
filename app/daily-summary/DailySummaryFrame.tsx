"use client";

import { useEffect, useMemo, useState } from "react";
import {
  Activity,
  CalendarClock,
  Database,
  Globe2,
  Landmark,
  RefreshCw,
  ShieldAlert,
  TrendingUp,
} from "lucide-react";
import QuantModuleHeader from "@/components/QuantModuleHeader";
import { useLanguage } from "@/contexts/LanguageContext";

type Digest = {
  overall?: string;
  summary?: string;
  indices?: Array<{ name?: string; change?: string; emoji?: string }>;
  sectors?: { strong?: string[]; weak?: string[] };
  upgrades?: Array<{ ticker?: string; firm?: string; from?: string; to?: string; change?: string }>;
  downgrades?: Array<{ ticker?: string; firm?: string; from?: string; to?: string; change?: string }>;
  policy_news?: Array<{ institution?: string; speaker?: string; signal?: string; content?: string }>;
  sentiment_signals?: Array<{ commodity?: string; score?: number; direction?: string; event?: string }>;
  supply_demand_signals?: Array<{ commodity?: string; score?: number; direction?: string; event?: string }>;
  key_events?: string[];
  key_points?: string[];
  strategy?: string[];
};

type SummaryResponse = {
  status: string;
  summary_available?: boolean;
  date?: string;
  generated_at?: string | null;
  summaries?: Record<string, Digest | null>;
  counts?: Record<string, number>;
  message?: string;
};

type LiveRecord = {
  id?: string;
  time?: string;
  content?: string;
  market?: string;
  important?: number;
  claude_score?: number | null;
  claude_confidence?: number | null;
  claude_reasoning?: string;
  claude_gate_triggered?: string | null;
};

type LiveResponse = {
  status: string;
  server_time?: string;
  data?: Record<string, LiveRecord[]>;
  counts?: Record<string, number>;
};

type LiveChannelKey = "a_share" | "us_stock" | "forex" | "commodity";

const channelMeta = {
  a_share: {
    titleZh: "A股",
    titleEn: "A-share",
    subtitleZh: "关卡A行情复盘",
    subtitleEn: "Gate A market recap",
    icon: Landmark,
    tone: "border-[#E8C8B0] bg-[#FFF9F4] text-[#934B20]",
  },
  us: {
    titleZh: "美股",
    titleEn: "US Stocks",
    subtitleZh: "分析师评级变动",
    subtitleEn: "Analyst rating changes",
    icon: TrendingUp,
    tone: "border-[#C9D8F2] bg-[#F6F8FF] text-[#2F4B91]",
  },
  forex: {
    titleZh: "外汇",
    titleEn: "FX",
    subtitleZh: "政策类新闻",
    subtitleEn: "Policy signals",
    icon: Globe2,
    tone: "border-[#C9E1DB] bg-[#F4FBF8] text-[#266456]",
  },
  commodity: {
    titleZh: "商品",
    titleEn: "Commodities",
    subtitleZh: "舆情与供需",
    subtitleEn: "Sentiment and supply/demand",
    icon: Activity,
    tone: "border-[#E6DDCD] bg-[#FFFDF8] text-[#6A552B]",
  },
};

const channels = ["a_share", "us", "forex", "commodity"] as const;

function compactDate(value?: string | null) {
  if (!value) {
    return "-";
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

function overallLabel(value: string | undefined, isChinese: boolean) {
  const labels: Record<string, [string, string, string]> = {
    bullish: ["偏多", "Bullish", "bg-rose-50 text-rose-700"],
    bearish: ["偏空", "Bearish", "bg-emerald-50 text-emerald-700"],
    neutral: ["中性", "Neutral", "bg-slate-100 text-slate-600"],
    mixed: ["分化", "Mixed", "bg-amber-50 text-amber-700"],
    dollar_strong: ["美元强", "Dollar strong", "bg-rose-50 text-rose-700"],
    dollar_weak: ["美元弱", "Dollar weak", "bg-emerald-50 text-emerald-700"],
  };
  const item = labels[value ?? ""] ?? ["待生成", "Pending", "bg-[#F8FAFC] text-[#7B879C]"];
  return { label: isChinese ? item[0] : item[1], className: item[2] };
}

function liveLabel(isChinese: boolean) {
  return {
    label: isChinese ? "实时" : "Live",
    className: "bg-white/80 text-[#5F4820]",
  };
}

function liveKeyForChannel(channel: (typeof channels)[number]): LiveChannelKey {
  return channel === "us" ? "us_stock" : channel;
}

async function fetchJson<T>(url: string): Promise<T> {
  const response = await fetch(url, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json() as Promise<T>;
}

function DigestRows({ digest }: { digest?: Digest | null }) {
  if (!digest) {
    return null;
  }

  const points = digest.key_events ?? digest.key_points ?? [];
  return (
    <div className="mt-4 space-y-3 text-sm leading-6 text-[#364152]">
      {digest.indices?.length ? (
        <div className="flex flex-wrap gap-2">
          {digest.indices.slice(0, 4).map((item) => (
            <span key={`${item.name}-${item.change}`} className="border border-[#E7ECF5] bg-white px-2 py-1">
              {item.name} <strong>{item.change}</strong>
            </span>
          ))}
        </div>
      ) : null}

      {digest.sectors?.strong?.length || digest.sectors?.weak?.length ? (
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
          <div className="bg-white/75 p-3">
            <div className="text-[11px] font-black uppercase tracking-[0.14em] text-rose-700">Strong</div>
            <div className="mt-1">{digest.sectors.strong?.join(" / ") || "-"}</div>
          </div>
          <div className="bg-white/75 p-3">
            <div className="text-[11px] font-black uppercase tracking-[0.14em] text-emerald-700">Weak</div>
            <div className="mt-1">{digest.sectors.weak?.join(" / ") || "-"}</div>
          </div>
        </div>
      ) : null}

      {digest.upgrades?.length || digest.downgrades?.length ? (
        <div className="space-y-2">
          {[...(digest.upgrades ?? []), ...(digest.downgrades ?? [])].slice(0, 4).map((item) => (
            <div key={`${item.ticker}-${item.firm}-${item.change}`} className="border-l-2 border-[#D7B46A] bg-white/75 px-3 py-2">
              <strong>{item.ticker || "-"}</strong> {item.firm || ""} {item.from || ""} to {item.to || ""}{" "}
              <span className="font-semibold text-[#8A6A2F]">{item.change || ""}</span>
            </div>
          ))}
        </div>
      ) : null}

      {digest.policy_news?.length ? (
        <div className="space-y-2">
          {digest.policy_news.slice(0, 4).map((item) => (
            <div key={`${item.institution}-${item.speaker}-${item.content}`} className="bg-white/75 px-3 py-2">
              <strong>{item.institution || "-"}</strong>
              {item.speaker ? ` / ${item.speaker}` : ""}: {item.content}
            </div>
          ))}
        </div>
      ) : null}

      {digest.sentiment_signals?.length || digest.supply_demand_signals?.length ? (
        <div className="space-y-2">
          {[...(digest.sentiment_signals ?? []), ...(digest.supply_demand_signals ?? [])]
            .slice(0, 5)
            .map((item) => (
              <div key={`${item.commodity}-${item.event}`} className="bg-white/75 px-3 py-2">
                <strong>{item.commodity || "-"}</strong>
                {item.score != null ? ` / ${item.score}` : ""}: {item.event}
              </div>
            ))}
        </div>
      ) : null}

      {points.length ? (
        <ol className="space-y-2">
          {points.slice(0, 4).map((point, index) => (
            <li key={point} className="grid grid-cols-[1.5rem_1fr] gap-2">
              <span className="font-black text-[#8A6A2F]">{index + 1}</span>
              <span>{point}</span>
            </li>
          ))}
        </ol>
      ) : null}
    </div>
  );
}

export default function DailySummaryFrame() {
  const { language } = useLanguage();
  const isChinese = language === "zh";
  const [summary, setSummary] = useState<SummaryResponse | null>(null);
  const [live, setLive] = useState<LiveResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function loadData() {
    setError("");
    try {
      const [summaryData, liveData] = await Promise.all([
        fetchJson<SummaryResponse>("/api/daily-summary/summary"),
        fetchJson<LiveResponse>("/api/daily-summary/live?limit=80"),
      ]);
      setSummary(summaryData);
      setLive(liveData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Daily Summary backend unavailable");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
    const timer = window.setInterval(loadData, 30000);
    return () => window.clearInterval(timer);
  }, []);

  const latestRecords = useMemo(() => {
    const rows = [
      ...(live?.data?.a_share ?? []),
      ...(live?.data?.us_stock ?? []),
      ...(live?.data?.forex ?? []),
      ...(live?.data?.commodity ?? []),
    ];
    return rows
      .slice()
      .sort((a, b) => String(b.time ?? "").localeCompare(String(a.time ?? "")))
      .slice(0, 12);
  }, [live]);
  const hasLiveData = latestRecords.length > 0;

  return (
    <div className="flex min-h-screen flex-col bg-[#FBFAF7]">
      <QuantModuleHeader
        backLabel={isChinese ? "量化指标监控" : "Quant Monitor"}
        title={isChinese ? "每日市场日报" : "Daily Summary"}
        subtitle={
          isChinese
            ? "金十实时新闻与跨资产市场日报。"
            : "Jin10 realtime market news and cross-asset daily brief."
        }
        icon={<CalendarClock className="h-5 w-5" />}
        meta={
          <div className="flex flex-wrap items-center gap-2 text-xs font-black uppercase tracking-[0.12em] text-[#8A6A2F]">
            <span className="inline-flex h-9 items-center gap-2 border border-[#E6DDCD] bg-white/70 px-3">
              <Database className="h-4 w-4" />
              {summary?.summary_available
                ? isChinese
                  ? "实时日报"
                  : "Live digest"
                : hasLiveData
                  ? isChinese
                    ? "实时新闻流"
                    : "Live feed"
                  : isChinese
                    ? "等待数据"
                    : "Pending"}
            </span>
            <span className="inline-flex h-9 items-center border border-[#E6DDCD] bg-white/70 px-3">
              {compactDate(summary?.generated_at)}
            </span>
          </div>
        }
        actions={
          <button
            type="button"
            onClick={loadData}
            className="inline-flex h-9 items-center gap-2 bg-[#111827] px-3 text-xs font-black uppercase tracking-[0.12em] text-white transition hover:bg-[#2D3748]"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
            {isChinese ? "刷新" : "Refresh"}
          </button>
        }
      />

      <main className="mx-auto flex w-full max-w-[1800px] flex-1 flex-col gap-5 px-5 py-5 sm:px-8 lg:px-10">
        {error ? (
          <div className="flex items-start gap-3 border border-rose-200 bg-rose-50 p-4 text-sm font-semibold text-rose-800">
            <ShieldAlert className="mt-0.5 h-5 w-5" />
            <span>{error}</span>
          </div>
        ) : null}

        <section className="grid grid-cols-1 gap-4 xl:grid-cols-4">
          {channels.map((channel) => {
            const meta = channelMeta[channel];
            const Icon = meta.icon;
            const digest = summary?.summaries?.[channel];
            const liveRows = live?.data?.[liveKeyForChannel(channel)] ?? [];
            const hasDigest = Boolean(digest?.summary);
            const label = hasDigest
              ? overallLabel(digest?.overall, isChinese)
              : liveRows.length
                ? liveLabel(isChinese)
                : overallLabel(undefined, isChinese);
            const inputCount = (summary?.counts?.[channel] ?? 0) || liveRows.length;
            return (
              <article key={channel} className={`min-h-[360px] border p-5 shadow-[0_14px_34px_rgba(78,56,21,0.07)] ${meta.tone}`}>
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <div className="flex items-center gap-2">
                      <Icon className="h-5 w-5" />
                      <h2 className="text-xl font-black text-[#111827]">
                        {isChinese ? meta.titleZh : meta.titleEn}
                      </h2>
                    </div>
                    <p className="mt-1 text-xs font-black uppercase tracking-[0.14em] opacity-70">
                      {isChinese ? meta.subtitleZh : meta.subtitleEn}
                    </p>
                  </div>
                  <span className={`whitespace-nowrap px-3 py-1 text-xs font-black ${label.className}`}>
                    {label.label}
                  </span>
                </div>

                <div className="mt-5 border-y border-current/10 py-4">
                  <div className="text-2xl font-semibold leading-snug text-[#111827]">
                    {digest?.summary ||
                      liveRows[0]?.content ||
                      (isChinese ? "等待实时数据" : "Waiting for realtime data")}
                  </div>
                  <div className="mt-2 text-xs font-black uppercase tracking-[0.14em] opacity-65">
                    {inputCount.toLocaleString()}{" "}
                    {hasDigest ? (isChinese ? "条日报输入" : "digest inputs") : isChinese ? "条实时新闻" : "live items"}
                  </div>
                </div>

                <DigestRows digest={digest} />
                {!hasDigest && liveRows.length ? (
                  <div className="mt-4 space-y-3">
                    {liveRows.slice(0, 3).map((record) => (
                      <div key={`${record.id}-${record.time}`} className="border-l-2 border-current/25 bg-white/70 px-3 py-2">
                        <div className="text-[11px] font-black uppercase tracking-[0.12em] opacity-60">
                          {record.time?.slice(5, 16) || "-"}
                        </div>
                        <p className="mt-1 text-sm leading-6 text-[#364152]">{record.content}</p>
                      </div>
                    ))}
                  </div>
                ) : null}
              </article>
            );
          })}
        </section>

        <section className="grid grid-cols-1 gap-4 xl:grid-cols-[0.8fr_1.2fr]">
          <article className="border border-[#E6DDCD] bg-[#FFFDF8] p-5">
            <div className="text-xs font-black uppercase tracking-[0.18em] text-[#8A6A2F]">
              {isChinese ? "数据状态" : "Data status"}
            </div>
            <div className="mt-4 grid grid-cols-2 gap-px bg-[#E6DDCD]">
              {[
                ["A股实时", live?.counts?.a_share ?? 0],
                ["美股实时", live?.counts?.us_stock ?? 0],
                ["A股日报源", live?.counts?.a_share_digest ?? 0],
                ["美股评级源", live?.counts?.us_analyst_digest ?? 0],
              ].map(([label, value]) => (
                <div key={label} className="bg-white p-4">
                  <div className="text-2xl font-semibold text-[#111827]">{value}</div>
                  <div className="mt-1 text-xs font-black uppercase tracking-[0.12em] text-[#7B879C]">{label}</div>
                </div>
              ))}
            </div>
            <p className="mt-4 text-sm leading-6 text-[#5B6472]">
              {isChinese
                ? "外汇和商品摘要入口已接好；实习生包里未包含它们的实时 collector，因此有数据文件时会自动展示，没有文件时保持空状态。"
                : "FX and commodity summary inputs are wired; their realtime collectors were not included in the intern package, so they render when source files exist."}
            </p>
          </article>

          <article className="border border-[#E6DDCD] bg-white p-5">
            <div className="mb-4 flex items-center justify-between gap-3">
              <div>
                <div className="text-xs font-black uppercase tracking-[0.18em] text-[#8A6A2F]">
                  {isChinese ? "最新入库事件" : "Latest events"}
                </div>
                <h2 className="mt-1 text-2xl font-black text-[#111827]">
                  {isChinese ? "实时新闻打分流" : "Realtime scored news flow"}
                </h2>
              </div>
              <span className="text-xs font-black uppercase tracking-[0.12em] text-[#7B879C]">
                {compactDate(live?.server_time)}
              </span>
            </div>
            <div className="max-h-[520px] overflow-y-auto border-t border-[#EEF1F6]">
              {latestRecords.length ? (
                latestRecords.map((record) => (
                  <div key={`${record.market}-${record.id}-${record.time}`} className="grid grid-cols-1 gap-2 border-b border-[#EEF1F6] py-3 lg:grid-cols-[9rem_1fr_6rem]">
                    <div className="text-xs font-black uppercase tracking-[0.12em] text-[#7B879C]">
                      {record.time?.slice(5, 16) || "-"}
                      <div className="mt-1 text-[#8A6A2F]">{record.market || "-"}</div>
                    </div>
                    <div className="text-sm leading-6 text-[#263244]">{record.content}</div>
                    <div className="text-right text-sm font-black text-[#111827]">
                      {record.claude_score != null ? record.claude_score : "-"}
                      <div className="mt-1 text-xs font-semibold text-[#7B879C]">
                        {record.claude_gate_triggered || "gate -"}
                      </div>
                    </div>
                  </div>
                ))
              ) : (
                <div className="py-12 text-center text-sm font-semibold text-[#7B879C]">
                  {isChinese ? "暂无实时入库事件" : "No realtime events yet"}
                </div>
              )}
            </div>
          </article>
        </section>
      </main>
    </div>
  );
}
