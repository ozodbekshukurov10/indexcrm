import calendar
import re
from datetime import date, timedelta
from difflib import SequenceMatcher

from django.apps import apps
from django.db.models import Q
from django.utils import timezone

from apps.ai_assistant.constants import (
    INTENT_CASHIER_ACTIVITY,
    INTENT_CUSTOMER_DEBT,
    INTENT_FINANCE_SUMMARY,
    INTENT_LOW_STOCK,
    INTENT_PRODUCT_PRICE,
    INTENT_PRODUCT_STOCK,
    INTENT_REPORTS_SUMMARY,
    INTENT_SALES_MONTH,
    INTENT_SALES_TODAY,
    INTENT_TOP_PRODUCTS,
)
from apps.ai_assistant.text import normalize_text

try:
    from rapidfuzz import fuzz
except ImportError:  # pragma: no cover - rapidfuzz is optional and not installed here.
    fuzz = None


PRODUCT_INTENTS = {
    INTENT_PRODUCT_STOCK,
    INTENT_PRODUCT_PRICE,
    INTENT_TOP_PRODUCTS,
    INTENT_REPORTS_SUMMARY,
}
CUSTOMER_INTENTS = {INTENT_CUSTOMER_DEBT, INTENT_REPORTS_SUMMARY}
CASHIER_INTENTS = {
    INTENT_CASHIER_ACTIVITY,
    INTENT_SALES_TODAY,
    INTENT_REPORTS_SUMMARY,
}
CATEGORY_INTENTS = {
    INTENT_LOW_STOCK,
    INTENT_TOP_PRODUCTS,
    INTENT_PRODUCT_STOCK,
    INTENT_REPORTS_SUMMARY,
}
SUPPLIER_INTENTS = {INTENT_REPORTS_SUMMARY}
BRANCH_INTENTS = {
    INTENT_CASHIER_ACTIVITY,
    INTENT_FINANCE_SUMMARY,
    INTENT_LOW_STOCK,
    INTENT_PRODUCT_STOCK,
    INTENT_REPORTS_SUMMARY,
    INTENT_SALES_MONTH,
    INTENT_SALES_TODAY,
    INTENT_TOP_PRODUCTS,
}
WAREHOUSE_INTENTS = {
    INTENT_LOW_STOCK,
    INTENT_PRODUCT_STOCK,
    INTENT_REPORTS_SUMMARY,
    INTENT_SALES_MONTH,
    INTENT_SALES_TODAY,
    INTENT_TOP_PRODUCTS,
}

COMMON_STOPWORDS = {
    "ayt",
    "ber",
    "bo",
    "boldi",
    "bormi",
    "bor",
    "boyicha",
    "haqida",
    "ichida",
    "iltimos",
    "kerak",
    "ma",
    "malumot",
    "menga",
    "mi",
    "nechta",
    "qanday",
    "qancha",
    "qaysi",
    "qaysilari",
    "qilib",
    "qil",
    "qildi",
    "qila",
    "qolgan",
    "shuni",
    "statistika",
    "umumiy",
    "ldi",
}

DATE_STOPWORDS = {
    "bugun",
    "bugungi",
    "bu",
    "davomida",
    "ertaga",
    "hafta",
    "kecha",
    "kun",
    "kunlik",
    "last",
    "oxirgi",
    "otgan",
    "oy",
    "oylik",
    "shu",
    "this",
    "today",
    "week",
    "yesterday",
}

ENTITY_STOPWORDS = {
    "product": {
        "bahosi",
        "dona",
        "mahsulot",
        "mahsulotlar",
        "mavjud",
        "mavjudmi",
        "narx",
        "narxi",
        "narxini",
        "necha",
        "ombor",
        "omborda",
        "omborida",
        "pul",
        "qoldi",
        "qoldig",
        "qoldigi",
        "qoldiq",
        "sklad",
        "sotuv",
        "turadi",
        "warehouse",
        "warehouseda",
        "zaxira",
    },
    "customer": {
        "mijoz",
        "nasiya",
        "nasiyaga",
        "qarz",
        "qarzdor",
        "qarzi",
    },
    "cashier": {
        "faoliyati",
        "ishlayapti",
        "kassir",
        "ochilganmi",
        "ochiqmi",
        "smena",
        "smenasi",
        "sotdi",
        "savdo",
        "tushum",
    },
    "category": {
        "bestseller",
        "eng",
        "kam",
        "kop",
        "mahsulot",
        "mahsulotlar",
        "minimum",
        "qoldi",
        "qoldig",
        "qoldigi",
        "qoldiq",
        "sotilgan",
        "top",
        "tugab",
        "tugayapti",
        "zaxirasi",
    },
    "supplier": {
        "beruvchi",
        "qarz",
        "qarzi",
        "supplier",
        "taminotchi",
        "yetkazib",
    },
    "branch": {
        "branch",
        "branchda",
        "branchida",
        "filial",
        "filialda",
        "filialida",
    },
    "warehouse": {
        "ombor",
        "omborda",
        "omborida",
        "sklad",
        "warehouse",
        "warehouseda",
        "warehouseida",
    },
}

