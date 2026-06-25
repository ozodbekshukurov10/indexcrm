# First Customer Pilot Checklist

Use this checklist before saying a customer pilot is ready. The target status is MVP/pilot-ready, not full production-ready.

## Install and Run

- Python 3.12+, Node.js, Docker Desktop or PostgreSQL/Redis are installed.
- `.env.example` has been copied to `.env`.
- `frontend/pos/.env.local.example` has been copied to `frontend/pos/.env.local`.
- PostgreSQL and Redis are running.
- `python manage.py check` passes.
- `.\scripts\windows\check-backend.ps1` passes on the customer/demo machine.
- If local scripts are blocked, the `powershell -ExecutionPolicy Bypass -File .\scripts\windows\check-backend.ps1` fallback works.
- `python manage.py migrate` completes.
- Backend opens at `http://127.0.0.1:8000/api/v1/health/`.
- Frontend opens at `http://127.0.0.1:3001/login`.

## Environment Safety

- Customer admin password has been changed.
- Demo passwords are not used for real customer operation.
- `.env` is not committed or shared publicly.
- `SECRET_KEY`, database password, `ALLOWED_HOSTS`, CORS, and CSRF origins are reviewed.
- `SECRET_KEY` is private and at least 50 characters before production-style use.
- `ALLOWED_HOSTS` is explicit and does not use `*`.
- CORS/CSRF origins match the frontend URL and do not use wildcard/local HTTP values for production.
- PostgreSQL and Redis credentials are customer-specific, not `index` / `index`.
- `python manage.py check --deploy --settings=config.settings.production` has been reviewed before internet exposure.
- For internet exposure, HTTPS/reverse proxy is planned before go-live.

## Demo Data and First Run

- `python manage.py seed_demo_data` was run only for Uzbek demo/pilot data.
- Demo branch, warehouse, products, stock, suppliers, customers, purchases, sales, cashbox/cashdesk, and active shift exist.
- For real customer data, demo products are removed or clearly marked as demo.

## Cashier Login and Shift

- Cashier can log in.
- POS route opens.
- Branch and warehouse are selected.
- Cash desk is selected, or the operator knows an admin must create one for pilot tracking.
- Cashbox handling is understood: checkout uses the backend default cashbox for the selected branch.
- Active cashier shift is visible.
- Checkout is blocked if shift is missing.
- Shift open/close behavior is understood by the operator.

## Product and Barcode

- At least 20 real products are entered or seeded.
- Product search works by name.
- SKU/barcode Enter-to-add works.
- USB scanner acts as keyboard input and sends Enter.
- Repeated scans increase quantity.
- Unknown barcode shows a clear message.

## Admin Dashboard CRUD

- Admin dashboard opens after owner/admin login.
- Products can be created/edited when category and unit setup data exists.
- Product setup errors are understandable if category/unit data is missing.
- Inventory stock adjustment saves only with a positive quantity and reason.
- Customers and suppliers can be created/edited with required contact fields.
- Finance cashboxes can be created/edited when a branch exists.
- Sales, reports, finance, and cashier activity pages show data or clear loading/error/empty states.

## POS Checkout

- Quantity increase/decrease works.
- Cash payment works.
- Card/mixed payment labels are understood as MVP placeholders unless real provider is integrated.
- Insufficient stock shows a clear error.
- Permission/branch/warehouse errors are understandable.
- Sale appears in dashboard sales after checkout.

## Receipt Print

- Receipt preview opens after successful checkout.
- Browser print opens.
- Receipt printer is visible to Windows/browser.
- 80mm paper output is readable.
- Browser headers/footers are disabled.
- Receipt includes receipt number, date/time, cashier, items, totals, paid amount, debt when present.

## Offline Sale

- Stop backend or disconnect network.
- Complete a test sale and confirm it is saved locally, not silently dropped.
- Offline queue shows pending/failed/sending/sent counts.
- Offline queue rows show local reference, total, created time, retry count, last error, and next-step guidance.
- Failed sales remain available for review and manual retry.
- Restart backend/network.
- Manual sync sends the local sale.
- Synced sales show useful server sale/receipt reference data when available.

## Backup

- `docs/BACKUP_AND_RECOVERY.md` has been followed.
- `.\scripts\windows\backup-postgres.ps1` creates a timestamped backup outside the project folder.
- `.\scripts\windows\restore-postgres.ps1` has been tested on a non-production database.
- Database backup finishes successfully.
- Backup file is stored outside the project folder.
- Restore has been tested on a non-production database.
- Customer knows when and where backups are stored.

## Go / No-Go

Go for pilot only if:

- Login, POS sale, receipt print, dashboard, and backup test pass.
- Operator can scan products without developer help.
- Customer accepts browser print as MVP receipt printing.
- Customer accepts no real fiscal printer/payment-terminal integration yet.
- Support contact and rollback/backup plan are agreed.

No-go if:

- Backups have not been tested.
- Checkout or stock updates are unreliable.
- Customer requires fiscal printer/payment integration immediately.
- The machine will be internet-exposed without production security setup.
- Operators cannot complete a sale without developer help.

## Known MVP Limitations

- Browser receipt print only.
- No real fiscal printer integration.
- No real payment terminal integration.
- No automatic background offline sync.
- No desktop installer/service manager yet.
- Manual backup process unless configured separately on the customer machine.
