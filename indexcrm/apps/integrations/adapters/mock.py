from typing import Any

from apps.integrations.adapters.base import (
    FiscalAdapter,
    LicensingAdapter,
    MarketplaceAdapter,
    NotificationAdapter,
    PaymentAdapter,
    ReceiptPrinterAdapter,
    SyncAdapter,
)
from apps.integrations.clients.base import IntegrationResult


class MockFiscalAdapter(FiscalAdapter):
    def send_receipt(self, receipt_data: dict[str, Any]) -> IntegrationResult:
        return self._mock_result("send_receipt", receipt_data)


class MockReceiptPrinterAdapter(ReceiptPrinterAdapter):
    def print_receipt(self, receipt_data: dict[str, Any]) -> IntegrationResult:
        return self._mock_result("print_receipt", receipt_data)


class MockMarketplaceAdapter(MarketplaceAdapter):
    def sync_order(self, order_data: dict[str, Any]) -> IntegrationResult:
        return self._mock_result("sync_order", order_data)

    def sync_stock(self, stock_data: dict[str, Any]) -> IntegrationResult:
        return self._mock_result("sync_stock", stock_data)


class MockPaymentAdapter(PaymentAdapter):
    def prepare_payment(self, payment_data: dict[str, Any]) -> IntegrationResult:
        return self._mock_result("prepare_payment", payment_data)


class MockNotificationAdapter(NotificationAdapter):
    def send_notification(self, notification_data: dict[str, Any]) -> IntegrationResult:
        return self._mock_result("send_notification", notification_data)


class MockSyncAdapter(SyncAdapter):
    def queue_offline_sync(self, sync_data: dict[str, Any]) -> IntegrationResult:
        return self._mock_result("queue_offline_sync", sync_data)


class MockLicensingAdapter(LicensingAdapter):
    def check_license(self, license_data: dict[str, Any]) -> IntegrationResult:
        return self._mock_result("check_license", license_data)
