"use client";

import { ArrowBigUp, ArrowBigDown, MessageCircle } from "lucide-react";
import type { Comment } from "@/types/thesis";

interface CommentThreadProps {
  comments: Comment[];
}

export function CommentThread({ comments }: CommentThreadProps) {
  const byParent: Record<string, Comment[]> = {};

  comments.forEach((c) => {
    const parentKey = c.parentId ?? "root";
    if (!byParent[parentKey]) byParent[parentKey] = [];
    byParent[parentKey].push(c);
  });

  const renderComments = (parentId: string | null, depth = 0) => {
    const key = parentId ?? "root";
    const list = byParent[key] ?? [];
    return list.map((comment) => (
      <div key={comment.id} className="mt-4">
        <div className="flex gap-3">
          {/* Vote rail */}
          <div className="flex flex-col items-center gap-1 text-gray-500 mt-1">
            <button
              type="button"
              aria-label="Upvote comment"
              className="rounded-full p-0.5 hover:bg-gray-100 hover:text-primary focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
            >
              <ArrowBigUp className="h-3.5 w-3.5" />
            </button>
            <span className="text-[11px] font-semibold text-gray-800 min-w-[1.5rem] text-center">
              {comment.score}
            </span>
            <button
              type="button"
              aria-label="Downvote comment"
              className="rounded-full p-0.5 hover:bg-gray-100 hover:text-rose-500 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
            >
              <ArrowBigDown className="h-3.5 w-3.5" />
            </button>
          </div>

          {/* Body */}
          <div className="flex-1">
            <div className="flex flex-wrap items-center gap-2 text-[11px] text-gray-500">
              <span className="font-medium text-gray-800">
                {comment.author.username}
              </span>
              <span>•</span>
              <span>{comment.author.badge}</span>
              <span>•</span>
              <span>{comment.createdAt}</span>
            </div>
            <p className="mt-1 text-sm text-gray-800 leading-relaxed">
              {comment.body}
            </p>
            <div className="mt-1 flex items-center gap-4 text-xs text-gray-500">
              <button
                type="button"
                className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 hover:bg-gray-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
              >
                <MessageCircle className="h-3 w-3" />
                <span>Reply</span>
              </button>
            </div>
          </div>
        </div>

        {/* Children */}
        <div
          className="ml-6 border-l border-gray-200 pl-4"
          style={{ marginLeft: depth > 0 ? 24 : 16 }}
        >
          {renderComments(comment.id, depth + 1)}
        </div>
      </div>
    ));
  };

  return <div>{renderComments(null)}</div>;
}

