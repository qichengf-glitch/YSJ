"use client";

import { useEffect, useState } from "react";
import Sparkline from "./Sparkline";

type MarketItem = {
  symbol: string;
  name: string;
  price: number;
  change: number;
  changePct: number;
};

type MarketGroup = {
  region: string;
  items: MarketItem[];
};

type ApiResponse = {
  updatedAt: number;
  groups: MarketGroup[];
};

export function MarketQuoteTable() {
  const [data, setData] = useState<ApiResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [spark, setSpark] = useState<Record<string, number[]>>({});

  const fetchData = async () => {
    try {
      setError(null);
      setLoading(true);
      const res = await fetch("/api/markets/quotes");
      if (!res.ok) {
        throw new Error(`Status ${res.status}`);
      }
      const json = (await res.json()) as ApiResponse;
      setData(json);
    } catch (err) {
      console.error(err);
      setError("Unable to load market data right now.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const id = setInterval(fetchData, 30_000);
    return () => clearInterval(id);
  }, []);

  // Sparkline data – refresh every 5 minutes
  useEffect(() => {
    const ALL_SYMBOLS = [
      "^GSPC",
      "^IXIC",
      "^DJI",
      "^RUT",
      "^VIX",
      "DX-Y.NYB",
      "^GDAXI",
      "^FTSE",
      "^FCHI",
      "^STOXX50E",
      "^N225",
      "^HSI",
      "^KS11",
      "000001.SS",
      "^AXJO",
    ];

    const loadSpark = async () => {
      try {
        const qs = encodeURIComponent(ALL_SYMBOLS.join(","));
        const res = await fetch(`/api/markets/spark?symbols=${qs}`);
        if (!res.ok) return;
        const json = (await res.json()) as { series?: Record<string, number[]> };
        setSpark(json.series ?? {});
      } catch {
        // swallow – sparkline is purely decorative
      }
    };

    loadSpark();
    const id = setInterval(loadSpark, 5 * 60 * 1000);
    return () => clearInterval(id);
  }, []);

  const renderSkeleton = () => (
    <div className="space-y-4">
      {[1, 2, 3].map((group) => (
        <div key={group} className="space-y-2">
          <div className="h-3 w-24 rounded bg-gray-100" />
          <div className="space-y-1.5">
            {Array.from({ length: 4 }).map((_, idx) => (
              <div
                key={idx}
                className="flex items-center justify-between rounded bg-gray-50 px-3 py-2"
              >
                <div className="h-3 w-32 rounded bg-gray-100" />
                <div className="h-3 w-16 rounded bg-gray-100" />
                <div className="h-3 w-24 rounded bg-gray-100" />
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );

  if (loading && !data) {
    return renderSkeleton();
  }

  if (error) {
    return (
      <div className="space-y-3 text-sm text-gray-600">
        <p>{error}</p>
        <button
          type="button"
          onClick={fetchData}
          className="rounded-full border border-gray-300 bg-white px-3 py-1 text-xs font-medium text-gray-700 hover:border-primary hover:text-primary focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
        >
          Retry
        </button>
      </div>
    );
  }

  if (!data) {
    return null;
  }

  return (
    <div className="space-y-4">
      {data.groups.map((group) => (
        <div key={group.region} className="space-y-2">
          <h3 className="text-sm font-semibold uppercase tracking-wide text-gray-600">
            {group.region}
          </h3>
          <div className="overflow-hidden rounded-lg border border-gray-200">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-600">
                    Symbol / Name
                  </th>
                  <th className="px-4 py-3 text-right text-sm font-semibold text-gray-600">
                    Price
                  </th>
                  <th className="px-4 py-3 text-right text-sm font-semibold text-gray-600">
                    Change
                  </th>
                  <th className="px-4 py-3 text-right text-sm font-semibold text-gray-600">
                    Intraday
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 bg-white">
                {group.items.map((item) => {
                  const positive = item.change > 0;
                  const negative = item.change < 0;
                  const color = positive
                    ? "text-emerald-600"
                    : negative
                    ? "text-rose-600"
                    : "text-gray-700";
                  return (
                    <tr key={item.symbol} className="hover:bg-gray-50">
                      <td className="px-4 py-3 align-middle">
                        <div className="font-mono text-sm font-medium text-gray-900">
                          {item.symbol.replace(/^\^/, "")}
                        </div>
                        <div className="text-xs text-gray-500 truncate max-w-[220px] mt-0.5">
                          {item.name}
                        </div>
                      </td>
                      <td className="px-4 py-3 text-right align-middle text-sm font-medium text-gray-900">
                        {item.price.toFixed(2)}
                      </td>
                      <td className={`px-4 py-3 text-right align-middle text-sm ${color}`}>
                        {item.change >= 0 ? "+" : ""}
                        {item.change.toFixed(2)}{" "}
                        <span className="ml-1">
                          ({item.changePct >= 0 ? "+" : ""}
                          {item.changePct.toFixed(2)}%)
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right align-middle">
                        <Sparkline
                          values={spark[item.symbol]}
                          trend={item.changePct >= 0 ? "up" : "down"}
                        />
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      ))}
    </div>
  );
}

