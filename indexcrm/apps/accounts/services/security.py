from django.db import transaction
from django.utils import timezone

from apps.accounts.models import (
    AccountSession,
    AuditAction,
    AuditLog,
    FailedLoginAttempt,
    LoginHistory,
    LoginStatus,
    UserProfile,
)


def _authenticated_user(user):
    return user if getattr(user, "is_authenticated", False) else None


def _request_ip(request):
    if request is None:
        return None
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def _request_user_agent(request):
    if request is None:
        return ""
    return request.META.get("HTTP_USER_AGENT", "")


def ensure_user_profile(user):
    profile, _created = UserProfile.objects.get_or_create(user=user)
    return profile


def record_audit_log(
    *,
    actor=None,
    action: str,
    entity_type: str = "",
    entity_id=None,
    object_repr: str = "",
    summary: str = "",
    metadata=None,
    request=None,
) -> AuditLog:
    return AuditLog.objects.create(
        actor=_authenticated_user(actor),
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        object_repr=object_repr[:255],
        summary=summary[:255],
        metadata=metadata or {},
        ip_address=_request_ip(request),
        user_agent=_request_user_agent(request),
    )


@transaction.atomic
def record_successful_login(*, user, identifier: str = "", request=None, token_jti=""):
    login_history = LoginHistory.objects.create(
        user=user,
        identifier=identifier or user.email,
        status=LoginStatus.SUCCESS,
        ip_address=_request_ip(request),
        user_agent=_request_user_agent(request),
    )
    account_session = AccountSession.objects.create(
        user=user,
        session_key=getattr(getattr(request, "session", None), "session_key", "") or "",
        token_jti=token_jti or "",
        ip_address=_request_ip(request),
        user_agent=_request_user_agent(request),
        last_seen_at=timezone.now(),
    )
    record_audit_log(
        actor=user,
        action=AuditAction.LOGIN,
        entity_type="accounts.User",
        entity_id=user.id,
        object_repr=user.email,
        summary="User logged in.",
        request=request,
    )
    return login_history, account_session


@transaction.atomic
def record_failed_login(*, identifier: str, request=None, reason: str = ""):
    login_history = LoginHistory.objects.create(
        identifier=identifier,
        status=LoginStatus.FAILED,
        ip_address=_request_ip(request),
        user_agent=_request_user_agent(request),
        failure_reason=reason[:255],
    )
    failed_attempt = FailedLoginAttempt.objects.create(
        identifier=identifier,
        ip_address=_request_ip(request),
        user_agent=_request_user_agent(request),
        failure_reason=reason[:255],
    )
    record_audit_log(
        action=AuditAction.SECURITY,
        entity_type="accounts.LoginHistory",
        entity_id=login_history.id,
        object_repr=identifier,
        summary="Failed login attempt.",
        metadata={"reason": reason[:255]},
        request=request,
    )
    return login_history, failed_attempt


@transaction.atomic
def logout_all_sessions(*, user, actor=None, request=None):
    now = timezone.now()
    updated = AccountSession.objects.filter(user=user, is_active=True).update(
        is_active=False,
        logged_out_at=now,
        updated_at=now,
    )
    record_audit_log(
        actor=actor or user,
        action=AuditAction.LOGOUT,
        entity_type="accounts.AccountSession",
        object_repr=user.email,
        summary="All account sessions marked as logged out.",
        metadata={"session_count": updated},
        request=request,
    )
    return updated
