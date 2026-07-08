import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";

type RouteContext = {
  params: {
    path?: string[];
  };
};

const BACKEND_URL =
  process.env.MARKET_RADAR_BACKEND_URL ?? "http://127.0.0.1:8000";

async function proxyToMarketRadarBackend(
  request: NextRequest,
  context: RouteContext
) {
  const path = context.params.path?.join("/") ?? "";
  const incomingUrl = new URL(request.url);
  const targetUrl = new URL(`/api/${path}${incomingUrl.search}`, BACKEND_URL);
  const headers = new Headers(request.headers);

  headers.delete("host");
  headers.delete("content-length");

  const init: RequestInit = {
    method: request.method,
    headers,
    cache: "no-store",
  };

  if (request.method !== "GET" && request.method !== "HEAD") {
    init.body = await request.arrayBuffer();
  }

  try {
    const response = await fetch(targetUrl, init);
    const responseHeaders = new Headers(response.headers);

    responseHeaders.delete("content-encoding");
    responseHeaders.delete("transfer-encoding");

    return new Response(response.body, {
      status: response.status,
      statusText: response.statusText,
      headers: responseHeaders,
    });
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Market Radar backend unavailable";

    return NextResponse.json(
      {
        detail:
          "Market Radar backend is not reachable. Start the FastAPI service in jin10_us_dashboard_site_v4_2, or set MARKET_RADAR_BACKEND_URL.",
        error: message,
      },
      { status: 502 }
    );
  }
}

export const GET = proxyToMarketRadarBackend;
export const POST = proxyToMarketRadarBackend;
export const PUT = proxyToMarketRadarBackend;
export const PATCH = proxyToMarketRadarBackend;
export const DELETE = proxyToMarketRadarBackend;
