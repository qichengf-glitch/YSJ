import { cookies } from "next/headers";
import { ACCESS_COOKIE, verifyAccessToken } from "@/lib/access";

export async function GET() {
  const token = cookies().get(ACCESS_COOKIE)?.value;

  return Response.json(
    { authenticated: verifyAccessToken(token) },
    {
      headers: {
        "Cache-Control": "no-store",
      },
    }
  );
}
