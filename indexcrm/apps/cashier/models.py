from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models

from apps.common.models import BaseModel


class CashierShift(BaseModel):
    cashier = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="cashier_shifts",
        help_text="Cashier who owns this shift.",
    )
    branch = models.ForeignKey(
        "stores.Branch",
        on_delete=models.PROTECT,
        related_name="cashier_shifts",
        help_text="Branch where the shift is opened.",
    )
    opened_at = models.DateTimeField(help_text="Shift opening date and time.")
    closed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Shift closing date and time.",
    )
    opening_balance = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Cash amount at shift opening.",
    )
    closing_balance = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Counted cash amount at shift close.",
    )
    expected_balance = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Expected cash balance calculated from cash payments.",
    )
    difference = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Difference between counted and expected cash.",
    )

    class Meta(BaseModel.Meta):
        indexes = [
            models.Index(fields=["cashier", "opened_at"]),
            models.Index(fields=["branch", "opened_at"]),
            models.Index(fields=["closed_at"]),
        ]

    @property
    def is_open(self):
        return self.closed_at is None

    def clean(self):
        if self.closed_at and self.closed_at < self.opened_at:
            raise ValidationError(
                {"closed_at": "Closed time cannot be before opened time."}
            )

    def __str__(self):
        return f"{self.cashier} shift {self.opened_at:%Y-%m-%d %H:%M}"
