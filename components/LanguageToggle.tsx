"use client";

import { useLanguage } from "@/contexts/LanguageContext";

export default function LanguageToggle() {
  const { language, toggleLanguage } = useLanguage();

  return (
    <button
      onClick={toggleLanguage}
      className="flex items-center space-x-2 text-sm font-medium text-white transition-colors"
    >
      <span className={language === "en" ? "text-blue-300 font-semibold" : "text-white"}>
        EN
      </span>
      <span className="text-white/40">|</span>
      <span className={language === "zh" ? "text-blue-300 font-semibold" : "text-white"}>
        中文
      </span>
    </button>
  );
}
