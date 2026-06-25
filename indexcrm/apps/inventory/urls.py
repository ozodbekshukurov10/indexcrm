from rest_framework.routers import DefaultRouter

from apps.inventory.views import (
    InventoryAdjustmentViewSet,
    StockMovementViewSet,
    StockViewSet,
    WarehouseViewSet,
)

router = DefaultRouter()
router.register("warehouses", WarehouseViewSet, basename="warehouse")
router.register("stocks", StockViewSet, basename="stock")
router.register("stock-movements", StockMovementViewSet, basename="stock-movement")
router.register(
    "inventory-adjustments", InventoryAdjustmentViewSet, basename="inventory-adjustment"
)

urlpatterns = router.urls
