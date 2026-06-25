from io import StringIO

import pytest
from django.core.management import call_command

from apps.accounts.models import User
from apps.cashier.models import CashierShift
from apps.catalog.models import Product
from apps.common.management.commands.seed_demo_data import (
    DEMO_ADMIN_EMAIL,
    DEMO_BRANCH_NAME,
    DEMO_CASHIER_EMAIL,
    DEMO_STORE_NAME,
    DEMO_WAREHOUSE_NAME,
    DEMO_SAMPLE_SALE_KEY,
    PRODUCTS,
)
from apps.inventory.models import Stock, Warehouse
from apps.sales.models import Sale, SaleStatus
from apps.stores.models import Branch, Store


@pytest.mark.django_db
def test_seed_demo_data_is_idempotent_and_creates_core_records():
    output = StringIO()

    call_command("seed_demo_data", stdout=output)
    first_counts = {
        "stores": Store.objects.filter(name=DEMO_STORE_NAME).count(),
        "branches": Branch.objects.filter(name=DEMO_BRANCH_NAME).count(),
        "warehouses": Warehouse.objects.filter(name=DEMO_WAREHOUSE_NAME).count(),
        "products": Product.objects.filter(sku__startswith="IDX-").count(),
        "stocks": Stock.objects.filter(product__sku__startswith="IDX-").count(),
        "sales": Sale.objects.filter(idempotency_key=DEMO_SAMPLE_SALE_KEY).count(),
    }

    call_command("seed_demo_data", stdout=StringIO())
    second_counts = {
        "stores": Store.objects.filter(name=DEMO_STORE_NAME).count(),
        "branches": Branch.objects.filter(name=DEMO_BRANCH_NAME).count(),
        "warehouses": Warehouse.objects.filter(name=DEMO_WAREHOUSE_NAME).count(),
        "products": Product.objects.filter(sku__startswith="IDX-").count(),
        "stocks": Stock.objects.filter(product__sku__startswith="IDX-").count(),
        "sales": Sale.objects.filter(idempotency_key=DEMO_SAMPLE_SALE_KEY).count(),
    }

    assert first_counts == second_counts
    assert first_counts["products"] == len(PRODUCTS)
    assert first_counts["products"] >= 60
    assert User.objects.filter(email=DEMO_ADMIN_EMAIL, is_superuser=True).exists()
    assert User.objects.filter(email=DEMO_CASHIER_EMAIL, role="cashier").exists()
    assert Product.objects.filter(name="Coca-Cola 1L").exists()
    assert Stock.objects.filter(product__sku="IDX-WATER-500", quantity__gt=0).exists()
    assert CashierShift.objects.filter(
        cashier__email=DEMO_CASHIER_EMAIL,
        closed_at__isnull=True,
    ).exists()
    assert Sale.objects.filter(
        idempotency_key=DEMO_SAMPLE_SALE_KEY,
        status=SaleStatus.COMPLETED,
    ).exists()
    assert "Demo data is ready" in output.getvalue()
