import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User, UserRole
from apps.integrations.models import (
    ExternalMapping,
    IntegrationCredential,
    IntegrationProvider,
    IntegrationProviderType,
    IntegrationTaskStatus,
    SyncLogStatus,
    WebhookEventStatus,
)
from apps.integrations.services import (
    create_integration_task,
    create_sync_log,
    log_webhook_event,
    lookup_credentials,
    update_retry_status,
)


@pytest.fixture
def owner(db):
    return User.objects.create_user(
        email="integration-owner@example.com",
        password="test-pass-123",
        role=UserRole.OWNER,
        is_staff=True,
    )


@pytest.fixture
def provider(db):
    return IntegrationProvider.objects.create(
        code="telegram_bot",
        name="Telegram Bot",
        provider_type=IntegrationProviderType.TELEGRAM,
        status="active",
        settings={"placeholder": True},
    )


@pytest.mark.django_db
def test_integration_api_masks_credentials_and_lists_placeholders(owner):
    client = APIClient()
    client.force_authenticate(user=owner)

    provider_response = client.post(
        "/api/integration-providers/",
        {
            "code": "uzum_market",
            "name": "Uzum Market",
            "provider_type": IntegrationProviderType.UZUM_MARKET,
            "status": "draft",
            "settings": {"sandbox": True},
        },
        format="json",
    )
    credential_response = client.post(
        "/api/integration-credentials/",
        {
            "provider": provider_response.data["id"],
            "key": "api_token",
            "value": "super-secret-token",
            "is_secret": False,
        },
        format="json",
    )
    placeholders_response = client.get("/api/integration-providers/placeholders/")

    assert provider_response.status_code == 201
    assert credential_response.status_code == 201
    assert "value" not in credential_response.data
    assert credential_response.data["masked_value"] == "********"
    assert "super-secret-token" not in str(credential_response.data)
    assert placeholders_response.status_code == 200
    placeholder_codes = {item["code"] for item in placeholders_response.data}
    assert IntegrationProviderType.FISCAL_CHECK in placeholder_codes
    assert IntegrationProviderType.RECEIPT_PRINTER in placeholder_codes
    assert IntegrationProviderType.UZUM_MARKET in placeholder_codes
    assert IntegrationProviderType.PAYMENT_PROVIDER in placeholder_codes
    assert IntegrationProviderType.TELEGRAM in placeholder_codes
    assert IntegrationProviderType.SMS in placeholder_codes
    assert IntegrationProviderType.OFFLINE_SYNC in placeholder_codes
    assert IntegrationProviderType.CENTRAL_LICENSING in placeholder_codes


@pytest.mark.django_db
def test_integration_services_lookup_logs_retry_and_webhooks(provider, owner):
    IntegrationCredential.objects.create(
        provider=provider,
        key="bot_token",
        value="telegram-secret-token",
        created_by=owner,
    )

    credentials = lookup_credentials(provider)
    task = create_integration_task(
        provider=provider,
        task_type="send_message",
        payload={"chat_id": "1"},
        created_by=owner,
    )
    sync_log = create_sync_log(
        provider=provider,
        task=task,
        operation="send_message",
        status=SyncLogStatus.FAILED,
        error_code="NOT_CONFIGURED",
        error_message="Telegram is not configured yet.",
    )
    retried_task = update_retry_status(
        task,
        status=IntegrationTaskStatus.RETRYING,
        result={"error": "temporary"},
        next_retry_at=timezone.now(),
    )
    webhook_event = log_webhook_event(
        provider=provider,
        event_type="message.created",
        external_event_id="evt_1",
        payload={"ok": True},
        signature="signature-placeholder",
    )

    assert credentials == {"bot_token": "telegram-secret-token"}
    assert IntegrationCredential.objects.get(provider=provider).last_used_at is not None
    assert sync_log.status == SyncLogStatus.FAILED
    assert sync_log.finished_at is not None
    assert retried_task.attempts == 1
    assert retried_task.status == IntegrationTaskStatus.RETRYING
    assert retried_task.finished_at is None
    assert webhook_event.status == WebhookEventStatus.RECEIVED


@pytest.mark.django_db
def test_integration_tasks_webhooks_and_mappings_api(owner, provider):
    client = APIClient()
    client.force_authenticate(user=owner)

    task_response = client.post(
        "/api/integration-tasks/",
        {
            "provider": str(provider.id),
            "task_type": "central_license_check_in",
            "payload": {"installation_id": "placeholder"},
        },
        format="json",
    )
    retry_response = client.post(
        f"/api/integration-tasks/{task_response.data['id']}/retry/",
        {"result": {"reason": "placeholder retry"}},
        format="json",
    )
    webhook_response = client.post(
        "/api/webhook-events/",
        {
            "provider": str(provider.id),
            "event_type": "payment.created",
            "external_event_id": "evt_1",
            "payload": {"amount": "1000"},
            "signature": "secret-signature",
        },
        format="json",
    )
    mapping_response = client.post(
        "/api/external-mappings/",
        {
            "provider": str(provider.id),
            "local_model": "catalog.Product",
            "local_id": "00000000-0000-0000-0000-000000000001",
            "external_id": "ext-product-1",
            "external_type": "product",
        },
        format="json",
    )

    assert task_response.status_code == 201
    assert retry_response.status_code == 200
    assert retry_response.data["status"] == IntegrationTaskStatus.RETRYING
    assert retry_response.data["attempts"] == 1
    assert webhook_response.status_code == 201
    assert "signature" not in webhook_response.data
    assert mapping_response.status_code == 201
    assert ExternalMapping.objects.filter(external_id="ext-product-1").exists()


@pytest.mark.django_db
def test_integration_api_requires_owner_or_admin(provider):
    cashier = User.objects.create_user(
        email="integration-cashier@example.com",
        password="test-pass-123",
        role=UserRole.CASHIER,
    )
    client = APIClient()
    client.force_authenticate(user=cashier)

    response = client.get("/api/integration-providers/")

    assert response.status_code == 403