LOCATION_STOPWORDS = (
    COMMON_STOPWORDS
    | DATE_STOPWORDS
    | {
        "aktivligini",
        "asosida",
        "boyicha",
        "da",
        "dagi",
        "ichida",
        "kassir",
        "kassirlar",
        "ko",
        "rsat",
        "savdo",
        "savdoni",
        "sotilgan",
        "tushum",
    }
)
BRANCH_MARKERS = {"branch", "branchda", "branchida", "filial", "filialda", "filialida"}
WAREHOUSE_MARKERS = {
    "ombor",
    "omborda",
    "omborida",
    "sklad",
    "warehouse",
    "warehouseda",
    "warehouseida",
}


def _id(value) -> str:
    return str(value)


def _digits(value: str) -> str:
    return re.sub(r"\D+", "", value or "")


def _date_to_string(value: date) -> str:
    return value.isoformat()


def _date_result(single_date: date | None = None, date_from: date | None = None, date_to: date | None = None) -> dict:
    if single_date is not None:
        serialized = _date_to_string(single_date)
        return {"date": serialized, "date_from": serialized, "date_to": serialized}
    if date_from is not None and date_to is not None:
        start = _date_to_string(date_from)
        end = _date_to_string(date_to)
        return {"date_range": {"from": start, "to": end}, "date_from": start, "date_to": end}
    return {}


def similarity_score(query: str, candidate: str) -> float:
    normalized_query = normalize_text(query)
    normalized_candidate = normalize_text(candidate)
    if not normalized_query or not normalized_candidate:
        return 0.0
    if normalized_query == normalized_candidate:
        return 100.0
    if fuzz is not None:
        return float(fuzz.WRatio(normalized_query, normalized_candidate))
    if normalized_query in normalized_candidate or normalized_candidate in normalized_query:
        return 90.0

    shorter, longer = sorted(
        (normalized_query, normalized_candidate),
        key=len,
    )
    full_score = SequenceMatcher(None, normalized_query, normalized_candidate).ratio()
    partial_score = 0.0
    if len(shorter) <= len(longer):
        for index in range(0, len(longer) - len(shorter) + 1):
            window = longer[index : index + len(shorter)]
            partial_score = max(
                partial_score,
                SequenceMatcher(None, shorter, window).ratio(),
            )
    return max(full_score, partial_score) * 100


def build_display_name(obj, fields: tuple[str, ...] = ("name",)) -> str:
    if hasattr(obj, "get_full_name"):
        full_name = obj.get_full_name()
        if full_name:
            return full_name

    values = []
    for field in fields:
        value = getattr(obj, field, "")
        if value:
            values.append(str(value))
    if values:
        return " ".join(values)
    return str(obj)


def safe_get_model_objects(app_label: str, model_name: str):
    try:
        model = apps.get_model(app_label, model_name)
    except LookupError:
        return None
    return model.objects.all()


def _with_active_filter(queryset):
    if queryset is not None and hasattr(queryset.model, "is_active"):
        return queryset.filter(is_active=True)
    return queryset


def _scope_branch_queryset(queryset, user, branch_lookup: str):
    if queryset is None or user is None:
        return queryset
    try:
        from apps.accounts.permissions import filter_queryset_by_branch_scope
    except ImportError:
        return queryset
    return filter_queryset_by_branch_scope(queryset, user, branch_lookup)


def _branch_queryset(user=None):
    queryset = _with_active_filter(safe_get_model_objects("stores", "Branch"))
    return _scope_branch_queryset(queryset, user, "id")


