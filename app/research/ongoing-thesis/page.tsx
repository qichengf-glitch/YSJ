"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { ThesisPostCard } from "@/components/ThesisPostCard";
import { ThesisFilterBar } from "@/components/ThesisFilterBar";
import { ThesisComposer } from "@/components/ThesisComposer";
import type { ThesisPost } from "@/types/thesis";

const mockPosts: ThesisPost[] = [
  {
    id: "us-equity-gamma-rotation",
    title: "US Equity Gamma Rotation Around CPI and FOMC Windows",
    excerpt:
      "Why single-stock and index options tend to reprice risk non-linearly around key macro dates, and how systematic traders can structure exposure.",
    body: "",
    author: {
      id: "1",
      username: "gamma_structurer",
      badge: "Contributor",
    },
    createdAt: "2 hours ago",
    readingTime: "12 min read",
    tags: ["Macro", "Options", "US Equities"],
    tickers: ["SPY", "QQQ"],
    sentiment: "Bullish",
    score: 128,
    commentsCount: 24,
  },
  {
    id: "rates-curve-carry",
    title: "The Shape of the Rates Curve and Forward Carry in 2026",
    excerpt:
      "A framework for thinking about curve trades when central banks are late-cycle and term premia are slowly normalizing.",
    body: "",
    author: {
      id: "2",
      username: "term_structure",
      badge: "Analyst",
    },
    createdAt: "6 hours ago",
    readingTime: "10 min read",
    tags: ["Macro", "Rates"],
    tickers: ["ZN", "ZB"],
    sentiment: "Neutral",
    score: 96,
    commentsCount: 18,
  },
  {
    id: "crypto-liquidity-fragmentation",
    title: "Liquidity Fragmentation in Crypto and the Cost of On-Chain Leverage",
    excerpt:
      "Why the effective cost of leverage in crypto markets is often under-estimated when funding, basis, and slippage are considered jointly.",
    body: "",
    author: {
      id: "3",
      username: "onchain_delta",
      badge: "Verified",
    },
    createdAt: "1 day ago",
    readingTime: "8 min read",
    tags: ["Crypto", "Leverage"],
    tickers: ["BTC", "ETH"],
    sentiment: "Bearish",
    score: 183,
    commentsCount: 41,
  },
];

type TabOption = "For You" | "Latest" | "Following";
type SortOption =
  | "New"
  | "Hot"
  | "Top (24h)"
  | "Top (7d)"
  | "Top (30d)"
  | "Controversial";

export default function OngoingThesisFeedPage() {
  const [selectedTab, setSelectedTab] = useState<TabOption>("For You");
  const [selectedSort, setSelectedSort] = useState<SortOption>("Hot");
  const [selectedTag, setSelectedTag] = useState<string | null>(null);
  const [tickerQuery, setTickerQuery] = useState("");
  const [visibleCount, setVisibleCount] = useState(3);

  const filteredPosts = useMemo(() => {
    return mockPosts.filter((post) => {
      const matchesTag = selectedTag
        ? post.tags.includes(selectedTag)
        : true;
      const matchesTicker = tickerQuery
        ? post.tickers
            .join(" ")
            .toLowerCase()
            .includes(tickerQuery.toLowerCase())
        : true;
      return matchesTag && matchesTicker;
    });
  }, [selectedTag, tickerQuery]);

  const visiblePosts = filteredPosts.slice(0, visibleCount);

  return (
    <main className="min-h-screen pb-12">
      <div className="pt-6 pb-2">
        <div className="max-w-6xl mx-auto px-6 sm:px-8 lg:px-12">
          {/* Breadcrumb */}
          <nav
            className="mb-1.5 text-sm text-gray-500"
            aria-label="Breadcrumb"
          >
            <ol className="flex items-center gap-1">
              <li>
                <Link href="/research" className="hover:text-primary">
                  Research Hub
                </Link>
              </li>
              <li>/</li>
              <li className="font-medium text-gray-700">Ongoing Thesis</li>
            </ol>
          </nav>

          {/* Header */}
          <header>
            <h1 className="text-2xl sm:text-3xl font-semibold text-gray-900 mb-0.5">
              Ongoing Thesis
            </h1>
            <p className="text-sm text-gray-600 max-w-2xl">
              Community-driven theses, frameworks, and ongoing debates around
              markets, macro, and specific trade structures.
            </p>
          </header>
        </div>
      </div>

      <ThesisFilterBar
        selectedTab={selectedTab}
        onTabChange={setSelectedTab}
        selectedSort={selectedSort}
        onSortChange={setSelectedSort}
        selectedTag={selectedTag}
        onTagChange={setSelectedTag}
        tickerQuery={tickerQuery}
        onTickerQueryChange={setTickerQuery}
      />

      <div className="pt-3 pb-8">
        <div className="max-w-6xl mx-auto px-6 sm:px-8 lg:px-12">
          {/* Composer */}
          <div className="mb-3">
            <ThesisComposer />
          </div>

          {/* Feed list */}
          <div>
            {visiblePosts.map((post) => (
              <ThesisPostCard key={post.id} post={post} />
            ))}

            {visiblePosts.length === 0 && (
              <div className="py-12 text-center text-sm text-gray-500">
                No theses match the current filters yet.
              </div>
            )}

            {visibleCount < filteredPosts.length && (
              <div className="pt-4 flex justify-center">
                <button
                  type="button"
                  onClick={() =>
                    setVisibleCount((count) => count + 3)
                  }
                  className="text-sm font-medium text-primary hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
                >
                  Load more
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </main>
  );
}

