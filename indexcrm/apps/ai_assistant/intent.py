from collections import defaultdict

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
from apps.ai_assistant.text import normalize_text

EXACT_PHRASE_SCORE = 4.0
KEYWORD_SCORE = 1.0
STRONG_KEYWORD_SCORE = 2.0
COMBINATION_SCORE = 3.0
UNKNOWN_THRESHOLD = 2.5
CONFIDENCE_FULL_SCORE = 9.0

INTENT_PRIORITY = {
    INTENT_HELP: 100,
    INTENT_FINANCE_SUMMARY: 90,
    INTENT_CUSTOMER_DEBT: 85,
    INTENT_CASHIER_ACTIVITY: 80,
    INTENT_SALES_MONTH: 75,
    INTENT_SALES_TODAY: 70,
    INTENT_LOW_STOCK: 65,
    INTENT_TOP_PRODUCTS: 60,
    INTENT_PRODUCT_PRICE: 55,
    INTENT_PRODUCT_STOCK: 50,
    INTENT_REPORTS_SUMMARY: 45,
}

INTENT_RULES = {
    INTENT_SALES_TODAY: {
        "phrases": (
            "bugun savdo",
            "bugungi savdo",
            "bugungi tushum",
            "bugun qancha sotildi",
            "bugun nechta savdo",
            "kunlik savdo",
            "bugungi kassadagi tushum",
        ),
        "strong_keywords": ("tushum", "savdo", "sotildi"),
        "keywords": ("bugun", "bugungi", "kunlik", "kassa", "kassadagi", "nechta"),
        "combinations": (
            ("bugun", "savdo"),
            ("bugungi", "tushum"),
            ("bugun", "sotildi"),
            ("kunlik", "savdo"),
        ),
    },
    INTENT_SALES_MONTH: {
        "phrases": (
            "bu oy savdo",
            "shu oy savdo",
            "shu hafta savdo",
            "oxirgi 7 kun savdo",
            "oxirgi 30 kun savdo",
            "oylik savdo",
            "oy boyicha savdo",
            "bu oy tushum",
            "oylik tushum",
            "oy davomida qancha sotildi",
        ),
        "strong_keywords": ("oylik", "savdo", "savdoni", "tushum", "sotildi"),
        "keywords": ("hafta", "kun", "oy", "oxirgi", "shu", "bu", "davomida", "boyicha"),
        "combinations": (
            ("bu", "oy", "savdo"),
            ("shu", "oy", "savdo"),
            ("shu", "hafta", "savdo"),
            ("oxirgi", "kun", "savdo"),
            ("oxirgi", "kunda", "savdoni"),
            ("bu", "oy", "tushum"),
            ("oylik", "savdo"),
            ("oylik", "tushum"),
            ("oy", "sotildi"),
        ),
    },
    INTENT_PRODUCT_STOCK: {
        "phrases": (
            "mahsulot qoldigi",
            "omborda qancha",
            "qancha qoldi",
            "qancha qoldigi",
        ),
        "strong_keywords": ("qoldiq", "qoldigi", "sklad", "zaxira", "mavjudmi"),
        "keywords": ("qoldi", "ombor", "omborda", "qancha", "mavjud", "bor"),
        "combinations": (
            ("qoldigi", "qancha"),
            ("qoldiq", "qancha"),
            ("omborda", "qancha"),
            ("zaxira", "qancha"),
        ),
    },
    INTENT_LOW_STOCK: {
        "phrases": (
            "kam qolgan",
            "minimum qoldiq",
            "qoldigi kam",
            "zaxirasi kam",
            "tugab qolgan",
        ),
        "strong_keywords": ("tugayapti", "minimum", "tugab", "kam"),
        "keywords": ("qolgan", "qoldiq", "qoldigi", "zaxirasi"),
        "combinations": (
            ("kam", "qolgan"),
            ("qoldigi", "kam"),
            ("zaxirasi", "kam"),
            ("tugab", "qolgan"),
        ),
    },
    INTENT_TOP_PRODUCTS: {
        "phrases": (
            "eng kop sotilgan",
            "top mahsulot",
            "kop sotilgan",
            "kop sotilgan mahsulot",
        ),
        "strong_keywords": ("bestseller", "top"),
        "keywords": ("eng", "kop", "sotilgan", "mahsulot", "mahsulotlar"),
        "combinations": (
            ("eng", "kop", "sotilgan"),
            ("kop", "sotilgan", "mahsulot"),
            ("top", "mahsulot"),
        ),
    },
    INTENT_PRODUCT_PRICE: {
        "phrases": (
            "qancha turadi",
            "sotuv narxi",
            "necha pul",
            "narxini ayt",
        ),
        "strong_keywords": ("narxi", "narx", "bahosi"),
        "keywords": ("turadi", "sotuv", "necha", "pul", "ayt"),
        "combinations": (
            ("qancha", "turadi"),
            ("necha", "pul"),
            ("sotuv", "narxi"),
            ("narxini", "ayt"),
        ),
    },
    INTENT_CASHIER_ACTIVITY: {
        "phrases": (
            "bugun qaysi kassir",
            "bugungi kassirlar aktivligini",
            "kassirlar aktivligini",
            "kassir qancha sotdi",
            "kassir faoliyati",
            "smena ochilganmi",
        ),
        "strong_keywords": ("kassir", "kassirlar", "smena"),
        "keywords": (
            "aktivlik",
            "aktivligini",
            "faoliyati",
            "ochilganmi",
            "ishlayapti",
            "sotdi",
            "bugun",
        ),
        "combinations": (
            ("qaysi", "kassir"),
            ("kassir", "bugun"),
            ("kassirlar", "aktivligini"),
            ("kassir", "sotdi"),
            ("smena", "ochilganmi"),
        ),
    },
    INTENT_FINANCE_SUMMARY: {
        "phrases": (
            "sof foyda",
            "bugungi foyda",
            "bu oy foyda",
        ),
        "strong_keywords": ("foyda", "daromad", "xarajat", "moliya", "balans"),
        "keywords": ("sof", "bugungi", "bugun", "oy"),
        "combinations": (
            ("bugungi", "foyda"),
            ("bugun", "foyda"),
            ("bu", "oy", "foyda"),
            ("sof", "foyda"),
        ),
    },
    INTENT_CUSTOMER_DEBT: {
        "phrases": (
            "mijoz qarzi",
            "kim qarzdor",
            "qarzdor mijoz",
        ),
        "strong_keywords": ("qarz", "qarzi", "qarzdor", "nasiya", "nasiyaga"),
        "keywords": ("mijoz", "kim", "qancha"),
        "combinations": (
            ("mijoz", "qarzi"),
            ("kim", "qarzdor"),
            ("qarzdor", "mijoz"),
        ),
    },
    INTENT_REPORTS_SUMMARY: {
        "phrases": (
            "umumiy hisobot",
            "kunlik hisobot",
            "oylik hisobot",
        ),
        "strong_keywords": ("hisobot", "report", "statistika"),
        "keywords": ("umumiy", "kunlik", "oylik", "menga", "ber"),
        "combinations": (
            ("menga", "hisobot"),
            ("umumiy", "hisobot"),
            ("kunlik", "hisobot"),
            ("oylik", "hisobot"),
        ),
    },
    INTENT_HELP: {
        "phrases": (
            "yordam",
            "help",
            "imkoniyatlaring",
            "nima qila olasan",
            "qanday savollar beraman",
            "qanday savollar bersam boladi",
            "imkoniyatlaring qanday",
        ),
        "strong_keywords": ("yordam", "help", "imkoniyatlaring"),
        "keywords": ("qanday", "savollar", "beraman", "bersam", "boladi", "kerak"),
        "combinations": (
            ("nima", "qila", "olasan"),
            ("qanday", "savollar"),
            ("imkoniyatlaring", "qanday"),
            ("yordam", "kerak"),
        ),
    },
}


