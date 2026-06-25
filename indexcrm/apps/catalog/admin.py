from django.contrib import admin

from apps.catalog.models import Barcode, Brand, Category, Product, ProductImage, Unit


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1


class BarcodeInline(admin.TabularInline):
    model = Barcode
    extra = 1


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "parent", "is_active", "created_at")
    list_filter = ("is_active", "parent", "created_at")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("id", "created_at", "updated_at", "deleted_at")


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ("name", "created_at")
    search_fields = ("name", "description")
    readonly_fields = ("id", "created_at", "updated_at", "deleted_at")


@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    list_display = ("name", "short_name", "created_at")
    search_fields = ("name", "short_name")
    readonly_fields = ("id", "created_at", "updated_at", "deleted_at")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "sku",
        "barcode",
        "category",
        "brand",
        "selling_price",
        "is_active",
    )
    list_filter = ("is_active", "has_expiry_date", "category", "brand", "unit")
    search_fields = ("name", "slug", "sku", "barcode", "barcodes__code")
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("id", "created_at", "updated_at", "deleted_at")
    inlines = (BarcodeInline, ProductImageInline)


@admin.register(Barcode)
class BarcodeAdmin(admin.ModelAdmin):
    list_display = ("code", "barcode_type", "product", "created_at")
    list_filter = ("barcode_type", "created_at")
    search_fields = ("code", "product__name", "product__sku")
    readonly_fields = ("id", "created_at", "updated_at", "deleted_at")


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ("product", "is_main", "created_at")
    list_filter = ("is_main", "created_at")
    search_fields = ("product__name", "product__sku")
    readonly_fields = ("id", "created_at", "updated_at", "deleted_at")
