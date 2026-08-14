"use client";

import Image from "next/image";
import Link from "next/link";
import {
  ArrowRight,
  BarChart3,
  Globe2,
  Search,
  ShieldCheck,
} from "lucide-react";
import FocusCards from "@/components/FocusCards";
import BrandMark from "@/components/BrandMark";
import { useLanguage } from "@/contexts/LanguageContext";

const content = {
  en: {
    hero: {
      kicker: "Quantitative Market Monitoring",
      title: "Market Intelligence for Quant Research.",
      copy:
        "A focused workspace for internal research staff to review market indicators, volatility regimes, event probabilities, daily briefs, and scoring outputs.",
      primaryCta: "Explore Research",
    },
    values: [
      ["Monitor", "Live dashboards for market indicators"],
      ["Compare", "Cross-module context for research work"],
      ["Review", "Outputs designed for disciplined follow-up"],
    ],
    sections: {
      eyebrow: "Workspace",
      title: "Research pages plus monitored market systems.",
      subtitle:
        "The public pages hold research material and ongoing theses. Quant Monitor is the controlled entry point for CN Option VIX, Prediction Market, Daily Summary, and Stock Grader.",
    },
    pillars: [
      {
        label: "01",
        title: "Research Context",
        text: "Research notes and ongoing theses provide the human-readable context around monitored market signals.",
      },
      {
        label: "02",
        title: "Quant Monitor",
        text: "Internal modules track volatility, prediction markets, daily market summaries, and equity scoring outputs.",
      },
      {
        label: "03",
        title: "Operator Workflow",
        text: "The interface is tuned for researchers and staff who need to scan, compare, and revisit indicators repeatedly.",
      },
    ],
    metrics: [
      ["4", "Monitoring Modules"],
      ["12h", "Browser Session"],
      ["Live", "Market Feeds"],
      ["Internal", "Research Workflow"],
    ],
    footer:
      "Internal market intelligence workspace for quantitative research and monitoring.",
    contact: "Contact",
    contactHint: "Email us",
    copyright: "© 2026 YSJLab. All rights reserved.",
  },
  zh: {
    hero: {
      kicker: "量化指标监控",
      title: "面向量化研究的市场情报工作台。",
      copy:
        "供内部科研人员和工作人员查看市场指标、波动率状态、事件概率、每日简报与评分输出。",
      primaryCta: "浏览研究",
    },
    values: [
      ["Monitor", "实时看板监控市场指标"],
      ["Compare", "跨模块比较研究上下文"],
      ["Review", "便于复核和后续跟踪的输出"],
    ],
    sections: {
      eyebrow: "工作台",
      title: "研究页面，加上受控的市场监控系统。",
      subtitle:
        "公开页面承载研究材料和进行中的 thesis。量化指标监控是进入中国期权 VIX、Prediction Market、Daily Summary 和 Stock Grader 的受控入口。",
    },
    pillars: [
      {
        label: "01",
        title: "研究语境",
        text: "研究文章和进行中的 thesis 提供对市场信号的人类可读解释背景。",
      },
      {
        label: "02",
        title: "量化指标监控",
        text: "内部模块跟踪波动率、预测市场、每日市场摘要和股票评分输出。",
      },
      {
        label: "03",
        title: "操作工作流",
        text: "界面面向需要反复浏览、比较和复核指标的科研人员与工作人员。",
      },
    ],
    metrics: [
      ["4", "监控模块"],
      ["12h", "浏览器会话"],
      ["Live", "市场数据流"],
      ["Internal", "内部研究流程"],
    ],
    footer: "面向量化研究和市场监控的内部情报工作台。",
    contact: "联系我们",
    contactHint: "发送邮件",
    copyright: "© 2026 YSJLab. 保留所有权利。",
  },
};

const metricIcons = [BarChart3, Search, Globe2, ShieldCheck];

