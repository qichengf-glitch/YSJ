"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import {
  ArrowRight,
  BarChart3,
  LockKeyhole,
  LogOut,
  ShieldCheck,
  TrendingUp,
} from "lucide-react";
import { useLanguage } from "@/contexts/LanguageContext";

const copy = {
  en: {
    eyebrow: "Private Access",
    title: "Private Research Operations",
    subtitle:
      "Authorized entry for live monitors, probability dashboards, daily briefs, and internal research systems.",
    operatingLayer: "Operating layer",
    operatingText:
      "The public site stays clean. Approved users enter here for restricted dashboards and tools.",
    sessionText: "Your browser session remains active for 12 hours after sign-in.",
    passcode: "Access Code",
    passcodePlaceholder: "Enter access code",
    submit: "Enter Portal",
    signingIn: "Verifying...",
    invalid: "The access code is not valid.",
    granted: "Access granted",
    grantedText: "Select a system below.",
    vixTitle: "CN Option VIX Monitor",
    vixDescription:
      "Live five-minute and half-day China financial-option volatility dashboard.",
    marketTitle: "Prediction Market",
    marketDescription: "Polymarket macro probability, liquidity, and tracked-wallet activity.",
    dailyTitle: "Daily Summary",
    dailyDescription: "Daily cross-asset brief for equities, FX, rates, and commodities.",
    stockGraderTitle: "Stock Grader",
    stockGraderDescription: "US equity fundamental scores, category reasons, and weekly review queue.",
    open: "Open",
    logout: "Sign out",
  },
  zh: {
    eyebrow: "Private Access",
    title: "私密研究运营入口",
    subtitle:
      "授权进入实时监控、预测市场、每日简报和内部研究系统。",
    operatingLayer: "运营层",
    operatingText:
      "公开网站保持干净展示；被授权用户从这里进入受限看板和内部工具。",
    sessionText: "登录后，本浏览器会保持 12 小时会话。",
    passcode: "访问码",
    passcodePlaceholder: "输入访问码",
    submit: "进入入口",
    signingIn: "验证中...",
    invalid: "访问码无效。",
    granted: "已授权访问",
    grantedText: "请选择下方系统。",
    vixTitle: "中国金融期权 VIX 监控",
    vixDescription:
      "五分钟实时与半日频中国金融期权波动率看板。",
    marketTitle: "预测市场",
    marketDescription: "Polymarket 宏观概率、流动性与跟踪钱包活动。",
    dailyTitle: "每日市场日报",
    dailyDescription: "股票、外汇、利率与商品的跨资产日报。",
    stockGraderTitle: "股票基本面评分",
    stockGraderDescription: "美股基本面评分、分类理由与每周复核队列。",
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
      href: "/cn-option-vix",
      icon: BarChart3,
    },
    {
      title: t.marketTitle,
      description: t.marketDescription,
      href: "/prediction-markets",
      icon: ShieldCheck,
    },
    {
      title: t.dailyTitle,
      description: t.dailyDescription,
      href: "/daily-summary",
      icon: ShieldCheck,
    },
    {
      title: t.stockGraderTitle,
      description: t.stockGraderDescription,
      href: "/stock-grader",
      icon: TrendingUp,
    },
  ];

  return (
    <main className="min-h-[calc(100vh-4rem)] bg-[#FBFAF7] text-[#111827]">
      <section className="mx-auto grid max-w-7xl grid-cols-1 gap-10 px-6 py-12 sm:px-8 lg:grid-cols-[minmax(0,1fr)_440px] lg:px-12 lg:py-20">
        <div className="flex flex-col justify-between">
          <div>
            <div className="mb-5 inline-flex items-center gap-2 border border-[#D7B46A] bg-[#F8F1E3] px-4 py-2 text-xs font-black uppercase tracking-[0.22em] text-[#8A6A2F]">
              <LockKeyhole className="h-3.5 w-3.5" />
              {t.eyebrow}
            </div>
            <h1 className="max-w-4xl text-5xl font-semibold leading-[1.02] text-[#111827] sm:text-6xl lg:text-7xl">
              {t.title}
            </h1>
            <p className="mt-7 max-w-3xl text-lg leading-8 text-[#5B6472]">
              {t.subtitle}
            </p>
          </div>

          <div className="mt-12 grid max-w-4xl grid-cols-1 gap-px border border-[#E6DDCD] bg-[#E6DDCD] sm:grid-cols-2">
            <article className="bg-[#111827] p-7 text-white">
              <div className="text-xs font-black uppercase tracking-[0.22em] text-[#D7B46A]">
                {t.operatingLayer}
              </div>
              <p className="mt-5 text-lg font-semibold leading-8">{t.operatingText}</p>
            </article>
            <article className="bg-[#FFFDF8] p-7">
              <div className="text-xs font-black uppercase tracking-[0.22em] text-[#8A6A2F]">
                Secure Session
              </div>
              <p className="mt-5 text-lg font-semibold leading-8 text-[#5F4820]">{t.sessionText}</p>
            </article>
          </div>
        </div>

        <div className="border border-[#E6DDCD] bg-[#FFFDF8] p-6 shadow-[0_24px_60px_rgba(78,56,21,0.12)]">
          <div className="mb-5 flex items-center justify-between border-b border-[#E6DDCD] pb-4">
            <div>
              <div className="text-xs font-black uppercase tracking-[0.18em] text-[#8A6A2F]">
                YSJLab
              </div>
              <div className="mt-1 text-lg font-semibold text-[#111827]">
                {authenticated ? t.granted : t.eyebrow}
              </div>
            </div>
            <div className="flex h-10 w-10 items-center justify-center bg-[#111827] text-[#D7B46A]">
              {authenticated ? <ShieldCheck className="h-5 w-5" /> : <LockKeyhole className="h-5 w-5" />}
            </div>
          </div>

          {authenticated ? (
            <div>
              <div className="mb-6 flex items-start justify-between gap-4">
                <p className="text-sm leading-6 text-[#5B6472]">{t.grantedText}</p>
                <button
                  type="button"
                  onClick={handleLogout}
                  className="inline-flex h-10 w-10 items-center justify-center border border-[#E6DDCD] text-[#5B6472] transition hover:border-[#D7B46A] hover:text-[#111827]"
                  aria-label={t.logout}
                >
                  <LogOut className="h-4 w-4" />
                </button>
              </div>

              <div className="space-y-3">
                {tools.map((tool) => {
                  const Icon = tool.icon;
                  return (
                    <Link
                      key={tool.href}
                      href={tool.href}
                      className="group flex items-center justify-between gap-4 border border-[#E6DDCD] bg-[#FBFAF7] p-4 transition hover:border-[#D7B46A] hover:bg-white"
                    >
                      <span className="flex min-w-0 items-start gap-3">
                        <span className="mt-0.5 inline-flex h-10 w-10 flex-none items-center justify-center bg-[#F8F1E3] text-[#8A6A2F]">
                          <Icon className="h-5 w-5" />
                        </span>
                        <span>
                          <span className="block text-sm font-black text-[#111827]">{tool.title}</span>
                          <span className="mt-1 block text-sm leading-5 text-[#5B6472]">
                            {tool.description}
                          </span>
                        </span>
                      </span>
                      <span className="inline-flex flex-none items-center gap-1 text-sm font-black text-[#8A6A2F]">
                        {t.open}
                        <ArrowRight className="h-4 w-4 transition group-hover:translate-x-0.5" />
                      </span>
                    </Link>
                  );
                })}
              </div>
            </div>
          ) : (
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
          )}
        </div>
      </section>
    </main>
  );
}
