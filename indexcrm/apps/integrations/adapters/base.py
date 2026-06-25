from dataclasses import dataclass, field
from typing import Any

from apps.integrations.clients.base import IntegrationResult


@dataclass(slots=True)
class AdapterContext:
    provider_code: str
    provider_type: str
    credentials: dict[str, str] = field(default_factory=dict)
    settings: dict[str, Any] = field(default_factory=dict)


class BaseIntegrationAdapter:
    provider_type: str | None = None

    def __init__(self, context: AdapterContext):
        self.context = context

    def health_check(self) -> IntegrationResult:
        return IntegrationResult(
            success=True,
            message=f"{self.context.provider_code} adapter is available in mock mode.",
        )

    def _mock_result(
        self, operation: str, payload: dict[str, Any]
    ) -> IntegrationResult:
        return IntegrationResult(
            success=True,
            external_id=f"mock-{self.context.provider_code}-{operation}",
            payload={
                "operation": operation,
                "provider": self.context.provider_code,
                "mock": True,
                "request": payload,
            },
            message=f"{operation} accepted by mock adapter.",
        )


class FiscalAdapter(BaseIntegrationAdapter):
    def send_receipt(self, receipt_data: dict[str, Any]) -> IntegrationResult:
        raise NotImplementedError


class ReceiptPrinterAdapter(BaseIntegrationAdapter):
    def print_receipt(self, receipt_data: dict[str, Any]) -> IntegrationResult:
        raise NotImplementedError


class MarketplaceAdapter(BaseIntegrationAdapter):
    def sync_order(self, order_data: dict[str, Any]) -> IntegrationResult:
        raise NotImplementedError

    def sync_stock(self, stock_data: dict[str, Any]) -> IntegrationResult:
        raise NotImplementedError


class PaymentAdapter(BaseIntegrationAdapter):
    def prepare_payment(self, payment_data: dict[str, Any]) -> IntegrationResult:
        raise NotImplementedError


class NotificationAdapter(BaseIntegrationAdapter):
    def send_notification(self, notification_data: dict[str, Any]) -> IntegrationResult:
        raise NotImplementedError


class SyncAdapter(BaseIntegrationAdapter):
    def queue_offline_sync(self, sync_data: dict[str, Any]) -> IntegrationResult:
        raise NotImplementedError


class LicensingAdapter(BaseIntegrationAdapter):
    def check_license(self, license_data: dict[str, Any]) -> IntegrationResult:
        raise NotImplementedError
