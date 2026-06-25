# Index CRM/ERP/POS

Index is a modular Django/DRF and Next.js CRM/ERP/POS for mini markets and retail stores. The current repository supports controlled local MVP/demo and first customer pilot testing; live fiscal, payment, and hardware integrations are intentionally deferred.

## What Is Included

- Django and Django REST Framework
- PostgreSQL-ready database configuration
- Redis cache and Celery worker wiring
- JWT authentication
- Swagger/OpenAPI documentation with drf-spectacular
- UUID-based shared `BaseModel` with timestamps and soft delete
- Custom email-based user model
- Modular app layout for store, catalog, inventory, purchases, sales, finance, reports, and integrations
- Docker Compose stack with web, PostgreSQL, Redis, Celery, Celery Beat, and Nginx
- Placeholder external integration clients and mock adapter layer
- Production settings, JSON logging, health/status checks, CI, and backup/restore documentation
- Next.js POS frontend foundation for cashier workflows
- Responsive owner/admin dashboard frontend for monitoring workflows

## Project Status

Completed stages:

- Stages 1-6: backend foundation, retail core, purchases, sales/cashier, finance, and reports
- Stages 7-10: accounts/RBAC/security, integration infrastructure, safe adapter layer, and production hardening
- Stage 11: POS frontend foundation
- Stage 12: owner/admin dashboard frontend foundation
- Stage 13: POS frontend polish, including login, protected routes, loading/error/empty states, and cart workflow polish
- Stage 14: owner/admin dashboard polish with role-aware navigation, mobile layout, and dashboard states
- Stage 16A: barcode/SKU Enter-to-add scanner workflow foundation
- Stages 23-25: demo seed data, POS operator usability, and admin CRUD MVP
- Stages 26-29: offline manual-sync reliability, deployment package, hardware pilot preparation, and customer hardening
- Stages 30-32: final MVP/pilot audit, pilot smoke/static gate, and final handover pack
- Stages 33-41A: code-only readiness fixes, POS context UX polish, Windows helper scripts, admin/dashboard CRUD polish, offline queue review/conflict polish, regression test coverage, production settings validation warnings, final sellable MVP audit, and Uzbek demo/localization polish

Current frontend status:

- POS cashier screen is available at `/`
- Owner/admin dashboard is available at `/dashboard`
- Frontend uses Next.js, TypeScript, Tailwind CSS, Zustand, and React Query
- API services are prepared for products, customers, sales, cashier shifts, reports, inventory, finance, suppliers, and accounts
- Barcode/SKU scanner-style Enter-to-add is implemented in the POS product search and barcode input flows
- Receipt preview and browser print preparation are implemented after successful sale completion
- Manual offline queue review/sync is implemented with IndexedDB primary storage, localStorage fallback, failure classification, and operator next-step guidance
- Admin CRUD MVP/pilot polish exists for products, stock adjustment, customers, suppliers, and cashboxes

Known pending items:

- Advanced chart rendering beyond the current lightweight dashboard polish
- Automatic offline background sync and conflict-edit/approval workflow
- Real receipt printer and fiscal/check integration
- Real scanner/printer validation on customer hardware
- Real external integrations
- Desktop packaging for local POS usage
- Central licensing/admin panel

Next roadmap order:

1. Customer-machine pilot smoke test with real scanner, receipt printer, backup, and restore drill
2. Production service/installer and backup scheduling
3. Real receipt printer, fiscal/check, and payment workflows
4. Real integrations
5. Desktop packaging and central licensing admin panel

## Quick Start

```bash
cp .env.example .env
docker compose up -d --build
```

For customer-like local MVP setup, use the short guide in `docs/client_install.md`.
For a single practical deployment package guide, see `docs/DEPLOYMENT.md`.
For the final pilot handover, setup pack, and go/no-go summary, see `docs/PILOT_HANDOVER.md`.
For production security and customer deployment hardening, see `docs/production.md`.
For PostgreSQL backup and restore commands, see `docs/backup_restore.md`.
For customer pilot backup/recovery steps, see `docs/BACKUP_AND_RECOVERY.md`.
For first customer go/no-go testing, see `docs/PILOT_CHECKLIST.md`.
For future hardware and external-service boundaries, see `docs/integration_preparation.md`.
For barcode scanner and browser receipt-printer pilot testing, see `docs/HARDWARE_PILOT.md`.

If your Docker installation uses the legacy Compose binary:

```bash
docker-compose up --build
```

The API will be available at:

