"use client";

import Link from "next/link";
import { ArrowBigUp, ArrowBigDown, MessageCircle, Bookmark, Share2, MoreHorizontal } from "lucide-react";
import type { ThesisPost } from "@/types/thesis";

interface ThesisPostCardProps {
  post: ThesisPost;
}

const sentimentColors: Record<string, string> = {
  Bullish: "text-emerald-600",
  Bearish: "text-rose-600",
  Neutral: "text-gray-600",
};

export function ThesisPostCard({ post }: ThesisPostCardProps) {
  const sentimentClass =
    sentimentColors[post.sentiment] ?? sentimentColors.Neutral;

  return (
    <article className="flex gap-4 py-4 border-b border-primary/30 last:border-0 transition-colors hover:opacity-90">
      {/* Vote rail */}
      <div className="flex flex-col items-center gap-1 text-gray-500">
        <button
          type="button"
          aria-label="Upvote thesis"
          className="rounded-full p-1 hover:bg-gray-100 hover:text-primary focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
        >
          <ArrowBigUp className="h-5 w-5" />
        </button>
        <div className="text-sm font-semibold text-gray-800 min-w-[2.5rem] text-center">
          {post.score}
        </div>
        <button
          type="button"
          aria-label="Downvote thesis"
          className="rounded-full p-1 hover:bg-gray-100 hover:text-rose-500 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
        >
          <ArrowBigDown className="h-5 w-5" />
        </button>
        <div className="mt-2 flex items-center gap-1 text-xs text-gray-500">
          <MessageCircle className="h-3.5 w-3.5" />
          <span>{post.commentsCount}</span>
        </div>
      </div>

      {/* Main content */}
      <div className="flex-1 space-y-2">
        <div className="flex flex-wrap items-center gap-2 text-xs text-gray-500">
          <span className="font-medium text-gray-800">{post.author.username}</span>
          <span>•</span>
          <span>{post.author.badge}</span>
          <span>•</span>
          <span>{post.createdAt}</span>
          <span>•</span>
          <span>{post.readingTime}</span>
        </div>

        <Link
          href={`/research/ongoing-thesis/${post.id}`}
          className="group block"
        >
          <h2 className="text-lg font-semibold text-gray-900 group-hover:text-primary">
            {post.title}
          </h2>
          <p className="mt-1 text-sm text-gray-600 line-clamp-2">
            {post.excerpt}
          </p>
        </Link>

        <div className="flex flex-wrap items-center gap-x-2 gap-y-1 mt-2 text-xs text-gray-500">
          <span className={`font-medium ${sentimentClass}`}>{post.sentiment}</span>
          {post.tags.map((tag) => (
            <span key={tag}>{tag}</span>
          ))}
          {post.tickers.map((ticker) => (
            <span key={ticker} className="font-mono text-gray-600">{ticker}</span>
          ))}
        </div>
      </div>

      {/* Actions */}
      <div className="flex flex-col items-end justify-between gap-2 text-gray-500">
        <div className="flex items-center gap-1">
          <button
            type="button"
            aria-label="Bookmark thesis"
            className="rounded-full p-1.5 hover:bg-gray-100 hover:text-primary focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
          >
            <Bookmark className="h-4 w-4" />
          </button>
          <button
            type="button"
            aria-label="Share thesis"
            className="rounded-full p-1.5 hover:bg-gray-100 hover:text-primary focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
          >
            <Share2 className="h-4 w-4" />
          </button>
          <button
            type="button"
            aria-label="More actions"
            className="rounded-full p-1.5 hover:bg-gray-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
          >
            <MoreHorizontal className="h-4 w-4" />
          </button>
        </div>
      </div>
    </article>
  );
}

