from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User, UserProfile, UserRole
from apps.cashier.services import close_cashier_shift, open_cashier_shift
from apps.catalog.models import Category, Product, Unit
from apps.inventory.models import Stock, StockMovement, StockMovementType
from apps.inventory.services import StockService
from apps.sales.models import Sale, SalePaymentMethod, SaleStatus
from apps.stores.models import Branch, Store


@pytest.fixture
def scoped_pos_context(db):
    owner = User.objects.create_user(
        email="owner-rbac@example.com",
        password="test-pass-123",
        role=UserRole.OWNER,
    )
    cashier = User.objects.create_user(
        email="cashier-rbac@example.com",
        password="test-pass-123",
        role=UserRole.CASHIER,
    )
    other_cashier = User.objects.create_user(
        email="other-cashier-rbac@example.com",
        password="test-pass-123",
        role=UserRole.CASHIER,
    )
    store = Store.objects.create(name="Index Scoped Store", owner=owner)
    branch = Branch.objects.create(store=store, name="Allowed Branch")
    other_branch = Branch.objects.create(store=store, name="Other Branch")
    warehouse = branch.warehouses.create(name="Allowed Warehouse")
    other_warehouse = other_branch.warehouses.create(name="Other Warehouse")
    UserProfile.objects.create(user=cashier, branch=branch)

    category = Category.objects.create(name="RBAC Beverages")
    unit = Unit.objects.create(name="piece-rbac", short_name="pcs-rbac")
    product = Product.objects.create(
        category=category,
        name="Scoped Water",
        sku="SCOPED-WATER",
        selling_price=Decimal("4000.00"),
        unit=unit,
        created_by=owner,
    )
    StockService.increase_stock(
        warehouse=warehouse,
        product=product,
        quantity=Decimal("10.000"),
        created_by=owner,
    )
    return owner, cashier, other_cashier, branch, other_branch, warehouse, other_warehouse, product


def sale_payload(
    branch,
    warehouse,
    product,
    key="scoped-checkout-1",
    quantity="1.000",
    amount="4000.00",
):
    return {
        "branch": str(branch.id),
        "warehouse": str(warehouse.id),
        "idempotency_key": key,
        "discount_amount": "0.00",
        "tax_amount": "0.00",
        "items": [
            {
                "product": str(product.id),
                "quantity": quantity,
                "price": "4000.00",
                "discount": "0.00",
            }
        ],
        "payments": [
            {"payment_method": SalePaymentMethod.CASH, "amount": amount}
        ],
    }


@pytest.mark.django_db
def test_pos_checkout_requires_active_cashier_shift(scoped_pos_context):
    (
        _owner,
        cashier,
        _other_cashier,
        branch,
        _other_branch,
        warehouse,
        _other_warehouse,
        product,
    ) = scoped_pos_context
    client = APIClient()
    client.force_authenticate(user=cashier)

    missing_shift_response = client.post(
        "/api/v1/sales/",
        sale_payload(branch, warehouse, product),
        format="json",
    )
    assert missing_shift_response.status_code == 400
    assert missing_shift_response.data["code"] == "shift_closed_missing"
    assert "active cashier shift" in missing_shift_response.data["message"].lower()
    assert "shift" in missing_shift_response.data
    assert not Sale.objects.filter(idempotency_key="scoped-checkout-1").exists()

    active_response = client.get(
        "/api/v1/cashier-shifts/active/",
        {"branch": str(branch.id)},
    )
    assert active_response.status_code == 200
    assert active_response.data is None

    shift = open_cashier_shift(cashier=cashier, branch=branch)
    active_response = client.get(
        "/api/v1/cashier-shifts/active/",
        {"branch": str(branch.id)},
    )
    assert active_response.status_code == 200
    assert active_response.data["id"] == str(shift.id)

    sale_response = client.post(
        "/api/v1/sales/",
        sale_payload(branch, warehouse, product, "scoped-checkout-2"),
        format="json",
    )
    assert sale_response.status_code == 201

    complete_response = client.post(
        f"/api/v1/sales/{sale_response.data['id']}/complete/",
    )
    assert complete_response.status_code == 200
    assert complete_response.data["status"] == "COMPLETED"


