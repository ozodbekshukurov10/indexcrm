from django.contrib import admin

from apps.stores.models import Branch, CashDesk, Store


@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "phone", "is_active", "created_at")
    list_filter = ("is_active", "created_at")
    search_fields = ("name", "phone", "address", "owner__email")
    readonly_fields = ("id", "created_at", "updated_at", "deleted_at")


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ("name", "store", "manager", "phone", "is_active", "created_at")
    list_filter = ("is_active", "store", "created_at")
    search_fields = ("name", "phone", "address", "store__name", "manager__email")
    readonly_fields = ("id", "created_at", "updated_at", "deleted_at")


@admin.register(CashDesk)
class CashDeskAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "branch", "is_active", "created_at")
    list_filter = ("is_active", "branch__store", "created_at")
    search_fields = ("name", "code", "branch__name", "branch__store__name")
    readonly_fields = ("id", "created_at", "updated_at", "deleted_at")
