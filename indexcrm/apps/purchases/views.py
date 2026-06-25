from django.core.exceptions import ValidationError as DjangoValidationError
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    extend_schema,
    extend_schema_view,
)
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK
from rest_framework.viewsets import ModelViewSet

from apps.accounts.permissions import (
    IsReadOnlyOrOwnerAdminManager,
    filter_queryset_by_branch_scope,
)
from apps.common.scoping import require_cashbox_access, require_warehouse_access
from apps.purchases.models import (
    PurchaseItem,
    PurchasePayment,
    PurchaseStatus,
    SupplierContact,
    SupplierPayment,
)
from apps.purchases.selectors import purchase_queryset, supplier_queryset
from apps.purchases.serializers import (
    PurchaseItemSerializer,
    PurchasePaymentSerializer,
    PurchaseSerializer,
    SupplierContactSerializer,
    SupplierPaymentSerializer,
    SupplierSerializer,
    raise_serializer_validation,
)
from apps.purchases.services import (
    cancel_purchase,
    confirm_purchase,
    delete_purchase_item,
)


def _bool_param(value):
    if value is None:
        return None
    return str(value).lower() in {"1", "true", "yes", "on"}


def _require_purchase_access(user, purchase):
    require_warehouse_access(user, purchase.warehouse)


@extend_schema_view(
    list=extend_schema(
        summary="List suppliers",
        parameters=[
            OpenApiParameter("is_active", bool, description="Filter by active status."),
            OpenApiParameter(
                "has_debt", bool, description="Return suppliers with positive balance."
            ),
        ],
    ),
    create=extend_schema(summary="Create supplier"),
    retrieve=extend_schema(summary="Retrieve supplier"),
    update=extend_schema(summary="Update supplier"),
    partial_update=extend_schema(summary="Partially update supplier"),
    destroy=extend_schema(summary="Soft delete supplier"),
)
class SupplierViewSet(ModelViewSet):
    serializer_class = SupplierSerializer
    permission_classes = (IsReadOnlyOrOwnerAdminManager,)
    filter_backends = (SearchFilter, OrderingFilter)
    search_fields = (
        "company_name",
        "full_name",
        "phone",
        "extra_phone",
        "email",
        "inn_or_tax_number",
    )
    ordering_fields = ("company_name", "balance", "created_at", "updated_at")
    ordering = ("company_name",)

    def get_queryset(self):
        queryset = supplier_queryset()
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


@extend_schema_view(list=extend_schema(summary="List supplier contacts"))
class SupplierContactViewSet(ModelViewSet):
    serializer_class = SupplierContactSerializer
    permission_classes = (IsReadOnlyOrOwnerAdminManager,)
    filter_backends = (SearchFilter, OrderingFilter)
    search_fields = (
        "full_name",
        "position",
        "phone",
        "email",
        "supplier__company_name",
    )
    ordering_fields = ("full_name", "created_at", "updated_at")
    ordering = ("full_name",)

    def get_queryset(self):
        queryset = SupplierContact.objects.select_related("supplier")
        supplier = self.request.query_params.get("supplier")
        if supplier:
            queryset = queryset.filter(supplier_id=supplier)
        return queryset


