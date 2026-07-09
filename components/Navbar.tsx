"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import LanguageToggle from "./LanguageToggle";
import { useLanguage } from "@/contexts/LanguageContext";

const strategyItems = {
  en: [
    {
      name: "US Options Fundamental-Biased Strategy",
      description: "Fundamental analysis with options for directional views and risk management.",
      href: "/strategy",
    },
    {
      name: "US Options Technical-Biased Strategy",
      description: "Technical analysis and market structure for tactical positioning.",
      href: "/strategy",
    },
    {
      name: "US Options Multi-Strategy",
      description: "Diversified approach for risk-adjusted returns across market conditions.",
      href: "/strategy",
    },
  ],
  zh: [
    {
      name: "美股期权基本面偏向策略",
      description: "基本面分析与期权结合，表达方向性观点并管理风险。",
      href: "/strategy",
    },
    {
      name: "美股期权技术面偏向策略",
      description: "技术分析与市场结构驱动，用于战术性定位。",
      href: "/strategy",
    },
    {
      name: "美股期权多策略",
      description: "多元化方法，在不同市场条件下优化风险调整回报。",
      href: "/strategy",
    },
  ],
};

const navItems = {
  en: {
    home: "Home",
    research: "Research",
    strategy: "Our Strategy",
    dashboards: "Dashboards",
    predictionMarkets: "Prediction Markets",
    marketRadar: "Market Radar",
    dailySummary: "Daily Summary",
    researchDropdown: {
      theoretical: "Theoretical Research",
      thesis: "Ongoing Thesis",
      marketData: "General Market Data & Our Picks",
    },
  },
  zh: {
    home: "首页",
    research: "研究",
    strategy: "我们的策略",
    dashboards: "看板",
    predictionMarkets: "预测市场",
    marketRadar: "市场雷达",
    dailySummary: "每日市场日报",
    researchDropdown: {
      theoretical: "理论研究",
      thesis: "进行中的研究",
      marketData: "市场数据与我们的选择",
    },
  },
};

