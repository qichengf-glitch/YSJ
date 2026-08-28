"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import {
  Activity,
  ArrowRight,
  BarChart3,
  Gauge,
  LockKeyhole,
  LogOut,
  ShieldCheck,
  TrendingUp,
} from "lucide-react";
import { useLanguage } from "@/contexts/LanguageContext";

const copy = {
  en: {
    eyebrow: "Access Controlled",
    title: "Quant Monitor",
    subtitle:
      "Enter the internal market-monitoring workspace for live indicators, probability dashboards, and scoring systems.",
    operatingLayer: "Monitoring layer",
    operatingText:
      "This page is the controlled entry point for the company’s internal quantitative monitoring modules.",
    sessionText: "Your browser session remains active for 12 hours after sign-in.",
    passcode: "Access Code",
    passcodePlaceholder: "Enter access code",
    submit: "Enter Portal",
    signingIn: "Verifying...",
    invalid: "The access code is not valid.",
    granted: "Access granted",
    grantedText: "Internal monitoring systems",
    vixTitle: "CN Option VIX Monitor",
    vixDescription:
      "Live five-minute and half-day China financial-option volatility dashboard.",
    vixCadence: "5-minute / half-day",
    vixStatus: "Live",
    vixBullets: ["China option VIX chain", "Relative sector spread", "Freshness and quality checks"],
    marketTitle: "Prediction Market",
    marketDescription: "Polymarket macro probability, liquidity, and tracked-wallet activity.",
    marketCadence: "Scheduled sync",
    marketStatus: "Live",
    marketBullets: ["Macro probability moves", "Liquidity and volume spikes", "Tracked-wallet exposure"],
    stockGraderTitle: "Stock Grader",
    stockGraderDescription: "US equity fundamental scores, category reasons, and weekly review queue.",
    stockGraderCadence: "Weekly / manual review",
    stockGraderStatus: "Review",
    stockGraderBullets: ["10-category scorecard", "Admin override audit", "Ticker-level rationale"],
    open: "Open",
    logout: "Sign out",
  },
  zh: {
    eyebrow: "受控访问",
    title: "量化指标监控",
    subtitle:
      "进入内部市场监控工作台，查看实时指标、预测市场与股票评分系统。",
    operatingLayer: "监控层",
    operatingText:
      "这里是公司内部量化监控模块的受控入口。",
    sessionText: "登录后，本浏览器会保持 12 小时会话。",
    passcode: "访问码",
    passcodePlaceholder: "输入访问码",
    submit: "进入入口",
    signingIn: "验证中...",
    invalid: "访问码无效。",
    granted: "已授权访问",
    grantedText: "内部监控系统",
    vixTitle: "中国金融期权 VIX 监控",
    vixDescription:
      "五分钟实时与半日频中国金融期权波动率看板。",
    vixCadence: "5 分钟 / 半日频",
    vixStatus: "实时",
    vixBullets: ["中国期权 VIX 链条", "板块相对波动率 spread", "数据新鲜度与质量检查"],
    marketTitle: "预测市场",
    marketDescription: "Polymarket 宏观概率、流动性与跟踪钱包活动。",
    marketCadence: "定时同步",
    marketStatus: "实时",
    marketBullets: ["宏观事件概率变化", "流动性与成交量异动", "跟踪钱包风险暴露"],
    stockGraderTitle: "股票基本面评分",
    stockGraderDescription: "美股基本面评分、分类理由与每周复核队列。",
    stockGraderCadence: "每周 / 人工复核",
    stockGraderStatus: "复核",
    stockGraderBullets: ["10 项分类评分", "管理员 override 审计", "个股评分理由追踪"],
    open: "打开",
    logout: "退出登录",
  },
};

type AccessPortalProps = {
  isAuthenticated: boolean;
};

