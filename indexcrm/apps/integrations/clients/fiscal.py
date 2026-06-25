from apps.integrations.clients.base import ExternalIntegrationClient, IntegrationResult


class FiscalSystemClient(ExternalIntegrationClient):
    code = "uzbekistan_fiscal"

    def health_check(self) -> IntegrationResult:
        return IntegrationResult(
            success=False, message="Fiscal integration is not configured yet."
        )