- API root: `http://localhost:8000/api/v1/`
- Health check: `http://localhost:8000/api/v1/health/`
- System status: `http://localhost:8000/api/v1/system/status/`
- Swagger UI: `http://localhost:8000/api/docs/`
- OpenAPI schema: `http://localhost:8000/api/schema/`

Create a superuser inside the web container:

```bash
docker compose exec web python manage.py createsuperuser
```

## Local Development Without Docker

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
copy .env.example .env
python manage.py check
python manage.py migrate
python manage.py runserver 127.0.0.1:8000
```

Local development expects PostgreSQL and Redis to be reachable through the URLs in `.env`.

## Local Run Order (Backend + POS)

1. Start backend services first: PostgreSQL for `DATABASE_URL`, plus Redis for cache/health checks.

```powershell
docker compose up -d db redis
```

To start the full Docker stack instead:

```powershell
docker compose up -d
```

After activating the venv, verify the local PostgreSQL port with `python -c "import socket; s=socket.socket(); s.settimeout(5); print(s.connect_ex(('127.0.0.1',5432)))"`.

Local PostgreSQL values for `.env`:

```env
DATABASE_URL=postgres://index:index@localhost:5432/index
DB_NAME=index
DB_USER=index
DB_PASSWORD=index
DB_HOST=localhost
DB_PORT=5432
```

2. From the repo root, run backend setup and server:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python manage.py check
python manage.py migrate
python manage.py seed_demo_data
python manage.py runserver 127.0.0.1:8000
```

3. From `frontend/pos`, run the POS frontend:

```powershell
npm.cmd run dev
```

The POS frontend defaults to `NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000/api/v1`.

For local development only, `seed_demo_data` creates/resets demo users and first-run data:

- Admin: `admin@example.com` / `Admin12345`
- Cashier: `cashier@example.com` / `Cashier12345`
- Manager: `manager@example.com` / `Manager12345`

The demo seed creates Uzbek mini-market sample data: store, branch, warehouse, cash desk/cashbox, active cashier shift, categories, units, brands, 60+ products with barcodes/SKUs, stock, suppliers, customers, purchases, completed sales, and basic finance records. The POS/dashboard UI is Uzbek-localized for MVP/pilot testing where practical.

To create a custom admin instead:

```bash
python manage.py createsuperuser --email admin@example.com
```

Or reset the local example account from Django shell:

```bash
python manage.py shell -c "from django.contrib.auth import get_user_model; User = get_user_model(); user, _ = User.objects.get_or_create(email='admin@example.com', defaults={'role': 'owner', 'is_staff': True, 'is_superuser': True, 'is_active': True}); user.set_password('Admin12345'); user.role='owner'; user.is_staff=True; user.is_superuser=True; user.is_active=True; user.save()"
```

Example local login: `admin@example.com` / `Admin12345`. Do not use this password outside local development.
Before a customer installation, change the admin password with `python manage.py changepassword admin@example.com`.

### MVP Local Run Flow

```powershell
copy .env.example .env
docker compose up -d db redis
.\.venv\Scripts\python.exe -c "import socket; s=socket.socket(); s.settimeout(5); print(s.connect_ex(('127.0.0.1',5432)))"
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py seed_demo_data
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

In a second terminal:

```powershell
cd frontend\pos
copy .env.local.example .env.local
npm.cmd install
npm.cmd run dev
```

Open `http://127.0.0.1:3001/login`, sign in with the local demo cashier for POS or the demo admin for dashboard, test a POS sale at `/`, then test the owner dashboard at `/dashboard`. Backend API/docs are at `http://127.0.0.1:8000/api/v1/` and `http://127.0.0.1:8000/api/docs/`.

### Windows Helper Scripts

For a Windows demo/customer machine, helper scripts are available under `scripts\windows`:

```powershell
.\scripts\windows\check-backend.ps1
.\scripts\windows\start-backend.ps1 -Migrate -SeedDemoData
.\scripts\windows\start-frontend.ps1 -Install
.\scripts\windows\run-tests.ps1 -Frontend -Build
.\scripts\windows\backup-postgres.ps1
.\scripts\windows\restore-postgres.ps1 -BackupFile ..\index_backups\index-YYYYMMDD-HHMMSS.dump
```

The restore helper requires typing `RESTORE` before it runs. Backups default to `..\index_backups`, outside the project folder.
If PowerShell blocks local scripts, run the same helper through `powershell -ExecutionPolicy Bypass -File`, for example:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\windows\check-backend.ps1
```

### Regression Checks Before Demo/Pilot

Run these before a demo build or customer pilot handover:

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe -m pytest
cd frontend\pos
npm.cmd run typecheck
npm.cmd run build
```

