from django.core.exceptions import ValidationError as DjangoValidationError
from drf_spectacular.utils import OpenApiExample, extend_schema_serializer
from rest_framework import serializers

from apps.inventory.models import (
    InventoryAdjustment,
    Stock,
    StockMovement,
    StockMovementType,
    Warehouse,
)
from apps.inventory.services import StockService


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            "Warehouse request",
            value={
                "branch": "38eb4b8d-d187-4f85-b756-2da19e84d032",
                "name": "Main Warehouse",
                "is_active": True,
            },
            request_only=True,
        ),
        OpenApiExample(
            "Warehouse response",
            value={
                "id": "b11e0988-9318-476e-a3f5-a728d6b87021",
                "branch": "38eb4b8d-d187-4f85-b756-2da19e84d032",
                "branch_name": "Main Branch",
                "name": "Main Warehouse",
                "is_active": True,
                "created_at": "2026-05-28T12:00:00Z",
                "updated_at": "2026-05-28T12:00:00Z",
            },
            response_only=True,
        ),
    ]
)
class WarehouseSerializer(serializers.ModelSerializer):
    branch_name = serializers.CharField(source="branch.name", read_only=True)

    class Meta:
        model = Warehouse
        fields = (
            "id",
            "branch",
            "branch_name",
            "name",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "branch_name", "created_at", "updated_at")


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            "Stock request",
            value={
                "warehouse": "b11e0988-9318-476e-a3f5-a728d6b87021",
                "product": "abdc2d58-3070-48fa-9651-7f8b3b6d3e2a",
                "reserved_quantity": "0.000",
                "low_stock_limit": "5.000",
            },
            request_only=True,
        ),
        OpenApiExample(
            "Stock response",
            value={
                "id": "70b6165a-3580-40d2-ac91-b126a7cb4714",
                "warehouse": "b11e0988-9318-476e-a3f5-a728d6b87021",
                "warehouse_name": "Main Warehouse",
                "product": "abdc2d58-3070-48fa-9651-7f8b3b6d3e2a",
                "product_name": "Sparkling Water 1L",
                "product_sku": "WATER-1L",
                "quantity": "25.000",
                "reserved_quantity": "0.000",
                "available_quantity": "25.000",
                "low_stock_limit": "5.000",
                "is_low_stock": False,
                "updated_at": "2026-05-28T12:00:00Z",
            },
            response_only=True,
        ),
    ]
)
class StockSerializer(serializers.ModelSerializer):
    warehouse_name = serializers.CharField(source="warehouse.name", read_only=True)
    product_name = serializers.CharField(source="product.name", read_only=True)
    product_sku = serializers.CharField(source="product.sku", read_only=True)
    available_quantity = serializers.DecimalField(
        max_digits=14,
        decimal_places=3,
        read_only=True,
    )
    is_low_stock = serializers.BooleanField(read_only=True)

    class Meta:
        model = Stock
        fields = (
            "id",
            "warehouse",
            "warehouse_name",
            "product",
            "product_name",
            "product_sku",
            "quantity",
            "reserved_quantity",
            "available_quantity",
            "low_stock_limit",
            "is_low_stock",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "warehouse_name",
            "product_name",
            "product_sku",
            "quantity",
            "available_quantity",
            "is_low_stock",
            "created_at",
            "updated_at",
        )

    def validate(self, attrs):
        if self.instance and ("warehouse" in attrs or "product" in attrs):
            raise serializers.ValidationError(
                {
                    "stock": "Warehouse and product cannot be changed after stock creation."
                }
            )

        quantity = getattr(self.instance, "quantity", attrs.get("quantity", 0))
        reserved_quantity = attrs.get(
            "reserved_quantity",
            getattr(self.instance, "reserved_quantity", 0),
        )

        if reserved_quantity > quantity:
            raise serializers.ValidationError(
                {"reserved_quantity": "Reserved quantity cannot exceed stock quantity."}
            )

        return attrs


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            "Stock movement request",
            value={
                "warehouse": "b11e0988-9318-476e-a3f5-a728d6b87021",
                "product": "abdc2d58-3070-48fa-9651-7f8b3b6d3e2a",
                "movement_type": "IN",
                "quantity": "25.000",
                "expiry_date": "2026-12-31",
                "note": "Initial stock",
            },
            request_only=True,
        ),
        OpenApiExample(
            "Stock movement response",
            value={
                "id": "bc4132fd-6651-4d64-8ee2-91ea081794b2",
                "warehouse": "b11e0988-9318-476e-a3f5-a728d6b87021",
                "warehouse_name": "Main Warehouse",
                "product": "abdc2d58-3070-48fa-9651-7f8b3b6d3e2a",
                "product_name": "Sparkling Water 1L",
                "movement_type": "IN",
                "quantity": "25.000",
                "expiry_date": "2026-12-31",
                "note": "Initial stock",
                "created_by": "69a59592-3332-422e-9243-412353f3ca59",
                "created_at": "2026-05-28T12:00:00Z",
            },
            response_only=True,
        ),
    ]
)
class StockMovementSerializer(serializers.ModelSerializer):
    warehouse_name = serializers.CharField(source="warehouse.name", read_only=True)
    product_name = serializers.CharField(source="product.name", read_only=True)

    class Meta:
        model = StockMovement
        fields = (
            "id",
            "warehouse",
            "warehouse_name",
            "product",
            "product_name",
            "movement_type",
            "quantity",
            "expiry_date",
            "note",
            "created_by",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "warehouse",
            "warehouse_name",
            "product",
            "product_name",
            "movement_type",
            "quantity",
            "expiry_date",
            "created_by",
            "created_at",
            "updated_at",
        )


