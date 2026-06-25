from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from rest_framework_simplejwt.views import (
    TokenRefreshView,
    TokenVerifyView,
)

from apps.accounts.views import AuditedTokenObtainPairView
from apps.common.views import HealthCheckView, SystemStatusView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    path("api/v1/health/", HealthCheckView.as_view(), name="health"),
    path("api/v1/system/status/", SystemStatusView.as_view(), name="system-status"),
    path(
        "api/v1/auth/token/",
        AuditedTokenObtainPairView.as_view(),
        name="token_obtain_pair",
    ),
    path(
        "api/v1/auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"
    ),
    path("api/v1/auth/token/verify/", TokenVerifyView.as_view(), name="token_verify"),
    path("api/accounts/", include("apps.accounts.urls")),
    path("api/v1/accounts/", include("apps.accounts.urls")),
    path("api/", include("apps.stores.urls")),
    path("api/", include("apps.catalog.urls")),
    path("api/", include("apps.inventory.urls")),
    path("api/", include("apps.purchases.urls")),
    path("api/", include("apps.sales.urls")),
    path("api/", include("apps.cashier.urls")),
    path("api/", include("apps.finance.urls")),
    path("api/", include("apps.reports.urls")),
    path("api/", include("apps.integrations.urls")),
    path("api/v1/", include("apps.stores.urls")),
    path("api/v1/", include("apps.catalog.urls")),
    path("api/v1/", include("apps.inventory.urls")),
    path("api/v1/", include("apps.purchases.urls")),
    path("api/v1/", include("apps.sales.urls")),
    path("api/v1/", include("apps.cashier.urls")),
    path("api/v1/", include("apps.finance.urls")),
    path("api/v1/", include("apps.reports.urls")),
    path("api/v1/", include("apps.integrations.urls")),
    path("api/v1/ai/", include("apps.ai_assistant.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
