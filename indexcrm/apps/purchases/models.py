from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone

from apps.common.models import BaseModel

MONEY_QUANT = Decimal("0.01")


class PaymentMethod(models.TextChoices):
    CASH = "CASH", "Cash"
    CARD = "CARD", "Card"
    BANK_TRANSFER = "BANK_TRANSFER", "Bank transfer"
    CLICK = "CLICK", "Click"
    PAYME = "PAYME", "Payme"
    OTHER = "OTHER", "Other"


class Supplier(BaseModel):
    company_name = models.CharField(
        max_length=255,
        help_text="Supplier company or trade name.",
    )
    full_name = models.CharField(
        max_length=255,
        blank=True,
        help_text="Primary supplier contact person.",
    )
    phone = models.CharField(
        max_length=32, blank=True, help_text="Primary phone number."
    )
    extra_phone = models.CharField(
        max_length=32,
        blank=True,
        help_text="Additional phone number.",
    )
    email = models.EmailField(blank=True, help_text="Supplier email address.")
    address = models.TextField(blank=True, help_text="Supplier address.")
    inn_or_tax_number = models.CharField(
        max_length=64,
        blank=True,
        db_index=True,
        help_text="Supplier INN or tax identification number.",
    )
    notes = models.TextField(blank=True, help_text="Internal supplier notes.")
    balance = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Current debt owed to this supplier.",
    )
    is_active = models.BooleanField(
        default=True, help_text="Whether the supplier is active."
    )

    class Meta(BaseModel.Meta):
        indexes = [
            models.Index(fields=["company_name"]),
            models.Index(fields=["full_name"]),
            models.Index(fields=["phone"]),
            models.Index(fields=["inn_or_tax_number"]),
            models.Index(fields=["is_active"]),
        ]

    def clean(self):
        if self.balance < Decimal("0.00"):
            raise ValidationError({"balance": "Supplier balance cannot be negative."})

    def __str__(self):
        return self.company_name


class SupplierContact(BaseModel):
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.CASCADE,
        related_name="contacts",
        help_text="Supplier this contact belongs to.",
    )
    full_name = models.CharField(max_length=255, help_text="Contact full name.")
    position = models.CharField(
        max_length=255, blank=True, help_text="Contact position."
    )
    phone = models.CharField(
        max_length=32, blank=True, help_text="Contact phone number."
    )
    email = models.EmailField(blank=True, help_text="Contact email address.")

    class Meta(BaseModel.Meta):
        indexes = [
            models.Index(fields=["supplier", "full_name"]),
            models.Index(fields=["phone"]),
            models.Index(fields=["email"]),
        ]

    def __str__(self):
        return f"{self.full_name} - {self.supplier.company_name}"


class SupplierPayment(BaseModel):
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.PROTECT,
        related_name="payments",
        help_text="Supplier receiving the payment.",
    )
    cashbox = models.ForeignKey(
        "finance.CashBox",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="supplier_payments",
        help_text="Optional cashbox used for this supplier debt payment.",
    )
    amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
        help_text="Payment amount.",
    )
    payment_method = models.CharField(
        max_length=32,
        choices=PaymentMethod.choices,
        default=PaymentMethod.CASH,
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
        related_name="supplier_payments",
        help_text="User who created this supplier payment.",
    )

    class Meta(BaseModel.Meta):
        indexes = [
            models.Index(fields=["supplier", "paid_at"]),
            models.Index(fields=["cashbox", "paid_at"]),
            models.Index(fields=["payment_method", "paid_at"]),
            models.Index(fields=["created_by", "paid_at"]),
        ]

    def __str__(self):
        cashbox_name = f" via {self.cashbox.name}" if self.cashbox_id else ""
        return f"{self.supplier.company_name} payment {self.amount}{cashbox_name}"


class PurchaseStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    CONFIRMED = "CONFIRMED", "Confirmed"
    CANCELLED = "CANCELLED", "Cancelled"


