from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count, DecimalField, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.utils import timezone

from apps.cashier.models import CashierShift
from apps.sales.models import Refund, Sale, SalePayment, SalePaymentMethod, SaleStatus

MONEY_QUANT = Decimal("0.01")


def _authenticated_user(user):
    return user if getattr(user, "is_authenticated", False) else None


def get_active_cashier_shift(*, cashier, branch=None):
    cashier = _authenticated_user(cashier)
    if cashier is None:
        return None

    queryset = CashierShift.objects.select_related("cashier", "branch").filter(
        cashier=cashier,
        closed_at__isnull=True,
    )
    if branch is not None:
        queryset = queryset.filter(branch=branch)
    return queryset.order_by("-opened_at").first()


def require_active_cashier_shift(*, cashier, branch):
    shift = get_active_cashier_shift(cashier=cashier, branch=branch)
    if shift is None:
        raise ValidationError(
            {"shift": "An active cashier shift is required before checkout."}
        )
    return shift


@transaction.atomic
def open_cashier_shift(
    *, cashier, branch, opening_balance=Decimal("0.00"), opened_at=None
):
    cashier = _authenticated_user(cashier)
    if cashier is None:
        raise ValidationError({"cashier": "Authenticated cashier is required."})

    existing_shift = CashierShift.objects.select_for_update().filter(
        cashier=cashier,
        branch=branch,
        closed_at__isnull=True,
    )
    if existing_shift.exists():
        raise ValidationError(
            {"shift": "Cashier already has an open shift for this branch."}
        )

    return CashierShift.objects.create(
        cashier=cashier,
        branch=branch,
        opened_at=opened_at or timezone.now(),
        opening_balance=Decimal(str(opening_balance)).quantize(MONEY_QUANT),
    )


def calculate_shift_totals(shift: CashierShift, *, closed_at=None):
    end_time = closed_at or shift.closed_at or timezone.now()
    sale_filter = Q(
        sale__cashier=shift.cashier,
        sale__branch=shift.branch,
        sale__sale_date__gte=shift.opened_at,
        sale__sale_date__lte=end_time,
        sale__status__in=[SaleStatus.COMPLETED, SaleStatus.REFUNDED],
    )
    payment_totals = SalePayment.objects.filter(sale_filter).aggregate(
        cash_total=Coalesce(
            Sum("amount", filter=Q(payment_method=SalePaymentMethod.CASH)),
            Value(Decimal("0.00")),
            output_field=DecimalField(max_digits=14, decimal_places=2),
        ),
        card_total=Coalesce(
            Sum("amount", filter=Q(payment_method=SalePaymentMethod.CARD)),
            Value(Decimal("0.00")),
            output_field=DecimalField(max_digits=14, decimal_places=2),
        ),
        click_total=Coalesce(
            Sum("amount", filter=Q(payment_method=SalePaymentMethod.CLICK)),
            Value(Decimal("0.00")),
            output_field=DecimalField(max_digits=14, decimal_places=2),
        ),
        payme_total=Coalesce(
            Sum("amount", filter=Q(payment_method=SalePaymentMethod.PAYME)),
            Value(Decimal("0.00")),
            output_field=DecimalField(max_digits=14, decimal_places=2),
        ),
        debt_total=Coalesce(
            Sum("amount", filter=Q(payment_method=SalePaymentMethod.DEBT)),
            Value(Decimal("0.00")),
            output_field=DecimalField(max_digits=14, decimal_places=2),
        ),
    )
    sale_totals = Sale.objects.filter(
        cashier=shift.cashier,
        branch=shift.branch,
        sale_date__gte=shift.opened_at,
        sale_date__lte=end_time,
        status__in=[SaleStatus.COMPLETED, SaleStatus.REFUNDED],
    ).aggregate(
        sale_count=Count("id"),
        total_sales=Coalesce(
            Sum("total_amount"),
            Value(Decimal("0.00")),
            output_field=DecimalField(max_digits=14, decimal_places=2),
        ),
    )
    refund_total = Refund.objects.filter(
        cashier=shift.cashier,
        original_sale__branch=shift.branch,
        refund_date__gte=shift.opened_at,
        refund_date__lte=end_time,
    ).aggregate(
        total=Coalesce(
            Sum("total_amount"),
            Value(Decimal("0.00")),
            output_field=DecimalField(max_digits=14, decimal_places=2),
        )
    )[
        "total"
    ]
    expected_balance = (
        shift.opening_balance + payment_totals["cash_total"] - refund_total
    ).quantize(MONEY_QUANT)
    return {
        **payment_totals,
        **sale_totals,
        "refund_total": refund_total,
        "expected_balance": expected_balance,
    }


@transaction.atomic
def close_cashier_shift(*, shift: CashierShift, closing_balance, closed_at=None):
    shift = (
        CashierShift.objects.select_for_update()
        .select_related("cashier", "branch")
        .get(pk=shift.pk)
    )
    if not shift.is_open:
        raise ValidationError({"shift": "Cashier shift is already closed."})

    closing_balance = Decimal(str(closing_balance)).quantize(MONEY_QUANT)
    closed_at = closed_at or timezone.now()
    totals = calculate_shift_totals(shift, closed_at=closed_at)

    shift.closed_at = closed_at
    shift.closing_balance = closing_balance
    shift.expected_balance = totals["expected_balance"]
    shift.difference = (closing_balance - shift.expected_balance).quantize(MONEY_QUANT)
    shift.full_clean()
    shift.save(
        update_fields=(
            "closed_at",
            "closing_balance",
            "expected_balance",
            "difference",
            "updated_at",
        )
    )
    return shift
