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

SAFE_CASHIER_INTENTS = {
    INTENT_PRODUCT_STOCK,
    INTENT_PRODUCT_PRICE,
    INTENT_CASHIER_ACTIVITY,
    INTENT_HELP,
    INTENT_UNKNOWN,
}

MANAGER_INTENTS = {
    INTENT_SALES_TODAY,
    INTENT_SALES_MONTH,
    INTENT_PRODUCT_STOCK,
    INTENT_LOW_STOCK,
    INTENT_TOP_PRODUCTS,
    INTENT_PRODUCT_PRICE,
    INTENT_CASHIER_ACTIVITY,
    INTENT_CUSTOMER_DEBT,
    INTENT_HELP,
    INTENT_UNKNOWN,
}

ADMIN_ONLY_INTENTS = {INTENT_FINANCE_SUMMARY, INTENT_REPORTS_SUMMARY}


def can_use_intent(user, intent: str) -> bool:
    if not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False) or getattr(user, "is_staff", False):
        return True
    if intent == INTENT_UNKNOWN:
        return True

    try:
        from apps.accounts.models import UserRole
        from apps.accounts.permissions import user_has_minimum_role
    except ImportError:
        # If the role system changes, keep non-staff users on non-aggregate product facts.
        return intent in SAFE_CASHIER_INTENTS

    if user_has_minimum_role(user, UserRole.ADMIN):
        return True
    if intent in ADMIN_ONLY_INTENTS:
        return False
    if user_has_minimum_role(user, UserRole.MANAGER):
        return intent in MANAGER_INTENTS
    if user_has_minimum_role(user, UserRole.CASHIER):
        return intent in SAFE_CASHIER_INTENTS
    if intent in {INTENT_HELP, INTENT_UNKNOWN}:
        return True
    return False


def can_view_ai_admin_data(user) -> bool:
    if not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False) or getattr(user, "is_staff", False):
        return True
    try:
        from apps.accounts.models import UserRole
        from apps.accounts.permissions import user_has_minimum_role
    except ImportError:
        return False
    return user_has_minimum_role(user, UserRole.ADMIN)


def can_access_session(user, session) -> bool:
    if not getattr(user, "is_authenticated", False):
        return False
    return session.user_id == user.id or can_view_ai_admin_data(user)
