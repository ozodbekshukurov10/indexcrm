from rest_framework.routers import DefaultRouter

from apps.purchases.views import (
    PurchaseItemViewSet,
    PurchasePaymentViewSet,
    PurchaseViewSet,
    SupplierContactViewSet,
    SupplierPaymentViewSet,
    SupplierViewSet,
)

router = DefaultRouter()
router.register("suppliers", SupplierViewSet, basename="supplier")
router.register(
    "supplier-contacts", SupplierContactViewSet, basename="supplier-contact"
)
router.register(
    "supplier-payments", SupplierPaymentViewSet, basename="supplier-payment"
)
router.register("purchases", PurchaseViewSet, basename="purchase")
router.register("purchase-items", PurchaseItemViewSet, basename="purchase-item")
router.register(
    "purchase-payments", PurchasePaymentViewSet, basename="purchase-payment"
)

urlpatterns = router.urls
