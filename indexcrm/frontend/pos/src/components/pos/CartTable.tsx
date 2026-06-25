"use client";

import { Minus, Plus, ScanBarcode, ShoppingCart, Trash2 } from "lucide-react";

import { formatMoney } from "@/lib/format";
import { CartItem, getCartLineTotal } from "@/stores/cartStore";

import { IconButton } from "./IconButton";

type CartTableProps = {
  items: CartItem[];
  onQuantityChange: (productId: string, quantity: number) => void;
  onRemove: (productId: string) => void;
};

export function CartTable({ items, onQuantityChange, onRemove }: CartTableProps) {
  return (
    <section className="flex min-h-0 flex-1 flex-col bg-white/30 backdrop-blur-sm">
      <div className="grid grid-cols-[1fr_132px_120px_56px] border-b border-white/20 bg-white/30 px-4 py-3 text-xs font-bold uppercase tracking-wider text-slate-500">
        <span>Mahsulot</span>
        <span className="text-center">Miqdor</span>
        <span className="text-right">Jami</span>
        <span />
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto">
        {items.length === 0 ? (
          <div className="flex h-full items-center justify-center p-6 text-center">
            <div>
              <ShoppingCart
                aria-hidden="true"
                className="mx-auto mb-3 h-10 w-10 text-slate-300"
              />
              <div className="text-xl font-black text-slate-700">
                Savat bo'sh
              </div>
              <div className="mt-2 flex items-center justify-center gap-2 text-sm font-semibold text-slate-500">
                <ScanBarcode aria-hidden="true" className="h-4 w-4" />
                Boshlash uchun barcode skan qiling yoki mahsulot tanlang.
              </div>
            </div>
          </div>
        ) : (
          items.map((item) => (
            <div
              key={item.product.id}
              className="grid min-h-24 grid-cols-[1fr_132px_120px_56px] items-center gap-3 border-b border-white/20 px-4 py-3 transition hover:bg-white/30"
            >
              <div className="min-w-0">
                <div className="truncate text-base font-black text-slate-900">
                  {item.product.name}
                </div>
                <div className="mt-0.5 text-sm font-semibold text-slate-500">
                  {item.product.sku || item.product.barcode || "-"} -{" "}
                  {formatMoney(item.price)}
                </div>
              </div>
              <div className="flex items-center justify-center gap-1">
                <IconButton
                  icon={<Minus aria-hidden="true" className="h-4 w-4" />}
                  label="Kamaytirish"
                  onClick={() =>
                    onQuantityChange(item.product.id, item.quantity - 1)
                  }
                  hideLabel
                  className="h-9 w-9 rounded-lg"
                />
                <input
                  value={item.quantity}
                  onChange={(event) =>
                    onQuantityChange(item.product.id, Number(event.target.value))
                  }
                  onFocus={(event) => event.target.select()}
                  className="glass-input h-9 w-14 rounded-lg text-center text-base font-bold"
                  inputMode="decimal"
                  min="0"
                  step="1"
                />
                <IconButton
                  icon={<Plus aria-hidden="true" className="h-4 w-4" />}
                  label="Ko'paytirish"
                  onClick={() =>
                    onQuantityChange(item.product.id, item.quantity + 1)
                  }
                  hideLabel
                  className="h-9 w-9 rounded-lg"
                />
              </div>
              <div className="text-right text-lg font-black text-slate-900">
                {formatMoney(getCartLineTotal(item))}
              </div>
              <IconButton
                icon={<Trash2 aria-hidden="true" className="h-4 w-4" />}
                label="O'chirish"
                tone="danger"
                onClick={() => onRemove(item.product.id)}
                hideLabel
                className="h-9 w-9 rounded-lg"
              />
            </div>
          ))
        )}
      </div>
    </section>
  );
}
