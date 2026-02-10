"use client";

import Link from "next/link";
import Section from "@/components/Section";
import { CommentThread } from "@/components/CommentThread";
import type { ThesisPost, Comment } from "@/types/thesis";
import {
  ArrowLeft,
  Calendar,
  Clock3,
  Download,
  Share2,
  Bookmark,
  Printer,
} from "lucide-react";

const mockPost: ThesisPost = {
  id: "us-equity-gamma-rotation",
  title: "US Equity Gamma Rotation Around CPI and FOMC Windows",
  excerpt: "",
  body: "",
  author: {
    id: "1",
    username: "gamma_structurer",
    badge: "Contributor",
  },
  createdAt: "Jan 24, 2026",
  readingTime: "12 min read",
  tags: ["Macro", "Options", "US Equities"],
  tickers: ["SPY", "QQQ"],
  sentiment: "Bullish",
  score: 128,
  commentsCount: 24,
};

const mockComments: Comment[] = [
  {
    id: "c1",
    postId: mockPost.id,
    parentId: null,
    author: {
      id: "2",
      username: "delta_neutral",
      badge: "Analyst",
    },
    body: "The framing around liquidity windows is very helpful. One additional angle is to look at dealer gamma by strike bucket rather than just aggregate.\n\nThat often shows where intraday pinning pressure is likely to emerge.",
    createdAt: "4 hours ago",
    score: 42,
  },
  {
    id: "c2",
    postId: mockPost.id,
    parentId: "c1",
    author: {
      id: "3",
      username: "macro_micro",
      badge: "Contributor",
    },
    body: "Agree. Also worth overlaying this with realized gap risk across prior CPI releases – the tails really matter for sizing.",
    createdAt: "3 hours ago",
    score: 21,
  },
  {
    id: "c3",
    postId: mockPost.id,
    parentId: null,
    author: {
      id: "4",
      username: "vol_surface",
      badge: "Verified",
    },
    body: "Would be great to see some empirical plots on how skew and term structure behave when realized macro surprise is large but directionally ambiguous.",
    createdAt: "1 hour ago",
    score: 35,
  },
];

