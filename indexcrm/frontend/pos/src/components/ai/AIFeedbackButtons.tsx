"use client";

import { ThumbsDown, ThumbsUp } from "lucide-react";

type FeedbackStatus = {
  state: "idle" | "saving" | "saved" | "error";
  message?: string;
};

type AIFeedbackButtonsProps = {
  disabled?: boolean;
  status?: FeedbackStatus;
  onFeedback: (rating: "good" | "bad") => void;
};

export function AIFeedbackButtons({
  disabled = false,
  status = { state: "idle" },
  onFeedback,
}: AIFeedbackButtonsProps) {
  const isSaving = status.state === "saving";
  return (
    <div className="mt-3 flex flex-wrap items-center gap-2">
      <button
        type="button"
        disabled={disabled || isSaving}
        onClick={() => onFeedback("good")}
        className="inline-flex h-8 items-center gap-2 rounded border border-emerald-200 bg-emerald-50 px-3 text-xs font-black text-emerald-800 hover:bg-emerald-100 disabled:cursor-not-allowed disabled:opacity-60"
      >
        <ThumbsUp aria-hidden="true" className="h-4 w-4" />
        Foydali
      </button>
      <button
        type="button"
        disabled={disabled || isSaving}
        onClick={() => onFeedback("bad")}
        className="inline-flex h-8 items-center gap-2 rounded border border-rose-200 bg-rose-50 px-3 text-xs font-black text-rose-800 hover:bg-rose-100 disabled:cursor-not-allowed disabled:opacity-60"
      >
        <ThumbsDown aria-hidden="true" className="h-4 w-4" />
        Foydasiz
      </button>
      {status.message ? (
        <span
          className={`text-xs font-bold ${
            status.state === "error" ? "text-rose-700" : "text-emerald-700"
          }`}
        >
          {status.message}
        </span>
      ) : null}
    </div>
  );
}
