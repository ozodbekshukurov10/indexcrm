from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response
from rest_framework.status import HTTP_201_CREATED
from rest_framework.viewsets import ModelViewSet

from apps.accounts.permissions import (
    IsReadOnlyOrOwnerAdminManager,
    filter_queryset_by_branch_scope,
)
from apps.common.scoping import require_warehouse_access
from apps.inventory.selectors import (
    inventory_adjustment_queryset,
    low_stock_queryset,
    stock_movement_queryset,
    stock_queryset,
    warehouse_queryset,
)
from apps.inventory.serializers import (
    InventoryAdjustmentSerializer,
    StockMovementCreateSerializer,
    StockMovementSerializer,
    StockSerializer,
    WarehouseSerializer,
)


def _bool_param(value):
    if value is None:
        return None
    return str(value).lower() in {"1", "true", "yes", "on"}


@extend_schema_view(
    list=extend_schema(
        summary="List warehouses",
        parameters=[
            OpenApiParameter("branch", str, description="Filter by branch UUID."),
            OpenApiParameter("is_active", bool, description="Filter by active status."),
        ],
    ),
    create=extend_schema(summary="Create warehouse"),
    retrieve=extend_schema(summary="Retrieve warehouse"),
    update=extend_schema(summary="Update warehouse"),
    partial_update=extend_schema(summary="Partially update warehouse"),
    destroy=extend_schema(summary="Soft delete warehouse"),
)
class WarehouseViewSet(ModelViewSet):
    serializer_class = WarehouseSerializer
    permission_classes = (IsReadOnlyOrOwnerAdminManager,)
    filter_backends = (SearchFilter, OrderingFilter)
    search_fields = ("name", "branch__name", "branch__store__name")
    ordering_fields = ("name", "created_at", "updated_at")
    ordering = ("name",)

    def get_queryset(self):
        queryset = warehouse_queryset()
        branch = self.request.query_params.get("branch")
        is_active = _bool_param(self.request.query_params.get("is_active"))

        if branch:
            queryset = queryset.filter(branch_id=branch)
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active)

        return filter_queryset_by_branch_scope(queryset, self.request.user, "branch_id")

    def perform_create(self, serializer):
        from apps.common.scoping import require_branch_access

        require_branch_access(self.request.user, serializer.validated_data["branch"])
        serializer.save()

    def perform_update(self, serializer):
        branch = serializer.validated_data.get("branch", serializer.instance.branch)
        from apps.common.scoping import require_branch_access

        require_branch_access(self.request.user, branch)
        serializer.save()


@extend_schema_view(
    list=extend_schema(
        summary="List stock records",
        parameters=[
            OpenApiParameter("warehouse", str, description="Filter by warehouse UUID."),
            OpenApiParameter("product", str, description="Filter by product UUID."),
            OpenApiParameter("branch", str, description="Filter by branch UUID."),
            OpenApiParameter(
                "low_stock", bool, description="Return only low-stock rows."
            ),
        ],
    ),
    create=extend_schema(summary="Create stock record"),
    retrieve=extend_schema(summary="Retrieve stock record"),
    update=extend_schema(summary="Update stock record metadata"),
    partial_update=extend_schema(summary="Partially update stock record metadata"),
    destroy=extend_schema(summary="Soft delete stock record"),
)
class StockViewSet(ModelViewSet):
    serializer_class = StockSerializer
    permission_classes = (IsReadOnlyOrOwnerAdminManager,)
    filter_backends = (SearchFilter, OrderingFilter)
    search_fields = (
        "warehouse__name",
        "product__name",
        "product__sku",
        "product__barcode",
        "product__barcodes__code",
    )
    ordering_fields = (
        "quantity",
        "reserved_quantity",
        "low_stock_limit",
        "created_at",
        "updated_at",
    )
    ordering = ("product__name",)

    def get_queryset(self):
        queryset = (
            low_stock_queryset()
            if _bool_param(self.request.query_params.get("low_stock"))
            else stock_queryset()
        )
        queryset = filter_queryset_by_branch_scope(
            queryset, self.request.user, "warehouse__branch_id"
        )
        return self._apply_filters(queryset).distinct()

    def _apply_filters(self, queryset):
        warehouse = self.request.query_params.get("warehouse")
        product = self.request.query_params.get("product")
        branch = self.request.query_params.get("branch")

        if warehouse:
            queryset = queryset.filter(warehouse_id=warehouse)
        if product:
            queryset = queryset.filter(product_id=product)
        if branch:
            queryset = queryset.filter(warehouse__branch_id=branch)

        return queryset

    @extend_schema(
        summary="List low stock records",
        parameters=[
            OpenApiParameter("warehouse", str, description="Filter by warehouse UUID."),
            OpenApiParameter("product", str, description="Filter by product UUID."),
            OpenApiParameter("branch", str, description="Filter by branch UUID."),
        ],
    )
    @action(detail=False, methods=["get"], url_path="low-stock")
    def low_stock(self, request):
        queryset = filter_queryset_by_branch_scope(
            low_stock_queryset(), self.request.user, "warehouse__branch_id"
        )
        queryset = self._apply_filters(queryset).distinct()
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def perform_create(self, serializer):
        require_warehouse_access(self.request.user, serializer.validated_data["warehouse"])
        serializer.save()

    def perform_update(self, serializer):
        warehouse = serializer.validated_data.get(
            "warehouse", serializer.instance.warehouse
        )
        require_warehouse_access(self.request.user, warehouse)
        serializer.save()


