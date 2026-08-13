import { NextResponse } from "next/server";
import {
  STOCK_GRADER_ADMIN_COOKIE,
  createStockGraderAdminToken,
  isStockGraderAdminConfigured,
  verifyStockGraderAdminPasscode,
} from "@/lib/stock-grader-admin";

export const dynamic = "force-dynamic";

export async function POST(request: Request) {
  if (!isStockGraderAdminConfigured()) {
    return NextResponse.json({ detail: "Stock Grader admin passcode is not configured." }, { status: 503 });
  }

  const body = await request.json().catch(() => ({}));
  const passcode = typeof body.passcode === "string" ? body.passcode : "";
  if (!verifyStockGraderAdminPasscode(passcode)) {
    return NextResponse.json({ detail: "Invalid admin passcode." }, { status: 401 });
  }

  const response = NextResponse.json({ ok: true });
  response.cookies.set({
    name: STOCK_GRADER_ADMIN_COOKIE,
    value: createStockGraderAdminToken(),
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    maxAge: 60 * 60 * 12,
    path: "/",
  });
  return response;
}

export function DELETE() {
  const response = NextResponse.json({ ok: true });
  response.cookies.set({
    name: STOCK_GRADER_ADMIN_COOKIE,
    value: "",
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    maxAge: 0,
    path: "/",
  });
  return response;
}

