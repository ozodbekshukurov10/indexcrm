import { apiRequest } from "./client";

export type DashboardSummary = {
  today_sales?: Record<string, unknown>;
  sales?: Record<string, unknown>;
  today_profit: Record<string, unknown> | string | number;
  total_expenses: string | number;
  total_debt: Record<string, unknown>;
  low_stock_count: number;
  best_selling_products: Array<Record<string, unknown>>;
  recent_sales: Array<Record<string, unknown>>;
  cashbox_summary: Array<Record<string, unknown>>;
};

export type DateRangeParams = {
  date_from?: string;
  date_to?: string;
  branch?: string;
};

export function getDashboardSummary(day?: string, branch?: string) {
  return apiRequest<DashboardSummary>(
    "/reports/dashboard/",
    {},
    { day, branch },
  );
}

export function getSalesReport(params: DateRangeParams) {
  return apiRequest<Record<string, unknown>>(
    "/reports/daily-sales/",
    {},
    {
      day: params.date_to,
      branch: params.branch,
    },
  );
}

export function getProfitReport(params: DateRangeParams) {
  return apiRequest<Record<string, unknown>>("/reports/profit/", {}, params);
}

export function getExpensesReport(params: DateRangeParams) {
  return apiRequest<Record<string, unknown>>("/reports/expenses/", {}, params);
}

export function getInventoryReport(params: { branch?: string; warehouse?: string }) {
  return apiRequest<Record<string, unknown>>("/reports/inventory/", {}, params);
}

export function getLowStockReport(params: { branch?: string; warehouse?: string }) {
  return apiRequest<Record<string, unknown>>("/reports/low-stock/", {}, params);
}

export function getBestSellingProducts(params: DateRangeParams & { limit?: number }) {
  return apiRequest<Array<Record<string, unknown>>>(
    "/reports/best-selling-products/",
    {},
    params,
  );
}

export function getCustomerDebts() {
  return apiRequest<Array<Record<string, unknown>>>("/reports/customer-debts/");
}

export function getSupplierDebts() {
  return apiRequest<Array<Record<string, unknown>>>("/reports/supplier-debts/");
}

export function getCashierPerformance(params: DateRangeParams) {
  return apiRequest<Array<Record<string, unknown>>>(
    "/reports/cashier-performance/",
    {},
    params,
  );
}
