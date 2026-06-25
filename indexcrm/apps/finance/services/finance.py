import uuid
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Case, DecimalField, F, Sum, Value, When
from django.db.models.functions import Coalesce
from django.utils import timezone

from apps.cashier.models import CashierShift
from apps.finance.models import (
    MONEY_QUANT,
    CashBox,
    CashTransaction,
    CashTransactionType,
    DailyClosing,
    Expense,
    ExpenseCategory,
    Income,
)
from apps.purchases.models import PurchasePayment
from apps.sales.models import Refund, Sale


def _authenticated_user(user):
    return user if getattr(user, "is_authenticated", False) else None


def _to_money(value, field_name="amount", *, allow_negative=False):
    try:
        amount = Decimal(str(value)).quantize(MONEY_QUANT)
    except (InvalidOperation, TypeError, ValueError) as error:
        raise ValidationError(
            {field_name: "Amount must be a valid decimal."}
        ) from error

    if allow_negative:
        if amount == Decimal("0.00"):
            raise ValidationError({field_name: "Amount cannot be zero."})
        return amount

    if amount <= Decimal("0.00"):
        raise ValidationError({field_name: "Amount must be greater than zero."})
    return amount


def _transaction_delta(transaction_type, amount):
    if transaction_type in {CashTransactionType.INCOME, CashTransactionType.SALE}:
        return amount
    if transaction_type in {
        CashTransactionType.EXPENSE,
        CashTransactionType.PURCHASE,
        CashTransactionType.REFUND,
    }:
        return -amount
    return amount


def _existing_transaction(transaction_type, reference_type, reference_id):
    if not reference_type or reference_id is None:
        return None
    return CashTransaction.objects.filter(
        transaction_type=transaction_type,
        reference_type=reference_type,
        reference_id=reference_id,
    ).first()


def get_default_cashbox(branch) -> CashBox:
    cashbox = (
        CashBox.objects.select_for_update()
        .filter(branch=branch, is_active=True)
        .order_by("created_at")
        .first()
    )
    if cashbox:
        return cashbox

    return CashBox.objects.create(branch=branch, name="Main Cashbox")


@transaction.atomic
def record_cash_transaction(
    *,
    cashbox: CashBox,
    transaction_type: str,
    amount,
    reference_type: str = "",
    reference_id=None,
    note: str = "",
    created_by=None,
    prevent_negative: bool = False,
) -> CashTransaction:
    existing = _existing_transaction(transaction_type, reference_type, reference_id)
    if existing:
        return existing

    amount = _to_money(
        amount,
        allow_negative=transaction_type == CashTransactionType.ADJUSTMENT,
    )
    cashbox = CashBox.objects.select_for_update().get(pk=cashbox.pk)
    new_balance = (
        cashbox.current_balance + _transaction_delta(transaction_type, amount)
    ).quantize(MONEY_QUANT)
    if prevent_negative and new_balance < Decimal("0.00"):
        raise ValidationError({"cashbox": "Cashbox balance cannot become negative."})

    cashbox.current_balance = new_balance
    cashbox.full_clean()
    cashbox.save(update_fields=("current_balance", "updated_at"))

    cash_transaction = CashTransaction.objects.create(
        cashbox=cashbox,
        transaction_type=transaction_type,
        amount=amount,
        reference_type=reference_type,
        reference_id=reference_id,
        note=note,
        created_by=_authenticated_user(created_by),
    )
    cash_transaction.full_clean()

    from apps.accounts.models import AuditAction
    from apps.accounts.services import record_audit_log

    record_audit_log(
        actor=created_by,
        action=AuditAction.FINANCE,
        entity_type="finance.CashTransaction",
        entity_id=cash_transaction.id,
        object_repr=f"{transaction_type} {amount}",
        summary=note or f"{transaction_type} cash transaction recorded.",
        metadata={
            "cashbox_id": str(cashbox.id),
            "reference_type": reference_type,
            "reference_id": str(reference_id) if reference_id else "",
        },
    )
    return cash_transaction


@transaction.atomic
def add_expense(
    *,
    cashbox: CashBox,
    category: ExpenseCategory,
    amount,
    note: str = "",
    expense_date=None,
    created_by=None,
) -> Expense:
    amount = _to_money(amount)
    expense = Expense.objects.create(
        cashbox=cashbox,
        category=category,
        amount=amount,
        note=note,
        expense_date=expense_date or timezone.now(),
        created_by=_authenticated_user(created_by),
    )
    record_cash_transaction(
        cashbox=cashbox,
        transaction_type=CashTransactionType.EXPENSE,
        amount=amount,
        reference_type="expense",
        reference_id=expense.id,
        note=note or f"Expense: {category.name}",
        created_by=created_by,
        prevent_negative=True,
    )
    return expense


