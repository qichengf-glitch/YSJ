"use client";

import { useLanguage } from "@/contexts/LanguageContext";

export default function LanguageToggle() {
  const { language, toggleLanguage } = useLanguage();

  return (
    <button
      onClick={toggleLanguage}
      className="flex flex-none items-center space-x-2 whitespace-nowrap text-sm font-semibold text-[#5B6780] transition-colors hover:text-[#273B9A]"
    >
      <span className={language === "en" ? "text-[#4F63F6] font-bold" : "text-[#5B6780]"}>
        EN
      </span>
      <span className="text-[#A8B2FF]">|</span>
      <span className={language === "zh" ? "text-[#4F63F6] font-bold" : "text-[#5B6780]"}>
        中文
      </span>
    </button>
  );
}
