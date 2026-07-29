import { NextResponse } from "next/server";
import { cookies } from "next/headers";
import { ACCESS_COOKIE, verifyAccessToken } from "@/lib/access";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

async function probe(name: string, url: string) {
  const started = Date.now();
  try {
    const response = await fetch(url, { cache: "no-store" });
    const body = await response.json().catch(() => null);
    return { name, ok: response.ok, status: response.status, latency_ms: Date.now() - started, body };
  } catch (error) {
    return {
      name,
      ok: false,
      status: 0,
      latency_ms: Date.now() - started,
      error: error instanceof Error ? error.message : String(error),
    };
  }
}

export async function GET() {
  if (!verifyAccessToken(cookies().get(ACCESS_COOKIE)?.value)) {
    return NextResponse.json({ detail: "Authentication required." }, { status: 401 });
  }

  const marketBase = process.env.MARKET_RADAR_BACKEND_URL ?? "http://127.0.0.1:8000";
  const vixBase = process.env.CN_VIX_BACKEND_URL ?? "http://127.0.0.1:8765";
  const services = await Promise.all([
    probe("jin10", new URL("/api/health", marketBase).toString()),
    probe("cn_option_vix", new URL("/healthz", vixBase).toString()),
  ]);
  const ok = services.every((service) => service.ok);
  return NextResponse.json({ ok, services }, { status: ok ? 200 : 503 });
}
