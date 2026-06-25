from rest_framework.routers import DefaultRouter

from apps.catalog.views import (
    BarcodeViewSet,
    BrandViewSet,
    CategoryViewSet,
    ProductImageViewSet,
    ProductViewSet,
    UnitViewSet,
)

router = DefaultRouter()
router.register("categories", CategoryViewSet, basename="category")
router.register("brands", BrandViewSet, basename="brand")
router.register("units", UnitViewSet, basename="unit")
router.register("products", ProductViewSet, basename="product")
router.register("product-images", ProductImageViewSet, basename="product-image")
router.register("barcodes", BarcodeViewSet, basename="barcode")

urlpatterns = router.urls
