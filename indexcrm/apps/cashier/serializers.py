from django.core.exceptions import ValidationError as DjangoValidationError
from drf_spectacular.utils import OpenApiExample, extend_schema_serializer
from rest_framework import serializers

from apps.cashier.models import CashierShift
from apps.cashier.services import close_cashier_shift, open_cashier_shift


def raise_serializer_validation(error):
    if hasattr(error, "message_dict"):
        raise serializers.ValidationError(error.message_dict) from error
    raise serializers.ValidationError(error.messages) from error


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            "Open shift request",
            value={
                "branch": "38eb4b8d-d187-4f85-b756-2da19e84d032",
                "opening_balance": "500000.00",
            },
            request_only=True,
        )
    ]
)
class CashierShiftSerializer(serializers.ModelSerializer):
    cashier_email = serializers.CharField(source="cashier.email", read_only=True)
    branch_name = serializers.CharField(source="branch.name", read_only=True)

    class Meta:
        model = CashierShift
        fields = (
            "id",
            "cashier",
            "cashier_email",
            "branch",
            "branch_name",
            "opened_at",
            "closed_at",
            "opening_balance",
            "closing_balance",
            "expected_balance",
            "difference",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "cashier",
            "cashier_email",
            "branch_name",
            "opened_at",
            "closed_at",
            "closing_balance",
            "expected_balance",
            "difference",
            "created_at",
            "updated_at",
        )

    def create(self, validated_data):
        request = self.context.get("request")
        try:
            return open_cashier_shift(
                cashier=request.user if request else None,
                **validated_data,
            )
        except DjangoValidationError as error:
            raise_serializer_validation(error)


class CloseCashierShiftSerializer(serializers.Serializer):
    closing_balance = serializers.DecimalField(max_digits=14, decimal_places=2)

    def save(self, **kwargs):
        shift = self.context["shift"]
        try:
            return close_cashier_shift(
                shift=shift,
                closing_balance=self.validated_data["closing_balance"],
            )
        except DjangoValidationError as error:
            raise_serializer_validation(error)
