# Pilot Handover

This document is the final current-stage handover for the Index CRM/ERP/POS MVP pilot. It is meant for a developer/operator preparing a customer-like local machine for a mini-market demo or first controlled pilot.

## Project Purpose

Index is a Django/DRF backend and Next.js POS/dashboard frontend for small retail stores. The MVP focuses on local login, cashier POS sales, inventory visibility, receipt preview/browser print, dashboard basics, demo data, manual offline queue review, and practical deployment documentation.

## Current Readiness

- MVP demo readiness: about 88%.
- First customer pilot readiness: about 78%, pending live database, hardware, print, and backup smoke tests.
- Paid production readiness: about 55%.

Index is suitable for a controlled local demo or pilot only after the customer machine passes the checklist below. It is not yet a fully production-ready retail system.

## MVP/Pilot Scope

Implemented for the current pilot:

- JWT login with protected POS/dashboard routes.
- Password show/hide on login.
- Demo seed data for local admin, cashier, store, branch, warehouse, products, stock, cashbox/cashdesk, active shift, and sample sale data.
- POS cashier flow with branch/warehouse selection, active shift guidance, product search, barcode/SKU Enter-to-add, cart quantity changes, checkout, and receipt preview/browser print.
- Dashboard basics for products, inventory, sales, finance, reports, customers, suppliers, cashboxes, and admin CRUD MVP with setup/error-state polish.
- Manual offline queue with IndexedDB primary storage, localStorage fallback, retry/review UI, backend health awareness, idempotency support, failure classification, and next-step guidance.
- Deployment, hardware pilot, backup/recovery, and go/no-go documentation.

Not implemented yet:

- Real fiscal printer integration.
- Direct ESC/POS printer driver or native USB/LAN printer discovery.
- Real payment terminal/provider integration.
- Real SMS/Telegram sending.
- Desktop installer/service manager.
- Automatic scheduled backups.
- Full automatic background offline sync and conflict-edit workflow.
- Full production security audit, monitoring, and internet-facing deployment automation.

## Customer Machine Prerequisites

- Windows machine with Python 3.12+, Node.js/npm, Git or a ZIP copy of the project.
- Docker Desktop running, or local PostgreSQL and Redis services running.
- Receipt printer installed in Windows if receipt printing will be tested.
- USB barcode scanner configured in keyboard mode with Enter/CR/LF suffix.

## Backend Startup

Run from the project root:

```powershell
cd C:\Users\Excalibur\Documents\indexcrm
copy .env.example .env
docker compose up -d db redis
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py seed_demo_data
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

If Docker uses the legacy Compose binary:

```powershell
docker-compose up -d db redis
```

Verify PostgreSQL port `5432` before migrations:

```powershell
.\.venv\Scripts\python.exe -c "import socket; s=socket.socket(); s.settimeout(5); print(s.connect_ex(('127.0.0.1',5432)))"
```

Expected result: `0`. A non-zero result usually means PostgreSQL/Docker is not running or the port is blocked.

## Frontend Startup

Run in a second terminal:

```powershell
cd C:\Users\Excalibur\Documents\indexcrm\frontend\pos
copy .env.local.example .env.local
npm.cmd install
npm.cmd run dev
```

The local frontend API URL is:

```env
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000/api/v1
```

Use `npm.cmd` on Windows if PowerShell blocks `npm.ps1`.

## Windows Helper Scripts

For a Windows demo/customer machine, the common commands can be run through helper scripts:

```powershell
.\scripts\windows\check-backend.ps1
.\scripts\windows\start-backend.ps1 -Migrate -SeedDemoData
.\scripts\windows\start-frontend.ps1 -Install
.\scripts\windows\run-tests.ps1 -Frontend -Build
.\scripts\windows\backup-postgres.ps1
.\scripts\windows\restore-postgres.ps1 -BackupFile ..\index_backups\index-YYYYMMDD-HHMMSS.dump
```

Run `restore-postgres.ps1` only after testing restore on a non-production database. It requires typing `RESTORE` before it changes the target database.
If Windows blocks local `.ps1` files, run helpers through `powershell -ExecutionPolicy Bypass -File`, for example:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\windows\check-backend.ps1
```

## Regression Checks Before Handover

Before a demo build or customer pilot handover, run:

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe -m pytest
cd frontend\pos
npm.cmd run typecheck
npm.cmd run build
```

Or use the Windows helper:

```powershell
.\scripts\windows\run-tests.ps1 -Frontend -Build
```

## Production Safety Validation

Before internet exposure or paid production use, set customer-specific production values in `.env`, then run:

```powershell
$env:DJANGO_SETTINGS_MODULE="config.settings.production"
.\.venv\Scripts\python.exe manage.py check --deploy --settings=config.settings.production
```

Review any `index.E*` or `index.W*` output. These checks flag weak secrets, `DEBUG=True`, unsafe hosts, unsafe CORS/CSRF origins, default database/Redis values, and insecure SSL/cookie settings. Passing this check does not replace a full production security audit.

## Demo Credentials

These credentials are created/reset by `python manage.py seed_demo_data` for local demo use only:

- Admin: `admin@example.com` / `Admin12345`
- Cashier: `cashier@example.com` / `Cashier12345`
- Manager: `manager@example.com` / `Manager12345`

The seed command creates Uzbek mini-market demo data for pilot testing: store, branch, warehouse, cash desk/cashbox, active cashier shift, categories, units, brands, 60+ products with SKUs/barcodes, stock, suppliers, customers, purchases, completed sales, and basic finance records. The POS/dashboard UI uses Uzbek user-facing text where practical; API field names and technical identifiers remain unchanged.

Before customer operation, change the admin password:

```powershell
.\.venv\Scripts\python.exe manage.py changepassword admin@example.com
```

## Health URLs

- Login: `http://127.0.0.1:3001/login`
- POS: `http://127.0.0.1:3001/`
- Dashboard: `http://127.0.0.1:3001/dashboard`
- API root: `http://127.0.0.1:8000/api/v1/`
- Health: `http://127.0.0.1:8000/api/v1/health/`
- System status: `http://127.0.0.1:8000/api/v1/system/status/`
- Swagger docs: `http://127.0.0.1:8000/api/docs/`

