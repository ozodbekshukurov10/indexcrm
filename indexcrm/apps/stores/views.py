from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.viewsets import ModelViewSet

from apps.accounts.permissions import (
    IsReadOnlyOrOwnerAdmin,
    IsReadOnlyOrOwnerAdminManager,
    filter_queryset_by_branch_scope,
    filter_queryset_by_store_scope,
)
from apps.common.scoping import require_branch_access, require_store_access
from apps.stores.models import Branch, CashDesk, Store
from apps.stores.serializers import (
    BranchSerializer,
    CashDeskSerializer,
    StoreSerializer,
)


def _bool_param(value):
    if value is None:
        return None
    return str(value).lower() in {"1", "true", "yes", "on"}


@extend_schema_view(
    list=extend_schema(
        summary="List stores",
        parameters=[
            OpenApiParameter("is_active", bool, description="Filter by active status."),
            OpenApiParameter("owner", str, description="Filter by owner user UUID."),
        ],
    ),
    create=extend_schema(summary="Create store"),
    retrieve=extend_schema(summary="Retrieve store"),
    update=extend_schema(summary="Update store"),
    partial_update=extend_schema(summary="Partially update store"),
    destroy=extend_schema(summary="Soft delete store"),
)
class StoreViewSet(ModelViewSet):
    serializer_class = StoreSerializer
    permission_classes = (IsReadOnlyOrOwnerAdmin,)
    parser_classes = (JSONParser, MultiPartParser, FormParser)
    filter_backends = (SearchFilter, OrderingFilter)
    search_fields = ("name", "phone", "address", "owner__email")
    ordering_fields = ("name", "created_at", "updated_at")
    ordering = ("-created_at",)

    def get_queryset(self):
        queryset = Store.objects.select_related("owner")
        is_active = _bool_param(self.request.query_params.get("is_active"))
        owner = self.request.query_params.get("owner")

        if is_active is not None:
            queryset = queryset.filter(is_active=is_active)
        if owner:
            queryset = queryset.filter(owner_id=owner)

        return filter_queryset_by_store_scope(queryset, self.request.user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


@extend_schema_view(
    list=extend_schema(
        summary="List branches",
        parameters=[
            OpenApiParameter("store", str, description="Filter by store UUID."),
            OpenApiParameter(
                "manager", str, description="Filter by manager user UUID."
            ),
            OpenApiParameter("is_active", bool, description="Filter by active status."),
        ],
    ),
    create=extend_schema(summary="Create branch"),
    retrieve=extend_schema(summary="Retrieve branch"),
    update=extend_schema(summary="Update branch"),
    partial_update=extend_schema(summary="Partially update branch"),
    destroy=extend_schema(summary="Soft delete branch"),
)
class BranchViewSet(ModelViewSet):
    serializer_class = BranchSerializer
    permission_classes = (IsReadOnlyOrOwnerAdminManager,)
    filter_backends = (SearchFilter, OrderingFilter)
    search_fields = ("name", "phone", "address", "store__name", "manager__email")
    ordering_fields = ("name", "created_at", "updated_at")
    ordering = ("-created_at",)

    def get_queryset(self):
        queryset = Branch.objects.select_related("store", "manager")
        store = self.request.query_params.get("store")
        manager = self.request.query_params.get("manager")
        is_active = _bool_param(self.request.query_params.get("is_active"))

        if store:
            queryset = queryset.filter(store_id=store)
        if manager:
            queryset = queryset.filter(manager_id=manager)
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active)

        return filter_queryset_by_branch_scope(queryset, self.request.user, "id")

    def perform_create(self, serializer):
        require_store_access(self.request.user, serializer.validated_data["store"])
        serializer.save()

    def perform_update(self, serializer):
        require_branch_access(self.request.user, serializer.instance)
        if "store" in serializer.validated_data:
            require_store_access(self.request.user, serializer.validated_data["store"])
        serializer.save()


@extend_schema_view(
    list=extend_schema(
        summary="List cash desks",
        parameters=[
            OpenApiParameter("branch", str, description="Filter by branch UUID."),
            OpenApiParameter("is_active", bool, description="Filter by active status."),
        ],
    ),
    create=extend_schema(summary="Create cash desk"),
    retrieve=extend_schema(summary="Retrieve cash desk"),
    update=extend_schema(summary="Update cash desk"),
    partial_update=extend_schema(summary="Partially update cash desk"),
    destroy=extend_schema(summary="Soft delete cash desk"),
)
class CashDeskViewSet(ModelViewSet):
    serializer_class = CashDeskSerializer
    permission_classes = (IsReadOnlyOrOwnerAdminManager,)
    filter_backends = (SearchFilter, OrderingFilter)
    search_fields = ("name", "code", "branch__name", "branch__store__name")
    ordering_fields = ("name", "code", "created_at", "updated_at")
    ordering = ("-created_at",)

    def get_queryset(self):
        queryset = CashDesk.objects.select_related("branch", "branch__store")
        branch = self.request.query_params.get("branch")
        is_active = _bool_param(self.request.query_params.get("is_active"))

        if branch:
            queryset = queryset.filter(branch_id=branch)
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active)

        return filter_queryset_by_branch_scope(queryset, self.request.user, "branch_id")

    def perform_create(self, serializer):
        require_branch_access(self.request.user, serializer.validated_data["branch"])
        serializer.save()

    def perform_update(self, serializer):
        branch = serializer.validated_data.get("branch", serializer.instance.branch)
        require_branch_access(self.request.user, branch)
        serializer.save()
