# Index CRM/ERP Roadmap

Index is a scalable CRM/ERP backend for mini markets and retail stores. The system is designed to grow into a professional multi-branch retail ERP with cashier operations, inventory, purchasing, sales, finance, reports, permissions, security, integrations, and future SaaS support.

## Current Status

- Stage 1: Foundation and architecture - complete
- Stage 2: Core store, product, and inventory system - complete
- Stage 3: Purchase and supplier management - complete
- Stage 4: Sales and cashier system - complete
- Stage 5: Finance, accounting, and cash flow system - complete
- Stage 6: Reports and analytics - complete
- Stage 7: Permissions, accounts and security - complete
- Stage 8: Integration infrastructure - complete
- Stage 9: Real integration preparation layer - complete
- Stage 10: Optimization and production - complete
- Stage 11: POS frontend foundation - complete
- Stage 12: Owner/admin dashboard frontend - complete
- Stage 13: POS frontend polish - complete
- Stage 14: Owner dashboard polish - complete
- Stage 15A: POS offline queue foundation audit and minimal local structure - complete
- Stage 15B: Backend idempotency foundation for replay-safe sale creation/completion - complete
- Stage 15C: Manual offline sale replay with idempotency guard - complete
- Stage 15D: Offline checkout save, queue review, sync recovery, and cross-tab guard polish - complete
- Stage 15E: Offline queue management screen and failed sale detail review - complete
- Stage 15F: Offline conflict review classification, active POS shift enforcement, and backend RBAC scoping - complete
- Stage 15G: Idempotency hardening, backend error mapping, and offline replay safety - complete
- Stage 15H: IndexedDB offline queue migration and safer local persistence - complete
- Stage 15I: Backend health check and smart offline mode detection - complete
- Stage 15J: Safe auto-sync preparation and manual sync reliability polish - complete
- Stage 26: Offline manual-sync reliability finish for MVP/demo - complete
- Stage 27: Local/demo deployment package, env examples, health/readiness docs, and production safety notes - complete
- Stage 28: Hardware pilot preparation for USB barcode scanners and browser receipt printing - complete
- Stage 29: Customer hardening with pilot checklist, backup/recovery guide, and safer customer-facing errors - complete
- Stage 30: Final MVP/pilot audit and readiness classification - complete
- Stage 31: Pilot smoke/static gate and critical-fix pass - complete; live DB-backed smoke remains customer-machine/environment dependent
- Stage 32: Final MVP/customer pilot setup pack and handover documentation - complete
- Stage 33: Final code-only readiness audit and safe self-contained fixes - complete
- Stage 34: POS branch, warehouse, cash desk, and shift readiness UX polish - complete
- Stage 35: Windows run/test/backup/restore helper scripts and docs - complete
- Stage 36: Admin/dashboard CRUD polish for pilot-facing owner workflows - complete
- Stage 37: Offline queue review and conflict/failure explanation polish - complete
- Stage 38: Test coverage and regression safety pass for MVP/pilot flows - complete
- Stage 39: Production settings validation and security warnings - complete
- Stage 40: Final sellable MVP audit and readiness classification - complete
- Stage 41A: Uzbek demo data pack and practical frontend localization polish - complete
- Stage 16A: Barcode scanner Enter-to-add foundation - complete
- Stage 16B/16C: Receipt/check preview and browser print preparation - partial

## Current Frontend Status

