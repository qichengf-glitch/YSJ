import { NextResponse } from "next/server";
import { cookies } from "next/headers";
import {
  STOCK_GRADER_ADMIN_COOKIE,
  verifyStockGraderAdminToken,
} from "@/lib/stock-grader-admin";
import { getStockGraderPayload } from "@/lib/stock-grader";
import {
  deleteStockGraderOverride,
  listStockGraderOverrides,
  upsertStockGraderOverride,
} from "@/lib/stock-grader-overrides";

export const dynamic = "force-dynamic";

function isAdmin() {
  return verifyStockGraderAdminToken(cookies().get(STOCK_GRADER_ADMIN_COOKIE)?.value);
}

function unauthorized() {
  return NextResponse.json({ detail: "Admin authentication required." }, { status: 401 });
}

export function GET() {
  if (!isAdmin()) {
    return unauthorized();
  }
  return NextResponse.json({
    overrides: listStockGraderOverrides(),
    payload: getStockGraderPayload(),
  });
}

export async function POST(request: Request) {
  if (!isAdmin()) {
    return unauthorized();
  }

  const body = await request.json().catch(() => ({}));
  try {
    const override = upsertStockGraderOverride({
      ticker: String(body.ticker || ""),
      categoryKey: String(body.categoryKey || ""),
      score: Number(body.score),
      note: String(body.note || ""),
      confidence: String(body.confidence || "medium"),
      author: String(body.author || "Admin"),
    });
    return NextResponse.json({
      ok: true,
      override,
      overrides: listStockGraderOverrides(),
      payload: getStockGraderPayload(),
    });
  } catch (error) {
    return NextResponse.json(
      { detail: error instanceof Error ? error.message : "Could not save override." },
      { status: 400 }
    );
  }
}

export async function DELETE(request: Request) {
  if (!isAdmin()) {
    return unauthorized();
  }

  const body = await request.json().catch(() => ({}));
  try {
    const removed = deleteStockGraderOverride({
      ticker: String(body.ticker || ""),
      categoryKey: String(body.categoryKey || ""),
      actor: String(body.actor || "Admin"),
    });
    return NextResponse.json({
      ok: true,
      removed,
      overrides: listStockGraderOverrides(),
      payload: getStockGraderPayload(),
    });
  } catch (error) {
    return NextResponse.json(
      { detail: error instanceof Error ? error.message : "Could not delete override." },
      { status: 400 }
    );
  }
}