@transaction.atomic
def add_income(
    *,
    cashbox: CashBox,
    amount,
    source: str,
    note: str = "",
    income_date=None,
    created_by=None,
) -> Income:
    amount = _to_money(amount)
    income = Income.objects.create(
        cashbox=cashbox,
        amount=amount,
        source=source,
        note=note,
        income_date=income_date or timezone.now(),
        created_by=_authenticated_user(created_by),
    )
    record_cash_transaction(
        cashbox=cashbox,
        transaction_type=CashTransactionType.INCOME,
        amount=amount,
        reference_type="income",
        reference_id=income.id,
        note=note or f"Income: {source}",
        created_by=created_by,
    )
    return income


@transaction.atomic
def transfer_between_cashboxes(
    *,
    source_cashbox: CashBox,
    target_cashbox: CashBox,
    amount,
    note: str = "",
    created_by=None,
):
    if source_cashbox.pk == target_cashbox.pk:
        raise ValidationError({"target_cashbox": "Target cashbox must be different."})

    amount = _to_money(amount)
    locked_cashboxes = {
        cashbox.pk: cashbox
        for cashbox in CashBox.objects.select_for_update().filter(
            pk__in=sorted([source_cashbox.pk, target_cashbox.pk])
        )
    }
    source_cashbox = locked_cashboxes[source_cashbox.pk]
    target_cashbox = locked_cashboxes[target_cashbox.pk]
    transfer_id = uuid.uuid4()

    source_transaction = record_cash_transaction(
        cashbox=source_cashbox,
        transaction_type=CashTransactionType.ADJUSTMENT,
        amount=-amount,
        reference_type="cashbox_transfer_out",
        reference_id=transfer_id,
        note=note or f"Transfer to {target_cashbox.name}",
        created_by=created_by,
        prevent_negative=True,
    )
    target_transaction = record_cash_transaction(
        cashbox=target_cashbox,
        transaction_type=CashTransactionType.ADJUSTMENT,
        amount=amount,
        reference_type="cashbox_transfer_in",
        reference_id=transfer_id,
        note=note or f"Transfer from {source_cashbox.name}",
        created_by=created_by,
    )
    return source_transaction, target_transaction


