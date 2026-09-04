"use client";

type AShareStrategyPanelFrameProps = {
  panelUrl: string;
};

export default function AShareStrategyPanelFrame({
  panelUrl,
}: AShareStrategyPanelFrameProps) {
  return (
    <main className="min-h-screen bg-[#FBFAF7] text-[#111827]">
      <iframe
        src={panelUrl}
        title="A-Share Strategy Panel"
        className="block h-[calc(100vh-4rem)] min-h-[760px] w-full border-0 bg-[#FBFAF7]"
      />
    </main>
  );
}
