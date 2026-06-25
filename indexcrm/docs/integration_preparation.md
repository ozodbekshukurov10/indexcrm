# Stage 20 Integration Preparation

This note documents the safe boundaries for future hardware and external services. Stage 20 does not enable live external API calls.

## Current MVP

- Browser-based POS frontend.
- Browser receipt preview and `window.print()` for paper receipts.
- Local PostgreSQL/Docker run path.
- Basic owner/admin dashboard.
- Existing mock integration providers, masked credentials, outbound task logs, sync logs, and webhook event placeholders in `apps.integrations`.

## Existing Integration Boundary

The backend already contains placeholder provider types for:

- Fiscal/check systems
- Receipt printers
- Payment providers
- Telegram
- SMS
- Offline sync
- Central licensing

Adapter interfaces live under `apps.integrations.adapters.base`, mock adapters under `apps.integrations.adapters.mock`, and dispatch helpers under `apps.integrations.services.adapters`. Real adapters should replace or sit beside the mock adapters without changing POS checkout behavior first.

## Receipt Printer Plan

Current behavior:

- Receipt data is loaded from `GET /api/v1/sales/{id}/receipt/`.
- The POS receipt panel renders the receipt in the browser.
- The `Print` button uses browser printing only.

Future adapter plan:

- Add an ESC/POS adapter behind the existing `ReceiptPrinterAdapter.print_receipt()` boundary.
- Support USB and LAN printer configuration through provider `settings` and masked `IntegrationCredential` records.
- Keep receipt templates compatible between browser print and printer payloads where possible.
- Record print attempts through `IntegrationTask` and `SyncLog`.

## Fiscal/Tax Plan

Do not modify sale models until a real provider contract is selected.

Future flow:

1. Sale is completed locally by existing checkout rules.
2. Fiscal provider receives a fiscalization request with receipt totals, items, taxes, payments, cashier, branch, and receipt number.
3. Provider response returns fiscal status, fiscal receipt number, external ID, QR/link payload if available, and error details if failed.
4. Failed fiscalization should not silently mark a receipt as fiscalized; it should create a retryable integration task and show an operator/admin-visible status.

Provider base URL and non-secret flags should use `IntegrationProvider.base_url` and `settings`. Secrets should use masked `IntegrationCredential` records or environment variables where appropriate.

## Payment Provider Plan

Current behavior:

- Cash/card/mixed payment UI exists for local sale recording.
- No real provider authorization, capture, refund, or terminal integration is active.

Future adapter plan:

- Use `PaymentAdapter.prepare_payment()` for provider-specific initialization.
- Map provider statuses into local states such as pending, authorized, paid, failed, refunded, and cancelled.
- Store provider transaction IDs through external mappings or future payment metadata after the provider contract is known.
- Keep cash checkout working even if provider APIs are down.

## Telegram/SMS Plan

Current behavior:

- Telegram and SMS provider types and mock notification adapters exist.
- `.env.example` includes blank placeholders for `TELEGRAM_BOT_TOKEN`, `SMS_PROVIDER`, and `SMS_API_KEY`.

Future use cases:

- Low stock alerts.
- Daily sales report messages.
- Failed sync or fiscalization warnings.
- Subscription/license warnings after licensing is implemented.

No secrets should be committed. Real sending should be opt-in per provider and branch.

## Desktop/PWA Plan

Current behavior:

- POS is a browser app.
- Offline queue foundations exist, but full automatic offline-first sync is not complete.

Future path:

- Evaluate PWA first for installability and offline shell caching.
- Evaluate Tauri/Electron only when local hardware printing, local database, and OS-level device access are required.
- Desktop/PWA builds must support local receipt printing, local offline storage, and sync to a central server when internet returns.

## Future-Only Items

- Real ESC/POS printer implementation.
- Real fiscal/tax provider integration.
- Real payment provider integration.
- Real Telegram/SMS sending.
- Desktop/PWA packaging.
- Central licensing enforcement.
- Advanced multi-branch deployment hardening.
