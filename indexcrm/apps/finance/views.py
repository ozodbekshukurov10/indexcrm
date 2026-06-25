from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK
from rest_framework.viewsets import ModelViewSet

from apps.accounts.permissions import (
    IsOwnerAdminOrManager,
    filter_queryset_by_branch_scope,
)
from apps.common.scoping import (
    require_branch_access,
    require_cashbox_access,
    scoped_branch_query_value,
)
from apps.finance.models import ExpenseCategory
from apps.finance.selectors import (
    cash_transaction_queryset,
    cashbox_queryset,
    daily_closing_queryset,
    expense_queryset,
    get_cashflow_summary,
    get_cashier_performance,
    get_customer_debts,
    get_expense_statistics,
    get_supplier_debts,
    get_total_profit,
    income_queryset,
)
from apps.finance.serializers import (
    CashBoxSerializer,
    CashboxTransferSerializer,
    CashTransactionSerializer,
    DailyClosingSerializer,
    ExpenseCategorySerializer,
    ExpenseSerializer,
    IncomeSerializer,
)
from apps.finance.services import calculate_cashbox_balance


def _bool_param(value):
    if value is None:
        return None
    return str(value).lower() in {"1", "true", "yes", "on"}


@extend_schema_view(
    list=extend_schema(
        summary="List cashboxes",
        parameters=[
            OpenApiParameter("branch", str, description="Filter by branch UUID."),
            OpenApiParameter("is_active", bool, description="Filter active cashboxes."),
        ],
    ),
    create=extend_schema(summary="Create cashbox"),
)
class CashBoxViewSet(ModelViewSet):
    serializer_class = CashBoxSerializer
    permission_classes = (IsOwnerAdminOrManager,)
    filter_backends = (SearchFilter, OrderingFilter)
    search_fields = ("name", "branch__name", "branch__store__name")
    ordering_fields = ("name", "current_balance", "created_at", "updated_at")
    ordering = ("branch__name", "name")

    def get_queryset(self):
        queryset = cashbox_queryset()
        branch = self.request.query_params.get("branch")
        is_active = _bool_param(self.request.query_params.get("is_active"))
        if branch:
            queryset = queryset.filter(branch_id=branch)
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active)
        return filter_queryset_by_branch_scope(queryset, self.request.user, "branch_id")

    def perform_create(self, serializer):
        require_branch_access(self.request.user, serializer.validated_data["branch"])
        serializer.save()

    def perform_update(self, serializer):
        branch = serializer.validated_data.get("branch", serializer.instance.branch)
        require_branch_access(self.request.user, branch)
        serializer.save()

    @extend_schema(summary="Calculate cashbox balance")
    @action(detail=True, methods=["get"])
    def balance(self, request, pk=None):
        cashbox = self.get_object()
        balance = calculate_cashbox_balance(cashbox)
        return Response(
            {"cashbox": str(cashbox.id), "balance": balance}, status=HTTP_200_OK
        )

    @extend_schema(
        summary="Transfer money between cashboxes",
        request=CashboxTransferSerializer,
        responses=CashTransactionSerializer(many=True),
    )
    @action(detail=True, methods=["post"])
    def transfer(self, request, pk=None):
        cashbox = self.get_object()
        serializer = CashboxTransferSerializer(
            data=request.data,
            context={"source_cashbox": cashbox, "request": request},
        )
        serializer.is_valid(raise_exception=True)
        require_cashbox_access(request.user, serializer.validated_data["target_cashbox"])
        transactions = serializer.save()
        response_serializer = CashTransactionSerializer(transactions, many=True)
        return Response(response_serializer.data, status=HTTP_200_OK)


