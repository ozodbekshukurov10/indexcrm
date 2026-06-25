from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK
from rest_framework.viewsets import ModelViewSet

from apps.accounts.permissions import IsOwnerOrAdmin
from apps.integrations.models import IntegrationProviderType, IntegrationTaskStatus
from apps.integrations.selectors import (
    credential_queryset,
    external_mapping_queryset,
    integration_task_queryset,
    provider_queryset,
    sync_log_queryset,
    webhook_event_queryset,
)
from apps.integrations.serializers import (
    ExternalMappingSerializer,
    IntegrationCredentialSerializer,
    IntegrationProviderSerializer,
    IntegrationTaskRetrySerializer,
    IntegrationTaskSerializer,
    SyncLogSerializer,
    WebhookEventSerializer,
)
from apps.integrations.services import update_retry_status


def _bool_param(value):
    if value is None:
        return None
    return str(value).lower() in {"1", "true", "yes", "on"}


@extend_schema_view(
    list=extend_schema(
        summary="List integration providers",
        parameters=[
            OpenApiParameter(
                "provider_type", str, description="Filter by provider type."
            ),
            OpenApiParameter("status", str, description="Filter by provider status."),
            OpenApiParameter("branch", str, description="Filter by branch UUID."),
            OpenApiParameter("is_active", bool, description="Filter active providers."),
        ],
    ),
    create=extend_schema(
        summary="Create integration provider placeholder",
        description="Creates configuration metadata only. Real external API calls are deferred.",
    ),
)
class IntegrationProviderViewSet(ModelViewSet):
    serializer_class = IntegrationProviderSerializer
    permission_classes = (IsOwnerOrAdmin,)
    filter_backends = (SearchFilter, OrderingFilter)
    search_fields = ("code", "name", "provider_type", "description", "branch__name")
    ordering_fields = ("name", "code", "provider_type", "status", "created_at")
    ordering = ("name",)

    def get_queryset(self):
        queryset = provider_queryset()
        provider_type = self.request.query_params.get("provider_type")
        status = self.request.query_params.get("status")
        branch = self.request.query_params.get("branch")
        is_active = _bool_param(self.request.query_params.get("is_active"))

        if provider_type:
            queryset = queryset.filter(provider_type=provider_type)
        if status:
            queryset = queryset.filter(status=status)
        if branch:
            queryset = queryset.filter(branch_id=branch)
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active)
        return queryset

    @extend_schema(
        summary="Integration provider placeholders",
        description="Returns supported placeholder provider types for future integrations.",
    )
    @action(detail=False, methods=["get"])
    def placeholders(self, request):
        return Response(
            [
                {"code": code, "name": label}
                for code, label in IntegrationProviderType.choices
            ],
            status=HTTP_200_OK,
        )


@extend_schema_view(
    list=extend_schema(
        summary="List masked integration credentials",
        parameters=[
            OpenApiParameter("provider", str, description="Filter by provider UUID."),
            OpenApiParameter("key", str, description="Filter by credential key."),
        ],
    ),
    create=extend_schema(
        summary="Create integration credential",
        description="Credential values are accepted on write but never returned in API responses.",
    ),
)
class IntegrationCredentialViewSet(ModelViewSet):
    serializer_class = IntegrationCredentialSerializer
    permission_classes = (IsOwnerOrAdmin,)
    filter_backends = (SearchFilter, OrderingFilter)
    search_fields = ("provider__code", "provider__name", "key", "created_by__email")
    ordering_fields = ("key", "expires_at", "last_used_at", "created_at")
    ordering = ("provider__name", "key")

    def get_queryset(self):
        queryset = credential_queryset()
        provider = self.request.query_params.get("provider")
        key = self.request.query_params.get("key")
        if provider:
            queryset = queryset.filter(provider_id=provider)
        if key:
            queryset = queryset.filter(key=key)
        return queryset

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


@extend_schema_view(
    list=extend_schema(
        summary="List integration tasks",
        parameters=[
            OpenApiParameter("provider", str, description="Filter by provider UUID."),
            OpenApiParameter("status", str, description="Filter by task status."),
            OpenApiParameter("task_type", str, description="Filter by task type."),
        ],
    ),
    create=extend_schema(
        summary="Create integration task placeholder",
        description="Creates an async-task placeholder. Execution workers are deferred.",
    ),
)
class IntegrationTaskViewSet(ModelViewSet):
    serializer_class = IntegrationTaskSerializer
    permission_classes = (IsOwnerOrAdmin,)
    filter_backends = (SearchFilter, OrderingFilter)
    search_fields = ("provider__code", "provider__name", "task_type", "status")
    ordering_fields = ("task_type", "status", "attempts", "next_retry_at", "created_at")
    ordering = ("-created_at",)

    def get_queryset(self):
        queryset = integration_task_queryset()
        provider = self.request.query_params.get("provider")
        status = self.request.query_params.get("status")
        task_type = self.request.query_params.get("task_type")
        if provider:
            queryset = queryset.filter(provider_id=provider)
        if status:
            queryset = queryset.filter(status=status)
        if task_type:
            queryset = queryset.filter(task_type=task_type)
        return queryset

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @extend_schema(
        summary="Mark integration task for retry",
        request=IntegrationTaskRetrySerializer,
        responses=IntegrationTaskSerializer,
    )
    @action(detail=True, methods=["post"])
    def retry(self, request, pk=None):
        serializer = IntegrationTaskRetrySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        task = update_retry_status(
            self.get_object(),
            status=IntegrationTaskStatus.RETRYING,
            result=serializer.validated_data.get("result"),
            next_retry_at=serializer.validated_data.get("next_retry_at"),
        )
        return Response(self.get_serializer(task).data, status=HTTP_200_OK)


