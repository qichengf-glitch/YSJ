"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import Section from "@/components/Section";
import { MarketQuoteTable } from "@/components/MarketQuoteTable";
import { OurPicksPanel } from "@/components/OurPicksPanel";

export default function MarketDataPage() {
  const [loadedAt, setLoadedAt] = useState<Date | null>(null);

  useEffect(() => {
    setLoadedAt(new Date());
  }, []);

  return (
    <main className="min-h-screen">
      <Section className="pt-6">
        <div className="mx-auto max-w-6xl space-y-6">
          <header className="space-y-2">
            <nav
              className="text-xs text-gray-500"
              aria-label="Breadcrumb"
            >
              <ol className="flex items-center gap-1">
                <li>
                  <Link href="/research" className="hover:text-primary">
                    Research
                  </Link>
                </li>
                <li>/</li>
                <li className="font-medium text-gray-700">
                  Market Data & Our Picks
                </li>
              </ol>
            </nav>
            <h1 className="text-3xl sm:text-4xl font-semibold text-gray-900">
              Market Data & Our Picks
            </h1>
            <p className="text-sm sm:text-base text-gray-600 max-w-2xl">
              Curated market data, analysis, and selected opportunities we&apos;re
              monitoring. World indices and key signals, alongside a rotating set
              of YSJ Lab watchlist ideas.
            </p>
            {loadedAt && (
              <p className="text-xs text-gray-400">
                Last updated{" "}
                {loadedAt.toLocaleTimeString([], {
                  hour: "2-digit",
                  minute: "2-digit",
                })}
              </p>
            )}
          </header>

          <div className="grid gap-6 lg:grid-cols-2">
            <div className="rounded-xl border border-gray-200 bg-white/90 shadow-sm">
              <div className="flex items-center justify-between border-b border-gray-200 px-4 py-3">
                <h2 className="text-sm font-semibold text-gray-900">
                  Market Data
                </h2>
                <p className="text-[11px] text-gray-500">
                  Quotes delayed / near real-time
                </p>
              </div>
              <div className="p-4">
                <MarketQuoteTable />
              </div>
            </div>

            <div className="rounded-xl border border-gray-200 bg-white/90 shadow-sm">
              <div className="flex items-center justify-between border-b border-gray-200 px-4 py-3">
                <h2 className="text-sm font-semibold text-gray-900">
                  Our Picks
                </h2>
                <p className="text-[11px] text-gray-500">
                  Illustrative ideas – not investment advice
                </p>
              </div>
              <div className="p-4">
                <OurPicksPanel />
              </div>
            </div>
          </div>
        </div>
      </Section>
    </main>
  );
}
