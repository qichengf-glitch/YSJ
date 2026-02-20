"use client";

import Link from "next/link";
import Section from "@/components/Section";
import { researchPapers } from "@/data/research";

export default function TheoreticalResearchIndexPage() {
  return (
    <main className="min-h-screen">
      <Section className="pt-3 pb-10 sm:pt-4 sm:pb-12">
        <div className="mx-auto max-w-6xl">
          {/* Header */}
          <header className="mb-10 rounded-3xl border border-slate-200 bg-white/55 px-6 py-7 sm:px-8 sm:py-9 shadow-[0_14px_35px_rgba(15,23,42,0.07)]">
            <nav className="text-sm text-gray-500" aria-label="Breadcrumb">
              <ol className="flex items-center gap-1">
                <li>
                  <Link href="/research" className="hover:text-primary">
                    Research Hub
                  </Link>
                </li>
                <li>/</li>
                <li className="font-medium text-gray-700">
                  Theoretical Research
                </li>
              </ol>
            </nav>

            <h1 className="mt-4 font-playfair text-5xl sm:text-6xl font-semibold text-gray-900 tracking-tight">
              Theoretical Research
            </h1>
            <p className="mt-4 text-xl text-gray-600 leading-relaxed max-w-4xl">
              Conceptual work that underpins YSJ Lab&apos;s systematic strategies –
              focusing on market microstructure, liquidity regimes, risk premia,
              and cross-asset interactions.
            </p>
          </header>

          {/* Article list */}
          <div className="space-y-8">
            {researchPapers.map((paper) => (
              <Link
                key={paper.slug}
                href={`/research/${paper.slug}`}
                className="group block rounded-2xl border border-slate-200 bg-[#f7fbff] p-6 sm:p-7 shadow-[0_10px_30px_rgba(15,23,42,0.06)] transition-all duration-300 ease-out hover:-translate-y-0.5 hover:shadow-[0_18px_40px_rgba(15,23,42,0.12)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-primary"
              >
                <div className="flex items-baseline gap-3 mb-1">
                  <span className="text-base text-primary font-medium">
                    {paper.category}
                  </span>
                  <span className="flex-1 h-px bg-primary/20 min-w-[2rem]" />
                </div>
                <h2 className="font-playfair text-3xl sm:text-4xl font-semibold text-gray-900 group-hover:text-primary transition-colors mt-2">
                  {paper.title}
                </h2>
                <p className="text-base text-gray-500 italic mt-1">
                  {paper.publishedAt ?? paper.year}
                </p>
                <p className="text-lg text-gray-600 leading-relaxed mt-4">
                  {paper.summary}
                </p>
              </Link>
            ))}
          </div>
        </div>
      </Section>
    </main>
  );
}