@extend_schema_view(
    list=extend_schema(
        summary="List cash transactions",
        parameters=[
            OpenApiParameter("cashbox", str, description="Filter by cashbox UUID."),
            OpenApiParameter("branch", str, description="Filter by branch UUID."),
            OpenApiParameter("transaction_type", str, description="Filter by type."),
            OpenApiParameter(
                "reference_type", str, description="Filter by reference type."
            ),
        ],
    ),
    create=extend_schema(summary="Create cashbox adjustment"),
)
class CashTransactionViewSet(ModelViewSet):
    serializer_class = CashTransactionSerializer
    permission_classes = (IsOwnerAdminOrManager,)
    http_method_names = ["get", "post", "patch", "head", "options"]
    filter_backends = (SearchFilter, OrderingFilter)
    search_fields = (
        "cashbox__name",
        "cashbox__branch__name",
        "reference_type",
        "note",
        "created_by__email",
    )
    ordering_fields = ("amount", "transaction_type", "created_at")
    ordering = ("-created_at",)

    def get_queryset(self):
        queryset = cash_transaction_queryset()
        cashbox = self.request.query_params.get("cashbox")
        branch = self.request.query_params.get("branch")
        transaction_type = self.request.query_params.get("transaction_type")
        reference_type = self.request.query_params.get("reference_type")

        if cashbox:
            queryset = queryset.filter(cashbox_id=cashbox)
        if branch:
            queryset = queryset.filter(cashbox__branch_id=branch)
        if transaction_type:
            queryset = queryset.filter(transaction_type=transaction_type)
        if reference_type:
            queryset = queryset.filter(reference_type=reference_type)
        return filter_queryset_by_branch_scope(
            queryset, self.request.user, "cashbox__branch_id"
        )

    def perform_create(self, serializer):
        require_cashbox_access(self.request.user, serializer.validated_data["cashbox"])
        serializer.save()

    def perform_update(self, serializer):
        cashbox = serializer.validated_data.get("cashbox", serializer.instance.cashbox)
        require_cashbox_access(self.request.user, cashbox)
        serializer.save()

    @extend_schema(
        summary="Cashflow summary",
        parameters=[
            OpenApiParameter("branch", str, description="Filter by branch UUID."),
            OpenApiParameter("date_from", str, description="Start date YYYY-MM-DD."),
            OpenApiParameter("date_to", str, description="End date YYYY-MM-DD."),
        ],
    )
    @action(detail=False, methods=["get"], url_path="cashflow-summary")
    def cashflow_summary(self, request):
        branch = scoped_branch_query_value(request.user, request.query_params.get("branch"))
        summary = get_cashflow_summary(
            date_from=request.query_params.get("date_from"),
            date_to=request.query_params.get("date_to"),
            branch=branch,
        )
        return Response(summary, status=HTTP_200_OK)

    @extend_schema(summary="Customer debts")
    @action(detail=False, methods=["get"], url_path="customer-debts")
    def customer_debts(self, request):
        debts = get_customer_debts().values("id", "full_name", "phone", "balance")
        return Response(list(debts), status=HTTP_200_OK)

    @extend_schema(summary="Supplier debts")
    @action(detail=False, methods=["get"], url_path="supplier-debts")
    def supplier_debts(self, request):
        debts = get_supplier_debts().values(
            "id",
            "company_name",
            "full_name",
            "phone",
            "balance",
        )
        return Response(list(debts), status=HTTP_200_OK)


class ExpenseCategoryViewSet(ModelViewSet):
    serializer_class = ExpenseCategorySerializer
    permission_classes = (IsOwnerAdminOrManager,)
    queryset = ExpenseCategory.objects.all()
    filter_backends = (SearchFilter, OrderingFilter)
    search_fields = ("name", "description")
    ordering_fields = ("name", "created_at", "updated_at")
    ordering = ("name",)


@extend_schema_view(
    list=extend_schema(
        summary="List expenses",
        parameters=[
            OpenApiParameter("cashbox", str, description="Filter by cashbox UUID."),
            OpenApiParameter("branch", str, description="Filter by branch UUID."),
            OpenApiParameter("category", str, description="Filter by category UUID."),
        ],
    ),
    create=extend_schema(summary="Create expense and cash transaction"),
)
class ExpenseViewSet(ModelViewSet):
    serializer_class = ExpenseSerializer
    permission_classes = (IsOwnerAdminOrManager,)
    http_method_names = ["get", "post", "patch", "head", "options"]
    filter_backends = (SearchFilter, OrderingFilter)
    search_fields = (
        "cashbox__name",
        "cashbox__branch__name",
        "category__name",
        "note",
        "created_by__email",
    )
    ordering_fields = ("amount", "expense_date", "created_at")
    ordering = ("-expense_date",)

    def get_queryset(self):
        queryset = expense_queryset()
        cashbox = self.request.query_params.get("cashbox")
        branch = self.request.query_params.get("branch")
        category = self.request.query_params.get("category")
        if cashbox:
            queryset = queryset.filter(cashbox_id=cashbox)
        if branch:
            queryset = queryset.filter(cashbox__branch_id=branch)
        if category:
            queryset = queryset.filter(category_id=category)
        return filter_queryset_by_branch_scope(
            queryset, self.request.user, "cashbox__branch_id"
        )

    def perform_create(self, serializer):
        require_cashbox_access(self.request.user, serializer.validated_data["cashbox"])
        serializer.save()

    def perform_update(self, serializer):
        cashbox = serializer.validated_data.get("cashbox", serializer.instance.cashbox)
        require_cashbox_access(self.request.user, cashbox)
        serializer.save()

    @extend_schema(summary="Expense statistics by category")
    @action(detail=False, methods=["get"], url_path="statistics")
    def statistics(self, request):
        branch = scoped_branch_query_value(request.user, request.query_params.get("branch"))
        data = get_expense_statistics(
            date_from=request.query_params.get("date_from"),
            date_to=request.query_params.get("date_to"),
            branch=branch,
        )
        return Response(list(data), status=HTTP_200_OK)


