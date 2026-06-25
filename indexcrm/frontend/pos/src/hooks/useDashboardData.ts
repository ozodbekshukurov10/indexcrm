import { useQuery } from "@tanstack/react-query";

import { getCurrentUser } from "@/services/api/accounts";
import { listCashierShifts } from "@/services/api/cashierShifts";
import { listCustomers } from "@/services/api/customers";
import { listCashBoxes, listExpenses } from "@/services/api/finance";
import { listStocks } from "@/services/api/inventory";
import { listProducts } from "@/services/api/products";
import {
  getBestSellingProducts,
  getCashierPerformance,
  getCustomerDebts,
  getDashboardSummary,
  getExpensesReport,
  getInventoryReport,
  getLowStockReport,
  getProfitReport,
  getSalesReport,
  getSupplierDebts,
} from "@/services/api/reports";
import { listSales } from "@/services/api/sales";
import { listSuppliers } from "@/services/api/suppliers";

export function useDashboardSummary() {
  return useQuery({
    queryKey: ["dashboard-summary"],
    queryFn: () => getDashboardSummary(),
  });
}

export function useSalesDashboard(dateFrom?: string, dateTo?: string) {
  return useQuery({
    queryKey: ["dashboard-sales", dateFrom, dateTo],
    queryFn: async () => {
      const [sales, report, bestSelling] = await Promise.all([
        listSales({ ordering: "-sale_date" }),
        getSalesReport({ date_from: dateFrom, date_to: dateTo }),
        getBestSellingProducts({ date_from: dateFrom, date_to: dateTo, limit: 10 }),
      ]);
      return { sales, report, bestSelling };
    },
  });
}

export function useProductsDashboard(search?: string) {
  return useQuery({
    queryKey: ["dashboard-products", search],
    queryFn: () => listProducts({ search }),
  });
}

export function useInventoryDashboard() {
  return useQuery({
    queryKey: ["dashboard-inventory"],
    queryFn: async () => {
      const [stocks, report, lowStock] = await Promise.all([
        listStocks({}),
        getInventoryReport({}),
        getLowStockReport({}),
      ]);
      return { stocks, report, lowStock };
    },
  });
}

export function useCustomersDashboard(search?: string) {
  return useQuery({
    queryKey: ["dashboard-customers", search],
    queryFn: async () => {
      const [customers, debts] = await Promise.all([
        listCustomers(search),
        getCustomerDebts(),
      ]);
      return { customers, debts };
    },
  });
}

export function useSuppliersDashboard(search?: string) {
  return useQuery({
    queryKey: ["dashboard-suppliers", search],
    queryFn: async () => {
      const [suppliers, debts] = await Promise.all([
        listSuppliers(search),
        getSupplierDebts(),
      ]);
      return { suppliers, debts };
    },
  });
}

export function useFinanceDashboard(dateFrom?: string, dateTo?: string) {
  return useQuery({
    queryKey: ["dashboard-finance", dateFrom, dateTo],
    queryFn: async () => {
      const [profit, expensesReport, cashboxes, expenses] = await Promise.all([
        getProfitReport({ date_from: dateFrom, date_to: dateTo }),
        getExpensesReport({ date_from: dateFrom, date_to: dateTo }),
        listCashBoxes(),
        listExpenses(),
      ]);
      return { profit, expensesReport, cashboxes, expenses };
    },
  });
}

export function useReportsDashboard(dateFrom?: string, dateTo?: string) {
  return useQuery({
    queryKey: ["dashboard-reports", dateFrom, dateTo],
    queryFn: async () => {
      const [profit, expenses, bestSelling, customers, suppliers] =
        await Promise.all([
          getProfitReport({ date_from: dateFrom, date_to: dateTo }),
          getExpensesReport({ date_from: dateFrom, date_to: dateTo }),
          getBestSellingProducts({ date_from: dateFrom, date_to: dateTo, limit: 10 }),
          getCustomerDebts(),
          getSupplierDebts(),
        ]);
      return { profit, expenses, bestSelling, customers, suppliers };
    },
  });
}

export function useCashierActivityDashboard(dateFrom?: string, dateTo?: string) {
  return useQuery({
    queryKey: ["dashboard-cashier-activity", dateFrom, dateTo],
    queryFn: async () => {
      const [performance, shifts] = await Promise.all([
        getCashierPerformance({ date_from: dateFrom, date_to: dateTo }),
        listCashierShifts({}),
      ]);
      return { performance, shifts };
    },
  });
}

export function useProfileDashboard() {
  return useQuery({
    queryKey: ["dashboard-profile"],
    queryFn: () => getCurrentUser(),
  });
}