class StockMovementCreateSerializer(serializers.ModelSerializer):
    target_warehouse = serializers.PrimaryKeyRelatedField(
        queryset=Warehouse.objects.all(),
        required=False,
        allow_null=True,
        help_text="Required only for TRANSFER movements.",
    )

    class Meta:
        model = StockMovement
        fields = (
            "warehouse",
            "target_warehouse",
            "product",
            "movement_type",
            "quantity",
            "expiry_date",
            "note",
        )

    def validate(self, attrs):
        movement_type = attrs.get("movement_type")
        target_warehouse = attrs.get("target_warehouse")
        product = attrs.get("product")
        expiry_date = attrs.get("expiry_date")

        if movement_type == StockMovementType.TRANSFER and target_warehouse is None:
            raise serializers.ValidationError(
                {"target_warehouse": "Target warehouse is required for transfers."}
            )
        if movement_type != StockMovementType.TRANSFER and target_warehouse is not None:
            raise serializers.ValidationError(
                {"target_warehouse": "Target warehouse is only allowed for transfers."}
            )
        if (
            product
            and product.has_expiry_date
            and movement_type in {StockMovementType.IN, StockMovementType.ADJUSTMENT}
            and not expiry_date
        ):
            raise serializers.ValidationError(
                {"expiry_date": "Expiry date is required for this product movement."}
            )

        return attrs

    def create(self, validated_data):
        request = self.context.get("request")
        created_by = request.user if request else None
        target_warehouse = validated_data.pop("target_warehouse", None)

        try:
            return StockService.apply_movement(
                created_by=created_by,
                target_warehouse=target_warehouse,
                **validated_data,
            )
        except DjangoValidationError as error:
            raise serializers.ValidationError(error.message_dict) from error


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            "Inventory adjustment request",
            value={
                "warehouse": "b11e0988-9318-476e-a3f5-a728d6b87021",
                "note": "Monthly stock count",
                "adjustment_date": "2026-05-28T12:00:00Z",
            },
            request_only=True,
        ),
        OpenApiExample(
            "Inventory adjustment response",
            value={
                "id": "f3a8a6e4-8afe-41e3-bc43-f5f491130baa",
                "warehouse": "b11e0988-9318-476e-a3f5-a728d6b87021",
                "warehouse_name": "Main Warehouse",
                "created_by": "69a59592-3332-422e-9243-412353f3ca59",
                "note": "Monthly stock count",
                "adjustment_date": "2026-05-28T12:00:00Z",
                "created_at": "2026-05-28T12:00:00Z",
                "updated_at": "2026-05-28T12:00:00Z",
            },
            response_only=True,
        ),
    ]
)
class InventoryAdjustmentSerializer(serializers.ModelSerializer):
    warehouse_name = serializers.CharField(source="warehouse.name", read_only=True)

    class Meta:
        model = InventoryAdjustment
        fields = (
            "id",
            "warehouse",
            "warehouse_name",
            "created_by",
            "note",
            "adjustment_date",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "warehouse_name",
            "created_by",
            "created_at",
            "updated_at",
        )
