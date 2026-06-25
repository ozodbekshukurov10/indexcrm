# Internal AI Assistant MVP

## Scope

Stage AI-1 added a normal Django app, `apps.ai_assistant`, inside Index. Stage AI-2 upgraded its rule-based intent detection with better normalization, phrase scoring, synonyms, conflict handling, and test coverage. Stage AI-3 upgraded entity extraction for products, customers, cashiers, categories, suppliers, and dates. Stage AI-4 connects the supported intents to read-only CRM tools. Stage AI-5 polishes Uzbek answer templates, formatting, empty states, clarification prompts, and optional response metadata. Stage AI-6 improves chat history, feedback, admin visibility, session handling, safe logging, and basic usage stats. Stage AI-7 adds the frontend AI Assistant chat page in the existing POS/dashboard frontend. Stage AI-8 adds the quality gate, safety audit, frontend checks, and manual test checklist.

The assistant does not use external AI APIs, local LLMs, embeddings, vector databases, RAG, or a separate microservice.

The assistant is read-only against business data. It can create its own chat sessions, chat messages, training examples, and feedback records, but it does not update products, stock, sales, finance, or POS checkout data.

## AI-9 Branch/Warehouse Context & Rich Filters

AI-9 adds rule-based branch, warehouse, and richer date context to supported business questions. The assistant still does not use an LLM, external AI API, embeddings, vector database, LangChain, or RAG.

Supported branch filters:

- branch names that exist in `stores.Branch`, for example `Chilonzor filialida`
- numbered branch references such as `filial 1`, `1-filial`, or `branch 2`; these are treated as the visible active branches ordered by creation time
- branch filters are applied through the existing branch-scope permission helpers, so they cannot expand what a user can see

Supported warehouse filters:

- warehouse names that exist in `inventory.Warehouse`, for example `Asosiy omborda`
- numbered warehouse references such as `ombor 1`, `1-ombor`, or `warehouse 2`; these are treated as the visible active warehouses ordered by creation time
- warehouse filters are applied through `Stock.warehouse`, `Sale.warehouse`, or `Warehouse.branch` only where those relations exist

Supported date phrases:

- `bugun`, `today`
- `kecha`, `yesterday`
- `bu hafta`, `shu hafta`, `this week`
- `bu oy`, `shu oy`, `this month`
- `oxirgi 7 kun`, `last 7 days`
- `oxirgi 30 kun`, `last 30 days`
- existing ISO and dotted dates such as `2026-06-22` and `22.06.2026`

Example Uzbek questions:

- `Bugun 1-filialda qancha savdo bo'ldi?`
- `Kecha asosiy omborda Coca-Cola qoldig'i qancha?`
- `Shu oy filial 2 da eng ko'p sotilgan mahsulotlar qaysi?`
- `Ombor 1 da kam qolgan mahsulotlarni ko'rsat`
- `Bugungi kassirlar aktivligini ko'rsat`
- `Oxirgi 7 kunda filial bo'yicha savdoni ko'rsat`

Filtered answers mention the applied context when available, for example `Filial: Chilonzor`, `Ombor: Asosiy ombor`, and `Davr: 22.06.2026`. If a requested branch or warehouse cannot be found in the user's visible scope, the assistant returns a safe not-found response instead of guessing.

Limitations:

- numbered branch and warehouse references are ordinal references over visible active records, not database UUIDs
- product prices remain global because the current `Product.selling_price` field is not branch-specific
- warehouse filters are ignored for finance summaries because finance rows relate to `CashBox.branch`, not directly to warehouses
- date and location parsing remains rule-based and heuristic

## Endpoint

`POST /api/v1/ai/chat/`

Authentication is required.

Request:

```json
{
  "message": "Bugun qancha savdo bo'ldi?",
  "session_id": null
}
```

Response:

```json
{
  "answer": "Bugun 12 ta savdo bo'ldi. Jami tushum 1 540 000 so'm. O'rtacha chek 128 333.33 so'm.",
  "intent": "sales_today",
  "confidence": 0.9,
  "entities": {},
  "source": "tool",
  "session_id": "7a6bf52b-f9c7-4638-a565-3e5c67dfd6bf",
  "suggestions": [
    "Bu oy savdo qancha?",
    "Eng ko'p sotilgan mahsulot qaysi?",
    "Qaysi kassir bugun ishlayapti?"
  ],
  "clarification_required": false,
  "display_type": "summary"
}
```

