import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { ACCESS_COOKIE, verifyAccessToken } from "@/lib/access";
import PredictionMarketDashboard from "./PredictionMarketDashboard";

export const metadata = {
  title: "Prediction Market | YSJ Lab",
  description: "Polymarket macro probability, liquidity, and whale activity dashboard.",
};

export default function PredictionMarketsPage() {
  const token = cookies().get(ACCESS_COOKIE)?.value;
  if (!verifyAccessToken(token)) {
    redirect("/access");
  }

  return <PredictionMarketDashboard />;
}
