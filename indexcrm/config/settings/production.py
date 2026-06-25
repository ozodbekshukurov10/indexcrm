# ruff: noqa: F403, F405
from django.core.exceptions import ImproperlyConfigured

from config.settings.base import *  # noqa: F403

SECRET_KEY = env("SECRET_KEY")  # noqa: F405
DEBUG = False
ENVIRONMENT = env("ENVIRONMENT", default="production")  # noqa: F405
IS_PRODUCTION = True
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")  # noqa: F405

if (
    not SECRET_KEY
    or SECRET_KEY == "unsafe-local-development-key"
    or len(SECRET_KEY) < 50
):
    raise ImproperlyConfigured(
        "Production SECRET_KEY must be set to a strong value of at least 50 characters."
    )

if not ALLOWED_HOSTS or "*" in ALLOWED_HOSTS:
    raise ImproperlyConfigured("Production ALLOWED_HOSTS must be explicit.")

SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)  # noqa: F405
SESSION_COOKIE_SECURE = env.bool("SESSION_COOKIE_SECURE", default=True)  # noqa: F405
CSRF_COOKIE_SECURE = env.bool("CSRF_COOKIE_SECURE", default=True)  # noqa: F405
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = env.bool("CSRF_COOKIE_HTTPONLY", default=True)  # noqa: F405
SESSION_COOKIE_SAMESITE = env("SESSION_COOKIE_SAMESITE", default="Lax")  # noqa: F405
CSRF_COOKIE_SAMESITE = env("CSRF_COOKIE_SAMESITE", default="Lax")  # noqa: F405
SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=31536000)  # noqa: F405
SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool(
    "SECURE_HSTS_INCLUDE_SUBDOMAINS", default=True
)  # noqa: F405
SECURE_HSTS_PRELOAD = env.bool("SECURE_HSTS_PRELOAD", default=True)  # noqa: F405
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = env(
    "SECURE_REFERRER_POLICY", default="same-origin"
)  # noqa: F405
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[])  # noqa: F405

LOGGING["handlers"]["console"]["formatter"] = env(  # noqa: F405
    "LOG_FORMATTER",
    default="json",
)
