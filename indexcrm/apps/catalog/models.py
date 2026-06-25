from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q

from apps.common.models import BaseModel
from apps.common.utils import build_unique_slug


class Category(BaseModel):
    name = models.CharField(max_length=255, help_text="Category name.")
    slug = models.SlugField(
        max_length=255, unique=True, help_text="URL-safe category slug."
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="children",
        help_text="Optional parent category for nested catalogs.",
    )
    image = models.ImageField(
        upload_to="catalog/categories/",
        blank=True,
        null=True,
        help_text="Category image.",
    )
    is_active = models.BooleanField(
        default=True, help_text="Whether the category is active."
    )

    class Meta(BaseModel.Meta):
        verbose_name_plural = "categories"
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["parent", "is_active"]),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = build_unique_slug(self)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Brand(BaseModel):
    name = models.CharField(max_length=255, unique=True, help_text="Brand name.")
    logo = models.ImageField(
        upload_to="catalog/brands/",
        blank=True,
        null=True,
        help_text="Brand logo image.",
    )
    description = models.TextField(blank=True, help_text="Optional brand description.")

    class Meta(BaseModel.Meta):
        indexes = [models.Index(fields=["name"])]

    def __str__(self):
        return self.name


class Unit(BaseModel):
    name = models.CharField(
        max_length=100, unique=True, help_text="Unit name, for example piece."
    )
    short_name = models.CharField(
        max_length=32,
        unique=True,
        help_text="Short unit label, for example pcs.",
    )

    class Meta(BaseModel.Meta):
        indexes = [models.Index(fields=["name"]), models.Index(fields=["short_name"])]

    def __str__(self):
        return self.short_name


class Product(BaseModel):
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="products",
        help_text="Primary product category.",
    )
    brand = models.ForeignKey(
        Brand,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="products",
        help_text="Optional product brand.",
    )
    name = models.CharField(max_length=255, help_text="Product name.")
    slug = models.SlugField(
        max_length=255, unique=True, help_text="URL-safe product slug."
    )
    description = models.TextField(blank=True, help_text="Product description.")
    barcode = models.CharField(
        max_length=128,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        help_text="Primary product barcode. Must be unique.",
    )
    sku = models.CharField(
        max_length=128,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        help_text="Internal stock keeping unit. Must be unique.",
    )
    cost_price = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Product cost price.",
    )
    selling_price = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Default product selling price.",
    )
    min_price = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Minimum allowed selling price.",
    )
    unit = models.ForeignKey(
        Unit,
        on_delete=models.PROTECT,
        related_name="products",
        help_text="Measurement unit used for this product.",
    )
    image = models.ImageField(
        upload_to="catalog/products/",
        blank=True,
        null=True,
        help_text="Primary product image.",
    )
    weight = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.000"))],
        help_text="Optional product weight.",
    )
    volume = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.000"))],
        help_text="Optional product volume.",
    )
    is_active = models.BooleanField(
        default=True, help_text="Whether the product is active."
    )
    has_expiry_date = models.BooleanField(
        default=False,
        help_text="Whether stock for this product should track expiry dates.",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_products",
        help_text="User who created the product.",
    )

    class Meta(BaseModel.Meta):
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["slug"]),
            models.Index(fields=["sku"]),
            models.Index(fields=["barcode"]),
            models.Index(fields=["category", "is_active"]),
            models.Index(fields=["brand", "is_active"]),
        ]

    def clean(self):
        if self.min_price > self.selling_price:
            raise ValidationError(
                {"min_price": "Minimum price cannot exceed selling price."}
            )

        if self.barcode:
            duplicate_barcodes = Barcode.objects.filter(code=self.barcode)
            if self.pk:
                duplicate_barcodes = duplicate_barcodes.exclude(product_id=self.pk)
            if duplicate_barcodes.exists():
                raise ValidationError(
                    {"barcode": "This barcode is already assigned to a product."}
                )

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = build_unique_slug(self)
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class BarcodeType(models.TextChoices):
    EAN13 = "EAN13", "EAN-13"
    EAN8 = "EAN8", "EAN-8"
    UPC = "UPC", "UPC"
    CODE128 = "CODE128", "Code 128"
    QR = "QR", "QR"
    OTHER = "OTHER", "Other"


class Barcode(BaseModel):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="barcodes",
        help_text="Product this barcode belongs to.",
    )
    code = models.CharField(
        max_length=128,
        unique=True,
        db_index=True,
        help_text="Unique barcode value.",
    )
    barcode_type = models.CharField(
        max_length=20,
        choices=BarcodeType.choices,
        default=BarcodeType.CODE128,
        help_text="Barcode standard or scanner format.",
    )

    class Meta(BaseModel.Meta):
        indexes = [
            models.Index(fields=["code"]),
            models.Index(fields=["barcode_type"]),
        ]

    def clean(self):
        duplicate_products = Product.objects.filter(barcode=self.code)
        if self.product_id:
            duplicate_products = duplicate_products.exclude(pk=self.product_id)
        if duplicate_products.exists():
            raise ValidationError(
                {"code": "This barcode is already used as a primary barcode."}
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.code


class ProductImage(BaseModel):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="images",
        help_text="Product this image belongs to.",
    )
    image = models.ImageField(
        upload_to="catalog/product-images/", help_text="Product image file."
    )
    is_main = models.BooleanField(
        default=False, help_text="Whether this image is the main image."
    )

    class Meta(BaseModel.Meta):
        indexes = [models.Index(fields=["product", "is_main"])]
        constraints = [
            models.UniqueConstraint(
                fields=["product"],
                condition=Q(is_main=True, deleted_at__isnull=True),
                name="unique_main_image_per_product",
            )
        ]

    def __str__(self):
        return f"{self.product.name} image"
