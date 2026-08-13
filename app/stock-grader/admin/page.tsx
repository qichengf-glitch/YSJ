import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { ACCESS_COOKIE, verifyAccessToken } from "@/lib/access";
import {
  STOCK_GRADER_ADMIN_COOKIE,
  isStockGraderAdminConfigured,
  verifyStockGraderAdminToken,
} from "@/lib/stock-grader-admin";
import { getStockGraderPayload } from "@/lib/stock-grader";
import StockGraderAdminConsole from "./StockGraderAdminConsole";

export const metadata = {
  title: "Stock Grader Admin | YSJ Lab",
  description: "Admin override console for discretionary Stock Grader inputs.",
};

export default function StockGraderAdminPage() {
  const token = cookies().get(ACCESS_COOKIE)?.value;
  if (!verifyAccessToken(token)) {
    redirect("/access");
  }

  const adminToken = cookies().get(STOCK_GRADER_ADMIN_COOKIE)?.value;
  const isAdmin = verifyStockGraderAdminToken(adminToken);

  return (
    <StockGraderAdminConsole
      initialPayload={getStockGraderPayload()}
      initialIsAdmin={isAdmin}
      isConfigured={isStockGraderAdminConfigured()}
    />
  );
}

