import fs from "fs";
import path from "path";

export type StockGraderCategory = {
  category: string;
  cell: string;
  score: number | null;
  reasonCell: string;
  reasonText: string;
  confidence: string;
  source: string;
};

export type StockGraderScore = {
  ticker: string;
  blockIndex: number | null;
  archetype: string;
  composite0To10: number | null;
  composite0To100: number | null;
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
  summary: {
    tickerCount: number;
    categoryCount: number;
    averageComposite: number | null;
    highConfidenceRows: number;
    watchOrReviewRows: number;
  };
};

type CsvRow = Record<string, string>;

const DEFAULT_REPORT_DIR = path.join(process.cwd(), "stock_grader", "data", "reports");

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
        composite0To10: parseNumber(row.composite_0_10),
        composite0To100: parseNumber(row.composite_0_100),
        categories: [],
      } satisfies StockGraderScore);

    current.categories.push({
      category: row.category || "Unknown",
      cell: row.cell || "",
      score: parseNumber(row.score),
      reasonCell: row.reason_cell || "",
      reasonText: row.reason_text || "",
      confidence: row.confidence || "unknown",
      source: row.source || "unknown",
    });
    byTicker.set(ticker, current);
  }

  return Array.from(byTicker.values()).sort((a, b) => {
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
    summary: {
      tickerCount: scores.length,
      categoryCount,
      averageComposite: composites.length
        ? Number((composites.reduce((sum, score) => sum + score, 0) / composites.length).toFixed(2))
        : null,
      highConfidenceRows,
      watchOrReviewRows: updateRows.filter((row) =>
        /watch|review|monitor/i.test(`${row.action} ${row.source}`)
      ).length,
    },
  };
}

