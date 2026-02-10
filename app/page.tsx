"use client";

import Link from "next/link";
import Section from "@/components/Section";
import { useLanguage } from "@/contexts/LanguageContext";

const content = {
  en: {
    hero: {
      title: "YSJ Lab",
      subtitle:
        "YSJ Lab is an independent financial research and strategy studio, focused on data-driven insights, systematic thinking, and forward-looking market analysis.",
    },
    whatWeDo: {
      title: "What We Do",
      cards: [
        {
          title: "Research",
          description:
            "Deep-dive analysis into market dynamics, economic indicators, and investment opportunities.",
          href: "/research",
        },
        {
          title: "Strategy",
          description:
            "Systematic approaches to portfolio management and risk-adjusted returns.",
          href: "/strategy",
        },
        {
          title: "Prediction Markets",
          description:
            "Data-driven predictions and probabilistic modeling for informed decision-making.",
          href: "/prediction-markets",
        },
      ],
    },
    philosophy: {
      title: "Our Philosophy",
      text: "We believe in rigorous analysis, disciplined execution, and continuous learning. Our approach combines quantitative methods with qualitative insights to navigate complex financial markets.",
    },
    footer: {
      copyright: "© 2024 YSJ Lab. All rights reserved.",
    },
  },
  zh: {
    hero: {
      title: "YSJ Lab",
      subtitle:
        "YSJ Lab 是一家独立的金融研究与策略工作室，专注于数据驱动的洞察、系统化思维，以及前瞻性的市场分析。",
    },
    whatWeDo: {
      title: "我们的工作",
      cards: [
        {
          title: "研究",
          description:
            "深入分析市场动态、经济指标和投资机会。",
          href: "/research",
        },
        {
          title: "策略",
          description:
            "系统化的投资组合管理和风险调整回报方法。",
          href: "/strategy",
        },
        {
          title: "预测市场",
          description:
            "数据驱动的预测和概率建模，为决策提供信息支持。",
          href: "/prediction-markets",
        },
      ],
    },
    philosophy: {
      title: "我们的理念",
      text: "我们相信严谨的分析、纪律性的执行和持续的学习。我们的方法结合定量分析和定性洞察，以应对复杂的金融市场。",
    },
    footer: {
      copyright: "© 2024 YSJ Lab。保留所有权利。",
    },
  },
};

export default function Home() {
  const { language } = useLanguage();
  const t = content[language];

  return (
    <main className="min-h-screen">
      {/* Hero Section */}
      <Section className="pt-24 pb-16">
        <div className="max-w-4xl mx-auto text-center">
          <h1 className="font-playfair text-5xl sm:text-6xl lg:text-7xl font-normal text-gray-900 mb-6 tracking-tight">
            {t.hero.title}
          </h1>
          <p className="text-lg sm:text-xl text-gray-700 leading-relaxed max-w-2xl mx-auto font-light">
            {t.hero.subtitle}
          </p>
        </div>
      </Section>

      {/* What We Do */}
      <Section>
        <h2 className="font-playfair text-4xl sm:text-5xl font-normal text-gray-900 mb-12 tracking-tight">
          {t.whatWeDo.title}
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {t.whatWeDo.cards.map((card, index) => (
            <Link
              key={index}
              href={card.href}
              className="group bg-[#b8e5ff] p-8 rounded-lg border-2 border-primary hover:border-primary-dark transition-colors block"
              style={{
                boxShadow: '0 4px 0 rgba(30, 58, 138, 0.4), 0 8px 0 rgba(30, 58, 138, 0.2), inset 0 1px 0 rgba(255, 255, 255, 0.1)'
              }}
            >
              <h3 className="text-2xl font-semibold text-gray-900 mb-4 group-hover:text-primary">
                {card.title}
              </h3>
              <p className="text-gray-600 leading-relaxed">{card.description}</p>
            </Link>
          ))}
        </div>
      </Section>

      {/* Philosophy */}
      <Section>
        <div className="max-w-3xl">
          <h2 className="font-playfair text-4xl sm:text-5xl font-normal text-gray-900 mb-8 tracking-tight">
            {t.philosophy.title}
          </h2>
          <p className="text-xl text-gray-600 leading-relaxed">
            {t.philosophy.text}
          </p>
        </div>
      </Section>

      {/* Footer */}
      <footer className="border-t border-gray-200 py-8">
        <div className="max-w-7xl mx-auto px-6 sm:px-8 lg:px-12">
          <p className="text-sm text-gray-500 text-center">
            {t.footer.copyright}
          </p>
        </div>
      </footer>
    </main>
  );
}
