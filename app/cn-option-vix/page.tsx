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
    process.env.VIX_DASHBOARD_PUBLIC_URL ||
    process.env.NEXT_PUBLIC_VIX_DASHBOARD_URL ||
    "/api/cn-option-vix-dashboard/index.html";

  return <CnOptionVixPage dashboardUrl={dashboardUrl} />;
}
