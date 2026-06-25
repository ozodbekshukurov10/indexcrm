from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.viewsets import ModelViewSet

from apps.accounts.permissions import IsReadOnlyOrOwnerAdminManager
from apps.catalog.models import Barcode, Brand, Category, Product, ProductImage, Unit
from apps.catalog.serializers import (
    BarcodeSerializer,
    BrandSerializer,
    CategorySerializer,
    ProductImageSerializer,
    ProductSerializer,
    UnitSerializer,
)


def _bool_param(value):
    if value is None:
        return None
    return str(value).lower() in {"1", "true", "yes", "on"}


@extend_schema_view(
    list=extend_schema(
        summary="List categories",
        parameters=[
            OpenApiParameter(
                "parent", str, description="Filter by parent category UUID."
            ),
            OpenApiParameter("is_active", bool, description="Filter by active status."),
        ],
    ),
    create=extend_schema(summary="Create category"),
    retrieve=extend_schema(summary="Retrieve category"),
    update=extend_schema(summary="Update category"),
    partial_update=extend_schema(summary="Partially update category"),
    destroy=extend_schema(summary="Soft delete category"),
)
class CategoryViewSet(ModelViewSet):
    serializer_class = CategorySerializer
    permission_classes = (IsReadOnlyOrOwnerAdminManager,)
    parser_classes = (JSONParser, MultiPartParser, FormParser)
    filter_backends = (SearchFilter, OrderingFilter)
    search_fields = ("name", "slug")
    ordering_fields = ("name", "slug", "created_at", "updated_at")
    ordering = ("name",)

    def get_queryset(self):
        queryset = Category.objects.select_related("parent")
        parent = self.request.query_params.get("parent")
        is_active = _bool_param(self.request.query_params.get("is_active"))

        if parent:
            queryset = queryset.filter(parent_id=parent)
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active)

        return queryset


@extend_schema_view(
    list=extend_schema(summary="List brands"),
    create=extend_schema(summary="Create brand"),
    retrieve=extend_schema(summary="Retrieve brand"),
    update=extend_schema(summary="Update brand"),
    partial_update=extend_schema(summary="Partially update brand"),
    destroy=extend_schema(summary="Soft delete brand"),
)
class BrandViewSet(ModelViewSet):
    serializer_class = BrandSerializer
    permission_classes = (IsReadOnlyOrOwnerAdminManager,)
    parser_classes = (JSONParser, MultiPartParser, FormParser)
    queryset = Brand.objects.all()
    filter_backends = (SearchFilter, OrderingFilter)
    search_fields = ("name", "description")
    ordering_fields = ("name", "created_at", "updated_at")
    ordering = ("name",)


@extend_schema_view(
    list=extend_schema(summary="List units"),
    create=extend_schema(summary="Create unit"),
    retrieve=extend_schema(summary="Retrieve unit"),
    update=extend_schema(summary="Update unit"),
    partial_update=extend_schema(summary="Partially update unit"),
    destroy=extend_schema(summary="Soft delete unit"),
)
class UnitViewSet(ModelViewSet):
    serializer_class = UnitSerializer
    permission_classes = (IsReadOnlyOrOwnerAdminManager,)
    queryset = Unit.objects.all()
    filter_backends = (SearchFilter, OrderingFilter)
    search_fields = ("name", "short_name")
    ordering_fields = ("name", "short_name", "created_at", "updated_at")
    ordering = ("name",)


