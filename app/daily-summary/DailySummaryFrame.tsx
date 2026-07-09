"use client";

import { useLanguage } from "@/contexts/LanguageContext";

export default function DailySummaryFrame() {
  const { language } = useLanguage();
  const isChinese = language === "zh";

  return (
    <iframe
      src={isChinese ? "/daily-summary/latest-zh.html" : "/daily-summary/latest-en.html"}
      title={isChinese ? "每日市场日报" : "Daily Market Summary"}
      className="h-full w-full border-0"
    />
  );
}
