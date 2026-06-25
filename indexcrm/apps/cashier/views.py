from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK
from rest_framework.viewsets import ModelViewSet

from apps.accounts.models import UserRole
from apps.accounts.permissions import (
    filter_queryset_by_branch_scope,
    user_has_minimum_role,
)
from apps.cashier.models import CashierShift
from apps.cashier.serializers import CashierShiftSerializer, CloseCashierShiftSerializer
from apps.cashier.services import calculate_shift_totals
from apps.common.scoping import require_branch_access


def _bool_param(value):
    if value is None:
        return None
    return str(value).lower() in {"1", "true", "yes", "on"}


@extend_schema_view(
    list=extend_schema(
        summary="List cashier shifts",
        parameters=[
            OpenApiParameter("cashier", str, description="Filter by cashier UUID."),
            OpenApiParameter("branch", str, description="Filter by branch UUID."),
            OpenApiParameter("is_open", bool, description="Filter open/closed shifts."),
        ],
    ),
    create=extend_schema(summary="Open cashier shift"),
)
class CashierShiftViewSet(ModelViewSet):
    serializer_class = CashierShiftSerializer
    filter_backends = (SearchFilter, OrderingFilter)
    search_fields = ("cashier__email", "branch__name")
    ordering_fields = (
        "opened_at",
        "closed_at",
        "opening_balance",
        "expected_balance",
        "difference",
    )
    ordering = ("-opened_at",)

    def get_queryset(self):
        queryset = CashierShift.objects.select_related(
            "cashier", "branch", "branch__store"
        )
        cashier = self.request.query_params.get("cashier")
        branch = self.request.query_params.get("branch")
        is_open = _bool_param(self.request.query_params.get("is_open"))

        if cashier:
            queryset = queryset.filter(cashier_id=cashier)
        if branch:
            queryset = queryset.filter(branch_id=branch)
        if is_open is not None:
            queryset = queryset.filter(closed_at__isnull=is_open)
        queryset = filter_queryset_by_branch_scope(queryset, self.request.user, "branch_id")
        if not user_has_minimum_role(self.request.user, UserRole.MANAGER):
            queryset = queryset.filter(cashier=self.request.user)
        return queryset

    def perform_create(self, serializer):
        require_branch_access(self.request.user, serializer.validated_data["branch"])
        serializer.save()

    @extend_schema(
        summary="Close cashier shift",
        request=CloseCashierShiftSerializer,
        responses=CashierShiftSerializer,
    )
    @action(detail=True, methods=["post"])
    def close(self, request, pk=None):
        shift = self.get_object()
        serializer = CloseCashierShiftSerializer(
            data=request.data,
            context={"shift": shift},
        )
        serializer.is_valid(raise_exception=True)
        shift = serializer.save()
        return Response(self.get_serializer(shift).data, status=HTTP_200_OK)

    @extend_schema(summary="Calculate current shift totals")
    @action(detail=True, methods=["get"])
    def totals(self, request, pk=None):
        return Response(calculate_shift_totals(self.get_object()), status=HTTP_200_OK)

    @extend_schema(summary="Current user's active cashier shift")
    @action(detail=False, methods=["get"], url_path="active")
    def active(self, request):
        queryset = self.get_queryset().filter(
            cashier=request.user,
            closed_at__isnull=True,
        )
        branch = request.query_params.get("branch")
        if branch:
            queryset = queryset.filter(branch_id=branch)
        shift = queryset.order_by("-opened_at").first()
        if shift is None:
            return Response(None, status=HTTP_200_OK)
        return Response(self.get_serializer(shift).data, status=HTTP_200_OK)
