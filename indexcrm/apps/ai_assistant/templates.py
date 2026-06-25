from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from apps.ai_assistant.constants import (
    INTENT_CASHIER_ACTIVITY,
    INTENT_CUSTOMER_DEBT,
    INTENT_FINANCE_SUMMARY,
    INTENT_HELP,
    INTENT_LOW_STOCK,
    INTENT_PRODUCT_PRICE,
    INTENT_PRODUCT_STOCK,
    INTENT_REPORTS_SUMMARY,
    INTENT_SALES_MONTH,
    INTENT_SALES_TODAY,
    INTENT_TOP_PRODUCTS,
    INTENT_UNKNOWN,
)

MONEY_QUANT = Decimal("0.01")
QUANTITY_QUANT = Decimal("0.001")
MAX_LIST_ITEMS = 5

DEFAULT_SUGGESTIONS = [
    "Bugun qancha savdo bo'ldi?",
    "Coca-Cola qoldig'i qancha?",
    "Qaysi mahsulotlar kam qolgan?",
]
PRODUCT_SUGGESTIONS = [
    "Coca-Cola 1L qoldig'i qancha?",
    "Pepsi necha pul?",
    "Qaysi mahsulotlar kam qolgan?",
]

PERMISSION_DENIED_ANSWER = (
    "Bu ma'lumotni ko'rish uchun sizda ruxsat yo'q. Ruxsat kerak bo'lsa, "
    "administrator yoki rahbar bilan bog'laning."
)
UNKNOWN_ANSWER = (
    "Savolingizni aniq tushunmadim. Men savdo, mahsulot qoldig'i, narx, "
    "kassir faoliyati, qarzdorlik va hisobotlar bo'yicha yordam bera olaman. "
    "Masalan: 'Bugun qancha savdo bo'ldi?' yoki 'Pepsi necha pul?'"
)
NOT_SUPPORTED_ANSWER = (
    "Bu savolni tushundim, lekin kerakli hisoblash yoki maydonlar hozircha "
    "tayyor emas. Mavjud savdo, qoldiq, narx yoki hisobot savollaridan birini "
    "so'rab ko'ring."
)
TOOL_NOT_READY_ANSWER = (
    "Bu turdagi savolni tushundim, lekin hisoblash qismi hali tayyor emas. "
    "Hozircha savdo, qoldiq, narx va umumiy hisobot savollariga javob bera olaman."
)
HELP_ANSWER = (
    "Yordam bera oladigan savollarim: bugungi yoki oylik savdo, mahsulot "
    "qoldig'i, mahsulot narxi, kam qolgan mahsulotlar, eng ko'p sotilgan "
    "mahsulotlar, kassir faoliyati, mijoz qarzi va umumiy hisobot. Masalan: "
    "'Bugun qancha savdo bo'ldi?', 'Coca-Cola qoldig'i qancha?', "
    "'Ali Valiyev qarzi qancha?'"
)
NOT_FOUND_ANSWER = (
    "So'ralgan ma'lumot topilmadi. Nom, sana yoki boshqa belgini aniqroq yozib "
    "qayta so'rang."
)
MISSING_PRODUCT_ANSWER = (
    "Qaysi mahsulotni nazarda tutyapsiz? Masalan: "
    "'Coca-Cola 1L qoldig'i qancha?' yoki 'Pepsi necha pul?'"
)
EMPTY_MESSAGE_ANSWER = "Savol matni bo'sh bo'lmasligi kerak."
ERROR_ANSWER = (
    "Kechirasiz, hozir javob tayyorlashda xatolik yuz berdi. Keyinroq urinib ko'ring."
)


def _to_decimal(value, default: Decimal = Decimal("0")) -> Decimal:
    if value in (None, ""):
        return default
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return default


def _trim_decimal(value: Decimal) -> str:
    normalized = value.normalize()
    if normalized == normalized.to_integral():
        return str(int(normalized))
    return format(normalized, "f")


