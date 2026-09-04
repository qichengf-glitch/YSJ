"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Activity, BarChart3, ChevronDown, Database, TrendingUp } from "lucide-react";
import BrandMark from "./BrandMark";
import LanguageToggle from "./LanguageToggle";
import { useLanguage } from "@/contexts/LanguageContext";

const navItems = {
  en: [
    { label: "Home", href: "/" },
    { label: "Research", href: "/research" },
    { label: "Ongoing Thesis", href: "/research/ongoing-thesis" },
    { label: "Quant Monitor", href: "/access" },
    { label: "Contact", href: "/contact" },
  ],
  zh: [
    { label: "首页", href: "/" },
    { label: "研究", href: "/research" },
    { label: "进行中的研究", href: "/research/ongoing-thesis" },
    { label: "量化指标监控", href: "/access" },
    { label: "联系我们", href: "/contact" },
  ],
};

const quantModules = {
  en: [
    {
      label: "CN Option VIX",
      detail: "Live volatility monitor",
      href: "/cn-option-vix",
      icon: BarChart3,
    },
    {
      label: "Prediction Market",
      detail: "Macro probability dashboard",
      href: "/prediction-markets",
      icon: Activity,
    },
    {
      label: "Stock Grader",
      detail: "Equity scoring system",
      href: "/stock-grader",
      icon: TrendingUp,
    },
    {
      label: "A-Share Strategy",
      detail: "Tick-stock-panel workspace",
      href: "/a-share-strategy-panel",
      icon: Database,
    },
  ],
  zh: [
    {
      label: "中国期权 VIX",
      detail: "实时波动率监控",
      href: "/cn-option-vix",
      icon: BarChart3,
    },
    {
      label: "预测市场",
      detail: "宏观概率看板",
      href: "/prediction-markets",
      icon: Activity,
    },
    {
      label: "股票评分",
      detail: "基本面评分系统",
      href: "/stock-grader",
      icon: TrendingUp,
    },
    {
      label: "A股策略面板",
      detail: "tick-stock-panel 工作台",
      href: "/a-share-strategy-panel",
      icon: Database,
    },
  ],
};

export default function Navbar() {
  const pathname = usePathname();
  const { language } = useLanguage();

  const isActive = (path: string) => {
    if (path === "/") {
      return pathname === "/";
    }
    return pathname.startsWith(path);
  };
  const isQuantActive =
    pathname.startsWith("/access") ||
    pathname.startsWith("/cn-option-vix") ||
    pathname.startsWith("/prediction-markets") ||
    pathname.startsWith("/stock-grader") ||
    pathname.startsWith("/a-share-data") ||
    pathname.startsWith("/a-share-strategy-panel");

  return (
    <nav className="sticky top-0 z-50 border-b border-[#E6DDCD] bg-[#FBFAF7]/94 backdrop-blur">
      <div className="mx-auto max-w-7xl px-4 sm:px-8 lg:px-12">
        <div className="flex min-h-16 items-center justify-between gap-4 py-3">
          <BrandMark />

          <div className="flex min-w-0 flex-1 items-center justify-end gap-3 sm:gap-6">
            <div className="hidden items-center gap-6 md:flex">
              {navItems[language].map((item) => (
                item.href === "/access" ? (
                  <div key={item.href} className="group relative">
                    <Link
                      href={item.href}
                      className={`inline-flex items-center gap-1.5 whitespace-nowrap text-sm font-semibold transition-colors ${
                        isQuantActive ? "text-[#8A6A2F]" : "text-[#5B6472] hover:text-[#111827]"
                      }`}
                    >
                      {item.label}
                      <ChevronDown className="h-3.5 w-3.5 transition group-hover:rotate-180" />
                    </Link>
                    <div className="invisible absolute right-0 top-full w-[300px] translate-y-3 border border-[#D7B46A]/55 bg-[#FFFDF8]/95 p-2 opacity-0 shadow-[0_20px_52px_rgba(78,56,21,0.18)] backdrop-blur-xl transition group-hover:visible group-hover:translate-y-2 group-hover:opacity-100 group-focus-within:visible group-focus-within:translate-y-2 group-focus-within:opacity-100">
                      <Link
                        href="/access"
                        className="mb-1 block border-b border-[#E6DDCD] px-3 py-2 text-xs font-black uppercase tracking-[0.16em] text-[#8A6A2F] transition hover:bg-[#F8F1E3]"
                      >
                        {language === "zh" ? "量化指标监控入口" : "Quant Monitor Home"}
                      </Link>
                      {quantModules[language].map((module) => {
                        const Icon = module.icon;
                        const active = pathname.startsWith(module.href);
                        return (
                          <Link
                            key={module.href}
                            href={module.href}
                            className={`flex items-center gap-3 px-3 py-3 transition ${
                              active ? "bg-[#111827] text-white" : "text-[#111827] hover:bg-[#F8F1E3]"
                            }`}
                          >
                            <span
                              className={`inline-flex h-9 w-9 flex-none items-center justify-center ${
                                active ? "bg-[#D7B46A] text-[#111827]" : "bg-[#F8F1E3] text-[#8A6A2F]"
                              }`}
                            >
                              <Icon className="h-4 w-4" />
                            </span>
                            <span className="min-w-0">
                              <span className="block text-sm font-black">{module.label}</span>
                              <span className={`mt-0.5 block text-xs font-semibold ${active ? "text-white/62" : "text-[#5B6472]"}`}>
                                {module.detail}
                              </span>
                            </span>
                          </Link>
                        );
                      })}
                    </div>
                  </div>
                ) : (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={`whitespace-nowrap text-sm font-semibold transition-colors ${
                      isActive(item.href)
                        ? "text-[#8A6A2F]"
                        : "text-[#5B6472] hover:text-[#111827]"
                    }`}
                  >
                    {item.label}
                  </Link>
                )
              ))}
            </div>

            <LanguageToggle />
          </div>
        </div>
      </div>
    </nav>
  );
}
