import fs from "fs";
import path from "path";

export const EDITABLE_STOCK_GRADER_CATEGORIES = [
  { key: "business_quality", display: "Business Quality" },
  { key: "income", display: "Income" },
  { key: "market_sentiment", display: "Market Sentiment" },
  { key: "industry", display: "Industry/Sector Tailwinds" },
] as const;

export type EditableStockGraderCategoryKey =
  (typeof EDITABLE_STOCK_GRADER_CATEGORIES)[number]["key"];

export type StockGraderOverrideRecord = {
  ticker: string;
  categoryKey: EditableStockGraderCategoryKey;
  category: string;
  score: number;
  note: string;
  confidence: "low" | "medium" | "high";
  author: string;
  createdAt: string;
  updatedAt: string;
};

export type StockGraderOverrideAuditEvent = {
  action: "upsert" | "delete";
  ticker: string;
  categoryKey: string;
  previous?: StockGraderOverrideRecord | null;
  next?: StockGraderOverrideRecord | null;
  actor: string;
  at: string;
};

type OverrideStore = {
  version: 1;
  records: StockGraderOverrideRecord[];
};

const DEFAULT_DATA_DIR = path.join(process.cwd(), "stock_grader", "data");

function dataDir() {
  return process.env.STOCK_GRADER_DATA_DIR || DEFAULT_DATA_DIR;
}

function overridePath() {
  return process.env.STOCK_GRADER_OVERRIDE_PATH || path.join(dataDir(), "overrides.json");
}

function auditPath() {
  return process.env.STOCK_GRADER_OVERRIDE_AUDIT_PATH || path.join(dataDir(), "override_audit.jsonl");
}

function ensureParent(filePath: string) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
}

function emptyStore(): OverrideStore {
  return { version: 1, records: [] };
}

function normalizeTicker(ticker: string) {
  return ticker.trim().toUpperCase();
}

function categoryDisplay(categoryKey: string) {
  return EDITABLE_STOCK_GRADER_CATEGORIES.find((item) => item.key === categoryKey)?.display;
}

function assertEditableCategory(categoryKey: string): asserts categoryKey is EditableStockGraderCategoryKey {
  if (!categoryDisplay(categoryKey)) {
    throw new Error("Category is not editable");
  }
}

function readStore(): OverrideStore {
  const filePath = overridePath();
  if (!fs.existsSync(filePath)) {
    return emptyStore();
  }

  try {
    const parsed = JSON.parse(fs.readFileSync(filePath, "utf8")) as OverrideStore;
    if (parsed.version !== 1 || !Array.isArray(parsed.records)) {
      return emptyStore();
    }
    return parsed;
  } catch {
    return emptyStore();
  }
}

function writeStore(store: OverrideStore) {
  const filePath = overridePath();
  ensureParent(filePath);
  const tempPath = `${filePath}.tmp`;
  fs.writeFileSync(tempPath, `${JSON.stringify(store, null, 2)}\n`);
  fs.renameSync(tempPath, filePath);
}

function appendAudit(event: StockGraderOverrideAuditEvent) {
  const filePath = auditPath();
  ensureParent(filePath);
  fs.appendFileSync(filePath, `${JSON.stringify(event)}\n`);
}

export function stockGraderCategoryKey(display: string) {
  const normalized = display.trim().toLowerCase();
  return EDITABLE_STOCK_GRADER_CATEGORIES.find((item) => item.display.toLowerCase() === normalized)?.key;
}

export function stockGraderOverrideId(ticker: string, categoryKey: string) {
  return `${normalizeTicker(ticker)}:${categoryKey}`;
}

export function listStockGraderOverrides() {
  return readStore().records.sort((a, b) => {
    const byTicker = a.ticker.localeCompare(b.ticker);
    if (byTicker) {
      return byTicker;
    }
    return a.category.localeCompare(b.category);
  });
}

export function getStockGraderOverrideMap() {
  return new Map(
    listStockGraderOverrides().map((record) => [
      stockGraderOverrideId(record.ticker, record.categoryKey),
      record,
    ])
  );
}

export function upsertStockGraderOverride(input: {
  ticker: string;
  categoryKey: string;
  score: number;
  note: string;
  confidence: string;
  author?: string;
}) {
  const ticker = normalizeTicker(input.ticker);
  assertEditableCategory(input.categoryKey);
  const score = Number(input.score);
  if (!Number.isInteger(score) || score < 1 || score > 10) {
    throw new Error("Score must be an integer from 1 to 10");
  }
  const note = input.note.trim();
  if (note.length < 6) {
    throw new Error("Note is required");
  }
  if (!["low", "medium", "high"].includes(input.confidence)) {
    throw new Error("Confidence must be low, medium, or high");
  }

  const store = readStore();
  const id = stockGraderOverrideId(ticker, input.categoryKey);
  const previousIndex = store.records.findIndex(
    (record) => stockGraderOverrideId(record.ticker, record.categoryKey) === id
  );
  const previous = previousIndex >= 0 ? store.records[previousIndex] : null;
  const now = new Date().toISOString();
  const next: StockGraderOverrideRecord = {
    ticker,
    categoryKey: input.categoryKey,
    category: categoryDisplay(input.categoryKey) || input.categoryKey,
    score,
    note,
    confidence: input.confidence as "low" | "medium" | "high",
    author: input.author?.trim() || "Admin",
    createdAt: previous?.createdAt || now,
    updatedAt: now,
  };

  if (previousIndex >= 0) {
    store.records[previousIndex] = next;
  } else {
    store.records.push(next);
  }
  writeStore(store);
  appendAudit({
    action: "upsert",
    ticker,
    categoryKey: input.categoryKey,
    previous,
    next,
    actor: next.author,
    at: now,
  });
  return next;
}

export function deleteStockGraderOverride(input: {
  ticker: string;
  categoryKey: string;
  actor?: string;
}) {
  const ticker = normalizeTicker(input.ticker);
  assertEditableCategory(input.categoryKey);
  const id = stockGraderOverrideId(ticker, input.categoryKey);
  const store = readStore();
  const previousIndex = store.records.findIndex(
    (record) => stockGraderOverrideId(record.ticker, record.categoryKey) === id
  );
  if (previousIndex < 0) {
    return null;
  }
  const [previous] = store.records.splice(previousIndex, 1);
  writeStore(store);
  appendAudit({
    action: "delete",
    ticker,
    categoryKey: input.categoryKey,
    previous,
    next: null,
    actor: input.actor?.trim() || "Admin",
    at: new Date().toISOString(),
  });
  return previous;
}

