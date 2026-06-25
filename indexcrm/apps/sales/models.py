import uuid
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone

from apps.common.models import BaseModel

MONEY_QUANT = Decimal("0.01")


class CustomerPaymentMethod(models.TextChoices):
    CASH = "CASH", "Cash"
    CARD = "CARD", "Card"
    BANK_TRANSFER = "BANK_TRANSFER", "Bank transfer"
    CLICK = "CLICK", "Click"
    PAYME = "PAYME", "Payme"
    OTHER = "OTHER", "Other"


class SalePaymentMethod(models.TextChoices):
    CASH = "CASH", "Cash"
    CARD = "CARD", "Card"
    CLICK = "CLICK", "Click"
    PAYME = "PAYME", "Payme"
    DEBT = "DEBT", "Debt"
    MIXED = "MIXED", "Mixed"


class Customer(BaseModel):
    full_name = models.CharField(max_length=255, help_text="Customer full name.")
    phone = models.CharField(
        max_length=32, blank=True, help_text="Primary phone number."
    )
    extra_phone = models.CharField(
        max_length=32,
        blank=True,
        help_text="Additional phone number.",
    )
    address = models.TextField(blank=True, help_text="Customer address.")
    balance = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Current customer debt balance.",
    )
    bonus_balance = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Customer bonus balance for future loyalty use.",
    )
    is_active = models.BooleanField(
        default=True, help_text="Whether the customer is active."
    )
    notes = models.TextField(blank=True, help_text="Internal customer notes.")

    class Meta(BaseModel.Meta):
        indexes = [
            models.Index(fields=["full_name"]),
            models.Index(fields=["phone"]),
            models.Index(fields=["is_active"]),
            models.Index(fields=["balance"]),
        ]

    def clean(self):
        if self.balance < Decimal("0.00"):
            raise ValidationError({"balance": "Customer balance cannot be negative."})
        if self.bonus_balance < Decimal("0.00"):
            raise ValidationError(
                {"bonus_balance": "Bonus balance cannot be negative."}
            )

    def __str__(self):
        return self.full_name


class CustomerPayment(BaseModel):
    customer = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,
        related_name="payments",
        help_text="Customer making the debt payment.",
    )
    cashbox = models.ForeignKey(
        "finance.CashBox",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="customer_payments",
        help_text="Optional cashbox receiving this customer debt payment.",
    )
    amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
        help_text="Payment amount.",
    )
    payment_method = models.CharField(
        max_length=32,
        choices=CustomerPaymentMethod.choices,
        default=CustomerPaymentMethod.CASH,
        help_text="Payment method used.",
    )
    note = models.TextField(blank=True, help_text="Payment note.")
    paid_at = models.DateTimeField(
        default=timezone.now, help_text="Payment date and time."
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="customer_payments",
        help_text="User who recorded this customer payment.",
    )

    class Meta(BaseModel.Meta):
        indexes = [
            models.Index(fields=["customer", "paid_at"]),
            models.Index(fields=["cashbox", "paid_at"]),
            models.Index(fields=["payment_method", "paid_at"]),
            models.Index(fields=["created_by", "paid_at"]),
        ]

    def __str__(self):
        cashbox_name = f" via {self.cashbox.name}" if self.cashbox_id else ""
        return f"{self.customer.full_name} payment {self.amount}{cashbox_name}"


class LoyaltyAccount(BaseModel):
    customer = models.OneToOneField(
        Customer,
        on_delete=models.CASCADE,
        related_name="loyalty_account",
        help_text="Customer attached to this loyalty account.",
    )
    points = models.PositiveIntegerField(default=0, help_text="Current loyalty points.")
    level = models.CharField(
        max_length=64, default="standard", help_text="Loyalty level."
    )
    total_spent = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Total completed sale amount for loyalty calculations.",
    )

    class Meta(BaseModel.Meta):
        indexes = [
            models.Index(fields=["level"]),
            models.Index(fields=["total_spent"]),
        ]

    def __str__(self):
        return f"{self.customer.full_name} loyalty account"


class SaleStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    COMPLETED = "COMPLETED", "Completed"
    CANCELLED = "CANCELLED", "Cancelled"
    REFUNDED = "REFUNDED", "Refunded"


def generate_receipt_number():
    timestamp = timezone.now().strftime("%Y%m%d%H%M%S")
    suffix = uuid.uuid4().hex[:6].upper()
    return f"R-{timestamp}-{suffix}"


