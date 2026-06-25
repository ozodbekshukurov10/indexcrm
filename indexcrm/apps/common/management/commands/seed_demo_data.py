from collections import Counter
from decimal import Decimal
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User, UserProfile, UserRole
from apps.cashier.models import CashierShift
from apps.catalog.models import Barcode, BarcodeType, Brand, Category, Product, Unit
from apps.finance.models import CashBox, Expense, ExpenseCategory, Income
from apps.finance.services import add_expense, add_income
from apps.inventory.models import Stock, StockMovement, StockMovementType, Warehouse
from apps.purchases.models import PaymentMethod, Purchase, Supplier
from apps.purchases.services import (
    confirm_purchase,
    create_purchase_item,
    create_purchase_payment,
    recalculate_purchase_totals,
)
from apps.sales.models import Customer, Sale, SalePaymentMethod, SaleStatus
from apps.sales.services import complete_sale, create_sale
from apps.stores.models import Branch, CashDesk, Store


DEMO_ADMIN_EMAIL = "admin@example.com"
DEMO_ADMIN_PASSWORD = "Admin12345"
DEMO_CASHIER_EMAIL = "cashier@example.com"
DEMO_CASHIER_PASSWORD = "Cashier12345"
DEMO_MANAGER_EMAIL = "manager@example.com"
DEMO_MANAGER_PASSWORD = "Manager12345"
DEMO_STORE_NAME = "Index Demo Market"
DEMO_LEGACY_STORE_NAME = "Index Demo Mini Market"
DEMO_BRANCH_NAME = "Asosiy filial"
DEMO_LEGACY_BRANCH_NAME = "Main Branch"
DEMO_WAREHOUSE_NAME = "Asosiy ombor"
DEMO_LEGACY_WAREHOUSE_NAME = "Main Warehouse"
DEMO_CASHDESK_CODE = "POS-1"
DEMO_SAMPLE_SALE_KEY = "index-demo-sample-sale-v1"


CATEGORIES = {
    "beverages": "Ichimliklar",
    "snacks": "Shirinliklar",
    "bakery": "Non mahsulotlari",
    "dairy": "Sut mahsulotlari",
    "tea-coffee": "Choy va kofe",
    "oil-sauces": "Yog' va souslar",
    "household": "Maishiy mahsulotlar",
    "canned": "Konserva mahsulotlari",
    "personal-care": "Gigiyena mahsulotlari",
    "grocery": "Don mahsulotlari",
    "kids": "Bolalar mahsulotlari",
    "frozen": "Muzqaymoq va sovuq mahsulotlar",
}

BRANDS = {
    "coca-cola": "Coca-Cola",
    "pepsi": "Pepsi",
    "nestle": "Nestle",
    "local": "Mahalliy",
    "baraka": "Baraka",
    "vodiy": "Vodiy",
    "ahmad": "Ahmad Tea",
    "greenfield": "Greenfield",
    "nescafe": "Nescafe",
    "clean": "Toza Uy",
    "daily": "Har Kun",
    "kids": "Bolajon",
}

UNITS = {
    "pcs": ("dona", "dona"),
    "kg": ("kilogramm", "kg"),
    "l": ("litr", "litr"),
    "box": ("quti", "quti"),
    "pack": ("paket", "paket"),
}