export default function Navbar() {
  const pathname = usePathname();
  const { language } = useLanguage();
  const t = navItems[language];
  const [isResearchOpen, setIsResearchOpen] = useState(false);
  const [isStrategyOpen, setIsStrategyOpen] = useState(false);
  const [isDashboardsOpen, setIsDashboardsOpen] = useState(false);

  const dashboardItems = [
    {
      label: t.dailySummary,
      description:
        language === "zh"
          ? "A股、美股、外汇与商品的每日摘要"
          : "Daily A-shares, US equities, FX, and commodities brief",
      href: "/daily-summary",
    },
    {
      label: t.marketRadar,
      description:
        language === "zh"
          ? "美股财报、事件更新与市场日历"
          : "US earnings, event updates, and market calendar",
      href: "/market-radar",
    },
    {
      label: t.predictionMarkets,
      description:
        language === "zh"
          ? "事件赔率与宏观主题概率跟踪"
          : "Event odds and macro probability tracking",
      href: "/prediction-markets",
    },
  ];

  const isActive = (path: string) => {
    if (path === "/") {
      return pathname === "/";
    }
    return pathname.startsWith(path);
  };

  return (
    <nav className="sticky top-0 z-50 bg-primary border-b border-primary-dark">
      <div className="max-w-7xl mx-auto px-6 sm:px-8 lg:px-12">
        <div className="flex items-center justify-between h-16">
          <Link href="/" className="font-playfair text-2xl font-normal text-white tracking-tight">
            YSJ Lab
          </Link>

          <div className="flex items-center space-x-8">
            <Link
              href="/"
              className={`text-sm font-medium transition-colors ${
                isActive("/")
                  ? "text-blue-300"
                  : "text-white hover:text-blue-300"
              }`}
            >
              {t.home}
            </Link>

            {/* Research with dropdown */}
            <div
              className="relative"
              onMouseEnter={() => setIsResearchOpen(true)}
              onMouseLeave={() => setIsResearchOpen(false)}
            >
              <Link
                href="/research"
                className={`text-sm font-medium transition-colors ${
                  isActive("/research")
                    ? "text-blue-300"
                    : "text-white hover:text-blue-300"
                }`}
              >
                {t.research}
              </Link>
              {/* Dropdown (desktop) */}
              <div
                className={`absolute left-0 top-full w-72 rounded-b-lg border border-primary-dark border-t-0 bg-primary shadow-lg transition-opacity duration-150 ${
                  isResearchOpen ? "opacity-100 visible" : "opacity-0 invisible"
                }`}
              >
                <div className="py-3">
                  <Link
                    href="/research/theoretical-research"
                    className="block px-4 py-2.5 text-sm text-white hover:bg-primary-dark hover:text-blue-300"
                  >
                    {t.researchDropdown.theoretical}
                  </Link>
                  <Link
                    href="/research/ongoing-thesis"
                    className="block px-4 py-2.5 text-sm text-white hover:bg-primary-dark hover:text-blue-300"
                  >
                    {t.researchDropdown.thesis}
                  </Link>
                  <Link
                    href="/research/market-data"
                    className="block px-4 py-2.5 text-sm text-white hover:bg-primary-dark hover:text-blue-300"
                  >
                    {t.researchDropdown.marketData}
                  </Link>
                </div>
              </div>
            </div>

            {/* Strategy with dropdown */}
            <div
              className="relative"
              onMouseEnter={() => setIsStrategyOpen(true)}
              onMouseLeave={() => setIsStrategyOpen(false)}
            >
              <Link
                href="/strategy"
                className={`text-sm font-medium transition-colors ${
                  isActive("/strategy")
                    ? "text-blue-300"
                    : "text-white hover:text-blue-300"
                }`}
              >
                {t.strategy}
              </Link>
              <div
                className={`absolute left-0 top-full w-96 rounded-b-lg border border-primary-dark border-t-0 bg-primary shadow-lg transition-opacity duration-150 ${
                  isStrategyOpen ? "opacity-100 visible" : "opacity-0 invisible"
                }`}
              >
                <div className="py-3">
                  {strategyItems[language].map((item, idx) => (
                    <Link
                      key={idx}
                      href={item.href}
                      className="block px-4 py-3 hover:bg-primary-dark group"
                    >
                      <div className="text-sm font-medium text-white group-hover:text-blue-300">
                        {item.name}
                      </div>
                      <div className="text-xs text-blue-200/90 mt-0.5 leading-snug">
                        {item.description}
                      </div>
                    </Link>
                  ))}
                </div>
              </div>
            </div>
            <div
              className="relative"
              onMouseEnter={() => setIsDashboardsOpen(true)}
              onMouseLeave={() => setIsDashboardsOpen(false)}
            >
              <button
                type="button"
                className={`text-sm font-medium transition-colors ${
                  isActive("/daily-summary") ||
                  isActive("/market-radar") ||
                  isActive("/prediction-markets")
                    ? "text-blue-300"
                    : "text-white hover:text-blue-300"
                }`}
              >
                {t.dashboards}
              </button>
              <div
                className={`absolute left-0 top-full w-80 rounded-b-lg border border-primary-dark border-t-0 bg-primary shadow-lg transition-opacity duration-150 ${
                  isDashboardsOpen ? "opacity-100 visible" : "opacity-0 invisible"
                }`}
              >
                <div className="py-3">
                  {dashboardItems.map((item) => (
                    <Link
                      key={item.href}
                      href={item.href}
                      className="block px-4 py-3 hover:bg-primary-dark group"
                    >
                      <div className="text-sm font-medium text-white group-hover:text-blue-300">
                        {item.label}
                      </div>
                      <div className="text-xs text-blue-200/90 mt-0.5 leading-snug">
                        {item.description}
                      </div>
                    </Link>
                  ))}
                </div>
              </div>
            </div>

            <LanguageToggle />
          </div>
        </div>
      </div>
    </nav>
  );
}
