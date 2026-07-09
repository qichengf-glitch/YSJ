"use client";

import Image from "next/image";
import Link from "next/link";
import { useLanguage } from "@/contexts/LanguageContext";

const sharedItems = [
  {
    href: "/research",
    image:
      "https://images.unsplash.com/photo-1551288049-bebda4e38f71?auto=format&fit=crop&w=1200&q=80",
  },
  {
    href: "/strategy",
    image:
      "https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?auto=format&fit=crop&w=1200&q=80",
  },
  {
    href: "/research/ongoing-thesis",
    image:
      "https://images.unsplash.com/photo-1454165804606-c3d57bc86b40?auto=format&fit=crop&w=1200&q=80",
  },
  {
    href: "/daily-summary",
    image:
      "https://images.unsplash.com/photo-1642790551116-18e150f248e8?auto=format&fit=crop&w=1200&q=80",
  },
  {
    href: "/market-radar",
    image:
      "https://images.unsplash.com/photo-1642790106117-e829e14a795f?auto=format&fit=crop&w=1200&q=80",
  },
  {
    href: "/prediction-markets",
    image:
      "https://images.unsplash.com/photo-1551434678-e076c223a692?auto=format&fit=crop&w=1200&q=80",
  },
];

const localizedItems = {
  en: [
    {
      title: "Research",
      description:
        "Independent macro research and structured analysis for long-term capital allocation.",
      alt: "Hands pointing at financial report with charts",
    },
    {
      title: "Strategy",
      description:
        "Systematic strategies across equities, commodities, options, and global markets.",
      alt: "Hand with stylus on candlestick charts display",
    },
    {
      title: "Ongoing Thesis",
      description:
        "Current research projects and investment theses under development with community-driven frameworks.",
      alt: "Analyst reviewing ongoing thesis notes and market data",
    },
    {
      title: "Daily Summary",
      description:
        "A compact cross-market brief covering A-shares, US equities, FX, and commodities.",
      alt: "Daily market dashboard on a laptop screen",
    },
    {
      title: "Market Radar",
      description:
        "A fast US market calendar dashboard for earnings, updates, holidays, and event odds.",
      alt: "Market intelligence dashboard with charts and data panels",
    },
    {
      title: "Prediction Markets",
      description:
        "Data-driven positioning in event-driven markets with disciplined risk control.",
      alt: "Person holding tablet with financial dashboard",
    },
  ],
  zh: [
    {
      title: "研究",
      description: "面向长期资产配置的独立宏观研究与结构化分析。",
      alt: "分析师查看包含图表的金融报告",
    },
    {
      title: "策略",
      description: "覆盖股票、大宗商品、期权与全球市场的系统化策略。",
      alt: "交易图表屏幕上的技术分析走势",
    },
    {
      title: "进行中的研究",
      description: "正在推进的研究项目、投资主题与协作式研究框架。",
      alt: "分析师查看研究笔记和市场数据",
    },
    {
      title: "每日市场日报",
      description: "集中查看 A 股、美股、外汇与商品的每日市场摘要。",
      alt: "电脑屏幕上的每日市场看板",
    },
    {
      title: "市场雷达",
      description: "快速查看美股财报、重要更新、假期安排与事件赔率。",
      alt: "包含图表和数据面板的市场情报仪表盘",
    },
    {
      title: "预测市场",
      description: "以数据驱动事件市场判断，并结合纪律化风险控制。",
      alt: "展示金融仪表盘的平板电脑",
    },
  ],
};

const actionText = {
  en: "Explore",
  zh: "查看",
};

export default function FocusCards() {
  const { language } = useLanguage();
  const items = sharedItems.map((item, index) => ({
    ...item,
    ...localizedItems[language][index],
  }));
  const action = actionText[language];

  return (
    <div className="w-full grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 lg:gap-7">
      {items.map((item) => (
        <Link
          key={item.href}
          href={item.href}
          aria-label={`${item.title} - ${action}`}
          className="group relative flex flex-col overflow-hidden rounded-2xl bg-[#f7fbff] border border-slate-200 shadow-[0_10px_30px_rgba(15,23,42,0.06)] transition-all duration-300 ease-out focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-primary hover:-translate-y-1 hover:shadow-[0_18px_40px_rgba(15,23,42,0.12)]"
        >
          <div className="relative aspect-[16/9] w-full overflow-hidden">
            <Image
              src={item.image}
              alt={item.alt}
              fill
              sizes="(min-width: 1024px) 25vw, (min-width: 640px) 50vw, 100vw"
              className="object-cover transition-transform duration-300 ease-out group-hover:scale-105"
              priority
            />
          </div>

          <div className="flex min-h-[200px] flex-1 flex-col gap-3 px-7 py-6">
            <h3 className="text-2xl font-semibold text-slate-900">{item.title}</h3>
            <p className="line-clamp-2 text-base text-slate-600 leading-relaxed">
              {item.description}
            </p>
            <span className="mt-auto text-sm font-medium text-primary inline-flex items-center gap-1">
              {action} <span aria-hidden="true">→</span>
            </span>
          </div>
        </Link>
      ))}
    </div>
  );
}
