import pytest

from apps.accounts.models import User, UserRole
from apps.integrations.adapters import MOCK_PROVIDER_DEFINITIONS
from apps.integrations.adapters.base import (
    BaseIntegrationAdapter,
    FiscalAdapter,
    LicensingAdapter,
    MarketplaceAdapter,
    NotificationAdapter,
    PaymentAdapter,
    ReceiptPrinterAdapter,
    SyncAdapter,
)
from apps.integrations.adapters.registry import get_mock_adapter
from apps.integrations.models import (
    IntegrationCredential,
    IntegrationProvider,
    IntegrationProviderType,
    IntegrationTask,
    IntegrationTaskStatus,
    SyncLog,
    SyncLogStatus,
    WebhookEvent,
)
from apps.integrations.services import (
    check_license,
    log_webhook_event,
    prepare_payment,
    print_receipt,
    queue_offline_sync,
    send_notification,
    send_receipt,
    sync_order,
    sync_stock,
)


@pytest.fixture
def owner(db):
    return User.objects.create_user(
        email="adapter-owner@example.com",
        password="test-pass-123",
        role=UserRole.OWNER,
    )


def create_provider(provider_type, code):
    return IntegrationProvider.objects.create(
        code=code,
        name=f"{code} provider",
        provider_type=provider_type,
        status="active",
        settings={"mock": True},
    )


@pytest.mark.django_db
def test_mock_provider_definitions_cover_stage_nine_placeholders():
    provider_types = {
        definition["provider_type"] for definition in MOCK_PROVIDER_DEFINITIONS
    }

    assert IntegrationProviderType.FISCAL_CHECK in provider_types
    assert IntegrationProviderType.RECEIPT_PRINTER in provider_types
    assert IntegrationProviderType.UZUM_MARKET in provider_types
    assert IntegrationProviderType.PAYMENT_PROVIDER in provider_types
    assert IntegrationProviderType.TELEGRAM in provider_types
    assert IntegrationProviderType.SMS in provider_types
    assert IntegrationProviderType.OFFLINE_SYNC in provider_types
    assert IntegrationProviderType.CENTRAL_LICENSING in provider_types


@pytest.mark.django_db
def test_mock_adapters_expose_expected_interfaces():
    fiscal = get_mock_adapter(
        create_provider(IntegrationProviderType.FISCAL_CHECK, "mock_fiscal_adapter")
    )
    printer = get_mock_adapter(
        create_provider(IntegrationProviderType.RECEIPT_PRINTER, "mock_printer_adapter")
    )
    marketplace = get_mock_adapter(
        create_provider(IntegrationProviderType.UZUM_MARKET, "mock_market_adapter")
    )
    notification = get_mock_adapter(
        create_provider(IntegrationProviderType.TELEGRAM, "mock_telegram_adapter")
    )
    payment = get_mock_adapter(
        create_provider(
            IntegrationProviderType.PAYMENT_PROVIDER, "mock_payment_adapter"
        )
    )
    sync = get_mock_adapter(
        create_provider(IntegrationProviderType.OFFLINE_SYNC, "mock_sync_adapter")
    )
    licensing = get_mock_adapter(
        create_provider(
            IntegrationProviderType.CENTRAL_LICENSING, "mock_license_adapter"
        )
    )

    assert isinstance(fiscal, BaseIntegrationAdapter)
    assert isinstance(fiscal, FiscalAdapter)
    assert isinstance(printer, ReceiptPrinterAdapter)
    assert isinstance(marketplace, MarketplaceAdapter)
    assert isinstance(notification, NotificationAdapter)
    assert isinstance(payment, PaymentAdapter)
    assert isinstance(sync, SyncAdapter)
    assert isinstance(licensing, LicensingAdapter)


