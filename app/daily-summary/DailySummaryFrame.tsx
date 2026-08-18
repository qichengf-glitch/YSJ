"use client";

import { useLanguage } from "@/contexts/LanguageContext";
import QuantModuleHeader from "@/components/QuantModuleHeader";
import { CalendarClock, Database } from "lucide-react";

export default function DailySummaryFrame() {
  const { language } = useLanguage();
  const isChinese = language === "zh";
  const title = isChinese ? "每日市场日报" : "Daily Summary";

  return (
    <div className="flex h-full flex-col bg-[#FBFAF7]">
      <QuantModuleHeader
        backLabel={isChinese ? "量化指标监控" : "Quant Monitor"}
        title={title}
        subtitle={
          isChinese
            ? "跨资产市场日报，目前为静态快照。"
            : "Cross-asset market brief, currently served as a static snapshot."
        }
        icon={<CalendarClock className="h-5 w-5" />}
        meta={
          <div className="flex flex-wrap items-center gap-2 text-xs font-black uppercase tracking-[0.12em] text-[#8A6A2F]">
            <span className="inline-flex h-9 items-center gap-2 border border-[#E6DDCD] bg-white px-3">
              <Database className="h-4 w-4" />
              {isChinese ? "静态快照" : "Static snapshot"}
            </span>
          </div>
        }
      />
      <iframe
        src={isChinese ? "/daily-summary/latest-zh.html" : "/daily-summary/latest-en.html"}
        title={isChinese ? "每日市场日报" : "Daily Market Summary"}
        className="min-h-0 flex-1 border-0"
      />
    </div>
  );
}
