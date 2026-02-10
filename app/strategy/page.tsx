"use client";

import Section from "@/components/Section";
import { useLanguage } from "@/contexts/LanguageContext";

const boxShadow3d =
  "0 4px 0 rgba(30, 58, 138, 0.4), 0 8px 0 rgba(30, 58, 138, 0.2), inset 0 1px 0 rgba(255, 255, 255, 0.1)";

const content = {
  en: {
    title: "Our Strategy",
    intro:
      "We employ disciplined, systematic strategies designed to capture market opportunities while managing risk. Our approach combines fundamental analysis, technical indicators, and quantitative models.",
    strategies: [
      {
        name: "US Options Fundamental-Biased Strategy",
        description:
          "A strategy focused on fundamental analysis of underlying assets, using options to express directional views and manage risk.",
        nav: "NAV: $---",
        holdings: "Holdings: Coming Soon",
      },
      {
        name: "US Options Technical-Biased Strategy",
        description:
          "A strategy driven by technical analysis and market structure, utilizing options for tactical positioning.",
        nav: "NAV: $---",
        holdings: "Holdings: Coming Soon",
      },
      {
        name: "US Options Multi-Strategy",
        description:
          "A diversified approach combining multiple strategies to optimize risk-adjusted returns across different market conditions.",
        nav: "NAV: $---",
        holdings: "Holdings: Coming Soon",
      },
    ],
  },
  zh: {
    title: "我们的策略",
    intro:
      "我们采用纪律性、系统化的策略，旨在捕捉市场机会的同时管理风险。我们的方法结合了基本面分析、技术指标和量化模型。",
    strategies: [
      {
        name: "美股期权基本面偏向策略",
        description:
          "专注于标的资产基本面分析的策略，使用期权表达方向性观点并管理风险。",
        nav: "净值: $---",
        holdings: "持仓: 即将推出",
      },
      {
        name: "美股期权技术面偏向策略",
        description:
          "由技术分析和市场结构驱动的策略，利用期权进行战术性定位。",
        nav: "净值: $---",
        holdings: "持仓: 即将推出",
      },
      {
        name: "美股期权多策略",
        description:
          "结合多种策略的多元化方法，以在不同市场条件下优化风险调整回报。",
        nav: "净值: $---",
        holdings: "持仓: 即将推出",
      },
    ],
  },
};

export default function Strategy() {
  const { language } = useLanguage();
  const t = content[language];

  return (
    <main className="min-h-screen pt-16">
      <Section className="pt-8">
        <div className="text-center">
          <h1 className="font-playfair text-4xl sm:text-5xl lg:text-6xl font-normal text-gray-900 mb-8 tracking-tight">
            {t.title}
          </h1>
          <p className="text-xl text-gray-600 mb-16 max-w-3xl mx-auto leading-relaxed">
            {t.intro}
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {t.strategies.map((strategy, index) => (
            <div
              key={index}
              className="bg-[#b8e5ff] rounded-lg border-2 border-primary p-6 hover:border-primary-dark transition-colors"
              style={{ boxShadow: boxShadow3d }}
            >
              <h2 className="text-xl font-semibold text-gray-900 mb-4">
                {strategy.name}
              </h2>
              <p className="text-gray-600 mb-6 leading-relaxed text-sm">
                {strategy.description}
              </p>
              <div className="space-y-2 pt-4 border-t border-primary/30">
                <p className="text-sm font-medium text-gray-900">
                  {strategy.nav}
                </p>
                <p className="text-sm text-gray-600">{strategy.holdings}</p>
              </div>
            </div>
          ))}
        </div>
      </Section>
    </main>
  );
}
