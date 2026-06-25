from calendar import monthrange
from datetime import date, datetime, time
from decimal import Decimal

from django.db.models import Case, Count, DecimalField, F, Q, Sum, Value, When
from django.db.models.functions import Coalesce, TruncDate, TruncMonth
from django.utils import timezone

from apps.finance.models import (
    MONEY_QUANT,
    CashBox,
    CashTransaction,
    CashTransactionType,
    Expense,
    Income,
)
from apps.purchases.models import Purchase, PurchaseStatus, Supplier
from apps.sales.models import Customer, Refund, Sale, SaleStatus


def _money_sum(queryset, field):
    return queryset.aggregate(
        total=Coalesce(
            Sum(field),
            Value(Decimal("0.00")),
            output_field=DecimalField(max_digits=14, decimal_places=2),
        )
    )["total"].quantize(MONEY_QUANT)


def _filter_date_range(queryset, field_name, date_from=None, date_to=None):
    if date_from:
        queryset = queryset.filter(**{f"{field_name}__gte": _day_start(date_from)})
    if date_to:
        queryset = queryset.filter(**{f"{field_name}__lte": _day_end(date_to)})
    return queryset


def _make_aware(value):
    if timezone.is_aware(value):
        return value
    return timezone.make_aware(value, timezone.get_current_timezone())


def _day_start(value):
    if isinstance(value, datetime):
        return _make_aware(value)
    return _make_aware(datetime.combine(value, time.min))


def _day_end(value):
    if isinstance(value, datetime):
        return _make_aware(value)
    return _make_aware(datetime.combine(value, time.max))


def cashbox_queryset():
    return CashBox.objects.select_related("branch", "branch__store")


def cash_transaction_queryset():
    return CashTransaction.objects.select_related(
        "cashbox",
        "cashbox__branch",
        "created_by",
    )


def expense_queryset():
    return Expense.objects.select_related(
        "cashbox",
        "cashbox__branch",
        "category",
        "created_by",
    )


def income_queryset():
    return Income.objects.select_related("cashbox", "cashbox__branch", "created_by")


def daily_closing_queryset():
    from apps.finance.models import DailyClosing

    return DailyClosing.objects.select_related(
        "branch",
        "branch__store",
        "cashier",
        "cashier_shift",
    )


def get_cashbox_summary(cashbox: CashBox):
    transactions = cash_transaction_queryset().filter(cashbox=cashbox)
    return {
        "cashbox_id": str(cashbox.id),
        "cashbox_name": cashbox.name,
        "branch_name": cashbox.branch.name,
        "current_balance": cashbox.current_balance,
        "transaction_count": transactions.count(),
        "latest_transaction_at": transactions.order_by("-created_at")
        .values_list("created_at", flat=True)
        .first(),
    }


def get_customer_debts():
    return Customer.objects.filter(balance__gt=0).order_by("-balance", "full_name")


def get_supplier_debts():
    return Supplier.objects.filter(balance__gt=0).order_by("-balance", "company_name")


def get_total_expenses(date_from=None, date_to=None, branch=None):
    queryset = Expense.objects.all()
    if branch:
        queryset = queryset.filter(cashbox__branch=branch)
    queryset = _filter_date_range(queryset, "expense_date", date_from, date_to)
    return _money_sum(queryset, "amount")


def get_total_income(date_from=None, date_to=None, branch=None):
    queryset = Income.objects.all()
    if branch:
        queryset = queryset.filter(cashbox__branch=branch)
    queryset = _filter_date_range(queryset, "income_date", date_from, date_to)
    return _money_sum(queryset, "amount")


def get_total_profit(date_from=None, date_to=None, branch=None):
    sales = Sale.objects.filter(status__in=[SaleStatus.COMPLETED, SaleStatus.REFUNDED])
    refunds = Refund.objects.all()
    purchases = Purchase.objects.filter(status=PurchaseStatus.CONFIRMED)

    if branch:
        sales = sales.filter(branch=branch)
        refunds = refunds.filter(original_sale__branch=branch)
        purchases = purchases.filter(warehouse__branch=branch)

    sales = _filter_date_range(sales, "sale_date", date_from, date_to)
    refunds = _filter_date_range(refunds, "refund_date", date_from, date_to)
    purchases = _filter_date_range(purchases, "purchase_date", date_from, date_to)

    total_sales = _money_sum(sales, "total_amount")
    total_refunds = _money_sum(refunds, "total_amount")
    total_purchases = _money_sum(purchases, "total_amount")
    total_expenses = get_total_expenses(date_from, date_to, branch)
    total_income = get_total_income(date_from, date_to, branch)
    net_sales = (total_sales - total_refunds).quantize(MONEY_QUANT)
    profit = (net_sales + total_income - total_purchases - total_expenses).quantize(
        MONEY_QUANT
    )

    return {
        "total_sales": total_sales,
        "total_refunds": total_refunds,
        "net_sales": net_sales,
        "total_purchases": total_purchases,
        "total_expenses": total_expenses,
        "total_income": total_income,
        "profit": profit,
    }


