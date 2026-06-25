# Backup and Restore Guide

Index includes backup configuration placeholders and command builders, but does not run backups automatically yet.

## Configuration

Set:

- `BACKUP_STORAGE_PATH=/backups/index`
- `BACKUP_RETENTION_DAYS=14`

Use durable object storage or encrypted volume storage for production backups.

## PostgreSQL Backup

Example manual backup:

```bash
pg_dump --format=custom --no-owner --no-acl --file /backups/index/index-$(date +%Y%m%d%H%M%S).dump "$DATABASE_URL"
```

Windows/local MVP example:

```powershell
pg_dump --format=custom --no-owner --no-acl --file C:\backups\index\index-latest.dump "postgres://index:index@localhost:5432/index"
```

Recommended production policy:

- Daily full database backup.
- For a small store, keep at least 14 daily backups plus an extra backup before updates.
- Additional backups before deployments and migrations.
- Encrypted storage.
- Store backups outside the project folder, preferably on encrypted external storage or managed object storage.
- Retention window aligned with business requirements.
- Restore drill at least once per release cycle.
- Never delete or recreate the local database before confirming a fresh backup exists.

## PostgreSQL Restore

Restore into an empty or intentionally replaceable database:

```bash
pg_restore --clean --if-exists --no-owner --no-acl --dbname "$DATABASE_URL" /backups/index/index-latest.dump
```

Windows/local MVP example:

```powershell
pg_restore --clean --if-exists --no-owner --no-acl --dbname "postgres://index:index@localhost:5432/index" C:\backups\index\index-latest.dump
```

If using a plain SQL dump instead of custom format, restore with:

```powershell
psql "postgres://index:index@localhost:5432/index" -f C:\backups\index\index-latest.sql
```

Before restore:

- Stop web and worker processes.
- Confirm the target database.
- Take a fresh backup of the current database if it still exists.
- Run migrations after restore if the backup came from an older version.

After restore:

- Run `python manage.py check`.
- Verify admin login.
- Verify product, stock, sales, finance, reports, and integration pages.
