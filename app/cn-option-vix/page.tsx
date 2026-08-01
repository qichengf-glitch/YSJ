import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { ACCESS_COOKIE, verifyAccessToken } from "@/lib/access";
import CnOptionVixPage from "./CnOptionVixPage";

export const metadata = {
  title: "CN Option VIX Monitor | YSJLab",
  description: "Private China option volatility monitoring dashboard.",
};

function normalizeDashboardUrl(url: string) {
  return url.replace(
    /\/api\/cn-option-vix-dashboard\/?$/,
    "/api/cn-option-vix-dashboard/index.html"
  );
}

export default function Page() {
  const token = cookies().get(ACCESS_COOKIE)?.value;
  if (!verifyAccessToken(token)) {
    redirect("/access");
  }

  const configuredDashboardUrl =
    process.env.VIX_DASHBOARD_PUBLIC_URL ||
    process.env.NEXT_PUBLIC_VIX_DASHBOARD_URL ||
    "/api/cn-option-vix-dashboard/index.html";
  const dashboardUrl = normalizeDashboardUrl(configuredDashboardUrl);

  return <CnOptionVixPage dashboardUrl={dashboardUrl} />;
}