def get_cashflow_summary(date_from=None, date_to=None, branch=None):
    queryset = CashTransaction.objects.all()
    if branch:
        queryset = queryset.filter(cashbox__branch=branch)
    queryset = _filter_date_range(queryset, "created_at", date_from, date_to)

    summary = queryset.aggregate(
        income=Coalesce(
            Sum("amount", filter=Q(transaction_type=CashTransactionType.INCOME)),
            Value(Decimal("0.00")),
            output_field=DecimalField(max_digits=14, decimal_places=2),
        ),
        sales=Coalesce(
            Sum("amount", filter=Q(transaction_type=CashTransactionType.SALE)),
            Value(Decimal("0.00")),
            output_field=DecimalField(max_digits=14, decimal_places=2),
        ),
        expenses=Coalesce(
            Sum("amount", filter=Q(transaction_type=CashTransactionType.EXPENSE)),
            Value(Decimal("0.00")),
            output_field=DecimalField(max_digits=14, decimal_places=2),
        ),
        purchases=Coalesce(
            Sum("amount", filter=Q(transaction_type=CashTransactionType.PURCHASE)),
            Value(Decimal("0.00")),
            output_field=DecimalField(max_digits=14, decimal_places=2),
        ),
        refunds=Coalesce(
            Sum("amount", filter=Q(transaction_type=CashTransactionType.REFUND)),
            Value(Decimal("0.00")),
            output_field=DecimalField(max_digits=14, decimal_places=2),
        ),
        adjustments=Coalesce(
            Sum("amount", filter=Q(transaction_type=CashTransactionType.ADJUSTMENT)),
            Value(Decimal("0.00")),
            output_field=DecimalField(max_digits=14, decimal_places=2),
        ),
    )
    net_cashflow = (
        summary["income"]
        + summary["sales"]
        - summary["expenses"]
        - summary["purchases"]
        - summary["refunds"]
        + summary["adjustments"]
    ).quantize(MONEY_QUANT)
    return {**summary, "net_cashflow": net_cashflow}


def get_daily_profit(day: date | None = None, branch=None):
    if day is None:
        from django.utils import timezone

        day = timezone.localdate()
    return get_total_profit(day, day, branch)


def get_monthly_profit(year=None, month=None, branch=None):
    from django.utils import timezone

    today = timezone.localdate()
    year = year or today.year
    month = month or today.month
    date_from = date(year, month, 1)
    date_to = date(year, month, monthrange(year, month)[1])
    return get_total_profit(date_from, date_to, branch)


def get_best_revenue_branches(limit=10, date_from=None, date_to=None):
    queryset = Sale.objects.filter(
        status__in=[SaleStatus.COMPLETED, SaleStatus.REFUNDED]
    )
    queryset = _filter_date_range(queryset, "sale_date", date_from, date_to)
    return (
        queryset.values("branch", "branch__name", "branch__store__name")
        .annotate(
            sale_count=Count("id"),
            revenue=Coalesce(
                Sum("total_amount"),
                Value(Decimal("0.00")),
                output_field=DecimalField(max_digits=14, decimal_places=2),
            ),
        )
        .order_by("-revenue", "-sale_count")[:limit]
    )


def get_cashier_performance(date_from=None, date_to=None, branch=None):
    queryset = Sale.objects.filter(
        status__in=[SaleStatus.COMPLETED, SaleStatus.REFUNDED]
    )
    if branch:
        queryset = queryset.filter(branch=branch)
    queryset = _filter_date_range(queryset, "sale_date", date_from, date_to)
    return (
        queryset.values("cashier", "cashier__email")
        .annotate(
            sale_count=Count("id"),
            revenue=Coalesce(
                Sum("total_amount"),
                Value(Decimal("0.00")),
                output_field=DecimalField(max_digits=14, decimal_places=2),
            ),
            paid_amount=Coalesce(
                Sum("paid_amount"),
                Value(Decimal("0.00")),
                output_field=DecimalField(max_digits=14, decimal_places=2),
            ),
            debt_amount=Coalesce(
                Sum("remaining_amount"),
                Value(Decimal("0.00")),
                output_field=DecimalField(max_digits=14, decimal_places=2),
            ),
        )
        .order_by("-revenue", "-sale_count")
    )


def get_expense_statistics(date_from=None, date_to=None, branch=None):
    queryset = Expense.objects.select_related("category")
    if branch:
        queryset = queryset.filter(cashbox__branch=branch)
    queryset = _filter_date_range(queryset, "expense_date", date_from, date_to)
    return (
        queryset.values("category", "category__name")
        .annotate(
            expense_count=Count("id"),
            total_amount=Coalesce(
                Sum("amount"),
                Value(Decimal("0.00")),
                output_field=DecimalField(max_digits=14, decimal_places=2),
            ),
        )
        .order_by("-total_amount", "category__name")
    )


def get_profit_trend(group_by="day", date_from=None, date_to=None, branch=None):
    queryset = CashTransaction.objects.all()
    if branch:
        queryset = queryset.filter(cashbox__branch=branch)
    queryset = _filter_date_range(queryset, "created_at", date_from, date_to)

    trunc = TruncMonth("created_at") if group_by == "month" else TruncDate("created_at")
    signed_amount = Case(
        When(
            transaction_type__in=[
                CashTransactionType.INCOME,
                CashTransactionType.SALE,
            ],
            then=F("amount"),
        ),
        When(
            transaction_type__in=[
                CashTransactionType.EXPENSE,
                CashTransactionType.PURCHASE,
                CashTransactionType.REFUND,
            ],
            then=-F("amount"),
        ),
        default=F("amount"),
        output_field=DecimalField(max_digits=14, decimal_places=2),
    )

    return (
        queryset.annotate(period=trunc)
        .values("period")
        .annotate(
            net_cashflow=Coalesce(
                Sum(signed_amount),
                Value(Decimal("0.00")),
                output_field=DecimalField(max_digits=14, decimal_places=2),
            )
        )
        .order_by("period")
    )
