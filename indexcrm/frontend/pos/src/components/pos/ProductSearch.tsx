"use client";

import { AlertCircle, Loader2, PackageSearch, RotateCw, Search } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { useProductSearch } from "@/hooks/useProducts";
import { formatMoney } from "@/lib/format";
import { findProductByBarcode } from "@/services/api/products";
import { Product } from "@/services/api/types";

type ProductSearchProps = {
  onSelectProduct: (product: Product) => void;
};

export function ProductSearch({ onSelectProduct }: ProductSearchProps) {
  const [search, setSearch] = useState("");
  const [enterNotice, setEnterNotice] = useState("");
  const [enterLoading, setEnterLoading] = useState(false);
  const searchInputRef = useRef<HTMLInputElement>(null);
  const productsQuery = useProductSearch(search);
  const products = productsQuery.data?.results ?? [];
  const normalizedSearch = search.trim();
  const isSearchReady =
    normalizedSearch.length === 0 || normalizedSearch.length >= 2;

  useEffect(() => {
    const listener = (event: KeyboardEvent) => {
      if (event.key === "F3") {
        event.preventDefault();
        searchInputRef.current?.focus();
        searchInputRef.current?.select();
      }
    };
    window.addEventListener("keydown", listener);
    return () => window.removeEventListener("keydown", listener);
  }, []);

  async function handleEnterAdd() {
    const code = search.trim();
    if (!code || enterLoading) {
      return;
    }

    setEnterNotice("");
    setEnterLoading(true);
    try {
      const exactProduct = await findProductByBarcode(code);
      if (exactProduct) {
        onSelectProduct(exactProduct);
        setSearch("");
        searchInputRef.current?.focus();
        return;
      }

      const refreshedProducts = (await productsQuery.refetch()).data?.results ?? [];
      if (refreshedProducts.length === 1) {
        onSelectProduct(refreshedProducts[0]);
        setSearch("");
        searchInputRef.current?.focus();
        return;
      }

      setEnterNotice(`Mahsulot topilmadi: ${code}`);
      searchInputRef.current?.focus();
    } catch (error) {
      setEnterNotice(
        error instanceof TypeError
          ? "Backend bilan aloqa yo'q. Mahsulot qo'shilmadi."
          : `${code} bo'yicha mahsulot qidiruvi amalga oshmadi. Qayta urinib ko'ring.`,
      );
      searchInputRef.current?.focus();
    } finally {
      setEnterLoading(false);
    }
  }

  return (
    <section className="flex min-h-0 flex-1 flex-col border-r border-white/20 bg-white/20 backdrop-blur-sm">
      <div className="border-b border-white/20 p-3">
        <div className="relative">
          <Search
            aria-hidden="true"
            className="pointer-events-none absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-slate-400"
          />
          <input
            ref={searchInputRef}
            value={search}
            onChange={(event) => {
              setSearch(event.target.value);
              setEnterNotice("");
            }}
            onKeyDown={(event) => {
              if (event.key === "Enter") {
                event.preventDefault();
                void handleEnterAdd();
              }
            }}
            placeholder="Mahsulot qidirish"
            className="glass-input h-12 w-full rounded-xl pl-11 pr-4 text-base font-semibold text-slate-900 placeholder:text-slate-400 transition focus:border-primary-400 focus:ring-2 focus:ring-primary-500/20"
          />
        </div>
        {enterNotice ? (
          <div
            role="status"
            className="mt-2 animate-fade-in rounded-xl border border-amber-200/60 bg-amber-50/80 px-4 py-2.5 text-sm font-bold text-amber-800 backdrop-blur-sm"
          >
            {enterNotice}
          </div>
        ) : null}
        {enterLoading ? (
          <div
            role="status"
            className="mt-2 flex animate-fade-in items-center gap-2 rounded-xl border border-primary-200/60 bg-primary-50/80 px-4 py-2.5 text-sm font-bold text-primary-700 backdrop-blur-sm"
          >
            <Loader2 aria-hidden="true" className="h-4 w-4 animate-spin" />
            Mahsulot qidirilmoqda
          </div>
        ) : null}
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto p-3">
        {!isSearchReady ? (
          <div className="glass-card flex min-h-48 flex-col items-center justify-center rounded-xl p-6 text-center shadow-glass">
            <Search aria-hidden="true" className="mb-3 h-8 w-8 text-slate-300" />
            <div className="text-base font-bold text-slate-700">
              Qidirish uchun yozishda davom eting
            </div>
            <div className="mt-1 text-sm font-medium text-slate-500">
              Kamida 2 ta belgi kiriting yoki barcode skan qiling.
            </div>
          </div>
        ) : null}

        {isSearchReady && productsQuery.isLoading ? (
          <div className="glass-card flex min-h-48 flex-col items-center justify-center rounded-xl p-6 text-center shadow-glass">
            <Loader2
              aria-hidden="true"
              className="mb-3 h-8 w-8 animate-spin text-primary-500"
            />
            <div className="text-base font-bold text-slate-700">
              Mahsulotlar yuklanmoqda
            </div>
            <div className="mt-1 text-sm font-medium text-slate-500">
              Savdo uchun faol mahsulotlar tayyorlanmoqda.
            </div>
          </div>
        ) : null}

        {isSearchReady && productsQuery.isError ? (
          <div className="glass-card flex min-h-48 flex-col items-center justify-center rounded-xl border-rose-200/60 bg-rose-50/80 p-6 text-center shadow-glass">
            <AlertCircle aria-hidden="true" className="mb-3 h-8 w-8 text-rose-500" />
            <div className="text-base font-bold text-rose-800">
              Mahsulotlarni yuklab bo'lmadi
            </div>
            <div className="mt-1 text-sm font-medium text-rose-600">
              Aloqani tekshirib, qayta urinib ko'ring.
            </div>
            <button
              type="button"
              onClick={() => void productsQuery.refetch()}
              className="mt-4 inline-flex items-center gap-2 rounded-xl border border-rose-200/60 bg-white/60 px-4 py-2.5 text-sm font-bold text-rose-700 shadow-glass backdrop-blur-sm transition hover:bg-white/80"
            >
              <RotateCw aria-hidden="true" className="h-4 w-4" />
              Qayta urinish
            </button>
          </div>
        ) : null}

        {isSearchReady && productsQuery.isSuccess && products.length > 0 ? (
          <div className="grid grid-cols-1 gap-2 xl:grid-cols-2">
            {products.map((product) => (
              <button
                key={product.id}
                onClick={() => onSelectProduct(product)}
                className="glass-card flex min-h-24 flex-col items-start justify-between rounded-xl p-4 text-left shadow-glass transition hover:bg-white/70 hover:shadow-glass-lg focus:border-primary-400 focus:outline-none focus:ring-2 focus:ring-primary-500/20"
              >
                <span className="line-clamp-2 text-sm font-black text-slate-900">
                  {product.name}
                </span>
                <span className="mt-1 text-xs font-semibold text-slate-500">
                  {product.sku || product.barcode || "-"}
                </span>
                <span className="mt-1.5 text-base font-black text-emerald-600">
                  {formatMoney(product.selling_price)}
                </span>
              </button>
            ))}
          </div>
        ) : null}

        {isSearchReady && productsQuery.isSuccess && products.length === 0 ? (
          <div className="glass-card flex min-h-48 flex-col items-center justify-center rounded-xl p-6 text-center shadow-glass">
            <PackageSearch
              aria-hidden="true"
              className="mb-3 h-8 w-8 text-slate-300"
            />
            <div className="text-base font-bold text-slate-700">
              {normalizedSearch ? "Mos mahsulot topilmadi" : "Faol mahsulot yo'q"}
            </div>
            <div className="mt-1 text-sm font-medium text-slate-500">
              {normalizedSearch
                ? "Boshqa nom, SKU yoki barcode bilan urinib ko'ring."
                : "Savdodan oldin katalogga faol mahsulot qo'shing."}
            </div>
          </div>
        ) : null}
      </div>
    </section>
  );
}