def _warehouse_queryset(user=None):
    queryset = _with_active_filter(safe_get_model_objects("inventory", "Warehouse"))
    if queryset is not None:
        queryset = queryset.select_related("branch", "branch__store")
    return _scope_branch_queryset(queryset, user, "branch_id")


def _candidate_aliases(obj, display_fields: tuple[str, ...]) -> list[str]:
    aliases = [build_display_name(obj, display_fields)]
    for field in display_fields:
        value = getattr(obj, field, "")
        if value:
            aliases.append(str(value))
    return aliases


def _location_alias_matches(message: str, queryset, alias_builder) -> tuple[object | None, float, str, str]:
    normalized = normalize_text(message)
    if queryset is None:
        return None, 0.0, "not_supported", ""
    for obj in queryset[:250]:
        for alias in alias_builder(obj):
            normalized_alias = normalize_text(alias)
            if normalized_alias and normalized_alias in normalized:
                return obj, 100.0, "matched", normalized_alias
    return None, 0.0, "not_found", ""


def _numbered_location_match(message: str, queryset, markers: tuple[str, ...]):
    if queryset is None:
        return None, None, "not_supported", ""

    normalized = normalize_text(message)
    marker_pattern = "|".join(re.escape(marker) for marker in markers)
    patterns = (
        rf"\b(?:{marker_pattern})\s*(\d+)\b",
        rf"\b(\d+)\s*(?:{marker_pattern})\b",
    )
    for pattern in patterns:
        match = re.search(pattern, normalized)
        if not match:
            continue
        number = int(match.group(1))
        if number <= 0:
            return None, number, "not_found", match.group(0)
        ordered = list(queryset.order_by("created_at", "id")[:number])
        if len(ordered) >= number:
            return ordered[number - 1], number, "matched", match.group(0)
        return None, number, "not_found", match.group(0)
    return None, None, "missing", ""


def _clean_location_tokens(tokens: list[str]) -> list[str]:
    return [
        token
        for token in tokens
        if token not in LOCATION_STOPWORDS and not token.isdigit() and len(token) > 1
    ]


def _location_query_from_marker(message: str, markers: set[str]) -> str:
    tokens = normalize_text(message).split()
    for index, token in enumerate(tokens):
        if token not in markers:
            continue
        previous_tokens = []
        for previous in reversed(tokens[max(0, index - 4) : index]):
            if previous in LOCATION_STOPWORDS or previous in BRANCH_MARKERS | WAREHOUSE_MARKERS:
                if previous_tokens:
                    break
                continue
            previous_tokens.append(previous)
        previous_tokens.reverse()
        cleaned_previous = _clean_location_tokens(previous_tokens)
        if cleaned_previous:
            return " ".join(cleaned_previous)

        next_tokens = []
        for following in tokens[index + 1 : index + 5]:
            if following in LOCATION_STOPWORDS or following in BRANCH_MARKERS | WAREHOUSE_MARKERS:
                if next_tokens:
                    break
                continue
            next_tokens.append(following)
        cleaned_next = _clean_location_tokens(next_tokens)
        if cleaned_next:
            return " ".join(cleaned_next)
    return ""


def _has_location_marker(message: str, markers: set[str]) -> bool:
    tokens = set(normalize_text(message).split())
    return bool(tokens.intersection(markers))


def best_match(
    raw_query: str,
    queryset,
    *,
    display_fields: tuple[str, ...],
    alias_builder=None,
    threshold: float = 70.0,
    limit: int = 250,
):
    query = normalize_text(raw_query)
    if not query or queryset is None:
        return None, 0.0, "missing" if not query else "not_supported"

    best_obj = None
    best_score = 0.0
    for obj in queryset[:limit]:
        aliases = (
            alias_builder(obj)
            if alias_builder is not None
            else _candidate_aliases(obj, display_fields)
        )
        for alias in aliases:
            score = similarity_score(query, alias)
            if normalize_text(alias) == query:
                score = 100.0
            if score > best_score:
                best_obj = obj
                best_score = score

    if best_obj is None:
        return None, 0.0, "not_found"
    if best_score >= threshold:
        return best_obj, round(best_score, 2), "matched"
    return None, round(best_score, 2), "uncertain"


