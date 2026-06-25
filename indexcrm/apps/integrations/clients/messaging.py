from apps.integrations.clients.base import ExternalIntegrationClient, IntegrationResult


class TelegramClient(ExternalIntegrationClient):
    code = "telegram"

    def health_check(self) -> IntegrationResult:
        return IntegrationResult(
            success=False,
            message="Telegram integration is not configured yet.",
        )


class SmsClient(ExternalIntegrationClient):
    code = "sms"

    def health_check(self) -> IntegrationResult:
        return IntegrationResult(
            success=False,
            message="SMS integration is not configured yet.",
        )