def _contains_token(tokens: set[str], keyword: str) -> bool:
    return keyword in tokens if " " not in keyword else False


def _phrase_matches(text: str, phrase: str) -> bool:
    return f" {phrase} " in f" {text} "


def _score_intent(text: str, tokens: set[str], config: dict) -> tuple[float, list[str]]:
    score = 0.0
    matched = []

    for phrase in config.get("phrases", ()):
        normalized_phrase = normalize_text(phrase)
        if _phrase_matches(text, normalized_phrase):
            score += EXACT_PHRASE_SCORE
            matched.append(normalized_phrase)

    for keyword in config.get("strong_keywords", ()):
        normalized_keyword = normalize_text(keyword)
        if _contains_token(tokens, normalized_keyword):
            score += STRONG_KEYWORD_SCORE
            matched.append(normalized_keyword)

    for keyword in config.get("keywords", ()):
        normalized_keyword = normalize_text(keyword)
        if _contains_token(tokens, normalized_keyword):
            score += KEYWORD_SCORE
            matched.append(normalized_keyword)

    for combination in config.get("combinations", ()):
        normalized_terms = tuple(normalize_text(term) for term in combination)
        if all(term in tokens for term in normalized_terms):
            score += COMBINATION_SCORE
            matched.append(" ".join(normalized_terms))

    return score, list(dict.fromkeys(matched))


def detect_intent(message: str) -> dict:
    text = normalize_text(message)
    if not text:
        return {
            "intent": INTENT_UNKNOWN,
            "confidence": 0.0,
            "matched_keywords": [],
            "scores": {},
        }

    tokens = set(text.split())
    scores: dict[str, float] = {}
    matches: dict[str, list[str]] = {}
    aggregate_matches = defaultdict(list)

    for intent, config in INTENT_RULES.items():
        score, matched_keywords = _score_intent(text, tokens, config)
        if score:
            scores[intent] = score
            matches[intent] = matched_keywords
            aggregate_matches[intent].extend(matched_keywords)

    if not scores:
        return {
            "intent": INTENT_UNKNOWN,
            "confidence": 0.0,
            "matched_keywords": [],
            "scores": {},
        }

    intent, score = max(
        scores.items(),
        key=lambda item: (item[1], INTENT_PRIORITY.get(item[0], 0)),
    )
    normalized_scores = {
        candidate_intent: round(candidate_score, 2)
        for candidate_intent, candidate_score in sorted(
            scores.items(),
            key=lambda item: (-item[1], -INTENT_PRIORITY.get(item[0], 0)),
        )
    }

    if score < UNKNOWN_THRESHOLD:
        return {
            "intent": INTENT_UNKNOWN,
            "confidence": 0.0,
            "matched_keywords": [],
            "scores": normalized_scores,
        }

    confidence = min(0.99, round(score / CONFIDENCE_FULL_SCORE, 2))
    return {
        "intent": intent,
        "confidence": confidence,
        "matched_keywords": list(dict.fromkeys(aggregate_matches[intent])),
        "scores": normalized_scores,
    }
