"use client";

import Link from "next/link";
import {
  Activity,
  ArrowUpRight,
  BarChart3,
  Clock3,
  Database,
  FileCode2,
  LineChart,
  LockKeyhole,
  RadioTower,
  ShieldCheck,
} from "lucide-react";
import { useLanguage } from "@/contexts/LanguageContext";

type CnOptionVixPageProps = {
  dashboardUrl: string;
};

const groups = [
  ["Overall", "All monitored option chains"],
  ["Index VIX", "50ETF, 300ETF, 500ETF and listed index-option proxies"],
  ["Blue Chip", "Large-cap and broad-market option instruments"],
  ["SZ Growth", "Shenzhen growth ETF option instruments"],
  ["Mid-Small", "Mid-small cap and MO related volatility chain"],
  ["Hard Tech", "STAR / hard-tech option instruments"],
];

const scripts = [
  {
    name: "monitor_live_5m.py",
    role: "Collects synchronized five-minute RQData snapshots and writes complete VIX points to SQLite.",
  },
  {
    name: "build_recent_5m.py",
    role: "Backfills recent native five-minute observations and repairs missed trading dates.",
  },
  {
    name: "bootstrap_dashboard.py",
    role: "Imports historical 30-minute outputs into the canonical half-day dashboard series.",
  },
  {
    name: "web/app.py",
    role: "Serves the live terminal, data-quality status, moving averages, levels, and relative spreads.",
  },
];

const copy = {
  en: {
    eyebrow: "Private System",
    title: "CN Option VIX Monitor",
    subtitle:
      "Live and historical China option volatility monitoring built from RiceQuant option-chain data, model-free VIX math, and OI-weighted aggregation.",
    openDashboard: "Open live dashboard",
    back: "Back to Private Access",
    frameTitle: "Live dashboard",
    frameNote:
      "The embedded terminal uses the deployed VIX service URL when configured, otherwise the authenticated same-origin proxy.",
    modules: "What is inside",
    groups: "Coverage",
    scripts: "Imported scripts",
    workflow: "Local run workflow",
    workflowText:
      "Set RQDATA_URI once. The service repairs missing dates at startup, collects every completed five-minute slot, and reconciles again after market close.",
    dataModel: "Data model",
    dataModelText:
      "The web process reads SQLite/CSV outputs and does not call RiceQuant directly. The collector is the only process that uses RQData credentials.",
    cards: [
      ["5-minute live", "Latest five trading days, native 5-minute observations, browser polling."],
      ["Half-day YTD", "2026 year-to-date AM 11:30 and PM 15:00 observations."],
      ["Regime snapshot", "30D / 60D moving averages, spreads, quality and freshness checks."],
    ],
  },
  zh: {
    eyebrow: "内部系统",
    title: "中国期权 VIX 监控",
    subtitle:
      "基于 RiceQuant 期权链、无模型 30 日 VIX 计算和 OI 加权聚合的中国期权波动率监控系统。",
    openDashboard: "打开实时看板",
    back: "返回 Private Access",
    frameTitle: "实时看板",
    frameNote:
      "下方嵌入页优先使用已部署的 VIX 服务地址；未配置时使用同域鉴权代理。",
    modules: "包含内容",
    groups: "覆盖范围",
    scripts: "已接入脚本",
    workflow: "本地运行流程",
    workflowText:
      "配置一次 RQDATA_URI 后，服务会在启动时自动补漏、每 5 分钟采集，并在收盘后再次核对补齐。",
    dataModel: "数据模型",
    dataModelText:
      "网页进程只读取 SQLite/CSV 输出，不直接调用 RiceQuant。真正使用 RQData 授权的是后台采集进程。",
    cards: [
      ["5 分钟实时", "近 5 个交易日原生 5 分钟观察点，浏览器定时轮询。"],
      ["半日频 YTD", "2026 年初至今 11:30 与 15:00 两个半日观察点。"],
      ["状态快照", "30D / 60D 均值、相对 Overall spread、数据质量和新鲜度检查。"],
    ],
  },
};

