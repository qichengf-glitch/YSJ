"use client";

import Image from "next/image";
import Link from "next/link";
import { useLanguage } from "@/contexts/LanguageContext";

const sharedItems = [
  {
    href: "/research",
    image: "/assets/research-icon.png",
  },
  {
    href: "/strategy",
    image: "/assets/strategy-icon.png",
  },
  {
    href: "/research/ongoing-thesis",
    image: "/assets/ongoing-thesis-icon.png",
  },
  {
    href: "/prediction-markets",
    image: "/assets/prediction-markets-icon.png",
  },
  {
    href: "/access",
    image: "/assets/private-radar-icon.png",
  },
];

const localizedItems = {
  en: [
    {
      title: "Research",
      description:
        "Independent macro research and structured analysis for long-term capital allocation.",
      alt: "Research report illustration with charts and magnifier",
    },
    {
      title: "Strategy",
      description:
        "Systematic strategies across equities, commodities, options, and global markets.",
      alt: "Strategy chess piece and planning board illustration",
    },
    {
      title: "Ongoing Thesis",
      description:
        "Current research projects and investment theses under development with community-driven feedback.",
      alt: "Notebook and idea discussion illustration",
    },
    {
      title: "Prediction Markets",
      description:
        "Data-driven positioning in event-driven markets with disciplined risk control.",
      alt: "Probability chart and market outcome illustration",
    },
    {
      title: "Private Access",
      description:
        "Authorized entry for internal dashboards, live monitors, daily briefs, and market radar tools.",
      alt: "Private dashboard and radar illustration",
    },
  ],
  zh: [
    {
      title: "研究",
      description: "面向长期资产配置的独立宏观研究与结构化分析。",
      alt: "包含图表和放大镜的研究报告插图",
    },
    {
      title: "策略",
      description: "覆盖股票、大宗商品、期权与全球市场的系统化策略。",
      alt: "策略棋子和规划图插图",
    },
    {
      title: "进行中的研究",
      description: "正在推进的研究项目、投资主题与协作式反馈。",
      alt: "笔记本和想法讨论插图",
    },
    {
      title: "预测市场",
      description: "以数据驱动事件市场判断，并结合纪律化风险控制。",
      alt: "概率图表和市场结果插图",
    },
    {
      title: "Private Access",
      description: "授权访问内部看板、实时监控、每日简报与市场雷达工具。",
      alt: "私密看板和雷达插图",
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
    <div className="grid w-full grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
      {items.map((item) => (
        <Link
          key={item.href}
          href={item.href}
          aria-label={`${item.title} - ${action}`}
          className="group flex min-h-[410px] flex-col overflow-hidden rounded-2xl border border-[#E7ECF5] bg-white shadow-[0_14px_34px_rgba(39,59,154,0.07)] transition-all duration-300 ease-out hover:-translate-y-1 hover:border-[#A8B2FF] hover:shadow-[0_22px_50px_rgba(39,59,154,0.14)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[#4F63F6]"
        >
          <div className="flex h-56 items-center justify-center bg-gradient-to-b from-white to-[#F8FAFC] p-7">
            <Image
              src={item.image}
              alt={item.alt}
              width={360}
              height={360}
              className="h-full w-full object-contain transition-transform duration-300 ease-out group-hover:scale-[1.03]"
            />
          </div>

          <div className="flex flex-1 flex-col gap-3 px-7 pb-7 pt-2">
            <h3 className="text-2xl font-bold tracking-tight text-[#18233A]">{item.title}</h3>
            <p className="text-base leading-relaxed text-[#5B6780]">
              {item.description}
            </p>
            <span className="mt-auto inline-flex items-center gap-1 text-sm font-semibold text-[#4F63F6]">
              {action} <span aria-hidden="true">→</span>
            </span>
          </div>
        </Link>
      ))}
    </div>
  );
}
