from apps.accounts.models import (
    AccountSession,
    AuditLog,
    FailedLoginAttempt,
    LoginHistory,
    Role,
    SystemInstallation,
    User,
    UserProfile,
    UserRoleAssignment,
)


def user_queryset():
    return User.objects.select_related("profile").prefetch_related(
        "role_assignments__role",
    )


def profile_queryset():
    return UserProfile.objects.select_related("user", "branch", "branch__store")


def role_queryset():
    return Role.objects.prefetch_related("permissions", "permission_groups")


def role_assignment_queryset():
    return UserRoleAssignment.objects.select_related(
        "user",
        "role",
        "branch",
        "assigned_by",
    )


def login_history_queryset():
    return LoginHistory.objects.select_related("user")


def failed_login_attempt_queryset():
    return FailedLoginAttempt.objects.all()


def account_session_queryset():
    return AccountSession.objects.select_related("user")


def audit_log_queryset():
    return AuditLog.objects.select_related("actor")


def system_installation_queryset():
    return SystemInstallation.objects.all()
