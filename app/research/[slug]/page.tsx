"use client";

import Link from "next/link";
import { Calendar, Clock3, Download, Printer, Share2, Bookmark } from "lucide-react";
import Section from "@/components/Section";
import { researchPapers } from "@/data/research";

type ArticleMeta = {
  category: string;
  title: string;
  subtitle: string;
  publishedAt: string;
  author: string;
  readingTime: string;
};

const papersBySlug = Object.fromEntries(
  researchPapers.map((p) => [p.slug, p])
);

const articlesBySlug: Record<string, ArticleMeta> = {
  "systematic-single-stock-gamma-exposure": {
    category: "Ongoing Thesis",
    title: "Systematic Approaches to Single-Stock Gamma Exposure",
    subtitle:
      "A research agenda for building disciplined exposure to single-stock gamma while managing inventory, liquidity, and risk constraints.",
    publishedAt: "Nov 15, 2025",
    author: "YSJ Lab Derivatives Research",
    readingTime: "16 min read",
  },
  "cross-asset-signals-macro-event-windows": {
    category: "Market Data & Our Picks",
    title: "Cross-Asset Signals Around Macro Event Windows",
    subtitle:
      "An exploratory framework for using cross-asset market data to structure views around key macro and policy announcements.",
    publishedAt: "Oct 3, 2025",
    author: "YSJ Lab Macro & Systematic Team",
    readingTime: "14 min read",
  },
};

const relatedResearch = [
  {
    category: "Theoretical Research",
    title: "Risk Premia Across Volatility Regimes",
    date: "Dec 2025",
  },
  {
    category: "Ongoing Thesis",
    title: "Systematic Approaches to Single-Stock Gamma Exposure",
    date: "Nov 2025",
  },
  {
    category: "Market Data & Our Picks",
    title: "Cross-Asset Signals Around Macro Event Windows",
    date: "Oct 2025",
  },
];

function PDFPaperPage({
  paper,
}: {
  paper: (typeof researchPapers)[number];
}) {
  const related = researchPapers.filter((p) => p.slug !== paper.slug).slice(0, 4);
  return (
    <main className="min-h-screen pt-10 pb-24">
      <Section className="pt-6">
        <div className="mx-auto grid max-w-6xl grid-cols-1 gap-12 lg:grid-cols-[1fr_280px]">
          {/* Main content */}
          <article>
            <header className="mb-8">
              <div className="text-sm text-gray-600 mb-2">
                {paper.category}
              </div>
              <h1 className="font-playfair text-3xl sm:text-4xl lg:text-[2.5rem] font-semibold text-gray-900 leading-tight mb-4">
                {paper.title}
              </h1>
              <p className="text-sm text-gray-600">
                <span className="italic">{paper.publishedAt ?? paper.year}</span>
                {" – "}
                <span className="text-primary">{paper.authors}</span>
              </p>
            </header>

            <hr className="border-t-2 border-primary/30 mb-8" />

            <div>
              <p className="text-base sm:text-lg text-gray-800 leading-relaxed">
                {paper.summary}
              </p>
              <p className="text-sm text-gray-500 mt-6">
                Download the full paper to read the complete content, exhibits, and analysis.
              </p>
            </div>
          </article>

          {/* Sidebar - AQR style */}
          <aside className="lg:pl-8">
            <div className="sticky top-24 space-y-8">
              {/* Action icons */}
              <div className="flex items-center gap-4 text-gray-400">
                <button type="button" aria-label="Print" className="p-1.5 hover:text-gray-600 transition-colors">
                  <Printer className="h-4 w-4" />
                </button>
                <button type="button" aria-label="Save" className="p-1.5 hover:text-gray-600 transition-colors">
                  <Bookmark className="h-4 w-4" />
                </button>
                <button type="button" aria-label="Share" className="p-1.5 hover:text-gray-600 transition-colors">
                  <Share2 className="h-4 w-4" />
                </button>
              </div>

              {/* Download button - outline style */}
              <a
                href={paper.pdfPath}
                download
                className="flex items-center justify-center gap-2 w-full py-3 px-4 rounded border-2 border-primary text-primary font-medium text-sm hover:bg-primary/5 transition-colors"
              >
                <Download className="h-4 w-4" />
                Download
              </a>

              {/* Related Thinking */}
              <div>
                <h2 className="text-sm font-semibold text-gray-900 mb-4">
                  Related Thinking
                </h2>
                <div className="space-y-4">
                  {related.map((p) => (
                    <Link
                      key={p.slug}
                      href={`/research/${p.slug}`}
                      className="block py-2 border-b border-gray-100 last:border-0 hover:text-primary transition-colors"
                    >
                      <div className="text-sm font-medium text-gray-900 leading-snug group-hover:text-primary">
                        {p.title}
                      </div>
                      <div className="text-xs text-gray-500 mt-0.5">
                        {p.category} – {p.publishedAt ?? p.year}
                      </div>
                    </Link>
                  ))}
                </div>
              </div>

              <Link
                href="/research/theoretical-research"
                className="block text-sm text-primary hover:underline pt-2"
              >
                ← Back to Theoretical Research
              </Link>
            </div>
          </aside>
        </div>
      </Section>
    </main>
  );
}

