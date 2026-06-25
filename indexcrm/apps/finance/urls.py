from rest_framework.routers import DefaultRouter

from apps.finance.views import (
    CashBoxViewSet,
    CashTransactionViewSet,
    DailyClosingViewSet,
    ExpenseCategoryViewSet,
    ExpenseViewSet,
    IncomeViewSet,
)

router = DefaultRouter()
router.register("cashboxes", CashBoxViewSet, basename="cashbox")
router.register(
    "cash-transactions",
    CashTransactionViewSet,
    basename="cash-transaction",
)
router.register(
    "expense-categories",
    ExpenseCategoryViewSet,
    basename="expense-category",
)
router.register("expenses", ExpenseViewSet, basename="expense")
router.register("incomes", IncomeViewSet, basename="income")
router.register("daily-closings", DailyClosingViewSet, basename="daily-closing")

urlpatterns = router.urls
