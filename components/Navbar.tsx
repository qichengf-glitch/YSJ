"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { LockKeyhole } from "lucide-react";
import BrandMark from "./BrandMark";
import LanguageToggle from "./LanguageToggle";
import { useLanguage } from "@/contexts/LanguageContext";

const navItems = {
  en: [
    { label: "Home", href: "/" },
    { label: "Research", href: "/research" },
    { label: "Strategy", href: "/strategy" },
    { label: "Prediction Markets", href: "/prediction-markets" },
    { label: "Contact", href: "/contact" },
  ],
  zh: [
    { label: "首页", href: "/" },
    { label: "研究", href: "/research" },
    { label: "策略", href: "/strategy" },
    { label: "预测市场", href: "/prediction-markets" },
    { label: "联系我们", href: "/contact" },
  ],
};

const accessText = {
  en: "Private Access",
  zh: "Private Access",
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

            <Link
              href="/access"
              className={`inline-flex h-10 items-center justify-center border px-3 text-xs font-bold transition sm:px-4 sm:text-sm ${
                isActive("/access")
                  ? "border-[#111827] bg-[#111827] text-white"
                  : "border-[#D7B46A] bg-[#F8F1E3] text-[#5F4820] hover:bg-[#D7B46A] hover:text-[#111827]"
              }`}
            >
              <LockKeyhole className="mr-1.5 h-3.5 w-3.5" />
              <span className="hidden sm:inline">{accessText[language]}</span>
              <span className="sm:hidden">Access</span>
            </Link>

            <LanguageToggle />
          </div>
        </div>
      </div>
    </nav>
  );
}