def format_money(value) -> str:
    amount = _to_decimal(value).quantize(MONEY_QUANT)
    if amount == amount.to_integral():
        formatted = f"{int(amount):,}".replace(",", " ")
    else:
        formatted = f"{amount:,.2f}".replace(",", " ")
    return f"{formatted} so'm"


def format_quantity(value, unit: str | None = None) -> str:
    quantity = _to_decimal(value).quantize(QUANTITY_QUANT)
    formatted = _trim_decimal(quantity)
    return f"{formatted} {unit}" if unit else formatted


def format_percent(value) -> str:
    percent = _to_decimal(value).quantize(MONEY_QUANT)
    return f"{_trim_decimal(percent)}%"


def format_date(value) -> str:
    if isinstance(value, datetime):
        return value.strftime("%d.%m.%Y")
    if isinstance(value, date):
        return value.strftime("%d.%m.%Y")
    if not value:
        return ""
    text = str(value)
    try:
        return date.fromisoformat(text[:10]).strftime("%d.%m.%Y")
    except ValueError:
        return text


def format_datetime(value) -> str:
    if isinstance(value, datetime):
        return value.strftime("%d.%m.%Y %H:%M")
    if not value:
        return ""
    text = str(value)
    try:
        return datetime.fromisoformat(text).strftime("%d.%m.%Y %H:%M")
    except ValueError:
        return text


def safe_value(value, fallback: str = "noma'lum") -> str:
    return str(value) if value not in (None, "") else fallback


def format_list(items, *, empty: str = NOT_FOUND_ANSWER, limit: int = MAX_LIST_ITEMS) -> str:
    rows = [str(item) for item in (items or []) if item not in (None, "")]
    if not rows:
        return empty
    visible = rows[:limit]
    suffix = f" va yana {len(rows) - limit} ta" if len(rows) > limit else ""
    return "; ".join(visible) + suffix


def _data(tool_result: dict | None) -> dict:
    return (tool_result or {}).get("data") or {}


def _status(tool_result: dict | None) -> str | None:
    return (tool_result or {}).get("status")


def _message(tool_result: dict | None) -> str:
    return safe_value((tool_result or {}).get("message"), NOT_FOUND_ANSWER)


def _count(value) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _money_is_positive(value) -> bool:
    return _to_decimal(value) > 0


def _date_range_text(data: dict) -> str:
    start = format_date(data.get("from") or data.get("date"))
    end = format_date(data.get("to") or data.get("date"))
    if start and end and start != end:
        return f"{start} - {end}"
    return start or end or "tanlangan davr"


def _has_business_filters(data: dict) -> bool:
    filters = data.get("filters") or {}
    return bool(filters.get("branch_name") or filters.get("warehouse_name"))


def _filter_parts(data: dict) -> list[str]:
    filters = data.get("filters") or {}
    branch_name = filters.get("branch_name")
    warehouse_name = filters.get("warehouse_name")
    parts = []
    if branch_name:
        parts.append(f"Filial: {branch_name}")
    if warehouse_name:
        parts.append(f"Ombor: {warehouse_name}")
    if data.get("from") or data.get("to") or data.get("date"):
        parts.append(f"Davr: {_date_range_text(data)}")
    return parts


def _filter_sentence(data: dict) -> str:
    parts = _filter_parts(data)
    if not parts:
        return ""
    return ". ".join(parts) + "."


def _scoped_prefix(title: str, data: dict) -> str:
    sentence = _filter_sentence(data)
    if not sentence:
        return ""
    return f"{title}: {sentence} "


def _no_data_for_filters(data: dict) -> str:
    sentence = _filter_sentence(data)
    if sentence:
        return f"Bu filterlar bo'yicha ma'lumot topilmadi. {sentence}"
    return "Bu filterlar bo'yicha ma'lumot topilmadi."


def _payment_parts(data: dict) -> list[str]:
    parts = []
    payment_labels = (
        ("cash_amount", "naqd"),
        ("card_amount", "karta"),
        ("mixed_amount", "aralash"),
    )
    for key, label in payment_labels:
        if _money_is_positive(data.get(key)):
            parts.append(f"{label} {format_money(data.get(key))}")
    return parts


