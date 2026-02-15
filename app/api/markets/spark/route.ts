import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export type SparkResp = {
  updatedAt: number;
  series: Record<string, number[]>;
};

let cache: SparkResp | null = null;
let cacheAt = 0;
const TTL_MS = 5 * 60 * 1000; // 5 minutes
const MAX_POINTS = 40;
const CONCURRENCY = 4;

function chunk<T>(arr: T[], size: number) {
  const out: T[][] = [];
  for (let i = 0; i < arr.length; i += size) out.push(arr.slice(i, i + size));
  return out;
}

async function fetchSeries(symbol: string): Promise<number[] | null> {
  const url = `https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(
    symbol
  )}?range=1d&interval=5m&includePrePost=false`;

  const res = await fetch(url, {
    cache: "no-store",
    headers: {
      "User-Agent":
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    },
  });
  if (!res.ok) return null;

  const json = await res.json();
  const result = json?.chart?.result?.[0];
  const closes: (number | null)[] | undefined =
    result?.indicators?.quote?.[0]?.close;

  if (!closes || closes.length === 0) return null;

  const values = closes.filter((v) => typeof v === "number") as number[];
  if (values.length < 5) return null;

  return values.slice(-MAX_POINTS);
}

export async function GET(req: Request) {
  const { searchParams } = new URL(req.url);
  const raw = searchParams.get("symbols") || "";
  const symbols = raw
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);

  if (symbols.length === 0) {
    return NextResponse.json({ error: "Missing symbols" }, { status: 400 });
  }

  const now = Date.now();
  if (cache && now - cacheAt < TTL_MS) {
    return NextResponse.json(cache);
  }

  const series: Record<string, number[]> = {};

  const batches = chunk(symbols, CONCURRENCY);
  for (const b of batches) {
    const results = await Promise.all(
      b.map(async (sym) => {
        try {
          const vals = await fetchSeries(sym);
          return [sym, vals] as const;
        } catch {
          return [sym, null] as const;
        }
      })
    );

    for (const [sym, vals] of results) {
      if (vals && vals.length) series[sym] = vals;
    }
  }

  const payload: SparkResp = { updatedAt: now, series };
  cache = payload;
  cacheAt = now;

  return NextResponse.json(payload);
}

