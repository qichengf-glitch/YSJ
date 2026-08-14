"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import BrandMark from "./BrandMark";
import LanguageToggle from "./LanguageToggle";
import { useLanguage } from "@/contexts/LanguageContext";

const navItems = {
  en: [
    { label: "Home", href: "/" },
    { label: "Research", href: "/research" },
    { label: "Ongoing Thesis", href: "/research/ongoing-thesis" },
    { label: "Quant Monitor", href: "/access" },
    { label: "Contact", href: "/contact" },
  ],
  zh: [
    { label: "首页", href: "/" },
    { label: "研究", href: "/research" },
    { label: "进行中的研究", href: "/research/ongoing-thesis" },
    { label: "量化指标监控", href: "/access" },
    { label: "联系我们", href: "/contact" },
  ],
};

export default function Navbar() {
  const pathname = usePathname();
  const { language } = useLanguage();

  const isActive = (path: string) => {
    if (path === "/") {
      return pathname === "/";
    }
    return pathname.startsWith(path);
  };

  return (
    <nav className="sticky top-0 z-50 border-b border-[#E6DDCD] bg-[#FBFAF7]/94 backdrop-blur">
      <div className="mx-auto max-w-7xl px-4 sm:px-8 lg:px-12">
        <div className="flex min-h-16 items-center justify-between gap-4 py-3">
          <BrandMark />

          <div className="flex min-w-0 flex-1 items-center justify-end gap-3 sm:gap-6">
            <div className="hidden items-center gap-6 md:flex">
              {navItems[language].map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`whitespace-nowrap text-sm font-semibold transition-colors ${
                    isActive(item.href)
                      ? "text-[#8A6A2F]"
                      : "text-[#5B6472] hover:text-[#111827]"
                  }`}
                >
                  {item.label}
                </Link>
              ))}
            </div>

            <LanguageToggle />
          </div>
        </div>
      </div>
    </nav>
  );
}
