from django.contrib import admin

from apps.cashier.models import CashierShift


@admin.register(CashierShift)
class CashierShiftAdmin(admin.ModelAdmin):
    list_display = (
        "cashier",
        "branch",
        "opened_at",
        "closed_at",
        "opening_balance",
        "closing_balance",
        "expected_balance",
        "difference",
    )
    list_filter = ("branch", "cashier", "opened_at", "closed_at")
    search_fields = ("cashier__email", "branch__name", "branch__store__name")
    readonly_fields = (
        "id",
        "expected_balance",
        "difference",
        "created_at",
        "updated_at",
        "deleted_at",
    )
