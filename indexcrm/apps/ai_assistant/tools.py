import logging
from datetime import date, datetime, time
from decimal import Decimal

from django.core.exceptions import FieldError, ValidationError
from django.db.models import Count, DecimalField, Max, Q, Sum, Value
from django.db.models.functions import Coalesce, TruncDate
from django.utils import timezone

from apps.accounts.models import UserRole
from apps.accounts.permissions import (
    filter_queryset_by_branch_scope,
    user_has_minimum_role,
)
from apps.ai_assistant.constants import (
    INTENT_CASHIER_ACTIVITY,
    INTENT_CUSTOMER_DEBT,
    INTENT_FINANCE_SUMMARY,
    INTENT_HELP,
    INTENT_LOW_STOCK,
    INTENT_PRODUCT_PRICE,
    INTENT_PRODUCT_STOCK,
    INTENT_REPORTS_SUMMARY,
    INTENT_SALES_MONTH,
    INTENT_SALES_TODAY,
    INTENT_TOP_PRODUCTS,
    INTENT_UNKNOWN,
)
from apps.cashier.models import CashierShift
from apps.catalog.models import Product
from apps.finance.models import CashBox, Expense, Income
from apps.inventory.models import Stock, Warehouse
from apps.sales.models import Customer, Sale, SaleItem, SalePayment, SaleStatus
from apps.stores.models import Branch
from apps.ai_assistant.text import normalize_text

logger = logging.getLogger(__name__)

MONEY_QUANT = Decimal("0.01")
QUANTITY_QUANT = Decimal("0.001")


def _money(value) -> str:
    return str(Decimal(str(value or "0")).quantize(MONEY_QUANT))


def _quantity(value) -> str:
    return str(Decimal(str(value or "0")).quantize(QUANTITY_QUANT))


def _ok(data: dict) -> dict:
    return {"status": "ok", "data": data}


def _not_found(message: str, **extra) -> dict:
    return {"status": "not_found", "message": message, **extra}


def _not_supported(message: str) -> dict:
    return {"status": "not_supported", "message": message}


def _permission_denied(message: str = "Permission denied.") -> dict:
    return {"status": "permission_denied", "message": message}


def _serialize_datetime(value):
    if value is None:
        return None
    return timezone.localtime(value).isoformat()


def _serialize_date(value) -> str:
    return value.isoformat() if hasattr(value, "isoformat") else str(value)


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


def _parse_date(value):
    if isinstance(value, date):
        return value
    if not value:
        return None
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        return None


def _range_from_entities(date_value=None, date_range=None, date_from=None, date_to=None):
    explicit_from = _parse_date(date_from)
    explicit_to = _parse_date(date_to)
    if explicit_from and explicit_to:
        return explicit_from, explicit_to
    if date_range:
        range_from = _parse_date(date_range.get("from"))
        range_to = _parse_date(date_range.get("to"))
        if range_from and range_to:
            return range_from, range_to
    parsed_date = _parse_date(date_value)
    if parsed_date:
        return parsed_date, parsed_date
    today = timezone.localdate()
    return today, today


def _date_filter(queryset, field_name, date_from=None, date_to=None):
    if date_from:
        queryset = queryset.filter(**{f"{field_name}__gte": _day_start(date_from)})
    if date_to:
        queryset = queryset.filter(**{f"{field_name}__lte": _day_end(date_to)})
    return queryset


def _sum_money(queryset, field_name):
    return queryset.aggregate(
        total=Coalesce(
            Sum(field_name),
            Value(Decimal("0.00")),
            output_field=DecimalField(max_digits=14, decimal_places=2),
        )
    )["total"].quantize(MONEY_QUANT)


def _sum_quantity(queryset, field_name):
    return queryset.aggregate(
        total=Coalesce(
            Sum(field_name),
            Value(Decimal("0.000")),
            output_field=DecimalField(max_digits=14, decimal_places=3),
        )
    )["total"].quantize(QUANTITY_QUANT)


