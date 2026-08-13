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
      title: "Smarter Research. Better Decisions.",
      primaryCta: "Explore All Sections",
      secondaryCta: "Our Approach",
      privateCta: "Private Access",
    },
    values: [
      {
        title: "Independent",
        text: "Research without conflicts of interest.",
      },
      {
        title: "Data-Driven",
        text: "Rigor, discipline, and transparent methods.",
      },
      {
        title: "Global",
        text: "Markets, sectors, and opportunities worldwide.",
      },
    ],
    sections: {
      eyebrow: "Sections",
      title: "Explore the public research platform",
      subtitle:
        "Daily Summary, Prediction Market, and live monitoring tools now live behind Private Access. The public homepage stays focused on open research, strategy, and thesis discovery.",
    },
    private: {
      title: "Need internal dashboards?",
      text:
        "Authorized users can sign in for live monitors, prediction market signals, daily briefs, and private research operations.",
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
      title: "更聪明的研究，更高质量的决策。",
      primaryCta: "浏览全部板块",
      secondaryCta: "了解方法论",
      privateCta: "Private Access",
    },
    values: [
      {
        title: "独立",
        text: "不受利益冲突影响的研究判断。",
      },
      {
        title: "数据驱动",
        text: "严谨、纪律化且透明的方法。",
      },
      {
        title: "全球",
        text: "覆盖市场、行业与跨区域机会。",
      },
    ],
    sections: {
      eyebrow: "公开板块",
      title: "浏览公开研究平台",
      subtitle:
        "Daily Summary、Prediction Market 与实时监控工具已收进 Private Access。公开首页聚焦研究、策略与投资主题发现。",
    },
    private: {
      title: "需要内部看板？",
      text:
        "授权用户可登录访问实时监控、预测市场信号、每日简报和私密研究运营工具。",
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

const valueIcons = [ShieldCheck, Database, Globe2];
const metricIcons = [BarChart3, Search, Globe2, ShieldCheck];

export default function Home() {
  const { language } = useLanguage();
  const t = content[language];

  return (
    <main className="min-h-screen bg-white text-[#18233A]">
      <section className="overflow-hidden bg-[linear-gradient(180deg,#FFFFFF_0%,#F8FAFC_100%)]">
        <div className="mx-auto grid max-w-7xl grid-cols-1 items-center gap-12 px-6 py-16 sm:px-8 lg:grid-cols-[0.95fr_1.05fr] lg:px-12 lg:py-20">
          <div>
            <h1 className="max-w-3xl text-5xl font-black leading-[0.98] tracking-tight text-[#18233A] sm:text-6xl lg:text-7xl">
              {t.hero.title}
            </h1>

            <div className="mt-14 flex flex-col gap-3 sm:flex-row sm:mt-16">
              <Link
                href="#sections"
                className="inline-flex h-12 items-center justify-center rounded-full bg-[#4F63F6] px-6 text-sm font-bold text-white shadow-[0_14px_28px_rgba(79,99,246,0.24)] transition hover:bg-[#273B9A]"
              >
                {t.hero.primaryCta}
                <ArrowRight className="ml-2 h-4 w-4" />
              </Link>
              <Link
                href="#approach"
                className="inline-flex h-12 items-center justify-center rounded-full border border-[#E7ECF5] bg-white px-6 text-sm font-bold text-[#273B9A] transition hover:border-[#A8B2FF] hover:bg-[#F8FAFC]"
              >
                {t.hero.secondaryCta}
              </Link>
              <Link
                href="/access"
                className="inline-flex h-12 items-center justify-center rounded-full border border-[#FFD76A] bg-[#FFF8E3] px-6 text-sm font-bold text-[#18233A] transition hover:bg-[#FFEFAF]"
              >
                <LockKeyhole className="mr-2 h-4 w-4" />
                {t.hero.privateCta}
              </Link>
            </div>

            <div id="approach" className="mt-10 grid grid-cols-1 gap-4 sm:grid-cols-3">
              {t.values.map((item, index) => {
                const Icon = valueIcons[index];
                return (
                  <div key={item.title} className="rounded-2xl border border-[#E7ECF5] bg-white p-5 shadow-[0_12px_30px_rgba(39,59,154,0.06)]">
                    <div className="mb-3 inline-flex h-9 w-9 items-center justify-center rounded-full bg-[#EEF2FF] text-[#4F63F6]">
                      <Icon className="h-4 w-4" />
                    </div>
                    <h3 className="text-sm font-bold text-[#18233A]">{item.title}</h3>
                    <p className="mt-2 text-sm leading-6 text-[#5B6780]">{item.text}</p>
                  </div>
                );
              })}
            </div>
          </div>

          <div className="relative isolate">
            <div className="pointer-events-none absolute -inset-6 rounded-[40%] bg-[radial-gradient(circle_at_55%_45%,rgba(79,99,246,0.16),rgba(191,229,139,0.08)_42%,transparent_70%)] blur-2xl" />
            <div className="pointer-events-none absolute inset-x-10 bottom-4 h-24 rounded-full bg-[#A8B2FF]/25 blur-3xl" />
            <Image
              src="/assets/hero-ysjlab-team.png"
              alt="YSJLab team reviewing finance research dashboards"
              width={1400}
              height={1000}
              priority
              className="relative z-10 w-full [mask-image:radial-gradient(ellipse_92%_88%_at_50%_48%,#000_62%,transparent_100%)] [-webkit-mask-image:radial-gradient(ellipse_92%_88%_at_50%_48%,#000_62%,transparent_100%)]"
            />
          </div>
        </div>
      </section>

      <section id="sections" className="bg-white px-6 py-16 sm:px-8 lg:px-12">
        <div className="mx-auto max-w-7xl">
          <div className="mb-10 max-w-3xl">
            <p className="text-sm font-bold uppercase tracking-[0.18em] text-[#4F63F6]">
              {t.sections.eyebrow}
            </p>
            <h2 className="mt-3 text-4xl font-black tracking-tight text-[#18233A] sm:text-5xl">
              {t.sections.title}
            </h2>
            <p className="mt-4 text-lg leading-8 text-[#5B6780]">
              {t.sections.subtitle}
            </p>
          </div>
          <FocusCards />
        </div>
      </section>

      <section className="bg-[#F8FAFC] px-6 py-14 sm:px-8 lg:px-12">
        <div className="mx-auto grid max-w-7xl grid-cols-1 gap-6 lg:grid-cols-[1fr_360px]">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {t.metrics.map(([value, label], index) => {
              const Icon = metricIcons[index];
              return (
                <div key={label} className="rounded-2xl border border-[#E7ECF5] bg-white p-6 shadow-[0_12px_28px_rgba(39,59,154,0.05)]">
                  <Icon className="mb-4 h-5 w-5 text-[#4F63F6]" />
                  <div className="text-2xl font-black text-[#18233A]">{value}</div>
                  <div className="mt-1 text-sm text-[#5B6780]">{label}</div>
                </div>
              );
            })}
          </div>

          <Link
            href="/access"
            className="group flex min-h-[220px] flex-col justify-between rounded-2xl border border-[#A8B2FF] bg-[#273B9A] p-7 text-white shadow-[0_18px_44px_rgba(39,59,154,0.18)] transition hover:-translate-y-1"
          >
            <div>
              <div className="mb-4 inline-flex h-11 w-11 items-center justify-center rounded-full bg-white/12">
                <LockKeyhole className="h-5 w-5" />
              </div>
              <h3 className="text-2xl font-black">{t.private.title}</h3>
              <p className="mt-3 text-sm leading-6 text-white/78">{t.private.text}</p>
            </div>
            <span className="mt-6 inline-flex items-center text-sm font-bold">
              {t.private.action}
              <ArrowRight className="ml-2 h-4 w-4 transition group-hover:translate-x-1" />
            </span>
          </Link>
        </div>
      </section>

      <footer className="border-t border-[#E7ECF5] bg-white px-6 py-8 sm:px-8 lg:px-12">
        <div className="mx-auto flex max-w-7xl flex-col gap-6 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <BrandMark size="footer" />
            <p className="mt-2 max-w-xl text-sm text-[#5B6780]">{t.footer}</p>
          </div>
          <div className="flex flex-col items-start gap-2 sm:items-end">
            <Link
              href="/contact"
              className="inline-flex items-center rounded-full border border-[#E7ECF5] bg-[#F8FAFC] px-4 py-2 text-sm font-bold text-[#273B9A] transition hover:border-[#A8B2FF] hover:bg-white"
            >
              {t.contact}
              <ArrowRight className="ml-2 h-4 w-4" />
            </Link>
            <a
              href="mailto:contact@ysjlab.com"
              className="text-sm font-semibold text-[#4F63F6] hover:underline"
            >
              {t.contactHint}: contact@ysjlab.com
            </a>
            <p className="text-sm text-[#5B6780]">{t.copyright}</p>
          </div>
        </div>
      </footer>
    </main>
  );
}
