from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone

from apps.common.models import BaseModel

MONEY_QUANT = Decimal("0.01")


class CashTransactionType(models.TextChoices):
    INCOME = "INCOME", "Income"
    EXPENSE = "EXPENSE", "Expense"
    SALE = "SALE", "Sale"
    PURCHASE = "PURCHASE", "Purchase"
    REFUND = "REFUND", "Refund"
    ADJUSTMENT = "ADJUSTMENT", "Adjustment"


class CashBox(BaseModel):
    branch = models.ForeignKey(
        "stores.Branch",
        on_delete=models.PROTECT,
        related_name="cashboxes",
        help_text="Branch this cashbox belongs to.",
    )
    name = models.CharField(max_length=255, help_text="Cashbox display name.")
    current_balance = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Current calculated cashbox balance.",
    )
    is_active = models.BooleanField(
        default=True, help_text="Whether this cashbox is active."
    )

    class Meta(BaseModel.Meta):
        verbose_name = "cash box"
        verbose_name_plural = "cash boxes"
        indexes = [
            models.Index(fields=["branch", "is_active"]),
            models.Index(fields=["name"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["branch", "name"],
                condition=Q(deleted_at__isnull=True),
                name="unique_active_cashbox_name_per_branch",
            )
        ]

    def __str__(self):
        return f"{self.branch.name} - {self.name}"


class CashTransaction(BaseModel):
    cashbox = models.ForeignKey(
        CashBox,
        on_delete=models.PROTECT,
        related_name="transactions",
        help_text="Cashbox affected by this transaction.",
    )
    transaction_type = models.CharField(
        max_length=20,
        choices=CashTransactionType.choices,
        help_text="Financial transaction type.",
    )
    amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        help_text="Transaction amount. Adjustments may be positive or negative.",
    )
    reference_type = models.CharField(
        max_length=64,
        blank=True,
        db_index=True,
        help_text="External or internal object type this transaction refers to.",
    )
    reference_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="UUID of the related object, when available.",
    )
    note = models.TextField(blank=True, help_text="Transaction note.")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cash_transactions",
        help_text="User who created this transaction.",
    )

    class Meta(BaseModel.Meta):
        verbose_name = "cash transaction"
        verbose_name_plural = "cash transactions"
        indexes = [
            models.Index(fields=["cashbox", "created_at"]),
            models.Index(fields=["cashbox", "transaction_type", "created_at"]),
            models.Index(fields=["transaction_type", "created_at"]),
            models.Index(fields=["reference_type", "reference_id"]),
            models.Index(fields=["created_by", "created_at"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["transaction_type", "reference_type", "reference_id"],
                condition=Q(
                    deleted_at__isnull=True,
                    reference_type__gt="",
                    reference_id__isnull=False,
                ),
                name="unique_active_cash_transaction_reference",
            )
        ]

    def clean(self):
        if self.transaction_type == CashTransactionType.ADJUSTMENT:
            if self.amount == Decimal("0.00"):
                raise ValidationError({"amount": "Adjustment amount cannot be zero."})
            return

        if self.amount <= Decimal("0.00"):
            raise ValidationError({"amount": "Amount must be greater than zero."})

    def __str__(self):
        reference = f" ({self.reference_type})" if self.reference_type else ""
        return f"{self.transaction_type} {self.amount} - {self.cashbox}{reference}"


class ExpenseCategory(BaseModel):
    name = models.CharField(max_length=255, help_text="Expense category name.")
    description = models.TextField(blank=True, help_text="Expense category details.")

    class Meta(BaseModel.Meta):
        verbose_name = "expense category"
        verbose_name_plural = "expense categories"
        indexes = [models.Index(fields=["name"])]
        constraints = [
            models.UniqueConstraint(
                fields=["name"],
                condition=Q(deleted_at__isnull=True),
                name="unique_active_expense_category_name",
            )
        ]

    def __str__(self):
        return self.name


class Expense(BaseModel):
    cashbox = models.ForeignKey(
        CashBox,
        on_delete=models.PROTECT,
        related_name="expenses",
        help_text="Cashbox used for the expense.",
    )
    category = models.ForeignKey(
        ExpenseCategory,
        on_delete=models.PROTECT,
        related_name="expenses",
        help_text="Expense category.",
    )
    amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
        help_text="Expense amount.",
    )
    note = models.TextField(blank=True, help_text="Expense note.")
    expense_date = models.DateTimeField(
        default=timezone.now,
        help_text="Expense date and time.",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="expenses",
        help_text="User who recorded this expense.",
    )

    class Meta(BaseModel.Meta):
        verbose_name = "expense"
        verbose_name_plural = "expenses"
        indexes = [
            models.Index(fields=["cashbox", "expense_date"]),
            models.Index(fields=["cashbox", "category", "expense_date"]),
            models.Index(fields=["category", "expense_date"]),
            models.Index(fields=["created_by", "expense_date"]),
        ]

    def __str__(self):
        return f"{self.category.name} {self.amount} - {self.cashbox.name}"