export default function Home() {
  const { language } = useLanguage();
  const t = content[language];

  return (
    <main className="min-h-screen bg-[#FBFAF7] text-[#111827]">
      <section className="relative min-h-[calc(100vh-4rem)] overflow-hidden bg-[#050505] text-white">
        <Image
          src="/assets/hero-ysjlab-team.png"
          alt="YSJLab market research workspace"
          fill
          priority
          className="object-cover opacity-45"
        />
        <div className="absolute inset-0 bg-[linear-gradient(90deg,rgba(0,0,0,0.88),rgba(0,0,0,0.62)_45%,rgba(0,0,0,0.26))]" />
        <div className="absolute inset-x-0 bottom-0 h-40 bg-[linear-gradient(0deg,#050505_0%,rgba(5,5,5,0)_100%)]" />

        <div className="relative z-10 flex min-h-[calc(100vh-4rem)] flex-col justify-end px-6 pb-10 pt-20 sm:px-8 lg:px-12">
          <div className="max-w-6xl">
            <p className="mb-5 text-xs font-black uppercase tracking-[0.24em] text-[#D7B46A]">
              {t.hero.kicker}
            </p>
            <h1 className="max-w-5xl text-5xl font-semibold leading-[1.02] text-white sm:text-6xl lg:text-7xl">
              {t.hero.title}
            </h1>
            <p className="mt-7 max-w-3xl text-base leading-8 text-white/74 sm:text-lg">
              {t.hero.copy}
            </p>
            <div className="mt-9 flex flex-col gap-3 sm:flex-row">
              <Link
                href="#sections"
                className="inline-flex min-h-12 items-center justify-center bg-[#D7B46A] px-6 text-sm font-black text-[#111827] transition hover:bg-[#E5C984]"
              >
                {t.hero.primaryCta}
                <ArrowRight className="ml-2 h-4 w-4" />
              </Link>
            </div>
          </div>

          <div className="mt-14 grid max-w-5xl grid-cols-1 gap-px border-t border-white/16 pt-5 sm:grid-cols-3">
            {t.values.map(([value, label]) => (
              <article key={value} className="pr-8">
                <strong className="block text-2xl font-semibold text-white">{value}</strong>
                <span className="mt-2 block max-w-xs text-sm leading-6 text-white/62">{label}</span>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="grid grid-cols-1 border-y border-[#E6DDCD] bg-[#E6DDCD] lg:grid-cols-3">
        {t.pillars.map((pillar, index) => (
          <article
            key={pillar.title}
            className={`min-h-[260px] p-8 ${
              index === 0
                ? "bg-[#FFFDF8]"
                : index === 1
                  ? "bg-[linear-gradient(135deg,#E2C982_0%,#F1DFB3_100%)]"
                  : "bg-[linear-gradient(135deg,#B98B3E_0%,#D7B46A_100%)]"
            }`}
          >
            <div className="text-xs font-black text-[#8A6A2F]">{pillar.label}</div>
            <h2 className="mt-9 text-2xl font-semibold text-[#111827]">{pillar.title}</h2>
            <p className="mt-4 text-sm leading-7 text-[#5B6472]">{pillar.text}</p>
          </article>
        ))}
      </section>

      <section id="sections" className="bg-[#FBFAF7] px-6 py-20 sm:px-8 lg:px-12">
        <div className="mx-auto max-w-7xl">
          <div className="mb-10 grid grid-cols-1 gap-8 lg:grid-cols-[0.8fr_1.2fr] lg:items-end">
            <div className="bg-[#111827] p-8 text-white">
              <p className="text-xs font-black uppercase tracking-[0.24em] text-[#E5C984]">
                {t.sections.eyebrow}
              </p>
              <h2 className="mt-4 text-4xl font-semibold leading-tight sm:text-5xl">
                {t.sections.title}
              </h2>
            </div>
            <p className="border-l-4 border-[#D7B46A] bg-white/70 p-7 text-lg leading-8 text-[#5B6472]">
              {t.sections.subtitle}
            </p>
          </div>
          <FocusCards />
        </div>
      </section>

      <section className="bg-[#111827] px-6 py-16 text-white sm:px-8 lg:px-12">
        <div className="mx-auto max-w-7xl">
          <div className="grid grid-cols-1 gap-px bg-white/12 sm:grid-cols-2 lg:grid-cols-4">
            {t.metrics.map(([value, label], index) => {
              const Icon = metricIcons[index];
              return (
                <div key={label} className="bg-[#111827] p-6">
                  <Icon className="mb-4 h-5 w-5 text-[#D7B46A]" />
                  <div className="text-2xl font-semibold text-white">{value}</div>
                  <div className="mt-1 text-sm text-white/62">{label}</div>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      <footer className="border-t border-[#E6DDCD] bg-[#FBFAF7] px-6 py-8 sm:px-8 lg:px-12">
        <div className="mx-auto flex max-w-7xl flex-col gap-6 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <BrandMark size="footer" />
            <p className="mt-2 max-w-xl text-sm text-[#5B6472]">{t.footer}</p>
          </div>
          <div className="flex flex-col items-start gap-2 sm:items-end">
            <Link
              href="/contact"
              className="inline-flex items-center border border-[#D7B46A] bg-[#F8F1E3] px-4 py-2 text-sm font-black text-[#5F4820] transition hover:bg-[#D7B46A] hover:text-[#111827]"
            >
              {t.contact}
              <ArrowRight className="ml-2 h-4 w-4" />
            </Link>
            <a
              href="mailto:contact@ysjlab.com"
              className="text-sm font-semibold text-[#8A6A2F] hover:underline"
            >
              {t.contactHint}: contact@ysjlab.com
            </a>
            <p className="text-sm text-[#5B6472]">{t.copyright}</p>
          </div>
        </div>
      </footer>
    </main>
  );
}
