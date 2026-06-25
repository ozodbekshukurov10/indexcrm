from django.contrib import admin, messages
from django.core.exceptions import ValidationError

from apps.purchases.models import (
    Purchase,
    PurchaseItem,
    PurchasePayment,
    Supplier,
    SupplierContact,
    SupplierPayment,
)
from apps.purchases.services import (
    cancel_purchase,
    confirm_purchase,
    recalculate_purchase_totals,
)


class SupplierContactInline(admin.TabularInline):
    model = SupplierContact
    extra = 1


class SupplierPaymentInline(admin.TabularInline):
    model = SupplierPayment
    extra = 0
    readonly_fields = ("created_at", "updated_at")


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = (
        "company_name",
        "full_name",
        "phone",
        "balance",
        "is_active",
        "created_at",
    )
    list_filter = ("is_active", "created_at")
    search_fields = (
        "company_name",
        "full_name",
        "phone",
        "extra_phone",
        "email",
        "inn_or_tax_number",
    )
    readonly_fields = ("id", "balance", "created_at", "updated_at", "deleted_at")
    inlines = (SupplierContactInline, SupplierPaymentInline)


@admin.register(SupplierContact)
class SupplierContactAdmin(admin.ModelAdmin):
    list_display = ("full_name", "supplier", "position", "phone", "email")
    list_filter = ("created_at",)
    search_fields = (
        "full_name",
        "position",
        "phone",
        "email",
        "supplier__company_name",
    )
    readonly_fields = ("id", "created_at", "updated_at", "deleted_at")


@admin.register(SupplierPayment)
class SupplierPaymentAdmin(admin.ModelAdmin):
    list_display = (
        "supplier",
        "cashbox",
        "amount",
        "payment_method",
        "paid_at",
        "created_by",
    )
    list_filter = ("payment_method", "cashbox", "paid_at", "created_at")
    search_fields = (
        "supplier__company_name",
        "supplier__full_name",
        "cashbox__name",
        "note",
        "created_by__email",
    )
    readonly_fields = ("id", "created_at", "updated_at", "deleted_at")


class PurchaseItemInline(admin.TabularInline):
    model = PurchaseItem
    extra = 1
    readonly_fields = ("total_price", "created_at", "updated_at")


class PurchasePaymentInline(admin.TabularInline):
    model = PurchasePayment
    extra = 0
    readonly_fields = ("created_at", "updated_at")


@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    list_display = (
        "invoice_number",
        "supplier",
        "warehouse",
        "status",
        "total_amount",
        "paid_amount",
        "remaining_amount",
        "purchase_date",
    )
    list_filter = ("status", "supplier", "warehouse", "purchase_date", "created_at")
    search_fields = (
        "invoice_number",
        "supplier__company_name",
        "supplier__full_name",
        "items__product__name",
        "items__product__sku",
    )
    readonly_fields = (
        "id",
        "status",
        "subtotal",
        "total_amount",
        "paid_amount",
        "remaining_amount",
        "confirmed_by",
        "confirmed_at",
        "created_at",
        "updated_at",
        "deleted_at",
    )
    inlines = (PurchaseItemInline, PurchasePaymentInline)
    actions = ("confirm_selected_purchases", "cancel_selected_purchases")

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        recalculate_purchase_totals(form.instance)

    @admin.action(description="Confirm selected purchases")
    def confirm_selected_purchases(self, request, queryset):
        confirmed_count = 0
        for purchase in queryset:
            try:
                confirm_purchase(purchase, confirmed_by=request.user)
                confirmed_count += 1
            except ValidationError as error:
                self.message_user(request, f"{purchase}: {error}", level=messages.ERROR)
        self.message_user(request, f"Confirmed purchases: {confirmed_count}")

    @admin.action(description="Cancel selected purchases")
    def cancel_selected_purchases(self, request, queryset):
        cancelled_count = 0
        for purchase in queryset:
            try:
                cancel_purchase(purchase, cancelled_by=request.user)
                cancelled_count += 1
            except ValidationError as error:
                self.message_user(request, f"{purchase}: {error}", level=messages.ERROR)
        self.message_user(request, f"Cancelled purchases: {cancelled_count}")


@admin.register(PurchaseItem)
class PurchaseItemAdmin(admin.ModelAdmin):
    list_display = (
        "purchase",
        "product",
        "quantity",
        "purchase_price",
        "total_price",
        "expiry_date",
    )
    list_filter = ("expiry_date", "created_at")
    search_fields = (
        "purchase__invoice_number",
        "product__name",
        "product__sku",
        "product__barcode",
    )
    readonly_fields = ("id", "total_price", "created_at", "updated_at", "deleted_at")


@admin.register(PurchasePayment)
class PurchasePaymentAdmin(admin.ModelAdmin):
    list_display = ("purchase", "amount", "payment_method", "paid_at", "created_by")
    list_filter = ("payment_method", "paid_at", "created_at")
    search_fields = (
        "purchase__invoice_number",
        "purchase__supplier__company_name",
        "note",
        "created_by__email",
    )
    readonly_fields = ("id", "created_at", "updated_at", "deleted_at")
