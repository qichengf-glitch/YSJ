"use client";

import Link from "next/link";
import { ArrowLeft, ArrowUpRight, BarChart3, Database, RadioTower } from "lucide-react";
import { useLanguage } from "@/contexts/LanguageContext";

type CnOptionVixPageProps = {
  dashboardUrl: string;
};

const copy = {
  en: {
    back: "Quant Monitor",
    title: "CN Option VIX Monitor",
    subtitle: "Live China financial-option volatility dashboard.",
    cadence: "5-minute / half-day",
    storage: "SQLite service",
    open: "Open full view",
  },
  zh: {
    back: "量化指标监控",
    title: "中国金融期权 VIX 监控",
    subtitle: "中国金融期权波动率实时看板。",
    cadence: "5 分钟 / 半日频",
    storage: "SQLite 服务",
    open: "全屏打开",
  },
};

export default function CnOptionVixPage({ dashboardUrl }: CnOptionVixPageProps) {
  const { language } = useLanguage();
  const t = copy[language];

  return (
    <main className="min-h-screen bg-[#FBFAF7] text-[#111827]">
      <section className="border-b border-[#E6DDCD] bg-[#FFFDF8] px-5 py-4 shadow-[0_14px_34px_rgba(78,56,21,0.08)] sm:px-8 lg:px-10">
        <div className="mx-auto flex max-w-[1800px] flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex min-w-0 flex-col gap-3 sm:flex-row sm:items-center">
            <Link
              href="/access"
              className="inline-flex h-10 w-fit items-center gap-2 border border-[#D7B46A] bg-[#F8F1E3] px-4 text-sm font-black text-[#5F4820] transition hover:bg-[#D7B46A] hover:text-[#111827]"
            >
              <ArrowLeft className="h-4 w-4" />
              {t.back}
            </Link>
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <BarChart3 className="h-5 w-5 text-[#8A6A2F]" />
                <h1 className="text-xl font-black text-[#111827] sm:text-2xl">{t.title}</h1>
              </div>
              <p className="mt-1 text-sm font-semibold text-[#5B6472]">{t.subtitle}</p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2 text-xs font-black uppercase tracking-[0.12em] text-[#8A6A2F]">
            <span className="inline-flex h-9 items-center gap-2 border border-[#E6DDCD] bg-white px-3">
              <RadioTower className="h-4 w-4" />
              {t.cadence}
            </span>
            <span className="inline-flex h-9 items-center gap-2 border border-[#E6DDCD] bg-white px-3">
              <Database className="h-4 w-4" />
              {t.storage}
            </span>
            <a
              href={dashboardUrl}
              target="_blank"
              rel="noreferrer"
              className="inline-flex h-9 items-center gap-2 bg-[#111827] px-3 text-white transition hover:bg-[#2B3445]"
            >
              {t.open}
              <ArrowUpRight className="h-4 w-4" />
            </a>
          </div>
        </div>
      </section>

      <iframe
        src={dashboardUrl}
        title="CN Option VIX Monitor"
        className="block h-[calc(100vh-112px)] min-h-[720px] w-full border-0 bg-[#FBFAF7]"
      />
    </main>
  );
}
