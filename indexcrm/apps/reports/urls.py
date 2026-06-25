from django.urls import path

from apps.reports.views import (
    BestSellingProductsReportView,
    CashierPerformanceReportView,
    CustomerDebtsReportView,
    DailySalesSummaryView,
    DashboardSummaryView,
    DebtExportView,
    ExpensesReportView,
    InventoryExportView,
    InventoryReportView,
    LowStockReportView,
    MonthlyProfitExportView,
    MonthlySalesExportView,
    MonthlySalesSummaryView,
    ProfitReportView,
    SupplierDebtsReportView,
)

urlpatterns = [
    path(
        "reports/dashboard/", DashboardSummaryView.as_view(), name="reports-dashboard"
    ),
    path(
        "reports/daily-sales/",
        DailySalesSummaryView.as_view(),
        name="reports-daily-sales",
    ),
    path(
        "reports/monthly-sales/",
        MonthlySalesSummaryView.as_view(),
        name="reports-monthly-sales",
    ),
    path("reports/profit/", ProfitReportView.as_view(), name="reports-profit"),
    path("reports/expenses/", ExpensesReportView.as_view(), name="reports-expenses"),
    path("reports/inventory/", InventoryReportView.as_view(), name="reports-inventory"),
    path("reports/low-stock/", LowStockReportView.as_view(), name="reports-low-stock"),
    path(
        "reports/best-selling-products/",
        BestSellingProductsReportView.as_view(),
        name="reports-best-selling-products",
    ),
    path(
        "reports/customer-debts/",
        CustomerDebtsReportView.as_view(),
        name="reports-customer-debts",
    ),
    path(
        "reports/supplier-debts/",
        SupplierDebtsReportView.as_view(),
        name="reports-supplier-debts",
    ),
    path(
        "reports/cashier-performance/",
        CashierPerformanceReportView.as_view(),
        name="reports-cashier-performance",
    ),
    path(
        "reports/export/monthly-sales/",
        MonthlySalesExportView.as_view(),
        name="reports-export-monthly-sales",
    ),
    path(
        "reports/export/monthly-profit/",
        MonthlyProfitExportView.as_view(),
        name="reports-export-monthly-profit",
    ),
    path(
        "reports/export/inventory/",
        InventoryExportView.as_view(),
        name="reports-export-inventory",
    ),
    path(
        "reports/export/debts/", DebtExportView.as_view(), name="reports-export-debts"
    ),
]
