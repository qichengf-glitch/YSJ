import { createHmac, timingSafeEqual } from "crypto";

export const ACCESS_COOKIE = "ysj_access";

const DEFAULT_SECRET = "ysj-local-access-secret";
const DEFAULT_PASSCODE = "0000";

function configuredPasscode() {
  return process.env.YSJ_ACCESS_PASSCODE?.trim() || "";
}

function configuredSecret() {
  return (
    process.env.YSJ_ACCESS_SECRET?.trim() ||
    process.env.YSJ_ACCESS_PASSCODE?.trim() ||
    ""
  );
}

export function isAccessConfigured() {
  if (process.env.NODE_ENV !== "production") {
    return true;
  }
  return Boolean(configuredPasscode() && configuredSecret());
}

function accessSecret() {
  return configuredSecret() || DEFAULT_SECRET;
}

export function accessPasscode() {
  return configuredPasscode() || DEFAULT_PASSCODE;
}

export function createAccessToken() {
  if (!isAccessConfigured()) {
    throw new Error("Production access control is not configured.");
  }
  const issuedAt = Date.now().toString();
  const signature = createHmac("sha256", accessSecret()).update(issuedAt).digest("hex");
  return `${issuedAt}.${signature}`;
}

export function verifyAccessToken(token?: string) {
  if (!isAccessConfigured() || !token) {
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
  if (Date.now() - issuedAtNumber > maxAgeMs || issuedAtNumber > Date.now() + 60_000) {
    return false;
  }

  const expected = createHmac("sha256", accessSecret()).update(issuedAt).digest("hex");
  const expectedBuffer = Buffer.from(expected);
  const signatureBuffer = Buffer.from(signature);

  return (
    expectedBuffer.length === signatureBuffer.length &&
    timingSafeEqual(expectedBuffer, signatureBuffer)
  );
}
