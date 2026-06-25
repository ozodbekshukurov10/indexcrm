from apps.integrations.clients.base import ExternalIntegrationClient, IntegrationResult


class UzumMarketClient(ExternalIntegrationClient):
    code = "uzum_market"

    def health_check(self) -> IntegrationResult:
        return IntegrationResult(
            success=False, message="Uzum Market integration is not configured yet."
        )
