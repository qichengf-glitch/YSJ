import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";
import { ACCESS_COOKIE, verifyAccessToken } from "@/lib/access";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

type RouteContext = {
  params: {
    path?: string[];
  };
};

const BACKEND_URL =
  process.env.DAILY_SUMMARY_BACKEND_URL ?? "http://127.0.0.1:8010";

const corsHeaders = {
  "access-control-allow-origin": "*",
  "access-control-allow-methods": "GET,POST,PUT,PATCH,DELETE,OPTIONS",
  "access-control-allow-headers": "content-type, authorization",
};

async function proxyToDailySummaryBackend(request: NextRequest, context: RouteContext) {
  if (!verifyAccessToken(cookies().get(ACCESS_COOKIE)?.value)) {
    return NextResponse.json(
      { detail: "Authentication required." },
      { status: 401, headers: corsHeaders }
    );
  }

  const path = context.params.path?.join("/") ?? "";
  const incomingUrl = new URL(request.url);
  const targetUrl = new URL(
    `/api/daily-summary/${path}${incomingUrl.search}`,
    BACKEND_URL
  );
  const headers = new Headers(request.headers);
  headers.delete("host");
  headers.delete("content-length");
  headers.delete("cookie");

  const init: RequestInit = {
    method: request.method,
    headers,
    cache: "no-store",
    redirect: "manual",
  };

  if (request.method !== "GET" && request.method !== "HEAD") {
    init.body = await request.arrayBuffer();
  }

  try {
    const response = await fetch(targetUrl, init);
    const responseHeaders = new Headers(response.headers);
    responseHeaders.delete("content-encoding");
    responseHeaders.delete("content-length");
    responseHeaders.delete("transfer-encoding");
    Object.entries(corsHeaders).forEach(([key, value]) => responseHeaders.set(key, value));
    responseHeaders.set("cache-control", "no-store");

    return new Response(response.body, {
      status: response.status,
      statusText: response.statusText,
      headers: responseHeaders,
    });
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Daily Summary backend unavailable";
    return NextResponse.json(
      {
        detail:
          "Daily Summary backend is not reachable. Start daily_summary_backend on port 8010 or set DAILY_SUMMARY_BACKEND_URL.",
        error: message,
      },
      { status: 502, headers: corsHeaders }
    );
  }
}

export const GET = proxyToDailySummaryBackend;
export const POST = proxyToDailySummaryBackend;
export const PUT = proxyToDailySummaryBackend;
export const PATCH = proxyToDailySummaryBackend;
export const DELETE = proxyToDailySummaryBackend;
export function OPTIONS() {
  return new Response(null, { status: 204, headers: corsHeaders });
}
