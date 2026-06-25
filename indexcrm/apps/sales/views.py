from django.core.exceptions import ValidationError as DjangoValidationError
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    extend_schema,
    extend_schema_view,
)
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK
from rest_framework.viewsets import ModelViewSet

from apps.accounts.models import UserRole
from apps.accounts.permissions import (
    IsReadOnlyOrOwnerAdminManager,
    filter_queryset_by_branch_scope,
    user_has_minimum_role,
)
from apps.cashier.services import require_active_cashier_shift
from apps.common.scoping import require_branch_access, require_cashbox_access
from apps.sales.exceptions import SaleErrorCode
from apps.sales.models import CustomerPayment, SaleItem, SalePayment, SaleStatus
from apps.sales.selectors import customer_queryset, refund_queryset, sale_queryset
from apps.sales.serializers import (
    CustomerPaymentSerializer,
    CustomerSerializer,
    ReceiptSerializer,
    RefundSerializer,
    SaleItemSerializer,
    SalePaymentSerializer,
    SaleSerializer,
    raise_serializer_validation,
)
from apps.sales.services import (
    build_receipt_data,
    cancel_sale,
    complete_sale,
    delete_sale_item,
)


def _bool_param(value):
    if value is None:
        return None
    return str(value).lower() in {"1", "true", "yes", "on"}


def _require_sale_access(user, sale):
    require_branch_access(user, sale.branch)
    if (
        not user_has_minimum_role(user, UserRole.MANAGER)
        and sale.cashier_id != user.id
    ):
        raise PermissionDenied(
            {
                "code": SaleErrorCode.PERMISSION_DENIED,
                "message": "You do not have access to this sale.",
                "detail": "You do not have access to this sale.",
            }
        )


@extend_schema_view(
    list=extend_schema(
        summary="List customers",
        parameters=[
            OpenApiParameter("is_active", bool, description="Filter by active status."),
            OpenApiParameter(
                "has_debt", bool, description="Return customers with positive balance."
            ),
        ],
    ),
    create=extend_schema(summary="Create customer"),
)
class CustomerViewSet(ModelViewSet):
    serializer_class = CustomerSerializer
    permission_classes = (IsReadOnlyOrOwnerAdminManager,)
    filter_backends = (SearchFilter, OrderingFilter)
    search_fields = ("full_name", "phone", "extra_phone", "address", "notes")
    ordering_fields = (
        "full_name",
        "balance",
        "bonus_balance",
        "created_at",
        "updated_at",
    )
    ordering = ("full_name",)

    def get_queryset(self):
        queryset = customer_queryset()
        is_active = _bool_param(self.request.query_params.get("is_active"))
        has_debt = _bool_param(self.request.query_params.get("has_debt"))
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active)
        if has_debt is not None:
            queryset = (
                queryset.filter(balance__gt=0)
                if has_debt
                else queryset.filter(balance=0)
            )
        return queryset


@extend_schema_view(
    list=extend_schema(
        summary="List customer payments",
        parameters=[
            OpenApiParameter("customer", str, description="Filter by customer UUID."),
            OpenApiParameter("cashbox", str, description="Filter by cashbox UUID."),
        ],
    ),
    create=extend_schema(summary="Create customer debt payment"),
)
class CustomerPaymentViewSet(ModelViewSet):
    serializer_class = CustomerPaymentSerializer
    permission_classes = (IsReadOnlyOrOwnerAdminManager,)
    filter_backends = (SearchFilter, OrderingFilter)
    search_fields = (
        "customer__full_name",
        "customer__phone",
        "cashbox__name",
        "note",
        "created_by__email",
    )
    ordering_fields = ("amount", "paid_at", "created_at")
    ordering = ("-paid_at",)

    def get_queryset(self):
        queryset = CustomerPayment.objects.select_related(
            "customer", "cashbox", "created_by"
        )
        customer = self.request.query_params.get("customer")
        cashbox = self.request.query_params.get("cashbox")
        if customer:
            queryset = queryset.filter(customer_id=customer)
        if cashbox:
            queryset = queryset.filter(cashbox_id=cashbox)
        return filter_queryset_by_branch_scope(
            queryset, self.request.user, "cashbox__branch_id"
        )

    def perform_create(self, serializer):
        cashbox = serializer.validated_data.get("cashbox")
        if cashbox is not None:
            require_cashbox_access(self.request.user, cashbox)
        serializer.save()

    def perform_update(self, serializer):
        cashbox = serializer.validated_data.get("cashbox", serializer.instance.cashbox)
        if cashbox is not None:
            require_cashbox_access(self.request.user, cashbox)
        serializer.save()


