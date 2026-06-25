from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import (
    AccessPermission,
    AccountSession,
    AuditLog,
    FailedLoginAttempt,
    LoginHistory,
    PermissionGroup,
    Role,
    SystemInstallation,
    User,
    UserProfile,
    UserRoleAssignment,
)
from apps.accounts.services import record_failed_login, record_successful_login


class UserProfileSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)
    branch_name = serializers.CharField(source="branch.name", read_only=True)

    class Meta:
        model = UserProfile
        fields = (
            "id",
            "user",
            "user_email",
            "avatar",
            "employee_code",
            "position",
            "branch",
            "branch_name",
            "biography",
            "language",
            "timezone",
            "theme",
            "notification_preferences",
            "employee_status",
            "notes",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "user_email",
            "branch_name",
            "created_at",
            "updated_at",
        )

    def validate_notification_preferences(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError(
                "Notification preferences must be an object."
            )
        return value


class MyProfileSerializer(UserProfileSerializer):
    class Meta(UserProfileSerializer.Meta):
        read_only_fields = (
            "id",
            "user",
            "user_email",
            "employee_code",
            "branch",
            "branch_name",
            "employee_status",
            "notes",
            "created_at",
            "updated_at",
        )


class UserSerializer(serializers.ModelSerializer):
    profile = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "first_name",
            "last_name",
            "phone",
            "role",
            "is_active",
            "profile",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "email",
            "role",
            "is_active",
            "profile",
            "created_at",
            "updated_at",
        )

    @extend_schema_field(UserProfileSerializer)
    def get_profile(self, instance):
        profile = getattr(instance, "profile", None)
        if profile is None:
            return None
        return UserProfileSerializer(profile, context=self.context).data


class UserManagementSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, min_length=8)
    profile = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "password",
            "first_name",
            "last_name",
            "phone",
            "role",
            "is_active",
            "is_staff",
            "profile",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "profile", "created_at", "updated_at")

    @extend_schema_field(UserProfileSerializer)
    def get_profile(self, instance):
        profile = getattr(instance, "profile", None)
        if profile is None:
            return None
        return UserProfileSerializer(profile, context=self.context).data

    def create(self, validated_data):
        password = validated_data.pop("password", None)
        user = User.objects.create_user(password=password, **validated_data)
        UserProfile.objects.get_or_create(user=user)
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        for field_name, value in validated_data.items():
            setattr(instance, field_name, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance


class AccessPermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccessPermission
        fields = (
            "id",
            "code",
            "name",
            "module",
            "description",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class PermissionGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = PermissionGroup
        fields = (
            "id",
            "code",
            "name",
            "description",
            "permissions",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = (
            "id",
            "code",
            "name",
            "description",
            "permissions",
            "permission_groups",
            "is_system",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class UserRoleAssignmentSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)
    role_code = serializers.CharField(source="role.code", read_only=True)
    branch_name = serializers.CharField(source="branch.name", read_only=True)

    class Meta:
        model = UserRoleAssignment
        fields = (
            "id",
            "user",
            "user_email",
            "role",
            "role_code",
            "branch",
            "branch_name",
            "assigned_by",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "user_email",
            "role_code",
            "branch_name",
            "assigned_by",
            "created_at",
            "updated_at",
        )


class LoginHistorySerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = LoginHistory
        fields = (
            "id",
            "user",
            "user_email",
            "identifier",
            "status",
            "ip_address",
            "user_agent",
            "failure_reason",
            "created_at",
        )
        read_only_fields = fields


class FailedLoginAttemptSerializer(serializers.ModelSerializer):
    class Meta:
        model = FailedLoginAttempt
        fields = (
            "id",
            "identifier",
            "ip_address",
            "user_agent",
            "failure_reason",
            "resolved_at",
            "created_at",
        )
        read_only_fields = fields


class AccountSessionSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = AccountSession
        fields = (
            "id",
            "user",
            "user_email",
            "session_key",
            "token_jti",
            "ip_address",
            "user_agent",
            "device_name",
            "is_active",
            "last_seen_at",
            "logged_out_at",
            "created_at",
        )
        read_only_fields = fields


class AuditLogSerializer(serializers.ModelSerializer):
    actor_email = serializers.EmailField(source="actor.email", read_only=True)

    class Meta:
        model = AuditLog
        fields = (
            "id",
            "actor",
            "actor_email",
            "action",
            "entity_type",
            "entity_id",
            "object_repr",
            "summary",
            "metadata",
            "ip_address",
            "user_agent",
            "created_at",
        )
        read_only_fields = fields


class SystemInstallationSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemInstallation
        fields = (
            "id",
            "installation_id",
            "license_key",
            "subscription_status",
            "last_check_in",
            "notes",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "installation_id", "created_at", "updated_at")


class AuditedTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        request = self.context.get("request")
        identifier = attrs.get(self.username_field, "")
        try:
            data = super().validate(attrs)
        except Exception as error:
            record_failed_login(
                identifier=identifier,
                request=request,
                reason=str(error),
            )
            raise

        token_jti = ""
        try:
            token_jti = str(RefreshToken(data["refresh"])["jti"])
        except TokenError:
            token_jti = ""

        record_successful_login(
            user=self.user,
            identifier=identifier,
            request=request,
            token_jti=token_jti,
        )
        return data
