import fs from "fs";
import path from "path";
import {
  getStockGraderOverrideMap,
  listStockGraderOverrides,
  stockGraderCategoryKey,
  stockGraderOverrideId,
  type StockGraderOverrideRecord,
} from "@/lib/stock-grader-overrides";

export type StockGraderCategory = {
  categoryKey: string;
  category: string;
  cell: string;
  systemScore: number | null;
  score: number | null;
  reasonCell: string;
  systemReasonText: string;
  reasonText: string;
  confidence: string;
  source: string;
  isManual: boolean;
  override: StockGraderOverrideRecord | null;
};

export type StockGraderScore = {
  ticker: string;
  blockIndex: number | null;
  archetype: string;
  systemComposite0To10: number | null;
  systemComposite0To100: number | null;
  composite0To10: number | null;
  composite0To100: number | null;
  hasManualOverride: boolean;
  categories: StockGraderCategory[];
};

export type StockGraderUpdate = {
  ticker: string;
  category: string;
  cell: string;
  oldScore: number | null;
  newScore: number | null;
  delta: number | null;
  reasonText: string;
  confidence: string;
  source: string;
  action: string;
};

export type StockGraderPayload = {
  latestFullScoreDate: string | null;
  latestUpdateDate: string | null;
  generatedAt: string | null;
  scores: StockGraderScore[];
  updates: StockGraderUpdate[];
  overrides: StockGraderOverrideRecord[];
  summary: {
    tickerCount: number;
    categoryCount: number;
    averageComposite: number | null;
    manualOverrideCount: number;
    manualTickerCount: number;
    highConfidenceRows: number;
    watchOrReviewRows: number;
  };
};

type CsvRow = Record<string, string>;

const DEFAULT_REPORT_DIR = path.join(process.cwd(), "stock_grader", "data", "reports");

const CATEGORY_KEY_BY_DISPLAY: Record<string, string> = {
  Valuation: "valuation",
  Growth: "growth",
  Profitability: "profitability",
  Financials: "financials",
  "Business Quality": "business_quality",
  Management: "management",
  Income: "income",
  "Market Sentiment": "market_sentiment",
  "EPS/Revison Trends": "eps_revisions",
  "Industry/Sector Tailwinds": "industry",
};

const ARCHETYPE_WEIGHTS: Record<string, Record<string, number>> = {
  A: {
    valuation: 0.25,
    growth: 0.05,
    profitability: 0.15,
    financials: 0.1,
    business_quality: 0.15,
    management: 0.1,
    income: 0.1,
    market_sentiment: 0.025,
    eps_revisions: 0.025,
    industry: 0.05,
  },
  B: {
    valuation: 0.15,
    growth: 0.15,
    profitability: 0.15,
    financials: 0.1,
    business_quality: 0.2,
    management: 0.1,
    income: 0.05,
    market_sentiment: 0.025,
    eps_revisions: 0.05,
    industry: 0.025,
  },
  C: {
    valuation: 0.1,
    growth: 0.25,
    profitability: 0.05,
    financials: 0.15,
    business_quality: 0.2,
    management: 0.1,
    income: 0.05,
    market_sentiment: 0.025,
    eps_revisions: 0.05,
    industry: 0.025,
  },
  D: {
    valuation: 0.15,
    growth: 0.05,
    profitability: 0.1,
    financials: 0.2,
    business_quality: 0.05,
    management: 0.1,
    income: 0.05,
    market_sentiment: 0.05,
    eps_revisions: 0.1,
    industry: 0.15,
  },
  E: {
    valuation: 0.05,
    growth: 0.1,
    profitability: 0,
    financials: 0.25,
    business_quality: 0.3,
    management: 0.15,
    income: 0,
    market_sentiment: 0.05,
    eps_revisions: 0,
    industry: 0.1,
  },
  F: {
    valuation: 0.15,
    growth: 0.1,
    profitability: 0.2,
    financials: 0.2,
    business_quality: 0.15,
    management: 0.1,
    income: 0,
    market_sentiment: 0.025,
    eps_revisions: 0.025,
    industry: 0.05,
  },
  G: {
    valuation: 0.1,
    growth: 0.1,
    profitability: 0.1,
    financials: 0.2,
    business_quality: 0.1,
    management: 0.2,
    income: 0,
    market_sentiment: 0.05,
    eps_revisions: 0.1,
    industry: 0.05,
  },
};

function reportDir() {
  return process.env.STOCK_GRADER_REPORT_DIR || DEFAULT_REPORT_DIR;
}

function parseNumber(value: string | undefined): number | null {
  if (value == null || value.trim() === "") {
    return null;
  }
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function archetypeLetter(archetype: string) {
  const match = archetype.match(/^([A-G]):/);
  return match?.[1] || "";
}

function roundScore(value: number) {
  return Number(value.toFixed(2));
}

function recomputeComposite(
  archetype: string,
  categories: Pick<StockGraderCategory, "categoryKey" | "score">[],
  fallback: number | null
) {
  const weights = ARCHETYPE_WEIGHTS[archetypeLetter(archetype)];
  if (!weights) {
    return fallback;
  }
  let total = 0;
  let seen = false;
  for (const category of categories) {
    const weight = weights[category.categoryKey];
    if (weight == null || category.score == null) {
      continue;
    }
    total += category.score * weight;
    seen = true;
  }
  return seen ? roundScore(total) : fallback;
}

function parseDateFromName(fileName: string, prefix: string) {
  const match = fileName.match(new RegExp(`^${prefix}_(\\d{8})\\.csv$`));
  if (!match) {
    return null;
  }
  const raw = match[1];
  return `${raw.slice(0, 4)}-${raw.slice(4, 6)}-${raw.slice(6, 8)}`;
}

function latestCsv(prefix: "full_scores" | "updates") {
  const dir = reportDir();
  if (!fs.existsSync(dir)) {
    return null;
  }
  const files = fs
    .readdirSync(dir)
    .filter((file) => file.startsWith(`${prefix}_`) && file.endsWith(".csv"))
    .sort();

  const fileName = files.at(-1);
  if (!fileName) {
    return null;
  }

  return {
    fileName,
    filePath: path.join(dir, fileName),
    date: parseDateFromName(fileName, prefix),
  };
}

function parseCsv(text: string): CsvRow[] {
  const rows: string[][] = [];
  let row: string[] = [];
  let cell = "";
  let quoted = false;

  for (let index = 0; index < text.length; index += 1) {
    const char = text[index];
    const next = text[index + 1];

    if (char === '"') {
      if (quoted && next === '"') {
        cell += '"';
        index += 1;
      } else {
        quoted = !quoted;
      }
      continue;
    }

    if (char === "," && !quoted) {
      row.push(cell);
      cell = "";
      continue;
    }

    if ((char === "\n" || char === "\r") && !quoted) {
      if (char === "\r" && next === "\n") {
        index += 1;
      }
      row.push(cell);
      if (row.some((value) => value.trim() !== "")) {
        rows.push(row);
      }
      row = [];
      cell = "";
      continue;
    }

    cell += char;
  }

  if (cell || row.length) {
    row.push(cell);
    if (row.some((value) => value.trim() !== "")) {
      rows.push(row);
    }
  }

  const [header, ...body] = rows;
  if (!header) {
    return [];
  }

  return body.map((values) =>
    header.reduce<CsvRow>((out, key, index) => {
      out[key] = values[index] ?? "";
      return out;
    }, {})
  );
}

function readCsv(filePath: string) {
  return parseCsv(fs.readFileSync(filePath, "utf8"));
}

function readFullScores() {
  const latest = latestCsv("full_scores");
  if (!latest) {
    return { date: null, rows: [] as CsvRow[] };
  }
  return { date: latest.date, rows: readCsv(latest.filePath) };
}

function readUpdates() {
  const latest = latestCsv("updates");
  if (!latest) {
    return { date: null, rows: [] as CsvRow[] };
  }
  return { date: latest.date, rows: readCsv(latest.filePath) };
}

function buildScores(rows: CsvRow[]): StockGraderScore[] {
  const byTicker = new Map<string, StockGraderScore>();
  const overrides = getStockGraderOverrideMap();

  for (const row of rows) {
    const ticker = row.ticker?.trim().toUpperCase();
    if (!ticker) {
      continue;
    }

    const current =
      byTicker.get(ticker) ??
      ({
        ticker,
        blockIndex: parseNumber(row.block_index),
        archetype: row.archetype || "Unclassified",
        systemComposite0To10: parseNumber(row.composite_0_10),
        systemComposite0To100: parseNumber(row.composite_0_100),
        composite0To10: parseNumber(row.composite_0_10),
        composite0To100: parseNumber(row.composite_0_100),
        hasManualOverride: false,
        categories: [],
      } satisfies StockGraderScore);

    const category = row.category || "Unknown";
    const categoryKey = CATEGORY_KEY_BY_DISPLAY[category] || stockGraderCategoryKey(category) || category;
    const override = overrides.get(stockGraderOverrideId(ticker, categoryKey)) ?? null;
    const systemScore = parseNumber(row.score);
    const score = override?.score ?? systemScore;
    const systemReasonText = row.reason_text || "";
    current.categories.push({
      categoryKey,
      category,
      cell: row.cell || "",
      systemScore,
      score,
      reasonCell: row.reason_cell || "",
      systemReasonText,
      reasonText: override?.note || systemReasonText,
      confidence: override?.confidence || row.confidence || "unknown",
      source: override ? "manual" : row.source || "unknown",
      isManual: Boolean(override),
      override,
    });
    if (override) {
      current.hasManualOverride = true;
    }
    byTicker.set(ticker, current);
  }

  const scores = Array.from(byTicker.values()).map((score) => {
    const finalComposite = recomputeComposite(score.archetype, score.categories, score.systemComposite0To10);
    return {
      ...score,
      composite0To10: finalComposite,
      composite0To100: finalComposite == null ? score.systemComposite0To100 : roundScore(finalComposite * 10),
    };
  });

  return scores.sort((a, b) => {
    const left = a.blockIndex ?? Number.MAX_SAFE_INTEGER;
    const right = b.blockIndex ?? Number.MAX_SAFE_INTEGER;
    return left - right;
  });
}

function buildUpdates(rows: CsvRow[]): StockGraderUpdate[] {
  return rows.map((row) => ({
    ticker: row.ticker || "",
    category: row.category || "",
    cell: row.cell || "",
    oldScore: parseNumber(row.old_score),
    newScore: parseNumber(row.new_score),
    delta: parseNumber(row.delta),
    reasonText: row.reason_text || "",
    confidence: row.confidence || "",
    source: row.source || "",
    action: row.action || "",
  }));
}

export function getStockGraderPayload(): StockGraderPayload {
  const full = readFullScores();
  const updates = readUpdates();
  const scores = buildScores(full.rows);
  const overrides = listStockGraderOverrides();
  const updateRows = buildUpdates(updates.rows);
  const composites = scores
    .map((score) => score.composite0To10)
    .filter((score): score is number => score != null);
  const categoryCount = scores[0]?.categories.length ?? 0;
  const highConfidenceRows = scores.reduce(
    (total, score) =>
      total + score.categories.filter((category) => category.confidence === "high").length,
    0
  );

  return {
    latestFullScoreDate: full.date,
    latestUpdateDate: updates.date,
    generatedAt: full.date || updates.date,
    scores,
    updates: updateRows,
    overrides,
    summary: {
      tickerCount: scores.length,
      categoryCount,
      averageComposite: composites.length
        ? Number((composites.reduce((sum, score) => sum + score, 0) / composites.length).toFixed(2))
        : null,
      manualOverrideCount: overrides.length,
      manualTickerCount: new Set(overrides.map((override) => override.ticker)).size,
      highConfidenceRows,
      watchOrReviewRows: updateRows.filter((row) =>
        /watch|review|monitor/i.test(`${row.action} ${row.source}`)
      ).length,
    },
  };
}
