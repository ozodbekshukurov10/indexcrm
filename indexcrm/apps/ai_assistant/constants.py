ROLE_USER = "user"
ROLE_ASSISTANT = "assistant"
ROLE_SYSTEM = "system"

ROLE_CHOICES = (
    (ROLE_USER, "User"),
    (ROLE_ASSISTANT, "Assistant"),
    (ROLE_SYSTEM, "System"),
)

FEEDBACK_GOOD = "good"
FEEDBACK_BAD = "bad"

FEEDBACK_RATING_CHOICES = (
    (FEEDBACK_GOOD, "Good"),
    (FEEDBACK_BAD, "Bad"),
)

SOURCE_TOOL = "tool"
SOURCE_FALLBACK = "fallback"
SOURCE_PERMISSION_DENIED = "permission_denied"
SOURCE_NOT_SUPPORTED = "not_supported"
SOURCE_ERROR = "error"
SOURCE_HELP = "help"

SOURCE_TYPES = (
    SOURCE_TOOL,
    SOURCE_FALLBACK,
    SOURCE_PERMISSION_DENIED,
    SOURCE_NOT_SUPPORTED,
    SOURCE_ERROR,
    SOURCE_HELP,
)

SOURCE_CHOICES = tuple((source, source.replace("_", " ").title()) for source in SOURCE_TYPES)

INTENT_SALES_TODAY = "sales_today"
INTENT_SALES_MONTH = "sales_month"
INTENT_PRODUCT_STOCK = "product_stock"
INTENT_LOW_STOCK = "low_stock"
INTENT_TOP_PRODUCTS = "top_products"
INTENT_PRODUCT_PRICE = "product_price"
INTENT_CASHIER_ACTIVITY = "cashier_activity"
INTENT_FINANCE_SUMMARY = "finance_summary"
INTENT_CUSTOMER_DEBT = "customer_debt"
INTENT_REPORTS_SUMMARY = "reports_summary"
INTENT_HELP = "help"
INTENT_UNKNOWN = "unknown"

INTENTS = (
    INTENT_SALES_TODAY,
    INTENT_SALES_MONTH,
    INTENT_PRODUCT_STOCK,
    INTENT_LOW_STOCK,
    INTENT_TOP_PRODUCTS,
    INTENT_PRODUCT_PRICE,
    INTENT_CASHIER_ACTIVITY,
    INTENT_FINANCE_SUMMARY,
    INTENT_CUSTOMER_DEBT,
    INTENT_REPORTS_SUMMARY,
    INTENT_HELP,
    INTENT_UNKNOWN,
)

INTENT_CHOICES = tuple((intent, intent.replace("_", " ").title()) for intent in INTENTS)