def calculate_cashbox_balance(
    cashbox: CashBox,
    *,
    date_from=None,
    date_to=None,
    save: bool = False,
):
    queryset = CashTransaction.objects.filter(cashbox=cashbox)
    if date_from:
        queryset = queryset.filter(created_at__gte=date_from)
    if date_to:
        queryset = queryset.filter(created_at__lte=date_to)

    delta_expression = Case(
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
    balance = queryset.aggregate(
        balance=Coalesce(
            Sum(delta_expression),
            Value(Decimal("0.00")),
            output_field=DecimalField(max_digits=14, decimal_places=2),
        )
    )["balance"].quantize(MONEY_QUANT)

    if save:
        cashbox = CashBox.objects.select_for_update().get(pk=cashbox.pk)
        cashbox.current_balance = balance
        cashbox.full_clean()
        cashbox.save(update_fields=("current_balance", "updated_at"))

    return balance


@transaction.atomic
def record_sale_transaction(sale: Sale, *, created_by=None):
    sale = Sale.objects.select_related("branch").get(pk=sale.pk)
    if sale.paid_amount <= Decimal("0.00"):
        return None

    cashbox = get_default_cashbox(sale.branch)
    return record_cash_transaction(
        cashbox=cashbox,
        transaction_type=CashTransactionType.SALE,
        amount=sale.paid_amount,
        reference_type="sale",
        reference_id=sale.id,
        note=f"Sale {sale.receipt_number}",
        created_by=created_by or sale.cashier,
    )


@transaction.atomic
def record_purchase_payment_transaction(
    purchase_payment: PurchasePayment,
    *,
    created_by=None,
):
    purchase_payment = PurchasePayment.objects.select_related(
        "purchase",
        "purchase__warehouse",
        "purchase__warehouse__branch",
        "created_by",
    ).get(pk=purchase_payment.pk)
    cashbox = get_default_cashbox(purchase_payment.purchase.warehouse.branch)
    return record_cash_transaction(
        cashbox=cashbox,
        transaction_type=CashTransactionType.PURCHASE,
        amount=purchase_payment.amount,
        reference_type="purchase_payment",
        reference_id=purchase_payment.id,
        note=f"Purchase payment {purchase_payment.purchase.invoice_number}",
        created_by=created_by or purchase_payment.created_by,
    )


@transaction.atomic
def record_supplier_payment_transaction(supplier_payment, *, created_by=None):
    from apps.purchases.models import SupplierPayment

    supplier_payment = (
        SupplierPayment.objects.select_related("supplier", "cashbox", "created_by")
        .filter(pk=supplier_payment.pk)
        .first()
    )
    if supplier_payment is None or supplier_payment.cashbox_id is None:
        return None

    return record_cash_transaction(
        cashbox=supplier_payment.cashbox,
        transaction_type=CashTransactionType.PURCHASE,
        amount=supplier_payment.amount,
        reference_type="supplier_payment",
        reference_id=supplier_payment.id,
        note=f"Supplier debt payment {supplier_payment.supplier.company_name}",
        created_by=created_by or supplier_payment.created_by,
    )


@transaction.atomic
def record_customer_payment_transaction(customer_payment, *, created_by=None):
    from apps.sales.models import CustomerPayment

    customer_payment = (
        CustomerPayment.objects.select_related("customer", "cashbox", "created_by")
        .filter(pk=customer_payment.pk)
        .first()
    )
    if customer_payment is None or customer_payment.cashbox_id is None:
        return None

    return record_cash_transaction(
        cashbox=customer_payment.cashbox,
        transaction_type=CashTransactionType.INCOME,
        amount=customer_payment.amount,
        reference_type="customer_payment",
        reference_id=customer_payment.id,
        note=f"Customer debt payment {customer_payment.customer.full_name}",
        created_by=created_by or customer_payment.created_by,
    )


@transaction.atomic
def record_refund_transaction(refund: Refund, *, created_by=None):
    refund = Refund.objects.select_related(
        "original_sale",
        "original_sale__branch",
        "cashier",
    ).get(pk=refund.pk)
    if refund.total_amount <= Decimal("0.00"):
        return None

    cashbox = get_default_cashbox(refund.original_sale.branch)
    return record_cash_transaction(
        cashbox=cashbox,
        transaction_type=CashTransactionType.REFUND,
        amount=refund.total_amount,
        reference_type="refund",
        reference_id=refund.id,
        note=f"Refund for sale {refund.original_sale.receipt_number}",
        created_by=created_by or refund.cashier,
    )


def _sum_money(queryset, field):
    return queryset.aggregate(
        total=Coalesce(
            Sum(field),
            Value(Decimal("0.00")),
            output_field=DecimalField(max_digits=14, decimal_places=2),
        )
    )["total"].quantize(MONEY_QUANT)


@transaction.atomic
def close_daily_shift(
    *,
    branch,
    cashier,
    actual_cash,
    cashier_shift: CashierShift | None = None,
    closed_at=None,
) -> DailyClosing:
    actual_cash = _to_money(actual_cash, field_name="actual_cash")
    cashier = _authenticated_user(cashier) or cashier
    closed_at = closed_at or timezone.now()

    open_shift_exists = (
        CashierShift.objects.select_for_update()
        .filter(
            branch=branch,
            cashier=cashier,
            closed_at__isnull=True,
        )
        .exists()
    )
    if open_shift_exists:
        raise ValidationError(
            {"cashier_shift": "Close the active cashier shift before daily closing."}
        )

    if cashier_shift is None:
        cashier_shift = (
            CashierShift.objects.select_for_update()
            .filter(
                branch=branch,
                cashier=cashier,
                closed_at__isnull=False,
                daily_closing__isnull=True,
            )
            .order_by("-closed_at")
            .first()
        )
    else:
        cashier_shift = (
            CashierShift.objects.select_for_update()
            .select_related("branch", "cashier")
            .get(pk=cashier_shift.pk)
        )

    if cashier_shift is None:
        raise ValidationError(
            {"cashier_shift": "No closed cashier shift is available for closing."}
        )
    if cashier_shift.closed_at is None:
        raise ValidationError({"cashier_shift": "Cashier shift must be closed first."})
    if hasattr(cashier_shift, "daily_closing"):
        raise ValidationError({"cashier_shift": "Cashier shift is already closed."})

    period_start = cashier_shift.opened_at
    period_end = cashier_shift.closed_at

    from apps.sales.models import Sale, SaleStatus

    sales = Sale.objects.filter(
        branch=branch,
        cashier=cashier,
        sale_date__gte=period_start,
        sale_date__lte=period_end,
        status__in=[SaleStatus.COMPLETED, SaleStatus.REFUNDED],
    )
    total_sales = _sum_money(sales, "total_amount")
    total_expenses = _sum_money(
        Expense.objects.filter(
            cashbox__branch=branch,
            created_by=cashier,
            expense_date__gte=period_start,
            expense_date__lte=period_end,
        ),
        "amount",
    )
    total_income = _sum_money(
        Income.objects.filter(
            cashbox__branch=branch,
            created_by=cashier,
            income_date__gte=period_start,
            income_date__lte=period_end,
        ),
        "amount",
    )
    expected_cash = cashier_shift.expected_balance.quantize(MONEY_QUANT)
    difference = (actual_cash - expected_cash).quantize(MONEY_QUANT)

    daily_closing = DailyClosing.objects.create(
        branch=branch,
        cashier=cashier,
        cashier_shift=cashier_shift,
        total_sales=total_sales,
        total_expenses=total_expenses,
        total_income=total_income,
        expected_cash=expected_cash,
        actual_cash=actual_cash,
        difference=difference,
        closed_at=closed_at,
    )
    daily_closing.full_clean()
    return daily_closing