PRODUCTS = [
    ("IDX-COLA-1000", "860000000001", "Coca-Cola 1L", "beverages", "coca-cola", "pcs", "8000.00", "12000.00", "72.000"),
    ("IDX-PEPSI-1000", "860000000002", "Pepsi 1L", "beverages", "pepsi", "pcs", "7800.00", "11500.00", "65.000"),
    ("IDX-FANTA-1000", "860000000003", "Fanta 1L", "beverages", "coca-cola", "pcs", "7800.00", "11500.00", "45.000"),
    ("IDX-WATER-1500", "860000000004", "Nestle suv 1.5L", "beverages", "nestle", "pcs", "2500.00", "4500.00", "100.000"),
    ("IDX-WATER-500", "860000000005", "Gazsiz suv 0.5L", "beverages", "local", "pcs", "1200.00", "2500.00", "130.000"),
    ("IDX-FLASH-045", "860000000006", "Flash Energy 0.45L", "beverages", "local", "pcs", "5500.00", "9000.00", "36.000"),
    ("IDX-JUICE-1000", "860000000007", "Olma sharbati 1L", "beverages", "vodiy", "pcs", "7500.00", "12500.00", "40.000"),
    ("IDX-AYRAN-500", "860000000008", "Ayran 0.5L", "dairy", "vodiy", "pcs", "3500.00", "6000.00", "18.000"),
    ("IDX-SNICKERS", "860000000009", "Snickers shokoladi", "snacks", "baraka", "pcs", "6500.00", "10000.00", "58.000"),
    ("IDX-MARS", "860000000010", "Mars shokoladi", "snacks", "baraka", "pcs", "6200.00", "9500.00", "50.000"),
    ("IDX-TWIX", "860000000011", "Twix shokoladi", "snacks", "baraka", "pcs", "6200.00", "9500.00", "50.000"),
    ("IDX-ALPEN-GOLD", "860000000012", "Alpen Gold shokoladi", "snacks", "baraka", "pcs", "10500.00", "16000.00", "30.000"),
    ("IDX-OREO", "860000000013", "Oreo pechenye", "snacks", "baraka", "pack", "7500.00", "12000.00", "28.000"),
    ("IDX-LAYS", "860000000014", "Lays chips", "snacks", "baraka", "pack", "10500.00", "16000.00", "24.000"),
    ("IDX-KIRIESHKI", "860000000015", "Kirieshki suxari", "snacks", "baraka", "pack", "2800.00", "5000.00", "44.000"),
    ("IDX-SEEDS", "860000000016", "Qovurilgan semechka", "snacks", "local", "pack", "3500.00", "6500.00", "34.000"),
    ("IDX-BREAD-WHT", "860000000017", "Oq non", "bakery", "local", "pcs", "2500.00", "4500.00", "42.000"),
    ("IDX-BATON", "860000000018", "Baton non", "bakery", "local", "pcs", "3000.00", "5500.00", "33.000"),
    ("IDX-LAVASH", "860000000019", "Lavash non paketi", "bakery", "local", "pack", "3500.00", "6500.00", "25.000"),
    ("IDX-SOMSA", "860000000020", "Mini somsa", "bakery", "local", "pcs", "3000.00", "6000.00", "12.000"),
    ("IDX-MILK-1L", "860000000021", "Sut 1L", "dairy", "vodiy", "pcs", "6500.00", "9500.00", "55.000"),
    ("IDX-KEFIR-1L", "860000000022", "Kefir 1L", "dairy", "vodiy", "pcs", "7000.00", "10500.00", "40.000"),
    ("IDX-QATIQ", "860000000023", "Qatiq 400g", "dairy", "vodiy", "pcs", "4500.00", "7500.00", "34.000"),
    ("IDX-YOGURT", "860000000024", "Yogurt 120g", "dairy", "vodiy", "pcs", "3500.00", "6000.00", "48.000"),
    ("IDX-EGGS-10", "860000000025", "Tuxum 10 dona", "dairy", "local", "box", "11500.00", "18000.00", "36.000"),
    ("IDX-BUTTER-200", "860000000026", "Sariyog' 200g", "dairy", "vodiy", "pcs", "15000.00", "23000.00", "22.000"),
    ("IDX-CHEESE-200", "860000000027", "Pishloq 200g", "dairy", "vodiy", "pcs", "14000.00", "22000.00", "16.000"),
    ("IDX-AHMAD-TEA", "860000000028", "Ahmad Tea choyi", "tea-coffee", "ahmad", "box", "17000.00", "26000.00", "26.000"),
    ("IDX-GREENFIELD", "860000000029", "Greenfield choyi", "tea-coffee", "greenfield", "box", "18000.00", "28000.00", "20.000"),
    ("IDX-NESCAFE", "860000000030", "Nescafe Classic", "tea-coffee", "nescafe", "pcs", "21000.00", "33000.00", "14.000"),
    ("IDX-COFFEE-3IN1", "860000000031", "3v1 kofe paketi", "tea-coffee", "nescafe", "pack", "1200.00", "2500.00", "90.000"),
    ("IDX-SUGAR-1KG", "860000000032", "Shakar 1kg", "grocery", "baraka", "kg", "9000.00", "13500.00", "70.000"),
    ("IDX-SALT-1KG", "860000000033", "Tuz 1kg", "grocery", "baraka", "kg", "2500.00", "4500.00", "60.000"),
    ("IDX-RICE-1KG", "860000000034", "Guruch 1kg", "grocery", "baraka", "kg", "13000.00", "19000.00", "64.000"),
    ("IDX-PASTA-400", "860000000035", "Makaron 400g", "grocery", "baraka", "pack", "5500.00", "9500.00", "52.000"),
    ("IDX-GRECHKA-1KG", "860000000036", "Grechka 1kg", "grocery", "baraka", "kg", "11000.00", "17000.00", "38.000"),
    ("IDX-FLOUR-1KG", "860000000037", "Un 1kg", "grocery", "baraka", "kg", "7500.00", "11500.00", "68.000"),
    ("IDX-MOSH-1KG", "860000000038", "Mosh 1kg", "grocery", "baraka", "kg", "14000.00", "21000.00", "20.000"),
    ("IDX-OIL-1L", "860000000039", "Kungaboqar yog'i 1L", "oil-sauces", "baraka", "l", "14500.00", "22000.00", "45.000"),
    ("IDX-KETCHUP", "860000000040", "Ketchup", "oil-sauces", "baraka", "pcs", "8000.00", "13000.00", "25.000"),
    ("IDX-MAYO", "860000000041", "Mayonez", "oil-sauces", "baraka", "pcs", "8500.00", "13500.00", "24.000"),
    ("IDX-SOY-SAUCE", "860000000042", "Soya sousi", "oil-sauces", "baraka", "pcs", "9500.00", "15000.00", "8.000"),
    ("IDX-TUNA", "860000000043", "Tuna konservasi", "canned", "baraka", "pcs", "15000.00", "24000.00", "18.000"),
    ("IDX-COND-MILK", "860000000044", "Quyultirilgan sut", "canned", "vodiy", "pcs", "9500.00", "15000.00", "22.000"),
    ("IDX-PEAS", "860000000045", "Yashil no'xat konservasi", "canned", "baraka", "pcs", "8500.00", "13500.00", "20.000"),
    ("IDX-CORN", "860000000046", "Makkajo'xori konservasi", "canned", "baraka", "pcs", "9000.00", "14500.00", "17.000"),
    ("IDX-SOAP", "860000000047", "Sovun", "household", "clean", "pcs", "4000.00", "7500.00", "40.000"),
    ("IDX-DETERGENT", "860000000048", "Kir yuvish kukuni 1kg", "household", "clean", "pack", "18000.00", "29000.00", "22.000"),
    ("IDX-DISH-GEL", "860000000049", "Idish yuvish suyuqligi", "household", "clean", "pcs", "9000.00", "15000.00", "26.000"),
    ("IDX-SPONGE", "860000000050", "Idish gubkasi", "household", "clean", "pack", "2500.00", "5000.00", "36.000"),
    ("IDX-NAPKINS", "860000000051", "Salfetka", "household", "clean", "pack", "3500.00", "6500.00", "45.000"),
    ("IDX-TRASH-BAG", "860000000052", "Chiqindi paketi", "household", "clean", "pack", "7000.00", "12000.00", "16.000"),
    ("IDX-SHAMPOO", "860000000053", "Shampun", "personal-care", "daily", "pcs", "16000.00", "26000.00", "18.000"),
    ("IDX-TOOTHPASTE", "860000000054", "Tish pastasi", "personal-care", "daily", "pcs", "8000.00", "13500.00", "28.000"),
    ("IDX-TOOTHBRUSH", "860000000055", "Tish cho'tkasi", "personal-care", "daily", "pcs", "5000.00", "9000.00", "30.000"),
    ("IDX-WET-WIPES", "860000000056", "Nam salfetka", "personal-care", "daily", "pack", "6000.00", "10000.00", "22.000"),
    ("IDX-DIAPER-S", "860000000057", "Bolalar tagligi S", "kids", "kids", "pack", "38000.00", "56000.00", "6.000"),
    ("IDX-BABY-FOOD", "860000000058", "Bolalar pyuresi", "kids", "kids", "pcs", "8500.00", "14000.00", "18.000"),
    ("IDX-BABY-WATER", "860000000059", "Bolalar suvi 0.33L", "kids", "kids", "pcs", "1800.00", "3500.00", "25.000"),
    ("IDX-ICECREAM", "860000000060", "Muzqaymoq plombir", "frozen", "local", "pcs", "3500.00", "7000.00", "14.000"),
    ("IDX-DUMPLINGS", "860000000061", "Chuchvara 500g", "frozen", "local", "pack", "18000.00", "28000.00", "10.000"),
    ("IDX-FROZEN-VEG", "860000000062", "Muzlatilgan sabzavot", "frozen", "local", "pack", "12000.00", "19000.00", "7.000"),
    ("IDX-CHICKEN", "860000000063", "Tovuq filesi 1kg", "frozen", "local", "kg", "32000.00", "44000.00", "5.000"),
    ("IDX-SAUSAGE", "860000000064", "Kolbasa 400g", "frozen", "local", "pcs", "22000.00", "34000.00", "9.000"),
]

