import type { NextRequest } from "next/server";

export const dynamic = "force-dynamic";

type QuoteItem = {
  symbol: string;
  longName?: string;
  regularMarketPrice?: number;
  regularMarketChange?: number;
  regularMarketChangePercent?: number;
};

type GroupConfig = {
  region: string;
  symbols: string[];
};

const GROUPS: GroupConfig[] = [
  {
    region: "Americas",
    symbols: ["^GSPC", "^IXIC", "^DJI", "^RUT", "^VIX", "DX-Y.NYB"],
  },
  {
    region: "Europe",
    symbols: ["^GDAXI", "^FTSE", "^FCHI", "^STOXX50E"],
  },
  {
    region: "Asia",
    symbols: ["^N225", "^HSI", "^KS11", "000001.SS", "^AXJO"],
  },
];

type NormalizedResponse = {
  updatedAt: number;
  groups: {
    region: string;
    items: {
      symbol: string;
      name: string;
      price: number;
      change: number;
      changePct: number;
    }[];
  }[];
};

let cachedData: NormalizedResponse | null = null;
let cachedAt = 0;
const TTL_MS = 60_000;

export async function GET(_req: NextRequest) {
  const now = Date.now();
  if (cachedData && now - cachedAt < TTL_MS) {
    return Response.json(cachedData, {
      headers: {
        "Cache-Control": "public, max-age=30",
      },
    });
  }

  const allSymbols = GROUPS.flatMap((g) => g.symbols).join(",");
  const url = `https://query1.finance.yahoo.com/v7/finance/quote?symbols=${encodeURIComponent(
    allSymbols
  )}`;

  try {
    const res = await fetch(url, {
      next: { revalidate: 60 },
      headers: {
        "User-Agent":
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
      },
    });
    if (!res.ok) {
      throw new Error(`Yahoo quote error: ${res.status}`);
    }
    const json = await res.json();
    const result: QuoteItem[] = json?.quoteResponse?.result ?? [];

    const bySymbol: Record<string, QuoteItem> = {};
    for (const q of result) {
      if (q.symbol) bySymbol[q.symbol] = q;
    }

    const normalized: NormalizedResponse = {
      updatedAt: now,
      groups: GROUPS.map((group) => ({
        region: group.region,
        items: group.symbols
          .map((symbol) => {
            const item = bySymbol[symbol];
            if (!item || item.regularMarketPrice == null) return null;
            return {
              symbol,
              name: item.longName ?? symbol,
              price: item.regularMarketPrice ?? 0,
              change: item.regularMarketChange ?? 0,
              changePct: item.regularMarketChangePercent ?? 0,
            };
          })
          .filter(Boolean) as NormalizedResponse["groups"][number]["items"],
      })),
    };

    cachedData = normalized;
    cachedAt = now;

    return Response.json(normalized, {
      headers: {
        "Cache-Control": "public, max-age=30",
      },
    });
  } catch (error) {
    console.error("Failed to fetch market quotes", error);

    // Fallback: static mock data for local development / blocked network
    const mock: NormalizedResponse = {
      updatedAt: now,
      groups: GROUPS.map((group) => ({
        region: group.region,
        items: group.symbols.map((symbol, idx) => ({
          symbol,
          name: symbol,
          price: 100 + idx * 5,
          change: idx % 2 === 0 ? 0.5 : -0.4,
          changePct: idx % 2 === 0 ? 0.4 : -0.3,
        })),
      })),
    };

    cachedData = mock;
    cachedAt = now;

    return Response.json(mock, {
      headers: {
        "Cache-Control": "public, max-age=30",
      },
    });
  }
}

