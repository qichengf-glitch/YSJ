"use client";

import Link from "next/link";
import Section from "@/components/Section";
import { researchPapers } from "@/data/research";

export default function TheoreticalResearchIndexPage() {
  return (
    <main className="min-h-screen">
      <Section className="pt-3 pb-10 sm:pt-4 sm:pb-12">
        <div className="mx-auto max-w-4xl">
          {/* Header */}
          <header className="space-y-3 mb-10">
            <nav
              className="text-sm text-gray-500"
              aria-label="Breadcrumb"
            >
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

            <h1 className="text-3xl sm:text-4xl font-semibold text-gray-900">
              Theoretical Research
            </h1>
            <p className="text-base text-gray-600 max-w-3xl">
              Conceptual work that underpins YSJ Lab&apos;s systematic strategies –
              focusing on market microstructure, liquidity regimes, risk premia,
              and cross-asset interactions.
            </p>
          </header>

          {/* Article list */}
          <div className="space-y-12">
            {researchPapers.map((paper) => (
              <Link
                key={paper.slug}
                href={`/research/${paper.slug}`}
                className="block group border-b border-gray-100 pb-12 last:border-0 last:pb-0"
              >
                <div className="flex items-baseline gap-3 mb-1">
                  <span className="text-base text-primary font-medium">
                    {paper.category}
                  </span>
                  <span className="flex-1 h-px bg-primary/20 min-w-[2rem]" />
                </div>
                <h2 className="font-playfair text-2xl sm:text-3xl font-semibold text-gray-900 group-hover:text-primary transition-colors mt-2">
                  {paper.title}
                </h2>
                <p className="text-base text-gray-500 italic mt-1">
                  {paper.publishedAt ?? paper.year}
                </p>
                <p className="text-base text-gray-600 leading-relaxed mt-3">
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
