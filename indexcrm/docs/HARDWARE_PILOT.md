# Hardware Pilot Checklist

This checklist is for MVP pilot testing with real mini-market hardware. It supports USB barcode scanners that behave like a keyboard and receipt printers through browser print.

## Supported MVP Setup

- USB barcode scanner in keyboard mode.
- Scanner sends barcode/SKU text followed by Enter.
- POS barcode input on `http://127.0.0.1:3001/`.
- Receipt preview and browser print.
- 80mm receipt paper by default; test 58mm printers through the browser print dialog if needed.

## Not Supported Yet

- Direct ESC/POS printer commands.
- Fiscal printer integration.
- Payment terminal integration.
- Native USB/LAN printer discovery.
- Tauri/Electron desktop wrapper.
- Service worker/PWA hardware bridge.

## Scanner Test Steps

1. Run backend, frontend, migrations, and `seed_demo_data`.
2. Log in as `cashier@example.com` / `Cashier12345`.
3. Open POS and confirm branch, warehouse, and active cashier shift are ready.
4. Click or focus the barcode field once; use `F2` to return focus to it during testing.
5. Scan a seeded product barcode/SKU.
6. Confirm the product is added to the cart.
7. Scan the same product again and confirm cart quantity increases.
8. Scan several different products quickly and confirm they are queued into the cart.
9. Scan an unknown code and confirm POS shows a friendly not-found message with the scanned code.
10. Type a product name/SKU in product search and press Enter to confirm manual search still works.

## Receipt Printer Test Steps

1. Complete a sale from POS.
2. Confirm receipt preview opens after checkout.
3. Confirm receipt includes receipt number, date/time, cashier, product names, quantity, unit price, line totals, subtotal, discount/tax when present, paid amount, debt when present, and final total.
4. Click `Print`.
5. In the browser print dialog, choose the receipt printer.
6. Use receipt paper size if available. For 80mm printers, test 80mm width first.
7. Disable browser headers/footers if the print dialog supports it.
8. Print one test receipt and check alignment, clipping, font size, and paper cutting.

## Common Issues and Fixes

- Scanner types into the wrong field: press `F2` or click the barcode field.
- Scanner does not press Enter: configure the scanner suffix to Enter/CR/LF.
- Product not found: confirm the product SKU/barcode exists in Products and seeded data was loaded.
- Same scan appears twice: the POS suppresses immediate duplicate Enter submissions, but scanner firmware may need debounce/suffix tuning.
- Fast scans miss items: slow the scan sequence and check backend/API health.
- Print opens full page instead of receipt: print from receipt preview, not the whole browser tab.
- Receipt too wide or clipped: choose 80mm paper or adjust printer scaling to 100%.
- Browser adds headers/footers: disable headers/footers in the browser print dialog.
- Printer is not listed: install the OS printer driver first; browser print can only use printers available to Windows.

## Pilot Pass Criteria

- Cashier can scan without using the mouse after initial focus.
- Repeated scans increase cart quantities correctly.
- Unknown scans are understandable and do not break checkout.
- Checkout still creates the sale and opens receipt preview.
- Browser print produces a readable receipt on the test printer.
- Dashboard sales page shows the completed pilot sale.

## Future Hardware Work

- ESC/POS adapter behind the existing integration boundary.
- USB/LAN printer settings per store or terminal.
- Fiscal receipt lifecycle and status tracking.
- Payment terminal provider adapter.
- Desktop/PWA wrapper only if direct device access becomes necessary.