def remove_intent_words(
    message: str,
    intent: str,
    extra_stopwords: set[str] | None = None,
) -> str:
    stopwords = set(COMMON_STOPWORDS) | set(DATE_STOPWORDS)
    if extra_stopwords:
        stopwords |= extra_stopwords

    tokens = [
        token
        for token in normalize_text(message).split()
        if token not in stopwords and len(token) > 1
    ]
    return " ".join(tokens).strip()


def _month_range(year: int, month: int) -> tuple[date, date]:
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, 1), date(year, month, last_day)


def extract_date_entities(message: str) -> dict:
    today = timezone.localdate()
    normalized = normalize_text(message)

    iso_match = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", message or "")
    if iso_match:
        try:
            parsed = date.fromisoformat(iso_match.group(0))
        except ValueError:
            parsed = None
        if parsed:
            return _date_result(single_date=parsed)

    dotted_match = re.search(r"\b(\d{2})\.(\d{2})\.(\d{4})\b", message or "")
    if dotted_match:
        day, month, year = map(int, dotted_match.groups())
        try:
            return _date_result(single_date=date(year, month, day))
        except ValueError:
            pass

    last_days_match = re.search(r"\b(?:oxirgi|last)\s+(\d+)\s+(?:kun|kunda|days?)", normalized)
    if last_days_match:
        days = max(1, int(last_days_match.group(1)))
        return _date_result(date_from=today - timedelta(days=days - 1), date_to=today)

    if "otgan hafta" in normalized:
        this_week_start = today - timedelta(days=today.weekday())
        previous_week_start = this_week_start - timedelta(days=7)
        previous_week_end = this_week_start - timedelta(days=1)
        return _date_result(date_from=previous_week_start, date_to=previous_week_end)
    if (
        "bu hafta" in normalized
        or "shu hafta" in normalized
        or "this week" in normalized
    ):
        week_start = today - timedelta(days=today.weekday())
        return _date_result(date_from=week_start, date_to=today)
    if "otgan oy" in normalized:
        first_this_month = today.replace(day=1)
        previous_month_end = first_this_month - timedelta(days=1)
        previous_month_start, _ = _month_range(
            previous_month_end.year,
            previous_month_end.month,
        )
        return _date_result(date_from=previous_month_start, date_to=previous_month_end)
    if (
        "bu oy" in normalized
        or "shu oy" in normalized
        or "this month" in normalized
        or intent_implies_month(normalized)
    ):
        return _date_result(date_from=today.replace(day=1), date_to=today)

    if "kecha" in normalized or "yesterday" in normalized:
        return _date_result(single_date=today - timedelta(days=1))
    if "ertaga" in normalized:
        return _date_result(single_date=today + timedelta(days=1))
    if "bugun" in normalized or "bugungi" in normalized or "today" in normalized:
        return _date_result(single_date=today)
    return {}


def intent_implies_month(normalized_message: str) -> bool:
    return "oylik" in normalized_message


def _add_match(result: dict, entity_type: str, status: str, score: float, query: str):
    result.setdefault("matches", {})[entity_type] = {
        "status": status,
        "score": score,
        "query": query,
    }


def _product_aliases(product) -> list[str]:
    aliases = [
        product.name,
        product.sku,
        product.barcode,
        getattr(product.category, "name", ""),
        getattr(product.brand, "name", ""),
    ]
    try:
        aliases.extend(product.barcodes.values_list("code", flat=True))
    except Exception:
        pass
    return [alias for alias in aliases if alias]


def _branch_aliases(branch) -> list[str]:
    return [
        value
        for value in (
            branch.name,
            str(branch),
            getattr(branch.store, "name", ""),
            f"{getattr(branch.store, 'name', '')} {branch.name}".strip(),
        )
        if value
    ]


def _warehouse_aliases(warehouse) -> list[str]:
    return [
        value
        for value in (
            warehouse.name,
            str(warehouse),
            f"{getattr(warehouse.branch, 'name', '')} {warehouse.name}".strip(),
        )
        if value
    ]


def _remove_location_terms(raw_query: str, result: dict) -> str:
    tokens = normalize_text(raw_query).split()
    removable: set[str] = set()
    for prefix in ("branch", "warehouse"):
        for key in (
            f"raw_{prefix}_query",
            f"{prefix}_name",
        ):
            removable.update(normalize_text(result.get(key, "")).split())
    cleaned = [token for token in tokens if token not in removable]
    return " ".join(cleaned).strip()


