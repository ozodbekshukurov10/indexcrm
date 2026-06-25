from datetime import datetime, time, timedelta
from decimal import Decimal

from django.db.models import Count, DecimalField, Q, Sum, Value
from django.db.models.functions import Coalesce, TruncDate
from django.utils import timezone

from apps.sales.models import Customer, Sale, SaleItem, SaleStatus


def customer_queryset():
    return Customer.objects.prefetch_related("payments")


def sale_queryset():
    return Sale.objects.select_related(
        "branch",
        "warehouse",
        "cashier",
        "customer",
    ).prefetch_related("items__product", "payments", "refunds")


def refund_queryset():
    from apps.sales.models import Refund

    return Refund.objects.select_related(
        "original_sale",
        "original_sale__branch",
        "cashier",
    ).prefetch_related("items__product")


def get_recent_sales(limit=10):
    return sale_queryset().order_by("-sale_date", "-created_at")[:limit]


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


def get_daily_sales(date=None, branch=None):
    date = date or timezone.localdate()
    queryset = sale_queryset().filter(
        sale_date__gte=_day_start(date),
        sale_date__lte=_day_end(date),
        status__in=[SaleStatus.COMPLETED, SaleStatus.REFUNDED],
    )
    if branch:
        queryset = queryset.filter(branch=branch)
    return queryset


def get_top_customers(limit=10):
    return Customer.objects.annotate(
        sale_count=Count(
            "sales",
            filter=Q(sales__status__in=[SaleStatus.COMPLETED, SaleStatus.REFUNDED]),
        ),
        total_spent=Coalesce(
            Sum(
                "sales__total_amount",
                filter=Q(sales__status__in=[SaleStatus.COMPLETED, SaleStatus.REFUNDED]),
            ),
            Value(Decimal("0.00")),
            output_field=DecimalField(max_digits=14, decimal_places=2),
        ),
    ).order_by("-total_spent", "-sale_count")[:limit]


def get_best_selling_products(limit=10, date_from=None, date_to=None):
    queryset = SaleItem.objects.filter(
        sale__status__in=[SaleStatus.COMPLETED, SaleStatus.REFUNDED]
    )
    if date_from:
        queryset = queryset.filter(sale__sale_date__gte=_day_start(date_from))
    if date_to:
        queryset = queryset.filter(sale__sale_date__lte=_day_end(date_to))

    return (
        queryset.values("product", "product__name", "product__sku")
        .annotate(
            sold_quantity=Coalesce(
                Sum("quantity"),
                Value(Decimal("0.000")),
                output_field=DecimalField(max_digits=14, decimal_places=3),
            ),
            sold_amount=Coalesce(
                Sum("total_price"),
                Value(Decimal("0.00")),
                output_field=DecimalField(max_digits=14, decimal_places=2),
            ),
        )
        .order_by("-sold_quantity", "-sold_amount")[:limit]
    )


def get_cashier_statistics(cashier=None, date_from=None, date_to=None):
    queryset = Sale.objects.filter(
        status__in=[SaleStatus.COMPLETED, SaleStatus.REFUNDED]
    )
    if cashier:
        queryset = queryset.filter(cashier=cashier)
    if date_from:
        queryset = queryset.filter(sale_date__gte=_day_start(date_from))
    if date_to:
        queryset = queryset.filter(sale_date__lte=_day_end(date_to))

    return queryset.values("cashier", "cashier__email").annotate(
        sale_count=Count("id"),
        total_amount=Coalesce(
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


def get_sales_summary(date_from=None, date_to=None, branch=None):
    if date_from is None:
        date_from = timezone.localdate() - timedelta(days=30)
    if date_to is None:
        date_to = timezone.localdate()

    queryset = Sale.objects.filter(
        sale_date__gte=_day_start(date_from),
        sale_date__lte=_day_end(date_to),
    )
    if branch:
        queryset = queryset.filter(branch=branch)

    summary = queryset.aggregate(
        total_sales=Count(
            "id", filter=Q(status__in=[SaleStatus.COMPLETED, SaleStatus.REFUNDED])
        ),
        completed_sales=Count("id", filter=Q(status=SaleStatus.COMPLETED)),
        cancelled_sales=Count("id", filter=Q(status=SaleStatus.CANCELLED)),
        refunded_sales=Count("id", filter=Q(status=SaleStatus.REFUNDED)),
        total_amount=Coalesce(
            Sum(
                "total_amount",
                filter=Q(status__in=[SaleStatus.COMPLETED, SaleStatus.REFUNDED]),
            ),
            Value(Decimal("0.00")),
            output_field=DecimalField(max_digits=14, decimal_places=2),
        ),
        paid_amount=Coalesce(
            Sum(
                "paid_amount",
                filter=Q(status__in=[SaleStatus.COMPLETED, SaleStatus.REFUNDED]),
            ),
            Value(Decimal("0.00")),
            output_field=DecimalField(max_digits=14, decimal_places=2),
        ),
        remaining_amount=Coalesce(
            Sum(
                "remaining_amount",
                filter=Q(status__in=[SaleStatus.COMPLETED, SaleStatus.REFUNDED]),
            ),
            Value(Decimal("0.00")),
            output_field=DecimalField(max_digits=14, decimal_places=2),
        ),
    )
    daily = (
        queryset.filter(status__in=[SaleStatus.COMPLETED, SaleStatus.REFUNDED])
        .annotate(day=TruncDate("sale_date"))
        .values("day")
        .annotate(
            sale_count=Count("id"),
            total_amount=Coalesce(
                Sum("total_amount"),
                Value(Decimal("0.00")),
                output_field=DecimalField(max_digits=14, decimal_places=2),
            ),
        )
        .order_by("day")
    )
    return {"summary": summary, "daily": list(daily)}
