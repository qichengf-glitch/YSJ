export const metadata = {
  title: "Market Radar | YSJ Lab",
  description: "US event intelligence dashboard for quick market access.",
};

export default function MarketRadarPage() {
  return (
    <main className="h-[calc(100vh-4rem)] bg-[#f5f5f7]">
      <iframe
        src="/market-radar/index.html"
        title="Market Radar Dashboard"
        className="h-full w-full border-0"
      />
    </main>
  );
}