def _match_branch(result: dict, message: str, user=None):
    if not _has_location_marker(message, BRANCH_MARKERS):
        return
    queryset = _branch_queryset(user=user)
    branch, number, status, raw_number_query = _numbered_location_match(
        message,
        queryset,
        tuple(BRANCH_MARKERS),
    )
    if number is not None:
        raw_query = raw_number_query or f"filial {number}"
        if branch is None:
            result.update(
                {
                    "branch_name": None,
                    "branch_id": None,
                    "branch_number": number,
                    "raw_branch_query": raw_query,
                    "branch_match_status": status,
                }
            )
            _add_match(result, "branch", status, 0.0, raw_query)
            return
        result.update(
            {
                "branch_name": branch.name,
                "branch_id": _id(branch.id),
                "branch_number": number,
                "raw_branch_query": raw_query,
                "branch_match_score": 100.0,
            }
        )
        _add_match(result, "branch", status, 100.0, raw_query)
        return

    branch, score, status, raw_alias_query = _location_alias_matches(
        message,
        queryset,
        _branch_aliases,
    )
    raw_query = raw_alias_query or _location_query_from_marker(message, BRANCH_MARKERS)
    if branch is None and raw_query:
        branch, score, status = best_match(
            raw_query,
            queryset,
            display_fields=("name",),
            alias_builder=_branch_aliases,
        )

    if not raw_query and branch is None:
        return
    if branch is None:
        result.update(
            {
                "branch_name": None,
                "branch_id": None,
                "raw_branch_query": raw_query,
                "branch_match_score": score,
                "branch_match_status": status,
            }
        )
        _add_match(result, "branch", status, score, raw_query)
        return

    result.update(
        {
            "branch_name": branch.name,
            "branch_id": _id(branch.id),
            "raw_branch_query": raw_query or branch.name,
            "branch_match_score": score,
        }
    )
    _add_match(result, "branch", "matched", score, raw_query or branch.name)


def _match_warehouse(result: dict, message: str, user=None):
    if not _has_location_marker(message, WAREHOUSE_MARKERS):
        return
    queryset = _warehouse_queryset(user=user)
    branch_id = result.get("branch_id")
    if queryset is not None and branch_id:
        queryset = queryset.filter(branch_id=branch_id)

    warehouse, number, status, raw_number_query = _numbered_location_match(
        message,
        queryset,
        tuple(WAREHOUSE_MARKERS),
    )
    if number is not None:
        raw_query = raw_number_query or f"ombor {number}"
        if warehouse is None:
            result.update(
                {
                    "warehouse_name": None,
                    "warehouse_id": None,
                    "warehouse_number": number,
                    "raw_warehouse_query": raw_query,
                    "warehouse_match_status": status,
                }
            )
            _add_match(result, "warehouse", status, 0.0, raw_query)
            return
        result.update(
            {
                "warehouse_name": warehouse.name,
                "warehouse_id": _id(warehouse.id),
                "warehouse_number": number,
                "warehouse_branch_id": _id(warehouse.branch_id),
                "warehouse_branch_name": warehouse.branch.name,
                "raw_warehouse_query": raw_query,
                "warehouse_match_score": 100.0,
            }
        )
        if not result.get("branch_id"):
            result["branch_id"] = _id(warehouse.branch_id)
            result["branch_name"] = warehouse.branch.name
        _add_match(result, "warehouse", status, 100.0, raw_query)
        return

    warehouse, score, status, raw_alias_query = _location_alias_matches(
        message,
        queryset,
        _warehouse_aliases,
    )
    raw_query = raw_alias_query or _location_query_from_marker(message, WAREHOUSE_MARKERS)
    if warehouse is None and raw_query:
        warehouse, score, status = best_match(
            raw_query,
            queryset,
            display_fields=("name",),
            alias_builder=_warehouse_aliases,
        )

    if not raw_query and warehouse is None:
        return
    if warehouse is None:
        result.update(
            {
                "warehouse_name": None,
                "warehouse_id": None,
                "raw_warehouse_query": raw_query,
                "warehouse_match_score": score,
                "warehouse_match_status": status,
            }
        )
        _add_match(result, "warehouse", status, score, raw_query)
        return

    result.update(
        {
            "warehouse_name": warehouse.name,
            "warehouse_id": _id(warehouse.id),
            "warehouse_branch_id": _id(warehouse.branch_id),
            "warehouse_branch_name": warehouse.branch.name,
            "raw_warehouse_query": raw_query or warehouse.name,
            "warehouse_match_score": score,
        }
    )
    if not result.get("branch_id"):
        result["branch_id"] = _id(warehouse.branch_id)
        result["branch_name"] = warehouse.branch.name
    _add_match(result, "warehouse", "matched", score, raw_query or warehouse.name)


