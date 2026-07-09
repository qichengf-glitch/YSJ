import DailySummaryFrame from "./DailySummaryFrame";

export const metadata = {
  title: "Daily Summary | YSJ Lab",
  description: "Daily cross-market summary dashboard.",
};

export default function DailySummaryPage() {
  return (
    <main className="h-[calc(100vh-4rem)] bg-[#f0f2f5]">
      <DailySummaryFrame />
    </main>
  );
}
