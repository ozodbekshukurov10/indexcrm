from decimal import Decimal

import pytest

from apps.accounts.models import User
from apps.catalog.models import Category, Product, Unit
from apps.finance.models import CashBox
from apps.finance.selectors import get_cashbox_summary
from apps.inventory.models import Stock
from apps.inventory.selectors import get_low_stock_products
from apps.purchases.models import Purchase, PurchaseItem, Supplier
from apps.purchases.selectors import get_recent_purchases
from apps.sales.models import Customer
from apps.sales.selectors import get_recent_sales
from apps.sales.services import create_sale
from apps.stores.models import Branch, Store


@pytest.fixture
def selector_context(db):
    user = User.objects.create_user(email="selectors@example.com", password="test-pass")
    store = Store.objects.create(name="Index Mini Market", owner=user)
    branch = Branch.objects.create(store=store, name="Main Branch", manager=user)
    cashbox = CashBox.objects.create(branch=branch, name="Main Cashbox")
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
    customer = Customer.objects.create(full_name="Ali Valiyev")
    supplier = Supplier.objects.create(company_name="Index Wholesale")
    Stock.objects.create(
        warehouse=warehouse,
        product=product,
        quantity=Decimal("2.000"),
        low_stock_limit=Decimal("5.000"),
    )
    return user, branch, warehouse, cashbox, product, customer, supplier


@pytest.mark.django_db
def test_recent_sales_and_purchases_selectors(selector_context):
    user, branch, warehouse, _cashbox, product, customer, supplier = selector_context
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
    )
    Purchase.objects.create(
        supplier=supplier,
        warehouse=warehouse,
        invoice_number="INV-SEL-0001",
        created_by=user,
    )
    PurchaseItem.objects.create(
        purchase=Purchase.objects.get(invoice_number="INV-SEL-0001"),
        product=product,
        quantity=Decimal("1.000"),
        purchase_price=Decimal("2500.00"),
    )

    recent_sales = get_recent_sales(limit=5)
    recent_purchases = get_recent_purchases(limit=5)

    assert recent_sales.first().pk == sale.pk
    assert recent_purchases.first().invoice_number == "INV-SEL-0001"


@pytest.mark.django_db
def test_low_stock_and_cashbox_summary_helpers(selector_context):
    _user, branch, warehouse, cashbox, product, _customer, _supplier = selector_context

    low_stock = get_low_stock_products(limit=10)
    summary = get_cashbox_summary(cashbox)

    assert low_stock.first().product_id == product.id
    assert summary["cashbox_id"] == str(cashbox.id)
    assert summary["branch_name"] == branch.name
    assert summary["current_balance"] == Decimal("0.00")
    assert summary["transaction_count"] == 0
