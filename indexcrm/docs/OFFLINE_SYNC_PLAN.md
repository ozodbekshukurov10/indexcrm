# Index POS Offline Sync Plan

Stage 15A started the offline queue foundation. Stage 15J prepares the manual
sync path for future automatic replay with safer retry metadata, local audit
events, and stronger lock renewal, but automatic background sync is still
disabled.

Stage 26 finishes the MVP manual-sync reliability pass. The queue remains
manual and local-device based, but duplicate local saves are guarded by
idempotency key, stale `syncing` records are recovered automatically during
queue refresh, and cashier/dashboard messages now use clearer local/sent/review
language.

Stage 37 keeps the same manual-sync architecture and adds clearer review and
conflict guidance. Failed records now surface a short classification, last
error, local/server references, and a "what to do next" message without deleting
or auto-replaying the sale.

## Current Online Checkout Flow

1. POS builds a `SalePayload` from the current cart, selected customer, branch ID, warehouse ID, and payments.
2. The frontend creates a draft sale with `POST /api/v1/sales/`.
3. The frontend completes that draft with `POST /api/v1/sales/{id}/complete/`.
4. Backend completion validates stock, decreases inventory, records stock movements, updates customer debt when needed, records finance transactions, and writes audit logs.
5. The completed sale is stored in POS state as `completedSale`, and the receipt preview loads receipt data from `GET /api/v1/sales/{id}/receipt/`.

## Stage 15A Implemented Foundation

- Typed pending sale records in `frontend/pos/src/services/offlineSalesQueue.ts`
- Local idempotency key generation for future replay safety
- Local queue status values: `pending`, `syncing`, `synced`, `failed`
- `createdAt`, `updatedAt`, `retryCount`, and `lastError` fields
- Original sale payload, cart item snapshot, payments, session data, totals, and receipt fallback shape
- LocalStorage queue helpers under the `index-pos-offline-sales` key
- Network status hook based on browser online/offline events
- POS indicator showing Online/Offline and pending sale count
- Placeholder sync function that intentionally does not replay sales yet

## Stage 15B Backend Idempotency Foundation

- `Sale.idempotency_key` stores an optional client-generated checkout key.
- The database enforces uniqueness for non-null sale idempotency keys.
- `POST /api/v1/sales/` accepts `idempotency_key` without requiring older clients to send it.
- Repeating sale creation with the same `idempotency_key` returns the existing sale instead of creating duplicate sale rows, sale items, or payments.
- `POST /api/v1/sales/{id}/complete/` is idempotent after success: if the sale is already completed, the backend returns it without reducing stock or recording finance twice.
- The POS online checkout now sends a stable generated idempotency key for a checkout attempt. If the cashier retries without changing the cart, the same key is reused.

## Stage 15C Manual Replay With Idempotency Guard

- The POS can now manually replay locally queued sales from the offline status strip.
- Replay is user-triggered only. It does not run on page load and does not start automatically when the browser comes online.
- Replay only processes queued sales with `pending` or `failed` status. Already `synced` sales are skipped.
- Queued sales are processed one by one, oldest first.
- Each replay uses the stored `idempotency_key` from the queued sale. It does not generate a new key during replay.
- Each queued sale is marked `syncing` before API calls, then `synced` with the server sale ID and receipt number, or `failed` with a cashier-friendly error.
- Replay is blocked while offline and while another replay is already running in the current POS tab.
- Failed queued sales remain in local storage for manual review and retry.

## Stage 15D Offline Checkout, Queue Review, and Recovery

- When the browser is offline, the POS payment action changes to `Save Offline Sale`.
- Saving an offline sale does not call the backend. It writes the current sale payload, cart snapshot, payment snapshot, cashier/session IDs, customer snapshot, local totals, local timestamp, local reference, and stable `idempotency_key` into localStorage.
- The cart is cleared only after the local queue save succeeds.
- The cashier sees `Sale saved offline. Sync when internet returns.` after a successful local save.
- The offline status strip now shows pending, failed, syncing, and synced counts plus a compact list of recent queued sales.
- Failed queued sales show a readable failure reason and remain available for manual retry.
- Items stuck in `syncing` for more than three minutes are recovered to `failed` with `Previous sync was interrupted. Please retry.`
- Manual replay uses a localStorage sync lock with a five-minute expiry so two POS tabs do not replay the same queue at the same time. Expired locks are cleared locally.