export default function OngoingThesisDetailPage({
  params,
}: {
  params: { id: string };
}) {
  const post = mockPost; // In a real app, you'd look up by id

  return (
    <main className="min-h-screen">
      <Section className="pt-8">
        <div className="mx-auto max-w-6xl">
          {/* Back link */}
          <div className="mb-4">
            <Link
              href="/research/ongoing-thesis"
              className="inline-flex items-center gap-2 text-xs font-medium text-gray-600 hover:text-primary"
            >
              <ArrowLeft className="h-3.5 w-3.5" />
              <span>Back to Ongoing Thesis</span>
            </Link>
          </div>

          {/* Header */}
          <header className="mb-6 space-y-4">
            <div className="text-xs font-medium uppercase tracking-wide text-primary">
              Ongoing Thesis
            </div>
            <h1 className="text-3xl sm:text-4xl font-semibold text-gray-900 leading-snug">
              {post.title}
            </h1>
            <div className="flex flex-wrap items-center gap-3 text-xs text-gray-600">
              <span className="font-medium text-gray-800">
                {post.author.username}
              </span>
              <span>•</span>
              <span>{post.author.badge}</span>
              <span>•</span>
              <span className="inline-flex items-center gap-1">
                <Calendar className="h-3.5 w-3.5 text-gray-400" />
                {post.createdAt}
              </span>
              <span>•</span>
              <span className="inline-flex items-center gap-1">
                <Clock3 className="h-3.5 w-3.5 text-gray-400" />
                {post.readingTime}
              </span>

              {/* Tags */}
              {post.tags.map((tag) => (
                <span
                  key={tag}
                  className="inline-flex items-center rounded-full bg-gray-100 px-2 py-0.5 text-[11px] font-medium text-gray-700"
                >
                  {tag}
                </span>
              ))}

              {/* Tickers */}
              {post.tickers.map((ticker) => (
                <span
                  key={ticker}
                  className="inline-flex items-center rounded-full border border-dashed border-gray-300 px-2 py-0.5 text-[11px] font-mono text-gray-800"
                >
                  {ticker}
                </span>
              ))}

              {/* Sentiment */}
              <span className="inline-flex items-center rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-0.5 text-[11px] font-medium text-emerald-700">
                {post.sentiment}
              </span>
            </div>

            {/* Actions */}
            <div className="flex flex-wrap items-center gap-2 text-xs text-gray-600">
              <ActionButton label="Download">
                <Download className="h-3.5 w-3.5" />
              </ActionButton>
              <ActionButton label="Share">
                <Share2 className="h-3.5 w-3.5" />
              </ActionButton>
              <ActionButton label="Bookmark">
                <Bookmark className="h-3.5 w-3.5" />
              </ActionButton>
              <ActionButton label="Print">
                <Printer className="h-3.5 w-3.5" />
              </ActionButton>
            </div>
          </header>

          <hr className="mb-6 border-gray-200" />

          {/* Body */}
          <article className="prose prose-gray max-w-none prose-headings:font-semibold prose-h2:text-lg prose-p:text-gray-700 prose-p:leading-relaxed">
            <section>
              <h2>Summary</h2>
              <p>
                This thesis outlines a practical way to think about US equity
                gamma exposure around key macro dates, focusing on how liquidity
                conditions, volatility risk premia, and systematic hedging flows
                interact. The core idea is that option markets often reprice risk
                in a stepwise fashion around CPI and FOMC windows, creating
                repeatable patterns in intraday volatility and gap risk.
              </p>
            </section>

            <section>
              <h2>Key Claims</h2>
              <ul>
                <li>
                  The distribution of intraday returns is meaningfully different
                  in the 1–2 sessions before and after major macro prints.
                </li>
                <li>
                  Dealer gamma positioning amplifies or dampens these dynamics,
                  especially when open interest is concentrated in short-dated
                  strikes near the money.
                </li>
                <li>
                  A systematic rotation of gamma exposure around these windows
                  can improve risk-adjusted returns relative to static exposure.
                </li>
              </ul>
            </section>

            <section>
              <h2>Assumptions</h2>
              <ul>
                <li>
                  Market participants continue to use options as the primary tool
                  for hedging macro event risk.
                </li>
                <li>
                  Structural demand for short-dated optionality remains elevated
                  due to macro uncertainty and systematic strategies.
                </li>
                <li>
                  Transaction costs and slippage can be managed via disciplined
                  execution windows and sizing rules.
                </li>
              </ul>
            </section>

            <section>
              <h2>Scenario Analysis</h2>
              <p>
                The framework distinguishes between three broad environments:
                benign macro surprises, one-sided shocks, and regime-changing
                prints. In each case, the thesis specifies how much gamma to
                carry, where along the curve to position, and how quickly to
                mean-revert exposure once realized volatility normalizes.
              </p>
            </section>

            <section>
              <h2>Risks &amp; Disconfirming Evidence</h2>
              <p>
                The main risk to this thesis is a structural shift in how macro
                risk is expressed – for example, if flows migrate from options to
                structured notes or if regulatory changes alter dealer balance
                sheet constraints. A second risk is that crowding erodes the
                premium associated with these patterns, making realized outcomes
                more path dependent.
              </p>
            </section>

            <section>
              <h2>What Would Change My Mind?</h2>
              <p>
                Sustained evidence that realized volatility around key macro dates
                no longer differs meaningfully from surrounding periods would
                call this thesis into question. So would a structural decline in
                short-dated open interest or a regime where macro outcomes are
                both well-telegraphed and quickly absorbed without dislocations.
              </p>
            </section>
          </article>

          {/* Comments */}
          <section className="mt-10">
            <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
              <h2 className="text-sm font-semibold text-gray-900">
                Discussion ({mockPost.commentsCount})
              </h2>
              <div className="inline-flex items-center gap-1 rounded-full bg-gray-100 px-2 py-1 text-[11px] text-gray-700">
                <span className="font-medium">Sort by:</span>
                <button
                  type="button"
                  className="rounded-full bg-white px-2 py-0.5 text-[11px] font-medium text-gray-800 shadow-sm"
                >
                  Best
                </button>
                <button
                  type="button"
                  className="rounded-full px-2 py-0.5 text-[11px] text-gray-600 hover:bg-white"
                >
                  New
                </button>
              </div>
            </div>

            {/* Comment box */}
            <div className="mb-4 rounded-xl border border-gray-200 bg-white/80 p-3 text-xs text-gray-600">
              <textarea
                placeholder="Add your perspective to the discussion (UI only)..."
                rows={3}
                className="w-full rounded-md border border-gray-200 bg-white px-2 py-1.5 text-xs text-gray-900 placeholder:text-gray-400 focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
              />
              <div className="mt-2 flex items-center justify-end gap-2">
                <button
                  type="button"
                  className="rounded-full px-3 py-1 text-[11px] font-medium text-gray-600 hover:bg-gray-100"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  className="rounded-full bg-primary px-3 py-1 text-[11px] font-semibold text-white hover:bg-primary-dark"
                >
                  Comment
                </button>
              </div>
            </div>

            <CommentThread comments={mockComments} />
          </section>
        </div>
      </Section>
    </main>
  );
}

function ActionButton({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      aria-label={label}
      className="inline-flex items-center gap-1 rounded-full border border-gray-200 bg-white px-3 py-1 text-[11px] font-medium text-gray-700 hover:border-primary hover:text-primary focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
    >
      {children}
      <span className="hidden sm:inline">{label}</span>
    </button>
  );
}