export default function ResearchArticleDetailPage({
  params,
}: {
  params: { slug: string };
}) {
  const paper = papersBySlug[params.slug];
  const article = articlesBySlug[params.slug];

  if (paper) {
    return <PDFPaperPage paper={paper} />;
  }
  if (!article) {
    return (
      <main className="min-h-screen pt-16">
        <Section className="pt-8">
          <h1 className="text-2xl font-semibold text-gray-900">Paper not found</h1>
          <Link href="/research" className="text-primary underline mt-4 inline-block">
            Back to Research
          </Link>
        </Section>
      </main>
    );
  }
  return (
    <main className="min-h-screen pt-10 pb-24">
      <Section className="pt-6">
        <div className="mx-auto grid max-w-6xl grid-cols-1 gap-10 lg:grid-cols-[minmax(0,3fr)_minmax(260px,1fr)]">
          {/* Main content */}
          <article className="space-y-8">
            {/* Header */}
            <header className="space-y-6">
              <div className="text-sm font-medium uppercase tracking-wide text-primary">
                {article.category}
              </div>

              <h1 className="text-3xl sm:text-4xl lg:text-[2.75rem] font-semibold text-gray-900 leading-snug">
                {article.title}
              </h1>

              <p className="text-base sm:text-lg text-gray-600 leading-relaxed max-w-3xl">
                {article.subtitle}
              </p>

              {/* Meta + actions */}
              <div className="flex flex-col gap-4 border-t border-gray-200 pt-4 sm:flex-row sm:items-center sm:justify-between">
                <div className="flex flex-wrap items-center gap-4 text-sm text-gray-600">
                  <div className="flex items-center gap-2">
                    <Calendar className="h-4 w-4 text-gray-400" />
                    <span>{article.publishedAt}</span>
                  </div>
                  <div className="h-4 w-px bg-gray-200 hidden sm:block" />
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-gray-800">
                      {article.author}
                    </span>
                  </div>
                  <div className="h-4 w-px bg-gray-200 hidden sm:block" />
                  <div className="flex items-center gap-2">
                    <Clock3 className="h-4 w-4 text-gray-400" />
                    <span>{article.readingTime}</span>
                  </div>
                </div>

                <div className="flex flex-wrap items-center gap-2">
                  <IconButton label="Download PDF">
                    <Download className="h-4 w-4" />
                  </IconButton>
                  <IconButton label="Share">
                    <Share2 className="h-4 w-4" />
                  </IconButton>
                  <IconButton label="Save">
                    <Bookmark className="h-4 w-4" />
                  </IconButton>
                  <IconButton label="Print">
                    <Printer className="h-4 w-4" />
                  </IconButton>
                </div>
              </div>
            </header>

            {/* Divider */}
            <hr className="border-t border-gray-200" />

            {/* Body */}
            <div className="prose prose-gray max-w-none prose-headings:font-semibold prose-h2:text-xl prose-h2:mt-10 prose-h2:mb-4 prose-p:text-gray-700 prose-p:leading-relaxed">
              <SectionBlock
                title="Introduction"
                paragraphs={[
                  "This research note outlines a conceptual framework for thinking about systematic options strategies in the context of changing liquidity regimes. While the focus is theoretical, the objective is highly practical: to help investors map observable market conditions into a structured view of when option-based risk premia are more or less attractive.",
                  "Rather than proposing a single backtested strategy, we emphasize the building blocks that underpin robust option frameworks: volatility surfaces, term structures, order-book depth, and the behavior of marginal liquidity providers. The ideas here are intended as a foundation for further empirical work within YSJ Lab’ research pipeline.",
                ]}
              />

              <SectionBlock
                title="Theoretical Framework"
                paragraphs={[
                  "We organize the problem along two dimensions: the state of market liquidity and the nature of volatility supply and demand. Conceptually, investors can think in terms of a grid where each cell corresponds to a distinct regime, with its own expectations for option carry, skew behavior, and gap risk.",
                ]}
              >
                <ul className="list-disc pl-5 space-y-1 text-gray-700">
                  <li>
                    <span className="font-medium text-gray-900">
                      Liquidity regime:
                    </span>{" "}
                    calm, stressed, or impaired, defined by depth-of-book metrics,
                    bid-ask spreads, and realized impact of larger trades.
                  </li>
                  <li>
                    <span className="font-medium text-gray-900">
                      Volatility regime:
                    </span>{" "}
                    low, normal, or elevated, considered both in absolute terms
                    and relative to macro and event risk.
                  </li>
                  <li>
                    <span className="font-medium text-gray-900">
                      Positioning & flows:
                    </span>{" "}
                    evidence of structural vol sellers, hedging activity, or flow
                    constraints in options and underlying markets.
                  </li>
                </ul>
              </SectionBlock>

              <SectionBlock
                title="Key Assumptions"
                paragraphs={[
                  "Any systematic option strategy implicitly embeds a set of assumptions about how markets clear risk over time. Making these assumptions explicit is critical for risk management and for understanding when a strategy is likely to underperform.",
                ]}
              >
                <ul className="list-disc pl-5 space-y-1 text-gray-700">
                  <li>
                    Transaction costs and market impact can be modeled as a
                    stable function of liquidity conditions, rather than as a
                    constant.
                  </li>
                  <li>
                    Investors are compensated for warehousing tail risk over long
                    horizons, but this compensation is time-varying and
                    sensitive to macro uncertainty.
                  </li>
                  <li>
                    Volatility surfaces reflect a mixture of structural demand
                    (hedging, regulation, product design) and tactical flows,
                    which may temporarily distort prices away from fundamental
                    risk premia.
                  </li>
                  <li>
                    Position limits, collateral terms, and margin policies
                    create non-linear constraints that matter most during stress
                    episodes.
                  </li>
                </ul>
              </SectionBlock>

              <SectionBlock
                title="Implications for Systematic Option Strategies"
                paragraphs={[
                  "Within this framework, systematic strategies can be thought of as rules that map observable state variables into position sizes, strikes, and maturities. The same rule set may behave very differently across liquidity regimes, which argues for explicit regime-awareness rather than static calibration.",
                  "For example, strategies that lean into short volatility premia may warrant tighter risk limits when liquidity is impaired and cross-asset correlations are elevated. Conversely, periods of normalized liquidity and elevated implied volatility relative to realized outcomes may offer more attractive opportunities for deploying risk.",
                ]}
              />

              <SectionBlock
                title="Next Steps in the YSJ Lab Research Program"
                paragraphs={[
                  "This note is part of a broader YSJ Lab research stream focused on building a disciplined toolkit for options-based strategies. Subsequent work will introduce empirical evidence, simulation studies, and implementation details across US index and single-stock options.",
                  "Future publications will also examine how these concepts extend to other asset classes and how investors can integrate systematic options with existing discretionary or fundamental processes.",
                ]}
              />
            </div>
          </article>

          {/* Sidebar */}
          <aside className="space-y-6 lg:pl-4 lg:border-l lg:border-gray-200">
            <div className="sticky top-24 space-y-4">
              <h2 className="text-sm font-semibold tracking-wide text-gray-900 uppercase">
                Related Research
              </h2>
              <div className="space-y-4">
                {relatedResearch.map((item, idx) => (
                  <div
                    key={idx}
                    className="rounded-lg border border-gray-200 bg-white/70 p-4 hover:border-primary transition-colors cursor-pointer"
                  >
                    <div className="text-xs font-medium uppercase tracking-wide text-primary mb-1">
                      {item.category}
                    </div>
                    <div className="text-sm font-semibold text-gray-900 leading-snug mb-1">
                      {item.title}
                    </div>
                    <div className="text-xs text-gray-500">{item.date}</div>
                  </div>
                ))}
              </div>
            </div>

            {/* Footer CTA in sidebar on large screens */}
            <div className="hidden lg:block pt-4 border-t border-gray-200 mt-4">
              <p className="text-sm text-gray-700 mb-3 font-medium">
                Stay ahead with YSJ Lab research.
              </p>
              <div className="flex flex-col gap-2">
                <button className="inline-flex items-center justify-center rounded-md border border-primary bg-primary px-3 py-2 text-xs font-medium text-white shadow-sm transition-colors hover:bg-primary-dark">
                  Subscribe to Research Updates
                </button>
                <button className="inline-flex items-center justify-center rounded-md border border-gray-300 px-3 py-2 text-xs font-medium text-gray-700 hover:bg-gray-50">
                  Back to Research Library
                </button>
              </div>
            </div>
          </aside>
        </div>

        {/* Footer CTA for mobile / tablet */}
        <div className="mt-12 border-t border-gray-200 pt-6 lg:hidden">
          <div className="flex flex-col gap-3">
            <button className="inline-flex items-center justify-center rounded-md border border-primary bg-primary px-4 py-2.5 text-sm font-medium text-white shadow-sm transition-colors hover:bg-primary-dark">
              Subscribe to Research Updates
            </button>
            <button className="inline-flex items-center justify-center rounded-md border border-gray-300 px-4 py-2.5 text-sm font-medium text-gray-700 hover:bg-gray-50">
              Back to Research Library
            </button>
          </div>
        </div>
      </Section>
    </main>
  );
}

interface SectionBlockProps {
  title: string;
  paragraphs: string[];
  children?: React.ReactNode;
}

function SectionBlock({ title, paragraphs, children }: SectionBlockProps) {
  return (
    <section>
      <h2 className="text-xl font-semibold text-gray-900 mb-3">{title}</h2>
      <div className="space-y-4">
        {paragraphs.map((p, idx) => (
          <p key={idx} className="text-gray-700 leading-relaxed text-[0.97rem]">
            {p}
          </p>
        ))}
      </div>
      {children && <div className="mt-4">{children}</div>}
    </section>
  );
}

interface IconButtonProps {
  label: string;
  children: React.ReactNode;
}

function IconButton({ label, children }: IconButtonProps) {
  return (
    <button
      type="button"
      className="inline-flex items-center gap-2 rounded-full border border-gray-200 bg-white px-3 py-1.5 text-xs font-medium text-gray-700 shadow-sm hover:border-primary hover:text-primary focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
      aria-label={label}
    >
      {children}
      <span className="hidden sm:inline">{label}</span>
    </button>
  );
}

