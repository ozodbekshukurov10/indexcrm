"use client";

import {
  AlertCircle,
  CheckCircle2,
  Loader2,
  LockKeyhole,
  Save,
  UnlockKeyhole,
  UserCog,
} from "lucide-react";
import { FormEvent, useEffect, useState } from "react";

import {
  useActiveCashierShift,
  useCloseCashierShift,
  useOpenCashierShift,
} from "@/hooks/useCashierShifts";
import { useBranches, useCashDesks, useWarehouses } from "@/hooks/useLocations";
import { ApiError } from "@/services/api/client";
import { useAuthStore } from "@/stores/authStore";
import { useCashierStore } from "@/stores/cashierStore";

export function CashierSessionPanel() {
  const session = useCashierStore();
  const { status, user } = useAuthStore();
  const [cashierName, setCashierName] = useState(session.cashierName);
  const [cashierEmail, setCashierEmail] = useState(session.cashierEmail);
  const [branchId, setBranchId] = useState(session.branchId);
  const [warehouseId, setWarehouseId] = useState(session.warehouseId);
  const [cashDeskId, setCashDeskId] = useState(session.cashDeskId);
  const [activeShiftId, setActiveShiftId] = useState(session.activeShiftId);
  const [authToken, setAuthToken] = useState(session.authToken);
  const [openingBalance, setOpeningBalance] = useState("0.00");
  const [closingBalance, setClosingBalance] = useState("0.00");
  const [shiftNotice, setShiftNotice] = useState("");
  const activeShift = useActiveCashierShift(branchId);
  const openShift = useOpenCashierShift();
  const closeShift = useCloseCashierShift();
  const branchesQuery = useBranches();
  const warehousesQuery = useWarehouses(branchId);
  const cashDesksQuery = useCashDesks(branchId);
  const branches = branchesQuery.data?.results ?? [];
  const warehouses = warehousesQuery.data?.results ?? [];
  const cashDesks = cashDesksQuery.data?.results ?? [];
  const selectedBranch = branches.find((branch) => branch.id === branchId);
  const selectedWarehouse = warehouses.find(
    (warehouse) => warehouse.id === warehouseId,
  );
  const selectedCashDesk = cashDesks.find(
    (cashDesk) => cashDesk.id === cashDeskId,
  );

  useEffect(() => {
    setCashierName(session.cashierName);
    setCashierEmail(session.cashierEmail);
    setBranchId(session.branchId);
    setWarehouseId(session.warehouseId);
    setCashDeskId(session.cashDeskId);
    setActiveShiftId(session.activeShiftId);
    setAuthToken(session.authToken);
  }, [
    session.activeShiftId,
    session.authToken,
    session.branchId,
    session.cashDeskId,
    session.cashierEmail,
    session.cashierName,
    session.warehouseId,
  ]);

  useEffect(() => {
    if (activeShift.data?.id && activeShift.data.id !== activeShiftId) {
      setActiveShiftId(activeShift.data.id);
      session.setActiveShiftId(activeShift.data.id);
      return;
    }

    if (activeShift.isSuccess && activeShift.data === null && activeShiftId) {
      setActiveShiftId("");
      session.setActiveShiftId("");
    }
  }, [activeShift.data, activeShift.isSuccess, activeShiftId, session]);

  useEffect(() => {
    if (!branchesQuery.isSuccess || branches.length === 0) {
      return;
    }

    const selectedBranchExists = branches.some((branch) => branch.id === branchId);
    if (selectedBranchExists) {
      return;
    }

    const profileBranchId = user?.profile?.branch ?? "";
    const nextBranch =
      branches.find((branch) => branch.id === profileBranchId) ?? branches[0];

    setBranchId(nextBranch.id);
    setWarehouseId("");
    setCashDeskId("");
    setActiveShiftId("");
    session.setSession({
      cashierName,
      cashierEmail,
      branchId: nextBranch.id,
      warehouseId: "",
      cashDeskId: "",
      activeShiftId: "",
      authToken,
    });
  }, [
    authToken,
    branches,
    branchesQuery.isSuccess,
    branchId,
    cashierEmail,
    cashierName,
    session,
    user?.profile?.branch,
  ]);

  useEffect(() => {
    if (!branchId || !warehousesQuery.isSuccess) {
      return;
    }

    const selectedWarehouseExists = warehouses.some(
      (warehouse) => warehouse.id === warehouseId,
    );
    if (selectedWarehouseExists) {
      return;
    }

    if (warehouses.length === 0) {
      if (warehouseId) {
        setWarehouseId("");
        session.setSession({
          cashierName,
          cashierEmail,
          branchId,
          warehouseId: "",
          cashDeskId,
          activeShiftId,
          authToken,
        });
      }
      return;
    }

    const nextWarehouse = warehouses[0];
    setWarehouseId(nextWarehouse.id);
    session.setSession({
      cashierName,
      cashierEmail,
      branchId,
      warehouseId: nextWarehouse.id,
      cashDeskId,
      activeShiftId,
      authToken,
    });
  }, [
    activeShiftId,
    authToken,
    branchId,
    cashDeskId,
    cashierEmail,
    cashierName,
    session,
    warehouseId,
    warehouses,
    warehousesQuery.isSuccess,
  ]);

  useEffect(() => {
    if (!branchId || !cashDesksQuery.isSuccess) {
      return;
    }

    const selectedCashDeskExists = cashDesks.some(
      (cashDesk) => cashDesk.id === cashDeskId,
    );
    if (selectedCashDeskExists) {
      return;
    }

    if (cashDesks.length === 0) {
      if (cashDeskId) {
        setCashDeskId("");
        session.setSession({
          cashierName,
          cashierEmail,
          branchId,
          warehouseId,
          cashDeskId: "",
          activeShiftId,
          authToken,
        });
      }
      return;
    }

    const nextCashDesk = cashDesks[0];
    setCashDeskId(nextCashDesk.id);
    session.setSession({
      cashierName,
      cashierEmail,
      branchId,
      warehouseId,
      cashDeskId: nextCashDesk.id,
      activeShiftId,
      authToken,
    });
  }, [
    activeShiftId,
    authToken,
    branchId,
    cashDeskId,
    cashDesks,
    cashDesksQuery.isSuccess,
    cashierEmail,
    cashierName,
    session,
    warehouseId,
  ]);

  useEffect(() => {
    if (activeShift.data?.expected_balance) {
      setClosingBalance(activeShift.data.expected_balance);
    }
  }, [activeShift.data?.expected_balance]);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    session.setSession({
      cashierName,
      cashierEmail,
      branchId,
      warehouseId,
      cashDeskId,
      activeShiftId,
      authToken,
    });
  }

  function persistSession(nextActiveShiftId = activeShiftId) {
    session.setSession({
      cashierName,
      cashierEmail,
      branchId,
      warehouseId,
      cashDeskId,
      activeShiftId: nextActiveShiftId,
      authToken,
    });
  }

  function handleBranchChange(nextBranchId: string) {
    setBranchId(nextBranchId);
    setWarehouseId("");
    setCashDeskId("");
    setActiveShiftId("");
    session.setSession({
      cashierName,
      cashierEmail,
      branchId: nextBranchId,
      warehouseId: "",
      cashDeskId: "",
      activeShiftId: "",
      authToken,
    });
    setShiftNotice(
      nextBranchId
        ? "Filial tanlandi. Omborni tanlang, keyin smenani oching yoki tanlang."
        : "Checkoutdan oldin filialni tanlang.",
    );
  }

  function handleWarehouseChange(nextWarehouseId: string) {
    setWarehouseId(nextWarehouseId);
    session.setSession({
      cashierName,
      cashierEmail,
      branchId,
      warehouseId: nextWarehouseId,
      cashDeskId,
      activeShiftId,
      authToken,
    });
    setShiftNotice(
      nextWarehouseId
        ? "Checkout qoldig'i uchun ombor tanlandi."
        : "Checkoutdan oldin omborni tanlang.",
    );
  }

  function handleCashDeskChange(nextCashDeskId: string) {
    setCashDeskId(nextCashDeskId);
    session.setSession({
      cashierName,
      cashierEmail,
      branchId,
      warehouseId,
      cashDeskId: nextCashDeskId,
      activeShiftId,
      authToken,
    });
    setShiftNotice(
      nextCashDeskId
        ? "Bu terminal uchun kassa tanlandi."
        : "Kassa tanlanmagan. Checkout davom etadi, lekin pilot sozlamasida kassa bo'lishi kerak.",
    );
  }

  function formatShiftError(error: unknown) {
    if (error instanceof ApiError) {
      const detail = error.detail as Record<string, unknown> | string;
      if (error.status === 401 || error.status === 403) {
        return "Bu akkaunt tanlangan filial uchun kassir smenasini boshqara olmaydi.";
      }
      if (error.status >= 500) {
        return "Server kassir smenasini yangilay olmadi. Bir marta qayta urinib ko'ring, davom etsa yordamga murojaat qiling.";
      }
      if (typeof detail === "string") {
        return detail;
      }
      if (detail && typeof detail === "object") {
        if (typeof detail.message === "string") {
          return detail.message;
        }
        if (typeof detail.detail === "string") {
          return detail.detail;
        }
        return "Kassir smenasi amali bajarilmadi. Filial huquqi va kassa summasini tekshirib, qayta urinib ko'ring.";
      }
      return "Kassir smenasi amali bajarilmadi. Filial huquqini tekshirib, qayta urinib ko'ring.";
    }
    return "Kassir smenasi amali bajarilmadi. Filial huquqini tekshirib, qayta urinib ko'ring.";
  }

  async function handleOpenShift() {
    if (!branchId) {
      setShiftNotice("Smena ochishdan oldin filial tanlanishi kerak.");
      return;
    }

    setShiftNotice("");
    try {
      const shift = await openShift.mutateAsync({
        branch: branchId,
        opening_balance: openingBalance || "0.00",
      });
      setActiveShiftId(shift.id);
      persistSession(shift.id);
      setShiftNotice(`${shift.branch_name || "tanlangan filial"} uchun smena ochildi.`);
    } catch (error) {
      setShiftNotice(formatShiftError(error));
    }
  }

  async function handleCloseShift() {
    if (!activeShiftId) {
      setShiftNotice("Faol smena tanlanmagan.");
      return;
    }

    setShiftNotice("");
    try {
      await closeShift.mutateAsync({
        shiftId: activeShiftId,
        closingBalance: closingBalance || "0.00",
      });
      setActiveShiftId("");
      session.setActiveShiftId("");
      setShiftNotice("Smena yopildi. Checkoutdan oldin yangi smena oching.");
    } catch (error) {
      setShiftNotice(formatShiftError(error));
    }
  }

  const configReady = Boolean(branchId && warehouseId);
  const sessionReady = Boolean(configReady && activeShiftId);
  const userName =
    user && ([user.first_name, user.last_name].filter(Boolean).join(" ") || user.email);
  const shiftLoading =
    status === "checking" || (Boolean(branchId) && activeShift.isFetching);
  const shiftActionPending = openShift.isPending || closeShift.isPending;
  const locationLoading =
    branchesQuery.isFetching ||
    (Boolean(branchId) && warehousesQuery.isFetching && warehouses.length === 0) ||
    (Boolean(branchId) && cashDesksQuery.isFetching && cashDesks.length === 0);
  let locationMessage = "";
  if (branchesQuery.isError) {
    locationMessage = "Filiallarni yuklab bo'lmadi. Checkoutdan oldin backend/API aloqasini tekshiring.";
  } else if (branchesQuery.isSuccess && branches.length === 0) {
    locationMessage = "Faol filial topilmadi. Avval seed_demo_data ishga tushiring yoki filial yarating.";
  } else if (branchId && warehousesQuery.isError) {
    locationMessage = "Bu filial uchun omborlarni yuklab bo'lmadi. Backend aloqasini tekshiring.";
  } else if (warehousesQuery.isSuccess && branchId && warehouses.length === 0) {
    locationMessage = "Bu filial uchun faol ombor topilmadi.";
  } else if (branchId && cashDesksQuery.isError) {
    locationMessage =
      "Kassalarni yuklab bo'lmadi. Checkout davom etadi, lekin admin POS kassa sozlamasini tekshirsin.";
  } else if (cashDesksQuery.isSuccess && branchId && cashDesks.length === 0) {
    locationMessage =
      "Bu filial uchun faol kassa topilmadi. Pilot kuzatuvi uchun admin kassa yaratsin.";
  }
  const missingSessionMessage = !branchId && !warehouseId
    ? "Filial va ombor tanlanmagan. Checkoutdan oldin Sessiyada tanlang."
    : !branchId
      ? "Filial tanlanmagan. Checkoutdan oldin Sessiyada filialni tanlang."
      : !warehouseId
        ? "Ombor tanlanmagan. Checkoutdan oldin Sessiyada omborni tanlang."
        : activeShift.isError
          ? "Faol kassir smenasini yuklab bo'lmadi. Bu filial uchun backend aloqasini tekshiring."
          : !activeShiftId
            ? "Faol kassir smenasi yo'q. Checkoutdan oldin Sessiyada smenani oching."
            : "";
  const setupGuidance = !branchId
    ? "Keyingi qadam: kassir filialini tanlang."
    : !warehouseId
      ? "Keyingi qadam: bu savdo uchun qoldiq beradigan omborni tanlang."
      : activeShift.isError
        ? "Keyingi qadam: backend aloqasini tekshiring, keyin smenani qayta aniqlang."
        : !activeShiftId
          ? "Keyingi qadam: kerak bo'lsa boshlang'ich naqdni kiriting, keyin Smenani ochish tugmasini bosing."
          : !cashDeskId
            ? "Kassa tanlanmagan. Checkout davom etadi, lekin pilot sozlamasida kassa bo'lishi kerak."
            : "";
  const readySessionMessage = `Tayyor: ${selectedBranch?.name ?? "tanlangan filial"} / ${
    selectedWarehouse?.name ?? "tanlangan ombor"
  } / ${selectedCashDesk?.code ?? selectedCashDesk?.name ?? "kassa"} / faol smena${userName ? ` - ${userName}` : ""}`;

  return (
    <form
      onSubmit={handleSubmit}
      className="no-print border-b border-slate-200 bg-slate-50 p-4"
    >
      <div className="mb-3 flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-slate-600">
        <UserCog aria-hidden="true" className="h-4 w-4" />
        Sessiya
      </div>

      <div
        className={`mb-3 flex min-h-10 items-center gap-2 rounded-xl border px-3 py-2 text-xs font-bold ${
          shiftLoading
            ? "border-blue-200 bg-blue-50 text-blue-700"
            : sessionReady
              ? "border-emerald-200 bg-emerald-50 text-emerald-700"
              : "border-amber-200 bg-amber-50 text-amber-800"
        }`}
      >
        {shiftLoading ? (
          <Loader2 aria-hidden="true" className="h-4 w-4 animate-spin" />
        ) : sessionReady ? (
          <CheckCircle2 aria-hidden="true" className="h-4 w-4" />
        ) : (
          <AlertCircle aria-hidden="true" className="h-4 w-4" />
        )}
        <span>
          {status === "checking"
            ? "Kassir sessiyasi yuklanmoqda"
            : sessionReady
              ? readySessionMessage
              : missingSessionMessage}
        </span>
      </div>

      <div className="mb-3 grid grid-cols-2 gap-2 text-xs font-bold">
        <div className="rounded-xl border border-slate-200/80 bg-white px-3 py-2.5 shadow-sm">
          <div className="text-[11px] uppercase tracking-wider text-slate-500">Filial</div>
          <div className="mt-0.5 truncate text-slate-800">
            {selectedBranch?.name ?? (branchId ? "Tanlangan filial" : "Yo'q")}
          </div>
        </div>
        <div className="rounded-xl border border-slate-200/80 bg-white px-3 py-2.5 shadow-sm">
          <div className="text-[11px] uppercase tracking-wider text-slate-500">Ombor</div>
          <div className="mt-0.5 truncate text-slate-800">
            {selectedWarehouse?.name ?? (warehouseId ? "Tanlangan ombor" : "Yo'q")}
          </div>
        </div>
        <div className="rounded-xl border border-slate-200/80 bg-white px-3 py-2.5 shadow-sm">
          <div className="text-[11px] uppercase tracking-wider text-slate-500">Kassa</div>
          <div className="mt-0.5 truncate text-slate-800">
            {selectedCashDesk
              ? `${selectedCashDesk.code} - ${selectedCashDesk.name}`
              : cashDeskId
                ? "Tanlangan kassa"
                : "Tanlanmagan"}
          </div>
        </div>
        <div className="rounded-xl border border-slate-200/80 bg-white px-3 py-2.5 shadow-sm">
          <div className="text-[11px] uppercase tracking-wider text-slate-500">Smena</div>
          <div className="mt-0.5 truncate text-slate-800">
            {activeShiftId ? "Faol smena ochiq" : "Yo'q"}
          </div>
        </div>
      </div>

      {setupGuidance && !shiftLoading ? (
        <div className="mb-3 animate-fade-in rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs font-bold text-amber-800">
          {setupGuidance}
        </div>
      ) : null}

      <div className="mb-3 grid grid-cols-2 gap-2">
        <input
          value={cashierName}
          onChange={(event) => setCashierName(event.target.value)}
          placeholder="Kassir"
          className="h-10 rounded-xl border border-slate-200/80 bg-white px-3 text-sm font-semibold text-slate-900 placeholder:text-slate-400 shadow-sm transition focus:border-primary-400 focus:ring-2 focus:ring-primary-500/20"
        />
        <input
          value={cashierEmail}
          onChange={(event) => setCashierEmail(event.target.value)}
          placeholder="Email"
          className="h-10 rounded-xl border border-slate-200/80 bg-white px-3 text-sm font-semibold text-slate-900 placeholder:text-slate-400 shadow-sm transition focus:border-primary-400 focus:ring-2 focus:ring-primary-500/20"
        />
        <label className="block">
          <span className="mb-1 block text-[11px] font-bold uppercase tracking-wider text-slate-500">
            Filial
          </span>
          <select
            value={branchId}
            onChange={(event) => handleBranchChange(event.target.value)}
            disabled={branchesQuery.isFetching && branches.length === 0}
            className="h-10 w-full rounded-xl border border-slate-200/80 bg-white px-3 text-sm font-semibold text-slate-900 shadow-sm transition focus:border-primary-400 focus:ring-2 focus:ring-primary-500/20"
          >
            <option value="">
              {branchesQuery.isFetching && branches.length === 0
                ? "Filiallar yuklanmoqda"
                : branches.length === 0
                  ? "Filial yo'q"
                  : "Filialni tanlang"}
            </option>
            {branches.map((branch) => (
              <option key={branch.id} value={branch.id}>
                {branch.store_name ? `${branch.store_name} - ${branch.name}` : branch.name}
              </option>
            ))}
          </select>
        </label>
        <label className="block">
          <span className="mb-1 block text-[11px] font-bold uppercase tracking-wider text-slate-500">
            Ombor
          </span>
          <select
            value={warehouseId}
            onChange={(event) => handleWarehouseChange(event.target.value)}
            disabled={!branchId || warehousesQuery.isFetching && warehouses.length === 0}
            className="h-10 w-full rounded-xl border border-slate-200/80 bg-white px-3 text-sm font-semibold text-slate-900 shadow-sm transition focus:border-primary-400 focus:ring-2 focus:ring-primary-500/20"
          >
            <option value="">
              {!branchId
                ? "Avval filialni tanlang"
                : warehousesQuery.isFetching && warehouses.length === 0
                  ? "Omborlar yuklanmoqda"
                  : warehouses.length === 0
                    ? "Ombor yo'q"
                    : "Omborni tanlang"}
            </option>
            {warehouses.map((warehouse) => (
              <option key={warehouse.id} value={warehouse.id}>
                {warehouse.name}
              </option>
            ))}
          </select>
        </label>
        <label className="block">
          <span className="mb-1 block text-[11px] font-bold uppercase tracking-wider text-slate-500">
            Kassa
          </span>
          <select
            value={cashDeskId}
            onChange={(event) => handleCashDeskChange(event.target.value)}
            disabled={!branchId || cashDesksQuery.isFetching && cashDesks.length === 0}
            className="h-10 w-full rounded-xl border border-slate-200/80 bg-white px-3 text-sm font-semibold text-slate-900 shadow-sm transition focus:border-primary-400 focus:ring-2 focus:ring-primary-500/20"
          >
            <option value="">
              {!branchId
                ? "Avval filialni tanlang"
                : cashDesksQuery.isFetching && cashDesks.length === 0
                  ? "Kassalar yuklanmoqda"
                  : cashDesks.length === 0
                    ? "Kassa yo'q"
                    : "Kassani tanlang"}
            </option>
            {cashDesks.map((cashDesk) => (
              <option key={cashDesk.id} value={cashDesk.id}>
                {cashDesk.code ? `${cashDesk.code} - ${cashDesk.name}` : cashDesk.name}
              </option>
            ))}
          </select>
        </label>
        <div className="block">
          <span className="mb-1 block text-[11px] font-bold uppercase tracking-wider text-slate-500">
            Kassa hisob
          </span>
          <div className="flex h-10 items-center rounded-xl border border-slate-200/80 bg-slate-50 px-3 text-xs font-bold text-slate-500 shadow-sm">
            {branchId ? "Filialning asosiy kassasi backend tomonidan belgilanadi" : "Avval filialni tanlang"}
          </div>
        </div>
      </div>

      {locationLoading ? (
        <div className="mb-3 flex animate-fade-in items-center gap-2 rounded-xl border border-blue-200 bg-blue-50 px-3 py-2 text-xs font-bold text-blue-700">
          <Loader2 aria-hidden="true" className="h-4 w-4 animate-spin" />
          Filial va ombor variantlari yuklanmoqda.
        </div>
      ) : locationMessage ? (
        <div className="mb-3 animate-fade-in rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs font-bold text-amber-800">
          {locationMessage}
        </div>
      ) : null}

      <div className="mb-3 rounded-xl border border-slate-200/80 bg-white px-3 py-2.5 text-xs font-bold text-slate-700 shadow-sm">
        {activeShiftId
          ? `Faol smena tanlangan: ${activeShift.data?.branch_name ?? selectedBranch?.name ?? "tanlangan filial"}`
          : "Hali faol smena tanlanmagan."}
      </div>

      <details className="mb-3 rounded-xl border border-slate-200/80 bg-white px-3 py-2.5 text-xs font-bold text-slate-600 shadow-sm">
        <summary className="cursor-pointer text-[11px] uppercase tracking-wider text-slate-500">
          Qo'lda ID / token
        </summary>
        <div className="mt-2 grid grid-cols-2 gap-2">
          <input
            value={branchId}
            onChange={(event) => setBranchId(event.target.value)}
            placeholder="Filial ID"
            className="h-10 rounded-xl border border-slate-200/80 bg-white px-3 text-sm font-semibold shadow-sm transition focus:border-primary-400 focus:ring-2 focus:ring-primary-500/20"
          />
          <input
            value={warehouseId}
            onChange={(event) => setWarehouseId(event.target.value)}
            placeholder="Ombor ID"
            className="h-10 rounded-xl border border-slate-200/80 bg-white px-3 text-sm font-semibold shadow-sm transition focus:border-primary-400 focus:ring-2 focus:ring-primary-500/20"
          />
          <input
            value={cashDeskId}
            onChange={(event) => setCashDeskId(event.target.value)}
            placeholder="Kassa ID"
            className="h-10 rounded-xl border border-slate-200/80 bg-white px-3 text-sm font-semibold shadow-sm transition focus:border-primary-400 focus:ring-2 focus:ring-primary-500/20"
          />
          <input
            value={activeShiftId}
            readOnly
            placeholder="Faol smena"
            className="h-10 rounded-xl border border-slate-200/80 bg-slate-50 px-3 text-sm font-semibold text-slate-500 shadow-sm"
          />
          <input
            type="password"
            value={authToken}
            onChange={(event) => setAuthToken(event.target.value)}
            placeholder="Bearer token"
            className="col-span-2 h-10 rounded-xl border border-slate-200/80 bg-white px-3 text-sm font-semibold shadow-sm transition focus:border-primary-400 focus:ring-2 focus:ring-primary-500/20"
          />
        </div>
      </details>

      <button
        type="submit"
        className="mb-3 flex h-10 w-full items-center justify-center gap-2 rounded-xl border border-primary-200 bg-primary-50 px-3 text-xs font-bold text-primary-700 shadow-sm transition hover:bg-primary-100 active:scale-[0.98]"
      >
        <Save aria-hidden="true" className="h-4 w-4" />
        Sessiyani saqlash
      </button>

      <div className="mb-3 grid grid-cols-2 gap-2">
        <label className="block">
          <span className="mb-1 block text-[11px] font-bold uppercase tracking-wider text-slate-500">
            Boshlang'ich naqd
          </span>
          <input
            value={openingBalance}
            onChange={(event) => setOpeningBalance(event.target.value)}
            inputMode="decimal"
            className="h-10 w-full rounded-xl border border-slate-200/80 bg-white px-3 text-sm font-semibold shadow-sm transition focus:border-primary-400 focus:ring-2 focus:ring-primary-500/20"
          />
        </label>
        <label className="block">
          <span className="mb-1 block text-[11px] font-bold uppercase tracking-wider text-slate-500">
            Yakuniy naqd
          </span>
          <input
            value={closingBalance}
            onChange={(event) => setClosingBalance(event.target.value)}
            inputMode="decimal"
            className="h-10 w-full rounded-xl border border-slate-200/80 bg-white px-3 text-sm font-semibold shadow-sm transition focus:border-primary-400 focus:ring-2 focus:ring-primary-500/20"
          />
        </label>
      </div>

      <div className="grid grid-cols-2 gap-2">
        <button
          type="button"
          onClick={handleOpenShift}
          disabled={!branchId || Boolean(activeShiftId) || shiftActionPending}
          className="flex h-10 items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-emerald-500 to-emerald-600 px-3 text-xs font-bold text-white shadow-sm shadow-emerald-500/20 transition hover:from-emerald-400 hover:to-emerald-500 active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-50 disabled:shadow-none"
        >
          {openShift.isPending ? (
            <Loader2 aria-hidden="true" className="h-4 w-4 animate-spin" />
          ) : (
            <UnlockKeyhole aria-hidden="true" className="h-4 w-4" />
          )}
          {openShift.isPending ? "Smena ochilmoqda" : "Smenani ochish"}
        </button>
        <button
          type="button"
          onClick={handleCloseShift}
          disabled={!activeShiftId || shiftActionPending}
          className="flex h-10 items-center justify-center gap-2 rounded-xl border border-amber-200 bg-amber-50 px-3 text-xs font-bold text-amber-700 shadow-sm transition hover:bg-amber-100 active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-50 disabled:shadow-none"
        >
          {closeShift.isPending ? (
            <Loader2 aria-hidden="true" className="h-4 w-4 animate-spin" />
          ) : (
            <LockKeyhole aria-hidden="true" className="h-4 w-4" />
          )}
          {closeShift.isPending ? "Smena yopilmoqda" : "Smenani yopish"}
        </button>
      </div>

      {shiftNotice ? (
        <div className="mt-3 animate-fade-in rounded-xl border border-slate-200/80 bg-white px-3 py-2.5 text-xs font-bold text-slate-700 shadow-sm">
          {shiftNotice}
        </div>
      ) : null}
    </form>
  );
}
