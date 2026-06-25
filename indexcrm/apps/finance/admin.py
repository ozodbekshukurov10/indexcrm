from django.contrib import admin

from apps.finance.models import (
    CashBox,
    CashTransaction,
    DailyClosing,
    Expense,
    ExpenseCategory,
    Income,
)


class CashTransactionInline(admin.TabularInline):
    model = CashTransaction
    extra = 0
    readonly_fields = (
        "transaction_type",
        "amount",
        "reference_type",
        "reference_id",
        "note",
        "created_by",
        "created_at",
        "updated_at",
    )
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(CashBox)
class CashBoxAdmin(admin.ModelAdmin):
    list_display = ("name", "branch", "current_balance", "is_active", "created_at")
    list_filter = ("is_active", "branch__store", "branch", "created_at")
    search_fields = ("name", "branch__name", "branch__store__name")
    readonly_fields = ("id", "created_at", "updated_at", "deleted_at")
    inlines = (CashTransactionInline,)


@admin.register(CashTransaction)
class CashTransactionAdmin(admin.ModelAdmin):
    list_display = (
        "cashbox",
        "transaction_type",
        "amount",
        "reference_type",
        "created_by",
        "created_at",
    )
    list_filter = (
        "transaction_type",
        "cashbox__branch__store",
        "cashbox__branch",
        "created_at",
    )
    search_fields = (
        "cashbox__name",
        "cashbox__branch__name",
        "reference_type",
        "reference_id",
        "note",
        "created_by__email",
    )
    readonly_fields = (
        "id",
        "cashbox",
        "transaction_type",
        "amount",
        "reference_type",
        "reference_id",
        "created_by",
        "created_at",
        "updated_at",
        "deleted_at",
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ExpenseCategory)
class ExpenseCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "description", "created_at")
    search_fields = ("name", "description")
    readonly_fields = ("id", "created_at", "updated_at", "deleted_at")


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = (
        "category",
        "cashbox",
        "amount",
        "expense_date",
        "created_by",
    )
    list_filter = (
        "category",
        "cashbox__branch__store",
        "cashbox__branch",
        "expense_date",
    )
    search_fields = (
        "category__name",
        "cashbox__name",
        "cashbox__branch__name",
        "note",
        "created_by__email",
    )
    readonly_fields = ("id", "created_at", "updated_at", "deleted_at")


@admin.register(Income)
class IncomeAdmin(admin.ModelAdmin):
    list_display = ("source", "cashbox", "amount", "income_date", "created_by")
    list_filter = ("cashbox__branch__store", "cashbox__branch", "income_date")
    search_fields = (
        "source",
        "cashbox__name",
        "cashbox__branch__name",
        "note",
        "created_by__email",
    )
    readonly_fields = ("id", "created_at", "updated_at", "deleted_at")


@admin.register(DailyClosing)
class DailyClosingAdmin(admin.ModelAdmin):
    list_display = (
        "branch",
        "cashier",
        "total_sales",
        "total_expenses",
        "total_income",
        "expected_cash",
        "actual_cash",
        "difference",
        "closed_at",
    )
    list_filter = ("branch__store", "branch", "cashier", "closed_at")
    search_fields = ("branch__name", "branch__store__name", "cashier__email")
    readonly_fields = (
        "id",
        "branch",
        "cashier",
        "cashier_shift",
        "total_sales",
        "total_expenses",
        "total_income",
        "expected_cash",
        "actual_cash",
        "difference",
        "closed_at",
        "created_at",
        "updated_at",
        "deleted_at",
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
