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
  process.env.MARKET_RADAR_BACKEND_URL ?? "http://127.0.0.1:8000";

const corsHeaders = {
  "access-control-allow-origin": "*",
  "access-control-allow-methods": "GET,POST,PUT,PATCH,DELETE,OPTIONS",
  "access-control-allow-headers": "content-type, authorization",
};

function isAuthorized() {
  return verifyAccessToken(cookies().get(ACCESS_COOKIE)?.value);
}

async function proxyToMarketRadarBackend(
  request: NextRequest,
  context: RouteContext
) {
  if (!isAuthorized()) {
    return NextResponse.json(
      { detail: "Authentication required." },
      { status: 401, headers: corsHeaders }
    );
  }

  const path = context.params.path?.join("/") ?? "";
  const incomingUrl = new URL(request.url);
  const targetUrl = new URL(`/api/${path}${incomingUrl.search}`, BACKEND_URL);
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
    responseHeaders.set("cache-control", "no-store");
    Object.entries(corsHeaders).forEach(([key, value]) => responseHeaders.set(key, value));

    return new Response(response.body, {
      status: response.status,
      statusText: response.statusText,
      headers: responseHeaders,
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Market Radar backend unavailable";
    return NextResponse.json(
      {
        detail: "Market Radar backend is not reachable. Start jin10_us_dashboard_site on port 8000 or set MARKET_RADAR_BACKEND_URL.",
        error: message,
      },
      { status: 502, headers: corsHeaders }
    );
  }
}

export const GET = proxyToMarketRadarBackend;
export const POST = proxyToMarketRadarBackend;
export const PUT = proxyToMarketRadarBackend;
export const PATCH = proxyToMarketRadarBackend;
export const DELETE = proxyToMarketRadarBackend;
export function OPTIONS() {
  return new Response(null, { status: 204, headers: corsHeaders });
}
