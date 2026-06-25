from apps.integrations.clients.base import ExternalIntegrationClient, IntegrationResult


class ReceiptPrinterClient(ExternalIntegrationClient):
    code = "receipt_printer"

    def health_check(self) -> IntegrationResult:
        return IntegrationResult(
            success=False,
            message="Receipt printer integration is not configured yet.",
        )
