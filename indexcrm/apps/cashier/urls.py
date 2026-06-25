from rest_framework.routers import DefaultRouter

from apps.cashier.views import CashierShiftViewSet

router = DefaultRouter()
router.register("cashier-shifts", CashierShiftViewSet, basename="cashier-shift")

urlpatterns = router.urls
