"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useLanguage } from "@/contexts/LanguageContext";

const tabs = {
  en: [
    { href: "/research/theoretical-research", label: "Theoretical Research" },
    { href: "/research/ongoing-thesis", label: "Ongoing Thesis" },
    { href: "/research/market-data", label: "Market Data & Our Picks" },
  ],
  zh: [
    { href: "/research/theoretical-research", label: "理论研究" },
    { href: "/research/ongoing-thesis", label: "进行中的研究" },
    { href: "/research/market-data", label: "市场数据与我们的选择" },
  ],
};

export default function ResearchTabNav() {
  const pathname = usePathname();
  const { language } = useLanguage();
  const items = tabs[language];

  return (
    <div className="border-b border-gray-200 bg-white/90">
      <div className="mx-auto max-w-6xl px-6 sm:px-8 lg:px-12">
        <nav
          className="-mb-px flex gap-1"
          aria-label="Research sections"
        >
          {items.map((tab) => {
            const isTheoretical =
              pathname === "/research/theoretical-research" ||
              (pathname.startsWith("/research/") &&
                !pathname.startsWith("/research/ongoing-thesis") &&
                !pathname.startsWith("/research/market-data") &&
                pathname !== "/research");
            const isActive =
              tab.href === "/research/theoretical-research"
                ? isTheoretical
                : pathname === tab.href || pathname.startsWith(tab.href + "/");
            return (
              <Link
                key={tab.href}
                href={tab.href}
                className={`whitespace-nowrap border-b-2 px-5 py-4 text-sm font-medium transition-colors ${
                  isActive
                    ? "border-primary text-primary"
                    : "border-transparent text-gray-600 hover:border-gray-300 hover:text-gray-900"
                }`}
              >
                {tab.label}
              </Link>
            );
          })}
        </nav>
      </div>
    </div>
  );
}
