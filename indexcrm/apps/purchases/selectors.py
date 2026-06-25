from decimal import Decimal

from django.db.models import Count, DecimalField, Q, Sum, Value
from django.db.models.functions import Coalesce

from apps.purchases.models import Purchase, PurchaseStatus, Supplier


def supplier_queryset():
    return Supplier.objects.prefetch_related("contacts")


def purchase_queryset():
    return Purchase.objects.select_related(
        "supplier",
        "warehouse",
        "warehouse__branch",
        "created_by",
        "confirmed_by",
    ).prefetch_related("items", "payments")


def get_supplier_total_debt(supplier: Supplier | None = None):
    if supplier is not None:
        return supplier.balance

    return Supplier.objects.aggregate(
        total_debt=Coalesce(
            Sum("balance"),
            Value(Decimal("0.00")),
            output_field=DecimalField(max_digits=14, decimal_places=2),
        )
    )["total_debt"]


def get_purchase_statistics():
    queryset = Purchase.objects.all()
    return queryset.aggregate(
        total_purchases=Count("id"),
        draft_purchases=Count("id", filter=Q(status=PurchaseStatus.DRAFT)),
        confirmed_purchases=Count("id", filter=Q(status=PurchaseStatus.CONFIRMED)),
        cancelled_purchases=Count("id", filter=Q(status=PurchaseStatus.CANCELLED)),
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
        remaining_amount=Coalesce(
            Sum("remaining_amount"),
            Value(Decimal("0.00")),
            output_field=DecimalField(max_digits=14, decimal_places=2),
        ),
    )


def get_top_suppliers(limit=10):
    return Supplier.objects.annotate(
        purchase_count=Count(
            "purchases",
            filter=Q(purchases__status=PurchaseStatus.CONFIRMED),
        ),
        purchase_total=Coalesce(
            Sum(
                "purchases__total_amount",
                filter=Q(purchases__status=PurchaseStatus.CONFIRMED),
            ),
            Value(Decimal("0.00")),
            output_field=DecimalField(max_digits=14, decimal_places=2),
        ),
    ).order_by("-purchase_total", "-purchase_count")[:limit]


def get_recent_purchases(limit=10):
    return purchase_queryset().order_by("-purchase_date", "-created_at")[:limit]
