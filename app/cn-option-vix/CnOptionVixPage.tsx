"use client";

import Link from "next/link";
import {
  Activity,
  ArrowUpRight,
  BarChart3,
  Clock3,
  Database,
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

const copy = {
  en: {
    eyebrow: "Private System",
    title: "CN Option VIX Monitor",
    subtitle:
      "Live and historical China option volatility monitoring built from RiceQuant option-chain data, model-free VIX math, and OI-weighted aggregation.",
    openDashboard: "Open live dashboard",
    back: "Back to Quant Monitor",
    frameTitle: "Live dashboard",
    frameNote:
      "The embedded dashboard connects to the protected VIX service and keeps the monitoring workflow inside the Quant Monitor workspace.",
    groups: "Coverage",
    dataModel: "System discipline",
    dataModelText:
      "The web layer reads prepared SQLite/CSV outputs. Data collection, credentialed market-data access, and model rebuilds remain isolated in the backend process.",
    operations: "Operating notes",
    operationNotes: [
      ["Live refresh", "Five-minute data and half-day snapshots update through the protected backend service."],
      ["Historical context", "YTD and percentile views use the same model-free VIX methodology as the live monitor."],
      ["Access boundary", "RiceQuant credentials are never used by the browser-facing page."],
    ],
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
    back: "返回量化指标监控",
    frameTitle: "实时看板",
    frameNote:
      "下方实时看板连接受保护的 VIX 服务，监控工作流保持在量化指标监控工作台内部。",
    groups: "覆盖范围",
    dataModel: "系统边界",
    dataModelText:
      "网页层只读取已准备好的 SQLite/CSV 输出。数据采集、授权行情访问和模型重建都隔离在后端流程中。",
    operations: "运营说明",
    operationNotes: [
      ["实时刷新", "5 分钟数据与半日快照通过受保护后端服务更新。"],
      ["历史语境", "YTD 与分位数视图使用与实时监控一致的无模型 VIX 方法。"],
      ["访问边界", "RiceQuant 凭证不会进入浏览器页面。"],
    ],
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
    <main className="min-h-screen bg-[#FBFAF7] text-[#111827]">
      <section className="mx-auto max-w-7xl px-6 py-10 sm:px-8 lg:px-12 lg:py-14">
        <div className="grid grid-cols-1 gap-8 lg:grid-cols-[0.95fr_1.05fr] lg:items-end">
          <div>
            <div className="mb-5 inline-flex items-center gap-2 border border-[#D7B46A] bg-[#F8F1E3] px-4 py-2 text-xs font-black uppercase tracking-[0.22em] text-[#8A6A2F]">
              <LockKeyhole className="h-3.5 w-3.5" />
              {t.eyebrow}
            </div>
            <h1 className="max-w-4xl text-4xl font-semibold leading-[1.04] text-[#111827] sm:text-5xl lg:text-6xl">
              {t.title}
            </h1>
            <p className="mt-5 max-w-3xl text-lg leading-8 text-[#5B6472]">
              {t.subtitle}
            </p>
            <div className="mt-7 flex flex-col gap-3 sm:flex-row">
              <a
                href={dashboardUrl}
                target="_blank"
                rel="noreferrer"
                className="inline-flex h-12 items-center justify-center bg-[#111827] px-6 text-sm font-black text-white transition hover:bg-[#2B3445]"
              >
                {t.openDashboard}
                <ArrowUpRight className="ml-2 h-4 w-4" />
              </a>
              <Link
                href="/access"
                className="inline-flex h-12 items-center justify-center border border-[#D7B46A] bg-[#F8F1E3] px-6 text-sm font-black text-[#5F4820] transition hover:bg-[#D7B46A] hover:text-[#111827]"
              >
                {t.back}
              </Link>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            {t.cards.map(([title, text], index) => {
              const Icon = [RadioTower, Clock3, Activity][index];
              return (
                <div key={title} className="border border-[#E6DDCD] bg-[#FFFDF8] p-5 shadow-[0_12px_30px_rgba(78,56,21,0.06)]">
                  <div className="mb-3 inline-flex h-10 w-10 items-center justify-center bg-[#F8F1E3] text-[#8A6A2F]">
                    <Icon className="h-5 w-5" />
                  </div>
                  <h2 className="text-sm font-black text-[#111827]">{title}</h2>
                  <p className="mt-2 text-sm leading-6 text-[#5B6472]">{text}</p>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-6 pb-8 sm:px-8 lg:px-12">
        <div className="border border-[#E6DDCD] bg-[#FFFDF8] p-4 shadow-[0_22px_55px_rgba(78,56,21,0.12)]">
          <div className="mb-4 flex flex-col gap-3 border-b border-[#E6DDCD] pb-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <div className="text-xs font-black uppercase tracking-[0.20em] text-[#8A6A2F]">
                {t.frameTitle}
              </div>
              <p className="mt-1 text-sm leading-6 text-[#5B6472]">{t.frameNote}</p>
            </div>
            <div className="inline-flex items-center gap-2 bg-[#F8F1E3] px-4 py-2 text-xs font-black text-[#5F4820]">
              <ShieldCheck className="h-4 w-4" />
              {dashboardUrl.replace(/^https?:\/\//, "")}
            </div>
          </div>
          <iframe
            src={dashboardUrl}
            title="CN Option VIX Monitor"
            className="h-[760px] w-full border border-[#E6DDCD] bg-[#FBFAF7]"
          />
        </div>
      </section>

      <section className="mx-auto grid max-w-7xl grid-cols-1 gap-6 px-6 pb-16 sm:px-8 lg:grid-cols-[0.8fr_1fr] lg:px-12">
        <div className="border border-[#E6DDCD] bg-[#FFFDF8] p-6 shadow-[0_14px_34px_rgba(78,56,21,0.07)]">
          <div className="mb-5 flex items-center gap-3">
            <BarChart3 className="h-5 w-5 text-[#8A6A2F]" />
            <h2 className="text-xl font-semibold">{t.groups}</h2>
          </div>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {groups.map(([name, detail]) => (
              <div key={name} className="bg-[#FBFAF7] p-4">
                <div className="text-sm font-black text-[#111827]">{name}</div>
                <div className="mt-1 text-sm leading-6 text-[#5B6472]">{detail}</div>
              </div>
            ))}
          </div>
        </div>

        <div className="border border-[#E6DDCD] bg-[#111827] p-6 text-white shadow-[0_14px_34px_rgba(78,56,21,0.07)]">
          <div className="mb-5 flex items-center gap-3">
            <ShieldCheck className="h-5 w-5 text-[#D7B46A]" />
            <h2 className="text-xl font-semibold">{t.operations}</h2>
          </div>
          <div className="space-y-3">
            {t.operationNotes.map(([title, text]) => (
              <div key={title} className="border border-white/12 bg-white/5 p-4">
                <div className="text-sm font-black text-[#E5C984]">{title}</div>
                <p className="mt-1 text-sm leading-6 text-white/66">{text}</p>
              </div>
            ))}
          </div>
        </div>

        <div className="border border-[#E6DDCD] bg-[#FFFDF8] p-6 shadow-[0_14px_34px_rgba(78,56,21,0.07)] lg:col-span-2">
          <div className="mb-4 flex items-center gap-3">
            <Database className="h-5 w-5 text-[#8A6A2F]" />
            <h2 className="text-xl font-semibold">{t.dataModel}</h2>
          </div>
          <p className="max-w-4xl text-sm leading-7 text-[#5B6472]">{t.dataModelText}</p>
        </div>
      </section>
    </main>
  );
}
