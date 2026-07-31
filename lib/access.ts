import { createHmac, timingSafeEqual } from "crypto";

export const ACCESS_COOKIE = "ysj_access";

const DEFAULT_SECRET = "ysj-local-access-secret";
const DEFAULT_PASSCODE = "0000";

function accessSecret() {
  return process.env.YSJ_ACCESS_SECRET || process.env.YSJ_ACCESS_PASSCODE || DEFAULT_SECRET;
}

export function accessPasscode() {
  return process.env.YSJ_ACCESS_PASSCODE || DEFAULT_PASSCODE;
}

export function createAccessToken() {
  const issuedAt = Date.now().toString();
  const signature = createHmac("sha256", accessSecret()).update(issuedAt).digest("hex");
  return `${issuedAt}.${signature}`;
}

export function verifyAccessToken(token?: string) {
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

  const expected = createHmac("sha256", accessSecret()).update(issuedAt).digest("hex");
  const expectedBuffer = Buffer.from(expected);
  const signatureBuffer = Buffer.from(signature);

  return (
    expectedBuffer.length === signatureBuffer.length &&
    timingSafeEqual(expectedBuffer, signatureBuffer)
  );
}
