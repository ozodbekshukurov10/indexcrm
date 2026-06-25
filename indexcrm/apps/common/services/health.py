from typing import Any

from django.conf import settings
from django.core.cache import cache
from django.db import connections
from django.utils import timezone


def get_health_status() -> tuple[dict[str, Any], int]:
    checks = {
        "database": "ok",
        "cache": "ok",
    }
    http_status = 200

    try:
        with connections["default"].cursor() as cursor:
            cursor.execute("SELECT 1")
    except Exception:
        checks["database"] = "unavailable"
        http_status = 503

    try:
        cache.set("healthcheck", "ok", timeout=5)
        if cache.get("healthcheck") != "ok":
            checks["cache"] = "unavailable"
            http_status = 503
    except Exception:
        checks["cache"] = "unavailable"
        http_status = 503

    payload = {
        "status": "ok" if http_status == 200 else "degraded",
        "checks": checks,
    }
    return payload, http_status


def get_system_status() -> tuple[dict[str, Any], int]:
    health_payload, http_status = get_health_status()
    payload = {
        **health_payload,
        "environment": getattr(settings, "ENVIRONMENT", "unknown"),
        "version": getattr(settings, "APP_VERSION", "0.1.0"),
        "debug": settings.DEBUG,
        "timestamp": timezone.now(),
    }
    return payload, http_status