@extend_schema_view(
    list=extend_schema(
        summary="List sales",
        parameters=[
            OpenApiParameter("branch", str, description="Filter by branch UUID."),
            OpenApiParameter("warehouse", str, description="Filter by warehouse UUID."),
            OpenApiParameter(
                "cashier", str, description="Filter by cashier user UUID."
            ),
            OpenApiParameter("customer", str, description="Filter by customer UUID."),
            OpenApiParameter("status", str, description="Filter by sale status."),
            OpenApiParameter(
                "product", str, description="Filter by product UUID in sale items."
            ),
        ],
    ),
    create=extend_schema(summary="Create sale draft"),
)
class SaleViewSet(ModelViewSet):
    serializer_class = SaleSerializer
    filter_backends = (SearchFilter, OrderingFilter)
    search_fields = (
        "receipt_number",
        "customer__full_name",
        "customer__phone",
        "cashier__email",
        "items__product__name",
        "items__product__sku",
        "items__product__barcode",
    )
    ordering_fields = (
        "sale_date",
        "receipt_number",
        "total_amount",
        "paid_amount",
        "remaining_amount",
        "created_at",
    )
    ordering = ("-sale_date",)

    def get_queryset(self):
        queryset = sale_queryset()
        branch = self.request.query_params.get("branch")
        warehouse = self.request.query_params.get("warehouse")
        cashier = self.request.query_params.get("cashier")
        customer = self.request.query_params.get("customer")
        status = self.request.query_params.get("status")
        product = self.request.query_params.get("product")

        if branch:
            queryset = queryset.filter(branch_id=branch)
        if warehouse:
            queryset = queryset.filter(warehouse_id=warehouse)
        if cashier:
            queryset = queryset.filter(cashier_id=cashier)
        if customer:
            queryset = queryset.filter(customer_id=customer)
        if status:
            queryset = queryset.filter(status=status)
        if product:
            queryset = queryset.filter(items__product_id=product)
        queryset = filter_queryset_by_branch_scope(queryset, self.request.user, "branch_id")
        if not user_has_minimum_role(self.request.user, UserRole.MANAGER):
            queryset = queryset.filter(cashier=self.request.user)
        return queryset.distinct()

    def perform_destroy(self, instance):
        if instance.status != SaleStatus.DRAFT:
            raise_serializer_validation(
                DjangoValidationError({"status": "Only draft sales can be deleted."})
            )
        instance.delete()

    @extend_schema(
        summary="Complete sale",
        description="Completes a draft sale, validates stock, reduces stock with OUT movements, and creates customer debt when remaining amount is positive.",
        request=None,
        responses=SaleSerializer,
        examples=[
            OpenApiExample(
                "Completed response",
                value={
                    "status": "COMPLETED",
                    "paid_amount": "5000.00",
                    "remaining_amount": "3000.00",
                },
                response_only=True,
            )
        ],
    )
    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        sale = self.get_object()
        try:
            if sale.status != SaleStatus.COMPLETED:
                require_active_cashier_shift(cashier=request.user, branch=sale.branch)
            sale = complete_sale(sale, completed_by=request.user)
        except DjangoValidationError as error:
            raise_serializer_validation(error)
        return Response(self.get_serializer(sale).data, status=HTTP_200_OK)

    @extend_schema(summary="Cancel draft sale", request=None, responses=SaleSerializer)
    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        try:
            sale = cancel_sale(self.get_object())
        except DjangoValidationError as error:
            raise_serializer_validation(error)
        return Response(self.get_serializer(sale).data, status=HTTP_200_OK)

    @extend_schema(
        summary="Printable receipt data",
        description="Returns receipt-ready data with QR and fiscal placeholders for future fiscal integrations.",
        responses=ReceiptSerializer,
    )
    @action(detail=True, methods=["get"])
    def receipt(self, request, pk=None):
        receipt_data = build_receipt_data(self.get_object())
        serializer = ReceiptSerializer(receipt_data)
        return Response(serializer.data, status=HTTP_200_OK)


