from django.conf import settings
from django.core.checks import Error, Warning, register


LOCAL_ORIGIN_PREFIXES = ("http://localhost", "http://127.0.0.1", "http://0.0.0.0")


def _database_setting(name):
    return settings.DATABASES.get("default", {}).get(name, "")


def _redis_location():
    return settings.CACHES.get("default", {}).get("LOCATION", "")


def _has_insecure_origin(origins):
    return any(origin == "*" or origin.startswith(LOCAL_ORIGIN_PREFIXES) for origin in origins)


def _has_non_https_origin(origins):
    return any(origin and not origin.startswith("https://") for origin in origins)


@register()
def production_security_checks(app_configs, **kwargs):
    if not getattr(settings, "IS_PRODUCTION", False):
        return []

    issues = []
    if settings.DEBUG:
        issues.append(
            Error(
                "DEBUG must be disabled in production.",
                id="index.E001",
            )
        )
    if (
        settings.SECRET_KEY == "unsafe-local-development-key"
        or len(settings.SECRET_KEY) < 50
    ):
        issues.append(
            Error(
                "Production SECRET_KEY must be strong and must not use the local default.",
                id="index.E002",
            )
        )
    if not settings.ALLOWED_HOSTS or "*" in settings.ALLOWED_HOSTS:
        issues.append(
            Error(
                "Production ALLOWED_HOSTS must list explicit hostnames.",
                id="index.E003",
            )
        )
    if not getattr(settings, "CSRF_TRUSTED_ORIGINS", []):
        issues.append(
            Warning(
                "Production CSRF_TRUSTED_ORIGINS is empty. Add the HTTPS frontend/admin origins that submit requests.",
                id="index.W004",
            )
        )
    if not getattr(settings, "CORS_ALLOWED_ORIGINS", []):
        issues.append(
            Warning(
                "Production CORS_ALLOWED_ORIGINS is empty. Add the HTTPS frontend origins that call the API.",
                id="index.W005",
            )
        )
    if getattr(settings, "CORS_ALLOW_ALL_ORIGINS", False):
        issues.append(
            Error(
                "Production CORS_ALLOW_ALL_ORIGINS must be disabled.",
                id="index.E004",
            )
        )
    if _has_insecure_origin(getattr(settings, "CSRF_TRUSTED_ORIGINS", [])):
        issues.append(
            Warning(
                "Production CSRF_TRUSTED_ORIGINS includes wildcard or local HTTP origins.",
                id="index.W006",
            )
        )
    if _has_insecure_origin(getattr(settings, "CORS_ALLOWED_ORIGINS", [])):
        issues.append(
            Warning(
                "Production CORS_ALLOWED_ORIGINS includes wildcard or local HTTP origins.",
                id="index.W007",
            )
        )
    if _has_non_https_origin(getattr(settings, "CSRF_TRUSTED_ORIGINS", [])):
        issues.append(
            Warning(
                "Production CSRF_TRUSTED_ORIGINS should use HTTPS origins.",
                id="index.W008",
            )
        )
    if _has_non_https_origin(getattr(settings, "CORS_ALLOWED_ORIGINS", [])):
        issues.append(
            Warning(
                "Production CORS_ALLOWED_ORIGINS should use HTTPS origins.",
                id="index.W009",
            )
        )
    if _database_setting("USER") in {"", "index", "postgres"} or _database_setting(
        "PASSWORD"
    ) in {"", "index", "postgres"}:
        issues.append(
            Warning(
                "Production database credentials look empty or default/local. Use customer-specific private credentials.",
                id="index.W010",
            )
        )
    if "localhost" in _database_setting("HOST") or _database_setting("HOST") in {
        "",
        "127.0.0.1",
    }:
        issues.append(
            Warning(
                "Production database host looks local. Confirm this is intended for the customer deployment.",
                id="index.W011",
            )
        )
    if "localhost" in _redis_location() or "127.0.0.1" in _redis_location():
        issues.append(
            Warning(
                "Production Redis URL looks local. Confirm Redis is private, reachable, and not an unintended dev default.",
                id="index.W012",
            )
        )
    if not getattr(settings, "SECURE_SSL_REDIRECT", False):
        issues.append(
            Warning(
                "SECURE_SSL_REDIRECT is disabled in production.",
                id="index.W001",
            )
        )
    if not getattr(settings, "SESSION_COOKIE_SECURE", False):
        issues.append(
            Warning(
                "SESSION_COOKIE_SECURE is disabled in production.",
                id="index.W002",
            )
        )
    if not getattr(settings, "CSRF_COOKIE_SECURE", False):
        issues.append(
            Warning(
                "CSRF_COOKIE_SECURE is disabled in production.",
                id="index.W003",
            )
        )
    return issues
