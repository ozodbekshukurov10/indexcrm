from django.contrib import admin, messages
from django.core.exceptions import ValidationError

from apps.sales.models import (
    Customer,
    CustomerPayment,
    LoyaltyAccount,
    Refund,
    RefundItem,
    Sale,
    SaleItem,
    SalePayment,
    SaleStatus,
)
from apps.sales.services import cancel_sale, complete_sale, recalculate_sale_totals


class CustomerPaymentInline(admin.TabularInline):
    model = CustomerPayment
    extra = 0
    readonly_fields = ("created_at", "updated_at")


class LoyaltyAccountInline(admin.StackedInline):
    model = LoyaltyAccount
    extra = 0
    readonly_fields = ("points", "total_spent", "created_at", "updated_at")


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = (
        "full_name",
        "phone",
        "balance",
        "bonus_balance",
        "is_active",
        "created_at",
    )
    list_filter = ("is_active", "created_at")
    search_fields = ("full_name", "phone", "extra_phone", "address", "notes")
    readonly_fields = (
        "id",
        "balance",
        "bonus_balance",
        "created_at",
        "updated_at",
        "deleted_at",
    )
    inlines = (CustomerPaymentInline, LoyaltyAccountInline)


@admin.register(CustomerPayment)
class CustomerPaymentAdmin(admin.ModelAdmin):
    list_display = (
        "customer",
        "cashbox",
        "amount",
        "payment_method",
        "paid_at",
        "created_by",
    )
    list_filter = ("payment_method", "cashbox", "paid_at", "created_at")
    search_fields = (
        "customer__full_name",
        "customer__phone",
        "cashbox__name",
        "note",
        "created_by__email",
    )
    readonly_fields = ("id", "created_at", "updated_at", "deleted_at")


class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 1
    readonly_fields = ("total_price", "created_at", "updated_at")


class SalePaymentInline(admin.TabularInline):
    model = SalePayment
    extra = 0
    readonly_fields = ("created_at", "updated_at")


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = (
        "receipt_number",
        "branch",
        "cashier",
        "customer",
        "status",
        "total_amount",
        "paid_amount",
        "remaining_amount",
        "sale_date",
    )
    list_filter = ("status", "branch", "cashier", "sale_date", "created_at")
    search_fields = (
        "receipt_number",
        "customer__full_name",
        "customer__phone",
        "cashier__email",
        "items__product__name",
        "items__product__sku",
    )
    readonly_fields = (
        "id",
        "receipt_number",
        "status",
        "subtotal",
        "total_amount",
        "paid_amount",
        "remaining_amount",
        "created_at",
        "updated_at",
        "deleted_at",
    )
    inlines = (SaleItemInline, SalePaymentInline)
    actions = ("complete_selected_sales", "cancel_selected_sales")

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = list(super().get_readonly_fields(request, obj))
        if obj and obj.status != SaleStatus.DRAFT:
            readonly_fields.extend(
                [
                    "branch",
                    "warehouse",
                    "cashier",
                    "customer",
                    "sale_date",
                    "discount_amount",
                    "tax_amount",
                    "note",
                ]
            )
        return readonly_fields

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        if form.instance.status == SaleStatus.DRAFT:
            recalculate_sale_totals(form.instance)

    @admin.action(description="Complete selected sales")
    def complete_selected_sales(self, request, queryset):
        completed_count = 0
        for sale in queryset:
            try:
                complete_sale(sale, completed_by=request.user)
                completed_count += 1
            except ValidationError as error:
                self.message_user(request, f"{sale}: {error}", level=messages.ERROR)
        self.message_user(request, f"Completed sales: {completed_count}")

    @admin.action(description="Cancel selected draft sales")
    def cancel_selected_sales(self, request, queryset):
        cancelled_count = 0
        for sale in queryset:
            try:
                cancel_sale(sale)
                cancelled_count += 1
            except ValidationError as error:
                self.message_user(request, f"{sale}: {error}", level=messages.ERROR)
        self.message_user(request, f"Cancelled sales: {cancelled_count}")


@admin.register(SaleItem)
class SaleItemAdmin(admin.ModelAdmin):
    list_display = ("sale", "product", "quantity", "price", "discount", "total_price")
    list_filter = ("created_at",)
    search_fields = (
        "sale__receipt_number",
        "product__name",
        "product__sku",
        "product__barcode",
    )
    readonly_fields = ("id", "total_price", "created_at", "updated_at", "deleted_at")


@admin.register(SalePayment)
class SalePaymentAdmin(admin.ModelAdmin):
    list_display = ("sale", "payment_method", "amount", "paid_at")
    list_filter = ("payment_method", "paid_at", "created_at")
    search_fields = ("sale__receipt_number", "sale__customer__full_name", "note")
    readonly_fields = ("id", "created_at", "updated_at", "deleted_at")


class RefundItemInline(admin.TabularInline):
    model = RefundItem
    extra = 0
    readonly_fields = ("created_at", "updated_at")


@admin.register(Refund)
class RefundAdmin(admin.ModelAdmin):
    list_display = ("original_sale", "cashier", "total_amount", "refund_date")
    list_filter = ("cashier", "refund_date", "created_at")
    search_fields = (
        "original_sale__receipt_number",
        "cashier__email",
        "reason",
        "items__product__name",
    )
    readonly_fields = ("id", "total_amount", "created_at", "updated_at", "deleted_at")
    inlines = (RefundItemInline,)


@admin.register(RefundItem)
class RefundItemAdmin(admin.ModelAdmin):
    list_display = ("refund", "product", "quantity", "amount")
    list_filter = ("created_at",)
    search_fields = (
        "refund__original_sale__receipt_number",
        "product__name",
        "product__sku",
    )
    readonly_fields = ("id", "created_at", "updated_at", "deleted_at")