LOW_STOCK_SKUS = {"IDX-DIAPER-S", "IDX-FROZEN-VEG", "IDX-CHICKEN", "IDX-SOY-SAUCE"}

SUPPLIERS = [
    ("Toshkent Ichimlik Savdo", "Aziz Rahmonov", "+998901112233", "sales@ichimlik.example", "Toshkent, Sergeli tumani"),
    ("Andijon Non Taminot", "Dilshod Akbarov", "+998932223344", "non@andijon.example", "Andijon, Bobur shoh ko'chasi"),
    ("Vodiy Sut Mahsulotlari", "Madina Karimova", "+998943334455", "sut@vodiy.example", "Farg'ona viloyati"),
    ("Baraka Maishiy Tovarlar", "Jasur Qodirov", "+998954445566", "baraka@tovar.example", "Toshkent, Chilonzor"),
    ("Fayzli Don Ombori", "Zilola Ergasheva", "+998975556677", "don@fayzli.example", "Samarqand viloyati"),
    ("Universal Market Servis", "Bekzod Saidov", "+998996667788", "info@ums.example", "Toshkent, Yunusobod"),
]

CUSTOMERS = [
    ("Ali Valiyev", "+998901010101", "Mahalla 1", "Doimiy demo mijoz", "0.00", "1200.00"),
    ("Dilshod Karimov", "+998902020202", "Mahalla 2", "Doimiy demo mijoz", "35000.00", "500.00"),
    ("Madina Tursunova", "+998903030303", "Mahalla 3", "Doimiy demo mijoz", "0.00", "2200.00"),
    ("Zilola Akramova", "+998904040404", "Mahalla 4", "Doimiy demo mijoz", "0.00", "900.00"),
    ("Jamshid Qodirov", "+998905050505", "Mahalla 5", "Doimiy demo mijoz", "45000.00", "100.00"),
    ("Shahnoza Ergasheva", "+998906060606", "Mahalla 6", "Doimiy demo mijoz", "0.00", "1500.00"),
    ("Bekzod Saidov", "+998907070707", "Mahalla 7", "Doimiy demo mijoz", "0.00", "800.00"),
    ("Gulnoza Xolmatova", "+998908080808", "Mahalla 8", "Doimiy demo mijoz", "12000.00", "300.00"),
    ("Sardor Hakimov", "+998909090909", "Mahalla 9", "Doimiy demo mijoz", "0.00", "700.00"),
    ("Nodira Rasulova", "+998931111111", "Mahalla 10", "Doimiy demo mijoz", "0.00", "1800.00"),
    ("Akmal Toshpulatov", "+998932222222", "Mahalla 11", "Doimiy demo mijoz", "0.00", "400.00"),
    ("Feruza Ortiqova", "+998933333333", "Mahalla 12", "Doimiy demo mijoz", "27000.00", "600.00"),
    ("Sherzod Mamatov", "+998934444444", "Mahalla 13", "Doimiy demo mijoz", "0.00", "1100.00"),
    ("Malika Ismoilova", "+998935555555", "Mahalla 14", "Doimiy demo mijoz", "0.00", "1400.00"),
    ("Otabek Nabiyev", "+998936666666", "Mahalla 15", "Doimiy demo mijoz", "0.00", "1000.00"),
]