@extend_schema_view(
    list=extend_schema(
        summary="List products",
        parameters=[
            OpenApiParameter("category", str, description="Filter by category UUID."),
            OpenApiParameter("brand", str, description="Filter by brand UUID."),
            OpenApiParameter("unit", str, description="Filter by unit UUID."),
            OpenApiParameter("is_active", bool, description="Filter by active status."),
            OpenApiParameter(
                "has_expiry_date",
                bool,
                description="Filter products that track expiry dates.",
            ),
        ],
    ),
    create=extend_schema(summary="Create product"),
    retrieve=extend_schema(summary="Retrieve product"),
    update=extend_schema(summary="Update product"),
    partial_update=extend_schema(summary="Partially update product"),
    destroy=extend_schema(summary="Soft delete product"),
)
class ProductViewSet(ModelViewSet):
    serializer_class = ProductSerializer
    permission_classes = (IsReadOnlyOrOwnerAdminManager,)
    parser_classes = (JSONParser, MultiPartParser, FormParser)
    filter_backends = (SearchFilter, OrderingFilter)
    search_fields = (
        "name",
        "slug",
        "description",
        "sku",
        "barcode",
        "barcodes__code",
        "category__name",
        "brand__name",
    )
    ordering_fields = (
        "name",
        "sku",
        "cost_price",
        "selling_price",
        "created_at",
        "updated_at",
    )
    ordering = ("name",)

    def get_queryset(self):
        queryset = Product.objects.select_related(
            "category", "brand", "unit", "created_by"
        ).prefetch_related("barcodes", "images")
        category = self.request.query_params.get("category")
        brand = self.request.query_params.get("brand")
        unit = self.request.query_params.get("unit")
        is_active = _bool_param(self.request.query_params.get("is_active"))
        has_expiry_date = _bool_param(self.request.query_params.get("has_expiry_date"))

        if category:
            queryset = queryset.filter(category_id=category)
        if brand:
            queryset = queryset.filter(brand_id=brand)
        if unit:
            queryset = queryset.filter(unit_id=unit)
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active)
        if has_expiry_date is not None:
            queryset = queryset.filter(has_expiry_date=has_expiry_date)

        return queryset.distinct()

    def perform_create(self, serializer):
        product = serializer.save(created_by=self.request.user)
        from apps.accounts.models import AuditAction
        from apps.accounts.services import record_audit_log

        record_audit_log(
            actor=self.request.user,
            action=AuditAction.CREATE,
            entity_type="catalog.Product",
            entity_id=product.id,
            object_repr=product.name,
            summary="Product created.",
        )

    def perform_update(self, serializer):
        product = serializer.save()
        from apps.accounts.models import AuditAction
        from apps.accounts.services import record_audit_log

        record_audit_log(
            actor=self.request.user,
            action=AuditAction.UPDATE,
            entity_type="catalog.Product",
            entity_id=product.id,
            object_repr=product.name,
            summary="Product updated.",
        )

    def perform_destroy(self, instance):
        product_id = instance.id
        product_name = instance.name
        instance.delete()
        from apps.accounts.models import AuditAction
        from apps.accounts.services import record_audit_log

        record_audit_log(
            actor=self.request.user,
            action=AuditAction.DELETE,
            entity_type="catalog.Product",
            entity_id=product_id,
            object_repr=product_name,
            summary="Product deleted.",
        )


@extend_schema_view(
    list=extend_schema(
        summary="List product images",
        parameters=[
            OpenApiParameter("product", str, description="Filter by product UUID."),
            OpenApiParameter("is_main", bool, description="Filter by main image flag."),
        ],
    ),
    create=extend_schema(summary="Upload product image"),
    retrieve=extend_schema(summary="Retrieve product image"),
    update=extend_schema(summary="Update product image"),
    partial_update=extend_schema(summary="Partially update product image"),
    destroy=extend_schema(summary="Soft delete product image"),
)
class ProductImageViewSet(ModelViewSet):
    serializer_class = ProductImageSerializer
    permission_classes = (IsReadOnlyOrOwnerAdminManager,)
    parser_classes = (JSONParser, MultiPartParser, FormParser)
    filter_backends = (SearchFilter, OrderingFilter)
    search_fields = ("product__name", "product__sku", "product__barcode")
    ordering_fields = ("is_main", "created_at", "updated_at")
    ordering = ("-is_main", "-created_at")

    def get_queryset(self):
        queryset = ProductImage.objects.select_related("product")
        product = self.request.query_params.get("product")
        is_main = _bool_param(self.request.query_params.get("is_main"))

        if product:
            queryset = queryset.filter(product_id=product)
        if is_main is not None:
            queryset = queryset.filter(is_main=is_main)

        return queryset


@extend_schema_view(
    list=extend_schema(
        summary="List barcodes",
        parameters=[
            OpenApiParameter("product", str, description="Filter by product UUID."),
            OpenApiParameter(
                "barcode_type", str, description="Filter by barcode type."
            ),
        ],
    ),
    create=extend_schema(summary="Create barcode"),
    retrieve=extend_schema(summary="Retrieve barcode"),
    update=extend_schema(summary="Update barcode"),
    partial_update=extend_schema(summary="Partially update barcode"),
    destroy=extend_schema(summary="Soft delete barcode"),
)
class BarcodeViewSet(ModelViewSet):
    serializer_class = BarcodeSerializer
    permission_classes = (IsReadOnlyOrOwnerAdminManager,)
    filter_backends = (SearchFilter, OrderingFilter)
    search_fields = ("code", "product__name", "product__sku", "product__barcode")
    ordering_fields = ("code", "barcode_type", "created_at", "updated_at")
    ordering = ("code",)

    def get_queryset(self):
        queryset = Barcode.objects.select_related(
            "product", "product__category", "product__brand"
        )
        product = self.request.query_params.get("product")
        barcode_type = self.request.query_params.get("barcode_type")

        if product:
            queryset = queryset.filter(product_id=product)
        if barcode_type:
            queryset = queryset.filter(barcode_type=barcode_type)

        return queryset