def _payment_sentence(data: dict) -> str:
    parts = _payment_parts(data)
    if not parts:
        return ""
    return f" To'lovlar: {', '.join(parts)}."


def _product_not_found_answer(intent: str, tool_result: dict | None) -> str:
    entity = (tool_result or {}).get("entity")
    filters = (tool_result or {}).get("filters") or {}
    if entity == "branch":
        value = filters.get("branch")
        detail = f" Filial: {value}." if value else ""
        return f"Filial topilmadi.{detail} Nom yoki raqamni aniqroq yozib qayta so'rang."
    if entity == "warehouse":
        value = filters.get("warehouse")
        detail = f" Ombor: {value}." if value else ""
        return f"Ombor topilmadi.{detail} Nom yoki raqamni aniqroq yozib qayta so'rang."
    if intent in {INTENT_PRODUCT_STOCK, INTENT_PRODUCT_PRICE}:
        return (
            "Mahsulot topilmadi. Nomini aniqroq yozing yoki SKU/barcode bilan so'rang. "
            "Masalan: 'Coca-Cola 1L qoldig'i qancha?'"
        )
    if intent == INTENT_CUSTOMER_DEBT:
        return "Mijoz topilmadi. Ism, telefon yoki familiyani aniqroq yozib qayta so'rang."
    return _message(tool_result)


def _format_product_rows(products, quantity_key="quantity") -> list[str]:
    rows = []
    for index, product in enumerate(products or [], start=1):
        name = safe_value(product.get("product_name"), "Mahsulot")
        unit = product.get("unit")
        quantity = format_quantity(product.get(quantity_key), unit)
        warehouse = product.get("warehouse_name")
        min_quantity = product.get("min_quantity")
        amount = product.get("total_amount")
        details = [quantity]
        if warehouse:
            details.append(str(warehouse))
        if min_quantity is not None:
            details.append(f"limit {format_quantity(min_quantity, unit)}")
        if amount is not None:
            details.append(format_money(amount))
        rows.append(f"{index}. {name} - {', '.join(details)}")
    return rows


def _format_debtor_rows(debtors) -> list[str]:
    rows = []
    for index, debtor in enumerate(debtors or [], start=1):
        name = safe_value(debtor.get("customer_name"), "Mijoz")
        phone = debtor.get("phone")
        debt = format_money(debtor.get("debt_amount"))
        details = f"{debt}"
        if phone:
            details += f", {phone}"
        rows.append(f"{index}. {name} - {details}")
    return rows


def _format_stock_rows(stocks, unit: str | None = None) -> str:
    rows = []
    for stock in stocks or []:
        name = safe_value(stock.get("warehouse_name"), "ombor")
        rows.append(f"{name}: {format_quantity(stock.get('quantity'), stock.get('unit') or unit)}")
    return format_list(rows, empty="", limit=3)


def _render_sales_today(data: dict) -> str:
    sales_count = _count(data.get("sales_count"))
    total = format_money(data.get("total_amount"))
    if sales_count == 0:
        if _has_business_filters(data):
            return _no_data_for_filters(data)
        return f"Bugun savdo topilmadi. Hozircha tushum {total}."
    answer = _scoped_prefix("Bugungi savdo bo'yicha natija", data) + (
        f"Bugun {sales_count} ta savdo bo'ldi. Jami tushum {total}. "
        f"O'rtacha chek {format_money(data.get('average_check'))}."
    )
    return answer + _payment_sentence(data)


def _render_sales_month(data: dict) -> str:
    sales_count = _count(data.get("sales_count"))
    period = _date_range_text(data)
    total = format_money(data.get("total_amount"))
    if sales_count == 0:
        if _has_business_filters(data):
            return _no_data_for_filters(data)
        return f"{period} oralig'ida savdo topilmadi. Jami tushum {total}."
    answer = _scoped_prefix("Savdo bo'yicha natija", data) + (
        f"{period} oralig'ida {sales_count} ta savdo bo'ldi. "
        f"Jami tushum {total}. Kunlik o'rtacha {format_money(data.get('average_daily_sales'))}."
    )
    best_day = data.get("best_day") or {}
    if best_day:
        answer += (
            f" Eng yaxshi kun: {format_date(best_day.get('date'))}, "
            f"{format_money(best_day.get('total_amount'))}."
        )
    return answer + _payment_sentence(data)


