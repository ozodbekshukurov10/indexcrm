import hashlib
import json
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import DecimalField, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.utils import timezone

from apps.inventory.models import StockMovementType
from apps.inventory.services import StockService
from apps.sales.exceptions import SaleIdempotencyConflictError
from apps.sales.models import (
    MONEY_QUANT,
    Customer,
    CustomerPayment,
    CustomerPaymentMethod,
    LoyaltyAccount,
    Refund,
    RefundItem,
    Sale,
    SaleItem,
    SalePayment,
    SalePaymentMethod,
    SaleStatus,
)


def _to_money(value, field_name="amount"):
    try:
        amount = Decimal(str(value)).quantize(MONEY_QUANT)
    except (InvalidOperation, TypeError, ValueError) as error:
        raise ValidationError(
            {field_name: "Amount must be a valid decimal."}
        ) from error

    if amount <= Decimal("0.00"):
        raise ValidationError({field_name: "Amount must be greater than zero."})

    return amount


def _authenticated_user(user):
    return user if getattr(user, "is_authenticated", False) else None


def _normalize_idempotency_key(value):
    return str(value).strip() if value else None


def _identity(value):
    if value is None:
        return None
    return str(getattr(value, "pk", value))


def _money(value, default="0.00"):
    if value is None:
        value = default
    return str(Decimal(str(value)).quantize(MONEY_QUANT))


def _quantity(value):
    return str(Decimal(str(value)).quantize(Decimal("0.001")))


