from calendar import monthrange
from datetime import date, datetime, time
from decimal import Decimal

from django.db.models import Count, DecimalField, F, Q, Sum, Value
from django.db.models.functions import Coalesce, TruncDate
from django.utils import timezone

from apps.finance.models import MONEY_QUANT, CashBox, Expense
from apps.finance.selectors import (
    get_cashbox_summary,
    get_cashier_performance,
    get_customer_debts,
    get_supplier_debts,
    get_total_profit,
)
from apps.inventory.selectors import low_stock_queryset, stock_queryset
from apps.purchases.models import Purchase, PurchaseStatus
from apps.sales.models import Refund, Sale, SaleItem, SaleStatus
from apps.sales.selectors import get_recent_sales


def _money_sum(queryset, field):
    return queryset.aggregate(
        total=Coalesce(
            Sum(field),
            Value(Decimal("0.00")),
            output_field=DecimalField(max_digits=14, decimal_places=2),
        )
    )["total"].quantize(MONEY_QUANT)


def _quantity_sum(queryset, field):
    return queryset.aggregate(
        total=Coalesce(
            Sum(field),
            Value(Decimal("0.000")),
            output_field=DecimalField(max_digits=14, decimal_places=3),
        )
    )["total"]


def _date_range_filter(queryset, field_name, date_from=None, date_to=None):
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


def month_bounds(year=None, month=None):
    today = timezone.localdate()
    year = int(year or today.year)
    month = int(month or today.month)
    return date(year, month, 1), date(year, month, monthrange(year, month)[1])


def daily_sales_summary(day=None, branch=None):
    day = day or timezone.localdate()
    sales = _date_range_filter(Sale.objects.all(), "sale_date", day, day)
    refunds = _date_range_filter(Refund.objects.all(), "refund_date", day, day)
    if branch:
        sales = sales.filter(branch=branch)
        refunds = refunds.filter(original_sale__branch=branch)

    completed_or_refunded = Q(status__in=[SaleStatus.COMPLETED, SaleStatus.REFUNDED])
    summary = sales.aggregate(
        total_sales=Count("id", filter=completed_or_refunded),
        completed_sales=Count("id", filter=Q(status=SaleStatus.COMPLETED)),
        refunded_sales=Count("id", filter=Q(status=SaleStatus.REFUNDED)),
        cancelled_sales=Count("id", filter=Q(status=SaleStatus.CANCELLED)),
        gross_sales=Coalesce(
            Sum("total_amount", filter=completed_or_refunded),
            Value(Decimal("0.00")),
            output_field=DecimalField(max_digits=14, decimal_places=2),
        ),
        paid_amount=Coalesce(
            Sum("paid_amount", filter=completed_or_refunded),
            Value(Decimal("0.00")),
            output_field=DecimalField(max_digits=14, decimal_places=2),
        ),
        debt_amount=Coalesce(
            Sum("remaining_amount", filter=completed_or_refunded),
            Value(Decimal("0.00")),
            output_field=DecimalField(max_digits=14, decimal_places=2),
        ),
    )
    refund_amount = _money_sum(refunds, "total_amount")
    return {
        "date": day,
        **summary,
        "refund_amount": refund_amount,
        "net_sales": (summary["gross_sales"] - refund_amount).quantize(MONEY_QUANT),
    }