class Sale(BaseModel):
    branch = models.ForeignKey(
        "stores.Branch",
        on_delete=models.PROTECT,
        related_name="sales",
        help_text="Branch where the sale happened.",
    )
    warehouse = models.ForeignKey(
        "inventory.Warehouse",
        on_delete=models.PROTECT,
        related_name="sales",
        help_text="Warehouse that supplies stock for this sale.",
    )
    cashier = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="sales",
        help_text="Cashier who created or completed the sale.",
    )
    customer = models.ForeignKey(
        Customer,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sales",
        help_text="Optional customer for debt and loyalty tracking.",
    )
    receipt_number = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        blank=True,
        help_text="Generated receipt number.",
    )
    idempotency_key = models.CharField(
        max_length=128,
        null=True,
        blank=True,
        help_text="Optional client-generated key used to safely retry checkout creation.",
    )
    idempotency_fingerprint = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        help_text="Hash of the checkout payload used to detect unsafe idempotency key reuse.",
    )
    sale_date = models.DateTimeField(
        default=timezone.now, help_text="Sale date and time."
    )
    status = models.CharField(
        max_length=20,
        choices=SaleStatus.choices,
        default=SaleStatus.DRAFT,
        help_text="Current sale workflow status.",
    )
    subtotal = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Sum of sale item totals before sale-level discount and tax.",
    )
    discount_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Sale-level discount amount.",
    )
    tax_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Sale-level tax amount.",
    )
    total_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Final sale amount after discount and tax.",
    )
    paid_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Paid amount excluding debt allocations.",
    )
    remaining_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Remaining customer debt for this sale.",
    )
    note = models.TextField(blank=True, help_text="Sale note.")

    class Meta(BaseModel.Meta):
        indexes = [
            models.Index(fields=["receipt_number"]),
            models.Index(fields=["idempotency_key"]),
            models.Index(fields=["idempotency_fingerprint"]),
            models.Index(fields=["status", "sale_date"]),
            models.Index(fields=["branch", "status"]),
            models.Index(fields=["branch", "status", "sale_date"]),
            models.Index(fields=["warehouse", "status"]),
            models.Index(fields=["cashier", "sale_date"]),
            models.Index(fields=["cashier", "status", "sale_date"]),
            models.Index(fields=["customer", "sale_date"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(subtotal__gte=Decimal("0.00")),
                name="sale_subtotal_non_negative",
            ),
            models.CheckConstraint(
                condition=Q(discount_amount__gte=Decimal("0.00")),
                name="sale_discount_non_negative",
            ),
            models.CheckConstraint(
                condition=Q(tax_amount__gte=Decimal("0.00")),
                name="sale_tax_amount_non_negative",
            ),
            models.CheckConstraint(
                condition=Q(total_amount__gte=Decimal("0.00")),
                name="sale_total_amount_non_negative",
            ),
            models.CheckConstraint(
                condition=Q(paid_amount__gte=Decimal("0.00")),
                name="sale_paid_amount_non_negative",
            ),
            models.CheckConstraint(
                condition=Q(remaining_amount__gte=Decimal("0.00")),
                name="sale_remaining_amount_non_negative",
            ),
            models.UniqueConstraint(
                fields=["idempotency_key"],
                condition=Q(idempotency_key__isnull=False),
                name="unique_sale_idempotency_key",
            ),
        ]

    @property
    def is_editable(self):
        return self.status == SaleStatus.DRAFT

    def calculate_amounts(self, subtotal=None, paid_amount=None):
        subtotal = Decimal(
            str(self.subtotal if subtotal is None else subtotal)
        ).quantize(MONEY_QUANT)
        paid_amount = Decimal(
            str(self.paid_amount if paid_amount is None else paid_amount)
        ).quantize(MONEY_QUANT)
        total_amount = (subtotal - self.discount_amount + self.tax_amount).quantize(
            MONEY_QUANT
        )

        if self.discount_amount > subtotal:
            raise ValidationError(
                {"discount_amount": "Discount cannot exceed subtotal."}
            )
        if total_amount < Decimal("0.00"):
            raise ValidationError({"total_amount": "Total amount cannot be negative."})
        if paid_amount > total_amount:
            raise ValidationError(
                {"paid_amount": "Paid amount cannot exceed total amount."}
            )

        self.subtotal = subtotal
        self.total_amount = total_amount
        self.paid_amount = paid_amount
        self.remaining_amount = total_amount - paid_amount

    def clean(self):
        self.calculate_amounts()

    def save(self, *args, **kwargs):
        if not self.receipt_number:
            self.receipt_number = generate_receipt_number()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.receipt_number} - {self.customer.full_name if self.customer_id else 'walk-in'}"