AI-5 keeps the original response fields stable and adds optional metadata:

- `suggestions`: short follow-up prompts the UI can show as quick actions
- `clarification_required`: `true` for unclear, missing entity, or not-found questions
- `display_type`: a UI hint such as `summary`, `list`, `product`, `clarification`, `notice`, or `text`
- `items`: optional raw list rows for list/product displays, when available

Sources:

- `tool`: an implemented read-only tool produced the answer
- `fallback`: unknown, missing entity, or other local fallback behavior
- `permission_denied`: the user is authenticated but cannot see that business data
- `not_supported`: the intent is understood but the required model/field/tool is not reliable yet
- `error`: a guarded internal failure occurred
- `help`: the assistant returned its local help answer

Additional assistant endpoints:

- `GET /api/v1/ai/sessions/`
- `GET /api/v1/ai/sessions/<session_id>/`
- `POST /api/v1/ai/sessions/<session_id>/close/`
- `POST /api/v1/ai/feedback/`
- `GET /api/v1/ai/stats/`

## Chat History

`GET /api/v1/ai/sessions/` returns only the current user's active sessions, newest first. Each row includes:

- `id`
- `title`
- `is_active`
- `message_count`
- `last_message_preview`
- `created_at`
- `updated_at`

`GET /api/v1/ai/sessions/<session_id>/` returns a session with messages ordered by `created_at`. Normal users can only fetch their own sessions. Staff, superusers, and admin-role users can inspect sessions directly when needed for support or monitoring.

Normal users do not receive `tool_result` in message history. Staff/admin users can see `tool_result` for debugging in session detail and the Django admin.

`POST /api/v1/ai/sessions/<session_id>/close/` sets `is_active=false`. It does not hard-delete chat history.

The chat service:

- creates a new session when `session_id` is absent
- appends messages when the authenticated user owns the active `session_id`
- creates a new safe session if a provided `session_id` is missing, inactive, or not owned by the user
- saves user messages before processing and assistant messages after processing
- stores assistant `source` on each assistant message
- updates session `updated_at` after assistant responses
- keeps a default title from the first user message, truncated to the model limit

AI-6 includes a tiny context convenience, not LLM memory: if a user asks a product follow-up such as `narxini ham ayt` in the same session, the service may reuse the last product entity from a previous assistant response. It currently reuses product context only and does not infer broad conversational meaning.

## Frontend UI

Stage AI-7 adds the frontend route:

`/dashboard/ai`

Navigation label:

`AI yordamchi`

The page uses the existing dashboard layout, Tailwind styling, auth token flow, and API base URL from `NEXT_PUBLIC_API_BASE_URL`. It does not call any external AI service.

Frontend capabilities:

- chat message list with user and assistant bubbles
- Uzbek input placeholder: `Savolingizni yozing...`
- Enter sends, Shift+Enter creates a new line
- loading text: `Javob tayyorlanmoqda...`
- safe error text: `AI yordamchi bilan ulanishda xatolik yuz berdi. Qayta urinib ko'ring.`
- default suggested questions
- current `session_id` reuse for follow-up messages
- recent session list and `Yangi chat`
- assistant feedback buttons: `Foydali` and `Foydasiz`
- message metadata visible only in development builds

Default suggested questions:

- `Bugun qancha savdo bo'ldi?`
- `Bugungi tushum qancha?`
- `Coca-Cola qoldig'i qancha?`
- `Pepsi narxi qancha?`
- `Qaysi mahsulotlar kam qolgan?`
- `Eng ko'p sotilgan mahsulot qaysi?`
- `Bu oy savdo qancha?`
- `Nima qila olasan?`

Frontend API calls:

- `POST /api/v1/ai/chat/`
- `GET /api/v1/ai/sessions/`
- `GET /api/v1/ai/sessions/<session_id>/`
- `POST /api/v1/ai/feedback/`

