from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from drf_spectacular.utils import OpenApiExample, extend_schema_serializer
from rest_framework import serializers

from apps.cashier.services import require_active_cashier_shift
from apps.common.scoping import require_branch_access, require_warehouse_access
from apps.sales.exceptions import (
    SaleErrorCode,
    SaleIdempotencyConflict,
    SaleIdempotencyConflictError,
    SaleValidationError,
    raise_sale_validation,
    sale_validation_error_payload,
)
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
from apps.sales.services import (
    build_sale_idempotency_fingerprint,
    build_receipt_data,
    create_customer_payment,
    create_sale,
    create_sale_item,
    create_sale_payment,
    refund_sale,
    update_sale_item,
)


def raise_serializer_validation(error):
    raise_sale_validation(error)


class LoyaltyAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoyaltyAccount
        fields = ("id", "points", "level", "total_spent", "created_at", "updated_at")
        read_only_fields = fields


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            "Customer request",
            value={
                "full_name": "Ali Valiyev",
                "phone": "+998901234567",
                "address": "Tashkent",
                "is_active": True,
            },
            request_only=True,
        )
    ]
)
class CustomerSerializer(serializers.ModelSerializer):
    loyalty_account = LoyaltyAccountSerializer(read_only=True)

    class Meta:
        model = Customer
        fields = (
            "id",
            "full_name",
            "phone",
            "extra_phone",
            "address",
            "balance",
            "bonus_balance",
            "is_active",
            "notes",
            "loyalty_account",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "balance",
            "bonus_balance",
            "loyalty_account",
            "created_at",
            "updated_at",
        )


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            "Customer payment request",
            value={
                "customer": "d62f79fb-3f2c-4321-af4d-a7d84b5f227f",
                "amount": "50000.00",
                "payment_method": "CASH",
                "note": "Debt payment",
            },
            request_only=True,
        )
    ]
)
class CustomerPaymentSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source="customer.full_name", read_only=True)
    cashbox_name = serializers.CharField(source="cashbox.name", read_only=True)

    class Meta:
        model = CustomerPayment
        fields = (
            "id",
            "customer",
            "customer_name",
            "cashbox",
            "cashbox_name",
            "amount",
            "payment_method",
            "note",
            "paid_at",
            "created_by",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "customer_name",
            "cashbox_name",
            "created_by",
            "created_at",
            "updated_at",
        )

    def create(self, validated_data):
        request = self.context.get("request")
        try:
            return create_customer_payment(
                created_by=request.user if request else None,
                **validated_data,
            )
        except DjangoValidationError as error:
            raise_serializer_validation(error)

    def update(self, instance, validated_data):
        blocked_fields = {"customer", "cashbox", "amount", "payment_method", "paid_at"}
        if blocked_fields.intersection(validated_data):
            raise serializers.ValidationError(
                {"payment": "Only the payment note can be updated after creation."}
            )
        return super().update(instance, validated_data)


class SaleItemWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = SaleItem
        fields = ("product", "quantity", "price", "discount")


class SalePaymentWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = SalePayment
        fields = ("payment_method", "amount", "note", "paid_at")


class SaleItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    product_sku = serializers.CharField(source="product.sku", read_only=True)

    class Meta:
        model = SaleItem
        fields = (
            "id",
            "sale",
            "product",
            "product_name",
            "product_sku",
            "quantity",
            "price",
            "discount",
            "total_price",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "product_name",
            "product_sku",
            "total_price",
            "created_at",
            "updated_at",
        )

    def create(self, validated_data):
        try:
            return create_sale_item(**validated_data)
        except DjangoValidationError as error:
            raise_serializer_validation(error)

    def update(self, instance, validated_data):
        try:
            return update_sale_item(instance, **validated_data)
        except DjangoValidationError as error:
            raise_serializer_validation(error)


