from datetime import timedelta
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env(
    DEBUG=(bool, False),
    PASSWORD_MIN_LENGTH=(int, 12),
    ACCESS_TOKEN_MINUTES=(int, 30),
    REFRESH_TOKEN_DAYS=(int, 7),
    USER_THROTTLE_RATE=(str, "1000/hour"),
    ANON_THROTTLE_RATE=(str, "100/hour"),
    BACKUP_RETENTION_DAYS=(int, 14),
)
env_file = BASE_DIR / ".env"
if env_file.exists():
    environ.Env.read_env(env_file)

SECRET_KEY = env("SECRET_KEY", default="unsafe-local-development-key")
DEBUG = env.bool("DEBUG", default=False)
ENVIRONMENT = env("ENVIRONMENT", default="local")
APP_VERSION = env("APP_VERSION", default="0.1.0")
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "corsheaders",
    "rest_framework",
    "rest_framework_simplejwt",
    "drf_spectacular",
]

LOCAL_APPS = [
    "apps.common",
    "apps.accounts",
    "apps.stores",
    "apps.catalog",
    "apps.inventory",
    "apps.purchases",
    "apps.sales",
    "apps.cashier",
    "apps.finance",
    "apps.reports",
    "apps.integrations",
    "apps.ai_assistant",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": env.db(
        "DATABASE_URL",
        default="postgres://index:index@localhost:5432/index",
    )
}

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": env("REDIS_URL", default="redis://localhost:6379/0"),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": env.int("PASSWORD_MIN_LENGTH")},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Tashkent"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "accounts.User"
JWT_SIGNING_KEY = env("JWT_SIGNING_KEY", default="") or SECRET_KEY
JWT_AUDIENCE = env("JWT_AUDIENCE", default="") or None
JWT_ISSUER = env("JWT_ISSUER", default="") or None

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "apps.common.pagination.DefaultPageNumberPagination",
    "DEFAULT_THROTTLE_CLASSES": (
        "rest_framework.throttling.UserRateThrottle",
        "rest_framework.throttling.AnonRateThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {
        "user": env("USER_THROTTLE_RATE"),
        "anon": env("ANON_THROTTLE_RATE"),
    },
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=env.int("ACCESS_TOKEN_MINUTES")),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=env.int("REFRESH_TOKEN_DAYS")),
    "AUTH_HEADER_TYPES": ("Bearer",),
    "ALGORITHM": env("JWT_ALGORITHM", default="HS256"),
    "SIGNING_KEY": JWT_SIGNING_KEY,
    "AUDIENCE": JWT_AUDIENCE,
    "ISSUER": JWT_ISSUER,
    "LEEWAY": env.int("JWT_LEEWAY_SECONDS", default=0),
    "UPDATE_LAST_LOGIN": env.bool("JWT_UPDATE_LAST_LOGIN", default=True),
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Index CRM/ERP API",
    "DESCRIPTION": "Backend API for retail CRM/ERP operations.",
    "VERSION": "0.1.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "ENUM_NAME_OVERRIDES": {
        "PaymentMethod": "apps.purchases.models.PaymentMethod",
        "SalePaymentMethod": "apps.sales.models.SalePaymentMethod",
    },
}

CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[])
CORS_ALLOW_CREDENTIALS = True

CELERY_BROKER_URL = env(
    "CELERY_BROKER_URL", default=env("REDIS_URL", default="redis://localhost:6379/1")
)
CELERY_RESULT_BACKEND = env(
    "CELERY_RESULT_BACKEND",
    default=env("REDIS_URL", default="redis://localhost:6379/2"),
)
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE

BACKUP_STORAGE_PATH = env("BACKUP_STORAGE_PATH", default=str(BASE_DIR / "backups"))
BACKUP_RETENTION_DAYS = env.int("BACKUP_RETENTION_DAYS")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "plain": {
            "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
        },
        "json": {
            "()": "apps.common.logging.JsonFormatter",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "plain",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": env("LOG_LEVEL", default="INFO"),
    },
    "loggers": {
        "django.request": {
            "handlers": ["console"],
            "level": env("DJANGO_REQUEST_LOG_LEVEL", default="ERROR"),
            "propagate": False,
        },
        "django.security": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        "apps": {
            "handlers": ["console"],
            "level": env("APP_LOG_LEVEL", default=env("LOG_LEVEL", default="INFO")),
            "propagate": False,
        },
    },
}
