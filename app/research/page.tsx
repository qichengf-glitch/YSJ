"use client";

import Image from "next/image";
import Link from "next/link";
import { ArrowRight, BookOpen, LineChart, MessageSquareText, ShieldCheck } from "lucide-react";
import { useLanguage } from "@/contexts/LanguageContext";

const content = {
  en: {
    eyebrow: "Research",
    title: "Research Hub",
    intro:
      "A structured home for published work, developing theses, and market intelligence. Follow the evidence from first principles to active observation.",
    standards: [
      ["Independent", "Clear assumptions and conclusions without product-driven incentives."],
      ["Evidence-led", "Data, methodology, and limitations remain visible throughout the work."],
      ["Open to revision", "Theses evolve as new evidence changes the balance of probabilities."],
    ],
    explore: "Explore section",
    blocks: [
      {
        href: "/research/theoretical-research",
        kicker: "Published work",
        title: "Theoretical Research",
        intro:
          "Papers and conceptual frameworks on finance, economics, portfolio construction, and market behavior.",
        image:
          "https://images.unsplash.com/photo-1454165804606-c3d57bc86b40?auto=format&fit=crop&w=1400&q=80",
        alt: "Analyst notes and documents for financial research",
      },
      {
        href: "/research/ongoing-thesis",
        kicker: "Work in progress",
        title: "Ongoing Thesis",
        intro:
          "Developing investment theses, research questions, and community discussion around markets and trade structures.",
        image:
          "https://images.unsplash.com/photo-1434030216411-0b793f4b4173?auto=format&fit=crop&w=1400&q=80",
        alt: "Researcher reviewing thesis drafts and charts",
      },
      {
        href: "/research/market-data",
        kicker: "Market intelligence",
        title: "Market Data & Our Picks",
        intro:
          "Global indices, selected signals, and a focused watchlist of opportunities under active observation.",
        image:
          "https://images.unsplash.com/photo-1518186285589-2f7649de83e0?auto=format&fit=crop&w=1400&q=80",
        alt: "Market dashboard displaying multi-asset data",
      },
    ],
  },
  zh: {
    eyebrow: "研究",
    title: "研究中心",
    intro:
      "汇集已发布成果、进行中的投资主题与市场情报。从第一性原理出发，沿着证据走向持续观察。",
    standards: [
      ["保持独立", "清晰呈现假设与结论，不受产品销售目标影响。"],
      ["证据驱动", "在研究过程中明确展示数据、方法与局限性。"],
      ["持续修正", "当新证据改变概率判断时，及时调整投资主题。"],
    ],
    explore: "进入板块",
    blocks: [
      {
        href: "/research/theoretical-research",
        kicker: "已发布成果",
        title: "理论研究",
        intro: "围绕金融、经济学、组合构建与市场行为的论文和概念框架。",
        image:
          "https://images.unsplash.com/photo-1454165804606-c3d57bc86b40?auto=format&fit=crop&w=1400&q=80",
        alt: "金融研究与文档资料",
      },
      {
        href: "/research/ongoing-thesis",
        kicker: "研究进行中",
        title: "进行中的研究",
        intro: "持续发展的投资主题、研究问题，以及围绕市场和交易结构的社区讨论。",
        image:
          "https://images.unsplash.com/photo-1434030216411-0b793f4b4173?auto=format&fit=crop&w=1400&q=80",
        alt: "研究人员查看课题草稿和图表",
      },
      {
        href: "/research/market-data",
        kicker: "市场情报",
        title: "市场数据与我们的选择",
        intro: "全球指数、精选信号，以及正在持续观察的重点机会清单。",
        image:
          "https://images.unsplash.com/photo-1518186285589-2f7649de83e0?auto=format&fit=crop&w=1400&q=80",
        alt: "多资产市场数据看板",
      },
    ],
  },
};

const standardIcons = [ShieldCheck, LineChart, MessageSquareText];
const blockIcons = [BookOpen, MessageSquareText, LineChart];

export default function ResearchPage() {
  const { language } = useLanguage();
  const t = content[language];

  return (
    <main className="min-h-screen bg-white text-[#18233A]">
      <section className="border-b border-[#E7ECF5] bg-[#F8FAFC] px-6 py-12 sm:px-8 lg:px-12">
        <div className="mx-auto grid max-w-7xl gap-10 lg:grid-cols-[0.9fr_1.1fr] lg:items-end">
          <div>
            <p className="text-sm font-bold uppercase text-[#4F63F6]">{t.eyebrow}</p>
            <h1 className="mt-3 text-4xl font-black leading-tight text-[#18233A] sm:text-5xl">
              {t.title}
            </h1>
            <p className="mt-5 max-w-xl text-lg leading-8 text-[#5B6780]">{t.intro}</p>
          </div>

          <div className="grid gap-5 border-t border-[#DCE3EF] pt-7 sm:grid-cols-3 lg:border-l lg:border-t-0 lg:pl-8 lg:pt-0">
            {t.standards.map(([title, text], index) => {
              const Icon = standardIcons[index];
              return (
                <div key={title}>
                  <Icon className="h-5 w-5 text-[#4F63F6]" />
                  <h2 className="mt-3 text-sm font-bold text-[#18233A]">{title}</h2>
                  <p className="mt-1 text-sm leading-6 text-[#5B6780]">{text}</p>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      <section className="px-6 py-14 sm:px-8 lg:px-12 lg:py-16">
        <div className="mx-auto grid max-w-7xl gap-6 md:grid-cols-3">
          {t.blocks.map((block, index) => {
            const Icon = blockIcons[index];
            return (
              <Link
                key={block.href}
                href={block.href}
                className="group flex min-h-[470px] flex-col overflow-hidden rounded-lg border border-[#E7ECF5] bg-white shadow-[0_12px_30px_rgba(39,59,154,0.06)] transition hover:-translate-y-1 hover:border-[#A8B2FF] hover:shadow-[0_20px_40px_rgba(39,59,154,0.11)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[#4F63F6]"
              >
                <div className="relative aspect-[16/10] overflow-hidden bg-[#F3F5F9]">
                  <Image
                    src={block.image}
                    alt={block.alt}
                    fill
                    sizes="(min-width: 768px) 33vw, 100vw"
                    className="object-cover transition duration-300 group-hover:scale-[1.025]"
                  />
                  <div className="absolute inset-x-0 bottom-0 h-16 bg-[linear-gradient(180deg,transparent,rgba(24,35,58,0.42))]" />
                </div>

                <div className="flex flex-1 flex-col p-6">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold uppercase text-[#4F63F6]">
                      {block.kicker}
                    </span>
                    <Icon className="h-5 w-5 text-[#778195]" />
                  </div>
                  <h2 className="mt-5 text-2xl font-black leading-tight text-[#18233A]">
                    {block.title}
                  </h2>
                  <p className="mt-3 text-sm leading-7 text-[#5B6780]">{block.intro}</p>
                  <span className="mt-auto inline-flex items-center border-t border-[#E7ECF5] pt-5 text-sm font-bold text-[#273B9A]">
                    {t.explore}
                    <ArrowRight className="ml-2 h-4 w-4 transition group-hover:translate-x-1" />
                  </span>
                </div>
              </Link>
            );
          })}
        </div>
      </section>
    </main>
  );
}