The normal frontend does not display raw `tool_result` JSON or backend tracebacks.

## Quality Gate

Stage AI-8 verifies the assistant with targeted backend tests and frontend checks.

Backend test coverage includes:

- intent detection for all supported Uzbek examples and unknown fallback
- entity extraction for products, customers, cashiers, suppliers, categories, and dates
- template formatting, empty states, clarification prompts, permission denial, and safe errors
- tool JSON serializability and empty-database behavior
- finance summary not inventing profit when cost/profit rules are unavailable
- session creation, session append, session scoping, and session close
- feedback validation, ownership checks, and duplicate update behavior
- staff-only stats and staff-only `tool_result` visibility
- internal exception masking with safe Uzbek error text
- source-level read-only audit for business tool modules
- dependency manifest audit for external AI/vector/local LLM packages
- frontend AI client audit for existing API config and no raw `tool_result` rendering

Recommended automated checks:

```powershell
.\.venv\Scripts\ruff.exe check apps\ai_assistant tests\test_ai_assistant.py
.\.venv\Scripts\pytest.exe tests\test_ai_assistant.py
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run --settings=config.settings.test
.\.venv\Scripts\pytest.exe
cd frontend\pos
npm.cmd run typecheck
npm.cmd run build
```

Audit results:

- no external AI API, local LLM, embeddings, vector database, or RAG dependency is used
- assistant business tools are read-only against products, stock, sales, finance, customers, and POS data
- allowed assistant writes are limited to chat sessions, chat messages, feedback, and training examples
- normal users cannot see other users' chat sessions
- normal frontend users do not see raw `tool_result`
- cashiers are denied finance/report intents by policy
- backend errors return safe Uzbek responses instead of tracebacks

## Manual Test Checklist

Use this checklist after backend and frontend checks pass:

- Log in as admin or owner.
- Open `/dashboard/ai`.
- Ask `Bugun qancha savdo bo'ldi?`.
- Ask `Coca-Cola qoldig'i qancha?`.
- Ask `Pepsi narxi qancha?`.
- Ask `Qaysi mahsulotlar kam qolgan?`.
- Ask `Nima qila olasan?`.
- Confirm assistant answers are Uzbek and the page does not show raw JSON.
- Confirm sessions appear in the recent chat list.
- Open a previous session and confirm messages load in order.
- Click `Foydali` or `Foydasiz` on an assistant answer and confirm `Fikringiz saqlandi.` appears.
- Start `Yangi chat` and confirm the current messages clear.
- Log in as cashier.
- Ask `Coca-Cola qoldig'i qancha?` and confirm product information works.
- Ask `Bugungi foyda qancha?` and confirm permission denial is safe.
- Refresh the AI page and confirm it does not crash.
- Temporarily stop the backend and confirm the frontend shows a safe connection error.

## Feedback

`POST /api/v1/ai/feedback/`

Request:

```json
{
  "message_id": "7a6bf52b-f9c7-4638-a565-3e5c67dfd6bf",
  "rating": "good",
  "comment": "Javob foydali bo'ldi"
}
```

Response:

```json
{
  "status": "ok",
  "message": "Fikringiz saqlandi."
}
```

Feedback rules:

- only authenticated users can leave feedback
- feedback can be left only on assistant messages from the user's own sessions
- rating must be `good` or `bad`
- duplicate feedback by the same user for the same assistant message updates the existing feedback row
- staff/admin can view all feedback in Django admin

## Admin And Stats

Django admin registers:

- `AIChatSession`
- `AIChatMessage`
- `AITrainingExample`
- `AIFeedback`

Admin list views include useful filters, search fields, ordering, source, short content previews, feedback author, and short feedback comments.

`GET /api/v1/ai/stats/` is restricted to staff, superusers, and admin-role users. It returns:

- `total_sessions`
- `total_messages`
- `total_user_messages`
- `total_assistant_messages`
- `top_intents`
- `feedback_good_count`
- `feedback_bad_count`
- `unknown_intent_count`
- `error_count`

## Supported Intents