class SalePaymentSerializer(serializers.ModelSerializer):
    receipt_number = serializers.CharField(source="sale.receipt_number", read_only=True)

    class Meta:
        model = SalePayment
        fields = (
            "id",
            "sale",
            "receipt_number",
            "payment_method",
            "amount",
            "note",
            "paid_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "receipt_number", "created_at", "updated_at")

    def create(self, validated_data):
        try:
            return create_sale_payment(**validated_data)
        except DjangoValidationError as error:
            raise_serializer_validation(error)

    def update(self, instance, validated_data):
        blocked_fields = {"sale", "payment_method", "amount", "paid_at"}
        if blocked_fields.intersection(validated_data):
            raise serializers.ValidationError(
                {"payment": "Only the payment note can be updated after creation."}
            )
        return super().update(instance, validated_data)


class SaleItemNestedSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    product_sku = serializers.CharField(source="product.sku", read_only=True)

    class Meta:
        model = SaleItem
        fields = (
            "id",
            "product",
            "product_name",
            "product_sku",
            "quantity",
            "price",
            "discount",
            "total_price",
        )


class SalePaymentNestedSerializer(serializers.ModelSerializer):
    class Meta:
        model = SalePayment
        fields = ("id", "payment_method", "amount", "note", "paid_at")


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            "Mixed sale request",
            value={
                "branch": "38eb4b8d-d187-4f85-b756-2da19e84d032",
                "warehouse": "b11e0988-9318-476e-a3f5-a728d6b87021",
                "customer": "d62f79fb-3f2c-4321-af4d-a7d84b5f227f",
                "discount_amount": "0.00",
                "tax_amount": "0.00",
                "items": [
                    {
                        "product": "abdc2d58-3070-48fa-9651-7f8b3b6d3e2a",
                        "quantity": "2.000",
                        "price": "4000.00",
                        "discount": "0.00",
                    }
                ],
                "payments": [
                    {"payment_method": "CASH", "amount": "5000.00"},
                    {"payment_method": "DEBT", "amount": "3000.00"},
                ],
            },
            request_only=True,
        )
    ]
)
class SaleSerializer(serializers.ModelSerializer):
    branch_name = serializers.CharField(source="branch.name", read_only=True)
    warehouse_name = serializers.CharField(source="warehouse.name", read_only=True)
    cashier_email = serializers.CharField(source="cashier.email", read_only=True)
    customer_name = serializers.CharField(source="customer.full_name", read_only=True)
    idempotency_key = serializers.CharField(
        allow_blank=True,
        allow_null=True,
        max_length=128,
        required=False,
    )
    items = SaleItemNestedSerializer(many=True, read_only=True)
    payments = SalePaymentNestedSerializer(many=True, read_only=True)

    class Meta:
        model = Sale
        fields = (
            "id",
            "branch",
            "branch_name",
            "warehouse",
            "warehouse_name",
            "cashier",
            "cashier_email",
            "customer",
            "customer_name",
            "receipt_number",
            "idempotency_key",
            "sale_date",
            "status",
            "subtotal",
            "discount_amount",
            "tax_amount",
            "total_amount",
            "paid_amount",
            "remaining_amount",
            "note",
            "items",
            "payments",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "branch_name",
            "warehouse_name",
            "cashier",
            "cashier_email",
            "receipt_number",
            "sale_date",
            "status",
            "subtotal",
            "total_amount",
            "paid_amount",
            "remaining_amount",
            "created_at",
            "updated_at",
        )
        extra_kwargs = {"idempotency_key": {"validators": []}}
        validators = []

    def get_fields(self):
        fields = super().get_fields()
        request = self.context.get("request")
        if request and request.method in {"POST", "PUT", "PATCH"}:
            fields["items"] = SaleItemWriteSerializer(many=True, required=False)
            fields["payments"] = SalePaymentWriteSerializer(many=True, required=False)
        return fields

    def validate(self, attrs):
        if attrs.get("idempotency_key") == "":
            attrs["idempotency_key"] = None
        if self.instance and self.instance.status != SaleStatus.DRAFT:
            raise serializers.ValidationError(
                {
                    "status": "Cannot edit sale after completion, cancellation, or refund."
                }
            )

        request = self.context.get("request")
        if request and request.method in {"POST", "PUT", "PATCH"}:
            branch = attrs.get("branch", getattr(self.instance, "branch", None))
            warehouse = attrs.get("warehouse", getattr(self.instance, "warehouse", None))
            if branch is not None:
                require_branch_access(request.user, branch)
            if warehouse is not None:
                require_warehouse_access(request.user, warehouse)
            if branch is not None and warehouse is not None and warehouse.branch_id != branch.id:
                raise SaleValidationError(
                    sale_validation_error_payload(
                        DjangoValidationError(
                            {"warehouse": "Warehouse must belong to the selected branch."}
                        ),
                        code=SaleErrorCode.SCOPE_DENIED,
                    )
                )
            if request.method == "POST" and branch is not None:
                idempotency_key = attrs.get("idempotency_key")
                existing_sale = Sale.objects.select_related("branch").filter(
                    idempotency_key=idempotency_key
                ).first() if idempotency_key else None
                if existing_sale:
                    require_branch_access(request.user, existing_sale.branch)
                    if existing_sale.branch_id != branch.id or (
                        warehouse is not None
                        and existing_sale.warehouse_id != warehouse.id
                    ):
                        raise SaleIdempotencyConflict()
                    fingerprint = build_sale_idempotency_fingerprint(
                        sale_data={
                            **attrs,
                            "branch": branch,
                            "warehouse": warehouse,
                            "cashier": request.user,
                        },
                        items=attrs.get("items", []),
                        payments=attrs.get("payments", []),
                    )
                    if (
                        existing_sale.idempotency_fingerprint
                        and existing_sale.idempotency_fingerprint != fingerprint
                    ):
                        raise SaleIdempotencyConflict()
                    return attrs
                try:
                    require_active_cashier_shift(cashier=request.user, branch=branch)
                except DjangoValidationError as error:
                    raise_serializer_validation(error)
        return attrs

    def create(self, validated_data):
        request = self.context.get("request")
        items = validated_data.pop("items", [])
        payments = validated_data.pop("payments", [])
        try:
            return create_sale(
                cashier=request.user if request else None,
                items=items,
                payments=payments,
                **validated_data,
            )
        except SaleIdempotencyConflictError as error:
            raise SaleIdempotencyConflict() from error
        except DjangoValidationError as error:
            raise_serializer_validation(error)

    def update(self, instance, validated_data):
        items = validated_data.pop("items", None)
        payments = validated_data.pop("payments", None)
        with transaction.atomic():
            for field_name, value in validated_data.items():
                setattr(instance, field_name, value)
            try:
                instance.full_clean()
                instance.save()
                if items is not None:
                    instance.items.all().delete()
                    for item_data in items:
                        create_sale_item(sale=instance, **item_data)
                if payments is not None:
                    instance.payments.all().delete()
                    for payment_data in payments:
                        create_sale_payment(sale=instance, **payment_data)
            except DjangoValidationError as error:
                raise_serializer_validation(error)
        return instance


class RefundItemWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = RefundItem
        fields = ("product", "quantity", "amount")
        extra_kwargs = {"amount": {"required": False}}


class RefundItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)

    class Meta:
        model = RefundItem
        fields = ("id", "refund", "product", "product_name", "quantity", "amount")
        read_only_fields = ("id", "product_name")


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            "Refund request",
            value={
                "original_sale": "94094265-3a1d-4813-89e8-1c3595d5f2cc",
                "reason": "Customer returned products",
                "items": [
                    {
                        "product": "abdc2d58-3070-48fa-9651-7f8b3b6d3e2a",
                        "quantity": "1.000",
                    }
                ],
            },
            request_only=True,
        )
    ]
)
class RefundSerializer(serializers.ModelSerializer):
    receipt_number = serializers.CharField(
        source="original_sale.receipt_number", read_only=True
    )
    cashier_email = serializers.CharField(source="cashier.email", read_only=True)
    items = RefundItemSerializer(many=True, read_only=True)

    class Meta:
        model = Refund
        fields = (
            "id",
            "original_sale",
            "receipt_number",
            "cashier",
            "cashier_email",
            "refund_date",
            "reason",
            "total_amount",
            "items",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "cashier",
            "cashier_email",
            "refund_date",
            "total_amount",
            "created_at",
            "updated_at",
        )

    def get_fields(self):
        fields = super().get_fields()
        request = self.context.get("request")
        if request and request.method == "POST":
            fields["items"] = RefundItemWriteSerializer(many=True, required=False)
        return fields

    def create(self, validated_data):
        request = self.context.get("request")
        items = validated_data.pop("items", None)
        try:
            return refund_sale(
                validated_data["original_sale"],
                cashier=request.user if request else None,
                reason=validated_data["reason"],
                items=items,
            )
        except DjangoValidationError as error:
            raise_serializer_validation(error)


class ReceiptSerializer(serializers.Serializer):
    receipt_number = serializers.CharField()
    sale_date = serializers.DateTimeField()
    branch = serializers.DictField()
    warehouse = serializers.DictField()
    cashier = serializers.DictField()
    customer = serializers.DictField(allow_null=True)
    items = serializers.ListField(child=serializers.DictField())
    payments = serializers.ListField(child=serializers.DictField())
    totals = serializers.DictField()
    qr_code = serializers.CharField(allow_null=True)
    fiscal = serializers.DictField()

    @classmethod
    def from_sale(cls, sale):
        return cls(build_receipt_data(sale))