def _safe_tool(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except FieldError:
            logger.exception("AI assistant tool field error: %s", func.__name__)
            return _not_supported("Kerakli model yoki maydonlar aniqlanmadi.")
        except Exception:
            logger.exception("AI assistant tool error: %s", func.__name__)
            return {"status": "error", "message": "Tool execution failed."}

    return wrapper


def _match_by_name(queryset, raw_value: str, aliases):
    normalized_query = normalize_text(raw_value)
    if not normalized_query:
        return None
    for obj in queryset[:250]:
        for alias in aliases(obj):
            normalized_alias = normalize_text(alias)
            if normalized_alias and (
                normalized_alias == normalized_query
                or normalized_alias in normalized_query
                or normalized_query in normalized_alias
            ):
                return obj
    return None


def _branch_aliases(branch):
    return [
        value
        for value in (
            branch.name,
            str(branch),
            getattr(branch.store, "name", ""),
            f"{getattr(branch.store, 'name', '')} {branch.name}".strip(),
        )
        if value
    ]


def _warehouse_aliases(warehouse):
    return [
        value
        for value in (
            warehouse.name,
            str(warehouse),
            f"{getattr(warehouse.branch, 'name', '')} {warehouse.name}".strip(),
        )
        if value
    ]


def _branch_queryset(user=None):
    queryset = Branch.objects.filter(is_active=True).select_related("store")
    if user is not None:
        queryset = filter_queryset_by_branch_scope(queryset, user, "id")
    return queryset


def _warehouse_queryset(user=None):
    queryset = Warehouse.objects.filter(is_active=True).select_related("branch", "branch__store")
    if user is not None:
        queryset = filter_queryset_by_branch_scope(queryset, user, "branch_id")
    return queryset


def _filter_details(branch=None, warehouse=None, extra: dict | None = None) -> dict:
    filters = dict(extra or {})
    if branch is not None:
        filters.update(
            {
                "branch_id": str(branch.id),
                "branch_name": branch.name,
            }
        )
    if warehouse is not None:
        filters.update(
            {
                "warehouse_id": str(warehouse.id),
                "warehouse_name": warehouse.name,
            }
        )
        filters.setdefault("branch_id", str(warehouse.branch_id))
        filters.setdefault("branch_name", warehouse.branch.name)
    return filters


def _apply_filter_details(data: dict, branch=None, warehouse=None) -> dict:
    filters = _filter_details(branch=branch, warehouse=warehouse)
    if not filters:
        return data
    data.update(filters)
    data["filters"] = filters
    return data


def _resolve_branch(user=None, branch_id=None, branch=None):
    if not branch_id and not branch:
        return None, None
    queryset = _branch_queryset(user=user)
    branch_obj = None
    if branch_id:
        try:
            branch_obj = queryset.filter(id=branch_id).first()
        except (ValidationError, ValueError, TypeError):
            branch_obj = None
    if branch_obj is None and branch:
        branch_obj = _match_by_name(queryset, branch, _branch_aliases)
    if branch_obj is None:
        return None, _not_found(
            "Filial topilmadi.",
            entity="branch",
            filters={"branch": str(branch_id or branch)},
        )
    return branch_obj, None


def _resolve_warehouse(user=None, warehouse_id=None, warehouse=None, branch_obj=None):
    if not warehouse_id and not warehouse:
        return None, None
    queryset = _warehouse_queryset(user=user)
    if branch_obj is not None:
        queryset = queryset.filter(branch=branch_obj)
    warehouse_obj = None
    if warehouse_id:
        try:
            warehouse_obj = queryset.filter(id=warehouse_id).first()
        except (ValidationError, ValueError, TypeError):
            warehouse_obj = None
    if warehouse_obj is None and warehouse:
        warehouse_obj = _match_by_name(queryset, warehouse, _warehouse_aliases)
    if warehouse_obj is None:
        filters = {"warehouse": str(warehouse_id or warehouse)}
        if branch_obj is not None:
            filters.update(_filter_details(branch=branch_obj))
        return None, _not_found(
            "Ombor topilmadi.",
            entity="warehouse",
            filters=filters,
        )
    return warehouse_obj, None


def _user_can_see_cost(user) -> bool:
    return (
        getattr(user, "is_staff", False)
        or getattr(user, "is_superuser", False)
        or user_has_minimum_role(user, UserRole.MANAGER)
    )


def _user_can_use_sensitive_reports(user) -> bool:
    return (
        getattr(user, "is_staff", False)
        or getattr(user, "is_superuser", False)
        or user_has_minimum_role(user, UserRole.ADMIN)
    )


def _sales_queryset(user=None, branch_id=None, warehouse_id=None):
    queryset = Sale.objects.filter(status=SaleStatus.COMPLETED).select_related(
        "branch",
        "cashier",
        "warehouse",
    )
    if branch_id:
        queryset = queryset.filter(branch_id=branch_id)
    if warehouse_id:
        queryset = queryset.filter(warehouse_id=warehouse_id)
    if user is not None:
        queryset = filter_queryset_by_branch_scope(queryset, user, "branch_id")
    return queryset


def _stock_queryset(user=None, branch_id=None, warehouse_id=None):
    queryset = Stock.objects.select_related(
        "warehouse",
        "warehouse__branch",
        "product",
        "product__unit",
    )
    if branch_id:
        queryset = queryset.filter(warehouse__branch_id=branch_id)
    if warehouse_id:
        queryset = queryset.filter(warehouse_id=warehouse_id)
    if user is not None:
        queryset = filter_queryset_by_branch_scope(
            queryset,
            user,
            "warehouse__branch_id",
        )
    return queryset


def _find_product(product_id=None, product_name=None):
    queryset = Product.objects.filter(is_active=True).select_related(
        "category",
        "unit",
    )
    if product_id:
        return queryset.filter(id=product_id).first()
    if product_name:
        return queryset.filter(
            Q(name__icontains=product_name)
            | Q(sku__icontains=product_name)
            | Q(barcode__icontains=product_name)
            | Q(barcodes__code__icontains=product_name)
        ).first()
    return None


def _payment_breakdown(sales_queryset):
    sale_ids = sales_queryset.values("id")
    payments = SalePayment.objects.filter(sale_id__in=sale_ids)
    rows = payments.values("payment_method").annotate(
        total=Coalesce(
            Sum("amount"),
            Value(Decimal("0.00")),
            output_field=DecimalField(max_digits=14, decimal_places=2),
        )
    )
    breakdown = {row["payment_method"]: row["total"] for row in rows}
    return {
        "cash_amount": _money(breakdown.get("CASH")),
        "card_amount": _money(breakdown.get("CARD")),
        "mixed_amount": _money(breakdown.get("MIXED")),
        "payment_breakdown": {
            key.lower(): _money(value) for key, value in breakdown.items()
        },
    }


@_safe_tool
def get_today_sales(
    user=None,
    date=None,
    branch_id=None,
    branch=None,
    warehouse_id=None,
    warehouse=None,
    date_from=None,
    date_to=None,
    date_range=None,
) -> dict:
    branch_obj, error = _resolve_branch(user=user, branch_id=branch_id, branch=branch)
    if error:
        return error
    warehouse_obj, error = _resolve_warehouse(
        user=user,
        warehouse_id=warehouse_id,
        warehouse=warehouse,
        branch_obj=branch_obj,
    )
    if error:
        return error

    if date_from or date_to or date_range:
        period_from, period_to = _range_from_entities(
            date_value=date,
            date_range=date_range,
            date_from=date_from,
            date_to=date_to,
        )
    else:
        day = _parse_date(date) or timezone.localdate()
        period_from, period_to = day, day
    queryset = _date_filter(
        _sales_queryset(
            user=user,
            branch_id=branch_obj.id if branch_obj else None,
            warehouse_id=warehouse_obj.id if warehouse_obj else None,
        ),
        "sale_date",
        period_from,
        period_to,
    )
    total_amount = _sum_money(queryset, "total_amount")
    sales_count = queryset.count()
    average_check = total_amount / sales_count if sales_count else Decimal("0.00")
    last_sale_time = queryset.aggregate(last=Max("sale_date"))["last"]
    data = {
        "date": _serialize_date(period_from) if period_from == period_to else None,
        "from": _serialize_date(period_from),
        "to": _serialize_date(period_to),
        "sales_count": sales_count,
        "total_amount": _money(total_amount),
        "average_check": _money(average_check),
        "last_sale_time": _serialize_datetime(last_sale_time),
        **_payment_breakdown(queryset),
    }
    _apply_filter_details(data, branch=branch_obj, warehouse=warehouse_obj)
    return _ok(data)


@_safe_tool
def get_monthly_sales(
    user=None,
    date_range=None,
    branch_id=None,
    branch=None,
    warehouse_id=None,
    warehouse=None,
    date_from=None,
    date_to=None,
) -> dict:
    branch_obj, error = _resolve_branch(user=user, branch_id=branch_id, branch=branch)
    if error:
        return error
    warehouse_obj, error = _resolve_warehouse(
        user=user,
        warehouse_id=warehouse_id,
        warehouse=warehouse,
        branch_obj=branch_obj,
    )
    if error:
        return error
    date_from, date_to = _range_from_entities(
        date_range=date_range,
        date_from=date_from,
        date_to=date_to,
    )
    queryset = _date_filter(
        _sales_queryset(
            user=user,
            branch_id=branch_obj.id if branch_obj else None,
            warehouse_id=warehouse_obj.id if warehouse_obj else None,
        ),
        "sale_date",
        date_from,
        date_to,
    )
    total_amount = _sum_money(queryset, "total_amount")
    sales_count = queryset.count()
    day_count = max(1, (date_to - date_from).days + 1)
    average_daily_sales = total_amount / day_count
    daily = (
        queryset.annotate(day=TruncDate("sale_date"))
        .values("day")
        .annotate(
            sales_count=Count("id"),
            total_amount=Coalesce(
                Sum("total_amount"),
                Value(Decimal("0.00")),
                output_field=DecimalField(max_digits=14, decimal_places=2),
            ),
        )
        .order_by("-total_amount", "-sales_count")
    )
    best_day = daily.first()
    data = {
        "from": _serialize_date(date_from),
        "to": _serialize_date(date_to),
        "sales_count": sales_count,
        "total_amount": _money(total_amount),
        "average_daily_sales": _money(average_daily_sales),
        "best_day": {
            "date": _serialize_date(best_day["day"]),
            "sales_count": best_day["sales_count"],
            "total_amount": _money(best_day["total_amount"]),
        }
        if best_day
        else None,
        **_payment_breakdown(queryset),
    }
    _apply_filter_details(data, branch=branch_obj, warehouse=warehouse_obj)
    return _ok(data)


@_safe_tool
def get_product_stock(
    product_id=None,
    product_name=None,
    warehouse_id=None,
    warehouse=None,
    branch_id=None,
    branch=None,
    user=None,
) -> dict:
    branch_obj, error = _resolve_branch(user=user, branch_id=branch_id, branch=branch)
    if error:
        return error
    warehouse_obj, error = _resolve_warehouse(
        user=user,
        warehouse_id=warehouse_id,
        warehouse=warehouse,
        branch_obj=branch_obj,
    )
    if error:
        return error
    product = _find_product(product_id=product_id, product_name=product_name)
    if product is None:
        return _not_found("Mahsulot topilmadi.")

    queryset = _stock_queryset(
        user=user,
        branch_id=branch_obj.id if branch_obj else None,
        warehouse_id=warehouse_obj.id if warehouse_obj else None,
    ).filter(product=product)
    stocks = list(queryset.order_by("warehouse__name"))
    total_quantity = sum((stock.quantity for stock in stocks), Decimal("0.000"))
    total_low_limit = sum((stock.low_stock_limit for stock in stocks), Decimal("0.000"))
    if total_quantity <= 0:
        stock_status = "zero"
    elif total_quantity <= total_low_limit:
        stock_status = "low"
    else:
        stock_status = "enough"

    data = {
        "product_id": str(product.id),
        "product_name": product.name,
        "sku": product.sku,
        "barcode": product.barcode,
        "quantity": _quantity(total_quantity),
        "unit": product.unit.short_name,
        "warehouse_name": stocks[0].warehouse.name if len(stocks) == 1 else "Barcha omborlar",
        "status": stock_status,
        "stocks": [
            {
                "warehouse_id": str(stock.warehouse_id),
                "warehouse_name": stock.warehouse.name,
                "quantity": _quantity(stock.quantity),
                "available_quantity": _quantity(stock.available_quantity),
                "min_quantity": _quantity(stock.low_stock_limit),
                "status": "zero"
                if stock.quantity <= 0
                else "low"
                if stock.quantity <= stock.low_stock_limit
                else "enough",
            }
            for stock in stocks
        ],
    }
    _apply_filter_details(data, branch=branch_obj, warehouse=warehouse_obj)
    return _ok(data)


@_safe_tool
def get_product_price(
    product_id=None,
    product_name=None,
    branch_id=None,
    branch=None,
    warehouse_id=None,
    warehouse=None,
    user=None,
) -> dict:
    branch_obj, error = _resolve_branch(user=user, branch_id=branch_id, branch=branch)
    if error:
        return error
    warehouse_obj, error = _resolve_warehouse(
        user=user,
        warehouse_id=warehouse_id,
        warehouse=warehouse,
        branch_obj=branch_obj,
    )
    if error:
        return error
    product = _find_product(product_id=product_id, product_name=product_name)
    if product is None:
        return _not_found("Mahsulot topilmadi.")

    data = {
        "product_id": str(product.id),
        "product_name": product.name,
        "sku": product.sku,
        "barcode": product.barcode,
        "sale_price": _money(product.selling_price),
        "unit": product.unit.short_name,
    }
    if user is not None and _user_can_see_cost(user):
        data["purchase_price"] = _money(product.cost_price)
    _apply_filter_details(data, branch=branch_obj, warehouse=warehouse_obj)
    return _ok(data)


@_safe_tool
def get_low_stock_products(
    user=None,
    limit=10,
    category_id=None,
    warehouse_id=None,
    warehouse=None,
    branch_id=None,
    branch=None,
) -> dict:
    branch_obj, error = _resolve_branch(user=user, branch_id=branch_id, branch=branch)
    if error:
        return error
    warehouse_obj, error = _resolve_warehouse(
        user=user,
        warehouse_id=warehouse_id,
        warehouse=warehouse,
        branch_obj=branch_obj,
    )
    if error:
        return error
    queryset = _stock_queryset(
        user=user,
        branch_id=branch_obj.id if branch_obj else None,
        warehouse_id=warehouse_obj.id if warehouse_obj else None,
    ).filter(
        quantity__lte=models_f("low_stock_limit")
    )
    if category_id:
        queryset = queryset.filter(product__category_id=category_id)
    rows = [
        {
            "product_id": str(stock.product_id),
            "product_name": stock.product.name,
            "quantity": _quantity(stock.quantity),
            "unit": stock.product.unit.short_name,
            "warehouse_id": str(stock.warehouse_id),
            "warehouse_name": stock.warehouse.name,
            "min_quantity": _quantity(stock.low_stock_limit),
        }
            for stock in queryset.order_by("quantity", "product__name")[:limit]
    ]
    data = {"count": len(rows), "products": rows}
    _apply_filter_details(data, branch=branch_obj, warehouse=warehouse_obj)
    return _ok(data)


def models_f(field_name):
    from django.db.models import F

    return F(field_name)


@_safe_tool
def get_top_products(
    user=None,
    date_range=None,
    limit=10,
    category_id=None,
    branch_id=None,
    branch=None,
    warehouse_id=None,
    warehouse=None,
    date_from=None,
    date_to=None,
) -> dict:
    branch_obj, error = _resolve_branch(user=user, branch_id=branch_id, branch=branch)
    if error:
        return error
    warehouse_obj, error = _resolve_warehouse(
        user=user,
        warehouse_id=warehouse_id,
        warehouse=warehouse,
        branch_obj=branch_obj,
    )
    if error:
        return error
    date_from, date_to = _range_from_entities(
        date_range=date_range,
        date_from=date_from,
        date_to=date_to,
    )
    queryset = SaleItem.objects.select_related("product", "product__unit", "sale").filter(
        sale__status=SaleStatus.COMPLETED
    )
    queryset = _date_filter(queryset, "sale__sale_date", date_from, date_to)
    if branch_obj is not None:
        queryset = queryset.filter(sale__branch_id=branch_obj.id)
    if warehouse_obj is not None:
        queryset = queryset.filter(sale__warehouse_id=warehouse_obj.id)
    if user is not None:
        queryset = filter_queryset_by_branch_scope(queryset, user, "sale__branch_id")
    if category_id:
        queryset = queryset.filter(product__category_id=category_id)

    rows = list(
        queryset.values("product_id", "product__name", "product__unit__short_name")
        .annotate(
            quantity_sold=Coalesce(
                Sum("quantity"),
                Value(Decimal("0.000")),
                output_field=DecimalField(max_digits=14, decimal_places=3),
            ),
            total_amount=Coalesce(
                Sum("total_price"),
                Value(Decimal("0.00")),
                output_field=DecimalField(max_digits=14, decimal_places=2),
            ),
        )
        .order_by("-quantity_sold", "-total_amount")[:limit]
    )
    data = {
        "from": _serialize_date(date_from),
        "to": _serialize_date(date_to),
        "products": [
            {
                "product_id": str(row["product_id"]),
                "product_name": row["product__name"],
                "quantity_sold": _quantity(row["quantity_sold"]),
                "unit": row["product__unit__short_name"],
                "total_amount": _money(row["total_amount"]),
            }
            for row in rows
        ],
    }
    _apply_filter_details(data, branch=branch_obj, warehouse=warehouse_obj)
    return _ok(data)


def _cashier_name(user) -> str:
    full_name = user.get_full_name()
    return full_name or user.email


@_safe_tool
def get_cashier_activity(
    user=None,
    cashier_id=None,
    date=None,
    date_range=None,
    branch_id=None,
    branch=None,
    date_from=None,
    date_to=None,
) -> dict:
    if user is not None and not user_has_minimum_role(user, UserRole.MANAGER):
        if cashier_id and str(cashier_id) != str(user.id):
            return _permission_denied("Bu kassir ma'lumotini ko'rish uchun ruxsat yo'q.")
        cashier_id = user.id

    branch_obj, error = _resolve_branch(user=user, branch_id=branch_id, branch=branch)
    if error:
        return error
    date_from, date_to = _range_from_entities(
        date_value=date,
        date_range=date_range,
        date_from=date_from,
        date_to=date_to,
    )
    shifts = CashierShift.objects.select_related("cashier", "branch")
    shifts = _date_filter(shifts, "opened_at", date_from, date_to)
    if branch_obj is not None:
        shifts = shifts.filter(branch_id=branch_obj.id)
    if user is not None:
        shifts = filter_queryset_by_branch_scope(shifts, user, "branch_id")
    if cashier_id:
        shifts = shifts.filter(cashier_id=cashier_id)

    sales = _date_filter(
        _sales_queryset(user=user, branch_id=branch_obj.id if branch_obj else None),
        "sale_date",
        date_from,
        date_to,
    )
    if cashier_id:
        sales = sales.filter(cashier_id=cashier_id)

    active_shift = shifts.filter(closed_at__isnull=True).order_by("-opened_at").first()
    latest_shift = active_shift or shifts.order_by("-opened_at").first()
    total_amount = _sum_money(sales, "total_amount")
    sales_count = sales.count()
    data = {
        "from": _serialize_date(date_from),
        "to": _serialize_date(date_to),
        "active_shift_exists": active_shift is not None,
        "cashier_id": str(latest_shift.cashier_id) if latest_shift else str(cashier_id) if cashier_id else None,
        "cashier_name": _cashier_name(latest_shift.cashier) if latest_shift else None,
        "shift_opened_at": _serialize_datetime(latest_shift.opened_at) if latest_shift else None,
        "shift_closed_at": _serialize_datetime(latest_shift.closed_at) if latest_shift else None,
        "branch_name": latest_shift.branch.name if latest_shift else None,
        "sales_count": sales_count,
        "total_amount": _money(total_amount),
    }
    _apply_filter_details(data, branch=branch_obj)
    return _ok(data)


@_safe_tool
def get_finance_summary(
    user=None,
    date=None,
    date_range=None,
    branch_id=None,
    branch=None,
    date_from=None,
    date_to=None,
) -> dict:
    if user is not None and not _user_can_use_sensitive_reports(user):
        return _permission_denied("Moliya xulosasini ko'rish uchun ruxsat yo'q.")

    branch_obj, error = _resolve_branch(user=user, branch_id=branch_id, branch=branch)
    if error:
        return error
    date_from, date_to = _range_from_entities(
        date_value=date,
        date_range=date_range,
        date_from=date_from,
        date_to=date_to,
    )
    sales = _date_filter(
        _sales_queryset(user=user, branch_id=branch_obj.id if branch_obj else None),
        "sale_date",
        date_from,
        date_to,
    )
    expenses = _date_filter(Expense.objects.select_related("cashbox"), "expense_date", date_from, date_to)
    incomes = _date_filter(Income.objects.select_related("cashbox"), "income_date", date_from, date_to)
    cashboxes = CashBox.objects.filter(is_active=True)
    if branch_obj is not None:
        expenses = expenses.filter(cashbox__branch_id=branch_obj.id)
        incomes = incomes.filter(cashbox__branch_id=branch_obj.id)
        cashboxes = cashboxes.filter(branch_id=branch_obj.id)
    if user is not None:
        expenses = filter_queryset_by_branch_scope(expenses, user, "cashbox__branch_id")
        incomes = filter_queryset_by_branch_scope(incomes, user, "cashbox__branch_id")
        cashboxes = filter_queryset_by_branch_scope(cashboxes, user, "branch_id")

    gross_sales = _sum_money(sales, "total_amount")
    other_income = _sum_money(incomes, "amount")
    total_income = gross_sales + other_income
    total_expense = _sum_money(expenses, "amount")
    cashbox_balance = _sum_money(cashboxes, "current_balance")
    data = {
        "from": _serialize_date(date_from),
        "to": _serialize_date(date_to),
        "total_income": _money(total_income),
        "other_income": _money(other_income),
        "total_expense": _money(total_expense),
        "gross_sales": _money(gross_sales),
        "estimated_profit": None,
        "profit_message": "Foyda hisoblash uchun tannarx ma'lumotlari yetarli emas.",
        "cashbox_balance": _money(cashbox_balance),
        "expense_count": expenses.count(),
        "income_count": incomes.count(),
    }
    _apply_filter_details(data, branch=branch_obj)
    return _ok(data)


@_safe_tool
def get_customer_debt(user=None, customer_id=None, customer_name=None, limit=10) -> dict:
    queryset = Customer.objects.filter(is_active=True)
    if customer_id:
        customer = queryset.filter(id=customer_id).first()
    elif customer_name:
        customer = queryset.filter(full_name__icontains=customer_name).first()
    else:
        customer = None

    if customer:
        last_sale_date = (
            Sale.objects.filter(customer=customer)
            .order_by("-sale_date")
            .values_list("sale_date", flat=True)
            .first()
        )
        return _ok(
            {
                "customer_id": str(customer.id),
                "customer_name": customer.full_name,
                "debt_amount": _money(customer.balance),
                "phone": customer.phone,
                "last_purchase_date": _serialize_datetime(last_sale_date),
            }
        )

    debtors = list(queryset.filter(balance__gt=0).order_by("-balance", "full_name")[:limit])
    if customer_id or customer_name:
        return _not_found("Mijoz topilmadi.")
    return _ok(
        {
            "debtors": [
                {
                    "customer_id": str(customer.id),
                    "customer_name": customer.full_name,
                    "debt_amount": _money(customer.balance),
                    "phone": customer.phone,
                }
                for customer in debtors
            ],
            "count": len(debtors),
        }
    )


@_safe_tool
def get_reports_summary(
    user=None,
    date=None,
    date_range=None,
    branch_id=None,
    branch=None,
    warehouse_id=None,
    warehouse=None,
    date_from=None,
    date_to=None,
) -> dict:
    if user is not None and not _user_can_use_sensitive_reports(user):
        return _permission_denied("Hisobot xulosasini ko'rish uchun ruxsat yo'q.")

    branch_obj, error = _resolve_branch(user=user, branch_id=branch_id, branch=branch)
    if error:
        return error
    warehouse_obj, error = _resolve_warehouse(
        user=user,
        warehouse_id=warehouse_id,
        warehouse=warehouse,
        branch_obj=branch_obj,
    )
    if error:
        return error
    date_from, date_to = _range_from_entities(
        date_value=date,
        date_range=date_range,
        date_from=date_from,
        date_to=date_to,
    )
    sales_result = get_monthly_sales(
        user=user,
        date_range={"from": _serialize_date(date_from), "to": _serialize_date(date_to)},
        branch_id=branch_obj.id if branch_obj else None,
        warehouse_id=warehouse_obj.id if warehouse_obj else None,
    )
    top_result = get_top_products(
        user=user,
        date_range={"from": _serialize_date(date_from), "to": _serialize_date(date_to)},
        limit=5,
        branch_id=branch_obj.id if branch_obj else None,
        warehouse_id=warehouse_obj.id if warehouse_obj else None,
    )
    low_stock_result = get_low_stock_products(
        user=user,
        limit=5,
        branch_id=branch_obj.id if branch_obj else None,
        warehouse_id=warehouse_obj.id if warehouse_obj else None,
    )
    finance_result = get_finance_summary(
        user=user,
        date_range={"from": _serialize_date(date_from), "to": _serialize_date(date_to)},
        branch_id=branch_obj.id if branch_obj else None,
    )
    data = {
        "from": _serialize_date(date_from),
        "to": _serialize_date(date_to),
        "sales": sales_result.get("data", {}),
        "top_products": top_result.get("data", {}).get("products", []),
        "low_stock_products": low_stock_result.get("data", {}).get("products", []),
        "finance": finance_result.get("data", {})
        if finance_result.get("status") == "ok"
        else None,
    }
    _apply_filter_details(data, branch=branch_obj, warehouse=warehouse_obj)
    return _ok(data)


TOOL_DISPATCH = {
    INTENT_SALES_TODAY: ("get_today_sales", get_today_sales),
    INTENT_SALES_MONTH: ("get_monthly_sales", get_monthly_sales),
    INTENT_PRODUCT_STOCK: ("get_product_stock", get_product_stock),
    INTENT_LOW_STOCK: ("get_low_stock_products", get_low_stock_products),
    INTENT_TOP_PRODUCTS: ("get_top_products", get_top_products),
    INTENT_PRODUCT_PRICE: ("get_product_price", get_product_price),
    INTENT_CASHIER_ACTIVITY: ("get_cashier_activity", get_cashier_activity),
    INTENT_FINANCE_SUMMARY: ("get_finance_summary", get_finance_summary),
    INTENT_CUSTOMER_DEBT: ("get_customer_debt", get_customer_debt),
    INTENT_REPORTS_SUMMARY: ("get_reports_summary", get_reports_summary),
}


def get_tool_name(intent: str) -> str:
    entry = TOOL_DISPATCH.get(intent)
    return entry[0] if entry else ""


def run_tool(intent: str, entities: dict, user=None) -> dict:
    if intent in {INTENT_HELP, INTENT_UNKNOWN}:
        return _ok({})

    entry = TOOL_DISPATCH.get(intent)
    if entry is None:
        return _not_supported("Bu intent uchun tool hali qo'shilmagan.")

    _tool_name, tool = entry
    kwargs = {"user": user}
    branch_filters = {
        "branch_id": entities.get("branch_id"),
        "branch": entities.get("raw_branch_query") or entities.get("branch_name"),
    }
    warehouse_filters = {
        "warehouse_id": entities.get("warehouse_id"),
        "warehouse": entities.get("raw_warehouse_query") or entities.get("warehouse_name"),
    }
    date_filters = {
        "date_from": entities.get("date_from"),
        "date_to": entities.get("date_to"),
    }
    if intent == INTENT_SALES_TODAY:
        kwargs.update(
            {
                "date": entities.get("date"),
                "date_range": entities.get("date_range"),
                **date_filters,
                **branch_filters,
                **warehouse_filters,
            }
        )
    elif intent == INTENT_SALES_MONTH:
        kwargs.update(
            {
                "date_range": entities.get("date_range"),
                **date_filters,
                **branch_filters,
                **warehouse_filters,
            }
        )
    elif intent == INTENT_PRODUCT_STOCK:
        kwargs.update(
            {
                "product_id": entities.get("product_id"),
                "product_name": entities.get("raw_product_query") or entities.get("product_name"),
                **branch_filters,
                **warehouse_filters,
            }
        )
    elif intent == INTENT_PRODUCT_PRICE:
        kwargs.update(
            {
                "product_id": entities.get("product_id"),
                "product_name": entities.get("raw_product_query") or entities.get("product_name"),
                **branch_filters,
                **warehouse_filters,
            }
        )
    elif intent == INTENT_LOW_STOCK:
        kwargs.update({"category_id": entities.get("category_id"), **branch_filters, **warehouse_filters})
    elif intent == INTENT_TOP_PRODUCTS:
        kwargs.update(
            {
                "date_range": entities.get("date_range"),
                "category_id": entities.get("category_id"),
                **date_filters,
                **branch_filters,
                **warehouse_filters,
            }
        )
    elif intent == INTENT_CASHIER_ACTIVITY:
        kwargs.update(
            {
                "cashier_id": entities.get("cashier_id"),
                "date": entities.get("date"),
                "date_range": entities.get("date_range"),
                **date_filters,
                **branch_filters,
            }
        )
    elif intent == INTENT_FINANCE_SUMMARY:
        kwargs.update(
            {
                "date": entities.get("date"),
                "date_range": entities.get("date_range"),
                **date_filters,
                **branch_filters,
            }
        )
    elif intent == INTENT_CUSTOMER_DEBT:
        kwargs.update(
            {
                "customer_id": entities.get("customer_id"),
                "customer_name": entities.get("raw_customer_query") or entities.get("customer_name"),
            }
        )
    elif intent == INTENT_REPORTS_SUMMARY:
        kwargs.update(
            {
                "date": entities.get("date"),
                "date_range": entities.get("date_range"),
                **date_filters,
                **branch_filters,
                **warehouse_filters,
            }
        )

    return tool(**kwargs)