def _render_product_stock(data: dict) -> str:
    name = safe_value(data.get("product_name"), "Mahsulot")
    quantity = format_quantity(data.get("quantity"), data.get("unit"))
    warehouse = safe_value(data.get("warehouse_name"), "ombor")
    stock_status = data.get("status")
    if _has_business_filters(data) and not data.get("stocks"):
        return _no_data_for_filters(data)
    if stock_status == "zero":
        answer = _scoped_prefix("Qoldiq bo'yicha natija", data) + f"{name} hozir {warehouse}da qolmagan."
    elif stock_status == "low":
        answer = _scoped_prefix("Qoldiq bo'yicha natija", data) + f"{name} kam qolgan: {warehouse}da {quantity} bor."
    else:
        answer = _scoped_prefix("Qoldiq bo'yicha natija", data) + f"{name} qoldig'i: {warehouse}da {quantity}. Holat: yetarli."
    stock_rows = _format_stock_rows(data.get("stocks"), data.get("unit"))
    if stock_rows:
        answer += f" Omborlar: {stock_rows}."
    return answer


def _render_product_price(data: dict) -> str:
    name = safe_value(data.get("product_name"), "Mahsulot")
    unit = data.get("unit")
    answer = _scoped_prefix("Narx bo'yicha natija", data) + f"{name} sotuv narxi: {format_money(data.get('sale_price'))}"
    if unit:
        answer += f" / {unit}"
    answer += "."
    if "purchase_price" in data:
        answer += f" Tannarx: {format_money(data.get('purchase_price'))}."
    return answer


def _render_low_stock(data: dict) -> str:
    products = data.get("products") or []
    if not products:
        if _has_business_filters(data):
            return _no_data_for_filters(data)
        return (
            "Kam qolgan mahsulotlar topilmadi. Ko'rinadigan omborlarda qoldiq "
            "belgilangan limitdan past emas."
        )
    rows = format_list(_format_product_rows(products), empty="")
    prefix = _scoped_prefix("Kam qoldiq bo'yicha natija", data)
    return f"{prefix}Kam qolgan mahsulotlar ({len(products)} ta): {rows}."


def _render_top_products(data: dict) -> str:
    products = data.get("products") or []
    period = _date_range_text(data)
    if not products:
        if _has_business_filters(data):
            return _no_data_for_filters(data)
        return f"{period} oralig'ida sotilgan mahsulotlar topilmadi."
    rows = format_list(_format_product_rows(products, "quantity_sold"), empty="")
    prefix = _scoped_prefix("Top mahsulotlar bo'yicha natija", data)
    return f"{prefix}{period} bo'yicha eng ko'p sotilgan mahsulotlar: {rows}."


def _render_cashier_activity(data: dict) -> str:
    sales_count = _count(data.get("sales_count"))
    cashier_name = data.get("cashier_name") or "Barcha kassirlar"
    period = _date_range_text(data)
    if sales_count == 0 and not data.get("active_shift_exists"):
        if _has_business_filters(data):
            return _no_data_for_filters(data)
        return f"{period} bo'yicha {cashier_name} faoliyati topilmadi."
    shift = "smena ochiq" if data.get("active_shift_exists") else "smena yopiq yoki topilmadi"
    answer = _scoped_prefix("Kassir faoliyati bo'yicha natija", data) + (
        f"{period} bo'yicha {cashier_name}: {sales_count} ta savdo, "
        f"jami {format_money(data.get('total_amount'))}, {shift}."
    )
    if data.get("branch_name"):
        answer += f" Filial: {data.get('branch_name')}."
    if data.get("shift_opened_at"):
        answer += f" Smena ochilgan vaqt: {format_datetime(data.get('shift_opened_at'))}."
    return answer


