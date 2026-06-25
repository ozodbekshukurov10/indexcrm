from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from rest_framework_simplejwt.views import TokenObtainPairView

from apps.accounts.models import AccessPermission, AccountSession, PermissionGroup, User
from apps.accounts.permissions import IsOwnerOrAdmin, user_has_role
from apps.accounts.selectors import (
    account_session_queryset,
    audit_log_queryset,
    failed_login_attempt_queryset,
    login_history_queryset,
    profile_queryset,
    role_assignment_queryset,
    role_queryset,
    system_installation_queryset,
    user_queryset,
)
from apps.accounts.serializers import (
    AccessPermissionSerializer,
    AccountSessionSerializer,
    AuditedTokenObtainPairSerializer,
    AuditLogSerializer,
    FailedLoginAttemptSerializer,
    LoginHistorySerializer,
    MyProfileSerializer,
    PermissionGroupSerializer,
    RoleSerializer,
    SystemInstallationSerializer,
    UserManagementSerializer,
    UserProfileSerializer,
    UserRoleAssignmentSerializer,
    UserSerializer,
)
from apps.accounts.services import ensure_user_profile, logout_all_sessions


def _bool_param(value):
    if value is None:
        return None
    return str(value).lower() in {"1", "true", "yes", "on"}


class AuditedTokenObtainPairView(TokenObtainPairView):
    serializer_class = AuditedTokenObtainPairSerializer


class MeView(RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = (IsAuthenticated,)

    def get_object(self):
        ensure_user_profile(self.request.user)
        return self.request.user


class MyProfileView(RetrieveUpdateAPIView):
    serializer_class = MyProfileSerializer
    permission_classes = (IsAuthenticated,)

    def get_object(self):
        return ensure_user_profile(self.request.user)


@extend_schema_view(
    list=extend_schema(
        summary="List users",
        parameters=[
            OpenApiParameter("role", str, description="Filter by account role."),
            OpenApiParameter("is_active", bool, description="Filter by active status."),
        ],
    ),
    create=extend_schema(summary="Create user"),
    retrieve=extend_schema(summary="Retrieve user"),
    update=extend_schema(summary="Update user"),
    partial_update=extend_schema(summary="Partially update user"),
    destroy=extend_schema(summary="Soft delete user"),
)
class UserViewSet(ModelViewSet):
    serializer_class = UserManagementSerializer
    permission_classes = (IsOwnerOrAdmin,)
    filter_backends = (SearchFilter, OrderingFilter)
    search_fields = (
        "email",
        "first_name",
        "last_name",
        "phone",
        "profile__employee_code",
    )
    ordering_fields = ("email", "role", "is_active", "created_at", "updated_at")
    ordering = ("email",)

    def get_queryset(self):
        queryset = user_queryset()
        role = self.request.query_params.get("role")
        is_active = _bool_param(self.request.query_params.get("is_active"))

        if role:
            queryset = queryset.filter(role=role)
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active)
        return queryset


@extend_schema_view(
    list=extend_schema(
        summary="List user profiles",
        parameters=[
            OpenApiParameter("branch", str, description="Filter by branch UUID."),
            OpenApiParameter(
                "employee_status", str, description="Filter by employee status."
            ),
        ],
    )
)
class UserProfileViewSet(ModelViewSet):
    serializer_class = UserProfileSerializer
    permission_classes = (IsOwnerOrAdmin,)
    filter_backends = (SearchFilter, OrderingFilter)
    search_fields = (
        "user__email",
        "user__first_name",
        "user__last_name",
        "employee_code",
        "position",
        "branch__name",
    )
    ordering_fields = ("employee_code", "position", "employee_status", "created_at")
    ordering = ("user__email",)

    def get_queryset(self):
        queryset = profile_queryset()
        branch = self.request.query_params.get("branch")
        employee_status = self.request.query_params.get("employee_status")

        if branch:
            queryset = queryset.filter(branch_id=branch)
        if employee_status:
            queryset = queryset.filter(employee_status=employee_status)
        return queryset


class AccessPermissionViewSet(ModelViewSet):
    queryset = AccessPermission.objects.all()
    serializer_class = AccessPermissionSerializer
    permission_classes = (IsOwnerOrAdmin,)
    filter_backends = (SearchFilter, OrderingFilter)
    search_fields = ("code", "name", "module", "description")
    ordering_fields = ("code", "module", "is_active", "created_at")
    ordering = ("module", "code")

    def get_queryset(self):
        queryset = AccessPermission.objects.all()
        module = self.request.query_params.get("module")
        is_active = _bool_param(self.request.query_params.get("is_active"))
        if module:
            queryset = queryset.filter(module=module)
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active)
        return queryset


class PermissionGroupViewSet(ModelViewSet):
    queryset = PermissionGroup.objects.prefetch_related("permissions")
    serializer_class = PermissionGroupSerializer
    permission_classes = (IsOwnerOrAdmin,)
    filter_backends = (SearchFilter, OrderingFilter)
    search_fields = ("code", "name", "description", "permissions__code")
    ordering_fields = ("code", "name", "is_active", "created_at")
    ordering = ("name",)


