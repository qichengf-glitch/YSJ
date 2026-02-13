"use client";

import Section from "@/components/Section";
import { useLanguage } from "@/contexts/LanguageContext";
import FocusCards from "@/components/FocusCards";

const content = {
  en: {
    hero: {
      label: "YSJ Lab",
      title: "Invest with Assurance",
      subtitle:
        "A disciplined, research-driven partner for investors navigating public and private markets.",
    },
    whatWeDo: {
      title: "What We Do",
    },
    philosophy: {
      title: "Our Mission",
      text: "We believe in rigorous analysis, disciplined execution, and continuous research. Through quantitative methods and qualitative insights, we aim to be the best companion for investors, no matter what market you're in.",
    },
    footer: {
      copyright: "© 2026 YSJ Holdings LLC, all rights reserved",
    },
  },
  zh: {
    hero: {
      label: "YSJ Lab",
      title: "Invest with Assurance",
      subtitle: "以研究为驱动的严谨伙伴，助您穿越公开与私募市场。",
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
      title: "我们的使命",
      text: "我们相信严谨的分析、纪律性的执行和持续的研究。通过定量方法与定性洞察，我们致力于成为投资者的最佳伙伴，无论您身处何种市场。",
    },
    footer: {
      copyright: "© 2026 YSJ Holdings LLC，保留所有权利。",
    },
  },
};

export default function Home() {
  const { language } = useLanguage();
  const t = content[language];

  return (
    <main className="min-h-screen">
      {/* Hero Section */}
      <section className="relative isolate min-h-[75vh] overflow-hidden">
        <video
          className="absolute inset-0 h-full w-full object-cover"
          src="/ysj-hero.mp4"
          autoPlay
          muted
          loop
          playsInline
          aria-hidden="true"
        />
        <div className="absolute inset-0 bg-gradient-to-b from-black/25 via-black/40 to-black/70" />

        <div className="absolute bottom-0 left-0 z-10 px-6 sm:px-8 lg:px-12 pb-12 sm:pb-16 lg:pb-20">
          <h1 className="font-playfair text-4xl sm:text-5xl lg:text-6xl font-normal text-white drop-shadow-md tracking-tight">
            {t.hero.title}
          </h1>
        </div>
      </section>

      {/* What We Do */}
      <Section fullWidth>
        <h2 className="font-playfair text-4xl sm:text-5xl font-normal text-gray-900 mb-12 tracking-tight text-center">
          {t.whatWeDo.title}
        </h2>
        <div className="w-full">
          <FocusCards />
        </div>
      </Section>

      {/* Philosophy */}
      <Section fullWidth>
        <div className="max-w-6xl mx-auto text-center">
          <h2 className="font-playfair text-5xl sm:text-6xl lg:text-7xl font-normal text-gray-900 mb-10 tracking-tight">
            {t.philosophy.title}
          </h2>
          <p className="text-2xl sm:text-3xl text-gray-700 leading-relaxed">
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
