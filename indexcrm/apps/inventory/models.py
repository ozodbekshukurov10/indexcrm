from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import F, Q
from django.utils import timezone

from apps.common.models import BaseModel


class Warehouse(BaseModel):
    branch = models.ForeignKey(
        "stores.Branch",
        on_delete=models.CASCADE,
        related_name="warehouses",
        help_text="Branch that owns this warehouse.",
    )
    name = models.CharField(max_length=255, help_text="Warehouse name.")
    is_active = models.BooleanField(
        default=True, help_text="Whether the warehouse is active."
    )

    class Meta(BaseModel.Meta):
        indexes = [
            models.Index(fields=["branch", "is_active"]),
            models.Index(fields=["name"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["branch", "name"],
                condition=Q(deleted_at__isnull=True),
                name="unique_active_warehouse_name_per_branch",
            )
        ]

    def __str__(self):
        return f"{self.branch.name} - {self.name}"


class Stock(BaseModel):
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.CASCADE,
        related_name="stocks",
        help_text="Warehouse holding the stock.",
    )
    product = models.ForeignKey(
        "catalog.Product",
        on_delete=models.PROTECT,
        related_name="stocks",
        help_text="Product held in stock.",
    )
    quantity = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        default=Decimal("0.000"),
        validators=[MinValueValidator(Decimal("0.000"))],
        help_text="Current physical stock quantity.",
    )
    reserved_quantity = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        default=Decimal("0.000"),
        validators=[MinValueValidator(Decimal("0.000"))],
        help_text="Quantity reserved for pending operations.",
    )
    low_stock_limit = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        default=Decimal("0.000"),
        validators=[MinValueValidator(Decimal("0.000"))],
        help_text="Threshold used for low stock alerts.",
    )

    class Meta(BaseModel.Meta):
        indexes = [
            models.Index(fields=["warehouse", "product"]),
            models.Index(fields=["warehouse", "updated_at"]),
            models.Index(fields=["product"]),
            models.Index(fields=["quantity", "low_stock_limit"]),
            models.Index(fields=["updated_at"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["warehouse", "product"],
                condition=Q(deleted_at__isnull=True),
                name="unique_active_stock_per_warehouse_product",
            ),
            models.CheckConstraint(
                condition=Q(quantity__gte=Decimal("0.000")),
                name="stock_quantity_non_negative",
            ),
            models.CheckConstraint(
                condition=Q(reserved_quantity__gte=Decimal("0.000")),
                name="stock_reserved_quantity_non_negative",
            ),
            models.CheckConstraint(
                condition=Q(low_stock_limit__gte=Decimal("0.000")),
                name="stock_low_limit_non_negative",
            ),
            models.CheckConstraint(
                condition=Q(quantity__gte=F("reserved_quantity")),
                name="stock_quantity_covers_reserved_quantity",
            ),
        ]

    @property
    def available_quantity(self):
        return self.quantity - self.reserved_quantity

    @property
    def is_low_stock(self):
        return self.quantity <= self.low_stock_limit

    def clean(self):
        if self.quantity < Decimal("0.000"):
            raise ValidationError({"quantity": "Stock quantity cannot be negative."})
        if self.reserved_quantity < Decimal("0.000"):
            raise ValidationError(
                {"reserved_quantity": "Reserved quantity cannot be negative."}
            )
        if self.low_stock_limit < Decimal("0.000"):
            raise ValidationError(
                {"low_stock_limit": "Low stock limit cannot be negative."}
            )
        if self.reserved_quantity > self.quantity:
            raise ValidationError(
                {"reserved_quantity": "Reserved quantity cannot exceed stock quantity."}
            )

    def __str__(self):
        return f"{self.product.name} @ {self.warehouse.name}"


class StockMovementType(models.TextChoices):
    IN = "IN", "In"
    OUT = "OUT", "Out"
    TRANSFER = "TRANSFER", "Transfer"
    ADJUSTMENT = "ADJUSTMENT", "Adjustment"


class StockMovement(BaseModel):
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.PROTECT,
        related_name="stock_movements",
        help_text="Warehouse affected by the movement.",
    )
    product = models.ForeignKey(
        "catalog.Product",
        on_delete=models.PROTECT,
        related_name="stock_movements",
        help_text="Product affected by the movement.",
    )
    movement_type = models.CharField(
        max_length=20,
        choices=StockMovementType.choices,
        help_text="Type of stock movement.",
    )
    quantity = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        validators=[MinValueValidator(Decimal("0.001"))],
        help_text="Quantity moved. For adjustments this is the absolute changed amount.",
    )
    expiry_date = models.DateField(
        null=True,
        blank=True,
        help_text="Optional expiry date for products that require expiry tracking.",
    )
    note = models.TextField(blank=True, help_text="Optional movement note.")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="stock_movements",
        help_text="User who initiated the movement.",
    )

    class Meta(BaseModel.Meta):
        indexes = [
            models.Index(fields=["warehouse", "product", "created_at"]),
            models.Index(fields=["movement_type", "created_at"]),
            models.Index(fields=["product", "expiry_date"]),
            models.Index(fields=["created_by", "created_at"]),
        ]

    def __str__(self):
        return f"{self.movement_type} {self.quantity} {self.product.name}"


class InventoryAdjustment(BaseModel):
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.PROTECT,
        related_name="inventory_adjustments",
        help_text="Warehouse where the inventory adjustment was counted.",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="inventory_adjustments",
        help_text="User who created the adjustment.",
    )
    note = models.TextField(blank=True, help_text="Adjustment note or reason.")
    adjustment_date = models.DateTimeField(
        default=timezone.now,
        help_text="Date and time of the stock count or adjustment.",
    )

    class Meta(BaseModel.Meta):
        indexes = [
            models.Index(fields=["warehouse", "adjustment_date"]),
            models.Index(fields=["created_by", "adjustment_date"]),
        ]

    def __str__(self):
        return (
            f"Adjustment for {self.warehouse.name} on {self.adjustment_date:%Y-%m-%d}"
        )