- Frontend workspace: `frontend/pos`
- Stack: Next.js, TypeScript, Tailwind CSS, Zustand, React Query
- POS route: `/`
- Owner/admin dashboard route: `/dashboard`
- Dashboard pages: overview, sales, products, inventory, customers, suppliers, finance, reports, cashier activity, profile/settings
- API integration layer exists for products, customers, sales, cashier shifts, reports, inventory, finance, suppliers, and accounts
- Frontend foundations include login, protected routes, POS polish, dashboard polish, barcode/SKU Enter-to-add, receipt preview, and browser print preparation.
- Stage 15A adds the first offline queue foundation: typed local pending-sale records, network status detection, and a POS sync status indicator.
- Stage 15B adds backend sale idempotency keys and idempotent repeated completion so future offline replay can avoid duplicate stock, finance, and receipt effects.
- Stage 15C adds guarded manual replay for locally queued pending/failed sales using the stored idempotency key.
- Stage 15D adds explicit offline checkout saving, compact local queue review, failed-sale retry visibility, stale syncing recovery, and a localStorage sync lock for multi-tab safety. Automatic background sync, PWA caching, IndexedDB, and advanced conflict resolution are still pending.
- Stage 15E adds `/dashboard/offline-queue` for local queue review, summary cards, filtering/sorting, failed sale detail inspection, selected/all manual retry, stale recovery, key/reference copy, and synced-only cleanup.
- Stage 15F adds active cashier shift enforcement for checkout, backend branch/store scoping for operational APIs, manager-level finance/report access, and offline failed-sale classification for stock, product, shift, permission, validation, backend, and unknown failures.
- Stage 15G adds sale idempotency payload fingerprints, duplicate-key conflict responses, clearer backend sale error codes, and offline replay mapping for idempotency conflicts.
- Stage 15H makes IndexedDB the primary offline sales queue store, migrates existing localStorage queue records safely, and keeps localStorage as fallback when IndexedDB is unavailable.
- Stage 15I adds smart POS connectivity state using browser online/offline plus backend health checks, routing checkout and manual sync away from risky backend calls when the API is unavailable.
- Stage 15J strengthens manual replay with last-attempt/error metadata, bounded local sync audit events, lock renewal, stale recovery logging, and a reusable `syncQueueOnce()` helper for future auto-sync. Automatic replay is still disabled.
- Stage 26 improves MVP offline reliability with duplicate local-save prevention by idempotency key, automatic stale `syncing` recovery during queue refresh, clearer manual sync result text, and plain local/sending/sent/review labels in POS and dashboard UI.
- Production packaging, real printer/fiscal devices, and full automatic offline sync are still pending.
- Stage 27 adds a practical local/demo deployment guide in `docs/DEPLOYMENT.md`, a frontend `.env.local.example`, consolidated health/readiness URLs, and explicit production safety notes. It does not add a real installer, desktop app, cloud deployment, or external integrations.
- Stage 28 improves scanner readiness with focused scan handling, immediate duplicate Enter suppression, clearer scanned-code errors, receipt-style browser print CSS, and a hardware pilot checklist in `docs/HARDWARE_PILOT.md`. Real ESC/POS, fiscal printer, payment terminal, and desktop wrapper work remain future-only.
- Stage 29 adds `docs/PILOT_CHECKLIST.md` and `docs/BACKUP_AND_RECOVERY.md`, clarifies MVP/pilot readiness, and removes a few raw technical messages from customer-facing login, dashboard, cashier shift, and checkout errors. It does not claim full production readiness.
- Stage 30 records the final MVP/pilot readiness audit after Stages 23-29 and keeps production-only gaps separate from demo/pilot gaps.
- Stage 31 reruns the backend/frontend static gates and code-level pilot flow audit. No critical code blocker was found. Live end-to-end testing still requires PostgreSQL/Redis or Docker Desktop to be running on the pilot machine.
- Stage 32 adds `docs/PILOT_HANDOVER.md`, links the final setup pack from README, and freezes the current status as MVP/pilot-focused rather than production-ready.
- Stage 33 fixes only code/docs items that do not require live PostgreSQL/Docker, customer hardware, providers, or production secrets: frontend build-root config, backup command consistency, and stale status wording.
- Stage 34 adds a clearer POS session readiness summary, branch/warehouse/cash desk selection, active-shift next-step guidance, and offline queue cash desk metadata without changing backend checkout enforcement.
- Stage 35 adds Windows PowerShell helpers for backend/frontend startup, backend checks, tests, timestamped PostgreSQL backups, and confirmed restore commands. It does not add a service manager, scheduler, installer, or production secrets.
- Stage 36 polishes the existing admin/dashboard CRUD surface with clearer setup guard messages, friendlier dashboard error details, stable table rows, and small contact/search accessibility fixes. It does not add new admin modules or destructive delete flows.
- Stage 37 improves manual offline queue review with shared failure guidance, clearer pending/failed/syncing/synced labels, next-step messages, and safer offline-save block wording. It keeps IndexedDB/localStorage storage, manual sync, idempotency, and failed-sale preservation unchanged.
- Stage 38 adds focused backend regression coverage for unauthenticated checkout protection, missing-shift no-write behavior, idempotent API completion stock effects, branch/warehouse mismatch rejection, and stock-conflict preservation. Frontend regression coverage remains typecheck/build because no frontend unit-test framework is configured.
- Stage 39 extends production-only Django checks and docs for weak secrets, debug mode, unsafe hosts, unsafe CORS/CSRF origins, default database/Redis settings, and insecure SSL/cookie settings. It improves detection and warnings only; it does not make the project fully production-ready.
- Stage 40 confirms the project is demo-ready from static/build/test evidence, pilot-ready after live customer-machine DB/hardware/backup smoke, and not fully paid-production-ready until security, backup automation, service management, and real fiscal/payment decisions are handled.
- Stage 41A expands local-first Uzbek demo data for mini-market testing and localizes practical POS/dashboard user-facing text. It keeps API/model identifiers unchanged and does not add a formal i18n framework.

