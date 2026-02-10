import React from "react";

function clamp(n: number, min: number, max: number) {
  return Math.max(min, Math.min(max, n));
}

export default function Sparkline({
  values,
  trend = "down",
  width = 110,
  height = 28,
}: {
  values?: number[];
  trend?: "up" | "down";
  width?: number;
  height?: number;
}) {
  if (!values || values.length < 2) {
    return (
      <div
        className="rounded bg-white/5"
        style={{ width, height }}
        aria-label="sparkline-loading"
      />
    );
  }

  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;

  const padX = 2;
  const padY = 2;

  const pts = values.map((v, i) => {
    const x =
      padX +
      (i * (width - padX * 2)) / (values.length - 1);
    const y =
      padY + (1 - (v - min) / range) * (height - padY * 2);
    return [x, y] as const;
  });

  const d = pts
    .map(([x, y], idx) => `${idx === 0 ? "M" : "L"} ${x.toFixed(2)} ${y.toFixed(2)}`)
    .join(" ");

  const [lx, ly] = pts[pts.length - 1];

  const strokeClass = trend === "up" ? "stroke-emerald-400" : "stroke-red-400";
  const dotClass = trend === "up" ? "fill-emerald-400" : "fill-red-400";

  const dotX = clamp(lx, 2, width - 2);
  const dotY = clamp(ly, 2, height - 2);

  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} aria-label="sparkline">
      <path d={d} className={`${strokeClass}`} fill="none" strokeWidth="2" strokeLinecap="round" />
      <circle cx={dotX} cy={dotY} r="2.6" className={dotClass} />
    </svg>
  );
}

