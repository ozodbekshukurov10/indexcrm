from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

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


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    extra = 0
    fields = (
        "avatar",
        "employee_code",
        "position",
        "branch",
        "employee_status",
        "language",
        "timezone",
        "theme",
        "notification_preferences",
        "biography",
        "notes",
    )


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    ordering = ("email",)
    list_display = (
        "email",
        "first_name",
        "last_name",
        "role",
        "is_staff",
        "is_active",
    )
    list_filter = ("role", "is_staff", "is_active", "is_superuser")
    search_fields = (
        "email",
        "first_name",
        "last_name",
        "phone",
        "profile__employee_code",
    )
    inlines = (UserProfileInline,)

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name", "phone")}),
        ("Access", {"fields": ("role", "is_active", "is_staff", "is_superuser")}),
        ("Permissions", {"fields": ("groups", "user_permissions")}),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "password1",
                    "password2",
                    "role",
                    "is_staff",
                    "is_active",
                ),
            },
        ),
    )
    readonly_fields = ("last_login", "date_joined")


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "employee_code",
        "position",
        "branch",
        "employee_status",
        "language",
        "theme",
    )
    list_filter = ("employee_status", "language", "theme", "branch")
    search_fields = ("user__email", "employee_code", "position", "branch__name")
    readonly_fields = ("created_at", "updated_at", "deleted_at")
    autocomplete_fields = ("user", "branch")
    ordering = ("user__email",)


@admin.register(AccessPermission)
class AccessPermissionAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "module", "is_active")
    list_filter = ("module", "is_active")
    search_fields = ("code", "name", "description")
    readonly_fields = ("created_at", "updated_at", "deleted_at")
    ordering = ("module", "code")


@admin.register(PermissionGroup)
class PermissionGroupAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "is_active")
    list_filter = ("is_active",)
    search_fields = ("code", "name", "description", "permissions__code")
    filter_horizontal = ("permissions",)
    readonly_fields = ("created_at", "updated_at", "deleted_at")
    ordering = ("name",)


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "is_system", "is_active")
    list_filter = ("is_system", "is_active")
    search_fields = ("code", "name", "description", "permissions__code")
    filter_horizontal = ("permissions", "permission_groups")
    readonly_fields = ("created_at", "updated_at", "deleted_at")
    ordering = ("name",)


@admin.register(UserRoleAssignment)
class UserRoleAssignmentAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "branch", "assigned_by", "is_active", "created_at")
    list_filter = ("role", "branch", "is_active")
    search_fields = ("user__email", "role__code", "role__name", "branch__name")
    readonly_fields = ("created_at", "updated_at", "deleted_at")
    autocomplete_fields = ("user", "role", "branch", "assigned_by")
    ordering = ("-created_at",)


@admin.register(LoginHistory)
class LoginHistoryAdmin(admin.ModelAdmin):
    list_display = ("identifier", "user", "status", "ip_address", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("identifier", "user__email", "ip_address", "failure_reason")
    readonly_fields = (
        "user",
        "identifier",
        "status",
        "ip_address",
        "user_agent",
        "failure_reason",
        "created_at",
        "updated_at",
        "deleted_at",
    )
    ordering = ("-created_at",)


@admin.register(FailedLoginAttempt)
class FailedLoginAttemptAdmin(admin.ModelAdmin):
    list_display = ("identifier", "ip_address", "resolved_at", "created_at")
    list_filter = ("resolved_at", "created_at")
    search_fields = ("identifier", "ip_address", "failure_reason")
    readonly_fields = ("created_at", "updated_at", "deleted_at")
    ordering = ("-created_at",)


@admin.register(AccountSession)
class AccountSessionAdmin(admin.ModelAdmin):
    list_display = ("user", "ip_address", "is_active", "last_seen_at", "logged_out_at")
    list_filter = ("is_active", "created_at", "logged_out_at")
    search_fields = (
        "user__email",
        "ip_address",
        "user_agent",
        "device_name",
        "token_jti",
    )
    readonly_fields = ("created_at", "updated_at", "deleted_at")
    ordering = ("-last_seen_at",)


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("actor", "action", "entity_type", "object_repr", "created_at")
    list_filter = ("action", "entity_type", "created_at")
    search_fields = ("actor__email", "entity_type", "object_repr", "summary")
    readonly_fields = (
        "actor",
        "action",
        "entity_type",
        "entity_id",
        "object_repr",
        "summary",
        "metadata",
        "ip_address",
        "user_agent",
        "created_at",
        "updated_at",
        "deleted_at",
    )
    ordering = ("-created_at",)


@admin.register(SystemInstallation)
class SystemInstallationAdmin(admin.ModelAdmin):
    list_display = (
        "installation_id",
        "subscription_status",
        "is_active",
        "last_check_in",
        "created_at",
    )
    list_filter = ("subscription_status", "is_active")
    search_fields = ("installation_id", "license_key", "notes")
    readonly_fields = ("installation_id", "created_at", "updated_at", "deleted_at")
    ordering = ("-created_at",)
