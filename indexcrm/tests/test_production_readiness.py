import pytest
from django.test import override_settings
from rest_framework.test import APIClient

from apps.common.checks import production_security_checks
from apps.common.services.backups import (
    build_postgres_backup_command,
    build_postgres_restore_command,
    get_backup_configuration,
)


@pytest.mark.django_db
def test_health_and_system_status_endpoints_are_public():
    client = APIClient()

    health_response = client.get("/api/v1/health/")
    status_response = client.get("/api/v1/system/status/")

    assert health_response.status_code == 200
    assert health_response.data["checks"]["database"] == "ok"
    assert status_response.status_code == 200
    assert status_response.data["checks"]["cache"] == "ok"
    assert "version" in status_response.data
    assert "timestamp" in status_response.data


def test_backup_configuration_and_command_builders():
    config = get_backup_configuration()

    assert config.storage_path
    assert config.retention_days > 0
    assert config.database_url_configured
    assert build_postgres_backup_command(output_file="/tmp/index.dump") == [
        "pg_dump",
        "--format=custom",
        "--no-owner",
        "--no-acl",
        "--file",
        "/tmp/index.dump",
    ]
    assert build_postgres_restore_command(backup_file="/tmp/index.dump") == [
        "pg_restore",
        "--clean",
        "--if-exists",
        "--no-owner",
        "--no-acl",
        "/tmp/index.dump",
    ]


@override_settings(
    IS_PRODUCTION=True,
    DEBUG=True,
    SECRET_KEY="short",
    ALLOWED_HOSTS=["*"],
    CSRF_TRUSTED_ORIGINS=["http://localhost:3001"],
    CORS_ALLOWED_ORIGINS=["http://127.0.0.1:3001"],
    CORS_ALLOW_ALL_ORIGINS=True,
    DATABASES={
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": "index",
            "USER": "index",
            "PASSWORD": "index",
            "HOST": "localhost",
            "PORT": "5432",
        }
    },
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": "redis://localhost:6379/0",
        }
    },
    SECURE_SSL_REDIRECT=False,
    SESSION_COOKIE_SECURE=False,
    CSRF_COOKIE_SECURE=False,
)
@pytest.mark.filterwarnings(
    "ignore:Overriding setting DATABASES can lead to unexpected behavior.:UserWarning"
)
def test_production_security_checks_flag_unsafe_settings():
    issue_ids = {issue.id for issue in production_security_checks(None)}

    assert "index.E001" in issue_ids
    assert "index.E002" in issue_ids
    assert "index.E003" in issue_ids
    assert "index.E004" in issue_ids
    assert "index.W001" in issue_ids
    assert "index.W002" in issue_ids
    assert "index.W003" in issue_ids
    assert "index.W006" in issue_ids
    assert "index.W007" in issue_ids
    assert "index.W008" in issue_ids
    assert "index.W009" in issue_ids
    assert "index.W010" in issue_ids
    assert "index.W011" in issue_ids
    assert "index.W012" in issue_ids


@override_settings(
    IS_PRODUCTION=True,
    DEBUG=False,
    SECRET_KEY="prod-secret-key-with-at-least-fifty-private-characters-12345",
    ALLOWED_HOSTS=["api.index.example"],
    CSRF_TRUSTED_ORIGINS=["https://pos.index.example"],
    CORS_ALLOWED_ORIGINS=["https://pos.index.example"],
    CORS_ALLOW_ALL_ORIGINS=False,
    DATABASES={
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": "index_customer",
            "USER": "index_customer_user",
            "PASSWORD": "private-password",
            "HOST": "db.internal",
            "PORT": "5432",
        }
    },
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": "redis://redis.internal:6379/0",
        }
    },
    SECURE_SSL_REDIRECT=True,
    SESSION_COOKIE_SECURE=True,
    CSRF_COOKIE_SECURE=True,
)
@pytest.mark.filterwarnings(
    "ignore:Overriding setting DATABASES can lead to unexpected behavior.:UserWarning"
)
def test_production_security_checks_allow_hardened_settings():
    assert production_security_checks(None) == []
