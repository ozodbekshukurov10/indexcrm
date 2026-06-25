from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from apps.accounts.models import User
from apps.cashier.services import close_cashier_shift, open_cashier_shift
from apps.catalog.models import Category, Product, Unit
from apps.finance.models import (
    CashBox,
    CashTransaction,
    CashTransactionType,
    DailyClosing,
    ExpenseCategory,
    Income,
)
from apps.finance.services import (
    add_expense,
    add_income,
    close_daily_shift,
    record_cash_transaction,
    record_customer_payment_transaction,
    record_purchase_payment_transaction,
    record_refund_transaction,
    record_sale_transaction,
    record_supplier_payment_transaction,
)
from apps.inventory.models import Stock
from apps.inventory.services import StockService
from apps.purchases.models import Purchase, PurchaseItem, Supplier, SupplierPayment
from apps.purchases.services import (
    confirm_purchase,
    create_purchase_payment,
    create_supplier_payment,
    recalculate_purchase_totals,
)
from apps.sales.models import Customer, CustomerPayment, SalePaymentMethod
from apps.sales.services import (
    complete_sale,
    create_customer_payment,
    create_sale,
    refund_sale,
)
from apps.stores.models import Branch, Store


@pytest.fixture
def finance_context(db):
    user = User.objects.create_user(email="finance@example.com", password="test-pass")
    store = Store.objects.create(name="Index Mini Market", owner=user)
    branch = Branch.objects.create(store=store, name="Main Branch", manager=user)
    cashbox = CashBox.objects.create(
        branch=branch,
        name="Main Cashbox",
        current_balance=Decimal("100000.00"),
    )
    category = Category.objects.create(name="Beverages")
    unit = Unit.objects.create(name="piece", short_name="pcs")
    warehouse = branch.warehouses.create(name="Main Warehouse")
    product = Product.objects.create(
        category=category,
        name="Sparkling Water 1L",
        sku="WATER-1L",
        selling_price=Decimal("4000.00"),
        unit=unit,
        created_by=user,
    )
    customer = Customer.objects.create(full_name="Ali Valiyev", phone="+998901234567")
    supplier = Supplier.objects.create(company_name="Index Wholesale")
    StockService.increase_stock(
        warehouse=warehouse,
        product=product,
        quantity=Decimal("10.000"),
        created_by=user,
        note="Initial stock",
    )
    return user, branch, warehouse, cashbox, product, customer, supplier


@pytest.mark.django_db
def test_income_and_expense_update_cashbox_and_transactions(finance_context):
    user, _branch, _warehouse, cashbox, _product, _customer, _supplier = finance_context
    expense_category = ExpenseCategory.objects.create(name="Utilities")

    add_income(
        cashbox=cashbox,
        amount=Decimal("25000.00"),
        source="Owner deposit",
        created_by=user,
    )
    add_expense(
        cashbox=cashbox,
        category=expense_category,
        amount=Decimal("10000.00"),
        note="Electricity",
        created_by=user,
    )

    cashbox.refresh_from_db()

    assert cashbox.current_balance == Decimal("115000.00")
    assert CashTransaction.objects.filter(
        cashbox=cashbox,
        transaction_type=CashTransactionType.INCOME,
        amount=Decimal("25000.00"),
    ).exists()
    assert CashTransaction.objects.filter(
        cashbox=cashbox,
        transaction_type=CashTransactionType.EXPENSE,
        amount=Decimal("10000.00"),
    ).exists()
    assert Income.objects.filter(
        cashbox=cashbox,
        source="Owner deposit",
        amount=Decimal("25000.00"),
    ).exists()


@pytest.mark.django_db
def test_invalid_finance_amounts_are_blocked(finance_context):
    user, _branch, _warehouse, cashbox, _product, _customer, _supplier = finance_context
    expense_category = ExpenseCategory.objects.create(name="Supplies")

    with pytest.raises(ValidationError):
        add_income(
            cashbox=cashbox,
            amount=Decimal("0.00"),
            source="Owner deposit",
            created_by=user,
        )

    with pytest.raises(ValidationError):
        add_expense(
            cashbox=cashbox,
            category=expense_category,
            amount=Decimal("-10.00"),
            created_by=user,
        )

    with pytest.raises(ValidationError):
        record_cash_transaction(
            cashbox=cashbox,
            transaction_type=CashTransactionType.ADJUSTMENT,
            amount=Decimal("0.00"),
            created_by=user,
        )


@pytest.mark.django_db
def test_expense_prevents_negative_cashbox_balance(finance_context):
    user, _branch, _warehouse, cashbox, _product, _customer, _supplier = finance_context
    cashbox.current_balance = Decimal("1000.00")
    cashbox.save(update_fields=("current_balance", "updated_at"))
    expense_category = ExpenseCategory.objects.create(name="Rent")

    with pytest.raises(ValidationError):
        add_expense(
            cashbox=cashbox,
            category=expense_category,
            amount=Decimal("2000.00"),
            created_by=user,
        )

    cashbox.refresh_from_db()
    assert cashbox.current_balance == Decimal("1000.00")


