from drf_spectacular.utils import OpenApiExample, extend_schema_serializer
from rest_framework import serializers

from apps.accounts.serializers import UserSerializer
from apps.stores.models import Branch, CashDesk, Store


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            "Store request",
            value={
                "name": "Index Mini Market",
                "phone": "+998901234567",
                "address": "Tashkent, Chilanzar district",
                "is_active": True,
            },
            request_only=True,
        ),
        OpenApiExample(
            "Store response",
            value={
                "id": "6bf7f442-42f6-43b4-873c-7231f18a9510",
                "name": "Index Mini Market",
                "logo": None,
                "phone": "+998901234567",
                "address": "Tashkent, Chilanzar district",
                "is_active": True,
                "owner": "69a59592-3332-422e-9243-412353f3ca59",
                "owner_detail": {"email": "owner@example.com", "role": "owner"},
                "created_at": "2026-05-28T12:00:00Z",
                "updated_at": "2026-05-28T12:00:00Z",
            },
            response_only=True,
        ),
    ]
)
class StoreSerializer(serializers.ModelSerializer):
    owner_detail = UserSerializer(source="owner", read_only=True)

    class Meta:
        model = Store
        fields = (
            "id",
            "name",
            "logo",
            "phone",
            "address",
            "is_active",
            "owner",
            "owner_detail",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "owner", "owner_detail", "created_at", "updated_at")


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            "Branch request",
            value={
                "store": "6bf7f442-42f6-43b4-873c-7231f18a9510",
                "name": "Main Branch",
                "address": "Tashkent, Yunusabad district",
                "phone": "+998901112233",
                "manager": "69a59592-3332-422e-9243-412353f3ca59",
                "is_active": True,
            },
            request_only=True,
        ),
        OpenApiExample(
            "Branch response",
            value={
                "id": "38eb4b8d-d187-4f85-b756-2da19e84d032",
                "store": "6bf7f442-42f6-43b4-873c-7231f18a9510",
                "store_name": "Index Mini Market",
                "name": "Main Branch",
                "address": "Tashkent, Yunusabad district",
                "phone": "+998901112233",
                "manager": "69a59592-3332-422e-9243-412353f3ca59",
                "manager_detail": {"email": "manager@example.com", "role": "manager"},
                "is_active": True,
                "created_at": "2026-05-28T12:00:00Z",
                "updated_at": "2026-05-28T12:00:00Z",
            },
            response_only=True,
        ),
    ]
)
class BranchSerializer(serializers.ModelSerializer):
    store_name = serializers.CharField(source="store.name", read_only=True)
    manager_detail = UserSerializer(source="manager", read_only=True)

    class Meta:
        model = Branch
        fields = (
            "id",
            "store",
            "store_name",
            "name",
            "address",
            "phone",
            "manager",
            "manager_detail",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "store_name",
            "manager_detail",
            "created_at",
            "updated_at",
        )


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            "Cash desk request",
            value={
                "branch": "38eb4b8d-d187-4f85-b756-2da19e84d032",
                "name": "Cash Desk 1",
                "code": "MAIN-01",
                "is_active": True,
            },
            request_only=True,
        ),
        OpenApiExample(
            "Cash desk response",
            value={
                "id": "b156f1be-0b9a-4f49-94f3-248979b0d337",
                "branch": "38eb4b8d-d187-4f85-b756-2da19e84d032",
                "branch_name": "Main Branch",
                "name": "Cash Desk 1",
                "code": "MAIN-01",
                "is_active": True,
                "created_at": "2026-05-28T12:00:00Z",
                "updated_at": "2026-05-28T12:00:00Z",
            },
            response_only=True,
        ),
    ]
)
class CashDeskSerializer(serializers.ModelSerializer):
    branch_name = serializers.CharField(source="branch.name", read_only=True)

    class Meta:
        model = CashDesk
        fields = (
            "id",
            "branch",
            "branch_name",
            "name",
            "code",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "branch_name", "created_at", "updated_at")
