"use client";

import Link from "next/link";

interface SectionEntryCardProps {
  href: string;
  title: string;
  subtitle: string;
}

export function SectionEntryCard({ href, title, subtitle }: SectionEntryCardProps) {
  return (
    <Link
      href={href}
      className="block rounded-xl border border-gray-200 bg-white/80 px-4 py-3 shadow-sm transition hover:border-primary hover:shadow-md"
    >
      <div className="text-sm font-semibold text-gray-900">{title}</div>
      <div className="mt-1 text-xs text-gray-600">{subtitle}</div>
    </Link>
  );
}

