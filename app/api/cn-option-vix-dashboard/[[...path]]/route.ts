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
  process.env.CN_VIX_BACKEND_URL ?? "http://127.0.0.1:8765";

async function proxyToVixBackend(request: NextRequest, context: RouteContext) {
  if (!verifyAccessToken(cookies().get(ACCESS_COOKIE)?.value)) {
    return NextResponse.json(
      { detail: "Authentication required." },
      { status: 401, headers: { "cache-control": "no-store" } }
    );
  }

  const rawPath = context.params.path?.join("/") ?? "";
  const path = rawPath === "index.html" ? "" : rawPath;
  const incomingUrl = new URL(request.url);
  const targetUrl = new URL(`/${path}${incomingUrl.search}`, BACKEND_URL);
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
    responseHeaders.set("cache-control", "no-store, no-cache, must-revalidate");

    return new Response(response.body, {
      status: response.status,
      statusText: response.statusText,
      headers: responseHeaders,
    });
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "CN VIX backend unavailable";
    return NextResponse.json(
      {
        detail:
          "CN VIX backend is not reachable. Start cn_option_vix on port 8765 or set CN_VIX_BACKEND_URL.",
        error: message,
      },
      { status: 502, headers: { "cache-control": "no-store" } }
    );
  }
}

export const GET = proxyToVixBackend;
export const POST = proxyToVixBackend;
export const PUT = proxyToVixBackend;
export const PATCH = proxyToVixBackend;
export const DELETE = proxyToVixBackend;
