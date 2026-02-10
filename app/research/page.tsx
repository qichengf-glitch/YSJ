"use client";

import Link from "next/link";
import Section from "@/components/Section";
import { useLanguage } from "@/contexts/LanguageContext";
import { ChevronRight } from "lucide-react";

const boxShadow3d =
  "0 4px 0 rgba(30, 58, 138, 0.4), 0 8px 0 rgba(30, 58, 138, 0.2), inset 0 1px 0 rgba(255, 255, 255, 0.1)";

const content = {
  en: {
    title: "Research Hub",
    intro: "Curated research, ongoing theses, and market insights to support informed investment decisions.",
    blocks: [
      {
        href: "/research/theoretical-research",
        title: "Theoretical Research",
        intro:
          "Our theoretical research explores fundamental questions in finance, economics, and market behavior. Academic papers and conceptual frameworks that underpin systematic strategies.",
      },
      {
        href: "/research/ongoing-thesis",
        title: "Ongoing Thesis",
        intro:
          "Current research projects and investment theses under development. Community-driven theses, frameworks, and ongoing debates around markets, macro, and specific trade structures.",
      },
      {
        href: "/research/market-data",
        title: "General Market Data & Our Picks",
        intro:
          "Curated market data, analysis, and selected opportunities we're monitoring. World indices, key signals, and a rotating set of YSJ Lab watchlist ideas.",
      },
    ],
  },
  zh: {
    title: "研究中心",
    intro: "精选研究、进行中的主题与市场洞察，为投资决策提供支持。",
    blocks: [
      {
        href: "/research/theoretical-research",
        title: "理论研究",
        intro:
          "我们的理论研究探索金融、经济学和市场行为中的基本问题。支撑系统化策略的学术论文与概念框架。",
      },
      {
        href: "/research/ongoing-thesis",
        title: "进行中的研究",
        intro:
          "当前的研究项目和正在开发的投资主题。社区驱动的主题、框架以及围绕市场、宏观和具体交易结构的持续讨论。",
      },
      {
        href: "/research/market-data",
        title: "市场数据与我们的选择",
        intro:
          "精选的市场数据、分析和我们正在关注的机会。全球指数、关键信号以及 YSJ Lab 观察清单。",
      },
    ],
  },
};

export default function ResearchPage() {
  const { language } = useLanguage();
  const t = content[language];

  return (
    <main className="min-h-screen">
      <Section className="pt-4 pb-12 sm:pt-5 sm:pb-14">
        <div className="mx-auto max-w-7xl">
          <h1 className="font-playfair text-4xl sm:text-5xl lg:text-6xl font-normal text-gray-900 mb-6 text-center tracking-tight">
            {t.title}
          </h1>
          <p className="text-xl text-gray-600 mb-10 sm:mb-14 max-w-2xl mx-auto text-center leading-relaxed">
            {t.intro}
          </p>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 sm:gap-8">
            {t.blocks.map((block) => (
              <Link
                key={block.href}
                href={block.href}
                className="group bg-[#b8e5ff] p-6 rounded-lg border-2 border-primary hover:border-primary-dark transition-colors block"
                style={{ boxShadow: boxShadow3d }}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    <h2 className="text-lg sm:text-xl font-semibold text-gray-900 group-hover:text-primary transition-colors">
                      {block.title}
                    </h2>
                    <p className="mt-2 text-sm text-gray-600 leading-relaxed">
                      {block.intro}
                    </p>
                  </div>
                  <ChevronRight className="h-5 w-5 text-primary flex-shrink-0 mt-1" />
                </div>
              </Link>
            ))}
          </div>
        </div>
      </Section>
    </main>
  );
}
