"use client";

import { FormEvent, useState } from "react";
import Image from "next/image";
import Link from "next/link";
import {
  Activity,
  ArrowRight,
  BarChart3,
  Clock3,
  Database,
  LockKeyhole,
  LogOut,
  ShieldCheck,
} from "lucide-react";
import { useLanguage } from "@/contexts/LanguageContext";

const copy = {
  en: {
    eyebrow: "Private Access",
    title: "Client portal for internal market systems",
    subtitle:
      "Sign in to reach restricted dashboards, monitoring tools, and research operations prepared for approved YSJ users.",
    statusLabel: "Portal scope",
    statusItems: ["Market dashboards", "Live volatility monitor", "Research operations"],
    sessionLabel: "Session",
    sessionValue: "12h secure browser session",
    dataLabel: "Data",
    dataValue: "Live systems connect after sign-in",
    passcode: "Access Code",
    passcodePlaceholder: "Enter access code",
    submit: "Enter Portal",
    signingIn: "Verifying...",
    invalid: "The access code is not valid.",
    granted: "Access granted",
    grantedText: "Choose a system below. Your session stays active for 12 hours on this browser.",
    vixTitle: "CN Option VIX Monitor",
    vixDescription:
      "Live five-minute and half-day China financial-option volatility dashboard.",
    marketTitle: "Market Radar",
    marketDescription: "US earnings, event updates, and market calendar.",
    dailyTitle: "Daily Summary",
    dailyDescription: "Daily cross-asset brief for equities, FX, rates, and commodities.",
    open: "Open",
    logout: "Sign out",
  },
  zh: {
    eyebrow: "私密访问",
    title: "内部市场系统客户端入口",
    subtitle:
      "登录后可进入已授权的看板、监控工具和研究运营系统。",
    statusLabel: "入口范围",
    statusItems: ["市场看板", "实时波动率监控", "研究运营"],
    sessionLabel: "会话",
    sessionValue: "12 小时安全浏览器会话",
    dataLabel: "数据",
    dataValue: "登录后连接实时系统",
    passcode: "访问码",
    passcodePlaceholder: "输入访问码",
    submit: "进入入口",
    signingIn: "验证中...",
    invalid: "访问码无效。",
    granted: "已授权访问",
    grantedText: "请选择下方系统。本浏览器会保持 12 小时登录状态。",
    vixTitle: "中国金融期权 VIX 监控",
    vixDescription:
      "五分钟实时与半日频中国金融期权波动率看板。",
    marketTitle: "市场雷达",
    marketDescription: "美股财报、事件更新与市场日历。",
    dailyTitle: "每日市场日报",
    dailyDescription: "股票、外汇、利率与商品的跨资产日报。",
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
      external: false,
      icon: BarChart3,
    },
    {
      title: t.marketTitle,
      description: t.marketDescription,
      href: "/market-radar",
      external: false,
      icon: ShieldCheck,
    },
    {
      title: t.dailyTitle,
      description: t.dailyDescription,
      href: "/daily-summary",
      external: false,
      icon: ShieldCheck,
    },
  ];

  return (
    <main className="min-h-[calc(100vh-4rem)] overflow-hidden bg-[linear-gradient(180deg,#FFFFFF_0%,#F8FAFC_100%)] text-[#18233A]">
      <section className="relative mx-auto grid max-w-7xl grid-cols-1 items-start gap-10 px-6 pb-16 pt-12 sm:px-8 lg:grid-cols-[minmax(0,1fr)_460px] lg:px-12 lg:pb-20 lg:pt-20">
        <div className="pointer-events-none absolute inset-0 -z-0 bg-[radial-gradient(circle_at_18%_22%,rgba(168,178,255,0.20),transparent_30%),radial-gradient(circle_at_82%_70%,rgba(191,229,139,0.18),transparent_34%)]" />
        <div className="relative z-10">
          <div className="mb-5 inline-flex items-center gap-2 rounded-full border border-[#E7ECF5] bg-white px-4 py-2 text-xs font-bold uppercase tracking-[0.18em] text-[#4F63F6] shadow-[0_10px_24px_rgba(79,99,246,0.08)]">
            <LockKeyhole className="h-3.5 w-3.5" />
            {t.eyebrow}
          </div>
          <h1 className="max-w-4xl text-4xl font-black leading-[0.98] tracking-tight text-[#18233A] sm:text-5xl lg:text-6xl">
            {t.title}
          </h1>
          <p className="mt-6 max-w-3xl text-lg leading-8 text-[#5B6780] sm:text-xl">
            {t.subtitle}
          </p>

          <div className="mt-10 grid max-w-4xl grid-cols-1 gap-4 sm:grid-cols-3">
            <div className="rounded-2xl border border-[#E7ECF5] bg-white p-5 shadow-[0_12px_30px_rgba(39,59,154,0.06)]">
              <div className="flex items-center gap-2 text-sm font-bold text-[#273B9A]">
                <Activity className="h-4 w-4" />
                {t.statusLabel}
              </div>
              <div className="mt-3 space-y-1.5 text-sm text-[#5B6780]">
                {t.statusItems.map((item) => (
                  <div key={item}>{item}</div>
                ))}
              </div>
            </div>
            <div className="rounded-2xl border border-[#E7ECF5] bg-white p-5 shadow-[0_12px_30px_rgba(39,59,154,0.06)]">
              <div className="flex items-center gap-2 text-sm font-bold text-[#273B9A]">
                <Clock3 className="h-4 w-4" />
                {t.sessionLabel}
              </div>
              <p className="mt-3 text-sm leading-6 text-[#5B6780]">{t.sessionValue}</p>
            </div>
            <div className="rounded-2xl border border-[#E7ECF5] bg-white p-5 shadow-[0_12px_30px_rgba(39,59,154,0.06)]">
              <div className="flex items-center gap-2 text-sm font-bold text-[#273B9A]">
                <Database className="h-4 w-4" />
                {t.dataLabel}
              </div>
              <p className="mt-3 text-sm leading-6 text-[#5B6780]">{t.dataValue}</p>
            </div>
          </div>

          <div className="mt-8 max-w-xl rounded-3xl border border-[#E7ECF5] bg-white/75 p-5 shadow-[0_16px_36px_rgba(39,59,154,0.08)] backdrop-blur">
            <Image
              src="/assets/private-dashboard-icon.png"
              alt="Private dashboard illustration"
              width={520}
              height={320}
              className="mx-auto max-h-44 w-full object-contain"
            />
          </div>
        </div>

        <div className="relative z-10 rounded-2xl border border-[#E7ECF5] bg-white p-6 shadow-[0_22px_55px_rgba(39,59,154,0.13)]">
          <div className="mb-5 flex items-center justify-between border-b border-[#E7ECF5] pb-4">
            <div>
              <div className="text-xs font-bold uppercase tracking-[0.16em] text-[#A8B2FF]">
                YSJLab
              </div>
              <div className="mt-1 text-lg font-black text-[#18233A]">
                {authenticated ? t.granted : t.eyebrow}
              </div>
            </div>
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#EEF2FF] text-[#4F63F6]">
              {authenticated ? <ShieldCheck className="h-5 w-5" /> : <LockKeyhole className="h-5 w-5" />}
            </div>
          </div>

          {authenticated ? (
            <div>
              <div className="mb-6 flex items-start justify-between gap-4">
                <div>
                  <p className="mt-2 text-sm leading-6 text-[#5B6780]">{t.grantedText}</p>
                </div>
                <button
                  type="button"
                  onClick={handleLogout}
                  className="inline-flex h-10 w-10 items-center justify-center rounded-xl border border-[#E7ECF5] text-[#5B6780] transition hover:border-[#A8B2FF] hover:text-[#4F63F6]"
                  aria-label={t.logout}
                >
                  <LogOut className="h-4 w-4" />
                </button>
              </div>

              <div className="space-y-3">
                {tools.map((tool) => {
                  const Icon = tool.icon;
                  const className =
                    "group flex items-center justify-between gap-4 rounded-2xl border border-[#E7ECF5] bg-[#F8FAFC] p-4 transition hover:-translate-y-0.5 hover:border-[#A8B2FF] hover:bg-white hover:shadow-[0_12px_28px_rgba(39,59,154,0.10)]";
                  const body = (
                    <>
                      <div className="flex min-w-0 items-start gap-3">
                        <span className="mt-0.5 inline-flex h-10 w-10 flex-none items-center justify-center rounded-xl bg-[#EEF2FF] text-[#4F63F6]">
                          <Icon className="h-5 w-5" />
                        </span>
                        <span>
                          <span className="block text-sm font-bold text-[#18233A]">{tool.title}</span>
                          <span className="mt-1 block text-sm leading-5 text-[#5B6780]">
                            {tool.description}
                          </span>
                        </span>
                      </div>
                      <span className="inline-flex flex-none items-center gap-1 text-sm font-bold text-[#4F63F6]">
                        {t.open}
                        <ArrowRight className="h-4 w-4 transition group-hover:translate-x-0.5" />
                      </span>
                    </>
                  );

                  return tool.external ? (
                    <a
                      key={tool.href}
                      href={tool.href}
                      target="_blank"
                      rel="noreferrer"
                      className={className}
                    >
                      {body}
                    </a>
                  ) : (
                    <Link key={tool.href} href={tool.href} className={className}>
                      {body}
                    </Link>
                  );
                })}
              </div>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-5">
              <div>
                <label htmlFor="accessCode" className="mb-2 block text-sm font-bold text-[#18233A]">
                  {t.passcode}
                </label>
                <input
                  id="accessCode"
                  type="password"
                  value={passcode}
                  onChange={(event) => setPasscode(event.target.value)}
                  placeholder={t.passcodePlaceholder}
                  className="h-12 w-full rounded-xl border border-[#E7ECF5] bg-[#F8FAFC] px-4 text-[#18233A] outline-none transition placeholder:text-[#9AA5BA] focus:border-[#A8B2FF] focus:ring-2 focus:ring-[#A8B2FF]/25"
                  autoComplete="current-password"
                  required
                />
                {error ? <p className="mt-2 text-sm text-red-600">{error}</p> : null}
              </div>
              <button
                type="submit"
                disabled={isSubmitting}
                className="inline-flex h-12 w-full items-center justify-center rounded-full bg-[#4F63F6] px-5 text-sm font-bold text-white shadow-[0_14px_28px_rgba(79,99,246,0.24)] transition hover:bg-[#273B9A] disabled:cursor-not-allowed disabled:opacity-70"
              >
                {isSubmitting ? t.signingIn : t.submit}
              </button>
              <div className="rounded-2xl border border-[#E7ECF5] bg-[#F8FAFC] p-4">
                <div className="mb-3 flex items-center gap-2 text-sm font-bold text-[#18233A]">
                  <BarChart3 className="h-4 w-4 text-[#4F63F6]" />
                  {t.vixTitle}
                </div>
                <div className="grid grid-cols-3 gap-2 text-center">
                  {["Overall", "Index", "Hard Tech"].map((label, index) => (
                    <div key={label} className="rounded-xl bg-white px-2 py-3 shadow-[0_8px_18px_rgba(39,59,154,0.06)]">
                      <div className="text-[10px] uppercase tracking-[0.14em] text-[#9AA5BA]">{label}</div>
                      <div className="mt-1 text-sm font-black text-[#18233A]">
                        {["36.6", "25.7", "49.9"][index]}%
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </form>
          )}
        </div>
      </section>
    </main>
  );
}
