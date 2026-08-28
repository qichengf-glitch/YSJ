"use client";

import { BarChart3, Database, RadioTower } from "lucide-react";
import { useLanguage } from "@/contexts/LanguageContext";
import QuantModuleHeader from "@/components/QuantModuleHeader";

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
  },
  zh: {
    back: "量化指标监控",
    title: "中国金融期权 VIX 监控",
    subtitle: "中国金融期权波动率实时看板。",
    cadence: "5 分钟 / 半日频",
    storage: "SQLite 服务",
  },
};

export default function CnOptionVixPage({ dashboardUrl }: CnOptionVixPageProps) {
  const { language } = useLanguage();
  const t = copy[language];

  return (
    <main className="min-h-screen bg-[#FBFAF7] text-[#111827]">
      <QuantModuleHeader
        backLabel={t.back}
        title={t.title}
        subtitle={t.subtitle}
        icon={<BarChart3 className="h-5 w-5" />}
        meta={
          <div className="flex flex-wrap items-center gap-2 text-xs font-black uppercase tracking-[0.12em] text-[#F0D694]">
            <span className="inline-flex h-9 items-center gap-2 border border-[#D7B46A]/45 bg-white/8 px-3">
              <RadioTower className="h-4 w-4" />
              {t.cadence}
            </span>
            <span className="inline-flex h-9 items-center gap-2 border border-[#D7B46A]/45 bg-white/8 px-3">
              <Database className="h-4 w-4" />
              {t.storage}
            </span>
          </div>
        }
      />

      <iframe
        src={dashboardUrl}
        title="CN Option VIX Monitor"
        className="block h-[calc(100vh-88px)] min-h-[720px] w-full border-0 bg-[#FBFAF7]"
      />
    </main>
  );
}