@pytest.mark.django_db
def test_unauthenticated_pos_sale_requires_login(scoped_pos_context):
    (
        _owner,
        _cashier,
        _other_cashier,
        branch,
        _other_branch,
        warehouse,
        _other_warehouse,
        product,
    ) = scoped_pos_context
    client = APIClient()

    response = client.post(
        "/api/v1/sales/",
        sale_payload(branch, warehouse, product, "anonymous-checkout-key"),
        format="json",
    )

    assert response.status_code in {401, 403}
    assert not Sale.objects.filter(idempotency_key="anonymous-checkout-key").exists()


@pytest.mark.django_db
def test_pos_sale_idempotency_reuses_same_payload(scoped_pos_context):
    (
        _owner,
        cashier,
        _other_cashier,
        branch,
        _other_branch,
        warehouse,
        _other_warehouse,
        product,
    ) = scoped_pos_context
    open_cashier_shift(cashier=cashier, branch=branch)
    client = APIClient()
    client.force_authenticate(user=cashier)
    payload = sale_payload(branch, warehouse, product, "same-payload-key")

    first_response = client.post("/api/v1/sales/", payload, format="json")
    second_response = client.post("/api/v1/sales/", payload, format="json")

    assert first_response.status_code == 201
    assert second_response.status_code == 201
    assert second_response.data["id"] == first_response.data["id"]
    assert Sale.objects.filter(idempotency_key="same-payload-key").count() == 1


@pytest.mark.django_db
def test_pos_sale_idempotency_rejects_different_payload(scoped_pos_context):
    (
        _owner,
        cashier,
        _other_cashier,
        branch,
        _other_branch,
        warehouse,
        _other_warehouse,
        product,
    ) = scoped_pos_context
    open_cashier_shift(cashier=cashier, branch=branch)
    client = APIClient()
    client.force_authenticate(user=cashier)

    first_response = client.post(
        "/api/v1/sales/",
        sale_payload(branch, warehouse, product, "conflicting-key"),
        format="json",
    )
    conflict_response = client.post(
        "/api/v1/sales/",
        sale_payload(
            branch,
            warehouse,
            product,
            "conflicting-key",
            quantity="2.000",
            amount="8000.00",
        ),
        format="json",
    )

    assert first_response.status_code == 201
    assert conflict_response.status_code == 409
    assert conflict_response.data["code"] == "idempotency_conflict"
    assert Sale.objects.filter(idempotency_key="conflicting-key").count() == 1


@pytest.mark.django_db
def test_pos_api_completion_decreases_stock_once_for_replayed_checkout(
    scoped_pos_context,
):
    (
        _owner,
        cashier,
        _other_cashier,
        branch,
        _other_branch,
        warehouse,
        _other_warehouse,
        product,
    ) = scoped_pos_context
    open_cashier_shift(cashier=cashier, branch=branch)
    client = APIClient()
    client.force_authenticate(user=cashier)

    sale_response = client.post(
        "/api/v1/sales/",
        sale_payload(branch, warehouse, product, "stock-once-key"),
        format="json",
    )
    first_complete_response = client.post(
        f"/api/v1/sales/{sale_response.data['id']}/complete/",
    )
    replay_complete_response = client.post(
        f"/api/v1/sales/{sale_response.data['id']}/complete/",
    )

    stock = Stock.objects.get(warehouse=warehouse, product=product)

    assert sale_response.status_code == 201
    assert first_complete_response.status_code == 200
    assert replay_complete_response.status_code == 200
    assert replay_complete_response.data["status"] == SaleStatus.COMPLETED
    assert stock.quantity == Decimal("9.000")
    assert (
        StockMovement.objects.filter(
            warehouse=warehouse,
            product=product,
            movement_type=StockMovementType.OUT,
        ).count()
        == 1
    )


