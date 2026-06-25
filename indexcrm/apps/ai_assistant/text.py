import re
import unicodedata

APOSTROPHE_VARIANTS = {
    "`": "'",
    "\u00b4": "'",
    "\u2018": "'",
    "\u2019": "'",
    "\u02bc": "'",
    "\u02bb": "'",
    "\u02b9": "'",
}


def normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text or "").lower()
    for source, target in APOSTROPHE_VARIANTS.items():
        normalized = normalized.replace(source, target)
    normalized = normalized.replace("o'", "o").replace("g'", "g")
    normalized = re.sub(r"[^\w\s]+", " ", normalized, flags=re.UNICODE)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized
