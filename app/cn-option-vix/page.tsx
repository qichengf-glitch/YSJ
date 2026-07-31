import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { ACCESS_COOKIE, verifyAccessToken } from "@/lib/access";
import CnOptionVixPage from "./CnOptionVixPage";

export const metadata = {
  title: "CN Option VIX Monitor | YSJLab",
  description: "Private China option volatility monitoring dashboard.",
};

export default function Page() {
  const token = cookies().get(ACCESS_COOKIE)?.value;
  if (!verifyAccessToken(token)) {
    redirect("/access");
  }

  const dashboardUrl =
    process.env.NEXT_PUBLIC_VIX_DASHBOARD_URL || "http://127.0.0.1:8765";

  return <CnOptionVixPage dashboardUrl={dashboardUrl} />;
}
