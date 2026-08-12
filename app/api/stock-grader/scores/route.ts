import { NextResponse } from "next/server";
import { cookies } from "next/headers";
import { ACCESS_COOKIE, verifyAccessToken } from "@/lib/access";
import { getStockGraderPayload } from "@/lib/stock-grader";

export const dynamic = "force-dynamic";

export function GET() {
  const token = cookies().get(ACCESS_COOKIE)?.value;
  if (!verifyAccessToken(token)) {
    return NextResponse.json({ detail: "Authentication required." }, { status: 401 });
  }

  return NextResponse.json(getStockGraderPayload(), {
    headers: {
      "cache-control": "no-store",
    },
  });
}
