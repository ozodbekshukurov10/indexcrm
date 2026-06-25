"use client";

import { Loader2, ScanBarcode } from "lucide-react";
import { FormEvent, useEffect, useRef, useState } from "react";

type BarcodeInputProps = {
  disabled?: boolean;
  busy?: boolean;
  onScan: (code: string) => void | Promise<void>;
};

function normalizeScanInput(value: string) {
  return value.replace(/[\r\n\t]/g, "").trim();
}

const DUPLICATE_SCAN_WINDOW_MS = 450;

export function BarcodeInput({ disabled, busy, onScan }: BarcodeInputProps) {
  const [code, setCode] = useState("");
  const [processing, setProcessing] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const processingRef = useRef(false);
  const queueRef = useRef<string[]>([]);
  const lastSubmittedRef = useRef<{ code: string; at: number } | null>(null);

  useEffect(() => {
    inputRef.current?.focus();
    const listener = (event: KeyboardEvent) => {
      if (event.key === "F2") {
        event.preventDefault();
        inputRef.current?.focus();
      }
    };
    window.addEventListener("keydown", listener);
    return () => window.removeEventListener("keydown", listener);
  }, []);

  async function processQueue() {
    if (processingRef.current) {
      return;
    }

    processingRef.current = true;
    setProcessing(true);
    try {
      while (queueRef.current.length > 0) {
        const nextCode = queueRef.current.shift();
        if (nextCode) {
          await onScan(nextCode);
        }
      }
    } finally {
      processingRef.current = false;
      setProcessing(false);
      inputRef.current?.focus();
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = normalizeScanInput(code);
    if (!trimmed) {
      inputRef.current?.focus();
      return;
    }

    const now = Date.now();
    const lastSubmitted = lastSubmittedRef.current;
    if (
      lastSubmitted &&
      lastSubmitted.code === trimmed &&
      now - lastSubmitted.at < DUPLICATE_SCAN_WINDOW_MS
    ) {
      setCode("");
      inputRef.current?.focus();
      return;
    }
    lastSubmittedRef.current = { code: trimmed, at: now };

    queueRef.current.push(trimmed);
    setCode("");
    inputRef.current?.focus();
    await processQueue();
  }

  const isBusy = busy || processing;

  return (
    <form onSubmit={handleSubmit} className="flex gap-2">
      <div className="relative flex-1">
        <ScanBarcode
          aria-hidden="true"
          className="pointer-events-none absolute left-4 top-1/2 h-6 w-6 -translate-y-1/2 text-slate-400"
        />
        <input
          ref={inputRef}
          value={code}
          onChange={(event) => setCode(event.target.value)}
          disabled={disabled}
          onFocus={(event) => event.target.select()}
          placeholder={isBusy ? "Skan qilinmoqda..." : "Barcode"}
          autoComplete="off"
          aria-label="Barcode yoki SKU"
          title="Barcode yoki SKU"
          inputMode="search"
          className="glass-input h-14 w-full rounded-xl pl-12 pr-4 text-xl font-bold text-slate-900 placeholder:text-slate-400 transition focus:border-primary-400 focus:ring-2 focus:ring-primary-500/20"
        />
      </div>
      <button
        type="submit"
        disabled={disabled || !code.trim()}
        className="inline-flex min-w-28 items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-primary-500/90 to-primary-600/90 px-4 text-sm font-bold text-white shadow-glass backdrop-blur-sm transition hover:from-primary-400/90 hover:to-primary-500/90 active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-50 disabled:shadow-none"
      >
        {isBusy ? (
          <Loader2 aria-hidden="true" className="h-5 w-5 animate-spin" />
        ) : (
          <ScanBarcode aria-hidden="true" className="h-5 w-5" />
        )}
        <span>Skan</span>
      </button>
    </form>
  );
}
