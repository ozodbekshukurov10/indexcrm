from apps.integrations.adapters.base import AdapterContext
from apps.integrations.adapters.mock import (
    MockFiscalAdapter,
    MockLicensingAdapter,
    MockMarketplaceAdapter,
    MockNotificationAdapter,
    MockPaymentAdapter,
    MockReceiptPrinterAdapter,
    MockSyncAdapter,
)
from apps.integrations.models import IntegrationProviderType

MOCK_ADAPTERS = {
    IntegrationProviderType.FISCAL_CHECK: MockFiscalAdapter,
    IntegrationProviderType.RECEIPT_PRINTER: MockReceiptPrinterAdapter,
    IntegrationProviderType.UZUM_MARKET: MockMarketplaceAdapter,
    IntegrationProviderType.PAYMENT_PROVIDER: MockPaymentAdapter,
    IntegrationProviderType.TELEGRAM: MockNotificationAdapter,
    IntegrationProviderType.SMS: MockNotificationAdapter,
    IntegrationProviderType.OFFLINE_SYNC: MockSyncAdapter,
    IntegrationProviderType.CENTRAL_LICENSING: MockLicensingAdapter,
}

MOCK_PROVIDER_DEFINITIONS = [
    {
        "code": "mock_fiscal",
        "name": "Mock Fiscal System",
        "provider_type": IntegrationProviderType.FISCAL_CHECK,
    },
    {
        "code": "mock_receipt_printer",
        "name": "Mock Receipt Printer",
        "provider_type": IntegrationProviderType.RECEIPT_PRINTER,
    },
    {
        "code": "mock_uzum_market",
        "name": "Mock Uzum Market",
        "provider_type": IntegrationProviderType.UZUM_MARKET,
    },
    {
        "code": "mock_payment_provider",
        "name": "Mock Payment Provider",
        "provider_type": IntegrationProviderType.PAYMENT_PROVIDER,
    },
    {
        "code": "mock_telegram",
        "name": "Mock Telegram",
        "provider_type": IntegrationProviderType.TELEGRAM,
    },
    {
        "code": "mock_sms",
        "name": "Mock SMS",
        "provider_type": IntegrationProviderType.SMS,
    },
    {
        "code": "mock_offline_sync",
        "name": "Mock Offline Sync",
        "provider_type": IntegrationProviderType.OFFLINE_SYNC,
    },
    {
        "code": "mock_licensing",
        "name": "Mock Central Licensing",
        "provider_type": IntegrationProviderType.CENTRAL_LICENSING,
    },
]


def build_adapter_context(provider):
    from apps.integrations.services.integrations import lookup_credentials

    return AdapterContext(
        provider_code=provider.code,
        provider_type=provider.provider_type,
        credentials=lookup_credentials(provider),
        settings=provider.settings or {},
    )


def get_mock_adapter(provider):
    adapter_class = MOCK_ADAPTERS.get(provider.provider_type)
    if adapter_class is None:
        raise ValueError(
            f"Unsupported integration provider type: {provider.provider_type}"
        )
    return adapter_class(build_adapter_context(provider))
