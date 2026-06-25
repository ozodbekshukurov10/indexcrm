from apps.integrations.clients.base import ExternalIntegrationClient, IntegrationResult


class OfflineSyncClient(ExternalIntegrationClient):
    code = "offline_sync"

    def health_check(self) -> IntegrationResult:
        return IntegrationResult(
            success=False,
            message="Offline sync integration is not configured yet.",
        )