@pytest.mark.django_db
def test_pos_checkout_rejects_closed_cashier_shift(scoped_pos_context):
    (
        _owner,
        cashier,
        _other_cashier,
        branch,
        _other_branch,
        warehouse,
        _other_warehouse,
        product,
    ) = scoped_pos_context
    shift = open_cashier_shift(cashier=cashier, branch=branch)
    close_cashier_shift(shift=shift, closing_balance=Decimal("0.00"))
    client = APIClient()
    client.force_authenticate(user=cashier)

    response = client.post(
        "/api/v1/sales/",
        sale_payload(branch, warehouse, product, "closed-shift-key"),
        format="json",
    )

    assert response.status_code == 400
    assert response.data["code"] == "shift_closed_missing"


@pytest.mark.django_db
def test_pos_checkout_rejects_mismatched_branch_and_warehouse_without_sale(
    scoped_pos_context,
):
    (
        owner,
        _cashier,
        _other_cashier,
        branch,
        _other_branch,
        _warehouse,
        other_warehouse,
        product,
    ) = scoped_pos_context
    client = APIClient()
    client.force_authenticate(user=owner)

    response = client.post(
        "/api/v1/sales/",
        sale_payload(branch, other_warehouse, product, "mismatched-context-key"),
        format="json",
    )

    assert response.status_code == 400
    assert response.data["code"] == "scope_denied"
    assert "warehouse" in response.data
    assert not Sale.objects.filter(idempotency_key="mismatched-context-key").exists()


@pytest.mark.django_db
def test_pos_checkout_rejects_out_of_scope_branch(scoped_pos_context):
    (
        _owner,
        cashier,
        _other_cashier,
        branch,
        other_branch,
        _warehouse,
        other_warehouse,
        product,
    ) = scoped_pos_context
    open_cashier_shift(cashier=cashier, branch=branch)
    client = APIClient()
    client.force_authenticate(user=cashier)

    response = client.post(
        "/api/v1/sales/",
        sale_payload(other_branch, other_warehouse, product, "scope-blocked-key"),
        format="json",
    )

    assert response.status_code == 403
    assert response.data["code"] == "scope_denied"


@pytest.mark.django_db
def test_pos_complete_sale_reports_stock_conflict(scoped_pos_context):
    (
        _owner,
        cashier,
        _other_cashier,
        branch,
        _other_branch,
        warehouse,
        _other_warehouse,
        product,
    ) = scoped_pos_context
    open_cashier_shift(cashier=cashier, branch=branch)
    client = APIClient()
    client.force_authenticate(user=cashier)

    sale_response = client.post(
        "/api/v1/sales/",
        sale_payload(
            branch,
            warehouse,
            product,
            "stock-conflict-key",
            quantity="999.000",
            amount="3996000.00",
        ),
        format="json",
    )
    complete_response = client.post(
        f"/api/v1/sales/{sale_response.data['id']}/complete/",
    )

    assert sale_response.status_code == 201
    assert complete_response.status_code == 400
    assert complete_response.data["code"] == "stock_conflict"
    assert "stock" in complete_response.data["message"].lower()
    assert Sale.objects.get(id=sale_response.data["id"]).status == SaleStatus.DRAFT
    assert not StockMovement.objects.filter(
        warehouse=warehouse,
        product=product,
        movement_type=StockMovementType.OUT,
    ).exists()


@pytest.mark.django_db
def test_cashier_operational_lists_are_branch_scoped(scoped_pos_context):
    (
        _owner,
        cashier,
        other_cashier,
        branch,
        other_branch,
        warehouse,
        other_warehouse,
        _product,
    ) = scoped_pos_context
    own_sale = Sale.objects.create(
        branch=branch,
        warehouse=warehouse,
        cashier=cashier,
    )
    Sale.objects.create(
        branch=other_branch,
        warehouse=other_warehouse,
        cashier=other_cashier,
    )

    client = APIClient()
    client.force_authenticate(user=cashier)

    sales_response = client.get("/api/v1/sales/")
    warehouse_response = client.get("/api/v1/warehouses/")

    assert sales_response.status_code == 200
    assert [row["id"] for row in sales_response.data["results"]] == [str(own_sale.id)]
    assert warehouse_response.status_code == 200
    assert [row["id"] for row in warehouse_response.data["results"]] == [
        str(warehouse.id)
    ]
