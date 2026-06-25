from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import (
    AccountSession,
    AuditAction,
    AuditLog,
    FailedLoginAttempt,
    LoginHistory,
    LoginStatus,
    User,
    UserRole,
)
from apps.accounts.permissions import user_has_permission
from apps.catalog.models import Category, Product, Unit
from apps.finance.models import CashBox
from apps.inventory.services import StockService
from apps.purchases.models import Purchase, PurchaseItem, Supplier
from apps.purchases.services import confirm_purchase, recalculate_purchase_totals
from apps.sales.models import Customer, SalePaymentMethod
from apps.sales.services import complete_sale, create_sale, refund_sale
from apps.stores.models import Branch, Store


@pytest.fixture
def owner(db):
    return User.objects.create_user(
        email="owner@example.com",
        password="test-pass-123",
        role=UserRole.OWNER,
        is_staff=True,
    )


@pytest.mark.django_db
def test_profile_and_rbac_endpoints(owner):
    cashier = User.objects.create_user(
        email="cashier@example.com",
        password="test-pass-123",
        role=UserRole.CASHIER,
    )
    client = APIClient()
    client.force_authenticate(user=owner)

    profile_response = client.patch(
        "/api/accounts/me/profile/",
        {
            "position": "Operations lead",
            "language": "uz",
            "theme": "dark",
            "notification_preferences": {"low_stock": True},
        },
        format="json",
    )
    permission_response = client.post(
        "/api/accounts/permissions/",
        {
            "code": "reports.view",
            "name": "View reports",
            "module": "reports",
        },
        format="json",
    )
    role_response = client.post(
        "/api/accounts/roles/",
        {
            "code": "report-manager",
            "name": "Report manager",
            "permissions": [permission_response.data["id"]],
        },
        format="json",
    )
    assignment_response = client.post(
        "/api/accounts/role-assignments/",
        {
            "user": str(cashier.id),
            "role": role_response.data["id"],
        },
        format="json",
    )

    assert profile_response.status_code == 200
    assert profile_response.data["theme"] == "dark"
    assert permission_response.status_code == 201
    assert role_response.status_code == 201
    assert assignment_response.status_code == 201
    assert user_has_permission(cashier, "reports.view")

    client.force_authenticate(user=cashier)
    forbidden_response = client.get("/api/accounts/roles/")
    assert forbidden_response.status_code == 403


@pytest.mark.django_db
def test_audited_token_login_tracks_success_and_failure(owner):
    client = APIClient()

    success_response = client.post(
        "/api/v1/auth/token/",
        {"email": owner.email, "password": "test-pass-123"},
        format="json",
        HTTP_USER_AGENT="pytest-client",
    )
    failure_response = client.post(
        "/api/v1/auth/token/",
        {"email": owner.email, "password": "wrong-password"},
        format="json",
        HTTP_USER_AGENT="pytest-client",
    )

    assert success_response.status_code == 200
    assert failure_response.status_code == 401
    assert LoginHistory.objects.filter(user=owner, status=LoginStatus.SUCCESS).exists()
    assert LoginHistory.objects.filter(
        identifier=owner.email,
        status=LoginStatus.FAILED,
    ).exists()
    assert FailedLoginAttempt.objects.filter(identifier=owner.email).exists()
    assert AccountSession.objects.filter(user=owner, is_active=True).exists()
    assert AuditLog.objects.filter(actor=owner, action=AuditAction.LOGIN).exists()
    assert AuditLog.objects.filter(action=AuditAction.SECURITY).exists()


@pytest.mark.django_db
def test_logout_all_sessions_marks_sessions_inactive(owner):
    AccountSession.objects.create(user=owner, token_jti="first")
    AccountSession.objects.create(user=owner, token_jti="second")
    client = APIClient()
    client.force_authenticate(user=owner)

    response = client.post("/api/accounts/sessions/logout-all/")

    assert response.status_code == 200
    assert response.data["logged_out_sessions"] == 2
    assert not AccountSession.objects.filter(user=owner, is_active=True).exists()
    assert AuditLog.objects.filter(actor=owner, action=AuditAction.LOGOUT).exists()


@pytest.mark.django_db
def test_security_audit_api_endpoints(owner):
    AccountSession.objects.create(user=owner, token_jti="first")
    LoginHistory.objects.create(
        user=owner,
        identifier=owner.email,
        status=LoginStatus.SUCCESS,
    )
    AuditLog.objects.create(
        actor=owner,
        action=AuditAction.ADMIN,
        entity_type="accounts.User",
        object_repr=owner.email,
        summary="Admin action",
    )

    client = APIClient()
    client.force_authenticate(user=owner)

    login_history_response = client.get("/api/accounts/login-history/")
    sessions_response = client.get("/api/accounts/sessions/")
    audit_logs_response = client.get("/api/accounts/audit-logs/")

    assert login_history_response.status_code == 200
    assert sessions_response.status_code == 200
    assert audit_logs_response.status_code == 200
    assert login_history_response.data["count"] >= 1
    assert sessions_response.data["count"] >= 1
    assert audit_logs_response.data["count"] >= 1


@pytest.mark.django_db
def test_retail_services_create_security_audit_logs(owner):
    store = Store.objects.create(name="Index Store", owner=owner)
    branch = Branch.objects.create(store=store, name="Main Branch", manager=owner)
    warehouse = branch.warehouses.create(name="Main Warehouse")
    CashBox.objects.create(branch=branch, name="Main Cashbox")
    category = Category.objects.create(name="Security Test Category")
    unit = Unit.objects.create(name="piece", short_name="pcs")
    product = Product.objects.create(
        category=category,
        name="Audit Product",
        sku="AUDIT-001",
        cost_price=Decimal("1000.00"),
        selling_price=Decimal("1500.00"),
        unit=unit,
        created_by=owner,
    )
    customer = Customer.objects.create(full_name="Audit Customer")
    supplier = Supplier.objects.create(company_name="Audit Supplier")

    StockService.increase_stock(
        warehouse=warehouse,
        product=product,
        quantity=Decimal("10.000"),
        created_by=owner,
    )
    sale = create_sale(
        branch=branch,
        warehouse=warehouse,
        cashier=owner,
        customer=customer,
        items=[
            {
                "product": product,
                "quantity": Decimal("1.000"),
                "price": Decimal("1500.00"),
                "discount": Decimal("0.00"),
            }
        ],
        payments=[
            {
                "payment_method": SalePaymentMethod.CASH,
                "amount": Decimal("1500.00"),
            }
        ],
    )
    complete_sale(sale, completed_by=owner)
    refund_sale(sale, cashier=owner, reason="Audit refund")

    purchase = Purchase.objects.create(
        supplier=supplier,
        warehouse=warehouse,
        invoice_number="AUDIT-PURCHASE-1",
        created_by=owner,
    )
    PurchaseItem.objects.create(
        purchase=purchase,
        product=product,
        quantity=Decimal("1.000"),
        purchase_price=Decimal("1000.00"),
    )
    recalculate_purchase_totals(purchase)
    confirm_purchase(purchase, confirmed_by=owner)

    assert AuditLog.objects.filter(action=AuditAction.STOCK).exists()
    assert AuditLog.objects.filter(action=AuditAction.SALE).exists()
    assert AuditLog.objects.filter(action=AuditAction.REFUND).exists()
    assert AuditLog.objects.filter(action=AuditAction.PURCHASE).exists()
    assert AuditLog.objects.filter(action=AuditAction.FINANCE).exists()