PURCHASES = [
    ("UZ-DEMO-001", "Toshkent Ichimlik Savdo", -18, [("IDX-COLA-1000", "24.000"), ("IDX-PEPSI-1000", "24.000"), ("IDX-WATER-1500", "36.000")], "120000.00"),
    ("UZ-DEMO-002", "Andijon Non Taminot", -12, [("IDX-BREAD-WHT", "20.000"), ("IDX-BATON", "16.000"), ("IDX-LAVASH", "12.000")], "80000.00"),
    ("UZ-DEMO-003", "Vodiy Sut Mahsulotlari", -9, [("IDX-MILK-1L", "24.000"), ("IDX-KEFIR-1L", "18.000"), ("IDX-YOGURT", "36.000")], "160000.00"),
    ("UZ-DEMO-004", "Baraka Maishiy Tovarlar", -7, [("IDX-DETERGENT", "10.000"), ("IDX-DISH-GEL", "12.000"), ("IDX-SOAP", "18.000")], "90000.00"),
    ("UZ-DEMO-005", "Fayzli Don Ombori", -5, [("IDX-RICE-1KG", "30.000"), ("IDX-SUGAR-1KG", "30.000"), ("IDX-FLOUR-1KG", "40.000")], "180000.00"),
    ("UZ-DEMO-006", "Universal Market Servis", -3, [("IDX-SNICKERS", "24.000"), ("IDX-OREO", "18.000"), ("IDX-LAYS", "16.000")], "110000.00"),
]

