from collections.abc import Callable
from typing import Any

from django.core.exceptions import ValidationError

from apps.integrations.adapters import get_mock_adapter
from apps.integrations.clients.base import IntegrationResult
from apps.integrations.models import (
    IntegrationDirection,
    IntegrationTaskStatus,
    SyncLogStatus,
)
from apps.integrations.services.integrations import (
    create_integration_task,
    create_sync_log,
    update_retry_status,
)


def _ensure_dict(payload, field_name):
    if not isinstance(payload, dict):
        raise ValidationError({field_name: "Payload must be an object."})
    return payload


def _execute_adapter_operation(
    *,
    provider,
    operation: str,
    payload: dict[str, Any],
    method_name: str,
    created_by=None,
) -> IntegrationResult:
    payload = _ensure_dict(payload, "payload")
    task = create_integration_task(
        provider=provider,
        task_type=operation,
        payload=payload,
        direction=IntegrationDirection.OUTBOUND,
        created_by=created_by,
    )
    try:
        adapter = get_mock_adapter(provider)
        method: Callable[[dict[str, Any]], IntegrationResult] | None = getattr(
            adapter, method_name, None
        )
        if method is None:
            raise ValidationError(
                {
                    "provider_type": (
                        f"{provider.provider_type} does not support {operation}."
                    )
                }
            )
        result = method(payload)
    except Exception as error:
        create_sync_log(
            provider=provider,
            task=task,
            operation=operation,
            status=SyncLogStatus.FAILED,
            request_payload=payload,
            error_code=error.__class__.__name__,
            error_message=str(error),
        )
        update_retry_status(
            task,
            status=IntegrationTaskStatus.FAILED,
            result={"error": str(error)},
        )
        raise

    status = SyncLogStatus.SUCCESS if result.success else SyncLogStatus.FAILED
    create_sync_log(
        provider=provider,
        task=task,
        operation=operation,
        status=status,
        message=result.message,
        request_payload=payload,
        response_payload={
            "external_id": result.external_id,
            "payload": dict(result.payload),
        },
    )
    update_retry_status(
        task,
        status=(
            IntegrationTaskStatus.SUCCESS
            if result.success
            else IntegrationTaskStatus.FAILED
        ),
        result={
            "success": result.success,
            "external_id": result.external_id,
            "message": result.message,
        },
    )
    return result


def send_receipt(*, provider, receipt_data, created_by=None) -> IntegrationResult:
    return _execute_adapter_operation(
        provider=provider,
        operation="send_receipt",
        payload=receipt_data,
        method_name="send_receipt",
        created_by=created_by,
    )


def print_receipt(*, provider, receipt_data, created_by=None) -> IntegrationResult:
    return _execute_adapter_operation(
        provider=provider,
        operation="print_receipt",
        payload=receipt_data,
        method_name="print_receipt",
        created_by=created_by,
    )


def sync_order(*, provider, order_data, created_by=None) -> IntegrationResult:
    return _execute_adapter_operation(
        provider=provider,
        operation="sync_order",
        payload=order_data,
        method_name="sync_order",
        created_by=created_by,
    )


def sync_stock(*, provider, stock_data, created_by=None) -> IntegrationResult:
    return _execute_adapter_operation(
        provider=provider,
        operation="sync_stock",
        payload=stock_data,
        method_name="sync_stock",
        created_by=created_by,
    )


def prepare_payment(*, provider, payment_data, created_by=None) -> IntegrationResult:
    return _execute_adapter_operation(
        provider=provider,
        operation="prepare_payment",
        payload=payment_data,
        method_name="prepare_payment",
        created_by=created_by,
    )


def send_notification(
    *,
    provider,
    recipient,
    message,
    channel=None,
    metadata=None,
    created_by=None,
) -> IntegrationResult:
    payload = {
        "recipient": recipient,
        "message": message,
        "channel": channel or provider.provider_type,
        "metadata": metadata or {},
    }
    return _execute_adapter_operation(
        provider=provider,
        operation="send_notification",
        payload=payload,
        method_name="send_notification",
        created_by=created_by,
    )


def check_license(*, provider, license_data, created_by=None) -> IntegrationResult:
    return _execute_adapter_operation(
        provider=provider,
        operation="check_license",
        payload=license_data,
        method_name="check_license",
        created_by=created_by,
    )


def queue_offline_sync(*, provider, sync_data, created_by=None) -> IntegrationResult:
    return _execute_adapter_operation(
        provider=provider,
        operation="queue_offline_sync",
        payload=sync_data,
        method_name="queue_offline_sync",
        created_by=created_by,
    )
