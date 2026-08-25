import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { ACCESS_COOKIE, verifyAccessToken } from "@/lib/access";
import DailySummaryFrame from "./DailySummaryFrame";

export const metadata = {
  title: "Daily Summary | YSJ Lab",
  description: "Daily cross-market summary dashboard.",
};

export default function DailySummaryPage() {
  const token = cookies().get(ACCESS_COOKIE)?.value;
  if (!verifyAccessToken(token)) {
    redirect("/access");
  }

  return (
    <main className="min-h-[calc(100vh-4rem)] bg-[#f0f2f5]">
      <DailySummaryFrame />
    </main>
  );
}
