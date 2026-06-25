from apps.integrations.clients.base import ExternalIntegrationClient, IntegrationResult


class PaymentProviderClient(ExternalIntegrationClient):
    code = "payment_provider"

    def health_check(self) -> IntegrationResult:
        return IntegrationResult(
            success=False, message="Payment integration is not configured yet."
        )
