from decimal import Decimal

import pytest

from apps.accounts.models import User
from apps.cashier.services import close_cashier_shift, open_cashier_shift
from apps.catalog.models import Category, Product, Unit
from apps.inventory.models import Stock, StockMovement, StockMovementType, Warehouse
from apps.inventory.services import StockService
from apps.sales.models import Customer, SalePaymentMethod, SaleStatus
from apps.sales.services import complete_sale, create_sale, refund_sale
from apps.stores.models import Branch, Store


@pytest.fixture
def sales_context(db):
    user = User.objects.create_user(email="cashier@example.com", password="test-pass")
    store = Store.objects.create(name="Index Mini Market", owner=user)
    branch = Branch.objects.create(store=store, name="Main Branch", manager=user)
    warehouse = Warehouse.objects.create(branch=branch, name="Main Warehouse")
    category = Category.objects.create(name="Beverages")
    unit = Unit.objects.create(name="piece", short_name="pcs")
    product = Product.objects.create(
        category=category,
        name="Sparkling Water 1L",
        sku="WATER-1L",
        selling_price=Decimal("4000.00"),
        unit=unit,
        created_by=user,
    )
    customer = Customer.objects.create(full_name="Ali Valiyev", phone="+998901234567")
    StockService.increase_stock(
        warehouse=warehouse,
        product=product,
        quantity=Decimal("10.000"),
        created_by=user,
        note="Initial stock",
    )
    return user, branch, warehouse, product, customer


def create_debt_sale(user, branch, warehouse, product, customer):
    return create_sale(
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


@pytest.mark.django_db
def test_complete_sale_reduces_stock_and_creates_customer_debt(sales_context):
    user, branch, warehouse, product, customer = sales_context
    sale = create_debt_sale(user, branch, warehouse, product, customer)

    completed_sale = complete_sale(sale, completed_by=user)

    stock = Stock.objects.get(warehouse=warehouse, product=product)
    customer.refresh_from_db()

    assert completed_sale.status == SaleStatus.COMPLETED
    assert stock.quantity == Decimal("8.000")
    assert customer.balance == Decimal("3000.00")
    assert StockMovement.objects.filter(
        warehouse=warehouse,
        product=product,
        movement_type=StockMovementType.OUT,
        quantity=Decimal("2.000"),
    ).exists()


@pytest.mark.django_db
def test_create_sale_reuses_existing_sale_for_idempotency_key(sales_context):
    user, branch, warehouse, product, customer = sales_context
    sale = create_sale(
        branch=branch,
        warehouse=warehouse,
        cashier=user,
        customer=customer,
        idempotency_key="offline-checkout-001",
        items=[
            {
                "product": product,
                "quantity": Decimal("1.000"),
                "price": Decimal("4000.00"),
                "discount": Decimal("0.00"),
            }
        ],
        payments=[
            {"payment_method": SalePaymentMethod.CASH, "amount": Decimal("4000.00")},
        ],
    )

    retried_sale = create_sale(
        branch=branch,
        warehouse=warehouse,
        cashier=user,
        customer=customer,
        idempotency_key="offline-checkout-001",
        items=[
            {
                "product": product,
                "quantity": Decimal("1.000"),
                "price": Decimal("4000.00"),
                "discount": Decimal("0.00"),
            }
        ],
        payments=[
            {"payment_method": SalePaymentMethod.CASH, "amount": Decimal("4000.00")},
        ],
    )

    assert retried_sale.id == sale.id
    assert sale.items.count() == 1
    assert sale.payments.count() == 1


@pytest.mark.django_db
def test_complete_sale_is_idempotent_after_success(sales_context):
    user, branch, warehouse, product, customer = sales_context
    sale = create_debt_sale(user, branch, warehouse, product, customer)

    completed_sale = complete_sale(sale, completed_by=user)
    retried_sale = complete_sale(sale, completed_by=user)

    assert retried_sale.id == completed_sale.id
    assert retried_sale.status == SaleStatus.COMPLETED
    assert (
        StockMovement.objects.filter(movement_type=StockMovementType.OUT).count() == 1
    )


@pytest.mark.django_db
def test_refund_sale_restores_stock_and_reduces_customer_debt(sales_context):
    user, branch, warehouse, product, customer = sales_context
    sale = create_debt_sale(user, branch, warehouse, product, customer)
    complete_sale(sale, completed_by=user)

    refund = refund_sale(
        sale,
        cashier=user,
        reason="Customer returned one bottle",
        items=[{"product": product, "quantity": Decimal("1.000")}],
    )

    stock = Stock.objects.get(warehouse=warehouse, product=product)
    customer.refresh_from_db()
    sale.refresh_from_db()

    assert refund.total_amount == Decimal("4000.00")
    assert stock.quantity == Decimal("9.000")
    assert customer.balance == Decimal("0.00")
    assert sale.status == SaleStatus.REFUNDED
    assert StockMovement.objects.filter(movement_type=StockMovementType.IN).count() == 2


@pytest.mark.django_db
def test_cashier_shift_close_calculates_expected_cash_balance(sales_context):
    user, branch, warehouse, product, customer = sales_context
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
            {"payment_method": SalePaymentMethod.CASH, "amount": Decimal("4000.00")},
        ],
    )
    complete_sale(sale, completed_by=user)

    closed_shift = close_cashier_shift(
        shift=shift,
        closing_balance=Decimal("104000.00"),
    )

    assert closed_shift.expected_balance == Decimal("104000.00")
    assert closed_shift.difference == Decimal("0.00")