def _match_product(result: dict, message: str, intent: str):
    raw_query = remove_intent_words(
        message,
        intent,
        ENTITY_STOPWORDS["product"],
    )
    raw_query = _remove_location_terms(raw_query, result)
    if not raw_query and intent in {INTENT_PRODUCT_STOCK, INTENT_PRODUCT_PRICE}:
        result.update(
            {
                "product_name": None,
                "product_id": None,
                "raw_product_query": raw_query,
                "product_match_status": "missing",
            }
        )
        _add_match(result, "product", "missing", 0.0, raw_query)
        return
    if not raw_query:
        return

    queryset = _with_active_filter(safe_get_model_objects("catalog", "Product"))
    if queryset is not None:
        queryset = queryset.select_related("category", "brand", "unit").prefetch_related(
            "barcodes"
        )

    product, score, status = best_match(
        raw_query,
        queryset,
        display_fields=("name", "sku", "barcode"),
        alias_builder=_product_aliases,
    )
    if product is None:
        result.update(
            {
                "product_name": None,
                "product_id": None,
                "raw_product_query": raw_query,
                "product_match_score": score,
                "product_match_status": status,
            }
        )
        _add_match(result, "product", status, score, raw_query)
        return

    result.update(
        {
            "product_name": product.name,
            "product_id": _id(product.id),
            "raw_product_query": raw_query,
            "product_match_score": score,
        }
    )
    _add_match(result, "product", status, score, raw_query)


def _match_customer(result: dict, message: str, intent: str):
    raw_query = remove_intent_words(
        message,
        intent,
        ENTITY_STOPWORDS["customer"],
    )
    if not raw_query:
        return

    queryset = _with_active_filter(safe_get_model_objects("sales", "Customer"))
    phone_digits = _digits(message)
    if queryset is not None and len(phone_digits) >= 5:
        customer = queryset.filter(
            Q(phone__icontains=phone_digits) | Q(extra_phone__icontains=phone_digits)
        ).first()
        if customer:
            result.update(
                {
                    "customer_name": customer.full_name,
                    "customer_id": _id(customer.id),
                    "raw_customer_query": raw_query,
                    "customer_match_score": 100.0,
                }
            )
            _add_match(result, "customer", "matched", 100.0, raw_query)
            return

    customer, score, status = best_match(
        raw_query,
        queryset,
        display_fields=("full_name", "phone", "extra_phone"),
    )
    if customer is None:
        result.update(
            {
                "customer_name": None,
                "customer_id": None,
                "raw_customer_query": raw_query,
                "customer_match_score": score,
                "customer_match_status": status,
            }
        )
        _add_match(result, "customer", status, score, raw_query)
        return

    result.update(
        {
            "customer_name": customer.full_name,
            "customer_id": _id(customer.id),
            "raw_customer_query": raw_query,
            "customer_match_score": score,
        }
    )
    _add_match(result, "customer", status, score, raw_query)


def _user_aliases(user) -> list[str]:
    full_name = user.get_full_name()
    aliases = [
        full_name,
        user.email,
        user.phone,
        user.role,
        user.first_name,
        user.last_name,
    ]
    return [alias for alias in aliases if alias]


