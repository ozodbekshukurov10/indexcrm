# MVP Deployment Package

This guide is for local/demo installation on a customer-like machine. It is not a full production installer.

## Required Software

- Python 3.12+
- Node.js with npm
- Docker Desktop, or local PostgreSQL and Redis services
- Git, or a ZIP copy of the project

## Environment Files

Backend:

```powershell
copy .env.example .env
```

Required local database values:

```env
DB_NAME=index
DB_USER=index
DB_PASSWORD=index
DB_HOST=localhost
DB_PORT=5432
DATABASE_URL=postgres://index:index@localhost:5432/index
REDIS_URL=redis://localhost:6379/0
```

Frontend:

```powershell
cd frontend\pos
copy .env.local.example .env.local
```

Required local API URL:

```env
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000/api/v1
```

Do not commit real `.env` or `.env.local` files.

Customer/production values must not reuse local defaults. Before internet exposure, replace `SECRET_KEY`, database/Redis credentials, `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS`, and frontend `NEXT_PUBLIC_API_BASE_URL` with customer-specific values. Use HTTPS origins when TLS is available.

## Start PostgreSQL and Redis

Recommended local/demo command:

```powershell
docker compose up -d db redis
```

If your Docker install uses the legacy Compose binary:

```powershell
docker-compose up -d db redis
```

Start the full Docker stack only when you want Docker to run the backend services too:

```powershell
docker compose up -d
```

Legacy Compose fallback:

```powershell
docker-compose up -d
```

Verify PostgreSQL port `5432`:

```powershell
.\.venv\Scripts\python.exe -c "import socket; s=socket.socket(); s.settimeout(5); print(s.connect_ex(('127.0.0.1',5432)))"
```

Expected result is `0`.

## Backend Setup

Run from the project root:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
copy .env.example .env
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py seed_demo_data
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

`seed_demo_data` is local/demo only. It creates or resets:

- Admin: `admin@example.com` / `Admin12345`
- Cashier: `cashier@example.com` / `Cashier12345`
- Demo store, branch, warehouse, cashdesk/cashbox data, products, stock, active cashier shift, and sample sale data

Manual local admin reset:

```powershell
.\.venv\Scripts\python.exe manage.py shell -c "from django.contrib.auth import get_user_model; User = get_user_model(); user, _ = User.objects.get_or_create(email='admin@example.com', defaults={'role': 'owner', 'is_staff': True, 'is_superuser': True, 'is_active': True}); user.set_password('Admin12345'); user.role='owner'; user.is_staff=True; user.is_superuser=True; user.is_active=True; user.save()"
```

Change the admin password before customer use:

```powershell
.\.venv\Scripts\python.exe manage.py changepassword admin@example.com
```

## Frontend Setup

Run in a second terminal:

```powershell
cd frontend\pos
copy .env.local.example .env.local
npm.cmd install
npm.cmd run dev
```

Use `npm.cmd` on Windows if PowerShell blocks `npm.ps1`.

## Windows Helper Scripts

For a Windows demo/customer machine, use the helper scripts when you want repeatable commands:

```powershell
.\scripts\windows\check-backend.ps1
.\scripts\windows\start-backend.ps1 -Migrate -SeedDemoData
.\scripts\windows\start-frontend.ps1 -Install
.\scripts\windows\backup-postgres.ps1
```

Restore is intentionally separate and requires confirmation:

```powershell
.\scripts\windows\restore-postgres.ps1 -BackupFile ..\index_backups\index-YYYYMMDD-HHMMSS.dump
```

If PowerShell blocks local `.ps1` files, use:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\windows\check-backend.ps1
```

## Local URLs

- Login: `http://127.0.0.1:3001/login`
- POS: `http://127.0.0.1:3001/`
- Dashboard: `http://127.0.0.1:3001/dashboard`
- Backend API root: `http://127.0.0.1:8000/api/v1/`
- Backend health: `http://127.0.0.1:8000/api/v1/health/`
- Backend system status: `http://127.0.0.1:8000/api/v1/system/status/`
- Swagger docs: `http://127.0.0.1:8000/api/docs/`

## MVP Demo Checklist

1. Open backend health and API docs.
2. Open the frontend login page.
3. Log in as cashier for POS or admin for dashboard.
4. Confirm password show/hide works.
5. Open POS and confirm branch, warehouse, and active cashier shift.
6. Search, scan, or type SKU/barcode and press Enter to add a product.
7. Update quantity and complete checkout.
8. Open receipt preview and use browser print.
9. Open dashboard, products, inventory, sales, finance, and reports.
10. Confirm sales data appears after seed data or a completed POS sale.

## Health and Readiness

- `GET /api/v1/health/` checks lightweight backend health.
- `GET /api/v1/system/status/` reports database/cache status plus environment metadata.
- If health fails, confirm PostgreSQL and Redis are running before debugging the frontend.
- Frontend connectivity depends on `NEXT_PUBLIC_API_BASE_URL`.

## Production Safety Notes

Before any real customer production deployment:

- Use `DJANGO_SETTINGS_MODULE=config.settings.production`.
- Set `DEBUG=False`.
- Replace `SECRET_KEY` with a private value of at least 50 characters.
- Set explicit `ALLOWED_HOSTS`; never use `*`.
- Set HTTPS frontend origins in `CORS_ALLOWED_ORIGINS` and `CSRF_TRUSTED_ORIGINS`.
- Keep `CORS_ALLOW_ALL_ORIGINS=False`.
- Replace local/default PostgreSQL and Redis credentials.
- Confirm frontend `NEXT_PUBLIC_API_BASE_URL` points to the real backend API URL.
- Set `SECURE_SSL_REDIRECT=True`, `SESSION_COOKIE_SECURE=True`, and `CSRF_COOKIE_SECURE=True` when HTTPS is available.
- Use private PostgreSQL and Redis credentials.
- Run `python manage.py collectstatic --noinput` and serve static/media files safely.
- Store backups outside the project folder and test restore before updates.
- Change all demo passwords.
- Put the backend behind HTTPS/reverse proxy before internet exposure.
- Run `python manage.py check --deploy --settings=config.settings.production` and review all `index.E*` / `index.W*` messages before handover.

## Troubleshooting

- PostgreSQL port check returns non-zero: run `docker compose up -d db redis`, or `docker-compose up -d db redis` on legacy Docker installs.
- Wrong DB user/password: align `.env`, `DATABASE_URL`, and Docker `POSTGRES_*` values.
- Migrations hang: PostgreSQL is not reachable.
- Frontend cannot find `package.json`: run commands from `frontend\pos`.
- PowerShell blocks npm: use `npm.cmd install` and `npm.cmd run dev`.
- Login says `Failed to fetch`: start Django and confirm `NEXT_PUBLIC_API_BASE_URL`.
- CORS/API mismatch: align frontend URL, `CORS_ALLOWED_ORIGINS`, and `CSRF_TRUSTED_ORIGINS`.

## MVP Limitations

- No real fiscal printer integration.
- No real payment provider integration.
- No real SMS/Telegram integration.
- No desktop installer yet.
- No service manager or auto-start installer yet.
- Backup/restore commands exist, but automatic backups still need customer-specific setup.

Before a real customer pilot, also run:

- `docs/PILOT_CHECKLIST.md`
- `docs/BACKUP_AND_RECOVERY.md`
- `docs/HARDWARE_PILOT.md`
