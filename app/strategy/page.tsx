"use client";

import Image from "next/image";
import Link from "next/link";
import {
  Activity,
  ArrowRight,
  BarChart3,
  Compass,
  Layers3,
  Scale,
  ScanSearch,
  ShieldCheck,
} from "lucide-react";
import { useLanguage } from "@/contexts/LanguageContext";

const content = {
  en: {
    eyebrow: "Strategy",
    title: "Research-led options strategies",
    intro:
      "We translate fundamental views, market structure, and quantitative signals into defined-risk option frameworks. Every idea moves through the same research, sizing, and review discipline.",
    imageAlt: "Strategy chess piece and planning board illustration",
    principles: [
      ["Research first", "A thesis and falsifiable evidence come before position construction."],
      ["Defined risk", "Sizing, liquidity, and exit conditions are specified before execution."],
      ["Regime aware", "Exposure adapts to volatility, trend, and cross-asset conditions."],
    ],
    frameworkEyebrow: "Strategy frameworks",
    frameworkTitle: "Three complementary lenses",
    frameworkIntro:
      "Each framework has a distinct source of edge while sharing the same portfolio-level risk controls.",
    status: "Research framework",
    strategies: [
      {
        number: "01",
        name: "Fundamental-biased",
        description:
          "Expresses differentiated views on an underlying company, sector, or macro theme through asymmetric option structures.",
        focus: "Catalysts · valuation · scenario analysis",
      },
      {
        number: "02",
        name: "Technical-biased",
        description:
          "Uses price structure, volatility behavior, and positioning signals to identify tactical entries and exits.",
        focus: "Trend · volatility · market structure",
      },
      {
        number: "03",
        name: "Multi-strategy",
        description:
          "Combines independent signals and structures to reduce reliance on any single market environment.",
        focus: "Diversification · allocation · drawdown control",
      },
    ],
    processEyebrow: "Operating process",
    processTitle: "From signal to review",
    process: [
      ["Discover", "Identify a measurable market dislocation."],
      ["Structure", "Select the option expression and payoff profile."],
      ["Control", "Set sizing, liquidity, and loss constraints."],
      ["Review", "Monitor assumptions and document outcomes."],
    ],
    ctaTitle: "The research behind the framework",
    ctaText:
      "Explore the papers, market notes, and ongoing theses that inform our strategy work.",
    cta: "Explore research",
  },
  zh: {
    eyebrow: "策略",
    title: "以研究驱动的期权策略",
    intro:
      "我们将基本面判断、市场结构与量化信号转化为风险明确的期权框架。每一个想法都经过统一的研究、仓位与复盘流程。",
    imageAlt: "策略棋子与规划图插图",
    principles: [
      ["研究先行", "先形成可证伪的投资判断，再进行头寸设计。"],
      ["风险明确", "执行前确定仓位、流动性要求与退出条件。"],
      ["适应环境", "根据波动率、趋势与跨资产环境调整风险敞口。"],
    ],
    frameworkEyebrow: "策略框架",
    frameworkTitle: "三种互补视角",
    frameworkIntro: "每套框架拥有不同的优势来源，同时共享统一的组合风险约束。",
    status: "研究框架",
    strategies: [
      {
        number: "01",
        name: "基本面偏向",
        description:
          "通过非对称期权结构，表达对公司、行业或宏观主题的差异化判断。",
        focus: "催化剂 · 估值 · 情景分析",
      },
      {
        number: "02",
        name: "技术面偏向",
        description:
          "结合价格结构、波动率行为与仓位信号，识别战术性进入和退出时点。",
        focus: "趋势 · 波动率 · 市场结构",
      },
      {
        number: "03",
        name: "多策略",
        description:
          "组合相互独立的信号与结构，降低对单一市场环境的依赖。",
        focus: "分散化 · 配置 · 回撤控制",
      },
    ],
    processEyebrow: "运作流程",
    processTitle: "从信号到复盘",
    process: [
      ["发现", "识别可以量化验证的市场错位。"],
      ["构建", "选择期权表达方式和收益结构。"],
      ["控制", "设定仓位、流动性和损失约束。"],
      ["复盘", "持续检查假设并记录结果。"],
    ],
    ctaTitle: "框架背后的研究",
    ctaText: "浏览支撑策略工作的论文、市场观察和进行中的研究主题。",
    cta: "浏览研究",
  },
};

const principleIcons = [ScanSearch, ShieldCheck, Compass];
const strategyIcons = [BarChart3, Activity, Layers3];
const strategyAccents = ["#4F63F6", "#16A39A", "#E39A32"];
const processIcons = [ScanSearch, Layers3, Scale, Activity];