## Current Pilot Readiness

Index is ready for controlled MVP/pilot testing on a local customer-like machine after deployment, demo data, backup, scanner, receipt print, and offline sync checks pass.

### Completed MVP/Pilot Work

- Backend auth/JWT/RBAC foundation, store/catalog/inventory/purchases/sales/cashier/finance/reports modules, health/status endpoints, and focused regression tests for critical POS/RBAC/stock/idempotency paths.
- POS login, protected routes, active shift guidance, branch/warehouse/cash desk selection, product search, barcode/SKU Enter-to-add, checkout, receipt preview, and browser print.
- Demo/first-run seed data for local admin/cashier/manager, Uzbek mini-market branch, warehouse, cash desk/cashbox, 60+ products, stock, suppliers, customers, purchases, completed sales, finance records, active shift, and sample receipt/dashboard data.
- Dashboard/admin MVP for overview, products, stock adjustment, customers, suppliers, sales, finance, reports, and basic CRUD workflows with pilot-facing setup/error states.
- Manual offline queue review/sync with IndexedDB primary storage, localStorage fallback, idempotency, backend health-aware messaging, and conflict next-step guidance.
- Local/demo deployment docs, hardware pilot docs, backup/recovery guide, pilot checklist, production safety warnings, and final handover pack.

### Remaining Before First Real Pilot

- Start Docker Desktop or local PostgreSQL/Redis on the customer/demo machine.
- Run migrations and `python manage.py seed_demo_data`.
- Complete a live DB-backed smoke test: login, POS sale, receipt browser print, dashboard sales visibility, offline local save, and manual sync.
- Test the real USB barcode scanner and real receipt printer with the cashier.
- Complete a backup and restore drill on a non-production database.
- Change demo/admin passwords and review customer-machine `.env` values.

### Remaining Before Paid Production

- Real fiscal printer/payment terminal/legal receipt decisions and integrations.
- Automatic backup scheduling and restore automation.
- Desktop installer/service manager or managed deployment process.
- Internet-facing TLS/reverse proxy deployment automation.
- Customer-specific secret management, monitoring, alerting, and full security audit.
- Full automatic offline background sync and conflict-edit/approval workflow.

### Future Roadmap

- Real fiscal printer/payment terminal integrations.
- SMS/Telegram and other selected external-service integrations.
- Native ESC/POS or desktop/PWA hardware bridge if browser print is not enough.
- Advanced analytics/charts and multi-branch deployment hardening.
- Central licensing/admin panel if the product moves toward managed SaaS/support.

## MVP Stop-Point - Stage 18D

Ready for local MVP testing:

- Local run notes cover PostgreSQL/Docker, backend migrate/admin reset/runserver, frontend `npm.cmd run dev`, login, POS sale, receipt preview, and dashboard smoke testing.
- Login, protected POS/dashboard routes, password show/hide, API base URL defaults, and clearer local connection errors are in place.
- POS supports active cashier shift guidance, product search/SKU/barcode Enter-to-add, checkout, and browser receipt preview/print.
- Owner/admin dashboard pages have practical loading, error, and empty states for MVP review.

Partial or data-dependent:

- Local testing needs branch, warehouse, product, stock, shift, and sales data to make POS and dashboard screens meaningful.
- Receipt printing is browser print preview only.
- Offline queue manual sync is usable for MVP/demo, but full automatic sync and conflict-resolution workflows remain pending.

Next after token reset:

