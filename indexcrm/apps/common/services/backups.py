from dataclasses import dataclass

from django.conf import settings


@dataclass(frozen=True)
class BackupConfiguration:
    storage_path: str
    retention_days: int
    database_url_configured: bool


def get_backup_configuration() -> BackupConfiguration:
    return BackupConfiguration(
        storage_path=getattr(settings, "BACKUP_STORAGE_PATH", "/backups/index"),
        retention_days=getattr(settings, "BACKUP_RETENTION_DAYS", 14),
        database_url_configured=bool(settings.DATABASES.get("default")),
    )


def build_postgres_backup_command(*, output_file: str) -> list[str]:
    return [
        "pg_dump",
        "--format=custom",
        "--no-owner",
        "--no-acl",
        "--file",
        output_file,
    ]


def build_postgres_restore_command(*, backup_file: str) -> list[str]:
    return [
        "pg_restore",
        "--clean",
        "--if-exists",
        "--no-owner",
        "--no-acl",
        backup_file,
    ]