def monthly_sales_summary(year=None, month=None, branch=None):
    date_from, date_to = month_bounds(year, month)
    sales = _date_range_filter(Sale.objects.all(), "sale_date", date_from, date_to)
    refunds = _date_range_filter(
        Refund.objects.all(), "refund_date", date_from, date_to
    )
    if branch:
        sales = sales.filter(branch=branch)
        refunds = refunds.filter(original_sale__branch=branch)

    completed_or_refunded = Q(status__in=[SaleStatus.COMPLETED, SaleStatus.REFUNDED])
    summary = sales.aggregate(
        total_sales=Count("id", filter=completed_or_refunded),
        completed_sales=Count("id", filter=Q(status=SaleStatus.COMPLETED)),
        refunded_sales=Count("id", filter=Q(status=SaleStatus.REFUNDED)),
        cancelled_sales=Count("id", filter=Q(status=SaleStatus.CANCELLED)),
        gross_sales=Coalesce(
            Sum("total_amount", filter=completed_or_refunded),
            Value(Decimal("0.00")),
            output_field=DecimalField(max_digits=14, decimal_places=2),
        ),
        paid_amount=Coalesce(
            Sum("paid_amount", filter=completed_or_refunded),
            Value(Decimal("0.00")),
            output_field=DecimalField(max_digits=14, decimal_places=2),
        ),
        debt_amount=Coalesce(
            Sum("remaining_amount", filter=completed_or_refunded),
            Value(Decimal("0.00")),
            output_field=DecimalField(max_digits=14, decimal_places=2),
        ),
    )
    refund_amount = _money_sum(refunds, "total_amount")
    daily = (
        sales.filter(status__in=[SaleStatus.COMPLETED, SaleStatus.REFUNDED])
        .annotate(day=TruncDate("sale_date"))
        .values("day")
        .annotate(
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
        .order_by("day")
    )
    return {
        "date_from": date_from,
        "date_to": date_to,
        **summary,
        "refund_amount": refund_amount,
        "net_sales": (summary["gross_sales"] - refund_amount).quantize(MONEY_QUANT),
        "daily": list(daily),
    }


def profit_report(date_from=None, date_to=None, branch=None):
    return get_total_profit(date_from=date_from, date_to=date_to, branch=branch)


def expenses_report(date_from=None, date_to=None, branch=None):
    expenses = Expense.objects.select_related("category", "cashbox", "cashbox__branch")
    if branch:
        expenses = expenses.filter(cashbox__branch=branch)
    expenses = _date_range_filter(expenses, "expense_date", date_from, date_to)
    categories = (
        expenses.values("category", "category__name")
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
    return {
        "date_from": date_from,
        "date_to": date_to,
        "total_expenses": _money_sum(expenses, "amount"),
        "expense_count": expenses.count(),
        "categories": list(categories),
    }


def inventory_report(branch=None, warehouse=None, category=None, brand=None):
    stocks = stock_queryset()
    if branch:
        stocks = stocks.filter(warehouse__branch=branch)
    if warehouse:
        stocks = stocks.filter(warehouse=warehouse)
    if category:
        stocks = stocks.filter(product__category=category)
    if brand:
        stocks = stocks.filter(product__brand=brand)

    totals = stocks.aggregate(
        product_count=Count("product", distinct=True),
        stock_record_count=Count("id"),
        total_quantity=Coalesce(
            Sum("quantity"),
            Value(Decimal("0.000")),
            output_field=DecimalField(max_digits=14, decimal_places=3),
        ),
        reserved_quantity=Coalesce(
            Sum("reserved_quantity"),
            Value(Decimal("0.000")),
            output_field=DecimalField(max_digits=14, decimal_places=3),
        ),
        total_cost_value=Coalesce(
            Sum(F("quantity") * F("product__cost_price")),
            Value(Decimal("0.00")),
            output_field=DecimalField(max_digits=14, decimal_places=2),
        ),
        total_selling_value=Coalesce(
            Sum(F("quantity") * F("product__selling_price")),
            Value(Decimal("0.00")),
            output_field=DecimalField(max_digits=14, decimal_places=2),
        ),
    )
    rows = [
        {
            "stock_id": str(stock.id),
            "warehouse": stock.warehouse.name,
            "branch": stock.warehouse.branch.name,
            "product": stock.product.name,
            "sku": stock.product.sku,
            "category": stock.product.category.name,
            "brand": stock.product.brand.name if stock.product.brand_id else None,
            "quantity": stock.quantity,
            "reserved_quantity": stock.reserved_quantity,
            "available_quantity": stock.available_quantity,
            "low_stock_limit": stock.low_stock_limit,
            "is_low_stock": stock.is_low_stock,
        }
        for stock in stocks.order_by(
            "warehouse__branch__store__name",
            "warehouse__branch__name",
            "warehouse__name",
            "product__name",
        )
    ]
    return {**totals, "items": rows}


def low_stock_report(branch=None, warehouse=None):
    stocks = low_stock_queryset()
    if branch:
        stocks = stocks.filter(warehouse__branch=branch)
    if warehouse:
        stocks = stocks.filter(warehouse=warehouse)
    rows = [
        {
            "stock_id": str(stock.id),
            "warehouse": stock.warehouse.name,
            "branch": stock.warehouse.branch.name,
            "product": stock.product.name,
            "sku": stock.product.sku,
            "quantity": stock.quantity,
            "low_stock_limit": stock.low_stock_limit,
            "available_quantity": stock.available_quantity,
        }
        for stock in stocks.order_by("quantity", "product__name")
    ]
    return {"low_stock_count": len(rows), "items": rows}


def best_selling_products(date_from=None, date_to=None, branch=None, limit=10):
    items = SaleItem.objects.select_related("product", "sale").filter(
        sale__status__in=[SaleStatus.COMPLETED, SaleStatus.REFUNDED]
    )
    if branch:
        items = items.filter(sale__branch=branch)
    if date_from:
        items = items.filter(sale__sale_date__gte=_day_start(date_from))
    if date_to:
        items = items.filter(sale__sale_date__lte=_day_end(date_to))
    return list(
        items.values("product", "product__name", "product__sku")
        .annotate(
            sold_quantity=Coalesce(
                Sum("quantity"),
                Value(Decimal("0.000")),
                output_field=DecimalField(max_digits=14, decimal_places=3),
            ),
            total_amount=Coalesce(
                Sum("total_price"),
                Value(Decimal("0.00")),
                output_field=DecimalField(max_digits=14, decimal_places=2),
            ),
            sale_count=Count("sale", distinct=True),
        )
        .order_by("-sold_quantity", "-total_amount")[:limit]
    )


def customer_debts_report():
    return list(
        get_customer_debts().values(
            "id",
            "full_name",
            "phone",
            "extra_phone",
            "balance",
        )
    )


def supplier_debts_report():
    return list(
        get_supplier_debts().values(
            "id",
            "company_name",
            "full_name",
            "phone",
            "balance",
        )
    )


def cashier_performance_report(date_from=None, date_to=None, branch=None):
    return list(get_cashier_performance(date_from, date_to, branch))


def recent_sales_report(limit=10, branch=None):
    if branch:
        sales = (
            Sale.objects.filter(branch=branch)
            .select_related("branch", "warehouse", "cashier", "customer")
            .prefetch_related("items__product", "payments", "refunds")
            .order_by("-sale_date", "-created_at")[:limit]
        )
    else:
        sales = get_recent_sales(limit=limit)
    return [
        {
            "id": str(sale.id),
            "receipt_number": sale.receipt_number,
            "branch": sale.branch.name,
            "cashier": sale.cashier.email,
            "customer": sale.customer.full_name if sale.customer_id else None,
            "status": sale.status,
            "total_amount": sale.total_amount,
            "paid_amount": sale.paid_amount,
            "remaining_amount": sale.remaining_amount,
            "sale_date": sale.sale_date,
        }
        for sale in sales
    ]


def cashbox_summaries(branch=None):
    cashboxes = CashBox.objects.select_related("branch").filter(is_active=True)
    if branch:
        cashboxes = cashboxes.filter(branch=branch)
    return [
        get_cashbox_summary(cashbox)
        for cashbox in cashboxes.order_by("branch__name", "name")
    ]


def total_debt_summary():
    customer_debt = _money_sum(get_customer_debts(), "balance")
    supplier_debt = _money_sum(get_supplier_debts(), "balance")
    return {
        "customer_debt": customer_debt,
        "supplier_debt": supplier_debt,
        "total_debt": (customer_debt + supplier_debt).quantize(MONEY_QUANT),
    }


def purchase_summary(date_from=None, date_to=None, branch=None):
    purchases = Purchase.objects.filter(status=PurchaseStatus.CONFIRMED)
    if branch:
        purchases = purchases.filter(warehouse__branch=branch)
    purchases = _date_range_filter(purchases, "purchase_date", date_from, date_to)
    return {
        "purchase_count": purchases.count(),
        "total_purchases": _money_sum(purchases, "total_amount"),
        "paid_amount": _money_sum(purchases, "paid_amount"),
        "remaining_amount": _money_sum(purchases, "remaining_amount"),
    }