def _render_finance_summary(data: dict) -> str:
    period = _date_range_text(data)
    answer = _scoped_prefix("Moliya bo'yicha natija", data) + (
        f"{period} moliya xulosasi: tushum {format_money(data.get('total_income'))}, "
        f"xarajat {format_money(data.get('total_expense'))}, "
        f"kassa qoldig'i {format_money(data.get('cashbox_balance'))}."
    )
    if data.get("estimated_profit") is not None:
        answer += f" Taxminiy foyda {format_money(data.get('estimated_profit'))}."
    elif data.get("profit_message"):
        answer += f" {data.get('profit_message')}"
    return answer


def _render_customer_debt(data: dict) -> str:
    if data.get("customer_name"):
        debt = data.get("debt_amount")
        if _to_decimal(debt) <= 0:
            return f"{data.get('customer_name')} bo'yicha qarz topilmadi."
        answer = f"{data.get('customer_name')} bo'yicha qarz: {format_money(debt)}."
        if data.get("phone"):
            answer += f" Telefon: {data.get('phone')}."
        if data.get("last_purchase_date"):
            answer += f" Oxirgi xarid: {format_datetime(data.get('last_purchase_date'))}."
        return answer

    debtors = data.get("debtors") or []
    if not debtors:
        return "Qarzdor mijozlar topilmadi."
    rows = format_list(_format_debtor_rows(debtors), empty="")
    return f"Qarzdor mijozlar ({len(debtors)} ta): {rows}."


def _render_reports_summary(data: dict) -> str:
    period = _date_range_text(data)
    sales = data.get("sales") or {}
    top_products = data.get("top_products") or []
    low_stock = data.get("low_stock_products") or []
    finance = data.get("finance") or {}
    answer = _scoped_prefix("Hisobot bo'yicha natija", data) + (
        f"{period} hisobot xulosasi: {sales.get('sales_count', 0)} ta savdo, "
        f"jami {format_money(sales.get('total_amount'))}."
    )
    if top_products:
        first = top_products[0]
        answer += (
            f" Top mahsulot: {first.get('product_name')} "
            f"({format_quantity(first.get('quantity_sold'), first.get('unit'))})."
        )
    if low_stock:
        answer += f" Kam qolgan mahsulotlar: {len(low_stock)} ta."
    if finance:
        answer += (
            f" Moliya: tushum {format_money(finance.get('total_income'))}, "
            f"xarajat {format_money(finance.get('total_expense'))}."
        )
    return answer


def _suggestions_for(intent: str, status: str | None) -> list[str]:
    if status in {"missing_entity", "not_found"}:
        return PRODUCT_SUGGESTIONS if intent in {INTENT_PRODUCT_STOCK, INTENT_PRODUCT_PRICE} else DEFAULT_SUGGESTIONS
    if status == "permission_denied":
        return ["Coca-Cola qoldig'i qancha?", "Pepsi necha pul?", "Nima qila olasan?"]
    if intent == INTENT_SALES_TODAY:
        return ["Bu oy savdo qancha?", "Eng ko'p sotilgan mahsulot qaysi?", "Qaysi kassir bugun ishlayapti?"]
    if intent == INTENT_SALES_MONTH:
        return ["Bugun qancha savdo bo'ldi?", "Eng ko'p sotilgan mahsulot qaysi?", "Menga hisobot ber"]
    if intent in {INTENT_PRODUCT_STOCK, INTENT_PRODUCT_PRICE}:
        return PRODUCT_SUGGESTIONS
    if intent == INTENT_LOW_STOCK:
        return ["Coca-Cola qoldig'i qancha?", "Eng ko'p sotilgan mahsulot qaysi?", "Bugun qancha savdo bo'ldi?"]
    if intent == INTENT_TOP_PRODUCTS:
        return ["Bugun qancha savdo bo'ldi?", "Qaysi mahsulotlar kam qolgan?", "Bu oy savdo qancha?"]
    if intent == INTENT_CASHIER_ACTIVITY:
        return ["Bugun qancha savdo bo'ldi?", "Menga hisobot ber", "Bu oy savdo qancha?"]
    if intent == INTENT_FINANCE_SUMMARY:
        return ["Menga hisobot ber", "Bu oy savdo qancha?", "Bugun qancha savdo bo'ldi?"]
    if intent == INTENT_CUSTOMER_DEBT:
        return ["Ali Valiyev qarzi qancha?", "Bugun qancha savdo bo'ldi?", "Menga hisobot ber"]
    if intent == INTENT_REPORTS_SUMMARY:
        return ["Bugun qancha savdo bo'ldi?", "Qaysi mahsulotlar kam qolgan?", "Bugungi foyda qancha?"]
    return DEFAULT_SUGGESTIONS


