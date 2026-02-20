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
    contact: {
      title: "Contact Us",
      intro:
        "Thank you for reaching out to us. Share a few details and we will follow up as quickly as possible.",
      firstName: "First Name",
      lastName: "Last Name",
      companyName: "Company Name",
      email: "Email",
      phoneNumber: "Phone Number",
      systems: "Automated Systems of Interest (if applicable)",
      storage: "Storage Solutions of Interest (if applicable)",
      services: "Services of Interest (if applicable)",
      project: "Tell Us About Your Project",
      submit: "Submit Inquiry",
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
    contact: {
      title: "联系我们",
      intro:
        "感谢您的联系。请填写以下信息，我们会尽快与您沟通。",
      firstName: "名字",
      lastName: "姓氏",
      companyName: "公司名称",
      email: "邮箱",
      phoneNumber: "电话号码",
      systems: "感兴趣的自动化系统（可选）",
      storage: "感兴趣的存储方案（可选）",
      services: "感兴趣的服务（可选）",
      project: "请介绍您的项目",
      submit: "提交咨询",
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

      {/* Contact */}
      <Section fullWidth className="pt-8 sm:pt-10">
        <div className="max-w-7xl mx-auto rounded-3xl border border-[#2a7d93]/20 bg-white/55 backdrop-blur-[1px] px-6 sm:px-8 lg:px-10 py-8 sm:py-10 shadow-[0_16px_40px_rgba(15,23,42,0.06)]">
          <h2 className="font-playfair text-4xl sm:text-5xl text-center text-gray-900 mb-4">
            {t.contact.title}
          </h2>
          <p className="text-lg text-[#184154] text-center max-w-4xl mx-auto mb-8 sm:mb-10">
            {t.contact.intro}
          </p>

          <form className="space-y-6" onSubmit={(e) => e.preventDefault()}>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              <div>
                <label htmlFor="firstName" className="block text-xl font-medium text-slate-700 mb-2">
                  {t.contact.firstName}
                  <span className="text-red-500"> *</span>
                </label>
                <input
                  id="firstName"
                  name="firstName"
                  required
                  className="w-full h-14 rounded-md border border-[#2a7d93] bg-white/70 px-4 text-slate-800 focus:outline-none focus:ring-2 focus:ring-[#2a7d93]/35"
                />
              </div>
              <div>
                <label htmlFor="lastName" className="block text-xl font-medium text-slate-700 mb-2">
                  {t.contact.lastName}
                  <span className="text-red-500"> *</span>
                </label>
                <input
                  id="lastName"
                  name="lastName"
                  required
                  className="w-full h-14 rounded-md border border-[#2a7d93] bg-white/70 px-4 text-slate-800 focus:outline-none focus:ring-2 focus:ring-[#2a7d93]/35"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
              <div>
                <label htmlFor="companyName" className="block text-xl font-medium text-slate-700 mb-2">
                  {t.contact.companyName}
                  <span className="text-red-500"> *</span>
                </label>
                <input
                  id="companyName"
                  name="companyName"
                  required
                  className="w-full h-14 rounded-md border border-[#2a7d93] bg-white/70 px-4 text-slate-800 focus:outline-none focus:ring-2 focus:ring-[#2a7d93]/35"
                />
              </div>
              <div>
                <label htmlFor="email" className="block text-xl font-medium text-slate-700 mb-2">
                  {t.contact.email}
                  <span className="text-red-500"> *</span>
                </label>
                <input
                  id="email"
                  name="email"
                  type="email"
                  required
                  className="w-full h-14 rounded-md border border-[#2a7d93] bg-white/70 px-4 text-slate-800 focus:outline-none focus:ring-2 focus:ring-[#2a7d93]/35"
                />
              </div>
              <div>
                <label htmlFor="phoneNumber" className="block text-xl font-medium text-slate-700 mb-2">
                  {t.contact.phoneNumber}
                  <span className="text-red-500"> *</span>
                </label>
                <input
                  id="phoneNumber"
                  name="phoneNumber"
                  type="tel"
                  required
                  placeholder="+1"
                  className="w-full h-14 rounded-md border border-[#2a7d93] bg-white/70 px-4 text-slate-800 focus:outline-none focus:ring-2 focus:ring-[#2a7d93]/35"
                />
              </div>
            </div>

            <div>
              <label htmlFor="systems" className="block text-xl font-medium text-slate-700 mb-2">
                {t.contact.systems}
              </label>
              <select
                id="systems"
                name="systems"
                className="w-full h-14 rounded-md border border-[#2a7d93] bg-white/70 px-4 text-slate-700 focus:outline-none focus:ring-2 focus:ring-[#2a7d93]/35"
                defaultValue=""
              >
                <option value="" disabled>
                  Select an option
                </option>
                <option value="portfolio-automation">Portfolio Automation</option>
                <option value="signal-monitoring">Signal Monitoring</option>
                <option value="risk-dashboard">Risk Dashboard</option>
              </select>
            </div>

            <div>
              <label htmlFor="storage" className="block text-xl font-medium text-slate-700 mb-2">
                {t.contact.storage}
              </label>
              <select
                id="storage"
                name="storage"
                className="w-full h-14 rounded-md border border-[#2a7d93] bg-white/70 px-4 text-slate-700 focus:outline-none focus:ring-2 focus:ring-[#2a7d93]/35"
                defaultValue=""
              >
                <option value="" disabled>
                  Select an option
                </option>
                <option value="cloud">Cloud</option>
                <option value="hybrid">Hybrid</option>
                <option value="on-premise">On-Premise</option>
              </select>
            </div>

            <div>
              <label htmlFor="services" className="block text-xl font-medium text-slate-700 mb-2">
                {t.contact.services}
              </label>
              <select
                id="services"
                name="services"
                className="w-full h-14 rounded-md border border-[#2a7d93] bg-white/70 px-4 text-slate-700 focus:outline-none focus:ring-2 focus:ring-[#2a7d93]/35"
                defaultValue=""
              >
                <option value="" disabled>
                  Select an option
                </option>
                <option value="research-advisory">Research Advisory</option>
                <option value="strategy-consulting">Strategy Consulting</option>
                <option value="market-intelligence">Market Intelligence</option>
              </select>
            </div>

            <div>
              <label htmlFor="project" className="block text-xl font-medium text-slate-700 mb-2">
                {t.contact.project}
              </label>
              <textarea
                id="project"
                name="project"
                rows={5}
                placeholder="Share your goals, timeline, and constraints..."
                className="w-full rounded-md border border-[#2a7d93] bg-white/70 px-4 py-3 text-slate-800 focus:outline-none focus:ring-2 focus:ring-[#2a7d93]/35"
              />
            </div>

            <div className="flex justify-center pt-2">
              <button
                type="submit"
                className="h-12 px-8 rounded-md bg-primary text-white font-semibold tracking-wide hover:bg-primary-dark transition-colors focus:outline-none focus:ring-2 focus:ring-primary/35"
              >
                {t.contact.submit}
              </button>
            </div>
          </form>
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
