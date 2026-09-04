import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { ACCESS_COOKIE, verifyAccessToken } from "@/lib/access";
import AShareDataDashboard from "./AShareDataDashboard";

export const metadata = {
  title: "A-Share Data Panel | YSJ Lab",
  description: "ClickHouse-backed A-share market data panel for monitoring and backtesting.",
};

export default function AShareDataPage() {
  const token = cookies().get(ACCESS_COOKIE)?.value;
  if (!verifyAccessToken(token)) {
    redirect("/access");
  }

  return <AShareDataDashboard />;
}