def _match_cashier(result: dict, message: str, intent: str):
    raw_query = remove_intent_words(
        message,
        intent,
        ENTITY_STOPWORDS["cashier"],
    )
    email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", message or "")
    if email_match:
        raw_query = email_match.group(0)
    if not raw_query:
        return

    queryset = _with_active_filter(safe_get_model_objects("accounts", "User"))
    if queryset is not None and "@" in raw_query:
        user = queryset.filter(email__iexact=raw_query).first()
        if user:
            result.update(
                {
                    "cashier_name": build_display_name(
                        user,
                        ("first_name", "last_name", "email"),
                    ),
                    "cashier_id": _id(user.id),
                    "raw_cashier_query": raw_query,
                    "cashier_match_score": 100.0,
                }
            )
            _add_match(result, "cashier", "matched", 100.0, raw_query)
            return

    cashier, score, status = best_match(
        raw_query,
        queryset,
        display_fields=("first_name", "last_name", "email", "phone", "role"),
        alias_builder=_user_aliases,
    )
    if cashier is None:
        result.update(
            {
                "cashier_name": None,
                "cashier_id": None,
                "raw_cashier_query": raw_query,
                "cashier_match_score": score,
                "cashier_match_status": status,
            }
        )
        _add_match(result, "cashier", status, score, raw_query)
        return

    result.update(
        {
            "cashier_name": build_display_name(
                cashier,
                ("first_name", "last_name", "email"),
            ),
            "cashier_id": _id(cashier.id),
            "raw_cashier_query": raw_query,
            "cashier_match_score": score,
        }
    )
    _add_match(result, "cashier", status, score, raw_query)


def _match_category(result: dict, message: str, intent: str):
    raw_query = remove_intent_words(
        message,
        intent,
        ENTITY_STOPWORDS["category"],
    )
    if not raw_query:
        return

    queryset = _with_active_filter(safe_get_model_objects("catalog", "Category"))
    category, score, status = best_match(
        raw_query,
        queryset,
        display_fields=("name", "slug"),
    )
    if category is None:
        _add_match(result, "category", status, score, raw_query)
        return

    result.update(
        {
            "category_name": category.name,
            "category_id": _id(category.id),
            "raw_category_query": raw_query,
            "category_match_score": score,
        }
    )
    _add_match(result, "category", status, score, raw_query)


def _supplier_aliases(supplier) -> list[str]:
    return [
        value
        for value in (
            supplier.company_name,
            supplier.full_name,
            supplier.phone,
            supplier.extra_phone,
            supplier.email,
            supplier.inn_or_tax_number,
        )
        if value
    ]


def _match_supplier(result: dict, message: str, intent: str):
    raw_query = remove_intent_words(
        message,
        intent,
        ENTITY_STOPWORDS["supplier"],
    )
    if not raw_query:
        return

    queryset = _with_active_filter(safe_get_model_objects("purchases", "Supplier"))
    phone_digits = _digits(message)
    if queryset is not None and len(phone_digits) >= 5:
        supplier = queryset.filter(
            Q(phone__icontains=phone_digits) | Q(extra_phone__icontains=phone_digits)
        ).first()
        if supplier:
            result.update(
                {
                    "supplier_name": supplier.company_name,
                    "supplier_id": _id(supplier.id),
                    "raw_supplier_query": raw_query,
                    "supplier_match_score": 100.0,
                }
            )
            _add_match(result, "supplier", "matched", 100.0, raw_query)
            return

    supplier, score, status = best_match(
        raw_query,
        queryset,
        display_fields=(
            "company_name",
            "full_name",
            "phone",
            "extra_phone",
            "email",
            "inn_or_tax_number",
        ),
        alias_builder=_supplier_aliases,
    )
    if supplier is None:
        _add_match(result, "supplier", status, score, raw_query)
        return

    result.update(
        {
            "supplier_name": supplier.company_name,
            "supplier_id": _id(supplier.id),
            "raw_supplier_query": raw_query,
            "supplier_match_score": score,
        }
    )
    _add_match(result, "supplier", status, score, raw_query)


def extract_entities(message: str, intent: str, user=None) -> dict:
    result: dict = {
        "raw_query": normalize_text(message),
        "matches": {},
    }
    result.update(extract_date_entities(message))

    if intent in BRANCH_INTENTS:
        _match_branch(result, message, user=user)
    if intent in WAREHOUSE_INTENTS:
        _match_warehouse(result, message, user=user)
    if intent in PRODUCT_INTENTS:
        _match_product(result, message, intent)
    if intent in CUSTOMER_INTENTS:
        _match_customer(result, message, intent)
    if intent in CASHIER_INTENTS:
        _match_cashier(result, message, intent)
    if intent in CATEGORY_INTENTS:
        _match_category(result, message, intent)
    if intent in SUPPLIER_INTENTS:
        _match_supplier(result, message, intent)

    if not result["matches"]:
        result.pop("matches")
    return result
