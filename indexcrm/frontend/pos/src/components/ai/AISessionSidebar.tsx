"use client";

import { History, MessageSquarePlus, RefreshCw } from "lucide-react";

import { AIChatSession } from "@/services/api/types";

type AISessionSidebarProps = {
  sessions: AIChatSession[];
  activeSessionId: string | null;
  isLoading?: boolean;
  onNewChat: () => void;
  onRefresh: () => void;
  onSelect: (sessionId: string) => void;
};

function formatDate(value: string) {
  if (!value) {
    return "";
  }
  return new Intl.DateTimeFormat("uz-Latn-UZ", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

export function AISessionSidebar({
  sessions,
  activeSessionId,
  isLoading = false,
  onNewChat,
  onRefresh,
  onSelect,
}: AISessionSidebarProps) {
  return (
    <aside className="grid gap-3 rounded border border-slate-200 bg-white p-3 shadow-panel lg:sticky lg:top-20 lg:max-h-[calc(100vh-6rem)] lg:overflow-y-auto">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 text-sm font-black text-slate-900">
          <History aria-hidden="true" className="h-4 w-4 text-blue-700" />
          Chatlar
        </div>
        <button
          type="button"
          onClick={onRefresh}
          disabled={isLoading}
          className="inline-flex h-8 w-8 items-center justify-center rounded border border-slate-200 bg-white text-slate-600 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
          aria-label="Chatlarni yangilash"
        >
          <RefreshCw
            aria-hidden="true"
            className={`h-4 w-4 ${isLoading ? "animate-spin" : ""}`}
          />
        </button>
      </div>
      <button
        type="button"
        onClick={onNewChat}
        className="inline-flex h-10 items-center justify-center gap-2 rounded bg-slate-950 px-3 text-sm font-black text-white hover:bg-slate-800"
      >
        <MessageSquarePlus aria-hidden="true" className="h-4 w-4" />
        Yangi chat
      </button>
      <div className="grid max-h-72 gap-2 overflow-y-auto pr-1 lg:max-h-none">
        {sessions.length ? (
          sessions.map((session) => {
            const active = activeSessionId === session.id;
            return (
              <button
                key={session.id}
                type="button"
                onClick={() => onSelect(session.id)}
                className={`rounded border p-3 text-left transition ${
                  active
                    ? "border-blue-600 bg-blue-50"
                    : "border-slate-200 bg-white hover:bg-slate-50"
                }`}
              >
                <div className="line-clamp-1 text-sm font-black text-slate-900">
                  {session.title || "Yangi chat"}
                </div>
                <div className="mt-1 line-clamp-2 text-xs font-semibold leading-5 text-slate-500">
                  {session.last_message_preview || "Hali xabar yo'q"}
                </div>
                <div className="mt-2 flex items-center justify-between gap-2 text-[11px] font-bold uppercase text-slate-400">
                  <span>{session.message_count ?? 0} xabar</span>
                  <span>{formatDate(session.updated_at)}</span>
                </div>
              </button>
            );
          })
        ) : (
          <div className="rounded border border-dashed border-slate-200 p-3 text-sm font-semibold text-slate-500">
            Hozircha chatlar yo'q.
          </div>
        )}
      </div>
    </aside>
  );
}
