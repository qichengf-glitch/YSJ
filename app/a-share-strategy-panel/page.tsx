import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { ACCESS_COOKIE, verifyAccessToken } from "@/lib/access";
import AShareStrategyPanelFrame from "./AShareStrategyPanelFrame";

export const metadata = {
  title: "A-Share Strategy Panel | YSJ Lab",
  description: "Internal tick-stock-panel workspace for A-share monitoring and backtesting.",
};

export default function AShareStrategyPanelPage() {
  const token = cookies().get(ACCESS_COOKIE)?.value;
  if (!verifyAccessToken(token)) {
    redirect("/access");
  }

  return <AShareStrategyPanelFrame panelUrl="/tick-panel" />;
}