@extend_schema_view(
    list=extend_schema(
        summary="List supplier payments",
        parameters=[
            OpenApiParameter("supplier", str, description="Filter by supplier UUID."),
            OpenApiParameter("cashbox", str, description="Filter by cashbox UUID."),
        ],
    ),
    create=extend_schema(summary="Create supplier payment"),
)
class SupplierPaymentViewSet(ModelViewSet):
    serializer_class = SupplierPaymentSerializer
    permission_classes = (IsReadOnlyOrOwnerAdminManager,)
    filter_backends = (SearchFilter, OrderingFilter)
    search_fields = (
        "supplier__company_name",
        "supplier__full_name",
        "cashbox__name",
        "note",
        "created_by__email",
    )
    ordering_fields = ("amount", "paid_at", "created_at")
    ordering = ("-paid_at",)

    def get_queryset(self):
        queryset = SupplierPayment.objects.select_related(
            "supplier", "cashbox", "created_by"
        )
        supplier = self.request.query_params.get("supplier")
        cashbox = self.request.query_params.get("cashbox")
        if supplier:
            queryset = queryset.filter(supplier_id=supplier)
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
        summary="List purchases",
        parameters=[
            OpenApiParameter("supplier", str, description="Filter by supplier UUID."),
            OpenApiParameter("warehouse", str, description="Filter by warehouse UUID."),
            OpenApiParameter("status", str, description="Filter by purchase status."),
            OpenApiParameter(
                "product", str, description="Filter by product UUID in items."
            ),
        ],
    ),
    create=extend_schema(summary="Create purchase draft"),
    retrieve=extend_schema(summary="Retrieve purchase"),
    update=extend_schema(summary="Update purchase draft"),
    partial_update=extend_schema(summary="Partially update purchase draft"),
    destroy=extend_schema(summary="Soft delete purchase draft"),
)
class PurchaseViewSet(ModelViewSet):
    serializer_class = PurchaseSerializer
    permission_classes = (IsReadOnlyOrOwnerAdminManager,)
    filter_backends = (SearchFilter, OrderingFilter)
    search_fields = (
        "invoice_number",
        "supplier__company_name",
        "supplier__full_name",
        "items__product__name",
        "items__product__sku",
        "items__product__barcode",
    )
    ordering_fields = (
        "purchase_date",
        "invoice_number",
        "subtotal",
        "total_amount",
        "paid_amount",
        "remaining_amount",
        "created_at",
    )
    ordering = ("-purchase_date",)

    def get_queryset(self):
        queryset = purchase_queryset()
        supplier = self.request.query_params.get("supplier")
        warehouse = self.request.query_params.get("warehouse")
        status = self.request.query_params.get("status")
        product = self.request.query_params.get("product")

        if supplier:
            queryset = queryset.filter(supplier_id=supplier)
        if warehouse:
            queryset = queryset.filter(warehouse_id=warehouse)
        if status:
            queryset = queryset.filter(status=status)
        if product:
            queryset = queryset.filter(items__product_id=product)

        queryset = filter_queryset_by_branch_scope(
            queryset, self.request.user, "warehouse__branch_id"
        )
        return queryset.distinct()

    def perform_create(self, serializer):
        require_warehouse_access(self.request.user, serializer.validated_data["warehouse"])
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        warehouse = serializer.validated_data.get(
            "warehouse", serializer.instance.warehouse
        )
        require_warehouse_access(self.request.user, warehouse)
        serializer.save()

    def perform_destroy(self, instance):
        if instance.status != PurchaseStatus.DRAFT:
            raise_serializer_validation(
                DjangoValidationError(
                    {"status": "Only draft purchases can be deleted."}
                )
            )
        instance.delete()

    @extend_schema(
        summary="Confirm purchase",
        description="Confirms a draft purchase, increases warehouse stock, creates IN stock movements, and increases supplier debt by the remaining amount.",
        request=None,
        responses=PurchaseSerializer,
        examples=[
            OpenApiExample(
                "Confirmed response",
                value={"status": "CONFIRMED", "remaining_amount": "20000.00"},
                response_only=True,
            )
        ],
    )
    @action(detail=True, methods=["post"])
    def confirm(self, request, pk=None):
        try:
            purchase = confirm_purchase(self.get_object(), confirmed_by=request.user)
        except DjangoValidationError as error:
            raise_serializer_validation(error)
        serializer = self.get_serializer(purchase)
        return Response(serializer.data, status=HTTP_200_OK)

    @extend_schema(
        summary="Cancel purchase",
        description="Cancels a purchase. Confirmed purchases roll back stock through OUT stock movements and reduce supplier debt by the remaining amount.",
        request=None,
        responses=PurchaseSerializer,
    )
    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        try:
            purchase = cancel_purchase(self.get_object(), cancelled_by=request.user)
        except DjangoValidationError as error:
            raise_serializer_validation(error)
        serializer = self.get_serializer(purchase)
        return Response(serializer.data, status=HTTP_200_OK)


class PurchaseItemViewSet(ModelViewSet):
    serializer_class = PurchaseItemSerializer
    permission_classes = (IsReadOnlyOrOwnerAdminManager,)
    filter_backends = (SearchFilter, OrderingFilter)
    search_fields = (
        "purchase__invoice_number",
        "product__name",
        "product__sku",
        "product__barcode",
    )
    ordering_fields = (
        "quantity",
        "purchase_price",
        "total_price",
        "expiry_date",
        "created_at",
    )
    ordering = ("-created_at",)

    def get_queryset(self):
        queryset = PurchaseItem.objects.select_related("purchase", "product")
        purchase = self.request.query_params.get("purchase")
        product = self.request.query_params.get("product")

        if purchase:
            queryset = queryset.filter(purchase_id=purchase)
        if product:
            queryset = queryset.filter(product_id=product)

        return filter_queryset_by_branch_scope(
            queryset, self.request.user, "purchase__warehouse__branch_id"
        )

    def perform_create(self, serializer):
        _require_purchase_access(self.request.user, serializer.validated_data["purchase"])
        serializer.save()

    def perform_update(self, serializer):
        purchase = serializer.validated_data.get(
            "purchase", serializer.instance.purchase
        )
        _require_purchase_access(self.request.user, purchase)
        serializer.save()

    def perform_destroy(self, instance):
        try:
            delete_purchase_item(instance)
        except DjangoValidationError as error:
            raise_serializer_validation(error)


@extend_schema_view(
    list=extend_schema(
        summary="List purchase payments",
        parameters=[
            OpenApiParameter("purchase", str, description="Filter by purchase UUID.")
        ],
    ),
    create=extend_schema(summary="Create purchase payment"),
)
class PurchasePaymentViewSet(ModelViewSet):
    serializer_class = PurchasePaymentSerializer
    permission_classes = (IsReadOnlyOrOwnerAdminManager,)
    filter_backends = (SearchFilter, OrderingFilter)
    search_fields = (
        "purchase__invoice_number",
        "purchase__supplier__company_name",
        "note",
        "created_by__email",
    )
    ordering_fields = ("amount", "paid_at", "created_at")
    ordering = ("-paid_at",)

    def get_queryset(self):
        queryset = PurchasePayment.objects.select_related(
            "purchase", "purchase__supplier", "created_by"
        )
        purchase = self.request.query_params.get("purchase")
        if purchase:
            queryset = queryset.filter(purchase_id=purchase)
        return filter_queryset_by_branch_scope(
            queryset, self.request.user, "purchase__warehouse__branch_id"
        )

    def perform_create(self, serializer):
        _require_purchase_access(self.request.user, serializer.validated_data["purchase"])
        serializer.save()

    def perform_update(self, serializer):
        purchase = serializer.validated_data.get(
            "purchase", serializer.instance.purchase
        )
        _require_purchase_access(self.request.user, purchase)
        serializer.save()