@pytest.mark.django_db
def test_purchase_payment_creates_purchase_cash_transaction(finance_context):
    user, _branch, warehouse, cashbox, product, _customer, supplier = finance_context
    purchase = Purchase.objects.create(
        supplier=supplier,
        warehouse=warehouse,
        invoice_number="INV-FIN-0001",
        created_by=user,
    )
    PurchaseItem.objects.create(
        purchase=purchase,
        product=product,
        quantity=Decimal("2.000"),
        purchase_price=Decimal("2500.00"),
    )
    recalculate_purchase_totals(purchase)
    confirm_purchase(purchase, confirmed_by=user)

    payment = create_purchase_payment(
        purchase=purchase,
        amount=Decimal("4000.00"),
        payment_method="CASH",
        created_by=user,
    )

    cashbox.refresh_from_db()

    assert cashbox.current_balance == Decimal("96000.00")
    assert CashTransaction.objects.filter(
        transaction_type=CashTransactionType.PURCHASE,
        reference_type="purchase_payment",
        reference_id=payment.id,
        amount=Decimal("4000.00"),
    ).exists()


@pytest.mark.django_db
def test_supplier_debt_payment_creates_purchase_cash_transaction(finance_context):
    user, _branch, _warehouse, cashbox, _product, _customer, supplier = finance_context
    supplier.balance = Decimal("12000.00")
    supplier.save(update_fields=("balance", "updated_at"))

    payment = create_supplier_payment(
        supplier=supplier,
        cashbox=cashbox,
        amount=Decimal("5000.00"),
        payment_method="CASH",
        created_by=user,
    )

    cashbox.refresh_from_db()
    supplier.refresh_from_db()

    assert supplier.balance == Decimal("7000.00")
    assert cashbox.current_balance == Decimal("95000.00")
    assert SupplierPayment.objects.filter(pk=payment.pk, cashbox=cashbox).exists()
    assert CashTransaction.objects.filter(
        transaction_type=CashTransactionType.PURCHASE,
        reference_type="supplier_payment",
        reference_id=payment.id,
        amount=Decimal("5000.00"),
    ).exists()


@pytest.mark.django_db
def test_sale_refund_and_customer_debt_payment_create_cash_transactions(
    finance_context,
):
    user, branch, warehouse, cashbox, product, customer, _supplier = finance_context
    sale = create_sale(
        branch=branch,
        warehouse=warehouse,
        cashier=user,
        customer=customer,
        items=[
            {
                "product": product,
                "quantity": Decimal("2.000"),
                "price": Decimal("4000.00"),
                "discount": Decimal("0.00"),
            }
        ],
        payments=[
            {"payment_method": SalePaymentMethod.CASH, "amount": Decimal("5000.00")},
            {"payment_method": SalePaymentMethod.DEBT, "amount": Decimal("3000.00")},
        ],
    )

    complete_sale(sale, completed_by=user)
    create_customer_payment(
        customer=customer,
        cashbox=cashbox,
        amount=Decimal("3000.00"),
        payment_method="CASH",
        created_by=user,
    )
    refund = refund_sale(
        sale,
        cashier=user,
        reason="Customer returned one bottle",
        items=[{"product": product, "quantity": Decimal("1.000")}],
    )

    cashbox.refresh_from_db()
    stock = Stock.objects.get(warehouse=warehouse, product=product)
    customer.refresh_from_db()

    assert stock.quantity == Decimal("9.000")
    assert customer.balance == Decimal("0.00")
    assert cashbox.current_balance == Decimal("104000.00")
    assert CashTransaction.objects.filter(
        reference_type="sale",
        reference_id=sale.id,
    ).exists()
    assert CashTransaction.objects.filter(
        reference_type="customer_payment",
        amount=Decimal("3000.00"),
    ).exists()
    assert CashTransaction.objects.filter(
        reference_type="refund",
        reference_id=refund.id,
        amount=Decimal("4000.00"),
    ).exists()
    assert CustomerPayment.objects.filter(
        customer=customer,
        cashbox=cashbox,
        amount=Decimal("3000.00"),
    ).exists()


