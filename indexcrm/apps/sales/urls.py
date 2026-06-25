from rest_framework.routers import DefaultRouter

from apps.sales.views import (
    CustomerPaymentViewSet,
    CustomerViewSet,
    RefundViewSet,
    SaleItemViewSet,
    SalePaymentViewSet,
    SaleViewSet,
)

router = DefaultRouter()
router.register("customers", CustomerViewSet, basename="customer")
router.register(
    "customer-payments", CustomerPaymentViewSet, basename="customer-payment"
)
router.register("sales", SaleViewSet, basename="sale")
router.register("sale-items", SaleItemViewSet, basename="sale-item")
router.register("sale-payments", SalePaymentViewSet, basename="sale-payment")
router.register("refunds", RefundViewSet, basename="refund")

urlpatterns = router.urls
