"use client";

import { Bot, UserRound } from "lucide-react";

import { AIFeedbackButtons } from "@/components/ai/AIFeedbackButtons";
import { AIChatMessage } from "@/services/api/types";

type FeedbackStatus = {
  state: "idle" | "saving" | "saved" | "error";
  message?: string;
};

type AIMessageBubbleProps = {
  message: AIChatMessage;
  showMetadata?: boolean;
  feedbackStatus?: FeedbackStatus;
  onFeedback?: (messageId: string, rating: "good" | "bad") => void;
};

function formatConfidence(value?: number) {
  if (typeof value !== "number") {
    return "";
  }
  return `${Math.round(value * 100)}%`;
}

export function AIMessageBubble({
  message,
  showMetadata = false,
  feedbackStatus,
  onFeedback,
}: AIMessageBubbleProps) {
  const isUser = message.role === "user";
  const label = isUser ? "Siz" : "AI yordamchi";
  const Icon = isUser ? UserRound : Bot;
  const canLeaveFeedback = !isUser && Boolean(message.id && onFeedback);

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[min(720px,92%)] rounded border px-4 py-3 shadow-panel ${
          isUser
            ? "border-blue-600 bg-blue-600 text-white"
            : "border-slate-200 bg-white text-slate-950"
        }`}
      >
        <div className="mb-2 flex items-center gap-2 text-xs font-black uppercase">
          <Icon
            aria-hidden="true"
            className={`h-4 w-4 ${isUser ? "text-blue-100" : "text-blue-700"}`}
          />
          <span className={isUser ? "text-blue-50" : "text-slate-500"}>
            {label}
          </span>
        </div>
        <div className="whitespace-pre-wrap break-words text-sm font-semibold leading-6">
          {message.content}
        </div>
        {!isUser && showMetadata ? (
          <div className="mt-3 flex flex-wrap gap-2 text-[11px] font-bold uppercase text-slate-400">
            {message.intent ? <span>Niyat: {message.intent}</span> : null}
            {message.source ? <span>Manba: {message.source}</span> : null}
            {message.confidence !== undefined ? (
              <span>Ishonch: {formatConfidence(message.confidence)}</span>
            ) : null}
          </div>
        ) : null}
        {canLeaveFeedback ? (
          <AIFeedbackButtons
            status={feedbackStatus}
            onFeedback={(rating) => onFeedback?.(message.id ?? "", rating)}
          />
        ) : null}
      </div>
    </div>
  );
}