class RoleViewSet(ModelViewSet):
    serializer_class = RoleSerializer
    permission_classes = (IsOwnerOrAdmin,)
    filter_backends = (SearchFilter, OrderingFilter)
    search_fields = ("code", "name", "description", "permissions__code")
    ordering_fields = ("code", "name", "is_system", "is_active", "created_at")
    ordering = ("name",)

    def get_queryset(self):
        queryset = role_queryset()
        is_active = _bool_param(self.request.query_params.get("is_active"))
        is_system = _bool_param(self.request.query_params.get("is_system"))
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active)
        if is_system is not None:
            queryset = queryset.filter(is_system=is_system)
        return queryset


class UserRoleAssignmentViewSet(ModelViewSet):
    serializer_class = UserRoleAssignmentSerializer
    permission_classes = (IsOwnerOrAdmin,)
    filter_backends = (SearchFilter, OrderingFilter)
    search_fields = ("user__email", "role__code", "role__name", "branch__name")
    ordering_fields = ("created_at", "updated_at", "is_active")
    ordering = ("-created_at",)

    def get_queryset(self):
        queryset = role_assignment_queryset()
        user = self.request.query_params.get("user")
        role = self.request.query_params.get("role")
        branch = self.request.query_params.get("branch")
        is_active = _bool_param(self.request.query_params.get("is_active"))

        if user:
            queryset = queryset.filter(user_id=user)
        if role:
            queryset = queryset.filter(role_id=role)
        if branch:
            queryset = queryset.filter(branch_id=branch)
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active)
        return queryset

    def perform_create(self, serializer):
        serializer.save(assigned_by=self.request.user)


class LoginHistoryViewSet(ReadOnlyModelViewSet):
    serializer_class = LoginHistorySerializer
    permission_classes = (IsOwnerOrAdmin,)
    filter_backends = (SearchFilter, OrderingFilter)
    search_fields = ("user__email", "identifier", "ip_address", "failure_reason")
    ordering_fields = ("status", "created_at")
    ordering = ("-created_at",)

    def get_queryset(self):
        queryset = login_history_queryset()
        status = self.request.query_params.get("status")
        user = self.request.query_params.get("user")
        if status:
            queryset = queryset.filter(status=status)
        if user:
            queryset = queryset.filter(user_id=user)
        return queryset


class FailedLoginAttemptViewSet(ReadOnlyModelViewSet):
    serializer_class = FailedLoginAttemptSerializer
    permission_classes = (IsOwnerOrAdmin,)
    filter_backends = (SearchFilter, OrderingFilter)
    search_fields = ("identifier", "ip_address", "failure_reason")
    ordering_fields = ("created_at", "resolved_at")
    ordering = ("-created_at",)

    def get_queryset(self):
        return failed_login_attempt_queryset()


class AccountSessionViewSet(ReadOnlyModelViewSet):
    queryset = AccountSession.objects.none()
    serializer_class = AccountSessionSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = (SearchFilter, OrderingFilter)
    search_fields = ("user__email", "ip_address", "user_agent", "device_name")
    ordering_fields = ("last_seen_at", "logged_out_at", "created_at")
    ordering = ("-last_seen_at",)

    def get_queryset(self):
        queryset = account_session_queryset()
        if not user_has_role(self.request.user, ["owner", "admin"]):
            return queryset.filter(user=self.request.user)

        user = self.request.query_params.get("user")
        is_active = _bool_param(self.request.query_params.get("is_active"))
        if user:
            queryset = queryset.filter(user_id=user)
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active)
        return queryset

    @extend_schema(
        summary="Mark all sessions as logged out",
        description="Marks stored account sessions as inactive. JWT blacklist integration is intentionally deferred.",
        request=None,
    )
    @action(detail=False, methods=["post"], url_path="logout-all")
    def logout_all(self, request):
        target_user = request.user
        user_id = request.query_params.get("user")
        if user_id and user_has_role(request.user, ["owner", "admin"]):
            target_user = User.objects.get(pk=user_id)
        count = logout_all_sessions(
            user=target_user, actor=request.user, request=request
        )
        return Response({"logged_out_sessions": count}, status=HTTP_200_OK)


class AuditLogViewSet(ReadOnlyModelViewSet):
    serializer_class = AuditLogSerializer
    permission_classes = (IsOwnerOrAdmin,)
    filter_backends = (SearchFilter, OrderingFilter)
    search_fields = ("actor__email", "action", "entity_type", "object_repr", "summary")
    ordering_fields = ("action", "entity_type", "created_at")
    ordering = ("-created_at",)

    def get_queryset(self):
        queryset = audit_log_queryset()
        action = self.request.query_params.get("action")
        entity_type = self.request.query_params.get("entity_type")
        actor = self.request.query_params.get("actor")
        if action:
            queryset = queryset.filter(action=action)
        if entity_type:
            queryset = queryset.filter(entity_type=entity_type)
        if actor:
            queryset = queryset.filter(actor_id=actor)
        return queryset


class SystemInstallationViewSet(ModelViewSet):
    serializer_class = SystemInstallationSerializer
    permission_classes = (IsOwnerOrAdmin,)
    filter_backends = (SearchFilter, OrderingFilter)
    search_fields = ("installation_id", "license_key", "subscription_status", "notes")
    ordering_fields = ("subscription_status", "last_check_in", "created_at")
    ordering = ("-created_at",)

    def get_queryset(self):
        queryset = system_installation_queryset()
        is_active = _bool_param(self.request.query_params.get("is_active"))
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active)
        return queryset
