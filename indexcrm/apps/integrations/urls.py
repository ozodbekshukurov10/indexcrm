from rest_framework.routers import DefaultRouter

from apps.integrations.views import (
    ExternalMappingViewSet,
    IntegrationCredentialViewSet,
    IntegrationProviderViewSet,
    IntegrationTaskViewSet,
    SyncLogViewSet,
    WebhookEventViewSet,
)

router = DefaultRouter()
router.register(
    "integration-providers", IntegrationProviderViewSet, basename="integration-provider"
)
router.register(
    "integration-credentials",
    IntegrationCredentialViewSet,
    basename="integration-credential",
)
router.register(
    "integration-tasks", IntegrationTaskViewSet, basename="integration-task"
)
router.register("sync-logs", SyncLogViewSet, basename="sync-log")
router.register("webhook-events", WebhookEventViewSet, basename="webhook-event")
router.register(
    "external-mappings", ExternalMappingViewSet, basename="external-mapping"
)

urlpatterns = router.urls