@pytest.mark.django_db
def test_stage_nine_service_methods_log_attempts(owner):
    fiscal = create_provider(
        IntegrationProviderType.FISCAL_CHECK, "mock_fiscal_service"
    )
    printer = create_provider(
        IntegrationProviderType.RECEIPT_PRINTER,
        "mock_printer_service",
    )
    marketplace = create_provider(
        IntegrationProviderType.UZUM_MARKET,
        "mock_market_service",
    )
    payment = create_provider(
        IntegrationProviderType.PAYMENT_PROVIDER,
        "mock_payment_service",
    )
    telegram = create_provider(
        IntegrationProviderType.TELEGRAM, "mock_telegram_service"
    )
    sms = create_provider(IntegrationProviderType.SMS, "mock_sms_service")
    offline_sync = create_provider(
        IntegrationProviderType.OFFLINE_SYNC,
        "mock_offline_service",
    )
    licensing = create_provider(
        IntegrationProviderType.CENTRAL_LICENSING,
        "mock_license_service",
    )

    IntegrationCredential.objects.create(
        provider=telegram,
        key="bot_token",
        value="mock-secret",
        created_by=owner,
    )

    results = [
        send_receipt(
            provider=fiscal,
            receipt_data={"receipt_number": "R-1"},
            created_by=owner,
        ),
        print_receipt(
            provider=printer,
            receipt_data={"receipt_number": "R-1"},
            created_by=owner,
        ),
        sync_order(
            provider=marketplace,
            order_data={"order_id": "ORDER-1"},
            created_by=owner,
        ),
        sync_stock(
            provider=marketplace,
            stock_data={"sku": "SKU-1", "quantity": "10"},
            created_by=owner,
        ),
        prepare_payment(
            provider=payment,
            payment_data={"amount": "1000.00"},
            created_by=owner,
        ),
        send_notification(
            provider=telegram,
            recipient="@index",
            message="Test notification",
            created_by=owner,
        ),
        send_notification(
            provider=sms,
            recipient="+998901234567",
            message="Test SMS",
            created_by=owner,
        ),
        queue_offline_sync(
            provider=offline_sync,
            sync_data={"model": "catalog.Product"},
            created_by=owner,
        ),
        check_license(
            provider=licensing,
            license_data={"installation_id": "local"},
            created_by=owner,
        ),
    ]

    assert all(result.success for result in results)
    assert SyncLog.objects.filter(status=SyncLogStatus.SUCCESS).count() == len(results)
    assert IntegrationTask.objects.filter(
        status=IntegrationTaskStatus.SUCCESS
    ).count() == len(results)
    assert IntegrationTask.objects.filter(attempts=1).count() == len(results)
    assert IntegrationCredential.objects.get(provider=telegram).last_used_at is not None
    assert SyncLog.objects.filter(operation="send_receipt").exists()
    assert SyncLog.objects.filter(operation="print_receipt").exists()
    assert SyncLog.objects.filter(operation="sync_order").exists()
    assert SyncLog.objects.filter(operation="sync_stock").exists()
    assert SyncLog.objects.filter(operation="send_notification").count() == 2
    assert SyncLog.objects.filter(operation="check_license").exists()
    assert SyncLog.objects.filter(operation="queue_offline_sync").exists()


@pytest.mark.django_db
def test_webhook_event_logging_remains_available_for_adapter_layer():
    provider = create_provider(IntegrationProviderType.PAYMENT_PROVIDER, "mock_webhook")

    event = log_webhook_event(
        provider=provider,
        event_type="payment.test",
        payload={"status": "mocked"},
        external_event_id="evt_mock",
        signature="signature-placeholder",
    )

    assert event.provider == provider
    assert event.signature == "signature-placeholder"
    assert WebhookEvent.objects.filter(event_type="payment.test").exists()


@pytest.mark.django_db
def test_unsupported_adapter_attempts_are_logged(owner):
    provider = create_provider(IntegrationProviderType.OTHER, "mock_unsupported")

    with pytest.raises(ValueError):
        send_receipt(
            provider=provider,
            receipt_data={"receipt_number": "R-unsupported"},
            created_by=owner,
        )

    task = IntegrationTask.objects.get(provider=provider)
    log = SyncLog.objects.get(provider=provider)

    assert task.status == IntegrationTaskStatus.FAILED
    assert task.attempts == 1
    assert log.status == SyncLogStatus.FAILED
    assert log.operation == "send_receipt"
