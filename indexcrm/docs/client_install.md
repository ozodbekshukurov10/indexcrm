# Index MVP Client Installation Guide

This guide is for a local MVP demo or pilot installation on a customer-like Windows machine.

## Required Software

- Python 3.12+
- Node.js with npm
- Docker Desktop, or a local PostgreSQL server
- Git or a ZIP copy of the project

## Local Database

Recommended for MVP testing:

```powershell
docker compose up -d db redis
```

Legacy Compose fallback:

```powershell
docker-compose up -d db redis
```

To start the full Docker stack instead:

```powershell
docker compose up -d
```

Legacy Compose fallback:

```powershell
docker-compose up -d
```

Local PostgreSQL values:

```env
DB_NAME=index
DB_USER=index
DB_PASSWORD=index
DB_HOST=localhost
DB_PORT=5432
DATABASE_URL=postgres://index:index@localhost:5432/index
```

Verify PostgreSQL is accepting connections:

```powershell
.\.venv\Scripts\python.exe -c "import socket; s=socket.socket(); s.settimeout(5); print(s.connect_ex(('127.0.0.1',5432)))"
```

Expected result: `0`.

## Backend Setup

Run from the project root:

```powershell
copy .env.example .env
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py seed_demo_data
```

The seed command creates/resets local demo users, store data, products, stock, an active cashier shift, and one sample completed sale:

- Admin: `admin@example.com` / `Admin12345`
- Cashier: `cashier@example.com` / `Cashier12345`

To reset only the local demo admin account manually:

```powershell
.\.venv\Scripts\python.exe manage.py shell -c "from django.contrib.auth import get_user_model; User = get_user_model(); user, _ = User.objects.get_or_create(email='admin@example.com', defaults={'role': 'owner', 'is_staff': True, 'is_superuser': True, 'is_active': True}); user.set_password('Admin12345'); user.role='owner'; user.is_staff=True; user.is_superuser=True; user.is_active=True; user.save()"
```

Run the backend:

```powershell
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

## Frontend Setup

Run in a second terminal:

```powershell
cd frontend\pos
copy .env.local.example .env.local
npm.cmd install
npm.cmd run dev
```

The local frontend API URL is:

```env
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000/api/v1
```

## URLs

- Login: `http://127.0.0.1:3001/login`
- POS: `http://127.0.0.1:3001/`
- Dashboard: `http://127.0.0.1:3001/dashboard`
- API: `http://127.0.0.1:8000/api/v1/`
- API docs: `http://127.0.0.1:8000/api/docs/`

Local demo logins:

- Admin: `admin@example.com` / `Admin12345`
- Cashier: `cashier@example.com` / `Cashier12345`

These accounts are for local MVP testing only. Change the admin password before any customer installation:

```powershell
.\.venv\Scripts\python.exe manage.py changepassword admin@example.com
```

## MVP Test Checklist

1. Open the backend API/docs URLs.
2. Open the frontend login page.
3. Log in with the local demo cashier for POS, or the demo admin for dashboard.
4. Confirm password show/hide works on the login page.
5. Open POS.
6. Open or select the seeded active cashier shift/session.
7. Search for a seeded product or add it by SKU/barcode Enter.
8. Update cart quantity if needed.
9. Take payment and complete checkout.
10. Open receipt preview and use browser print.
11. Open the dashboard.
12. Check products, inventory, sales, finance, and reports pages.
13. Confirm the sales page reflects the seeded sample sale and any completed test sale.
14. Run a PostgreSQL backup and confirm the dump file is stored outside the project folder.

## Troubleshooting

- PostgreSQL port `5432` returns a non-zero socket result: run `docker compose up -d db redis`, or start your local PostgreSQL service.
- Database login fails: confirm `DATABASE_URL`, `DB_USER`, `DB_PASSWORD`, and Docker `POSTGRES_USER`/`POSTGRES_PASSWORD` match.
- Migrations hang or fail with connection errors: PostgreSQL is not running or the credentials are wrong.
- Frontend package command fails from the project root: run `cd frontend\pos` first.
- Login says `Failed to fetch` or backend is unreachable: start Django on `127.0.0.1:8000` and confirm `NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000/api/v1`.
- CORS/API mismatch: confirm `.env` includes the frontend origin in `CORS_ALLOWED_ORIGINS` and `CSRF_TRUSTED_ORIGINS`.
- PowerShell blocks `npm.ps1`: use `npm.cmd install` and `npm.cmd run dev`.
- Empty dashboard/POS data: run `.\.venv\Scripts\python.exe manage.py seed_demo_data` after migrations.

## MVP Status

Ready for MVP demo:

- Local PostgreSQL/Docker setup
- Login and protected POS/dashboard routes
- Password show/hide
- POS sale flow with active cashier shift
- Receipt preview and browser print
- Dashboard basic usage
- Existing offline queue foundation

Not ready for customer production:

- Real fiscal printer integration
- Real payment integration
- Real SMS/Telegram integrations
- Full desktop installer
- Full automatic backup/restore validation
- Production security audit
- Advanced multi-branch deployment hardening
