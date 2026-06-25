# Backup and Recovery

This is MVP-level guidance for a first customer pilot. It is not enterprise disaster recovery.

## What Must Be Backed Up

- PostgreSQL database: products, stock, sales, users, shifts, finance, reports.
- Media files under `MEDIA_ROOT` if customer uploads/images are used.
- The active `.env` file, stored separately and securely.
- Deployment notes for the customer machine: install path, ports, admin contact, printer/scanner model notes.

Static files can be regenerated with `python manage.py collectstatic --noinput`; they do not need to be treated like customer data.

## Daily Backup Recommendation

For a small store pilot:

- Take one database backup every day after closing.
- Keep at least 14 daily backups.
- Take an extra backup before migrations, updates, data imports, or customer-machine maintenance.
- Store backups outside the project folder, preferably on encrypted external storage or a secured network/cloud location.
- Never delete or recreate the local database until a fresh backup has been confirmed.

## PostgreSQL Backup

Windows helper script:

```powershell
.\scripts\windows\backup-postgres.ps1
```

By default, the helper reads `.env`, creates a timestamped custom-format dump, and saves it under `..\index_backups`, outside the project folder. You can override settings when needed:

```powershell
.\scripts\windows\backup-postgres.ps1 -BackupDir D:\IndexBackups -Database index -DbUser index -DbHost localhost -DbPort 5432
```

PowerShell/local example:

```powershell
mkdir C:\backups\index
pg_dump --format=custom --no-owner --no-acl --file C:\backups\index\index-latest.dump "postgres://index:index@localhost:5432/index"
```

Timestamped example:

```powershell
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
pg_dump --format=custom --no-owner --no-acl --file "C:\backups\index\index-$stamp.dump" "postgres://index:index@localhost:5432/index"
```

Docker database example:

```powershell
docker compose exec db pg_dump --format=custom --no-owner --no-acl -U index -d index -f /tmp/index-latest.dump
docker cp indexcrm-db-1:/tmp/index-latest.dump C:\backups\index\index-latest.dump
```

Legacy Compose fallback:

```powershell
docker-compose exec db pg_dump --format=custom --no-owner --no-acl -U index -d index -f /tmp/index-latest.dump
```

Container names can differ by Docker version; run `docker ps` if the copy command cannot find the container.

## Media Backup

If media uploads are used:

```powershell
robocopy media C:\backups\index\media /MIR
```

For Docker volumes, copy media from the mounted `media` volume or from the host path used in the deployment.

## PostgreSQL Restore

Restore only to an empty or intentionally replaceable database.

Windows helper script:

```powershell
.\scripts\windows\restore-postgres.ps1 -BackupFile ..\index_backups\index-YYYYMMDD-HHMMSS.dump
```

The restore helper shows a destructive-action warning and requires typing `RESTORE`. Test restore on a non-production database before using it on a customer machine.

```powershell
pg_restore --clean --if-exists --no-owner --no-acl --dbname "postgres://index:index@localhost:5432/index" C:\backups\index\index-latest.dump
```

Plain SQL restore:

```powershell
psql "postgres://index:index@localhost:5432/index" -f C:\backups\index\index-latest.sql
```

After restore:

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py migrate
```

Then verify login, POS sale, inventory, sales, finance, and reports.

## Customer-Machine Failure Recovery

1. Stop backend/frontend services if they are still running.
2. Do not reinstall or delete PostgreSQL before copying the latest available backup.
3. Preserve the current `.env`, project folder, `media`, and PostgreSQL data directory if possible.
4. Install Python, Node.js, PostgreSQL/Docker on the replacement machine.
5. Restore `.env`, media, and PostgreSQL backup.
6. Run migrations and `python manage.py check`.
7. Log in as admin and change any temporary recovery password.
8. Test POS checkout, receipt browser print, dashboard sales, inventory, and backup command again.

## Backup Test Checklist

- Backup command finishes without error.
- Backup file exists and is not zero bytes.
- Backup file is stored outside the project folder.
- Restore command has been tested on a non-production test database.
- Admin login works after restore.
- Latest products, stock, sales, and finance records appear after restore.

## Pilot Limitations

- Backups are manual unless the customer machine adds scheduled tasks.
- No automatic cloud backup is included yet.
- No full disaster-recovery automation is included yet.
- Restore must be tested before relying on this for production.
