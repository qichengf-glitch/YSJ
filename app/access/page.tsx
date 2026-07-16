import { cookies } from "next/headers";
import { ACCESS_COOKIE, verifyAccessToken } from "@/lib/access";
import AccessPortal from "./AccessPortal";

export default function AccessPage() {
  const token = cookies().get(ACCESS_COOKIE)?.value;
  const isAuthenticated = verifyAccessToken(token);

  return <AccessPortal isAuthenticated={isAuthenticated} />;
}