## Stage 15E Offline Queue Management

- A dedicated offline queue management page is available at `/dashboard/offline-queue`.
- The dashboard navigation includes `Offline Queue` for owner, admin, manager, and cashier roles.
- The page shows all locally queued sales from localStorage across `pending`, `failed`, `syncing`, and `synced` states.
- Summary cards show total queued records, pending, failed, synced, total queued amount, and failed amount.
- Queue filters support all, pending, failed, synced, and syncing records.
- Sorting supports newest first, oldest first, and failed first.
- A detail review panel shows local reference, idempotency key, status, timestamps, retry count, failure reason, server sale/receipt references, totals, payments, customer, cashier/session data, and item snapshots.
- Manual retry is available for a selected pending/failed sale or all pending/failed sales.
- Stale syncing recovery remains manual from the page and does not trigger replay.
- Synced records can be cleared after confirmation. Pending, failed, and syncing records are preserved to avoid losing real cashier sales.
- The compact POS offline strip links to the full queue review page.

## Stage 15F Session Enforcement, RBAC, and Conflict Classification

- POS checkout now requires an active cashier shift before online checkout or offline sale saving.
- The frontend reads the current active shift from the backend instead of relying on a manually entered shift ID.
- Backend sale creation/completion rejects checkout when the cashier has no active shift for the sale branch.
- Operational APIs now apply branch/store scoping for non owner/admin users where the current data model supports it.
- Finance and reports APIs require manager-level access or higher.
- Failed offline replay records now store a conflict class: backend unavailable, validation error, stock conflict, product missing/deleted, shift missing/closed, permission/store scope, or unknown.
- The offline queue dashboard shows the conflict class, last error, retry count, local reference, totals, and any server sale/receipt reference captured during a partial replay.

## Stage 15G Idempotency Hardening and Error Mapping

- New sale rows store an `idempotency_fingerprint` hash of the normalized checkout payload.
- Repeating `POST /api/v1/sales/` with the same `idempotency_key` and same payload returns the existing sale and does not create duplicate rows, items, payments, stock effects, or finance effects.
- Reusing the same `idempotency_key` with a different payload returns a `409 idempotency_conflict` response instead of silently returning the old sale.
- Legacy sales that already have an idempotency key but no fingerprint still return the existing sale for compatibility.
- Sale validation responses now include machine-readable codes for idempotency conflict, shift missing/closed, stock conflict, branch/warehouse/store scope denial, permission denial, and generic validation failures.
- Offline replay maps backend error codes into cashier-facing classes, including the new idempotency conflict class.
- Manual retry remains user-controlled, blocked while offline/backend-unreachable, protected by the localStorage sync lock, and preserves failed records for review.

## Stage 15H IndexedDB Offline Queue Persistence

- IndexedDB is now the primary browser storage for queued offline POS sales.
- The storage adapter keeps localStorage as a fallback when IndexedDB cannot be opened or used.
- Existing localStorage queue records are copied into IndexedDB on first load, preserving local references, idempotency keys, cart/payment/session/customer snapshots, status, retry/error metadata, and server sale/receipt fields.
- The migration writes a simple version marker only after the copy succeeds. It does not delete the old localStorage queue data.
- Migration avoids duplicate records by local sale ID, so repeated startup checks do not duplicate the same queued sale.
- Manual sync, selected retry, failed-sale preservation, stale syncing recovery, and synced-only cleanup remain user-controlled.
- The POS status strip and offline queue dashboard show a warning when IndexedDB is unavailable and the queue is using localStorage fallback.

## Stage 15I Smart Connectivity Detection