- `sales_today`
- `sales_month`
- `product_stock`
- `low_stock`
- `top_products`
- `product_price`
- `cashier_activity`
- `finance_summary`
- `customer_debt`
- `reports_summary`
- `help`
- `unknown`

## Supported Questions

- `Bugun qancha savdo bo'ldi?`
- `Bugungi tushum qancha?`
- `Bu oy savdo qancha?`
- `Coca-Cola qoldig'i qancha?`
- `Pepsi necha pul?`
- `Qaysi mahsulotlar kam qolgan?`
- `Eng ko'p sotilgan mahsulot qaysi?`
- `Bugungi foyda qancha?`
- `Ali Valiyev qarzi qancha?`
- `Qaysi kassir bugun ishlayapti?`
- `Menga hisobot ber`
- `Nima qila olasan?`

AI-4 tools now answer the main CRM questions from existing Index models. When a model or field is unclear, tools return `not_supported` instead of guessing.

AI-5 templates format money as `1 540 000 so'm`, quantities as `18 dona`, and dates as `18.06.2026` in user-facing answers. Empty and not-found states use explicit Uzbek wording instead of generic failures.

Clarification examples:

- Missing product: `Qaysi mahsulotni nazarda tutyapsiz?`
- Unknown question: `Savolingizni aniq tushunmadim.`
- Product not found: `Mahsulot topilmadi. Nomini aniqroq yozing yoki SKU/barcode bilan so'rang.`

## Intent Detection

AI-2 keeps `detect_intent(message: str)` compatible with AI-1:

```json
{
  "intent": "sales_today",
  "confidence": 0.89,
  "matched_keywords": ["bugun", "savdo"],
  "scores": {
    "sales_today": 8.0
  }
}
```

The detector:

- lowercases and trims text
- normalizes apostrophe variants
- normalizes Uzbek `o'`/`g'` style letters for matching
- removes repeated punctuation while keeping numbers and product words usable
- scores exact phrases, strong keywords, regular keywords, and intent-specific combinations
- resolves overlaps such as `bugungi foyda` versus `bugungi tushum`

## Entity Extraction

AI-3 keeps `extract_entities(message: str, intent: str, user=None)` stable and JSON-serializable. It can return:

```json
{
  "product_name": "Coca-Cola 1L",
  "product_id": "7a6bf52b-f9c7-4638-a565-3e5c67dfd6bf",
  "raw_product_query": "coca cola",
  "product_match_score": 90.0,
  "date": "2026-06-18",
  "matches": {
    "product": {
      "status": "matched",
      "score": 90.0,
      "query": "coca cola"
    }
  }
}
```

Supported entity types:

- products from `catalog.Product`
- categories from `catalog.Category`
- customers from `sales.Customer`
- cashiers/users from `accounts.User`
- suppliers from `purchases.Supplier`
- dates and date ranges from Uzbek date phrases

Supported date phrases:

- `bugun`
- `kecha`
- `ertaga`
- `bu hafta`
- `o'tgan hafta`
- `bu oy`
- `o'tgan oy`
- `oxirgi 7 kun`
- `oxirgi 30 kun`
- `2026-06-03`
- `03.06.2026`

Matching strategy:

- exact normalized text match scores `100`
- SKU, barcode, phone, email, and supplier tax number are considered where the model has those fields
- `icontains`-style behavior is covered by normalized substring scoring
- `rapidfuzz` is used if already installed; otherwise `difflib` fallback scoring is used
- matches below `70` are returned as `uncertain`/`not_found` without selecting a record

Examples:

- `Coca-Cola qoldig'i qancha?` extracts product `Coca-Cola 1L`
- `Pepsi necha pul?` extracts product `Pepsi 1L`
- `Ali Valiyev qarzi qancha?` extracts customer `Ali Valiyev`
- `Kassir Demo bugun qancha savdo qildi?` extracts cashier `Kassir Demo`
- `Ichimliklardan qaysilari kam qolgan?` extracts category `Ichimliklar`
- `Bu oy savdo qancha?` extracts current month date range

## Implemented Tools

