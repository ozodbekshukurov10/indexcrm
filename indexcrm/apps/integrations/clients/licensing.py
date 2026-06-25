from apps.integrations.clients.base import ExternalIntegrationClient, IntegrationResult


class CentralLicensingClient(ExternalIntegrationClient):
    code = "central_licensing"

    def health_check(self) -> IntegrationResult:
        return IntegrationResult(
            success=False,
            message="Central licensing check-in is not configured yet.",
        )