- Demo seed data or fixtures, hardware scanner/printer validation, fiscal/payment integrations, desktop packaging, and final offline sync workflows.

## Stage 20 - Hardware and Integration Preparation

Current MVP scope:

- Browser-based POS.
- Browser receipt preview and print.
- Local PostgreSQL/Docker run path.
- Basic owner/admin dashboard usage.

Future integration boundaries are documented in `docs/integration_preparation.md` for ESC/POS printers, fiscal/tax providers, payment providers, Telegram/SMS notifications, desktop/PWA packaging, and central licensing. Existing backend provider models, mock adapters, masked credentials, integration tasks, sync logs, and webhook placeholders remain the safe staging area for this work.

Stage 20 does not implement live external APIs, fiscalization, payment processing, printer drivers, desktop packaging, or checkout/offline-sync refactors.

## Stage 21 - Security, Backup, and Customer Deployment Hardening

Prepared:

- Local-vs-production environment notes for `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, CORS/CSRF origins, database credentials, static/media storage, and frontend API URL.
- Local demo admin warnings and password change/reset commands.
- PostgreSQL backup/restore examples and small-store backup policy.
- Customer deployment checklist and common troubleshooting notes.

Still required before real production sale:

- Customer-specific secret management, TLS/proxy setup, backup restore drill, production security review, monitoring/alerting setup, and installer/service automation.

## Known Pending Items

- Full shift-management workflows beyond the current POS open/select and readiness guidance
- Real barcode scanner workflow testing on hardware
- Real receipt printer and fiscal/check integration
- Advanced chart rendering for dashboard analytics
- Failed-sale edit/approval workflow after classified conflict review
- Automatic offline queue replay after a conflict edit/approval workflow
- Real external integrations with fiscal/check, payment, Telegram/SMS, and licensing systems
- Desktop packaging for local cashier terminals
- Central licensing/admin panel and SaaS administration layer

## Next Roadmap Order

1. Failed-sale conflict edit/approval workflow
2. Real receipt printer and fiscal/check workflow
3. Real integrations
4. Desktop packaging
5. Central licensing admin panel

## Updated Enterprise Direction

Index will include an enterprise account and profile management infrastructure. This work is planned mainly for Stage 7 and Stage 8 so it does not interrupt the current business-domain build order.

## Stage 5 - Finance, Accounting, and Cash Flow System

Goal: create financial tracking for real daily operations.

Implemented scope:

- Cashboxes and current balances
- Immutable cash transaction history
- Expenses and expense categories
- Income tracking
- Sale, purchase payment, refund, and debt payment cashflow integration
- Cashbox transfers and adjustments
- Customer and supplier debt selectors
- Profit and cashflow selectors
- Daily cashier closing workflow
- Cashier and branch financial analytics

## Stage 6 - Reports and Analytics

Goal: generate business analytics and operational reports.

Implemented scope:

- Daily sales reports
- Monthly sales reports
- Profit reports
- Expenses reports
- Inventory reports
- Best-selling products
- Low stock reports
- Customer and supplier debt reports
- Cashier performance reports
- Dashboard summary
- Excel export for monthly sales, monthly profit, inventory, and debt reports

## Updated Stage 7 - Permissions, Accounts and Security

Goal: build enterprise-level identity, profile, permission, and security infrastructure.

Implemented scope:

- User profile records with avatar, employee code, position, branch assignment, preferences, and employee status
- Custom RBAC models for roles, permissions, permission groups, and branch-scoped role assignments
- Owner/admin protected account, RBAC, security history, audit log, and installation placeholder APIs
- Audited JWT login success and failure tracking
- Account session records and logout-all session marker
- Audit log services and hooks for product, stock, sale, purchase, refund, and finance operations
- Local installation/license placeholder model for future central admin infrastructure

Professional profile system:

- Profile image/avatar
- First name and last name
- Username
- Phone number and email
- Employee code
- Position/job title
- Branch assignment
- Biography/about section
- Language preferences
- Timezone preferences
- Dark/light theme settings
- Notification preferences

Employee management:

- Employee status
- Active/inactive employees
- Branch transfer history
- Employee salary placeholder
- Working schedule placeholder
- Shift history
- Attendance placeholder
- Employee notes

Account security:

- Password change
- Password history
- Login history
- Failed login attempts
- Device/session tracking
- Active sessions
- Logout all devices
- IP logging
- Browser/device logging
- Two-factor authentication structure
- OTP placeholder support

Activity and audit logs:

- User activity logs
- CRUD action tracking
- Sale and purchase activity tracking
- Inventory activity logs
- Admin actions
- Suspicious activity tracking

Advanced RBAC:

- Dynamic roles
- Custom permissions
- Permission groups
- Branch-based permissions
- Cashier-only permissions
- Manager dashboards
- Super admin permissions
- API permission layers

Personal dashboards:

- Personal statistics
- Cashier performance
- Sales statistics
- Recent activities
- Assigned tasks placeholder
- Personal reports

## Updated Stage 8 - Integration Infrastructure

Goal: prepare event, notification, webhook, and secure credential infrastructure for future integrations.

Implemented scope:

- Integration providers for fiscal/check, receipt printer, payments, Telegram, SMS, offline sync, and central licensing placeholders
- Integration credentials with masked API/admin output
- Sync logs for future async synchronization and retry history
- Webhook event logging placeholders
- Integration task queue placeholders with retry status updates
- External mappings between local records and future remote entities
- Placeholder client classes for receipt printers, messaging, offline sync, and central licensing check-in

Future scope:

- Notification infrastructure
- In-app notifications
- Telegram notification placeholders
- Email notification placeholders
- Low stock alerts
- Cashier alerts
- Shift close alerts
- Debt reminders
- Webhook/event system
- Async notification queues
- Audit streaming
- Integration credential encryption

## Stage 9 - Real Integration Preparation Layer

Goal: prepare safe adapter/service structure for future real integrations without connecting live APIs.

Implemented scope:

- Base integration adapter interfaces for fiscal, receipt printer, marketplace, payment, notification, offline sync, and licensing categories
- Mock/test adapters for fiscal/check, receipt printer, payment providers, Telegram, SMS, offline sync, and central licensing check-in
- Service methods for sending receipts, printing receipts, syncing orders and stock, preparing payments, sending notifications, checking licenses, and queueing offline sync payloads
- Outbound adapter attempts logged through integration tasks and sync logs
- Inbound webhook attempts still logged through webhook events
- No real API keys, live network calls, fiscal providers, payment providers, or external account connections

## Stage 10 - Optimization and Production

Goal: prepare the system for real production usage.

Implemented scope:

- Performance optimization
- Query optimization
- Production settings hardening
- Secure headers and production checks
- Throttling configuration placeholders
- Structured JSON logging
- Health and system status checks
- Backup and restore service placeholders
- CI/CD validation workflow
- Deployment and environment documentation
- Security hardening

## Stage 11 - POS Frontend Foundation

Goal: create the first MVP cashier POS frontend foundation.

Implemented scope:

- Next.js, TypeScript, Tailwind CSS, Zustand, and React Query scaffold
- Full-screen cashier layout optimized for monoblock-style POS use
- Barcode input, product search, cart, quantity controls, item removal, subtotal, and total
- Customer selection, cashier session state, payment panel, and completed sale flow
- Cash, card, and mixed payment UI paths
- Receipt preview with print placeholder
- API services for products, customers, sales, and cashier shifts
- Local POS state stores for cart, customer, and cashier session
- No offline mode, real printer integration, or live fiscal integration yet

## Stage 12 - Owner/Admin Dashboard Frontend

Goal: create a responsive owner/admin dashboard for desktop and mobile monitoring.

Implemented scope:

- Responsive dashboard layout with desktop sidebar and mobile bottom navigation
- Dashboard overview, sales, products, inventory, customers, suppliers, finance, reports, cashier activity, and profile/settings pages
- Widgets for today sales, today profit, total expenses, debts, low stock, best-selling products, recent sales, and cashbox summary
- API services and React Query hooks for reports, sales, inventory, finance, customers, suppliers, accounts, and cashier shifts
- Reusable dashboard components: StatCard, DataTable, DateFilter, ChartPlaceholder, EmptyState, LoadingState, and SectionHeader
- No offline mode, real integrations, or advanced chart rendering yet

## Long-Term Architecture Goals

Index should remain scalable and modular for:

- Mobile app support
- Web dashboard support
- AI analytics
- Cloud synchronization
- Real-time cashier monitoring
- SaaS support
- Multi-branch retail operations