export default function AccessPortal({ isAuthenticated }: AccessPortalProps) {
  const { language } = useLanguage();
  const t = copy[language];
  const [authenticated, setAuthenticated] = useState(isAuthenticated);
  const [passcode, setPasscode] = useState("");
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    let active = true;

    async function syncSession() {
      try {
        const response = await fetch("/api/access/session", { cache: "no-store" });
        if (!response.ok) {
          return;
        }
        const data = (await response.json()) as { authenticated?: boolean };
        if (active) {
          setAuthenticated(Boolean(data.authenticated));
        }
      } catch {
        // Keep the server-rendered state if the lightweight session check fails.
      }
    }

    function handlePageShow() {
      void syncSession();
    }

    void syncSession();
    window.addEventListener("pageshow", handlePageShow);
    return () => {
      active = false;
      window.removeEventListener("pageshow", handlePageShow);
    };
  }, []);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSubmitting(true);
    setError("");

    const response = await fetch("/api/access/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ passcode }),
    });

    setIsSubmitting(false);

    if (!response.ok) {
      setError(t.invalid);
      return;
    }

    setAuthenticated(true);
    setPasscode("");
  }

  async function handleLogout() {
    await fetch("/api/access/logout", { method: "POST" });
    setAuthenticated(false);
  }

  const tools = [
    {
      title: t.vixTitle,
      description: t.vixDescription,
      cadence: t.vixCadence,
      status: t.vixStatus,
      bullets: t.vixBullets,
      href: "/cn-option-vix",
      icon: BarChart3,
    },
    {
      title: t.marketTitle,
      description: t.marketDescription,
      cadence: t.marketCadence,
      status: t.marketStatus,
      bullets: t.marketBullets,
      href: "/prediction-markets",
      icon: Activity,
    },
    {
      title: t.stockGraderTitle,
      description: t.stockGraderDescription,
      cadence: t.stockGraderCadence,
      status: t.stockGraderStatus,
      bullets: t.stockGraderBullets,
      href: "/stock-grader",
      icon: TrendingUp,
    },
  ];

  return (
    <main className="min-h-[calc(100vh-4rem)] bg-[radial-gradient(circle_at_top_left,rgba(215,180,106,0.16),transparent_32%),linear-gradient(180deg,#FBFAF7_0%,#F5EFE4_100%)] text-[#111827]">
      <section className="mx-auto max-w-7xl px-6 py-10 sm:px-8 lg:px-12 lg:py-14">
        <div className="mb-8 flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <div className="mb-5 inline-flex items-center gap-2 border border-[#D7B46A] bg-[#FFFDF8]/80 px-4 py-2 text-xs font-black uppercase tracking-[0.22em] text-[#8A6A2F] shadow-[0_12px_32px_rgba(78,56,21,0.08)] backdrop-blur-xl">
              {authenticated ? <ShieldCheck className="h-3.5 w-3.5" /> : <LockKeyhole className="h-3.5 w-3.5" />}
              {authenticated ? t.granted : t.eyebrow}
            </div>
            <h1 className="max-w-4xl text-5xl font-semibold leading-[1.02] text-[#111827] sm:text-6xl lg:text-7xl">
              {t.title}
            </h1>
            <p className="mt-7 max-w-3xl text-lg leading-8 text-[#5B6472]">{t.subtitle}</p>
          </div>
          {authenticated ? (
            <button
              type="button"
              onClick={handleLogout}
              className="inline-flex h-11 w-fit items-center gap-2 border border-[#E6DDCD] bg-[#FFFDF8] px-4 text-sm font-black text-[#5B6472] transition hover:border-[#D7B46A] hover:text-[#111827]"
            >
              <LogOut className="h-4 w-4" />
              {t.logout}
            </button>
          ) : null}
        </div>

        {authenticated ? (
          <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
            {tools.map((tool) => {
              const Icon = tool.icon;
              return (
                <Link
                  key={tool.href}
                  href={tool.href}
                  className="group flex min-h-[360px] flex-col border border-[#E6DDCD] bg-[#FFFDF8]/82 p-6 shadow-[0_18px_48px_rgba(78,56,21,0.08)] backdrop-blur-xl transition hover:-translate-y-0.5 hover:border-[#D7B46A] hover:bg-white hover:shadow-[0_24px_60px_rgba(78,56,21,0.14)]"
                >
                  <span className="flex items-start justify-between gap-4">
                    <span className="inline-flex h-12 w-12 flex-none items-center justify-center bg-[#111827] text-[#D7B46A]">
                        <Icon className="h-5 w-5" />
                    </span>
                    <span className="border border-[#D7B46A] bg-[#F8F1E3] px-2 py-1 text-[10px] font-black uppercase tracking-[0.12em] text-[#8A6A2F]">
                      {tool.status}
                    </span>
                  </span>
                  <span className="mt-6 block">
                    <span className="text-2xl font-black leading-tight text-[#111827]">{tool.title}</span>
                    <span className="mt-3 block text-sm leading-6 text-[#5B6472]">{tool.description}</span>
                  </span>
                  <span className="mt-6 block border-t border-[#E6DDCD] pt-5">
                    <span className="mb-3 inline-flex items-center gap-2 text-xs font-black uppercase tracking-[0.12em] text-[#8A6A2F]">
                      <Gauge className="h-4 w-4" />
                      {tool.cadence}
                    </span>
                  </span>
                  <span className="grid gap-2 text-sm leading-5 text-[#5B6472]">
                    {tool.bullets.map((bullet) => (
                      <span key={bullet} className="flex gap-2">
                        <span className="mt-2 h-1.5 w-1.5 flex-none bg-[#D7B46A]" />
                        <span>{bullet}</span>
                      </span>
                    ))}
                  </span>
                  <span className="mt-auto inline-flex items-center gap-2 pt-6 text-sm font-black text-[#8A6A2F]">
                    {t.open}
                    <ArrowRight className="h-4 w-4 transition group-hover:translate-x-0.5" />
                  </span>
                </Link>
              );
            })}
          </div>
        ) : (
          <div className="max-w-xl border border-[#E6DDCD] bg-[#FFFDF8] p-6 shadow-[0_24px_60px_rgba(78,56,21,0.12)]">
            <form onSubmit={handleSubmit} className="space-y-4">
              <label className="block">
                <span className="text-sm font-black text-[#111827]">{t.passcode}</span>
                <input
                  value={passcode}
                  onChange={(event) => setPasscode(event.target.value)}
                  type="password"
                  placeholder={t.passcodePlaceholder}
                  className="mt-2 h-12 w-full border border-[#E6DDCD] bg-[#FBFAF7] px-4 text-base font-semibold text-[#111827] outline-none transition focus:border-[#D7B46A] focus:ring-2 focus:ring-[#D7B46A]/25"
                />
              </label>
              {error ? (
                <div className="border border-rose-200 bg-rose-50 px-4 py-3 text-sm font-semibold text-rose-700">
                  {error}
                </div>
              ) : null}
              <button
                type="submit"
                disabled={isSubmitting}
                className="inline-flex h-12 w-full items-center justify-center bg-[#111827] px-5 text-sm font-black text-white transition hover:bg-[#2B3445] disabled:cursor-not-allowed disabled:opacity-70"
              >
                {isSubmitting ? t.signingIn : t.submit}
                <ArrowRight className="ml-2 h-4 w-4" />
              </button>
            </form>
          </div>
        )}
      </section>
    </main>
  );
}
