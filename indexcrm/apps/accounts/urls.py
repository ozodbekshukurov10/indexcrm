from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.accounts.views import (
    AccessPermissionViewSet,
    AccountSessionViewSet,
    AuditLogViewSet,
    FailedLoginAttemptViewSet,
    LoginHistoryViewSet,
    MeView,
    MyProfileView,
    PermissionGroupViewSet,
    RoleViewSet,
    SystemInstallationViewSet,
    UserProfileViewSet,
    UserRoleAssignmentViewSet,
    UserViewSet,
)

router = DefaultRouter()
router.register("users", UserViewSet, basename="account-user")
router.register("profiles", UserProfileViewSet, basename="account-profile")
router.register("roles", RoleViewSet, basename="account-role")
router.register("permissions", AccessPermissionViewSet, basename="account-permission")
router.register(
    "permission-groups",
    PermissionGroupViewSet,
    basename="account-permission-group",
)
router.register(
    "role-assignments",
    UserRoleAssignmentViewSet,
    basename="account-role-assignment",
)
router.register("login-history", LoginHistoryViewSet, basename="account-login-history")
router.register(
    "failed-login-attempts",
    FailedLoginAttemptViewSet,
    basename="account-failed-login-attempt",
)
router.register("sessions", AccountSessionViewSet, basename="account-session")
router.register("audit-logs", AuditLogViewSet, basename="account-audit-log")
router.register(
    "installations",
    SystemInstallationViewSet,
    basename="account-installation",
)

urlpatterns = [
    path("me/", MeView.as_view(), name="me"),
    path("me/profile/", MyProfileView.as_view(), name="me-profile"),
    *router.urls,
]