def _display_type(intent: str, status: str | None) -> str:
    if status in {"permission_denied", "error", "not_supported"}:
        return "notice"
    if status in {"missing_entity", "not_found"} or intent == INTENT_UNKNOWN:
        return "clarification"
    if intent in {INTENT_LOW_STOCK, INTENT_TOP_PRODUCTS, INTENT_CUSTOMER_DEBT}:
        return "list"
    if intent in {INTENT_PRODUCT_STOCK, INTENT_PRODUCT_PRICE}:
        return "product"
    if intent in {INTENT_SALES_TODAY, INTENT_SALES_MONTH, INTENT_FINANCE_SUMMARY, INTENT_REPORTS_SUMMARY}:
        return "summary"
    return "text"


def _items_for(intent: str, data: dict):
    if intent == INTENT_LOW_STOCK:
        return data.get("products") or []
    if intent == INTENT_TOP_PRODUCTS:
        return data.get("products") or []
    if intent == INTENT_CUSTOMER_DEBT:
        return data.get("debtors") or []
    if intent == INTENT_PRODUCT_STOCK:
        return data.get("stocks") or []
    return None


def render_response_metadata(
    intent: str,
    tool_result: dict | None,
    entities: dict | None = None,
) -> dict:
    status = _status(tool_result)
    data = _data(tool_result)
    metadata = {
        "suggestions": _suggestions_for(intent, status),
        "clarification_required": status in {"missing_entity", "not_found"}
        or (intent == INTENT_UNKNOWN and status != "error"),
        "display_type": _display_type(intent, status),
    }
    items = _items_for(intent, data)
    if items is not None:
        metadata["items"] = items
    return metadata


def render_answer(intent: str, tool_result: dict | None, entities: dict | None = None) -> str:
    status = _status(tool_result)
    if intent == INTENT_UNKNOWN:
        return UNKNOWN_ANSWER
    if intent == INTENT_HELP:
        return HELP_ANSWER
    if status == "permission_denied":
        return PERMISSION_DENIED_ANSWER
    if status == "not_supported":
        if (tool_result or {}).get("reason") == "tool_not_ready":
            return TOOL_NOT_READY_ANSWER
        return NOT_SUPPORTED_ANSWER
    if status == "not_found":
        return _product_not_found_answer(intent, tool_result)
    if status == "missing_entity" and (tool_result or {}).get("entity") == "product":
        return MISSING_PRODUCT_ANSWER
    if status == "error":
        return ERROR_ANSWER

    data = _data(tool_result)
    if intent == INTENT_SALES_TODAY:
        return _render_sales_today(data)
    if intent == INTENT_SALES_MONTH:
        return _render_sales_month(data)
    if intent == INTENT_PRODUCT_STOCK:
        return _render_product_stock(data)
    if intent == INTENT_LOW_STOCK:
        return _render_low_stock(data)
    if intent == INTENT_TOP_PRODUCTS:
        return _render_top_products(data)
    if intent == INTENT_PRODUCT_PRICE:
        return _render_product_price(data)
    if intent == INTENT_CASHIER_ACTIVITY:
        return _render_cashier_activity(data)
    if intent == INTENT_FINANCE_SUMMARY:
        return _render_finance_summary(data)
    if intent == INTENT_CUSTOMER_DEBT:
        return _render_customer_debt(data)
    if intent == INTENT_REPORTS_SUMMARY:
        return _render_reports_summary(data)
    return UNKNOWN_ANSWER
