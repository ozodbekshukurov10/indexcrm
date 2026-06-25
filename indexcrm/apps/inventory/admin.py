from django.contrib import admin

from apps.inventory.models import InventoryAdjustment, Stock, StockMovement, Warehouse


@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ("name", "branch", "is_active", "created_at")
    list_filter = ("is_active", "branch__store", "created_at")
    search_fields = ("name", "branch__name", "branch__store__name")
    readonly_fields = ("id", "created_at", "updated_at", "deleted_at")


@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = (
        "product",
        "warehouse",
        "quantity",
        "reserved_quantity",
        "low_stock_limit",
        "updated_at",
    )
    list_filter = ("warehouse__branch__store", "warehouse", "updated_at")
    search_fields = (
        "product__name",
        "product__sku",
        "product__barcode",
        "warehouse__name",
    )
    readonly_fields = ("id", "created_at", "updated_at", "deleted_at")


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = (
        "product",
        "warehouse",
        "movement_type",
        "quantity",
        "expiry_date",
        "created_by",
        "created_at",
    )
    list_filter = ("movement_type", "warehouse", "expiry_date", "created_at")
    search_fields = (
        "product__name",
        "product__sku",
        "product__barcode",
        "note",
        "created_by__email",
    )
    readonly_fields = ("id", "created_at", "updated_at", "deleted_at")


@admin.register(InventoryAdjustment)
class InventoryAdjustmentAdmin(admin.ModelAdmin):
    list_display = ("warehouse", "created_by", "adjustment_date", "created_at")
    list_filter = ("warehouse", "adjustment_date", "created_at")
    search_fields = ("warehouse__name", "note", "created_by__email")
    readonly_fields = ("id", "created_at", "updated_at", "deleted_at")
