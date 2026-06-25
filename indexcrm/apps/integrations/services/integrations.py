from django.db import transaction
from django.utils import timezone

from apps.integrations.models import (
    IntegrationCredential,
    IntegrationTask,
    IntegrationTaskStatus,
    SyncLog,
    SyncLogStatus,
    WebhookEvent,
    WebhookEventStatus,
)


def _authenticated_user(user):
    return user if getattr(user, "is_authenticated", False) else None


def mask_credential_value(value):
    if not value:
        return ""
    return "********"


def lookup_credentials(provider):
    credentials = IntegrationCredential.objects.filter(
        provider=provider,
        deleted_at__isnull=True,
    )
    now = timezone.now()
    credential_map = {}
    used_ids = []
    for credential in credentials:
        credential_map[credential.key] = credential.value
        used_ids.append(credential.id)

    if used_ids:
        IntegrationCredential.objects.filter(id__in=used_ids).update(
            last_used_at=now,
            updated_at=now,
        )
    return credential_map


def create_sync_log(
    *,
    provider,
    operation,
    status=SyncLogStatus.STARTED,
    task=None,
    message="",
    request_payload=None,
    response_payload=None,
    error_code="",
    error_message="",
):
    return SyncLog.objects.create(
        provider=provider,
        task=task,
        operation=operation,
        status=status,
        message=message,
        request_payload=request_payload or {},
        response_payload=response_payload or {},
        error_code=error_code,
        error_message=error_message,
        finished_at=(
            timezone.now()
            if status in {SyncLogStatus.SUCCESS, SyncLogStatus.FAILED}
            else None
        ),
    )


@transaction.atomic
def update_retry_status(
    task,
    *,
    status=IntegrationTaskStatus.RETRYING,
    result=None,
    next_retry_at=None,
):
    task = IntegrationTask.objects.select_for_update().get(pk=task.pk)
    task.attempts += 1
    task.status = status
    task.result = result or task.result
    task.next_retry_at = next_retry_at
    if status == IntegrationTaskStatus.RUNNING:
        task.started_at = timezone.now()
        task.finished_at = None
    if status == IntegrationTaskStatus.RETRYING:
        task.finished_at = None
    if status in {
        IntegrationTaskStatus.SUCCESS,
        IntegrationTaskStatus.FAILED,
        IntegrationTaskStatus.CANCELLED,
    }:
        task.finished_at = timezone.now()
    task.full_clean()
    task.save(
        update_fields=(
            "attempts",
            "status",
            "result",
            "next_retry_at",
            "started_at",
            "finished_at",
            "updated_at",
        )
    )
    return task


def log_webhook_event(
    *,
    provider,
    event_type,
    payload=None,
    headers=None,
    external_event_id="",
    signature="",
    status=WebhookEventStatus.RECEIVED,
):
    return WebhookEvent.objects.create(
        provider=provider,
        event_type=event_type,
        external_event_id=external_event_id,
        status=status,
        headers=headers or {},
        payload=payload or {},
        signature=signature,
    )


def create_integration_task(
    *,
    provider,
    task_type,
    payload=None,
    direction=None,
    created_by=None,
):
    data = {
        "provider": provider,
        "task_type": task_type,
        "payload": payload or {},
        "created_by": _authenticated_user(created_by),
    }
    if direction:
        data["direction"] = direction
    return IntegrationTask.objects.create(**data)