## POS Login and Cashier Flow

1. Open `http://127.0.0.1:3001/login`.
2. Log in as `cashier@example.com` / `Cashier12345`.
3. Confirm the POS route opens.
4. Confirm branch, warehouse, and cash desk are selected.
5. Confirm the backend cashbox note is visible; sale finance uses the branch default cashbox after checkout.
6. Confirm an active cashier shift is visible, or open/select a shift if the UI prompts for it.
7. Add products by search, SKU, or barcode Enter-to-add.
8. Update quantity and complete checkout.
9. Confirm receipt preview opens and the sale appears in dashboard sales after refresh.

Checkout should stay blocked if branch, warehouse, or active shift is missing.

## Dashboard Admin CRUD Test Flow

1. Log in as `admin@example.com` / `Admin12345`.
2. Open `http://127.0.0.1:3001/dashboard`.
3. Create or edit a product; product setup requires at least one category and unit from demo seed data or admin setup.
4. Adjust stock from an existing inventory row and enter a reason.
5. Create or edit a customer and supplier contact.
6. Create or edit a finance cashbox; cashbox setup requires at least one branch.
7. Confirm sales, reports, finance, and cashier activity pages show data or clear empty/error states.

## Barcode Scanner Test Flow

1. Confirm the scanner is in keyboard mode and sends Enter after the code.
2. Focus the POS barcode field once. Use `F2` to return focus during testing.
3. Scan a seeded product barcode/SKU.
4. Confirm the product is added to the cart.
5. Scan the same item again and confirm quantity increases.
6. Scan several products quickly and confirm they are added safely.
7. Scan an unknown code and confirm the POS shows a friendly not-found message.

## Receipt Browser Print Flow

1. Complete a POS sale.
2. Confirm receipt preview opens.
3. Confirm receipt includes receipt number, date/time, cashier/session info when available, item names, quantities, unit prices, line totals, subtotal, paid amount, debt when present, and final total.
4. Click `Print`.
5. Select the installed receipt printer in the browser print dialog.
6. Test 80mm paper first; disable browser headers/footers if available.

Browser print is the MVP fallback. Direct ESC/POS and fiscal printing are future work.

## Offline Sale and Manual Sync Flow

1. Start with backend and frontend running.
2. Stop the backend or disconnect the network.
3. Complete a small POS sale and confirm it is saved locally, not silently dropped.
4. Open the offline queue/review UI and confirm pending/failed/sending/sent counts, local reference, retry count, last error, and next-step guidance are understandable.
5. Restart backend/network.
6. Run manual sync.
7. Confirm synced sales show server sale/receipt references and failed sales remain available for review.

Automatic background sync is not part of the current MVP.

## Backup and Restore Reminder

Before a real pilot:

- Run a PostgreSQL backup using `docs/BACKUP_AND_RECOVERY.md` or `.\scripts\windows\backup-postgres.ps1`.
- Store the backup outside the project folder.
- Test restore on a non-production database.
- Back up media files if product images or uploads are used.

Never delete or recreate the local database until a fresh backup has been confirmed.

## Go / No-Go Rules

Go for first pilot only if:

- Backend health, login, POS checkout, receipt browser print, dashboard sales, offline save/manual sync, and backup test pass on the customer machine.
- Real scanner and receipt printer have been tested with the operator.
- Customer accepts browser print and no real fiscal/payment integration for the MVP pilot.
- Admin password and production-like `.env` values have been changed from demo defaults.
- Rollback/backup plan and support contact are agreed.

No-go if:

- PostgreSQL/Redis cannot run reliably.
- Migrations or `seed_demo_data` fail.
- Checkout, stock update, receipt preview, or dashboard sales are unreliable.
- Backup and restore have not been tested.
- Customer requires fiscal printer or payment terminal integration before pilot.
- The app will be internet-exposed without production security work.

## Support and Rollback Notes

- Take a database backup before updates, imports, migrations, or pilot-day changes.
- Keep a copy of the working `.env`, `frontend/pos/.env.local`, and printer/scanner setup notes.
- For rollback, stop backend/frontend services, restore the latest known-good PostgreSQL backup, restore media if used, rerun `manage.py check` and `manage.py migrate`, then verify login, POS sale, receipt print, dashboard, and backup.
- If the frontend cannot log in, check backend health first, then verify `NEXT_PUBLIC_API_BASE_URL`.
- If migrations hang, check PostgreSQL port `5432` before changing code.

## Known MVP Limitations

- Local/demo deployment is documented, but no installer or service manager is included.
- Browser print only; no direct printer/fiscal driver.
- Cash/card/mixed payment labels are MVP checkout modes, not real payment provider integration.
- Offline queue supports manual review/sync, not full automatic background sync.
- Backup commands are documented, but scheduled backups must be configured on the customer machine.
- Production secrets, TLS/reverse proxy, monitoring, legal fiscal requirements, and customer-specific security review remain required before paid production use.
