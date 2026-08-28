"use client";

type CnOptionVixPageProps = {
  dashboardUrl: string;
};

export default function CnOptionVixPage({ dashboardUrl }: CnOptionVixPageProps) {
  return (
    <main className="min-h-screen bg-[#FBFAF7] text-[#111827]">
      <iframe
        src={dashboardUrl}
        title="CN Option VIX Monitor"
        className="block h-[calc(100vh-4rem)] min-h-[720px] w-full border-0 bg-[#FBFAF7]"
      />
    </main>
  );
}
