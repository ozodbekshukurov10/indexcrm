from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from apps.accounts.models import User
from apps.catalog.models import Category, Product, Unit
from apps.inventory.models import Stock, StockMovement, StockMovementType, Warehouse
from apps.purchases.models import Purchase, PurchaseItem, PurchaseStatus, Supplier
from apps.purchases.services import (
    cancel_purchase,
    confirm_purchase,
    create_purchase_payment,
    recalculate_purchase_totals,
)
from apps.stores.models import Branch, Store


@pytest.fixture
def purchase_context(db):
    user = User.objects.create_user(email="owner@example.com", password="test-pass")
    store = Store.objects.create(name="Index Mini Market", owner=user)
    branch = Branch.objects.create(store=store, name="Main Branch")
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
    supplier = Supplier.objects.create(company_name="Index Wholesale")
    purchase = Purchase.objects.create(
        supplier=supplier,
        warehouse=warehouse,
        invoice_number="INV-0001",
        discount=Decimal("1000.00"),
        created_by=user,
    )
    PurchaseItem.objects.create(
        purchase=purchase,
        product=product,
        quantity=Decimal("10.000"),
        purchase_price=Decimal("2500.00"),
    )
    recalculate_purchase_totals(purchase)
    return user, supplier, warehouse, product, purchase


@pytest.mark.django_db
def test_confirm_purchase_increases_stock_and_supplier_debt(purchase_context):
    user, supplier, warehouse, product, purchase = purchase_context

    confirmed_purchase = confirm_purchase(purchase, confirmed_by=user)

    stock = Stock.objects.get(warehouse=warehouse, product=product)
    supplier.refresh_from_db()

    assert confirmed_purchase.status == PurchaseStatus.CONFIRMED
    assert stock.quantity == Decimal("10.000")
    assert supplier.balance == Decimal("24000.00")
    assert StockMovement.objects.filter(
        product=product,
        warehouse=warehouse,
        movement_type=StockMovementType.IN,
        quantity=Decimal("10.000"),
    ).exists()


@pytest.mark.django_db
def test_confirm_purchase_prevents_duplicate_confirmation(purchase_context):
    user, *_rest, purchase = purchase_context

    confirm_purchase(purchase, confirmed_by=user)

    with pytest.raises(ValidationError):
        confirm_purchase(purchase, confirmed_by=user)

    assert StockMovement.objects.filter(movement_type=StockMovementType.IN).count() == 1


@pytest.mark.django_db
def test_cancel_confirmed_purchase_rolls_back_stock_and_debt(purchase_context):
    user, supplier, warehouse, product, purchase = purchase_context

    confirm_purchase(purchase, confirmed_by=user)
    cancelled_purchase = cancel_purchase(purchase, cancelled_by=user)

    stock = Stock.objects.get(warehouse=warehouse, product=product)
    supplier.refresh_from_db()

    assert cancelled_purchase.status == PurchaseStatus.CANCELLED
    assert stock.quantity == Decimal("0.000")
    assert supplier.balance == Decimal("0.00")
    assert (
        StockMovement.objects.filter(movement_type=StockMovementType.OUT).count() == 1
    )


@pytest.mark.django_db
def test_purchase_payment_reduces_supplier_debt_after_confirmation(purchase_context):
    user, supplier, _warehouse, _product, purchase = purchase_context

    confirm_purchase(purchase, confirmed_by=user)
    create_purchase_payment(
        purchase=purchase,
        amount=Decimal("4000.00"),
        payment_method="CASH",
        created_by=user,
    )

    purchase.refresh_from_db()
    supplier.refresh_from_db()

    assert purchase.paid_amount == Decimal("4000.00")
    assert purchase.remaining_amount == Decimal("20000.00")
    assert supplier.balance == Decimal("20000.00")