@extend_schema_view(
    list=extend_schema(
        summary="List stock movements",
        parameters=[
            OpenApiParameter("warehouse", str, description="Filter by warehouse UUID."),
            OpenApiParameter("product", str, description="Filter by product UUID."),
            OpenApiParameter(
                "movement_type", str, description="Filter by movement type."
            ),
            OpenApiParameter("expiry_date", str, description="Filter by expiry date."),
        ],
    ),
    create=extend_schema(
        summary="Create stock movement",
        description=(
            "Creates a stock movement through the inventory service. IN increases stock, "
            "OUT decreases stock, TRANSFER moves stock between warehouses, and ADJUSTMENT "
            "sets the stock quantity to the submitted quantity."
        ),
    ),
    retrieve=extend_schema(summary="Retrieve stock movement"),
    update=extend_schema(summary="Update stock movement note"),
    partial_update=extend_schema(summary="Partially update stock movement note"),
    destroy=extend_schema(summary="Soft delete stock movement"),
)
class StockMovementViewSet(ModelViewSet):
    permission_classes = (IsReadOnlyOrOwnerAdminManager,)
    filter_backends = (SearchFilter, OrderingFilter)
    search_fields = (
        "warehouse__name",
        "product__name",
        "product__sku",
        "product__barcode",
        "note",
        "created_by__email",
    )
    ordering_fields = ("quantity", "movement_type", "created_at", "updated_at")
    ordering = ("-created_at",)

    def get_queryset(self):
        queryset = stock_movement_queryset()
        warehouse = self.request.query_params.get("warehouse")
        product = self.request.query_params.get("product")
        movement_type = self.request.query_params.get("movement_type")
        expiry_date = self.request.query_params.get("expiry_date")

        if warehouse:
            queryset = queryset.filter(warehouse_id=warehouse)
        if product:
            queryset = queryset.filter(product_id=product)
        if movement_type:
            queryset = queryset.filter(movement_type=movement_type)
        if expiry_date:
            queryset = queryset.filter(expiry_date=expiry_date)

        return filter_queryset_by_branch_scope(
            queryset, self.request.user, "warehouse__branch_id"
        )

    def get_serializer_class(self):
        if self.action == "create":
            return StockMovementCreateSerializer
        return StockMovementSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        require_warehouse_access(request.user, serializer.validated_data["warehouse"])
        target_warehouse = serializer.validated_data.get("target_warehouse")
        if target_warehouse is not None:
            require_warehouse_access(request.user, target_warehouse)
        movement = serializer.save()
        response_serializer = StockMovementSerializer(
            movement, context=self.get_serializer_context()
        )
        return Response(response_serializer.data, status=HTTP_201_CREATED)


@extend_schema_view(
    list=extend_schema(
        summary="List inventory adjustments",
        parameters=[
            OpenApiParameter("warehouse", str, description="Filter by warehouse UUID."),
        ],
    ),
    create=extend_schema(summary="Create inventory adjustment"),
    retrieve=extend_schema(summary="Retrieve inventory adjustment"),
    update=extend_schema(summary="Update inventory adjustment"),
    partial_update=extend_schema(summary="Partially update inventory adjustment"),
    destroy=extend_schema(summary="Soft delete inventory adjustment"),
)
class InventoryAdjustmentViewSet(ModelViewSet):
    serializer_class = InventoryAdjustmentSerializer
    permission_classes = (IsReadOnlyOrOwnerAdminManager,)
    filter_backends = (SearchFilter, OrderingFilter)
    search_fields = ("warehouse__name", "note", "created_by__email")
    ordering_fields = ("adjustment_date", "created_at", "updated_at")
    ordering = ("-adjustment_date",)

    def get_queryset(self):
        queryset = inventory_adjustment_queryset()
        warehouse = self.request.query_params.get("warehouse")

        if warehouse:
            queryset = queryset.filter(warehouse_id=warehouse)

        return filter_queryset_by_branch_scope(
            queryset, self.request.user, "warehouse__branch_id"
        )

    def perform_create(self, serializer):
        require_warehouse_access(self.request.user, serializer.validated_data["warehouse"])
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        warehouse = serializer.validated_data.get(
            "warehouse", serializer.instance.warehouse
        )
        require_warehouse_access(self.request.user, warehouse)
        serializer.save()
