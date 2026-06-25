"use client";

import { Edit3, PackagePlus, PackageSearch, Save, X } from "lucide-react";
import { FormEvent, useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { DataTable } from "@/components/dashboard/DataTable";
import { ErrorState } from "@/components/dashboard/ErrorState";
import { LoadingState } from "@/components/dashboard/LoadingState";
import { SectionHeader } from "@/components/dashboard/SectionHeader";
import { StatCard } from "@/components/dashboard/StatCard";
import { IconButton } from "@/components/pos/IconButton";
import { useProductsDashboard } from "@/hooks/useDashboardData";
import { formatApiError } from "@/lib/apiErrors";
import { formatMoney } from "@/lib/format";
import {
  createProduct,
  listBrands,
  listCategories,
  listUnits,
  ProductPayload,
  updateProduct,
} from "@/services/api/products";
import { Product } from "@/services/api/types";

type ProductFormState = {
  id?: string;
  name: string;
  category: string;
  brand: string;
  unit: string;
  sku: string;
  barcode: string;
  cost_price: string;
  selling_price: string;
  is_active: boolean;
};

const emptyForm: ProductFormState = {
  name: "",
  category: "",
  brand: "",
  unit: "",
  sku: "",
  barcode: "",
  cost_price: "0.00",
  selling_price: "0.00",
  is_active: true,
};

function formFromProduct(product: Product): ProductFormState {
  return {
    id: product.id,
    name: product.name,
    category: product.category,
    brand: product.brand ?? "",
    unit: product.unit,
    sku: product.sku ?? "",
    barcode: product.barcode ?? "",
    cost_price: product.cost_price,
    selling_price: product.selling_price,
    is_active: product.is_active,
  };
}

function buildPayload(form: ProductFormState): ProductPayload {
  return {
    category: form.category,
    brand: form.brand || null,
    name: form.name.trim(),
    barcode: form.barcode.trim() || null,
    sku: form.sku.trim() || null,
    cost_price: form.cost_price || "0.00",
    selling_price: form.selling_price || "0.00",
    min_price: form.cost_price || "0.00",
    unit: form.unit,
    is_active: form.is_active,
  };
}

export function ProductsDashboardPage() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [form, setForm] = useState<ProductFormState | null>(null);
  const [formMessage, setFormMessage] = useState("");
  const productsQuery = useProductsDashboard(search);
  const products = productsQuery.data?.results ?? [];
  const categoriesQuery = useQuery({
    queryKey: ["catalog-categories"],
    queryFn: listCategories,
  });
  const brandsQuery = useQuery({
    queryKey: ["catalog-brands"],
    queryFn: listBrands,
  });
  const unitsQuery = useQuery({ queryKey: ["catalog-units"], queryFn: listUnits });
  const categories = categoriesQuery.data?.results ?? [];
  const brands = brandsQuery.data?.results ?? [];
  const units = unitsQuery.data?.results ?? [];
  const productSetupLoading = categoriesQuery.isLoading || unitsQuery.isLoading;
  const productSetupUnavailable = categoriesQuery.isError || unitsQuery.isError;

  useEffect(() => {
    if (!form || form.id) {
      return;
    }
    if (!form.category && categories[0]) {
      setForm((current) =>
        current ? { ...current, category: categories[0].id } : current,
      );
    }
    if (!form.unit && units[0]) {
      setForm((current) => (current ? { ...current, unit: units[0].id } : current));
    }
  }, [categories, form, units]);

  const saveProduct = useMutation({
    mutationFn: (nextForm: ProductFormState) => {
      const payload = buildPayload(nextForm);
      return nextForm.id
        ? updateProduct(nextForm.id, payload)
        : createProduct(payload);
    },
    onSuccess: () => {
      setForm(null);
      setFormMessage("Mahsulot saqlandi.");
      void queryClient.invalidateQueries({ queryKey: ["dashboard-products"] });
      void queryClient.invalidateQueries({ queryKey: ["products"] });
    },
    onError: (error) => {
      setFormMessage(formatApiError(error, "Mahsulotni saqlab bo'lmadi."));
    },
  });

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFormMessage("");
    if (!form) {
      return;
    }
    if (!form.name.trim()) {
      setFormMessage("Mahsulot nomi majburiy.");
      return;
    }
    if (!form.category || !form.unit) {
      setFormMessage("Kategoriya va birlik majburiy. Avval seed_demo_data ishga tushiring.");
      return;
    }
    saveProduct.mutate(form);
  }

  if (productsQuery.isLoading) {
    return (
      <LoadingState
        label="Mahsulotlar"
        description="Faol katalog yozuvlari yuklanmoqda."
      />
    );
  }

  if (productsQuery.isError) {
    return (
      <ErrorState
        title="Mahsulotlarni yuklab bo'lmadi"
        error={productsQuery.error}
        onRetry={() => void productsQuery.refetch()}
      />
    );
  }

  return (
    <div className="grid gap-5">
      <SectionHeader
        title="Mahsulotlar"
        description="Sotiladigan katalogni yaratish va yuritish."
        actions={
          <div className="flex flex-col gap-2 sm:flex-row">
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              aria-label="Mahsulotlarni qidirish"
              placeholder="Mahsulotlarni qidirish"
              className="h-11 rounded border border-slate-300 px-3 font-semibold shadow-panel"
            />
            <IconButton
              type="button"
              icon={<PackagePlus aria-hidden="true" className="h-4 w-4" />}
              label="Yangi mahsulot"
              tone="primary"
              onClick={() => {
                if (productSetupLoading) {
                  setFormMessage("Mahsulot sozlama ro'yxatlari hali yuklanmoqda. Birozdan keyin urinib ko'ring.");
                  return;
                }
                if (productSetupUnavailable) {
                  setFormMessage("Mahsulot sozlama ro'yxatlarini yuklab bo'lmadi. Backend ishlaganda qayta urinib ko'ring.");
                  return;
                }
                if (categories.length === 0 || units.length === 0) {
                  setFormMessage("Mahsulot qo'shishdan oldin kamida bitta kategoriya va birlik yarating yoki seed qiling.");
                  return;
                }
                setForm({
                  ...emptyForm,
                  category: categories[0]?.id ?? "",
                  unit: units[0]?.id ?? "",
                });
                setFormMessage("");
              }}
            />
          </div>
        }
      />
      <StatCard
        title="Yuklangan mahsulotlar"
        value={String(productsQuery.data?.count ?? products.length)}
        icon={PackageSearch}
        tone="blue"
      />
      {form ? (
        <form
          onSubmit={handleSubmit}
          className="rounded border border-slate-200 bg-white p-4 shadow-panel"
        >
          <div className="mb-3 flex items-center justify-between gap-3">
            <h2 className="text-base font-black text-slate-950">
              {form.id ? "Mahsulotni tahrirlash" : "Mahsulot yaratish"}
            </h2>
            <IconButton
              type="button"
              icon={<X aria-hidden="true" className="h-4 w-4" />}
              label="Bekor qilish"
              onClick={() => setForm(null)}
            />
          </div>
          <div className="grid gap-3 md:grid-cols-3">
            <label className="grid gap-1 text-sm font-bold text-slate-700">
              Nomi
              <input
                value={form.name}
                onChange={(event) => setForm({ ...form, name: event.target.value })}
                className="h-11 rounded border border-slate-300 px-3 shadow-panel"
              />
            </label>
            <label className="grid gap-1 text-sm font-bold text-slate-700">
              Kategoriya
              <select
                value={form.category}
                onChange={(event) => setForm({ ...form, category: event.target.value })}
                className="h-11 rounded border border-slate-300 bg-white px-3 shadow-panel"
              >
                <option value="">Kategoriya tanlang</option>
                {categories.map((category) => (
                  <option key={category.id} value={category.id}>
                    {category.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="grid gap-1 text-sm font-bold text-slate-700">
              Birlik
              <select
                value={form.unit}
                onChange={(event) => setForm({ ...form, unit: event.target.value })}
                className="h-11 rounded border border-slate-300 bg-white px-3 shadow-panel"
              >
                <option value="">Birlik tanlang</option>
                {units.map((unit) => (
                  <option key={unit.id} value={unit.id}>
                    {unit.name} ({unit.short_name})
                  </option>
                ))}
              </select>
            </label>
            <label className="grid gap-1 text-sm font-bold text-slate-700">
              SKU
              <input
                value={form.sku}
                onChange={(event) => setForm({ ...form, sku: event.target.value })}
                className="h-11 rounded border border-slate-300 px-3 shadow-panel"
              />
            </label>
            <label className="grid gap-1 text-sm font-bold text-slate-700">
              Barcode
              <input
                value={form.barcode}
                onChange={(event) => setForm({ ...form, barcode: event.target.value })}
                className="h-11 rounded border border-slate-300 px-3 shadow-panel"
              />
            </label>
            <label className="grid gap-1 text-sm font-bold text-slate-700">
              Brend
              <select
                value={form.brand}
                onChange={(event) => setForm({ ...form, brand: event.target.value })}
                className="h-11 rounded border border-slate-300 bg-white px-3 shadow-panel"
              >
                <option value="">Brendsiz</option>
                {brands.map((brand) => (
                  <option key={brand.id} value={brand.id}>
                    {brand.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="grid gap-1 text-sm font-bold text-slate-700">
              Kirim narxi
              <input
                value={form.cost_price}
                onChange={(event) =>
                  setForm({ ...form, cost_price: event.target.value })
                }
                inputMode="decimal"
                className="h-11 rounded border border-slate-300 px-3 shadow-panel"
              />
            </label>
            <label className="grid gap-1 text-sm font-bold text-slate-700">
              Sotuv narxi
              <input
                value={form.selling_price}
                onChange={(event) =>
                  setForm({ ...form, selling_price: event.target.value })
                }
                inputMode="decimal"
                className="h-11 rounded border border-slate-300 px-3 shadow-panel"
              />
            </label>
            <label className="flex items-center gap-2 self-end text-sm font-bold text-slate-700">
              <input
                type="checkbox"
                checked={form.is_active}
                onChange={(event) =>
                  setForm({ ...form, is_active: event.target.checked })
                }
                className="h-5 w-5"
              />
              Faol
            </label>
          </div>
          {formMessage ? (
            <div className="mt-3 rounded border border-amber-200 bg-amber-50 px-3 py-2 text-sm font-bold text-amber-900">
              {formMessage}
            </div>
          ) : null}
          <IconButton
            type="submit"
            icon={<Save aria-hidden="true" className="h-4 w-4" />}
            label={saveProduct.isPending ? "Mahsulot saqlanmoqda" : "Mahsulotni saqlash"}
            tone="success"
            disabled={saveProduct.isPending}
            className="mt-3"
          />
        </form>
      ) : formMessage ? (
        <div className="rounded border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm font-bold text-emerald-900">
          {formMessage}
        </div>
      ) : null}
      <DataTable
        title="Mahsulotlar ro'yxati"
        rows={products}
        rowKey={(row) => row.id}
        emptyTitle={search ? "Mos mahsulot topilmadi" : "Mahsulot topilmadi"}
        emptyDescription={
          search
            ? "Boshqa nom, SKU, barcode, kategoriya yoki brend bilan urinib ko'ring."
            : "Katalogda yaratilgan mahsulotlar shu yerda chiqadi."
        }
        columns={[
          { key: "name", header: "Nomi", render: (row) => row.name },
          { key: "sku", header: "SKU", render: (row) => row.sku || "-" },
          {
            key: "category",
            header: "Kategoriya",
            render: (row) => row.category_name,
          },
          {
            key: "price",
            header: "Narx",
            align: "right",
            render: (row) => formatMoney(row.selling_price),
          },
          {
            key: "status",
            header: "Holat",
            render: (row) => (row.is_active ? "Faol" : "Faol emas"),
          },
          {
            key: "actions",
            header: "Amallar",
            align: "right",
            render: (row) => (
              <IconButton
                type="button"
                icon={<Edit3 aria-hidden="true" className="h-4 w-4" />}
                label="Mahsulotni tahrirlash"
                hideLabel
                onClick={() => {
                  setForm(formFromProduct(row));
                  setFormMessage("");
                }}
              />
            ),
          },
        ]}
      />
    </div>
  );
}
