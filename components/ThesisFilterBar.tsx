"use client";

import { Search } from "lucide-react";

const tabOptions = ["For You", "Latest", "Following"] as const;
type TabOption = (typeof tabOptions)[number];

const sortOptions = [
  "New",
  "Hot",
  "Top (24h)",
  "Top (7d)",
  "Top (30d)",
  "Controversial",
] as const;
type SortOption = (typeof sortOptions)[number];

interface ThesisFilterBarProps {
  selectedTab: TabOption;
  onTabChange: (tab: TabOption) => void;
  selectedSort: SortOption;
  onSortChange: (sort: SortOption) => void;
  selectedTag: string | null;
  onTagChange: (tag: string | null) => void;
  tickerQuery: string;
  onTickerQueryChange: (value: string) => void;
}

const tagOptions = [
  "Macro",
  "Rates",
  "Tech",
  "Options",
  "Crypto",
  "US Equities",
] as const;

export function ThesisFilterBar({
  selectedTab,
  onTabChange,
  selectedSort,
  onSortChange,
  selectedTag,
  onTagChange,
  tickerQuery,
  onTickerQueryChange,
}: ThesisFilterBarProps) {
  return (
    <div className="sticky top-16 z-30 backdrop-blur-sm">
      <div className="mx-auto flex max-w-6xl flex-col gap-1 px-6 py-2 sm:px-8 lg:px-12">
        {/* Tabs - text links style */}
        <div className="flex flex-wrap items-center gap-6 text-sm">
          {tabOptions.map((tab) => (
            <button
              key={tab}
              type="button"
              onClick={() => onTabChange(tab)}
              className={`pb-1 text-sm font-medium transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 ${
                selectedTab === tab
                  ? "text-primary border-b-2 border-primary"
                  : "text-gray-600 hover:text-gray-900 border-b-2 border-transparent"
              }`}
            >
              {tab}
            </button>
          ))}
        </div>

        {/* Filters - minimal, inline */}
        <div className="flex flex-wrap items-center gap-4">
          <div className="flex flex-wrap items-center gap-4">
            <span className="text-sm text-gray-500">Sort:</span>
            {sortOptions.slice(0, 4).map((opt) => (
              <button
                key={opt}
                type="button"
                onClick={() => onSortChange(opt)}
                className={`text-sm font-medium transition-colors ${
                  selectedSort === opt
                    ? "text-primary"
                    : "text-gray-500 hover:text-gray-700"
                }`}
              >
                {opt}
              </button>
            ))}
          </div>
          <div className="flex flex-wrap gap-4">
            {tagOptions.map((tag) => (
              <button
                key={tag}
                type="button"
                onClick={() =>
                  onTagChange(selectedTag === tag ? null : tag)
                }
                className={`text-sm font-medium transition-colors ${
                  selectedTag === tag
                    ? "text-primary"
                    : "text-gray-500 hover:text-gray-700"
                }`}
              >
                {tag}
              </button>
            ))}
          </div>
          <div className="flex items-center gap-2 ml-auto">
            <div className="flex items-center gap-2 text-gray-500">
              <Search className="h-3.5 w-3.5" />
              <input
                type="text"
                placeholder="Filter by ticker"
                className="w-28 bg-transparent text-sm text-gray-700 placeholder:text-gray-400 focus:outline-none sm:w-40 border-b border-gray-300/60 focus:border-primary"
                value={tickerQuery}
                onChange={(e) => onTickerQueryChange(e.target.value)}
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

