import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { ACCESS_COOKIE, verifyAccessToken } from "@/lib/access";
import { getStockGraderPayload } from "@/lib/stock-grader";
import StockGraderDashboard from "./StockGraderDashboard";

export const metadata = {
  title: "Stock Grader | YSJ Lab",
  description: "Deterministic US equity fundamental scoring dashboard.",
};

export default function StockGraderPage() {
  const token = cookies().get(ACCESS_COOKIE)?.value;
  if (!verifyAccessToken(token)) {
    redirect("/access");
  }

  return <StockGraderDashboard payload={getStockGraderPayload()} />;
}

