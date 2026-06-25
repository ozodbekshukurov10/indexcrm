from django.http import HttpResponse
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsOwnerAdminOrManager
from apps.common.scoping import scoped_branch_query_value
from apps.reports.selectors import (
    best_selling_products,
    cashier_performance_report,
    customer_debts_report,
    daily_sales_summary,
    expenses_report,
    inventory_report,
    low_stock_report,
    monthly_sales_summary,
    profit_report,
    supplier_debts_report,
)
from apps.reports.serializers import (
    DailyReportQuerySerializer,
    DateRangeQuerySerializer,
    ExportQuerySerializer,
    InventoryReportQuerySerializer,
    LimitDateRangeQuerySerializer,
    LowStockReportQuerySerializer,
    MonthlyReportQuerySerializer,
)
from apps.reports.services import (
    dashboard_summary,
    debt_export,
    inventory_export,
    monthly_profit_export,
    monthly_sales_export,
)


def _validated_query(serializer_class, request):
    serializer = serializer_class(data=request.query_params)
    serializer.is_valid(raise_exception=True)
    return serializer.validated_data


def _xlsx_response(filename, content):
    response = HttpResponse(
        content,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


class ScopedReportView(APIView):
    permission_classes = (IsOwnerAdminOrManager,)

    def scoped_branch(self, request, branch):
        return scoped_branch_query_value(request.user, branch)


class DashboardSummaryView(ScopedReportView):
    @extend_schema(
        summary="Dashboard summary",
        parameters=[DailyReportQuerySerializer],
        responses=OpenApiTypes.OBJECT,
    )
    def get(self, request):
        params = _validated_query(DailyReportQuerySerializer, request)
        branch = self.scoped_branch(request, params.get("branch"))
        return Response(
            dashboard_summary(
                day=params.get("day"),
                branch=branch,
            )
        )


class DailySalesSummaryView(ScopedReportView):
    @extend_schema(
        summary="Daily sales summary",
        parameters=[DailyReportQuerySerializer],
        responses=OpenApiTypes.OBJECT,
    )
    def get(self, request):
        params = _validated_query(DailyReportQuerySerializer, request)
        branch = self.scoped_branch(request, params.get("branch"))
        return Response(
            daily_sales_summary(
                day=params.get("day"),
                branch=branch,
            )
        )


class MonthlySalesSummaryView(ScopedReportView):
    @extend_schema(
        summary="Monthly sales summary",
        parameters=[MonthlyReportQuerySerializer],
        responses=OpenApiTypes.OBJECT,
    )
    def get(self, request):
        params = _validated_query(MonthlyReportQuerySerializer, request)
        params["branch"] = self.scoped_branch(request, params.get("branch"))
        return Response(monthly_sales_summary(**params))


class ProfitReportView(ScopedReportView):
    @extend_schema(
        summary="Profit report",
        parameters=[DateRangeQuerySerializer],
        responses=OpenApiTypes.OBJECT,
    )
    def get(self, request):
        params = _validated_query(DateRangeQuerySerializer, request)
        params["branch"] = self.scoped_branch(request, params.get("branch"))
        return Response(profit_report(**params))


class ExpensesReportView(ScopedReportView):
    @extend_schema(
        summary="Expenses report",
        parameters=[DateRangeQuerySerializer],
        responses=OpenApiTypes.OBJECT,
    )
    def get(self, request):
        params = _validated_query(DateRangeQuerySerializer, request)
        params["branch"] = self.scoped_branch(request, params.get("branch"))
        return Response(expenses_report(**params))


class InventoryReportView(ScopedReportView):
    @extend_schema(
        summary="Inventory report",
        parameters=[InventoryReportQuerySerializer],
        responses=OpenApiTypes.OBJECT,
    )
    def get(self, request):
        params = _validated_query(InventoryReportQuerySerializer, request)
        params["branch"] = self.scoped_branch(request, params.get("branch"))
        return Response(inventory_report(**params))


class LowStockReportView(ScopedReportView):
    @extend_schema(
        summary="Low stock report",
        parameters=[LowStockReportQuerySerializer],
        responses=OpenApiTypes.OBJECT,
    )
    def get(self, request):
        params = _validated_query(LowStockReportQuerySerializer, request)
        params["branch"] = self.scoped_branch(request, params.get("branch"))
        return Response(low_stock_report(**params))


class BestSellingProductsReportView(ScopedReportView):
    @extend_schema(
        summary="Best-selling products report",
        parameters=[LimitDateRangeQuerySerializer],
        responses=OpenApiTypes.OBJECT,
    )
    def get(self, request):
        params = _validated_query(LimitDateRangeQuerySerializer, request)
        params["branch"] = self.scoped_branch(request, params.get("branch"))
        return Response(best_selling_products(**params))


class CustomerDebtsReportView(ScopedReportView):
    @extend_schema(summary="Customer debts report", responses=OpenApiTypes.OBJECT)
    def get(self, request):
        return Response(customer_debts_report())


class SupplierDebtsReportView(ScopedReportView):
    @extend_schema(summary="Supplier debts report", responses=OpenApiTypes.OBJECT)
    def get(self, request):
        return Response(supplier_debts_report())


class CashierPerformanceReportView(ScopedReportView):
    @extend_schema(
        summary="Cashier performance report",
        parameters=[DateRangeQuerySerializer],
        responses=OpenApiTypes.OBJECT,
    )
    def get(self, request):
        params = _validated_query(DateRangeQuerySerializer, request)
        params["branch"] = self.scoped_branch(request, params.get("branch"))
        return Response(cashier_performance_report(**params))


class MonthlySalesExportView(ScopedReportView):
    @extend_schema(
        summary="Export monthly sales report as Excel",
        parameters=[ExportQuerySerializer],
        responses=OpenApiTypes.BINARY,
    )
    def get(self, request):
        params = _validated_query(ExportQuerySerializer, request)
        params["branch"] = self.scoped_branch(request, params.get("branch"))
        filename, content = monthly_sales_export(**params)
        return _xlsx_response(filename, content)


class MonthlyProfitExportView(ScopedReportView):
    @extend_schema(
        summary="Export monthly profit report as Excel",
        parameters=[ExportQuerySerializer],
        responses=OpenApiTypes.BINARY,
    )
    def get(self, request):
        params = _validated_query(ExportQuerySerializer, request)
        params["branch"] = self.scoped_branch(request, params.get("branch"))
        filename, content = monthly_profit_export(**params)
        return _xlsx_response(filename, content)


class InventoryExportView(ScopedReportView):
    @extend_schema(
        summary="Export inventory report as Excel",
        parameters=[InventoryReportQuerySerializer],
        responses=OpenApiTypes.BINARY,
    )
    def get(self, request):
        params = _validated_query(InventoryReportQuerySerializer, request)
        params["branch"] = self.scoped_branch(request, params.get("branch"))
        filename, content = inventory_export(**params)
        return _xlsx_response(filename, content)


class DebtExportView(ScopedReportView):
    @extend_schema(
        summary="Export debt report as Excel",
        responses=OpenApiTypes.BINARY,
    )
    def get(self, request):
        filename, content = debt_export()
        return _xlsx_response(filename, content)
