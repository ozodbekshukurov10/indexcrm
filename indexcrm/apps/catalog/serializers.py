from drf_spectacular.utils import OpenApiExample, extend_schema_serializer
from rest_framework import serializers

from apps.catalog.models import Barcode, Brand, Category, Product, ProductImage, Unit


def _validate_barcode_is_globally_unique(code, product=None, instance=None):
    if not code:
        return

    product_queryset = Product.all_objects.filter(barcode=code)
    if product:
        product_queryset = product_queryset.exclude(pk=product.pk)
    elif instance and getattr(instance, "pk", None):
        product_queryset = product_queryset.exclude(pk=instance.pk)

    barcode_queryset = Barcode.all_objects.filter(code=code)
    if product:
        barcode_queryset = barcode_queryset.exclude(product=product)

    if product_queryset.exists() or barcode_queryset.exists():
        raise serializers.ValidationError(
            "This barcode is already assigned to a product."
        )


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            "Category request",
            value={"name": "Beverages", "parent": None, "is_active": True},
            request_only=True,
        ),
        OpenApiExample(
            "Category response",
            value={
                "id": "f0d84931-29df-4c9d-8895-b4c1233d51db",
                "name": "Beverages",
                "slug": "beverages",
                "parent": None,
                "parent_name": None,
                "image": None,
                "is_active": True,
                "created_at": "2026-05-28T12:00:00Z",
                "updated_at": "2026-05-28T12:00:00Z",
            },
            response_only=True,
        ),
    ]
)
class CategorySerializer(serializers.ModelSerializer):
    parent_name = serializers.CharField(source="parent.name", read_only=True)

    class Meta:
        model = Category
        fields = (
            "id",
            "name",
            "slug",
            "parent",
            "parent_name",
            "image",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "slug", "parent_name", "created_at", "updated_at")


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            "Brand request",
            value={"name": "Index Foods", "description": "Private label products."},
            request_only=True,
        ),
        OpenApiExample(
            "Brand response",
            value={
                "id": "1a3e548b-74c0-4a76-a3c7-db424daab6df",
                "name": "Index Foods",
                "logo": None,
                "description": "Private label products.",
                "created_at": "2026-05-28T12:00:00Z",
                "updated_at": "2026-05-28T12:00:00Z",
            },
            response_only=True,
        ),
    ]
)
class BrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = ("id", "name", "logo", "description", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            "Unit request",
            value={"name": "piece", "short_name": "pcs"},
            request_only=True,
        ),
        OpenApiExample(
            "Unit response",
            value={
                "id": "c80f15f8-db87-41e2-9a24-21acbd801ddf",
                "name": "piece",
                "short_name": "pcs",
                "created_at": "2026-05-28T12:00:00Z",
                "updated_at": "2026-05-28T12:00:00Z",
            },
            response_only=True,
        ),
    ]
)
class UnitSerializer(serializers.ModelSerializer):
    class Meta:
        model = Unit
        fields = ("id", "name", "short_name", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            "Product image request",
            value={
                "product": "abdc2d58-3070-48fa-9651-7f8b3b6d3e2a",
                "image": "binary image upload",
                "is_main": True,
            },
            request_only=True,
        ),
        OpenApiExample(
            "Product image response",
            value={
                "id": "4d173d81-885e-4097-b692-2eddb21e25a2",
                "product": "abdc2d58-3070-48fa-9651-7f8b3b6d3e2a",
                "product_name": "Sparkling Water 1L",
                "image": "http://localhost:8000/media/catalog/product-images/image.jpg",
                "is_main": True,
                "created_at": "2026-05-28T12:00:00Z",
                "updated_at": "2026-05-28T12:00:00Z",
            },
            response_only=True,
        ),
    ]
)
class ProductImageSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)

    class Meta:
        model = ProductImage
        fields = (
            "id",
            "product",
            "product_name",
            "image",
            "is_main",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "product_name", "created_at", "updated_at")


