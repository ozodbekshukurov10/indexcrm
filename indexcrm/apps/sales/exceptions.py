from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from rest_framework.exceptions import APIException


class SaleErrorCode:
    IDEMPOTENCY_CONFLICT = "idempotency_conflict"
    PERMISSION_DENIED = "permission_denied"
    SCOPE_DENIED = "scope_denied"
    SHIFT_CLOSED_MISSING = "shift_closed_missing"
    STOCK_CONFLICT = "stock_conflict"
    VALIDATION_ERROR = "validation_error"
    UNKNOWN = "unknown"


ERROR_MESSAGES = {
    SaleErrorCode.IDEMPOTENCY_CONFLICT: (
        "This idempotency key was already used for a different sale payload."
    ),
    SaleErrorCode.PERMISSION_DENIED: "Permission denied for this sale operation.",
    SaleErrorCode.SCOPE_DENIED: "Branch, warehouse, or store scope blocked this sale.",
    SaleErrorCode.SHIFT_CLOSED_MISSING: (
        "An active cashier shift is required before checkout."
    ),
    SaleErrorCode.STOCK_CONFLICT: "Stock is not available for this sale.",
    SaleErrorCode.VALIDATION_ERROR: "Backend validation rejected this sale.",
    SaleErrorCode.UNKNOWN: "The sale request failed.",
}


class SaleIdempotencyConflictError(Exception):
    pass


class SaleIdempotencyConflict(APIException):
    status_code = 409
    default_code = SaleErrorCode.IDEMPOTENCY_CONFLICT

    def __init__(self):
        super().__init__(
            {
                "code": SaleErrorCode.IDEMPOTENCY_CONFLICT,
                "message": ERROR_MESSAGES[SaleErrorCode.IDEMPOTENCY_CONFLICT],
                "detail": ERROR_MESSAGES[SaleErrorCode.IDEMPOTENCY_CONFLICT],
            }
        )


class SaleValidationError(APIException):
    status_code = 400
    default_code = SaleErrorCode.VALIDATION_ERROR

    def __init__(self, payload):
        super().__init__(payload)


def stringify_error_detail(detail):
    if detail is None:
        return ""
    if isinstance(detail, str):
        return detail
    if isinstance(detail, list):
        return " ".join(stringify_error_detail(item) for item in detail)
    if isinstance(detail, dict):
        return " ".join(
            f"{key} {stringify_error_detail(value)}"
            for key, value in detail.items()
        )
    return str(detail)


def classify_sale_validation_error(error):
    detail = error.message_dict if hasattr(error, "message_dict") else error.messages
    text = stringify_error_detail(detail).lower()
    if "idempotency" in text:
        return SaleErrorCode.IDEMPOTENCY_CONFLICT
    if any(token in text for token in ("shift", "cashier session", "open shift")):
        return SaleErrorCode.SHIFT_CLOSED_MISSING
    if any(
        token in text
        for token in (
            "stock",
            "reserved",
            "insufficient",
            "negative",
            "available",
        )
    ):
        return SaleErrorCode.STOCK_CONFLICT
    if any(token in text for token in ("scope", "branch", "warehouse", "access")):
        return SaleErrorCode.SCOPE_DENIED
    return SaleErrorCode.VALIDATION_ERROR


def sale_validation_error_payload(error, *, code=None):
    error_code = code or classify_sale_validation_error(error)
    if hasattr(error, "message_dict"):
        payload = dict(error.message_dict)
    else:
        payload = {"detail": error.messages}
    payload["code"] = error_code
    payload["message"] = ERROR_MESSAGES.get(
        error_code,
        ERROR_MESSAGES[SaleErrorCode.UNKNOWN],
    )
    return payload


def raise_sale_validation(error):
    if isinstance(error, SaleIdempotencyConflictError):
        raise SaleIdempotencyConflict() from error
    if isinstance(error, DjangoValidationError):
        raise SaleValidationError(sale_validation_error_payload(error)) from error
    raise serializers.ValidationError(
        {
            "code": SaleErrorCode.UNKNOWN,
            "message": ERROR_MESSAGES[SaleErrorCode.UNKNOWN],
            "detail": str(error),
        }
    ) from error
