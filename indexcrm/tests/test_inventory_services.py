from datetime import date
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from apps.accounts.models import User
from apps.catalog.models import Category, Product, Unit
from apps.inventory.models import Stock, StockMovement, StockMovementType, Warehouse
from apps.inventory.selectors import low_stock_queryset
from apps.inventory.services import StockService
from apps.stores.models import Branch, Store


@pytest.fixture
def stock_context(db):
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
    return user, warehouse, product


@pytest.mark.django_db
def test_stock_service_increases_stock_and_logs_movement(stock_context):
    user, warehouse, product = stock_context

    movement = StockService.increase_stock(
        warehouse=warehouse,
        product=product,
        quantity=Decimal("10.000"),
        created_by=user,
        note="Initial stock",
    )

    stock = Stock.objects.get(warehouse=warehouse, product=product)

    assert stock.quantity == Decimal("10.000")
    assert movement.movement_type == StockMovementType.IN
    assert movement.quantity == Decimal("10.000")
    assert StockMovement.objects.count() == 1


@pytest.mark.django_db
def test_stock_service_rejects_negative_stock(stock_context):
    user, warehouse, product = stock_context

    with pytest.raises(ValidationError):
        StockService.decrease_stock(
            warehouse=warehouse,
            product=product,
            quantity=Decimal("1.000"),
            created_by=user,
        )

    assert not Stock.objects.filter(warehouse=warehouse, product=product).exists()
    assert StockMovement.objects.count() == 0


@pytest.mark.django_db
def test_stock_service_logs_expiry_date_on_movement(stock_context):
    user, warehouse, product = stock_context
    product.has_expiry_date = True
    product.save(update_fields=("has_expiry_date", "updated_at"))

    movement = StockService.increase_stock(
        warehouse=warehouse,
        product=product,
        quantity=Decimal("5.000"),
        expiry_date=date(2026, 12, 31),
        created_by=user,
    )

    assert movement.expiry_date == date(2026, 12, 31)


@pytest.mark.django_db
def test_low_stock_selector_returns_rows_at_or_below_limit(stock_context):
    user, warehouse, product = stock_context
    StockService.increase_stock(
        warehouse=warehouse,
        product=product,
        quantity=Decimal("3.000"),
        created_by=user,
    )
    stock = Stock.objects.get(warehouse=warehouse, product=product)
    stock.low_stock_limit = Decimal("5.000")
    stock.save(update_fields=("low_stock_limit", "updated_at"))

    assert low_stock_queryset().filter(pk=stock.pk).exists()
