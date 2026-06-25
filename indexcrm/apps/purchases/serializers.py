from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from drf_spectacular.utils import OpenApiExample, extend_schema_serializer
from rest_framework import serializers

from apps.purchases.models import (
    Purchase,
    PurchaseItem,
    PurchasePayment,
    PurchaseStatus,
    Supplier,
    SupplierContact,
    SupplierPayment,
)
from apps.purchases.services import (
    create_purchase_item,
    create_purchase_payment,
    create_supplier_payment,
    recalculate_purchase_totals,
    update_purchase_item,
)


def raise_serializer_validation(error):
    if hasattr(error, "message_dict"):
        raise serializers.ValidationError(error.message_dict) from error
    raise serializers.ValidationError(error.messages) from error


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            "Supplier request",
            value={
                "company_name": "Index Wholesale",
                "full_name": "Aziz Karimov",
                "phone": "+998901234567",
                "email": "supplier@example.com",
                "inn_or_tax_number": "123456789",
                "is_active": True,
            },
            request_only=True,
        ),
        OpenApiExample(
            "Supplier response",
            value={
                "id": "c59fc8c2-0329-41d3-93bb-73eeab914ac2",
                "company_name": "Index Wholesale",
                "full_name": "Aziz Karimov",
                "phone": "+998901234567",
                "balance": "0.00",
                "is_active": True,
            },
            response_only=True,
        ),
    ]
)
class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = (
            "id",
            "company_name",
            "full_name",
            "phone",
            "extra_phone",
            "email",
            "address",
            "inn_or_tax_number",
            "notes",
            "balance",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "balance", "created_at", "updated_at")


class SupplierContactSerializer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(
        source="supplier.company_name", read_only=True
    )

    class Meta:
        model = SupplierContact
        fields = (
            "id",
            "supplier",
            "supplier_name",
            "full_name",
            "position",
            "phone",
            "email",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "supplier_name", "created_at", "updated_at")


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            "Supplier payment request",
            value={
                "supplier": "c59fc8c2-0329-41d3-93bb-73eeab914ac2",
                "amount": "100000.00",
                "payment_method": "BANK_TRANSFER",
                "note": "Debt payment",
            },
            request_only=True,
        )
    ]
)
class SupplierPaymentSerializer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(
        source="supplier.company_name", read_only=True
    )
    cashbox_name = serializers.CharField(source="cashbox.name", read_only=True)

    class Meta:
        model = SupplierPayment
        fields = (
            "id",
            "supplier",
            "supplier_name",
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
            "supplier_name",
            "cashbox_name",
            "created_by",
            "created_at",
            "updated_at",
        )

    def create(self, validated_data):
        request = self.context.get("request")
        try:
            return create_supplier_payment(
                created_by=request.user if request else None,
                **validated_data,
            )
        except DjangoValidationError as error:
            raise_serializer_validation(error)

    def update(self, instance, validated_data):
        blocked_fields = {"supplier", "cashbox", "amount", "payment_method", "paid_at"}
        if blocked_fields.intersection(validated_data):
            raise serializers.ValidationError(
                {"payment": "Only the payment note can be updated after creation."}
            )
        return super().update(instance, validated_data)


class PurchaseItemWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = PurchaseItem
        fields = ("product", "quantity", "purchase_price", "expiry_date")


class PurchaseItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    product_sku = serializers.CharField(source="product.sku", read_only=True)

    class Meta:
        model = PurchaseItem
        fields = (
            "id",
            "purchase",
            "product",
            "product_name",
            "product_sku",
            "quantity",
            "purchase_price",
            "total_price",
            "expiry_date",
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
            return create_purchase_item(**validated_data)
        except DjangoValidationError as error:
            raise_serializer_validation(error)

    def update(self, instance, validated_data):
        try:
            return update_purchase_item(instance, **validated_data)
        except DjangoValidationError as error:
            raise_serializer_validation(error)


class PurchasePaymentNestedSerializer(serializers.ModelSerializer):
    class Meta:
        model = PurchasePayment
        fields = ("id", "amount", "payment_method", "note", "paid_at", "created_by")


class PurchaseItemNestedSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    product_sku = serializers.CharField(source="product.sku", read_only=True)

    class Meta:
        model = PurchaseItem
        fields = (
            "id",
            "product",
            "product_name",
            "product_sku",
            "quantity",
            "purchase_price",
            "total_price",
            "expiry_date",
        )


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            "Purchase create request",
            value={
                "supplier": "c59fc8c2-0329-41d3-93bb-73eeab914ac2",
                "warehouse": "b11e0988-9318-476e-a3f5-a728d6b87021",
                "invoice_number": "INV-0001",
                "discount": "5000.00",
                "tax_amount": "0.00",
                "note": "Weekly purchase",
                "items": [
                    {
                        "product": "abdc2d58-3070-48fa-9651-7f8b3b6d3e2a",
                        "quantity": "10.000",
                        "purchase_price": "2500.00",
                        "expiry_date": "2026-12-31",
                    }
                ],
            },
            request_only=True,
        ),
        OpenApiExample(
            "Purchase response",
            value={
                "invoice_number": "INV-0001",
                "status": "DRAFT",
                "subtotal": "25000.00",
                "discount": "5000.00",
                "tax_amount": "0.00",
                "total_amount": "20000.00",
                "paid_amount": "0.00",
                "remaining_amount": "20000.00",
            },
            response_only=True,
        ),
    ]
)
class PurchaseSerializer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(
        source="supplier.company_name", read_only=True
    )
    warehouse_name = serializers.CharField(source="warehouse.name", read_only=True)
    items = PurchaseItemNestedSerializer(many=True, read_only=True)
    payments = PurchasePaymentNestedSerializer(many=True, read_only=True)

    class Meta:
        model = Purchase
        fields = (
            "id",
            "supplier",
            "supplier_name",
            "warehouse",
            "warehouse_name",
            "invoice_number",
            "purchase_date",
            "status",
            "subtotal",
            "discount",
            "tax_amount",
            "total_amount",
            "paid_amount",
            "remaining_amount",
            "note",
            "created_by",
            "confirmed_by",
            "confirmed_at",
            "items",
            "payments",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "supplier_name",
            "warehouse_name",
            "status",
            "subtotal",
            "total_amount",
            "paid_amount",
            "remaining_amount",
            "created_by",
            "confirmed_by",
            "confirmed_at",
            "payments",
            "created_at",
            "updated_at",
        )

    def get_fields(self):
        fields = super().get_fields()
        if self.context.get("request") and self.context["request"].method in {
            "POST",
            "PUT",
            "PATCH",
        }:
            fields["items"] = PurchaseItemWriteSerializer(many=True, required=False)
        return fields

    def validate(self, attrs):
        if self.instance and self.instance.status != PurchaseStatus.DRAFT:
            raise serializers.ValidationError(
                {"status": "Cannot edit purchase after confirmation or cancellation."}
            )
        return attrs

    def create(self, validated_data):
        items_data = validated_data.pop("items", [])

        with transaction.atomic():
            purchase = Purchase.objects.create(**validated_data)
            try:
                for item_data in items_data:
                    create_purchase_item(purchase=purchase, **item_data)
                recalculate_purchase_totals(purchase)
            except DjangoValidationError as error:
                raise_serializer_validation(error)

        return purchase

    def update(self, instance, validated_data):
        items_data = validated_data.pop("items", None)
        with transaction.atomic():
            for field_name, value in validated_data.items():
                setattr(instance, field_name, value)
            try:
                instance.full_clean()
                instance.save()
                if items_data is not None:
                    instance.items.all().delete()
                    for item_data in items_data:
                        create_purchase_item(purchase=instance, **item_data)
                recalculate_purchase_totals(instance)
            except DjangoValidationError as error:
                raise_serializer_validation(error)
        return instance


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            "Purchase payment request",
            value={
                "purchase": "9fa5920a-9792-41c9-acb8-a5d3abe0b044",
                "amount": "10000.00",
                "payment_method": "CASH",
                "note": "Partial payment",
            },
            request_only=True,
        )
    ]
)
class PurchasePaymentSerializer(serializers.ModelSerializer):
    purchase_invoice_number = serializers.CharField(
        source="purchase.invoice_number", read_only=True
    )

    class Meta:
        model = PurchasePayment
        fields = (
            "id",
            "purchase",
            "purchase_invoice_number",
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
            "purchase_invoice_number",
            "created_by",
            "created_at",
            "updated_at",
        )

    def create(self, validated_data):
        request = self.context.get("request")
        try:
            return create_purchase_payment(
                created_by=request.user if request else None,
                **validated_data,
            )
        except DjangoValidationError as error:
            raise_serializer_validation(error)

    def update(self, instance, validated_data):
        blocked_fields = {"purchase", "amount", "payment_method", "paid_at"}
        if blocked_fields.intersection(validated_data):
            raise serializers.ValidationError(
                {"payment": "Only the payment note can be updated after creation."}
            )
        return super().update(instance, validated_data)