class BarcodeNestedSerializer(serializers.ModelSerializer):
    class Meta:
        model = Barcode
        fields = ("id", "code", "barcode_type")


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            "Product request",
            value={
                "category": "f0d84931-29df-4c9d-8895-b4c1233d51db",
                "brand": "1a3e548b-74c0-4a76-a3c7-db424daab6df",
                "name": "Sparkling Water 1L",
                "description": "Carbonated drinking water.",
                "barcode": "4780012345678",
                "sku": "WATER-1L",
                "cost_price": "2500.00",
                "selling_price": "4000.00",
                "min_price": "3500.00",
                "unit": "c80f15f8-db87-41e2-9a24-21acbd801ddf",
                "weight": "1.000",
                "volume": "1.000",
                "is_active": True,
                "has_expiry_date": True,
            },
            request_only=True,
        ),
        OpenApiExample(
            "Product response",
            value={
                "id": "abdc2d58-3070-48fa-9651-7f8b3b6d3e2a",
                "category": "f0d84931-29df-4c9d-8895-b4c1233d51db",
                "category_name": "Beverages",
                "brand": "1a3e548b-74c0-4a76-a3c7-db424daab6df",
                "brand_name": "Index Foods",
                "name": "Sparkling Water 1L",
                "slug": "sparkling-water-1l",
                "barcode": "4780012345678",
                "sku": "WATER-1L",
                "selling_price": "4000.00",
                "unit": "c80f15f8-db87-41e2-9a24-21acbd801ddf",
                "unit_short_name": "pcs",
                "is_active": True,
                "has_expiry_date": True,
                "barcodes": [
                    {
                        "id": "a8c64f76-f437-4035-ae54-7d4598c81284",
                        "code": "4780012345678",
                        "barcode_type": "EAN13",
                    }
                ],
                "images": [],
                "created_at": "2026-05-28T12:00:00Z",
                "updated_at": "2026-05-28T12:00:00Z",
            },
            response_only=True,
        ),
    ]
)
class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    brand_name = serializers.CharField(source="brand.name", read_only=True)
    unit_short_name = serializers.CharField(source="unit.short_name", read_only=True)
    barcodes = BarcodeNestedSerializer(many=True, read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = (
            "id",
            "category",
            "category_name",
            "brand",
            "brand_name",
            "name",
            "slug",
            "description",
            "barcode",
            "sku",
            "cost_price",
            "selling_price",
            "min_price",
            "unit",
            "unit_short_name",
            "image",
            "weight",
            "volume",
            "is_active",
            "has_expiry_date",
            "created_by",
            "barcodes",
            "images",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "slug",
            "category_name",
            "brand_name",
            "unit_short_name",
            "created_by",
            "barcodes",
            "images",
            "created_at",
            "updated_at",
        )

    def validate_barcode(self, value):
        _validate_barcode_is_globally_unique(
            value,
            product=self.instance if self.instance else None,
            instance=self.instance,
        )
        return value

    def validate(self, attrs):
        selling_price = attrs.get(
            "selling_price", getattr(self.instance, "selling_price", None)
        )
        min_price = attrs.get("min_price", getattr(self.instance, "min_price", None))

        if (
            selling_price is not None
            and min_price is not None
            and min_price > selling_price
        ):
            raise serializers.ValidationError(
                {"min_price": "Minimum price cannot exceed selling price."}
            )

        return attrs


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            "Barcode request",
            value={
                "product": "abdc2d58-3070-48fa-9651-7f8b3b6d3e2a",
                "code": "4780012345678",
                "barcode_type": "EAN13",
            },
            request_only=True,
        ),
        OpenApiExample(
            "Barcode response",
            value={
                "id": "a8c64f76-f437-4035-ae54-7d4598c81284",
                "product": "abdc2d58-3070-48fa-9651-7f8b3b6d3e2a",
                "product_name": "Sparkling Water 1L",
                "code": "4780012345678",
                "barcode_type": "EAN13",
                "created_at": "2026-05-28T12:00:00Z",
                "updated_at": "2026-05-28T12:00:00Z",
            },
            response_only=True,
        ),
    ]
)
class BarcodeSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)

    class Meta:
        model = Barcode
        fields = (
            "id",
            "product",
            "product_name",
            "code",
            "barcode_type",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "product_name", "created_at", "updated_at")

    def validate_code(self, value):
        product = None
        if self.initial_data.get("product"):
            try:
                product = Product.objects.get(pk=self.initial_data["product"])
            except Product.DoesNotExist:
                product = None
        if self.instance:
            product = self.instance.product

        _validate_barcode_is_globally_unique(value, product=product)
        return value
