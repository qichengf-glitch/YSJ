import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import type { ReactNode } from "react";

type QuantModuleHeaderProps = {
  title: string;
  subtitle: string;
  backLabel?: string;
  icon: ReactNode;
  meta?: ReactNode;
  actions?: ReactNode;
};

export default function QuantModuleHeader({
  title,
  subtitle,
  backLabel = "Quant Monitor",
  icon,
  meta,
  actions,
}: QuantModuleHeaderProps) {
  return (
    <section className="sticky top-0 z-20 border-b border-[#E6DDCD]/80 bg-[#FFFDF8]/78 px-5 py-3 shadow-[0_16px_42px_rgba(78,56,21,0.10)] backdrop-blur-xl sm:px-8 lg:px-10">
      <div className="mx-auto flex max-w-[1800px] flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex min-w-0 flex-col gap-3 sm:flex-row sm:items-center">
          <Link
            href="/access"
            className="inline-flex h-10 w-fit items-center gap-2 border border-[#D7B46A] bg-white/55 px-4 text-sm font-black text-[#5F4820] transition hover:bg-[#F8F1E3]"
          >
            <ArrowLeft className="h-4 w-4" />
            {backLabel}
          </Link>
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-[#8A6A2F]">{icon}</span>
              <h1 className="text-xl font-black text-[#111827] sm:text-2xl">{title}</h1>
            </div>
            <p className="mt-1 text-sm font-semibold text-[#5B6472]">{subtitle}</p>
          </div>
        </div>

        {(meta || actions) ? (
          <div className="flex flex-wrap items-center gap-2">
            {meta}
            {actions}
          </div>
        ) : null}
      </div>
    </section>
  );
}