SALE_TEMPLATES = [
    [("IDX-COLA-1000", "1.000"), ("IDX-SNICKERS", "2.000"), ("IDX-BREAD-WHT", "1.000")],
    [("IDX-MILK-1L", "2.000"), ("IDX-EGGS-10", "1.000"), ("IDX-BATON", "1.000")],
    [("IDX-SUGAR-1KG", "1.000"), ("IDX-RICE-1KG", "1.000"), ("IDX-OIL-1L", "1.000")],
    [("IDX-OREO", "2.000"), ("IDX-LAYS", "1.000"), ("IDX-WATER-500", "3.000")],
    [("IDX-AHMAD-TEA", "1.000"), ("IDX-COFFEE-3IN1", "5.000")],
    [("IDX-DETERGENT", "1.000"), ("IDX-DISH-GEL", "1.000"), ("IDX-NAPKINS", "2.000")],
    [("IDX-QATIQ", "2.000"), ("IDX-YOGURT", "4.000"), ("IDX-BUTTER-200", "1.000")],
    [("IDX-KETCHUP", "1.000"), ("IDX-MAYO", "1.000"), ("IDX-PASTA-400", "2.000")],
    [("IDX-SOAP", "3.000"), ("IDX-TOOTHPASTE", "1.000")],
    [("IDX-ICECREAM", "3.000"), ("IDX-FANTA-1000", "1.000")],
]

EXPENSES = [
    ("Ijara to'lovi", "450000.00", -10),
    ("Ish haqi", "650000.00", -7),
    ("Transport xarajati", "120000.00", -5),
    ("Kommunal to'lovlar", "180000.00", -3),
    ("Internet to'lovi", "90000.00", -2),
    ("Reklama xarajati", "75000.00", -1),
]