class Purchase(BaseModel):
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.PROTECT,
        related_name="purchases",
        help_text="Supplier for this purchase.",
    )
    warehouse = models.ForeignKey(
        "inventory.Warehouse",
        on_delete=models.PROTECT,
        related_name="purchases",
        help_text="Warehouse that receives purchased products.",
    )
    invoice_number = models.CharField(
        max_length=128,
        db_index=True,
        help_text="Supplier invoice number.",
    )
    purchase_date = models.DateTimeField(
        default=timezone.now,
        help_text="Purchase date and time.",
    )
    status = models.CharField(
        max_length=20,
        choices=PurchaseStatus.choices,
        default=PurchaseStatus.DRAFT,
        help_text="Current purchase workflow status.",
    )
    subtotal = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Sum of purchase item totals before discount and tax.",
    )
    discount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Purchase-level discount amount.",
    )
    tax_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Purchase-level tax amount.",
    )
    total_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Final purchase amount after discount and tax.",
    )
    paid_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Amount already paid for this purchase.",
    )
    remaining_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Remaining debt for this purchase.",
    )
    note = models.TextField(blank=True, help_text="Purchase note.")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_purchases",
        help_text="User who created the purchase.",
    )
    confirmed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="confirmed_purchases",
        help_text="User who confirmed the purchase.",
    )
    confirmed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Date and time when the purchase was confirmed.",
    )

    class Meta(BaseModel.Meta):
        indexes = [
            models.Index(fields=["invoice_number"]),
            models.Index(fields=["status", "purchase_date"]),
            models.Index(fields=["supplier", "status"]),
            models.Index(fields=["supplier", "status", "purchase_date"]),
            models.Index(fields=["warehouse", "status"]),
            models.Index(fields=["warehouse", "status", "purchase_date"]),
            models.Index(fields=["created_by", "created_at"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["invoice_number"],
                condition=Q(deleted_at__isnull=True),
                name="unique_active_purchase_invoice_number",
            ),
            models.CheckConstraint(
                condition=Q(subtotal__gte=Decimal("0.00")),
                name="purchase_subtotal_non_negative",
            ),
            models.CheckConstraint(
                condition=Q(discount__gte=Decimal("0.00")),
                name="purchase_discount_non_negative",
            ),
            models.CheckConstraint(
                condition=Q(tax_amount__gte=Decimal("0.00")),
                name="purchase_tax_amount_non_negative",
            ),
            models.CheckConstraint(
                condition=Q(total_amount__gte=Decimal("0.00")),
                name="purchase_total_amount_non_negative",
            ),
            models.CheckConstraint(
                condition=Q(paid_amount__gte=Decimal("0.00")),
                name="purchase_paid_amount_non_negative",
            ),
            models.CheckConstraint(
                condition=Q(remaining_amount__gte=Decimal("0.00")),
                name="purchase_remaining_amount_non_negative",
            ),
        ]

    @property
    def is_editable(self):
        return self.status == PurchaseStatus.DRAFT

    def calculate_amounts(self, subtotal=None, paid_amount=None):
        subtotal = self.subtotal if subtotal is None else subtotal
        paid_amount = self.paid_amount if paid_amount is None else paid_amount
        subtotal = Decimal(str(subtotal)).quantize(MONEY_QUANT)
        paid_amount = Decimal(str(paid_amount)).quantize(MONEY_QUANT)
        total_amount = (subtotal - self.discount + self.tax_amount).quantize(
            MONEY_QUANT
        )

        if self.discount > subtotal:
            raise ValidationError({"discount": "Discount cannot exceed subtotal."})
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

    def __str__(self):
        return f"{self.invoice_number} - {self.supplier.company_name}"


class PurchaseItem(BaseModel):
    purchase = models.ForeignKey(
        Purchase,
        on_delete=models.CASCADE,
        related_name="items",
        help_text="Purchase this item belongs to.",
    )
    product = models.ForeignKey(
        "catalog.Product",
        on_delete=models.PROTECT,
        related_name="purchase_items",
        help_text="Purchased product.",
    )
    quantity = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        validators=[MinValueValidator(Decimal("0.001"))],
        help_text="Purchased quantity.",
    )
    purchase_price = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Unit purchase price.",
    )
    total_price = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Calculated item total.",
    )
    expiry_date = models.DateField(
        null=True,
        blank=True,
        help_text="Optional expiry date for products that expire.",
    )

    class Meta(BaseModel.Meta):
        indexes = [
            models.Index(fields=["purchase", "product"]),
            models.Index(fields=["product", "expiry_date"]),
        ]

    def clean(self):
        if self.purchase_id and not self.purchase.is_editable:
            raise ValidationError(
                {"purchase": "Cannot edit items after purchase confirmation."}
            )
        if self.product_id and self.product.has_expiry_date and not self.expiry_date:
            raise ValidationError(
                {"expiry_date": "Expiry date is required for this product."}
            )

    def save(self, *args, **kwargs):
        self.total_price = (self.quantity * self.purchase_price).quantize(MONEY_QUANT)
        self.full_clean()
        super().save(*args, **kwargs)

    def delete(self, using=None, keep_parents=False):
        if not self.purchase.is_editable:
            raise ValidationError(
                {"purchase": "Cannot delete items after purchase confirmation."}
            )
        return super().delete(using=using, keep_parents=keep_parents)

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"


class PurchasePayment(BaseModel):
    purchase = models.ForeignKey(
        Purchase,
        on_delete=models.PROTECT,
        related_name="payments",
        help_text="Purchase this payment belongs to.",
    )
    amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
        help_text="Payment amount.",
    )
    payment_method = models.CharField(
        max_length=32,
        choices=PaymentMethod.choices,
        default=PaymentMethod.CASH,
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
        related_name="purchase_payments",
        help_text="User who created this purchase payment.",
    )

    class Meta(BaseModel.Meta):
        indexes = [
            models.Index(fields=["purchase", "paid_at"]),
            models.Index(fields=["payment_method", "paid_at"]),
            models.Index(fields=["created_by", "paid_at"]),
        ]

    def __str__(self):
        return f"{self.purchase.invoice_number} payment {self.amount}"
