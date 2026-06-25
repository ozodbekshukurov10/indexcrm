from apps.integrations.clients.base import ExternalIntegrationClient, IntegrationResult


class CashRegisterClient(ExternalIntegrationClient):
    code = "cash_register"

    def health_check(self) -> IntegrationResult:
        return IntegrationResult(
            success=False, message="Cash register integration is not configured yet."
        )