@pytest.mark.django_db
def test_duplicate_finance_transactions_are_prevented(finance_context):
    user, branch, warehouse, cashbox, product, customer, supplier = finance_context
    sale = create_sale(
        branch=branch,
        warehouse=warehouse,
        cashier=user,
        customer=customer,
        items=[
            {
                "product": product,
                "quantity": Decimal("1.000"),
                "price": Decimal("4000.00"),
                "discount": Decimal("0.00"),
            }
        ],
        payments=[
            {"payment_method": SalePaymentMethod.CASH, "amount": Decimal("4000.00")}
        ],
    )
    complete_sale(sale, completed_by=user)
    sale.refresh_from_db()

    sale_transaction = record_sale_transaction(sale, created_by=user)
    assert sale_transaction is not None
    assert (
        CashTransaction.objects.filter(
            transaction_type=CashTransactionType.SALE,
            reference_type="sale",
            reference_id=sale.id,
        ).count()
        == 1
    )

    purchase = Purchase.objects.create(
        supplier=supplier,
        warehouse=warehouse,
        invoice_number="INV-FIN-0002",
        created_by=user,
    )
    PurchaseItem.objects.create(
        purchase=purchase,
        product=product,
        quantity=Decimal("2.000"),
        purchase_price=Decimal("2000.00"),
    )
    recalculate_purchase_totals(purchase)
    confirm_purchase(purchase, confirmed_by=user)
    purchase_payment = create_purchase_payment(
        purchase=purchase,
        amount=Decimal("1500.00"),
        payment_method="CASH",
        created_by=user,
    )
    record_purchase_payment_transaction(purchase_payment, created_by=user)
    assert (
        CashTransaction.objects.filter(
            transaction_type=CashTransactionType.PURCHASE,
            reference_type="purchase_payment",
            reference_id=purchase_payment.id,
        ).count()
        == 1
    )

    customer.balance = Decimal("3000.00")
    customer.save(update_fields=("balance", "updated_at"))
    customer_payment = create_customer_payment(
        customer=customer,
        cashbox=cashbox,
        amount=Decimal("1000.00"),
        payment_method="CASH",
        created_by=user,
    )
    record_customer_payment_transaction(customer_payment, created_by=user)
    assert (
        CashTransaction.objects.filter(
            transaction_type=CashTransactionType.INCOME,
            reference_type="customer_payment",
            reference_id=customer_payment.id,
        ).count()
        == 1
    )

    supplier.balance = Decimal("5000.00")
    supplier.save(update_fields=("balance", "updated_at"))
    supplier_payment = create_supplier_payment(
        supplier=supplier,
        cashbox=cashbox,
        amount=Decimal("1200.00"),
        payment_method="CASH",
        created_by=user,
    )
    record_supplier_payment_transaction(supplier_payment, created_by=user)
    assert (
        CashTransaction.objects.filter(
            transaction_type=CashTransactionType.PURCHASE,
            reference_type="supplier_payment",
            reference_id=supplier_payment.id,
        ).count()
        == 1
    )

    refund = refund_sale(
        sale,
        cashier=user,
        reason="Customer returned product",
        items=[{"product": product, "quantity": Decimal("1.000")}],
    )
    record_refund_transaction(refund, created_by=user)
    assert (
        CashTransaction.objects.filter(
            transaction_type=CashTransactionType.REFUND,
            reference_type="refund",
            reference_id=refund.id,
        ).count()
        == 1
    )


@pytest.mark.django_db
def test_daily_closing_requires_closed_shift_and_prevents_double_closing(
    finance_context,
):
    user, branch, warehouse, _cashbox, product, customer, _supplier = finance_context
    shift = open_cashier_shift(
        cashier=user,
        branch=branch,
        opening_balance=Decimal("100000.00"),
    )
    sale = create_sale(
        branch=branch,
        warehouse=warehouse,
        cashier=user,
        customer=customer,
        items=[
            {
                "product": product,
                "quantity": Decimal("1.000"),
                "price": Decimal("4000.00"),
                "discount": Decimal("0.00"),
            }
        ],
        payments=[
            {"payment_method": SalePaymentMethod.CASH, "amount": Decimal("4000.00")}
        ],
    )
    complete_sale(sale, completed_by=user)

    with pytest.raises(ValidationError):
        close_daily_shift(branch=branch, cashier=user, actual_cash=Decimal("104000.00"))

    closed_shift = close_cashier_shift(
        shift=shift,
        closing_balance=Decimal("104000.00"),
    )
    closing = close_daily_shift(
        branch=branch,
        cashier=user,
        cashier_shift=closed_shift,
        actual_cash=Decimal("104000.00"),
    )

    assert closing.total_sales == Decimal("4000.00")
    assert closing.expected_cash == Decimal("104000.00")
    assert closing.difference == Decimal("0.00")
    assert DailyClosing.objects.filter(
        pk=closing.pk, cashier_shift=closed_shift
    ).exists()

    with pytest.raises(ValidationError):
        close_daily_shift(
            branch=branch,
            cashier=user,
            cashier_shift=closed_shift,
            actual_cash=Decimal("104000.00"),
        )
