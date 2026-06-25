from rest_framework.routers import DefaultRouter

from apps.stores.views import BranchViewSet, CashDeskViewSet, StoreViewSet

router = DefaultRouter()
router.register("stores", StoreViewSet, basename="store")
router.register("branches", BranchViewSet, basename="branch")
router.register("cashdesks", CashDeskViewSet, basename="cashdesk")

urlpatterns = router.urls