@extend_schema_view(
    list=extend_schema(
        summary="List sync logs",
        parameters=[
            OpenApiParameter("provider", str, description="Filter by provider UUID."),
            OpenApiParameter(
                "task", str, description="Filter by integration task UUID."
            ),
            OpenApiParameter("status", str, description="Filter by sync status."),
            OpenApiParameter("operation", str, description="Filter by operation."),
        ],
    ),
    create=extend_schema(summary="Create sync log placeholder"),
)
class SyncLogViewSet(ModelViewSet):
    serializer_class = SyncLogSerializer
    permission_classes = (IsOwnerOrAdmin,)
    filter_backends = (SearchFilter, OrderingFilter)
    search_fields = ("provider__code", "provider__name", "operation", "message")
    ordering_fields = ("status", "operation", "started_at", "finished_at", "created_at")
    ordering = ("-created_at",)

    def get_queryset(self):
        queryset = sync_log_queryset()
        provider = self.request.query_params.get("provider")
        task = self.request.query_params.get("task")
        status = self.request.query_params.get("status")
        operation = self.request.query_params.get("operation")
        if provider:
            queryset = queryset.filter(provider_id=provider)
        if task:
            queryset = queryset.filter(task_id=task)
        if status:
            queryset = queryset.filter(status=status)
        if operation:
            queryset = queryset.filter(operation=operation)
        return queryset


@extend_schema_view(
    list=extend_schema(
        summary="List webhook events",
        parameters=[
            OpenApiParameter("provider", str, description="Filter by provider UUID."),
            OpenApiParameter("status", str, description="Filter by webhook status."),
            OpenApiParameter("event_type", str, description="Filter by event type."),
        ],
    ),
    create=extend_schema(
        summary="Log webhook event placeholder",
        description="Stores inbound webhook metadata only. Real verification/processing is deferred.",
    ),
)
class WebhookEventViewSet(ModelViewSet):
    serializer_class = WebhookEventSerializer
    permission_classes = (IsOwnerOrAdmin,)
    filter_backends = (SearchFilter, OrderingFilter)
    search_fields = (
        "provider__code",
        "provider__name",
        "event_type",
        "external_event_id",
    )
    ordering_fields = ("event_type", "status", "received_at", "created_at")
    ordering = ("-received_at",)

    def get_queryset(self):
        queryset = webhook_event_queryset()
        provider = self.request.query_params.get("provider")
        status = self.request.query_params.get("status")
        event_type = self.request.query_params.get("event_type")
        if provider:
            queryset = queryset.filter(provider_id=provider)
        if status:
            queryset = queryset.filter(status=status)
        if event_type:
            queryset = queryset.filter(event_type=event_type)
        return queryset


@extend_schema_view(
    list=extend_schema(
        summary="List external mappings",
        parameters=[
            OpenApiParameter("provider", str, description="Filter by provider UUID."),
            OpenApiParameter(
                "local_model", str, description="Filter by local model label."
            ),
            OpenApiParameter(
                "external_type", str, description="Filter by external type."
            ),
        ],
    ),
    create=extend_schema(summary="Create external mapping placeholder"),
)
class ExternalMappingViewSet(ModelViewSet):
    serializer_class = ExternalMappingSerializer
    permission_classes = (IsOwnerOrAdmin,)
    filter_backends = (SearchFilter, OrderingFilter)
    search_fields = (
        "provider__code",
        "provider__name",
        "local_model",
        "external_id",
        "external_type",
    )
    ordering_fields = ("local_model", "external_type", "last_synced_at", "created_at")
    ordering = ("provider__name", "local_model")

    def get_queryset(self):
        queryset = external_mapping_queryset()
        provider = self.request.query_params.get("provider")
        local_model = self.request.query_params.get("local_model")
        external_type = self.request.query_params.get("external_type")
        if provider:
            queryset = queryset.filter(provider_id=provider)
        if local_model:
            queryset = queryset.filter(local_model=local_model)
        if external_type:
            queryset = queryset.filter(external_type=external_type)
        return queryset
