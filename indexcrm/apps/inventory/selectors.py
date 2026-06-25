from django.db.models import F

from apps.inventory.models import InventoryAdjustment, Stock, StockMovement, Warehouse


def warehouse_queryset():
    return Warehouse.objects.select_related("branch", "branch__store")


def stock_queryset():
    return Stock.objects.select_related(
        "warehouse",
        "warehouse__branch",
        "warehouse__branch__store",
        "product",
        "product__category",
        "product__brand",
        "product__unit",
    )


def low_stock_queryset():
    return stock_queryset().filter(quantity__lte=F("low_stock_limit"))


def get_low_stock_products(limit=50):
    return low_stock_queryset().order_by(
        "warehouse__branch__store__name", "warehouse__name", "product__name"
    )[:limit]


def stock_movement_queryset():
    return StockMovement.objects.select_related(
        "warehouse",
        "warehouse__branch",
        "product",
        "product__category",
        "created_by",
    )


def inventory_adjustment_queryset():
    return InventoryAdjustment.objects.select_related(
        "warehouse",
        "warehouse__branch",
        "created_by",
    )
