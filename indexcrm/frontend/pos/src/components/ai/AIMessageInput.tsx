"use client";

import { Loader2, SendHorizonal } from "lucide-react";

type AIMessageInputProps = {
  value: string;
  disabled?: boolean;
  onChange: (value: string) => void;
  onSend: () => void;
};

export function AIMessageInput({
  value,
  disabled = false,
  onChange,
  onSend,
}: AIMessageInputProps) {
  return (
    <div className="flex gap-2">
      <textarea
        value={value}
        disabled={disabled}
        rows={2}
        onChange={(event) => onChange(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            onSend();
          }
        }}
        placeholder="Savolingizni yozing..."
        className="min-h-[52px] flex-1 resize-none rounded border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-950 shadow-panel placeholder:text-slate-400 disabled:cursor-not-allowed disabled:bg-slate-100"
      />
      <button
        type="button"
        disabled={disabled || !value.trim()}
        onClick={onSend}
        className="inline-flex h-[52px] min-w-28 items-center justify-center gap-2 rounded bg-blue-700 px-4 text-sm font-black text-white shadow-panel hover:bg-blue-800 disabled:cursor-not-allowed disabled:bg-slate-300"
      >
        {disabled ? (
          <Loader2 aria-hidden="true" className="h-4 w-4 animate-spin" />
        ) : (
          <SendHorizonal aria-hidden="true" className="h-4 w-4" />
        )}
        Yuborish
      </button>
    </div>
  );
}