export default function CnOptionVixPage({ dashboardUrl }: CnOptionVixPageProps) {
  const { language } = useLanguage();
  const t = copy[language];

  return (
    <main className="min-h-screen bg-[linear-gradient(180deg,#FFFFFF_0%,#F8FAFC_100%)] text-[#18233A]">
      <section className="mx-auto max-w-7xl px-6 py-10 sm:px-8 lg:px-12 lg:py-14">
        <div className="grid grid-cols-1 gap-8 lg:grid-cols-[0.95fr_1.05fr] lg:items-end">
          <div>
            <div className="mb-5 inline-flex items-center gap-2 rounded-full border border-[#E7ECF5] bg-white px-4 py-2 text-xs font-bold uppercase tracking-[0.18em] text-[#4F63F6] shadow-[0_10px_24px_rgba(79,99,246,0.08)]">
              <LockKeyhole className="h-3.5 w-3.5" />
              {t.eyebrow}
            </div>
            <h1 className="max-w-4xl text-4xl font-black leading-[0.98] tracking-tight text-[#18233A] sm:text-5xl lg:text-6xl">
              {t.title}
            </h1>
            <p className="mt-5 max-w-3xl text-lg leading-8 text-[#5B6780]">
              {t.subtitle}
            </p>
            <div className="mt-7 flex flex-col gap-3 sm:flex-row">
              <a
                href={dashboardUrl}
                target="_blank"
                rel="noreferrer"
                className="inline-flex h-12 items-center justify-center rounded-full bg-[#4F63F6] px-6 text-sm font-bold text-white shadow-[0_14px_28px_rgba(79,99,246,0.24)] transition hover:bg-[#273B9A]"
              >
                {t.openDashboard}
                <ArrowUpRight className="ml-2 h-4 w-4" />
              </a>
              <Link
                href="/access"
                className="inline-flex h-12 items-center justify-center rounded-full border border-[#E7ECF5] bg-white px-6 text-sm font-bold text-[#273B9A] transition hover:border-[#A8B2FF] hover:bg-[#F8FAFC]"
              >
                {t.back}
              </Link>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            {t.cards.map(([title, text], index) => {
              const Icon = [RadioTower, Clock3, Activity][index];
              return (
                <div key={title} className="rounded-2xl border border-[#E7ECF5] bg-white p-5 shadow-[0_12px_30px_rgba(39,59,154,0.06)]">
                  <div className="mb-3 inline-flex h-10 w-10 items-center justify-center rounded-xl bg-[#EEF2FF] text-[#4F63F6]">
                    <Icon className="h-5 w-5" />
                  </div>
                  <h2 className="text-sm font-black text-[#18233A]">{title}</h2>
                  <p className="mt-2 text-sm leading-6 text-[#5B6780]">{text}</p>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-6 pb-8 sm:px-8 lg:px-12">
        <div className="rounded-3xl border border-[#E7ECF5] bg-white p-4 shadow-[0_22px_55px_rgba(39,59,154,0.12)]">
          <div className="mb-4 flex flex-col gap-3 border-b border-[#E7ECF5] pb-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <div className="text-xs font-bold uppercase tracking-[0.16em] text-[#A8B2FF]">
                {t.frameTitle}
              </div>
              <p className="mt-1 text-sm leading-6 text-[#5B6780]">{t.frameNote}</p>
            </div>
            <div className="inline-flex items-center gap-2 rounded-full bg-[#F8FAFC] px-4 py-2 text-xs font-bold text-[#273B9A]">
              <ShieldCheck className="h-4 w-4" />
              {dashboardUrl.replace(/^https?:\/\//, "")}
            </div>
          </div>
          <iframe
            src={dashboardUrl}
            title="CN Option VIX Monitor"
            className="h-[760px] w-full rounded-2xl border border-[#E7ECF5] bg-[#F8FAFC]"
          />
        </div>
      </section>

      <section className="mx-auto grid max-w-7xl grid-cols-1 gap-6 px-6 pb-16 sm:px-8 lg:grid-cols-[0.8fr_1fr] lg:px-12">
        <div className="rounded-3xl border border-[#E7ECF5] bg-white p-6 shadow-[0_14px_34px_rgba(39,59,154,0.07)]">
          <div className="mb-5 flex items-center gap-3">
            <BarChart3 className="h-5 w-5 text-[#4F63F6]" />
            <h2 className="text-xl font-black">{t.groups}</h2>
          </div>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {groups.map(([name, detail]) => (
              <div key={name} className="rounded-2xl bg-[#F8FAFC] p-4">
                <div className="text-sm font-black text-[#18233A]">{name}</div>
                <div className="mt-1 text-sm leading-6 text-[#5B6780]">{detail}</div>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-3xl border border-[#E7ECF5] bg-white p-6 shadow-[0_14px_34px_rgba(39,59,154,0.07)]">
          <div className="mb-5 flex items-center gap-3">
            <FileCode2 className="h-5 w-5 text-[#4F63F6]" />
            <h2 className="text-xl font-black">{t.scripts}</h2>
          </div>
          <div className="space-y-3">
            {scripts.map((script) => (
              <div key={script.name} className="rounded-2xl border border-[#E7ECF5] bg-[#F8FAFC] p-4">
                <div className="font-mono text-sm font-black text-[#273B9A]">{script.name}</div>
                <p className="mt-1 text-sm leading-6 text-[#5B6780]">{script.role}</p>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-3xl border border-[#E7ECF5] bg-white p-6 shadow-[0_14px_34px_rgba(39,59,154,0.07)]">
          <div className="mb-4 flex items-center gap-3">
            <Database className="h-5 w-5 text-[#4F63F6]" />
            <h2 className="text-xl font-black">{t.dataModel}</h2>
          </div>
          <p className="text-sm leading-7 text-[#5B6780]">{t.dataModelText}</p>
        </div>

        <div className="rounded-3xl border border-[#E7ECF5] bg-white p-6 shadow-[0_14px_34px_rgba(39,59,154,0.07)]">
          <div className="mb-4 flex items-center gap-3">
            <LineChart className="h-5 w-5 text-[#4F63F6]" />
            <h2 className="text-xl font-black">{t.workflow}</h2>
          </div>
          <p className="text-sm leading-7 text-[#5B6780]">{t.workflowText}</p>
          <pre className="mt-4 overflow-x-auto rounded-2xl bg-[#18233A] p-4 text-xs leading-6 text-white">
{`cd new-YSJ-main
nano .env
./scripts/sync_cn_vix_through.sh 2026-07-23
sudo systemctl restart ysj-vix`}
          </pre>
        </div>
      </section>
    </main>
  );
}
