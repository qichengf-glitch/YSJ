import { NextResponse } from "next/server";
import { ACCESS_COOKIE, accessPasscode, createAccessToken } from "@/lib/access";

export async function POST(request: Request) {
  const body = await request.json().catch(() => ({}));
  const passcode = typeof body.passcode === "string" ? body.passcode : "";

  if (passcode !== accessPasscode()) {
    return NextResponse.json({ ok: false, message: "Invalid access code." }, { status: 401 });
  }

  const response = NextResponse.json({ ok: true });
  response.cookies.set({
    name: ACCESS_COOKIE,
    value: createAccessToken(),
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    maxAge: 60 * 60 * 12,
    path: "/",
  });

  return response;
}