- POS connectivity no longer relies on `navigator.onLine` alone.
- The frontend reuses the existing public `GET /api/v1/health/` endpoint to verify that the backend API is actually reachable.
- The smart connectivity state distinguishes online/API reachable, browser offline, backend unreachable, checking, and unknown states.
- Backend health is checked on POS load, browser online/offline changes, focus/interval refresh, before manual sync, and before checkout when the current health state is stale or unknown.
- Online checkout is used only when the backend health check is healthy. If the browser is offline or the backend is unreachable, checkout routes to the existing offline sale save flow.
- Manual sync remains user-triggered and requires both browser connectivity and a passing backend health check.
- Network timeout, fetch failure, and backend 5xx health responses are treated as backend unavailable. Auth or permission API failures remain auth/permission problems, not offline status.

## Stage 15J Manual Sync Reliability Preparation

- Manual sync still processes only `pending` and `failed` records, oldest first. `synced` records are skipped, and `syncing` records must be recovered before retry.
- Queued sale metadata is normalized on read for backward compatibility and now includes last attempt time, last error code/message, failure category, synced time, and server sale/receipt references when available.
- Sync uses a same-tab in-flight guard plus the existing localStorage cross-tab lock. The lock still expires, and an active manual sync now renews the lock while it runs.
- Expired locks and stale `syncing` records are recovered locally without deleting sales. Recovered sale records become `failed` and are visible for manual review.
- A bounded local sync audit log records non-sensitive events such as sync started, sync skipped, sale syncing, sale synced, sale failed, stale recovery, and lock recovery. The dashboard shows recent events.
- Manual retry preflight still requires browser connectivity, backend reachability through smart health checks, and an auth token before replay starts.
- A reusable `syncQueueOnce()` function is available for future auto-sync orchestration, but nothing calls it automatically yet.

## Stage 26 Offline Reliability Finish

- Saving the same checkout offline more than once with the same idempotency key no longer creates duplicate local queue records.
- POS offline save confirmation now includes the local reference and clearly says the sale has not been sent to the backend yet.
- The queue hook safely recovers stale `syncing` records during normal queue refresh when no active sync lock is present.
- Manual sync result text now says how many sales were sent and how many still need review.
- The cashier offline strip uses clearer labels: local, needs review, sending, and sent.
- The offline queue dashboard uses the same plain-language labels while preserving failed records for review and retry.
- Backend idempotency, payload fingerprint checks, failed-sale preservation, IndexedDB primary storage, localStorage fallback, and manual sync locks remain unchanged.

## Stage 37 Offline Queue Review and Conflict Polish

- The offline queue dashboard now shows clearer pending, syncing, failed, and synced status labels.
- Queue rows include a next-step message for each sale, based on the current status or failure class.
- Failed sale detail includes a guidance panel explaining the class, why it matters, and what the operator/admin should do next.
- The POS offline strip uses the same failure guidance for recent failed records.
- Offline save is still blocked when branch, warehouse, or active shift context is missing, and the message now clearly says the sale was not saved locally.
- Sync error detail formatting avoids raw backend `code`/`status` fields in cashier/admin messages.
- Manual sync, IndexedDB/localStorage persistence, local sync lock, stale syncing recovery, idempotency keys, and failed-sale preservation remain unchanged.

## Not Implemented Yet

- Background sync or retry worker
- Service worker or PWA installation
- Failed-sale edit/approval resolution for changed stock, deleted products, or closed shifts
- Automatic background replay after connectivity returns
- Server-side sync audit model for offline replay
- Receipt numbering that is guaranteed valid before server sync
- Dedicated failed-sale edit flow
- Editing failed queued sale payloads
- Server-side queue review for central admin visibility

## Remaining Replay Decisions

Backend idempotency with payload consistency checks, guarded manual replay, IndexedDB-backed offline checkout queue saving, smart backend-aware connectivity checks, local queue review, session enforcement, local sync audit events, and failure classification are now available. Before enabling automatic background sync, the project still needs a conflict edit/approval workflow and server-side sync/audit visibility.

## Recommended Stage 15K

Stage 15K should add selected-sale conflict edit/approval handling before any automatic background replay is enabled.