Windows helper equivalent:

```powershell
.\scripts\windows\run-tests.ps1 -Frontend -Build
```

### Production Safety Check

Index is still MVP/pilot-focused, not fully production-ready. Before internet exposure or paid production use, set customer-specific production values in `.env`, then run:

```powershell
$env:DJANGO_SETTINGS_MODULE="config.settings.production"
.\.venv\Scripts\python.exe manage.py check --deploy --settings=config.settings.production
```

Production checks warn/fail for unsafe `SECRET_KEY`, `DEBUG`, wildcard/empty `ALLOWED_HOSTS`, wildcard/local/non-HTTPS CORS/CSRF origins, default database credentials, local Redis URLs, and insecure SSL/cookie settings.

### MVP Test Checklist

- Backend health/API/docs open: `http://127.0.0.1:8000/api/v1/` and `http://127.0.0.1:8000/api/docs/`.
- Frontend opens: `http://127.0.0.1:3001/`.
- Uzbek demo data exists after `python manage.py seed_demo_data`.
- Login works, including password show/hide, with `admin@example.com` or `cashier@example.com`.
- POS opens for `cashier@example.com`, the seeded branch, warehouse, cash desk, and active shift are visible, and product search/SKU/barcode Enter-to-add works with seeded products.
- Checkout completes and receipt preview/print opens.
- Dashboard opens, including products, inventory, and sales basic pages.

### Sellable MVP Demo Flow

Backend terminal:

```powershell
cd C:\Users\Excalibur\Documents\indexcrm
docker compose up -d db redis
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py seed_demo_data
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

Frontend terminal:

```powershell
cd C:\Users\Excalibur\Documents\indexcrm\frontend\pos
npm.cmd install
npm.cmd run dev
```

Demo checklist:

1. Open `http://127.0.0.1:3001/login` and sign in with `cashier@example.com` / `Cashier12345` for POS, or `admin@example.com` / `Admin12345` for dashboard.
2. Confirm password show/hide works.
3. Open dashboard and verify sales, products, and inventory pages load with data or clear empty states.
4. Open POS at `/`, confirm the Branch, Warehouse, and Cash desk selectors default to the seeded records, then open or select the seeded active shift.
5. Search a product or scan/type SKU/barcode and press Enter to add it.
6. Update cart quantity, choose payment, and complete checkout.
7. Confirm receipt preview opens, then use the browser `Print` button.
8. Return to dashboard sales/report pages and confirm the completed sale appears after local data exists.

Demo prerequisites and limitations:

- PostgreSQL must be running on port `5432`; if not, run `docker compose up -d db redis`.
- Run `python manage.py seed_demo_data` after migrations to create demo branch, warehouse, products, stock, active cashier shift, and a sample completed sale.
- Browser print is MVP/demo only; real ESC/POS and fiscal printing are future work.
- Real payment, fiscal, SMS/Telegram, and desktop installer integrations are not part of this MVP demo.

### MVP Installation Readiness

Ready for MVP/pilot testing: local PostgreSQL/Docker setup, local MVP run, login, POS sale flow, receipt preview/browser print, dashboard basic usage, demo seed data, admin CRUD basics with clear setup/error states, manual offline queue review/sync with conflict guidance, deployment docs, hardware pilot docs, and backup/recovery guidance.

Not production-ready yet: real fiscal printer, real payment integrations, SMS/Telegram integrations, full desktop installer/service manager, automatic backups, full production security audit, full automatic offline sync, and advanced multi-branch deployment hardening.

### Current POS Cashier Test Flow

1. Start PostgreSQL/Redis, run migrations, run `python manage.py seed_demo_data`, and start `python manage.py runserver 127.0.0.1:8000`.
2. Start the POS frontend with `npm.cmd run dev` from `frontend/pos`.
3. Log in at `http://127.0.0.1:3001/login` with `cashier@example.com` / `Cashier12345`.
4. On the POS screen, confirm the Branch, Warehouse, and Cash desk selectors are filled; use the dropdowns if multiple records exist.
5. Open/select the active cashier shift. Checkout stays blocked until branch, warehouse, and active shift are ready; cash desk is shown for terminal setup and pilot tracking.
6. Scan a barcode or type a product name/SKU/barcode and press Enter to add it to the cart.
7. Choose cash/card/mixed payment, complete the sale, then use the receipt preview `Print` button.

### Current Admin Dashboard Test Flow

