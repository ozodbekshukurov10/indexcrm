from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.catalog.models import Category, Product, Unit
from apps.finance.models import CashBox, ExpenseCategory
from apps.finance.services import add_expense, add_income
from apps.inventory.services import StockService
from apps.purchases.models import Purchase, PurchaseItem, Supplier
from apps.purchases.services import (
    confirm_purchase,
    create_purchase_payment,
    recalculate_purchase_totals,
)
from apps.reports.selectors import (
    best_selling_products,
    customer_debts_report,
    daily_sales_summary,
    inventory_report,
    low_stock_report,
    monthly_sales_summary,
    profit_report,
    supplier_debts_report,
)
from apps.reports.services import (
    dashboard_summary,
    debt_export,
    inventory_export,
    monthly_profit_export,
    monthly_sales_export,
)
from apps.sales.models import Customer, SalePaymentMethod
from apps.sales.services import complete_sale, create_sale
from apps.stores.models import Branch, Store


@pytest.fixture
def reports_context(db):
    user = User.objects.create_user(email="reports@example.com", password="test-pass")
    store = Store.objects.create(name="Index Mini Market", owner=user)
    branch = Branch.objects.create(store=store, name="Main Branch", manager=user)
    warehouse = branch.warehouses.create(name="Main Warehouse")
    cashbox = CashBox.objects.create(branch=branch, name="Main Cashbox")
    category = Category.objects.create(name="Beverages")
    expense_category = ExpenseCategory.objects.create(name="Utilities")
    unit = Unit.objects.create(name="piece", short_name="pcs")
    product = Product.objects.create(
        category=category,
        name="Sparkling Water 1L",
        sku="WATER-1L",
        cost_price=Decimal("2500.00"),
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
        note="Opening stock",
    )
    stock = product.stocks.get(warehouse=warehouse)
    stock.low_stock_limit = Decimal("11.000")
    stock.save(update_fields=("low_stock_limit", "updated_at"))

    add_income(
        cashbox=cashbox,
        amount=Decimal("100000.00"),
        source="Owner deposit",
        created_by=user,
    )
    add_expense(
        cashbox=cashbox,
        category=expense_category,
        amount=Decimal("10000.00"),
        note="Utilities",
        created_by=user,
    )

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

    purchase = Purchase.objects.create(
        supplier=supplier,
        warehouse=warehouse,
        invoice_number="INV-REPORT-0001",
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
    create_purchase_payment(
        purchase=purchase,
        amount=Decimal("1000.00"),
        payment_method="CASH",
        created_by=user,
    )
    return user, branch, warehouse, cashbox, product, customer, supplier


@pytest.mark.django_db
def test_core_report_selectors(reports_context):
    _user, branch, _warehouse, _cashbox, product, _customer, _supplier = reports_context
    today = timezone.localdate()

    daily = daily_sales_summary(day=today, branch=branch.id)
    monthly = monthly_sales_summary(
        year=today.year, month=today.month, branch=branch.id
    )
    profit = profit_report(date_from=today, date_to=today, branch=branch.id)
    inventory = inventory_report(branch=branch.id)
    low_stock = low_stock_report(branch=branch.id)
    best_sellers = best_selling_products(
        date_from=today,
        date_to=today,
        branch=branch.id,
    )

    assert daily["total_sales"] == 1
    assert daily["gross_sales"] == Decimal("8000.00")
    assert monthly["net_sales"] == Decimal("8000.00")
    assert profit["profit"] == Decimal("93000.00")
    assert inventory["product_count"] == 1
    assert low_stock["low_stock_count"] == 1
    assert best_sellers[0]["product"] == product.id


@pytest.mark.django_db
def test_dashboard_summary_includes_stage_six_widgets(reports_context):
    _user, branch, _warehouse, cashbox, _product, customer, supplier = reports_context
    summary = dashboard_summary(day=timezone.localdate(), branch=branch.id)

    customer.refresh_from_db()
    supplier.refresh_from_db()

    assert summary["today_sales"]["total_sales"] == 1
    assert summary["low_stock_count"] == 1
    assert summary["total_debt"]["customer_debt"] == customer.balance
    assert summary["total_debt"]["supplier_debt"] == supplier.balance
    assert summary["cashbox_summary"][0]["cashbox_id"] == str(cashbox.id)
    assert summary["recent_sales"][0]["receipt_number"]


@pytest.mark.django_db
def test_debt_reports_and_excel_exports(reports_context):
    _user, _branch, _warehouse, _cashbox, _product, customer, supplier = reports_context

    customer_debts = customer_debts_report()
    supplier_debts = supplier_debts_report()
    sales_filename, sales_content = monthly_sales_export()
    profit_filename, profit_content = monthly_profit_export()
    inventory_filename, inventory_content = inventory_export()
    debt_filename, debt_content = debt_export()

    assert customer_debts[0]["id"] == customer.id
    assert supplier_debts[0]["id"] == supplier.id
    assert sales_filename.endswith(".xlsx")
    assert profit_filename.endswith(".xlsx")
    assert inventory_filename.endswith(".xlsx")
    assert sales_content.startswith(b"PK")
    assert profit_content.startswith(b"PK")
    assert inventory_content.startswith(b"PK")
    assert debt_filename == "debt-report.xlsx"
    assert debt_content.startswith(b"PK")


@pytest.mark.django_db
def test_reports_api_dashboard_and_export(reports_context):
    user, branch, _warehouse, _cashbox, _product, _customer, _supplier = reports_context
    client = APIClient()
    client.force_authenticate(user=user)

    dashboard_response = client.get(
        "/api/reports/dashboard/",
        {"branch": str(branch.id)},
    )
    export_response = client.get(
        "/api/reports/export/monthly-sales/",
        {"year": timezone.localdate().year, "month": timezone.localdate().month},
    )
    profit_export_response = client.get(
        "/api/reports/export/monthly-profit/",
        {"year": timezone.localdate().year, "month": timezone.localdate().month},
    )
    inventory_export_response = client.get("/api/reports/export/inventory/")
    debt_export_response = client.get("/api/reports/export/debts/")

    assert dashboard_response.status_code == 200
    assert dashboard_response.data["today_sales"]["total_sales"] == 1
    assert export_response.status_code == 200
    assert export_response["Content-Type"] == (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert b"PK" == export_response.content[:2]
    assert profit_export_response.status_code == 200
    assert inventory_export_response.status_code == 200
    assert debt_export_response.status_code == 200
    assert profit_export_response.content[:2] == b"PK"
    assert inventory_export_response.content[:2] == b"PK"
    assert debt_export_response.content[:2] == b"PK"