class Income(BaseModel):
    cashbox = models.ForeignKey(
        CashBox,
        on_delete=models.PROTECT,
        related_name="incomes",
        help_text="Cashbox receiving this income.",
    )
    amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
        help_text="Income amount.",
    )
    source = models.CharField(
        max_length=255,
        help_text="Income source, such as owner deposit or other revenue.",
    )
    note = models.TextField(blank=True, help_text="Income note.")
    income_date = models.DateTimeField(
        default=timezone.now,
        help_text="Income date and time.",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="incomes",
        help_text="User who recorded this income.",
    )

    class Meta(BaseModel.Meta):
        verbose_name = "income"
        verbose_name_plural = "incomes"
        indexes = [
            models.Index(fields=["cashbox", "income_date"]),
            models.Index(fields=["source"]),
            models.Index(fields=["created_by", "income_date"]),
        ]

    def __str__(self):
        return f"{self.source} {self.amount} - {self.cashbox.name}"


class DailyClosing(BaseModel):
    branch = models.ForeignKey(
        "stores.Branch",
        on_delete=models.PROTECT,
        related_name="daily_closings",
        help_text="Branch being closed.",
    )
    cashier = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="daily_closings",
        help_text="Cashier responsible for this closing.",
    )
    cashier_shift = models.OneToOneField(
        "cashier.CashierShift",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="daily_closing",
        help_text="Closed cashier shift attached to this daily closing.",
    )
    total_sales = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Total sales during the closing period.",
    )
    total_expenses = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Total expenses during the closing period.",
    )
    total_income = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Total additional income during the closing period.",
    )
    expected_cash = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Expected cash amount at close.",
    )
    actual_cash = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Manually counted cash amount.",
    )
    difference = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Difference between actual and expected cash.",
    )
    closed_at = models.DateTimeField(
        default=timezone.now,
        help_text="Date and time when the closing was completed.",
    )

    class Meta(BaseModel.Meta):
        verbose_name = "daily closing"
        verbose_name_plural = "daily closings"
        indexes = [
            models.Index(fields=["branch", "closed_at"]),
            models.Index(fields=["cashier", "closed_at"]),
        ]

    def clean(self):
        if self.cashier_shift_id:
            if self.cashier_shift.branch_id != self.branch_id:
                raise ValidationError(
                    {"cashier_shift": "Shift branch must match closing branch."}
                )
            if self.cashier_shift.cashier_id != self.cashier_id:
                raise ValidationError(
                    {"cashier_shift": "Shift cashier must match closing cashier."}
                )
            if self.cashier_shift.closed_at is None:
                raise ValidationError(
                    {"cashier_shift": "Cashier shift must be closed first."}
                )

    def __str__(self):
        return f"{self.branch.name} closing {self.closed_at:%Y-%m-%d}"