class Command(BaseCommand):
    help = "Seed/reset local Uzbek demo data for MVP POS and dashboard testing."

    def handle(self, *args, **options):
        environment = str(getattr(settings, "ENVIRONMENT", "local")).lower()
        if environment not in {"local", "development", "dev", "test"}:
            raise CommandError(
                "seed_demo_data is local/demo only. Refusing to run outside a local "
                "environment."
            )

        with transaction.atomic():
            summary = self._seed()

        self.stdout.write(self.style.SUCCESS("Demo data is ready."))
        for label, value in summary.items():
            self.stdout.write(f"{label}: {value}")

    def _seed(self):
        admin = self._reset_user(
            email=DEMO_ADMIN_EMAIL,
            password=DEMO_ADMIN_PASSWORD,
            role=UserRole.OWNER,
            is_staff=True,
            is_superuser=True,
            first_name="Do'kon",
            last_name="egasi",
        )
        cashier = self._reset_user(
            email=DEMO_CASHIER_EMAIL,
            password=DEMO_CASHIER_PASSWORD,
            role=UserRole.CASHIER,
            is_staff=False,
            is_superuser=False,
            first_name="Kassir",
            last_name="",
        )
        manager = self._reset_user(
            email=DEMO_MANAGER_EMAIL,
            password=DEMO_MANAGER_PASSWORD,
            role=UserRole.MANAGER,
            is_staff=True,
            is_superuser=False,
            first_name="Menejer",
            last_name="",
        )

        store = self._upsert_store(admin)
        branch = self._upsert_branch(store, manager)
        warehouse = self._upsert_warehouse(branch)
        cashdesk, _ = CashDesk.objects.update_or_create(
            branch=branch,
            code=DEMO_CASHDESK_CODE,
            defaults={"name": "Kassa 1", "is_active": True},
        )
        cashbox = self._upsert_cashbox(branch)

        self._assign_profile(admin, branch, "DEMO-OWNER", "Do'kon egasi")
        self._assign_profile(cashier, branch, "DEMO-CASHIER", "Kassir")
        self._assign_profile(manager, branch, "DEMO-MANAGER", "Menejer")

        categories = self._seed_categories()
        brands = self._seed_brands()
        units = self._seed_units()
        products = self._seed_products(
            categories=categories,
            brands=brands,
            units=units,
            created_by=admin,
        )
        suppliers = self._seed_suppliers()
        customers = self._seed_customers()

        self._seed_stock(warehouse=warehouse, products=products)
        purchases_created = self._seed_purchases(
            warehouse=warehouse,
            suppliers=suppliers,
            products=products,
            created_by=admin,
        )
        shift = self._ensure_open_shift(cashier=cashier, branch=branch)
        sales_created = self._seed_sales(
            branch=branch,
            warehouse=warehouse,
            cashier=cashier,
            customers=customers,
            products=products,
        )
        finance_records = self._seed_finance(
            cashbox=cashbox,
            created_by=admin,
        )

        return {
            "admin login": f"{DEMO_ADMIN_EMAIL} / {DEMO_ADMIN_PASSWORD}",
            "cashier login": f"{DEMO_CASHIER_EMAIL} / {DEMO_CASHIER_PASSWORD}",
            "manager login": f"{DEMO_MANAGER_EMAIL} / {DEMO_MANAGER_PASSWORD}",
            "store": store.name,
            "branch": f"{branch.name} ({branch.id})",
            "warehouse": f"{warehouse.name} ({warehouse.id})",
            "cashdesk": cashdesk.name,
            "cashbox": cashbox.name,
            "open cashier shift": shift.id,
            "categories": Category.objects.filter(slug__in=CATEGORIES.keys()).count(),
            "products": Product.objects.filter(sku__startswith="IDX-").count(),
            "stock records": Stock.objects.filter(warehouse=warehouse).count(),
            "suppliers": Supplier.objects.filter(
                company_name__in=[item[0] for item in SUPPLIERS]
            ).count(),
            "customers": Customer.objects.filter(
                phone__in=[item[1] for item in CUSTOMERS]
            ).count(),
            "sales": Sale.objects.filter(idempotency_key__startswith="index-demo").count(),
            "new sales this run": sales_created,
            "purchases": Purchase.objects.filter(invoice_number__startswith="UZ-DEMO-").count(),
            "new purchases this run": purchases_created,
            "finance records": finance_records,
        }

    def _reset_user(self, *, email, password, role, is_staff, is_superuser, **extra):
        user, _ = User.objects.update_or_create(
            email=email,
            defaults={
                "role": role,
                "is_staff": is_staff,
                "is_superuser": is_superuser,
                "is_active": True,
                **extra,
            },
        )
        user.set_password(password)
        user.save(update_fields=["password", "updated_at"])
        return user

    def _upsert_store(self, admin):
        store = Store.objects.filter(
            name__in=[DEMO_STORE_NAME, DEMO_LEGACY_STORE_NAME]
        ).first()
        defaults = {
            "name": DEMO_STORE_NAME,
            "owner": admin,
            "phone": "+998 90 000 00 00",
            "address": "Toshkent shahri, demo mini-market",
            "is_active": True,
        }
        if store is None:
            return Store.objects.create(**defaults)
        for field, value in defaults.items():
            setattr(store, field, value)
        store.save()
        return store

    def _upsert_branch(self, store, manager):
        branch = Branch.objects.filter(
            store=store,
            name__in=[DEMO_BRANCH_NAME, DEMO_LEGACY_BRANCH_NAME],
        ).first()
        defaults = {
            "store": store,
            "name": DEMO_BRANCH_NAME,
            "manager": manager,
            "phone": "+998 90 000 00 01",
            "address": "Asosiy filial, Toshkent",
            "is_active": True,
        }
        if branch is None:
            return Branch.objects.create(**defaults)
        for field, value in defaults.items():
            setattr(branch, field, value)
        branch.save()
        return branch

    def _upsert_warehouse(self, branch):
        warehouse = Warehouse.objects.filter(
            branch=branch,
            name__in=[DEMO_WAREHOUSE_NAME, DEMO_LEGACY_WAREHOUSE_NAME],
        ).first()
        defaults = {
            "branch": branch,
            "name": DEMO_WAREHOUSE_NAME,
            "is_active": True,
        }
        if warehouse is None:
            return Warehouse.objects.create(**defaults)
        for field, value in defaults.items():
            setattr(warehouse, field, value)
        warehouse.save()
        return warehouse

    def _upsert_cashbox(self, branch):
        cashbox = CashBox.objects.filter(
            branch=branch,
            name__in=["Asosiy kassa", "Main Cashbox"],
        ).first()
        defaults = {
            "branch": branch,
            "name": "Asosiy kassa",
            "is_active": True,
        }
        if cashbox is None:
            return CashBox.objects.create(**defaults)
        for field, value in defaults.items():
            setattr(cashbox, field, value)
        cashbox.save()
        return cashbox

    def _assign_profile(self, user, branch, employee_code, position):
        UserProfile.objects.update_or_create(
            user=user,
            defaults={
                "branch": branch,
                "employee_code": employee_code,
                "position": position,
                "employee_status": "active",
                "language": "uz",
            },
        )

    def _seed_categories(self):
        categories = {}
        for slug, name in CATEGORIES.items():
            category, _ = Category.objects.update_or_create(
                slug=slug,
                defaults={"name": name, "is_active": True},
            )
            categories[slug] = category
        return categories

    def _seed_brands(self):
        brands = {}
        for key, name in BRANDS.items():
            brand, _ = Brand.objects.update_or_create(
                name=name,
                defaults={"description": "Demo katalog brendi."},
            )
            brands[key] = brand
        return brands

    def _seed_units(self):
        units = {}
        for key, (name, short_name) in UNITS.items():
            unit, _ = Unit.objects.update_or_create(
                short_name=short_name,
                defaults={"name": name},
            )
            units[key] = unit
        return units

    def _seed_products(self, *, categories, brands, units, created_by):
        products = {}
        for (
            sku,
            barcode,
            name,
            category_key,
            brand_key,
            unit_key,
            cost_price,
            selling_price,
            _stock_quantity,
        ) in PRODUCTS:
            product, _ = Product.objects.update_or_create(
                sku=sku,
                defaults={
                    "category": categories[category_key],
                    "brand": brands[brand_key],
                    "name": name,
                    "description": "Uzbek demo mini-market mahsuloti.",
                    "barcode": barcode,
                    "cost_price": Decimal(cost_price),
                    "selling_price": Decimal(selling_price),
                    "min_price": Decimal(cost_price),
                    "unit": units[unit_key],
                    "is_active": True,
                    "created_by": created_by,
                },
            )
            Barcode.objects.update_or_create(
                code=barcode,
                defaults={
                    "product": product,
                    "barcode_type": BarcodeType.EAN13,
                },
            )
            products[sku] = product
        return products

    def _seed_suppliers(self):
        suppliers = {}
        for company_name, full_name, phone, email, address in SUPPLIERS:
            supplier, _ = Supplier.objects.update_or_create(
                company_name=company_name,
                defaults={
                    "full_name": full_name,
                    "phone": phone,
                    "email": email,
                    "address": address,
                    "notes": "Uzbek demo yetkazib beruvchi.",
                    "is_active": True,
                },
            )
            suppliers[company_name] = supplier
        return suppliers

    def _seed_customers(self):
        customers = []
        for full_name, phone, address, notes, balance, bonus_balance in CUSTOMERS:
            customer, _ = Customer.objects.update_or_create(
                phone=phone,
                defaults={
                    "full_name": full_name,
                    "address": address,
                    "notes": notes,
                    "balance": Decimal(balance),
                    "bonus_balance": Decimal(bonus_balance),
                    "is_active": True,
                },
            )
            customers.append(customer)
        return customers

    def _seed_stock(self, *, warehouse, products):
        pending_sale_quantities = self._pending_sale_quantities()
        pending_purchase_quantities = self._pending_purchase_quantities()

        for sku, *_unused, stock_quantity in PRODUCTS:
            target_quantity = Decimal(stock_quantity)
            seed_quantity = target_quantity
            seed_quantity += pending_sale_quantities.get(sku, Decimal("0.000"))
            seed_quantity -= pending_purchase_quantities.get(sku, Decimal("0.000"))
            if seed_quantity < Decimal("0.000"):
                seed_quantity = Decimal("0.000")

            low_limit = Decimal("10.000") if sku in LOW_STOCK_SKUS else Decimal("5.000")
            Stock.objects.update_or_create(
                warehouse=warehouse,
                product=products[sku],
                defaults={
                    "quantity": seed_quantity,
                    "reserved_quantity": Decimal("0.000"),
                    "low_stock_limit": low_limit,
                },
            )

            note = "Demo boshlang'ich qoldiq"
            if not StockMovement.objects.filter(
                warehouse=warehouse,
                product=products[sku],
                note=note,
            ).exists():
                StockMovement.objects.create(
                    warehouse=warehouse,
                    product=products[sku],
                    movement_type=StockMovementType.IN,
                    quantity=max(seed_quantity, Decimal("0.001")),
                    note=note,
                )

    def _pending_sale_quantities(self):
        quantities = Counter()
        for index in range(30):
            key = DEMO_SAMPLE_SALE_KEY if index == 0 else f"index-demo-uz-sale-{index + 1:03d}"
            if Sale.objects.filter(idempotency_key=key).exists():
                continue
            for sku, quantity in SALE_TEMPLATES[index % len(SALE_TEMPLATES)]:
                quantities[sku] += Decimal(quantity)
        return quantities

    def _pending_purchase_quantities(self):
        quantities = Counter()
        for invoice_number, _supplier, _days, items, _paid in PURCHASES:
            if Purchase.objects.filter(invoice_number=invoice_number).exists():
                continue
            for sku, quantity in items:
                quantities[sku] += Decimal(quantity)
        return quantities

    def _seed_purchases(self, *, warehouse, suppliers, products, created_by):
        created_count = 0
        now = timezone.now()
        for invoice_number, supplier_name, days_offset, items, paid_amount in PURCHASES:
            if Purchase.objects.filter(invoice_number=invoice_number).exists():
                continue

            purchase = Purchase.objects.create(
                supplier=suppliers[supplier_name],
                warehouse=warehouse,
                invoice_number=invoice_number,
                purchase_date=now + timedelta(days=days_offset),
                note="Demo kirim: Uzbek mini-market tovarlari.",
                created_by=created_by,
            )
            for sku, quantity in items:
                product = products[sku]
                create_purchase_item(
                    purchase=purchase,
                    product=product,
                    quantity=Decimal(quantity),
                    purchase_price=product.cost_price,
                )
            recalculate_purchase_totals(purchase)
            pay_amount = min(Decimal(paid_amount), purchase.total_amount)
            if pay_amount > Decimal("0.00"):
                create_purchase_payment(
                    purchase=purchase,
                    amount=pay_amount,
                    payment_method=PaymentMethod.CASH,
                    note="Demo kirim to'lovi",
                    paid_at=purchase.purchase_date,
                    created_by=created_by,
                )
            confirm_purchase(purchase, confirmed_by=created_by)
            created_count += 1
        return created_count

    def _ensure_open_shift(self, *, cashier, branch):
        shift = CashierShift.objects.filter(
            cashier=cashier,
            branch=branch,
            closed_at__isnull=True,
        ).first()
        if shift:
            shift.opening_balance = Decimal("150000.00")
            shift.expected_balance = max(shift.expected_balance, Decimal("150000.00"))
            shift.save(update_fields=["opening_balance", "expected_balance", "updated_at"])
            return shift

        return CashierShift.objects.create(
            cashier=cashier,
            branch=branch,
            opened_at=timezone.now(),
            opening_balance=Decimal("150000.00"),
            expected_balance=Decimal("150000.00"),
        )

    def _seed_sales(self, *, branch, warehouse, cashier, customers, products):
        created_count = 0
        now = timezone.now()
        for index in range(30):
            idempotency_key = (
                DEMO_SAMPLE_SALE_KEY
                if index == 0
                else f"index-demo-uz-sale-{index + 1:03d}"
            )
            if Sale.objects.filter(idempotency_key=idempotency_key).exists():
                continue

            items = []
            total = Decimal("0.00")
            for sku, quantity_value in SALE_TEMPLATES[index % len(SALE_TEMPLATES)]:
                product = products[sku]
                quantity = Decimal(quantity_value)
                line_total = (product.selling_price * quantity).quantize(Decimal("0.01"))
                total += line_total
                items.append(
                    {
                        "product": product,
                        "quantity": quantity,
                        "price": product.selling_price,
                        "discount": Decimal("0.00"),
                    }
                )

            if index % 5 == 0:
                payments = [
                    {
                        "payment_method": SalePaymentMethod.CASH,
                        "amount": (total * Decimal("0.60")).quantize(Decimal("0.01")),
                        "note": "Naqd qism",
                    },
                    {
                        "payment_method": SalePaymentMethod.CARD,
                        "amount": (
                            total - (total * Decimal("0.60")).quantize(Decimal("0.01"))
                        ).quantize(Decimal("0.01")),
                        "note": "Karta qism",
                    },
                ]
            else:
                payment_method = (
                    SalePaymentMethod.CARD if index % 4 == 0 else SalePaymentMethod.CASH
                )
                payments = [
                    {
                        "payment_method": payment_method,
                        "amount": total.quantize(Decimal("0.01")),
                        "note": "Demo to'lov",
                    }
                ]

            sale = create_sale(
                branch=branch,
                warehouse=warehouse,
                cashier=cashier,
                customer=customers[index % len(customers)] if index % 3 == 0 else None,
                idempotency_key=idempotency_key,
                note="Uzbek demo savdo",
                items=items,
                payments=payments,
            )
            if sale.status != SaleStatus.COMPLETED:
                complete_sale(sale, completed_by=cashier)
            sale_date = now - timedelta(days=index % 18, hours=index % 7)
            sale.sale_date = sale_date
            sale.note = "Uzbek demo savdo"
            sale.save(update_fields=["sale_date", "note", "updated_at"])
            created_count += 1
        return created_count

    def _seed_finance(self, *, cashbox, created_by):
        now = timezone.now()
        records = 0
        income_note = "Demo boshlang'ich pul qo'yildi"
        if not Income.objects.filter(cashbox=cashbox, note=income_note).exists():
            add_income(
                cashbox=cashbox,
                amount=Decimal("1500000.00"),
                source="Boshlang'ich kassa",
                note=income_note,
                income_date=now - timedelta(days=20),
                created_by=created_by,
            )
            records += 1

        for name, amount, days_offset in EXPENSES:
            category, _ = ExpenseCategory.objects.update_or_create(
                name=name,
                defaults={"description": "Uzbek demo xarajat kategoriyasi."},
            )
            note = f"Demo xarajat: {name}"
            if Expense.objects.filter(cashbox=cashbox, category=category, note=note).exists():
                continue
            add_expense(
                cashbox=cashbox,
                category=category,
                amount=Decimal(amount),
                note=note,
                expense_date=now + timedelta(days=days_offset),
                created_by=created_by,
            )
            records += 1
        return records