def build_sale_idempotency_fingerprint(*, sale_data, items=None, payments=None):
    items = items or []
    payments = payments or []
    normalized_items = [
        {
            "product": _identity(item.get("product")),
            "quantity": _quantity(item.get("quantity")),
            "price": _money(item.get("price")),
            "discount": _money(item.get("discount")),
        }
        for item in items
    ]
    normalized_payments = [
        {
            "payment_method": payment.get("payment_method", SalePaymentMethod.CASH),
            "amount": _money(payment.get("amount")),
            "note": payment.get("note") or "",
        }
        for payment in payments
    ]
    payload = {
        "branch": _identity(sale_data.get("branch")),
        "warehouse": _identity(sale_data.get("warehouse")),
        "cashier": _identity(_authenticated_user(sale_data.get("cashier"))),
        "customer": _identity(sale_data.get("customer")),
        "discount_amount": _money(sale_data.get("discount_amount")),
        "tax_amount": _money(sale_data.get("tax_amount")),
        "note": sale_data.get("note") or "",
        "items": sorted(normalized_items, key=lambda item: json.dumps(item, sort_keys=True)),
        "payments": sorted(
            normalized_payments,
            key=lambda payment: json.dumps(payment, sort_keys=True),
        ),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _ensure_idempotency_fingerprint_matches(existing_sale, fingerprint):
    if (
        existing_sale.idempotency_fingerprint
        and fingerprint
        and existing_sale.idempotency_fingerprint != fingerprint
    ):
        raise SaleIdempotencyConflictError


def _payment_totals(sale: Sale):
    totals = SalePayment.objects.filter(sale=sale).aggregate(
        paid_amount=Coalesce(
            Sum("amount", filter=~Q(payment_method=SalePaymentMethod.DEBT)),
            Value(Decimal("0.00")),
            output_field=DecimalField(max_digits=14, decimal_places=2),
        ),
        debt_amount=Coalesce(
            Sum("amount", filter=Q(payment_method=SalePaymentMethod.DEBT)),
            Value(Decimal("0.00")),
            output_field=DecimalField(max_digits=14, decimal_places=2),
        ),
    )
    return totals["paid_amount"].quantize(MONEY_QUANT), totals["debt_amount"].quantize(
        MONEY_QUANT
    )


def recalculate_sale_totals(sale: Sale, *, save=True) -> Sale:
    subtotal = (
        SaleItem.objects.filter(sale=sale).aggregate(
            total=Coalesce(
                Sum("total_price"),
                Value(Decimal("0.00")),
                output_field=DecimalField(max_digits=14, decimal_places=2),
            )
        )["total"]
    ).quantize(MONEY_QUANT)
    paid_amount, debt_amount = _payment_totals(sale)

    sale.calculate_amounts(subtotal=subtotal, paid_amount=paid_amount)

    if paid_amount + debt_amount > sale.total_amount:
        raise ValidationError({"payments": "Sale payments cannot exceed total amount."})
    if debt_amount > Decimal("0.00") and debt_amount != sale.remaining_amount:
        raise ValidationError(
            {"payments": "Debt payment amount must match remaining amount."}
        )

    if save:
        sale.full_clean()
        sale.save(
            update_fields=(
                "subtotal",
                "total_amount",
                "paid_amount",
                "remaining_amount",
                "updated_at",
            )
        )

    return sale


@transaction.atomic
def create_sale(*, items=None, payments=None, **sale_data) -> Sale:
    items = items or []
    payments = payments or []
    idempotency_key = _normalize_idempotency_key(sale_data.get("idempotency_key"))
    sale_data["idempotency_key"] = idempotency_key
    fingerprint = None
    if idempotency_key:
        fingerprint = build_sale_idempotency_fingerprint(
            sale_data=sale_data,
            items=items,
            payments=payments,
        )
        sale_data["idempotency_fingerprint"] = fingerprint

    if idempotency_key:
        existing_sale = (
            Sale.objects.select_for_update()
            .filter(idempotency_key=idempotency_key)
            .first()
        )
        if existing_sale:
            _ensure_idempotency_fingerprint_matches(existing_sale, fingerprint)
            return existing_sale

    try:
        with transaction.atomic():
            sale = Sale.objects.create(**sale_data)
    except IntegrityError:
        if not idempotency_key:
            raise
        existing_sale = (
            Sale.objects.select_for_update()
            .filter(idempotency_key=idempotency_key)
            .first()
        )
        if existing_sale:
            _ensure_idempotency_fingerprint_matches(existing_sale, fingerprint)
            return existing_sale
        raise

    for item_data in items:
        create_sale_item(sale=sale, **item_data)
    for payment_data in payments:
        create_sale_payment(sale=sale, **payment_data)

    recalculate_sale_totals(sale)
    return sale


@transaction.atomic
def create_sale_item(**data) -> SaleItem:
    sale = data["sale"]
    sale = Sale.objects.select_for_update().get(pk=sale.pk)

    if not sale.is_editable:
        raise ValidationError({"sale": "Cannot edit items after sale completion."})

    data["sale"] = sale
    item = SaleItem.objects.create(**data)
    recalculate_sale_totals(sale)
    return item


@transaction.atomic
def update_sale_item(item: SaleItem, **data) -> SaleItem:
    item = SaleItem.objects.select_for_update().select_related("sale").get(pk=item.pk)

    if not item.sale.is_editable:
        raise ValidationError({"sale": "Cannot edit items after sale completion."})

    for field_name, value in data.items():
        setattr(item, field_name, value)
    item.save()
    recalculate_sale_totals(item.sale)
    return item


@transaction.atomic
def delete_sale_item(item: SaleItem) -> None:
    item = SaleItem.objects.select_for_update().select_related("sale").get(pk=item.pk)

    if not item.sale.is_editable:
        raise ValidationError({"sale": "Cannot delete items after sale completion."})

    sale = item.sale
    item.delete()
    recalculate_sale_totals(sale)


@transaction.atomic
def create_sale_payment(
    *,
    sale: Sale,
    payment_method: str = SalePaymentMethod.CASH,
    amount,
    note: str = "",
    paid_at=None,
) -> SalePayment:
    amount = _to_money(amount)
    sale = Sale.objects.select_for_update().get(pk=sale.pk)

    if not sale.is_editable:
        raise ValidationError({"sale": "Cannot edit payments after sale completion."})

    payment = SalePayment.objects.create(
        sale=sale,
        payment_method=payment_method,
        amount=amount,
        note=note,
        paid_at=paid_at or timezone.now(),
    )
    recalculate_sale_totals(sale)
    return payment


@transaction.atomic
def create_customer_payment(
    *,
    customer: Customer,
    cashbox=None,
    amount,
    payment_method: str = CustomerPaymentMethod.CASH,
    note: str = "",
    paid_at=None,
    created_by=None,
) -> CustomerPayment:
    amount = _to_money(amount)
    customer = Customer.objects.select_for_update().get(pk=customer.pk)

    if amount > customer.balance:
        raise ValidationError({"amount": "Payment cannot exceed customer debt."})

    payment = CustomerPayment.objects.create(
        customer=customer,
        cashbox=cashbox,
        amount=amount,
        payment_method=payment_method,
        note=note,
        paid_at=paid_at or timezone.now(),
        created_by=_authenticated_user(created_by),
    )
    customer.balance = (customer.balance - amount).quantize(MONEY_QUANT)
    customer.full_clean()
    customer.save(update_fields=("balance", "updated_at"))

    from apps.finance.services import record_customer_payment_transaction

    record_customer_payment_transaction(payment, created_by=created_by)
    return payment


@transaction.atomic
def complete_sale(sale: Sale, *, completed_by=None) -> Sale:
    sale = (
        Sale.objects.select_for_update()
        .select_related("customer", "warehouse", "branch", "cashier")
        .get(pk=sale.pk)
    )

    if sale.status == SaleStatus.COMPLETED:
        return sale
    if sale.status in {SaleStatus.CANCELLED, SaleStatus.REFUNDED}:
        raise ValidationError({"status": "Only draft sales can be completed."})

    items = list(
        SaleItem.objects.select_related("product").select_for_update().filter(sale=sale)
    )
    if not items:
        raise ValidationError({"items": "Sale must have at least one item."})

    recalculate_sale_totals(sale)

    if sale.remaining_amount > Decimal("0.00") and sale.customer_id is None:
        raise ValidationError({"customer": "Customer is required for debt sales."})

    for item in items:
        StockService.decrease_stock(
            warehouse=sale.warehouse,
            product=item.product,
            quantity=item.quantity,
            created_by=completed_by or sale.cashier,
            note=f"Sale {sale.receipt_number} completed",
            movement_type=StockMovementType.OUT,
        )

    if sale.customer_id and sale.remaining_amount > Decimal("0.00"):
        customer = Customer.objects.select_for_update().get(pk=sale.customer_id)
        customer.balance = (customer.balance + sale.remaining_amount).quantize(
            MONEY_QUANT
        )
        customer.full_clean()
        customer.save(update_fields=("balance", "updated_at"))

    if sale.customer_id:
        (
            loyalty_account,
            _created,
        ) = LoyaltyAccount.objects.select_for_update().get_or_create(
            customer_id=sale.customer_id
        )
        loyalty_account.total_spent = (
            loyalty_account.total_spent + sale.total_amount
        ).quantize(MONEY_QUANT)
        loyalty_account.points += int(sale.total_amount // Decimal("1000.00"))
        loyalty_account.save(update_fields=("total_spent", "points", "updated_at"))

    sale.status = SaleStatus.COMPLETED
    sale.sale_date = timezone.now()
    sale.full_clean()
    sale.save(update_fields=("status", "sale_date", "updated_at"))

    from apps.finance.services import record_sale_transaction

    record_sale_transaction(sale, created_by=completed_by or sale.cashier)
    from apps.accounts.models import AuditAction
    from apps.accounts.services import record_audit_log

    record_audit_log(
        actor=completed_by or sale.cashier,
        action=AuditAction.SALE,
        entity_type="sales.Sale",
        entity_id=sale.id,
        object_repr=sale.receipt_number,
        summary="Sale completed.",
        metadata={
            "branch_id": str(sale.branch_id),
            "total_amount": str(sale.total_amount),
            "paid_amount": str(sale.paid_amount),
        },
    )
    return sale


@transaction.atomic
def cancel_sale(sale: Sale) -> Sale:
    sale = Sale.objects.select_for_update().get(pk=sale.pk)

    if sale.status == SaleStatus.CANCELLED:
        raise ValidationError({"status": "Sale is already cancelled."})
    if sale.status != SaleStatus.DRAFT:
        raise ValidationError({"status": "Completed sales must be refunded."})

    sale.status = SaleStatus.CANCELLED
    sale.full_clean()
    sale.save(update_fields=("status", "updated_at"))
    return sale


def _default_refund_items(sale: Sale):
    return [
        {
            "product": item.product,
            "quantity": item.quantity,
            "amount": item.total_price,
        }
        for item in sale.items.select_related("product")
    ]


def _sold_quantity_for_product(sale: Sale, product):
    return SaleItem.objects.filter(sale=sale, product=product).aggregate(
        quantity=Coalesce(
            Sum("quantity"),
            Value(Decimal("0.000")),
            output_field=DecimalField(max_digits=14, decimal_places=3),
        )
    )["quantity"]


def _refunded_quantity_for_product(sale: Sale, product):
    return RefundItem.objects.filter(
        refund__original_sale=sale, product=product
    ).aggregate(
        quantity=Coalesce(
            Sum("quantity"),
            Value(Decimal("0.000")),
            output_field=DecimalField(max_digits=14, decimal_places=3),
        )
    )[
        "quantity"
    ]


@transaction.atomic
def refund_sale(
    sale: Sale,
    *,
    cashier=None,
    reason: str,
    items=None,
    refund_date=None,
) -> Refund:
    sale = (
        Sale.objects.select_for_update()
        .select_related("customer", "warehouse", "branch", "cashier")
        .get(pk=sale.pk)
    )

    if sale.status != SaleStatus.COMPLETED:
        raise ValidationError({"status": "Only completed sales can be refunded."})

    items = items or _default_refund_items(sale)
    if not items:
        raise ValidationError({"items": "Refund must include at least one item."})

    refund = Refund.objects.create(
        original_sale=sale,
        cashier=_authenticated_user(cashier) or sale.cashier,
        refund_date=refund_date or timezone.now(),
        reason=reason,
    )

    total_amount = Decimal("0.00")
    for item_data in items:
        product = item_data["product"]
        quantity = Decimal(str(item_data["quantity"]))
        if quantity <= Decimal("0.000"):
            raise ValidationError(
                {"quantity": "Refund quantity must be greater than zero."}
            )

        sold_quantity = _sold_quantity_for_product(sale, product)
        refunded_quantity = _refunded_quantity_for_product(sale, product)
        if quantity > sold_quantity - refunded_quantity:
            raise ValidationError(
                {"quantity": "Refund quantity exceeds sold quantity."}
            )

        amount = item_data.get("amount")
        if amount is None:
            sale_item = SaleItem.objects.filter(sale=sale, product=product).first()
            amount = ((sale_item.total_price / sale_item.quantity) * quantity).quantize(
                MONEY_QUANT
            )
        amount = _to_money(amount)
        total_amount += amount

        RefundItem.objects.create(
            refund=refund,
            product=product,
            quantity=quantity,
            amount=amount,
        )
        StockService.increase_stock(
            warehouse=sale.warehouse,
            product=product,
            quantity=quantity,
            created_by=cashier or sale.cashier,
            note=f"Refund for sale {sale.receipt_number}",
            movement_type=StockMovementType.IN,
        )

    refund.total_amount = total_amount.quantize(MONEY_QUANT)
    refund.full_clean()
    refund.save(update_fields=("total_amount", "updated_at"))

    if sale.customer_id:
        customer = Customer.objects.select_for_update().get(pk=sale.customer_id)
        customer.balance = max(
            Decimal("0.00"),
            (customer.balance - refund.total_amount).quantize(MONEY_QUANT),
        )
        customer.full_clean()
        customer.save(update_fields=("balance", "updated_at"))

    sale.status = SaleStatus.REFUNDED
    sale.full_clean()
    sale.save(update_fields=("status", "updated_at"))

    from apps.finance.services import record_refund_transaction

    record_refund_transaction(refund, created_by=cashier or sale.cashier)
    from apps.accounts.models import AuditAction
    from apps.accounts.services import record_audit_log

    record_audit_log(
        actor=cashier or sale.cashier,
        action=AuditAction.REFUND,
        entity_type="sales.Refund",
        entity_id=refund.id,
        object_repr=f"Refund {sale.receipt_number}",
        summary="Sale refunded.",
        metadata={
            "sale_id": str(sale.id),
            "total_amount": str(refund.total_amount),
        },
    )
    return refund


def build_receipt_data(sale: Sale) -> dict:
    sale = (
        Sale.objects.select_related("branch", "warehouse", "cashier", "customer")
        .prefetch_related("items__product", "payments")
        .get(pk=sale.pk)
    )
    return {
        "receipt_number": sale.receipt_number,
        "sale_date": sale.sale_date,
        "branch": {
            "id": str(sale.branch_id),
            "name": sale.branch.name,
            "address": sale.branch.address,
            "phone": sale.branch.phone,
        },
        "warehouse": {"id": str(sale.warehouse_id), "name": sale.warehouse.name},
        "cashier": {
            "id": str(sale.cashier_id),
            "email": sale.cashier.email,
            "full_name": sale.cashier.get_full_name(),
        },
        "customer": (
            {
                "id": str(sale.customer_id),
                "full_name": sale.customer.full_name,
                "phone": sale.customer.phone,
            }
            if sale.customer_id
            else None
        ),
        "items": [
            {
                "product_id": str(item.product_id),
                "product_name": item.product.name,
                "sku": item.product.sku,
                "quantity": item.quantity,
                "price": item.price,
                "discount": item.discount,
                "total_price": item.total_price,
            }
            for item in sale.items.all()
        ],
        "payments": [
            {
                "payment_method": payment.payment_method,
                "amount": payment.amount,
                "paid_at": payment.paid_at,
            }
            for payment in sale.payments.all()
        ],
        "totals": {
            "subtotal": sale.subtotal,
            "discount_amount": sale.discount_amount,
            "tax_amount": sale.tax_amount,
            "total_amount": sale.total_amount,
            "paid_amount": sale.paid_amount,
            "remaining_amount": sale.remaining_amount,
        },
        "qr_code": None,
        "fiscal": {
            "fiscal_receipt_id": None,
            "fiscal_sign": None,
            "fiscal_url": None,
            "terminal_id": None,
        },
    }
