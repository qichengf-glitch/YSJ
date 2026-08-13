import { createHmac, timingSafeEqual } from "crypto";

export const STOCK_GRADER_ADMIN_COOKIE = "ysj_stock_grader_admin";

const DEFAULT_ADMIN_SECRET = "ysj-stock-grader-local-admin-secret";

function adminSecret() {
  return (
    process.env.STOCK_GRADER_ADMIN_SECRET ||
    process.env.STOCK_GRADER_ADMIN_PASSCODE ||
    DEFAULT_ADMIN_SECRET
  );
}

export function isStockGraderAdminConfigured() {
  return Boolean(process.env.STOCK_GRADER_ADMIN_PASSCODE);
}

export function verifyStockGraderAdminPasscode(passcode: string) {
  const expected = process.env.STOCK_GRADER_ADMIN_PASSCODE;
  if (!expected) {
    return false;
  }
  const left = Buffer.from(passcode);
  const right = Buffer.from(expected);
  return left.length === right.length && timingSafeEqual(left, right);
}

export function createStockGraderAdminToken() {
  const issuedAt = Date.now().toString();
  const signature = createHmac("sha256", adminSecret()).update(issuedAt).digest("hex");
  return `${issuedAt}.${signature}`;
}

export function verifyStockGraderAdminToken(token?: string) {
  if (!token) {
    return false;
  }

  const [issuedAt, signature] = token.split(".");
  if (!issuedAt || !signature) {
    return false;
  }

  const issuedAtNumber = Number(issuedAt);
  if (!Number.isFinite(issuedAtNumber)) {
    return false;
  }

  const maxAgeMs = 1000 * 60 * 60 * 12;
  if (Date.now() - issuedAtNumber > maxAgeMs) {
    return false;
  }

  const expected = createHmac("sha256", adminSecret()).update(issuedAt).digest("hex");
  const expectedBuffer = Buffer.from(expected);
  const signatureBuffer = Buffer.from(signature);
  return (
    expectedBuffer.length === signatureBuffer.length &&
    timingSafeEqual(expectedBuffer, signatureBuffer)
  );
}

