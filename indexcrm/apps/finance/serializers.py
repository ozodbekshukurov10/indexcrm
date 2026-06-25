from django.core.exceptions import ValidationError as DjangoValidationError
from drf_spectacular.utils import OpenApiExample, extend_schema_serializer
from rest_framework import serializers

from apps.finance.models import (
    CashBox,
    CashTransaction,
    CashTransactionType,
    DailyClosing,
    Expense,
    ExpenseCategory,
    Income,
)
from apps.finance.services import (
    add_expense,
    add_income,
    close_daily_shift,
    record_cash_transaction,
    transfer_between_cashboxes,
)


def raise_serializer_validation(error):
    if hasattr(error, "message_dict"):
        raise serializers.ValidationError(error.message_dict) from error
    raise serializers.ValidationError(error.messages) from error


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            "Cashbox request",
            value={
                "branch": "38eb4b8d-d187-4f85-b756-2da19e84d032",
                "name": "Main Cashbox",
                "current_balance": "0.00",
                "is_active": True,
            },
            request_only=True,
        )
    ]
)
class CashBoxSerializer(serializers.ModelSerializer):
    branch_name = serializers.CharField(source="branch.name", read_only=True)

    class Meta:
        model = CashBox
        fields = (
            "id",
            "branch",
            "branch_name",
            "name",
            "current_balance",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "branch_name", "created_at", "updated_at")


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            "Cash adjustment request",
            value={
                "cashbox": "9c9cb59c-c273-45d8-a7dd-2f30986ab59f",
                "transaction_type": "ADJUSTMENT",
                "amount": "50000.00",
                "note": "Opening balance correction",
            },
            request_only=True,
        ),
        OpenApiExample(
            "Sale transaction response",
            value={
                "transaction_type": "SALE",
                "amount": "125000.00",
                "reference_type": "sale",
                "note": "Sale R-20260528120000-ABC123",
            },
            response_only=True,
        ),
    ]
)
class CashTransactionSerializer(serializers.ModelSerializer):
    cashbox_name = serializers.CharField(source="cashbox.name", read_only=True)
    branch_name = serializers.CharField(source="cashbox.branch.name", read_only=True)
    created_by_email = serializers.CharField(source="created_by.email", read_only=True)

    class Meta:
        model = CashTransaction
        fields = (
            "id",
            "cashbox",
            "cashbox_name",
            "branch_name",
            "transaction_type",
            "amount",
            "reference_type",
            "reference_id",
            "note",
            "created_by",
            "created_by_email",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "cashbox_name",
            "branch_name",
            "reference_type",
            "reference_id",
            "created_by",
            "created_by_email",
            "created_at",
            "updated_at",
        )

    def validate(self, attrs):
        if (
            self.instance is None
            and attrs.get("transaction_type") != CashTransactionType.ADJUSTMENT
        ):
            raise serializers.ValidationError(
                {
                    "transaction_type": (
                        "Direct cash transaction creation is only allowed for "
                        "ADJUSTMENT. Use income, expense, sale, purchase, or refund "
                        "flows for other transaction types."
                    )
                }
            )
        return attrs

    def create(self, validated_data):
        request = self.context.get("request")
        try:
            return record_cash_transaction(
                created_by=request.user if request else None,
                prevent_negative=True,
                **validated_data,
            )
        except DjangoValidationError as error:
            raise_serializer_validation(error)

    def update(self, instance, validated_data):
        blocked_fields = {"cashbox", "transaction_type", "amount"}
        if blocked_fields.intersection(validated_data):
            raise serializers.ValidationError(
                {"transaction": "Only the transaction note can be updated."}
            )
        return super().update(instance, validated_data)


class CashboxTransferSerializer(serializers.Serializer):
    target_cashbox = serializers.PrimaryKeyRelatedField(queryset=CashBox.objects.all())
    amount = serializers.DecimalField(max_digits=14, decimal_places=2)
    note = serializers.CharField(required=False, allow_blank=True)

    def save(self, **kwargs):
        request = self.context.get("request")
        try:
            return transfer_between_cashboxes(
                source_cashbox=self.context["source_cashbox"],
                target_cashbox=self.validated_data["target_cashbox"],
                amount=self.validated_data["amount"],
                note=self.validated_data.get("note", ""),
                created_by=request.user if request else None,
            )
        except DjangoValidationError as error:
            raise_serializer_validation(error)


class ExpenseCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ExpenseCategory
        fields = ("id", "name", "description", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            "Expense request",
            value={
                "cashbox": "9c9cb59c-c273-45d8-a7dd-2f30986ab59f",
                "category": "ab9b50cc-cf42-42ba-b7c3-24ba91d099e2",
                "amount": "35000.00",
                "note": "Cleaning supplies",
            },
            request_only=True,
        )
    ]
)
class ExpenseSerializer(serializers.ModelSerializer):
    cashbox_name = serializers.CharField(source="cashbox.name", read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)
    created_by_email = serializers.CharField(source="created_by.email", read_only=True)

    class Meta:
        model = Expense
        fields = (
            "id",
            "cashbox",
            "cashbox_name",
            "category",
            "category_name",
            "amount",
            "note",
            "expense_date",
            "created_by",
            "created_by_email",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "cashbox_name",
            "category_name",
            "created_by",
            "created_by_email",
            "created_at",
            "updated_at",
        )

    def create(self, validated_data):
        request = self.context.get("request")
        try:
            return add_expense(
                created_by=request.user if request else None,
                **validated_data,
            )
        except DjangoValidationError as error:
            raise_serializer_validation(error)

    def update(self, instance, validated_data):
        blocked_fields = {"cashbox", "category", "amount", "expense_date"}
        if blocked_fields.intersection(validated_data):
            raise serializers.ValidationError(
                {"expense": "Only the expense note can be updated after creation."}
            )
        return super().update(instance, validated_data)


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            "Income request",
            value={
                "cashbox": "9c9cb59c-c273-45d8-a7dd-2f30986ab59f",
                "amount": "100000.00",
                "source": "Owner deposit",
                "note": "Initial working cash",
            },
            request_only=True,
        )
    ]
)
class IncomeSerializer(serializers.ModelSerializer):
    cashbox_name = serializers.CharField(source="cashbox.name", read_only=True)
    created_by_email = serializers.CharField(source="created_by.email", read_only=True)

    class Meta:
        model = Income
        fields = (
            "id",
            "cashbox",
            "cashbox_name",
            "amount",
            "source",
            "note",
            "income_date",
            "created_by",
            "created_by_email",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "cashbox_name",
            "created_by",
            "created_by_email",
            "created_at",
            "updated_at",
        )

    def create(self, validated_data):
        request = self.context.get("request")
        try:
            return add_income(
                created_by=request.user if request else None,
                **validated_data,
            )
        except DjangoValidationError as error:
            raise_serializer_validation(error)

    def update(self, instance, validated_data):
        blocked_fields = {"cashbox", "amount", "source", "income_date"}
        if blocked_fields.intersection(validated_data):
            raise serializers.ValidationError(
                {"income": "Only the income note can be updated after creation."}
            )
        return super().update(instance, validated_data)


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            "Daily closing request",
            value={
                "branch": "38eb4b8d-d187-4f85-b756-2da19e84d032",
                "cashier": "b6e04949-7778-4b1c-ad2f-7bc7fd462de2",
                "cashier_shift": "ba8213fd-9a1f-459a-8947-c6d70a977bb3",
                "actual_cash": "504000.00",
            },
            request_only=True,
        )
    ]
)
class DailyClosingSerializer(serializers.ModelSerializer):
    branch_name = serializers.CharField(source="branch.name", read_only=True)
    cashier_email = serializers.CharField(source="cashier.email", read_only=True)

    class Meta:
        model = DailyClosing
        fields = (
            "id",
            "branch",
            "branch_name",
            "cashier",
            "cashier_email",
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
        )
        read_only_fields = (
            "id",
            "branch_name",
            "cashier_email",
            "total_sales",
            "total_expenses",
            "total_income",
            "expected_cash",
            "difference",
            "closed_at",
            "created_at",
            "updated_at",
        )
        extra_kwargs = {"cashier": {"required": False}}

    def validate(self, attrs):
        cashier_shift = attrs.get("cashier_shift")
        if cashier_shift:
            attrs.setdefault("branch", cashier_shift.branch)
            attrs.setdefault("cashier", cashier_shift.cashier)

        request = self.context.get("request")
        if "cashier" not in attrs and request:
            attrs["cashier"] = request.user
        return attrs

    def create(self, validated_data):
        try:
            return close_daily_shift(**validated_data)
        except DjangoValidationError as error:
            raise_serializer_validation(error)
