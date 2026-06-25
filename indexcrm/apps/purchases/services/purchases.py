from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import DecimalField, Sum, Value
from django.db.models.functions import Coalesce
from django.utils import timezone

from apps.inventory.models import StockMovementType
from apps.inventory.services import StockService
from apps.purchases.models import (
    MONEY_QUANT,
    PaymentMethod,
    Purchase,
    PurchaseItem,
    PurchasePayment,
    PurchaseStatus,
    Supplier,
    SupplierPayment,
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


def recalculate_purchase_totals(purchase: Purchase, *, save=True) -> Purchase:
    subtotal = (
        PurchaseItem.objects.filter(purchase=purchase).aggregate(
            total=Coalesce(
                Sum("total_price"),
                Value(Decimal("0.00")),
                output_field=DecimalField(max_digits=14, decimal_places=2),
            )
        )["total"]
    ).quantize(MONEY_QUANT)
    paid_amount = (
        PurchasePayment.objects.filter(purchase=purchase).aggregate(
            total=Coalesce(
                Sum("amount"),
                Value(Decimal("0.00")),
                output_field=DecimalField(max_digits=14, decimal_places=2),
            )
        )["total"]
    ).quantize(MONEY_QUANT)

    purchase.calculate_amounts(subtotal=subtotal, paid_amount=paid_amount)

    if save:
        purchase.full_clean()
        purchase.save(
            update_fields=(
                "subtotal",
                "total_amount",
                "paid_amount",
                "remaining_amount",
                "updated_at",
            )
        )

    return purchase


@transaction.atomic
def create_purchase_item(**data) -> PurchaseItem:
    purchase = data["purchase"]
    purchase = Purchase.objects.select_for_update().get(pk=purchase.pk)

    if not purchase.is_editable:
        raise ValidationError(
            {"purchase": "Cannot edit items after purchase confirmation."}
        )

    data["purchase"] = purchase
    item = PurchaseItem.objects.create(**data)
    recalculate_purchase_totals(purchase)
    return item


@transaction.atomic
def update_purchase_item(item: PurchaseItem, **data) -> PurchaseItem:
    item = (
        PurchaseItem.objects.select_for_update()
        .select_related("purchase")
        .get(pk=item.pk)
    )

    if not item.purchase.is_editable:
        raise ValidationError(
            {"purchase": "Cannot edit items after purchase confirmation."}
        )

    for field_name, value in data.items():
        setattr(item, field_name, value)
    item.save()
    recalculate_purchase_totals(item.purchase)
    return item


@transaction.atomic
def delete_purchase_item(item: PurchaseItem) -> None:
    item = (
        PurchaseItem.objects.select_for_update()
        .select_related("purchase")
        .get(pk=item.pk)
    )

    if not item.purchase.is_editable:
        raise ValidationError(
            {"purchase": "Cannot delete items after purchase confirmation."}
        )

    purchase = item.purchase
    item.delete()
    recalculate_purchase_totals(purchase)


@transaction.atomic
def create_supplier_payment(
    *,
    supplier: Supplier,
    cashbox=None,
    amount,
    payment_method: str = PaymentMethod.CASH,
    note: str = "",
    paid_at=None,
    created_by=None,
) -> SupplierPayment:
    amount = _to_money(amount)
    supplier = Supplier.objects.select_for_update().get(pk=supplier.pk)

    if amount > supplier.balance:
        raise ValidationError({"amount": "Payment cannot exceed supplier debt."})

    payment = SupplierPayment.objects.create(
        supplier=supplier,
        cashbox=cashbox,
        amount=amount,
        payment_method=payment_method,
        note=note,
        paid_at=paid_at or timezone.now(),
        created_by=_authenticated_user(created_by),
    )

    supplier.balance = (supplier.balance - amount).quantize(MONEY_QUANT)
    supplier.full_clean()
    supplier.save(update_fields=("balance", "updated_at"))

    from apps.finance.services import record_supplier_payment_transaction

    record_supplier_payment_transaction(payment, created_by=created_by)
    return payment


@transaction.atomic
def create_purchase_payment(
    *,
    purchase: Purchase,
    amount,
    payment_method: str = PaymentMethod.CASH,
    note: str = "",
    paid_at=None,
    created_by=None,
) -> PurchasePayment:
    amount = _to_money(amount)
    purchase = (
        Purchase.objects.select_for_update()
        .select_related("supplier")
        .get(pk=purchase.pk)
    )

    if purchase.status == PurchaseStatus.CANCELLED:
        raise ValidationError({"purchase": "Cannot pay for a cancelled purchase."})

    recalculate_purchase_totals(purchase)

    if amount > purchase.remaining_amount:
        raise ValidationError(
            {"amount": "Payment cannot exceed remaining purchase debt."}
        )

    payment = PurchasePayment.objects.create(
        purchase=purchase,
        amount=amount,
        payment_method=payment_method,
        note=note,
        paid_at=paid_at or timezone.now(),
        created_by=_authenticated_user(created_by),
    )

    purchase.paid_amount = (purchase.paid_amount + amount).quantize(MONEY_QUANT)
    purchase.remaining_amount = (purchase.total_amount - purchase.paid_amount).quantize(
        MONEY_QUANT
    )
    purchase.full_clean()
    purchase.save(update_fields=("paid_amount", "remaining_amount", "updated_at"))

    if purchase.status == PurchaseStatus.CONFIRMED:
        supplier = Supplier.objects.select_for_update().get(pk=purchase.supplier_id)
        supplier.balance = max(
            Decimal("0.00"), (supplier.balance - amount).quantize(MONEY_QUANT)
        )
        supplier.full_clean()
        supplier.save(update_fields=("balance", "updated_at"))

    from apps.finance.services import record_purchase_payment_transaction

    record_purchase_payment_transaction(payment, created_by=created_by)

    return payment


@transaction.atomic
def confirm_purchase(purchase: Purchase, *, confirmed_by=None) -> Purchase:
    purchase = (
        Purchase.objects.select_for_update()
        .select_related("supplier", "warehouse")
        .get(pk=purchase.pk)
    )
    supplier = Supplier.objects.select_for_update().get(pk=purchase.supplier_id)

    if purchase.status == PurchaseStatus.CONFIRMED:
        raise ValidationError({"status": "Purchase is already confirmed."})
    if purchase.status == PurchaseStatus.CANCELLED:
        raise ValidationError({"status": "Cancelled purchases cannot be confirmed."})

    items = list(
        PurchaseItem.objects.select_related("product")
        .select_for_update()
        .filter(purchase=purchase)
    )
    if not items:
        raise ValidationError({"items": "Purchase must have at least one item."})

    recalculate_purchase_totals(purchase)

    for item in items:
        if item.product.has_expiry_date and not item.expiry_date:
            raise ValidationError(
                {
                    "expiry_date": (
                        f"Expiry date is required for product {item.product.name}."
                    )
                }
            )

        StockService.increase_stock(
            warehouse=purchase.warehouse,
            product=item.product,
            quantity=item.quantity,
            created_by=confirmed_by,
            expiry_date=item.expiry_date,
            note=(
                f"Purchase {purchase.invoice_number} confirmed"
                + (f"; expiry {item.expiry_date}" if item.expiry_date else "")
            ),
            movement_type=StockMovementType.IN,
        )

    supplier.balance = (supplier.balance + purchase.remaining_amount).quantize(
        MONEY_QUANT
    )
    supplier.full_clean()
    supplier.save(update_fields=("balance", "updated_at"))

    purchase.status = PurchaseStatus.CONFIRMED
    purchase.confirmed_by = _authenticated_user(confirmed_by)
    purchase.confirmed_at = timezone.now()
    purchase.full_clean()
    purchase.save(
        update_fields=(
            "status",
            "confirmed_by",
            "confirmed_at",
            "updated_at",
        )
    )
    from apps.accounts.models import AuditAction
    from apps.accounts.services import record_audit_log

    record_audit_log(
        actor=confirmed_by,
        action=AuditAction.PURCHASE,
        entity_type="purchases.Purchase",
        entity_id=purchase.id,
        object_repr=purchase.invoice_number,
        summary="Purchase confirmed.",
        metadata={
            "supplier_id": str(purchase.supplier_id),
            "warehouse_id": str(purchase.warehouse_id),
            "total_amount": str(purchase.total_amount),
        },
    )
    return purchase


@transaction.atomic
def cancel_purchase(purchase: Purchase, *, cancelled_by=None) -> Purchase:
    purchase = (
        Purchase.objects.select_for_update()
        .select_related("supplier", "warehouse")
        .get(pk=purchase.pk)
    )

    if purchase.status == PurchaseStatus.CANCELLED:
        raise ValidationError({"status": "Purchase is already cancelled."})

    if purchase.status == PurchaseStatus.DRAFT:
        purchase.status = PurchaseStatus.CANCELLED
        purchase.full_clean()
        purchase.save(update_fields=("status", "updated_at"))
        from apps.accounts.models import AuditAction
        from apps.accounts.services import record_audit_log

        record_audit_log(
            actor=cancelled_by,
            action=AuditAction.PURCHASE,
            entity_type="purchases.Purchase",
            entity_id=purchase.id,
            object_repr=purchase.invoice_number,
            summary="Draft purchase cancelled.",
            metadata={
                "supplier_id": str(purchase.supplier_id),
                "warehouse_id": str(purchase.warehouse_id),
            },
        )
        return purchase

    supplier = Supplier.objects.select_for_update().get(pk=purchase.supplier_id)
    recalculate_purchase_totals(purchase)

    items = list(
        PurchaseItem.objects.select_related("product")
        .select_for_update()
        .filter(purchase=purchase)
    )
    for item in items:
        StockService.decrease_stock(
            warehouse=purchase.warehouse,
            product=item.product,
            quantity=item.quantity,
            created_by=cancelled_by,
            note=f"Purchase {purchase.invoice_number} cancelled",
            movement_type=StockMovementType.OUT,
        )

    supplier.balance = max(
        Decimal("0.00"),
        (supplier.balance - purchase.remaining_amount).quantize(MONEY_QUANT),
    )
    supplier.full_clean()
    supplier.save(update_fields=("balance", "updated_at"))

    purchase.status = PurchaseStatus.CANCELLED
    purchase.full_clean()
    purchase.save(update_fields=("status", "updated_at"))
    from apps.accounts.models import AuditAction
    from apps.accounts.services import record_audit_log

    record_audit_log(
        actor=cancelled_by,
        action=AuditAction.PURCHASE,
        entity_type="purchases.Purchase",
        entity_id=purchase.id,
        object_repr=purchase.invoice_number,
        summary="Purchase cancelled.",
        metadata={
            "supplier_id": str(purchase.supplier_id),
            "warehouse_id": str(purchase.warehouse_id),
        },
    )
    return purchase
