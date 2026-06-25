# Production Deployment Guide

This guide prepares Index for production without changing business behavior.

## Settings

Use the production settings module:

```bash
DJANGO_SETTINGS_MODULE=config.settings.production
```

Production requires:

- `SECRET_KEY`: strong value, at least 50 characters.
- `DEBUG=False`
- `ALLOWED_HOSTS`: explicit hostnames only, never `*`.
- `DATABASE_URL`: PostgreSQL connection URL.
- `REDIS_URL`: Redis cache URL.
- `CELERY_BROKER_URL` and `CELERY_RESULT_BACKEND`: Redis or another Celery backend.
- `CORS_ALLOWED_ORIGINS`: dashboard/mobile origins only.
- `CSRF_TRUSTED_ORIGINS`: HTTPS origins that submit unsafe requests.
- `CORS_ALLOW_ALL_ORIGINS=False`
- `SECURE_SSL_REDIRECT=True`, `SESSION_COOKIE_SECURE=True`, and `CSRF_COOKIE_SECURE=True` when HTTPS is available.

Local `.env.example` values are for development only. Before a customer installation, set a private `SECRET_KEY`, replace local database credentials, set explicit customer hostnames/IPs, and use HTTPS origins for CORS/CSRF when TLS is available.

Production system checks fail or warn for:

- weak/local `SECRET_KEY`
- `DEBUG=True`
- empty or wildcard `ALLOWED_HOSTS`
- empty, wildcard, local, or non-HTTPS CORS/CSRF origins
- `CORS_ALLOW_ALL_ORIGINS=True`
- default/local database credentials
- local Redis URLs
- disabled SSL redirect or insecure cookies

## Security

Production settings enable SSL redirect, secure cookies, HSTS, content-type nosniff, strict frame protection, and JSON application logging. Terminating TLS at a proxy is supported with `SECURE_PROXY_SSL_HEADER`.

Recommended proxy requirements:

- Forward `X-Forwarded-Proto`.
- Serve HTTPS only.
- Block direct access to app worker ports.
- Store secrets in the deployment platform, not in committed files.

Static and media files:

- Static files are collected into `STATIC_ROOT` and served by Whitenoise or the front proxy.
- Media files live under `MEDIA_ROOT`; store customer uploads on durable backed-up storage.
- Do not expose private backups, `.env`, or media directories through Nginx/Apache aliases.

## Admin Password Safety

`admin@example.com` / `Admin12345` is a local demo example only. Before installing for a customer, create a customer-specific admin and change the password immediately:

```bash
python manage.py changepassword admin@example.com
```

For local reset only:

```bash
python manage.py shell -c "from django.contrib.auth import get_user_model; User = get_user_model(); user, _ = User.objects.get_or_create(email='admin@example.com', defaults={'role': 'owner', 'is_staff': True, 'is_superuser': True, 'is_active': True}); user.set_password('Admin12345'); user.role='owner'; user.is_staff=True; user.is_superuser=True; user.is_active=True; user.save()"
```

## Customer Deployment Checklist

1. Install Python 3.12+, Node.js, PostgreSQL or Docker, and Git/ZIP project copy.
2. Copy `.env.example` to `.env` and set production/local customer values.
3. Confirm PostgreSQL is running and credentials work.
4. Install backend dependencies and run `python manage.py check`.
5. Run `python manage.py migrate`.
6. Create the customer admin account and change its password.
7. Run backend and frontend services.
8. Test login, POS sale, receipt browser print, dashboard pages, and backup/restore commands.
9. Store `.env` and backups securely.

## Troubleshooting

- PostgreSQL `5432` is not running: start PostgreSQL or run `docker compose up -d db redis`.
- Wrong DB user/password: check `DATABASE_URL`, `DB_USER`, `DB_PASSWORD`, and the Docker `POSTGRES_*` values.
- Migrations hang or fail with connection errors: PostgreSQL is not reachable; verify port `5432` before retrying.
- Frontend cannot find `package.json`: run commands from `frontend/pos`.
- PowerShell blocks `npm.ps1`: use `npm.cmd install` and `npm.cmd run dev`.
- Login says `Failed to fetch`: start Django and confirm `NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000/api/v1`.
- CORS/API mismatch: align `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS`, and the frontend URL.

## Runtime Commands

```bash
python manage.py check --deploy
python manage.py migrate --noinput
python manage.py collectstatic --noinput
gunicorn config.wsgi:application --bind 0.0.0.0:8000
```

For an explicit production-settings validation from a local shell:

```bash
DJANGO_SETTINGS_MODULE=config.settings.production python manage.py check --deploy --settings=config.settings.production
```

On Windows PowerShell:

```powershell
$env:DJANGO_SETTINGS_MODULE="config.settings.production"
.\.venv\Scripts\python.exe manage.py check --deploy --settings=config.settings.production
```

## Monitoring

Public lightweight health endpoints:

- `GET /api/v1/health/`
- `GET /api/v1/system/status/`

Both check database and cache connectivity. The status endpoint also returns environment, app version, debug state, and timestamp.

## Logging

Production uses structured JSON logs by default through `LOG_FORMATTER=json`. Keep application logs on stdout/stderr and let the platform collect them.

Useful variables:

- `LOG_LEVEL=INFO`
- `APP_LOG_LEVEL=INFO`
- `DJANGO_REQUEST_LOG_LEVEL=ERROR`
- `LOG_FORMATTER=json`

## Rate Limits

DRF throttle defaults are prepared through:

- `USER_THROTTLE_RATE=1000/hour`
- `ANON_THROTTLE_RATE=100/hour`

Tune these once real dashboard, mobile, and POS traffic profiles are known.