export default function StrategyPage() {
  const { language } = useLanguage();
  const t = content[language];

  return (
    <main className="min-h-screen bg-white text-[#18233A]">
      <section className="border-b border-[#E7ECF5] bg-[#F8FAFC] px-6 py-12 sm:px-8 sm:py-14 lg:px-12">
        <div className="mx-auto grid max-w-7xl items-center gap-10 lg:grid-cols-[1fr_420px]">
          <div className="max-w-3xl">
            <p className="text-sm font-bold uppercase text-[#4F63F6]">{t.eyebrow}</p>
            <h1 className="mt-3 text-4xl font-black leading-tight text-[#18233A] sm:text-5xl">
              {t.title}
            </h1>
            <p className="mt-5 max-w-2xl text-lg leading-8 text-[#5B6780]">{t.intro}</p>

            <div className="mt-9 grid gap-5 border-t border-[#DCE3EF] pt-7 sm:grid-cols-3">
              {t.principles.map(([title, text], index) => {
                const Icon = principleIcons[index];
                return (
                  <div key={title} className="flex gap-3">
                    <Icon className="mt-0.5 h-5 w-5 flex-none text-[#4F63F6]" />
                    <div>
                      <h2 className="text-sm font-bold text-[#18233A]">{title}</h2>
                      <p className="mt-1 text-sm leading-6 text-[#5B6780]">{text}</p>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          <Image
            src="/assets/strategy-icon.png"
            alt={t.imageAlt}
            width={520}
            height={520}
            priority
            className="mx-auto w-full max-w-[360px] object-contain mix-blend-multiply lg:max-w-[420px]"
          />
        </div>
      </section>

      <section className="px-6 py-14 sm:px-8 lg:px-12 lg:py-16">
        <div className="mx-auto max-w-7xl">
          <div className="max-w-3xl">
            <p className="text-sm font-bold uppercase text-[#4F63F6]">{t.frameworkEyebrow}</p>
            <h2 className="mt-2 text-3xl font-black text-[#18233A] sm:text-4xl">
              {t.frameworkTitle}
            </h2>
            <p className="mt-4 text-base leading-7 text-[#5B6780]">{t.frameworkIntro}</p>
          </div>

          <div className="mt-9 grid gap-5 lg:grid-cols-3">
            {t.strategies.map((strategy, index) => {
              const Icon = strategyIcons[index];
              const accent = strategyAccents[index];
              return (
                <article
                  key={strategy.number}
                  className="flex min-h-[300px] flex-col rounded-lg border border-[#E7ECF5] bg-white p-6 shadow-[0_12px_30px_rgba(39,59,154,0.06)]"
                  style={{ borderTopColor: accent, borderTopWidth: 3 }}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-[#778195]">{strategy.number}</span>
                    <Icon className="h-5 w-5" style={{ color: accent }} />
                  </div>
                  <div className="mt-8">
                    <span className="inline-flex rounded-full bg-[#F3F5F9] px-3 py-1 text-xs font-bold text-[#5B6780]">
                      {t.status}
                    </span>
                    <h3 className="mt-4 text-2xl font-black text-[#18233A]">{strategy.name}</h3>
                    <p className="mt-3 text-sm leading-6 text-[#5B6780]">{strategy.description}</p>
                  </div>
                  <p className="mt-auto border-t border-[#E7ECF5] pt-5 text-xs font-bold text-[#273B9A]">
                    {strategy.focus}
                  </p>
                </article>
              );
            })}
          </div>
        </div>
      </section>

      <section className="bg-[#18233A] px-6 py-14 text-white sm:px-8 lg:px-12">
        <div className="mx-auto max-w-7xl">
          <p className="text-sm font-bold uppercase text-[#A8B2FF]">{t.processEyebrow}</p>
          <h2 className="mt-2 text-3xl font-black sm:text-4xl">{t.processTitle}</h2>
          <div className="mt-9 grid gap-px overflow-hidden rounded-lg bg-white/15 sm:grid-cols-2 lg:grid-cols-4">
            {t.process.map(([title, text], index) => {
              const Icon = processIcons[index];
              return (
                <div key={title} className="min-h-[170px] bg-[#18233A] p-6">
                  <div className="flex items-center justify-between">
                    <Icon className="h-5 w-5 text-[#A8B2FF]" />
                    <span className="text-xs font-bold text-white/45">0{index + 1}</span>
                  </div>
                  <h3 className="mt-7 text-lg font-bold">{title}</h3>
                  <p className="mt-2 text-sm leading-6 text-white/65">{text}</p>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      <section className="px-6 py-12 sm:px-8 lg:px-12">
        <div className="mx-auto flex max-w-7xl flex-col gap-5 border-b border-t border-[#E7ECF5] py-8 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="text-2xl font-black text-[#18233A]">{t.ctaTitle}</h2>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-[#5B6780]">{t.ctaText}</p>
          </div>
          <Link
            href="/research"
            className="inline-flex h-11 flex-none items-center justify-center rounded-full bg-[#4F63F6] px-5 text-sm font-bold text-white transition hover:bg-[#273B9A]"
          >
            {t.cta}
            <ArrowRight className="ml-2 h-4 w-4" />
          </Link>
        </div>
      </section>
    </main>
  );
}
