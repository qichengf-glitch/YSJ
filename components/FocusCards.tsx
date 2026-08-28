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
    href: "/research/ongoing-thesis",
    image: "/assets/ongoing-thesis-icon.png",
  },
  {
    href: "/access",
    image: "/assets/prediction-markets-icon.png",
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
      title: "Ongoing Thesis",
      description:
        "Current research projects and investment theses under development with community-driven feedback.",
      alt: "Notebook and idea discussion illustration",
    },
    {
      title: "Quant Monitor",
      description:
        "Access-controlled monitoring for VIX, prediction markets, and stock scoring.",
      alt: "Probability chart and market monitoring illustration",
    },
  ],
  zh: [
    {
      title: "研究",
      description: "面向长期资产配置的独立宏观研究与结构化分析。",
      alt: "包含图表和放大镜的研究报告插图",
    },
    {
      title: "进行中的研究",
      description: "正在推进的研究项目、投资主题与协作式反馈。",
      alt: "笔记本和想法讨论插图",
    },
    {
      title: "量化指标监控",
      description: "受控访问 VIX、预测市场与股票评分等内部监控模块。",
      alt: "概率图表和市场结果插图",
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
          className="group flex min-h-[410px] flex-col overflow-hidden border border-[#E6DDCD] bg-[#FFFDF8] shadow-[0_14px_34px_rgba(78,56,21,0.07)] transition-all duration-300 ease-out hover:-translate-y-1 hover:border-[#D7B46A] hover:shadow-[0_22px_50px_rgba(78,56,21,0.13)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[#D7B46A]"
        >
          <div className="flex h-56 items-center justify-center bg-gradient-to-b from-[#FFFDF8] to-[#F8F1E3] p-7">
            <Image
              src={item.image}
              alt={item.alt}
              width={360}
              height={360}
              className="h-full w-full object-contain transition-transform duration-300 ease-out group-hover:scale-[1.03]"
            />
          </div>

          <div className="flex flex-1 flex-col gap-3 px-7 pb-7 pt-2">
            <h3 className="text-2xl font-bold tracking-tight text-[#111827]">{item.title}</h3>
            <p className="text-base leading-relaxed text-[#5B6472]">
              {item.description}
            </p>
            <span className="mt-auto inline-flex items-center gap-1 text-sm font-semibold text-[#8A6A2F]">
              {action} <span aria-hidden="true">→</span>
            </span>
          </div>
        </Link>
      ))}
    </div>
  );
}
