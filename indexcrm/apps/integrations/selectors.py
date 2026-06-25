from apps.integrations.models import (
    ExternalMapping,
    IntegrationCredential,
    IntegrationProvider,
    IntegrationTask,
    SyncLog,
    WebhookEvent,
)


def provider_queryset():
    return IntegrationProvider.objects.select_related("branch", "branch__store")


def credential_queryset():
    return IntegrationCredential.objects.select_related("provider", "created_by")


def sync_log_queryset():
    return SyncLog.objects.select_related("provider", "task")


def webhook_event_queryset():
    return WebhookEvent.objects.select_related("provider")


def integration_task_queryset():
    return IntegrationTask.objects.select_related("provider", "created_by")


def external_mapping_queryset():
    return ExternalMapping.objects.select_related("provider")


def get_provider_by_code(code):
    return provider_queryset().get(code=code)


def get_credentials_for_provider(provider):
    return {
        credential.key: credential.value
        for credential in IntegrationCredential.objects.filter(
            provider=provider,
            deleted_at__isnull=True,
        )
    }


def get_external_mapping(
    provider, *, local_model=None, local_id=None, external_id=None
):
    queryset = external_mapping_queryset().filter(provider=provider)
    if local_model and local_id:
        return queryset.get(local_model=local_model, local_id=local_id)
    if external_id:
        return queryset.get(external_id=external_id)
    raise ValueError("Provide either local_model/local_id or external_id.")
