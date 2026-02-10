"use client";

import { useState } from "react";
import { FileText, Flashlight, Link2, BarChart2, X } from "lucide-react";

type ComposerMode = "Thesis" | "Quick Take" | "Link" | "Chart";

export function ThesisComposer() {
  const [isExpanded, setIsExpanded] = useState(false);
  const [mode, setMode] = useState<ComposerMode>("Thesis");

  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [tags, setTags] = useState("");
  const [tickers, setTickers] = useState("");

  const handlePublish = () => {
    // UI only – in real app this would call an API
    console.log("Publishing thesis", {
      mode,
      title,
      body,
      tags,
      tickers,
    });
    setIsExpanded(false);
    setTitle("");
    setBody("");
    setTags("");
    setTickers("");
  };

  const openWithMode = (newMode: ComposerMode) => {
    setMode(newMode);
    setIsExpanded(true);
  };

  return (
    <div className="rounded-lg border border-gray-200/50 bg-white/30 p-4">
      {/* Compact header */}
      {!isExpanded && (
        <div className="flex flex-col gap-3">
          <button
            type="button"
            className="w-full rounded-full border border-gray-200 bg-gray-50 px-4 py-2 text-left text-sm text-gray-500 hover:border-primary/60 hover:bg-white focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
            onClick={() => openWithMode("Thesis")}
          >
            What&apos;s your thesis?
          </button>
          <div className="flex flex-wrap items-center gap-2 text-xs text-gray-600">
            <ComposerModeButton
              icon={<FileText className="h-3.5 w-3.5" />}
              label="Thesis"
              onClick={() => openWithMode("Thesis")}
            />
            <ComposerModeButton
              icon={<Flashlight className="h-3.5 w-3.5" />}
              label="Quick Take"
              onClick={() => openWithMode("Quick Take")}
            />
            <ComposerModeButton
              icon={<Link2 className="h-3.5 w-3.5" />}
              label="Link"
              onClick={() => openWithMode("Link")}
            />
            <ComposerModeButton
              icon={<BarChart2 className="h-3.5 w-3.5" />}
              label="Chart"
              onClick={() => openWithMode("Chart")}
            />
          </div>
        </div>
      )}

      {/* Expanded composer */}
      {isExpanded && (
        <div className="space-y-4">
          <div className="flex items-center justify-between text-xs text-gray-600">
            <div className="inline-flex items-center gap-2 rounded-full bg-gray-100 px-3 py-1 font-medium text-gray-800">
              <span>{mode}</span>
            </div>
            <button
              type="button"
              onClick={() => setIsExpanded(false)}
              className="inline-flex items-center gap-1 rounded-full px-2 py-1 text-gray-500 hover:bg-gray-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
            >
              <X className="h-3 w-3" />
              <span>Close</span>
            </button>
          </div>

          <input
            type="text"
            placeholder="Title"
            className="w-full rounded-md border border-gray-200 bg-white px-3 py-2 text-sm text-gray-900 placeholder:text-gray-400 focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
          />

          <textarea
            placeholder={
              mode === "Quick Take"
                ? "Share a concise view or reaction..."
                : "Outline your thesis, key claims, and what would change your mind..."
            }
            rows={6}
            className="w-full rounded-md border border-gray-200 bg-white px-3 py-2 text-sm text-gray-900 placeholder:text-gray-400 focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
            value={body}
            onChange={(e) => setBody(e.target.value)}
          />

          <div className="flex flex-col gap-2 text-xs sm:flex-row sm:gap-4">
            <div className="flex-1">
              <label className="mb-1 block text-gray-600">
                Tags (comma separated)
              </label>
              <input
                type="text"
                placeholder="Macro, Tech, Options"
                className="w-full rounded-md border border-gray-200 bg-white px-3 py-2 text-xs text-gray-900 placeholder:text-gray-400 focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                value={tags}
                onChange={(e) => setTags(e.target.value)}
              />
            </div>
            <div className="flex-1">
              <label className="mb-1 block text-gray-600">
                Tickers (comma separated)
              </label>
              <input
                type="text"
                placeholder="AAPL, SPY, BTC"
                className="w-full rounded-md border border-gray-200 bg-white px-3 py-2 text-xs text-gray-900 placeholder:text-gray-400 focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                value={tickers}
                onChange={(e) => setTickers(e.target.value)}
              />
            </div>
          </div>

          <div className="flex items-center justify-end gap-2">
            <button
              type="button"
              className="rounded-full px-3 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
              onClick={() => setIsExpanded(false)}
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handlePublish}
              className="rounded-full bg-primary px-4 py-1.5 text-xs font-semibold text-white shadow-sm hover:bg-primary-dark focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
            >
              Publish
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

interface ComposerModeButtonProps {
  icon: React.ReactNode;
  label: string;
  onClick: () => void;
}

function ComposerModeButton({ icon, label, onClick }: ComposerModeButtonProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="inline-flex items-center gap-1 rounded-full border border-gray-200 bg-white px-3 py-1 text-[11px] font-medium text-gray-700 hover:bg-gray-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
    >
      {icon}
      <span>{label}</span>
    </button>
  );
}