class SaleItemViewSet(ModelViewSet):
    serializer_class = SaleItemSerializer
    filter_backends = (SearchFilter, OrderingFilter)
    search_fields = (
        "sale__receipt_number",
        "product__name",
        "product__sku",
        "product__barcode",
    )
    ordering_fields = ("quantity", "price", "discount", "total_price", "created_at")
    ordering = ("-created_at",)

    def get_queryset(self):
        queryset = SaleItem.objects.select_related("sale", "product")
        sale = self.request.query_params.get("sale")
        product = self.request.query_params.get("product")
        if sale:
            queryset = queryset.filter(sale_id=sale)
        if product:
            queryset = queryset.filter(product_id=product)
        queryset = filter_queryset_by_branch_scope(
            queryset, self.request.user, "sale__branch_id"
        )
        if not user_has_minimum_role(self.request.user, UserRole.MANAGER):
            queryset = queryset.filter(sale__cashier=self.request.user)
        return queryset

    def perform_destroy(self, instance):
        try:
            delete_sale_item(instance)
        except DjangoValidationError as error:
            raise_serializer_validation(error)

    def perform_create(self, serializer):
        _require_sale_access(self.request.user, serializer.validated_data["sale"])
        serializer.save()

    def perform_update(self, serializer):
        sale = serializer.validated_data.get("sale", serializer.instance.sale)
        _require_sale_access(self.request.user, sale)
        serializer.save()


class SalePaymentViewSet(ModelViewSet):
    serializer_class = SalePaymentSerializer
    filter_backends = (SearchFilter, OrderingFilter)
    search_fields = ("sale__receipt_number", "sale__customer__full_name", "note")
    ordering_fields = ("amount", "payment_method", "paid_at", "created_at")
    ordering = ("-paid_at",)

    def get_queryset(self):
        queryset = SalePayment.objects.select_related("sale", "sale__customer")
        sale = self.request.query_params.get("sale")
        payment_method = self.request.query_params.get("payment_method")
        if sale:
            queryset = queryset.filter(sale_id=sale)
        if payment_method:
            queryset = queryset.filter(payment_method=payment_method)
        queryset = filter_queryset_by_branch_scope(
            queryset, self.request.user, "sale__branch_id"
        )
        if not user_has_minimum_role(self.request.user, UserRole.MANAGER):
            queryset = queryset.filter(sale__cashier=self.request.user)
        return queryset

    def perform_create(self, serializer):
        _require_sale_access(self.request.user, serializer.validated_data["sale"])
        serializer.save()

    def perform_update(self, serializer):
        sale = serializer.validated_data.get("sale", serializer.instance.sale)
        _require_sale_access(self.request.user, sale)
        serializer.save()


@extend_schema_view(
    list=extend_schema(
        summary="List refunds",
        parameters=[
            OpenApiParameter(
                "original_sale", str, description="Filter by original sale UUID."
            ),
            OpenApiParameter("cashier", str, description="Filter by cashier UUID."),
        ],
    ),
    create=extend_schema(summary="Create refund and restore stock"),
)
class RefundViewSet(ModelViewSet):
    serializer_class = RefundSerializer
    http_method_names = ["get", "post", "head", "options"]
    filter_backends = (SearchFilter, OrderingFilter)
    search_fields = (
        "original_sale__receipt_number",
        "cashier__email",
        "reason",
        "items__product__name",
    )
    ordering_fields = ("refund_date", "total_amount", "created_at")
    ordering = ("-refund_date",)

    def get_queryset(self):
        queryset = refund_queryset()
        original_sale = self.request.query_params.get("original_sale")
        cashier = self.request.query_params.get("cashier")
        if original_sale:
            queryset = queryset.filter(original_sale_id=original_sale)
        if cashier:
            queryset = queryset.filter(cashier_id=cashier)
        queryset = filter_queryset_by_branch_scope(
            queryset, self.request.user, "original_sale__branch_id"
        )
        if not user_has_minimum_role(self.request.user, UserRole.MANAGER):
            queryset = queryset.filter(cashier=self.request.user)
        return queryset.distinct()

    def perform_create(self, serializer):
        _require_sale_access(self.request.user, serializer.validated_data["original_sale"])
        serializer.save()