- `get_today_sales(user=None)`
- `get_monthly_sales(user=None, date_range=None, branch_id=None)`
- `get_product_stock(product_id=None, product_name=None, warehouse_id=None, user=None)`
- `get_product_price(product_id=None, product_name=None, user=None)`
- `get_low_stock_products(user=None, limit=10, category_id=None, warehouse_id=None)`
- `get_top_products(user=None, date_range=None, limit=10, category_id=None)`
- `get_cashier_activity(user=None, cashier_id=None, date=None, date_range=None)`
- `get_finance_summary(user=None, date=None, date_range=None)`
- `get_customer_debt(user=None, customer_id=None, customer_name=None)`
- `get_reports_summary(user=None, date=None, date_range=None)`
- `run_tool(intent, entities, user=None)`

The tools use existing Django ORM models:

- `apps.catalog.models.Product`
- `apps.inventory.models.Stock`
- `apps.sales.models.Sale`
- `apps.sales.models.SaleItem`
- `apps.sales.models.SalePayment`
- `apps.sales.models.Customer`
- `apps.cashier.models.CashierShift`
- `apps.finance.models.CashBox`
- `apps.finance.models.Expense`
- `apps.finance.models.Income`

Branch scoping reuses `apps.accounts.permissions.filter_queryset_by_branch_scope` where business rows are branch-owned. Product price is global because the current `Product.selling_price` field is not branch-specific.

Tool result format:

```json
{
  "status": "ok",
  "data": {
    "sales_count": 42,
    "total_amount": "5230000.00"
  }
}
```

Errors and empty states use:

```json
{
  "status": "not_found",
  "message": "Mahsulot topilmadi."
}
```

## Tool Examples

Sales today:

```json
{
  "status": "ok",
  "data": {
    "date": "2026-06-18",
    "sales_count": 12,
    "total_amount": "1540000.00",
    "cash_amount": "1000000.00",
    "card_amount": "540000.00",
    "average_check": "128333.33"
  }
}
```

Product stock:

```json
{
  "status": "ok",
  "data": {
    "product_name": "Coca-Cola 1L",
    "quantity": "18.000",
    "unit": "pcs",
    "warehouse_name": "Asosiy ombor",
    "status": "enough"
  }
}
```

Finance summary intentionally does not invent profit. If cost/profit logic is not reliable, `estimated_profit` is `null` and the tool returns:

`Foyda hisoblash uchun tannarx ma'lumotlari yetarli emas.`

## Permission Behavior

Only authenticated users can use the assistant.

Cashiers can ask:

- product stock
- product price
- own cashier activity
- help
- unknown/fallback questions

Managers can ask sales, inventory, top products, cashier activity, and customer debt questions.

Owner/admin/staff/superuser users can use all implemented business-data intents, including finance and reports. If role assignment or branch scope is incomplete, scoped tools return only data visible through the existing branch-scope helpers, which may mean empty results.

Chat history permissions are separate from business-data intent permissions:

- normal users can list and open only their own chat sessions
- session close is scoped to the owner or staff/admin support users
- feedback is accepted only for the user's own assistant messages
- usage stats are staff/admin only

Permission denied answer:

`Bu ma'lumotni ko'rish uchun sizda ruxsat yo'q. Ruxsat kerak bo'lsa, administrator yoki rahbar bilan bog'laning.`

## Limitations

- Rule-based intent detection only; no generative model is used.
- Entity extraction is rule-based and heuristic; it does not use a generative model.
- No LLM-style conversational memory; only limited same-session product follow-up reuse exists.
- Profit is not invented; `estimated_profit` is intentionally `null` until reliable cost/profit rules are defined.
- Supplier entities are extracted, but supplier-specific assistant tools are still future work.
- No write actions against business data.
- Frontend feedback has no free-text comment input yet; it sends the selected rating only.
- The session sidebar lists recent sessions from the paginated first page only.

## Recommended Next Stage

For AI-9, add branch/warehouse selection prompts, supplier-specific answers, richer report filters, frontend feedback comments, exportable assistant audit views, and more precise profit logic if business rules are confirmed. Keep LLM, embeddings, and RAG decisions separate until permissions, audit, and data scoping are mature.