class SaleItem(BaseModel):
    sale = models.ForeignKey(
        Sale,
        on_delete=models.CASCADE,
        related_name="items",
        help_text="Sale this item belongs to.",
    )
    product = models.ForeignKey(
        "catalog.Product",
        on_delete=models.PROTECT,
        related_name="sale_items",
        help_text="Sold product.",
    )
    quantity = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        validators=[MinValueValidator(Decimal("0.001"))],
        help_text="Sold quantity.",
    )
    price = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Unit sale price.",
    )
    discount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Item-level discount amount.",
    )
    total_price = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Calculated item total.",
    )

    class Meta(BaseModel.Meta):
        indexes = [
            models.Index(fields=["sale", "product"]),
            models.Index(fields=["product"]),
        ]

    def clean(self):
        if self.sale_id and not self.sale.is_editable:
            raise ValidationError({"sale": "Cannot edit items after sale completion."})
        gross_total = (self.quantity * self.price).quantize(MONEY_QUANT)
        if self.discount > gross_total:
            raise ValidationError(
                {"discount": "Item discount cannot exceed item total."}
            )

    def save(self, *args, **kwargs):
        self.total_price = ((self.quantity * self.price) - self.discount).quantize(
            MONEY_QUANT
        )
        self.full_clean()
        super().save(*args, **kwargs)

    def delete(self, using=None, keep_parents=False):
        if not self.sale.is_editable:
            raise ValidationError(
                {"sale": "Cannot delete items after sale completion."}
            )
        return super().delete(using=using, keep_parents=keep_parents)

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"


class SalePayment(BaseModel):
    sale = models.ForeignKey(
        Sale,
        on_delete=models.PROTECT,
        related_name="payments",
        help_text="Sale this payment belongs to.",
    )
    payment_method = models.CharField(
        max_length=32,
        choices=SalePaymentMethod.choices,
        default=SalePaymentMethod.CASH,
        help_text="Payment method used.",
    )
    amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
        help_text="Payment amount.",
    )
    note = models.TextField(blank=True, help_text="Payment note.")
    paid_at = models.DateTimeField(
        default=timezone.now, help_text="Payment date and time."
    )

    class Meta(BaseModel.Meta):
        indexes = [
            models.Index(fields=["sale", "paid_at"]),
            models.Index(fields=["payment_method", "paid_at"]),
        ]

    def clean(self):
        if self.sale_id and not self.sale.is_editable:
            raise ValidationError(
                {"sale": "Cannot edit payments after sale completion."}
            )

    def __str__(self):
        return f"{self.sale.receipt_number} {self.payment_method} {self.amount}"


class Refund(BaseModel):
    original_sale = models.ForeignKey(
        Sale,
        on_delete=models.PROTECT,
        related_name="refunds",
        help_text="Original sale being refunded.",
    )
    cashier = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="refunds",
        help_text="Cashier who created the refund.",
    )
    refund_date = models.DateTimeField(
        default=timezone.now, help_text="Refund date and time."
    )
    reason = models.TextField(help_text="Refund reason.")
    total_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Total refund amount.",
    )

    class Meta(BaseModel.Meta):
        indexes = [
            models.Index(fields=["original_sale", "refund_date"]),
            models.Index(fields=["cashier", "refund_date"]),
        ]

    def __str__(self):
        return f"Refund {self.original_sale.receipt_number}"


class RefundItem(BaseModel):
    refund = models.ForeignKey(
        Refund,
        on_delete=models.CASCADE,
        related_name="items",
        help_text="Refund this item belongs to.",
    )
    product = models.ForeignKey(
        "catalog.Product",
        on_delete=models.PROTECT,
        related_name="refund_items",
        help_text="Refunded product.",
    )
    quantity = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        validators=[MinValueValidator(Decimal("0.001"))],
        help_text="Refunded quantity.",
    )
    amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
        help_text="Refund amount for this item.",
    )

    class Meta(BaseModel.Meta):
        indexes = [
            models.Index(fields=["refund", "product"]),
            models.Index(fields=["product"]),
        ]

    def __str__(self):
        return f"{self.product.name} refund {self.quantity}"
