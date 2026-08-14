"use client";

import Image from "next/image";
import Link from "next/link";
import {
  ArrowRight,
  BarChart3,
  Database,
  Globe2,
  LockKeyhole,
  Search,
  ShieldCheck,
} from "lucide-react";
import FocusCards from "@/components/FocusCards";
import BrandMark from "@/components/BrandMark";
import { useLanguage } from "@/contexts/LanguageContext";

const content = {
  en: {
    hero: {
      kicker: "YSJLab Research Systems",
      title: "Independent Research. Disciplined Systems.",
      copy:
        "A public research layer for market perspective, with private operating systems for live monitors, probability signals, daily briefs, and internal scoring.",
      primaryCta: "Explore Research",
      secondaryCta: "Private Access",
    },
    values: [
      ["Global", "Markets observed across public assets"],
      ["Systematic", "Repeatable workflows and documented assumptions"],
      ["Diligent", "Risk-aware tools for live monitoring"],
    ],
    sections: {
      eyebrow: "Sections",
      title: "Public perspective, private operating layer.",
      subtitle:
        "Daily Summary, Prediction Market, CN Option VIX, and Stock Grader stay behind controlled access. Public pages remain focused on research, strategy, and thesis discovery.",
    },
    pillars: [
      {
        label: "01",
        title: "Research Foundation",
        text: "Independent market research, strategy notes, and ongoing theses give the public site a clear editorial spine.",
      },
      {
        label: "02",
        title: "Systematic Intelligence",
        text: "Private dashboards turn volatility, probability markets, market calendars, and scorecards into operational signals.",
      },
      {
        label: "03",
        title: "Controlled Access",
        text: "Internal tools remain gated, session-based, and separated from public-facing company content.",
      },
    ],
    private: {
      title: "Need internal dashboards?",
      text:
        "Authorized users can enter the private portal for live monitors, prediction market signals, daily briefs, and scoring systems.",
      action: "Enter Private Access",
    },
    metrics: [
      ["10K+", "Community Members"],
      ["1,200+", "Research Reports"],
      ["80+", "Markets Covered"],
      ["Independent", "No Conflicts"],
    ],
    footer:
      "Independent financial research and strategy systems for global market participants.",
    contact: "Contact",
    contactHint: "Email us",
    copyright: "© 2026 YSJLab. All rights reserved.",
  },
  zh: {
    hero: {
      kicker: "YSJLab 研究系统",
      title: "独立研究，纪律化系统。",
      copy:
        "公开层承载市场观点与研究内容，私密层承载实时监控、预测市场信号、每日简报和内部评分系统。",
      primaryCta: "浏览研究",
      secondaryCta: "Private Access",
    },
    values: [
      ["Global", "覆盖公开资产与全球市场"],
      ["Systematic", "可重复的流程与有记录的假设"],
      ["Diligent", "围绕风险意识搭建实时工具"],
    ],
    sections: {
      eyebrow: "平台板块",
      title: "公开观点层，私密运营层。",
      subtitle:
        "Daily Summary、Prediction Market、中国期权 VIX 与 Stock Grader 保持在受控访问之后。公开页面聚焦研究、策略与投资主题发现。",
    },
    pillars: [
      {
        label: "01",
        title: "研究基础",
        text: "独立市场研究、策略文章和进行中的 thesis 构成公开网站的清晰内容骨架。",
      },
      {
        label: "02",
        title: "系统化情报",
        text: "私密看板把波动率、预测市场、市场日历和评分模型转化为可执行的运营信号。",
      },
      {
        label: "03",
        title: "受控访问",
        text: "内部工具保持登录、会话和权限隔离，不混入公开公司展示页面。",
      },
    ],
    private: {
      title: "需要内部看板？",
      text:
        "授权用户可进入 Private Access，访问实时监控、预测市场信号、每日简报和评分系统。",
      action: "进入 Private Access",
    },
    metrics: [
      ["10K+", "社区成员"],
      ["1,200+", "研究报告"],
      ["80+", "覆盖市场"],
      ["独立", "无利益冲突"],
    ],
    footer: "为全球市场参与者提供独立金融研究与策略系统。",
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
              <Link
                href="/access"
                className="inline-flex min-h-12 items-center justify-center border border-white/30 bg-white/10 px-6 text-sm font-black text-white transition hover:bg-white/18"
              >
                <LockKeyhole className="mr-2 h-4 w-4" />
                {t.hero.secondaryCta}
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
        <div className="mx-auto grid max-w-7xl grid-cols-1 gap-8 lg:grid-cols-[1fr_380px]">
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

          <Link
            href="/access"
            className="group flex min-h-[230px] flex-col justify-between border border-[#D7B46A] bg-[#F8F1E3] p-7 text-[#111827] transition hover:bg-[#EAD7AD]"
          >
            <div>
              <div className="mb-4 inline-flex h-11 w-11 items-center justify-center bg-[#111827] text-[#D7B46A]">
                <LockKeyhole className="h-5 w-5" />
              </div>
              <h3 className="text-2xl font-semibold">{t.private.title}</h3>
              <p className="mt-3 text-sm leading-6 text-[#5F4820]">{t.private.text}</p>
            </div>
            <span className="mt-6 inline-flex items-center text-sm font-black">
              {t.private.action}
              <ArrowRight className="ml-2 h-4 w-4 transition group-hover:translate-x-1" />
            </span>
          </Link>
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