@extend_schema_view(
    list=extend_schema(
        summary="List incomes",
        parameters=[
            OpenApiParameter("cashbox", str, description="Filter by cashbox UUID."),
            OpenApiParameter("branch", str, description="Filter by branch UUID."),
            OpenApiParameter("source", str, description="Filter by income source."),
        ],
    ),
    create=extend_schema(summary="Create income and cash transaction"),
)
class IncomeViewSet(ModelViewSet):
    serializer_class = IncomeSerializer
    permission_classes = (IsOwnerAdminOrManager,)
    http_method_names = ["get", "post", "patch", "head", "options"]
    filter_backends = (SearchFilter, OrderingFilter)
    search_fields = ("cashbox__name", "cashbox__branch__name", "source", "note")
    ordering_fields = ("amount", "income_date", "created_at")
    ordering = ("-income_date",)

    def get_queryset(self):
        queryset = income_queryset()
        cashbox = self.request.query_params.get("cashbox")
        branch = self.request.query_params.get("branch")
        source = self.request.query_params.get("source")
        if cashbox:
            queryset = queryset.filter(cashbox_id=cashbox)
        if branch:
            queryset = queryset.filter(cashbox__branch_id=branch)
        if source:
            queryset = queryset.filter(source__icontains=source)
        return filter_queryset_by_branch_scope(
            queryset, self.request.user, "cashbox__branch_id"
        )

    def perform_create(self, serializer):
        require_cashbox_access(self.request.user, serializer.validated_data["cashbox"])
        serializer.save()

    def perform_update(self, serializer):
        cashbox = serializer.validated_data.get("cashbox", serializer.instance.cashbox)
        require_cashbox_access(self.request.user, cashbox)
        serializer.save()


@extend_schema_view(
    list=extend_schema(
        summary="List daily closings",
        parameters=[
            OpenApiParameter("branch", str, description="Filter by branch UUID."),
            OpenApiParameter("cashier", str, description="Filter by cashier UUID."),
        ],
    ),
    create=extend_schema(summary="Close daily cashier shift"),
)
class DailyClosingViewSet(ModelViewSet):
    serializer_class = DailyClosingSerializer
    permission_classes = (IsOwnerAdminOrManager,)
    http_method_names = ["get", "post", "head", "options"]
    filter_backends = (SearchFilter, OrderingFilter)
    search_fields = ("branch__name", "branch__store__name", "cashier__email")
    ordering_fields = (
        "closed_at",
        "total_sales",
        "total_expenses",
        "total_income",
        "difference",
    )
    ordering = ("-closed_at",)

    def get_queryset(self):
        queryset = daily_closing_queryset()
        branch = self.request.query_params.get("branch")
        cashier = self.request.query_params.get("cashier")
        if branch:
            queryset = queryset.filter(branch_id=branch)
        if cashier:
            queryset = queryset.filter(cashier_id=cashier)
        return filter_queryset_by_branch_scope(queryset, self.request.user, "branch_id")

    def perform_create(self, serializer):
        require_branch_access(self.request.user, serializer.validated_data["branch"])
        serializer.save()

    @extend_schema(summary="Profit summary")
    @action(detail=False, methods=["get"], url_path="profit-summary")
    def profit_summary(self, request):
        branch = scoped_branch_query_value(request.user, request.query_params.get("branch"))
        data = get_total_profit(
            date_from=request.query_params.get("date_from"),
            date_to=request.query_params.get("date_to"),
            branch=branch,
        )
        return Response(data, status=HTTP_200_OK)

    @extend_schema(summary="Cashier performance")
    @action(detail=False, methods=["get"], url_path="cashier-performance")
    def cashier_performance(self, request):
        branch = scoped_branch_query_value(request.user, request.query_params.get("branch"))
        data = get_cashier_performance(
            date_from=request.query_params.get("date_from"),
            date_to=request.query_params.get("date_to"),
            branch=branch,
        )
        return Response(list(data), status=HTTP_200_OK)