1. Log in as an owner/admin at `http://127.0.0.1:3001/login`.
2. Open `Dashboard`, then check `Products`, `Inventory`, `Customers`, `Suppliers`, `Sales`, `Finance`, and `Reports`.
3. In `Products`, create or edit a product with category, unit, SKU/barcode, purchase price, sale price, and active status.
4. In `Inventory`, use `Adjust Stock` on an existing stock row to increase/decrease stock with a reason.
5. In `Customers` and `Suppliers`, create or edit contact records.
6. In `Finance`, create or edit cashboxes; balances are changed through sales, income, expense, and adjustment transactions.
7. Return to sales/report pages and confirm the demo sale or newly completed POS sale appears.
8. If a create form is blocked, follow the page message first; products need category/unit setup, and cashboxes need at least one branch.

## POS Frontend

```powershell
cd frontend\pos
copy .env.local.example .env.local
npm.cmd install
npm.cmd run dev
```

The frontend app runs on `http://localhost:3001` and expects the backend API at `NEXT_PUBLIC_API_BASE_URL`.

- POS: `http://localhost:3001/`
- Owner/admin dashboard: `http://localhost:3001/dashboard`

## Architecture Rules

- Put shared model behavior in `apps.common`.
- Put business logic in each app's `services` package.
- Keep views and serializers thin.
- Inherit future database models from `BaseModel`.
- Keep external integrations isolated under `apps.integrations`.
- Keep enterprise account, security, RBAC, audit, and notification infrastructure modular for Stage 7 and Stage 8. See `ROADMAP.md`.

## Core API Endpoints

Store system:

- `api/stores/`
- `api/branches/`
- `api/cashdesks/`

Product system:

- `api/categories/`
- `api/brands/`
- `api/units/`
- `api/products/`
- `api/product-images/`
- `api/barcodes/`

Inventory system:

- `api/warehouses/`
- `api/stocks/`
- `api/stocks/low-stock/`
- `api/stock-movements/`
- `api/inventory-adjustments/`

Purchase system:

- `api/suppliers/`
- `api/supplier-contacts/`
- `api/supplier-payments/`
- `api/purchases/`
- `api/purchases/{id}/confirm/`
- `api/purchases/{id}/cancel/`
- `api/purchase-items/`
- `api/purchase-payments/`

Sales and cashier system:

- `api/customers/`
- `api/customer-payments/`
- `api/sales/`
- `api/sales/{id}/complete/`
- `api/sales/{id}/cancel/`
- `api/sales/{id}/receipt/`
- `api/sale-items/`
- `api/sale-payments/`
- `api/refunds/`
- `api/cashier-shifts/`
- `api/cashier-shifts/{id}/close/`
- `api/cashier-shifts/{id}/totals/`

Finance system:

- `api/cashboxes/`
- `api/cashboxes/{id}/balance/`
- `api/cashboxes/{id}/transfer/`
- `api/cash-transactions/`
- `api/cash-transactions/cashflow-summary/`
- `api/cash-transactions/customer-debts/`
- `api/cash-transactions/supplier-debts/`
- `api/expense-categories/`
- `api/expenses/`
- `api/expenses/statistics/`
- `api/incomes/`
- `api/daily-closings/`
- `api/daily-closings/profit-summary/`
- `api/daily-closings/cashier-performance/`

Reports and analytics:

- `api/reports/dashboard/`
- `api/reports/daily-sales/`
- `api/reports/monthly-sales/`
- `api/reports/profit/`
- `api/reports/expenses/`
- `api/reports/inventory/`
- `api/reports/low-stock/`
- `api/reports/best-selling-products/`
- `api/reports/customer-debts/`
- `api/reports/supplier-debts/`
- `api/reports/cashier-performance/`
- `api/reports/export/monthly-sales/`
- `api/reports/export/monthly-profit/`
- `api/reports/export/inventory/`
- `api/reports/export/debts/`

Accounts, profiles, RBAC, and security:

- `api/accounts/me/`
- `api/accounts/me/profile/`
- `api/accounts/users/`
- `api/accounts/profiles/`
- `api/accounts/permissions/`
- `api/accounts/permission-groups/`
- `api/accounts/roles/`
- `api/accounts/role-assignments/`
- `api/accounts/login-history/`
- `api/accounts/failed-login-attempts/`
- `api/accounts/sessions/`
- `api/accounts/sessions/logout-all/`
- `api/accounts/audit-logs/`
- `api/accounts/installations/`

Integration infrastructure:

- `api/integration-providers/`
- `api/integration-providers/placeholders/`
- `api/integration-credentials/`
- `api/integration-tasks/`
- `api/integration-tasks/{id}/retry/`
- `api/sync-logs/`
- `api/webhook-events/`
- `api/external-mappings/`
