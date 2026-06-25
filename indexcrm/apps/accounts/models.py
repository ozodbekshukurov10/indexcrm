import uuid

from django.conf import settings
from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone

from apps.common.models import BaseModel, SoftDeleteQuerySet


class UserRole(models.TextChoices):
    OWNER = "owner", "Owner"
    ADMIN = "admin", "Admin"
    MANAGER = "manager", "Manager"
    CASHIER = "cashier", "Cashier"


UserQuerySetManager = BaseUserManager.from_queryset(SoftDeleteQuerySet)


class UserManager(UserQuerySetManager):
    use_in_migrations = True

    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The email address must be set.")

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("role", UserRole.OWNER)
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, password, **extra_fields)


class User(BaseModel, AbstractUser):
    username = None
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=32, blank=True)
    role = models.CharField(
        max_length=20, choices=UserRole.choices, default=UserRole.OWNER
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta(BaseModel.Meta):
        verbose_name = "user"
        verbose_name_plural = "users"

    def __str__(self):
        return self.email


class ThemePreference(models.TextChoices):
    SYSTEM = "system", "System"
    LIGHT = "light", "Light"
    DARK = "dark", "Dark"


class EmployeeStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    INACTIVE = "inactive", "Inactive"
    ON_LEAVE = "on_leave", "On leave"


class UserProfile(BaseModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
        help_text="User account this employee profile belongs to.",
    )
    avatar = models.ImageField(
        upload_to="accounts/avatars/",
        blank=True,
        null=True,
        help_text="Profile avatar image.",
    )
    employee_code = models.CharField(
        max_length=64,
        unique=True,
        null=True,
        blank=True,
        help_text="Internal employee code.",
    )
    position = models.CharField(
        max_length=128,
        blank=True,
        help_text="Employee position or job title.",
    )
    branch = models.ForeignKey(
        "stores.Branch",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="employee_profiles",
        help_text="Primary branch assignment.",
    )
    biography = models.TextField(blank=True, help_text="Short employee biography.")
    language = models.CharField(
        max_length=16,
        default="en",
        help_text="Preferred interface language code.",
    )
    timezone = models.CharField(
        max_length=64,
        default="Asia/Tashkent",
        help_text="Preferred timezone name.",
    )
    theme = models.CharField(
        max_length=16,
        choices=ThemePreference.choices,
        default=ThemePreference.SYSTEM,
        help_text="Preferred interface theme.",
    )
    notification_preferences = models.JSONField(
        default=dict,
        blank=True,
        help_text="Per-channel notification preferences.",
    )
    employee_status = models.CharField(
        max_length=24,
        choices=EmployeeStatus.choices,
        default=EmployeeStatus.ACTIVE,
        help_text="Current employee status.",
    )
    notes = models.TextField(blank=True, help_text="Internal employee notes.")

    class Meta(BaseModel.Meta):
        verbose_name = "user profile"
        verbose_name_plural = "user profiles"
        indexes = [
            models.Index(fields=["employee_code"]),
            models.Index(fields=["branch", "employee_status"]),
        ]

    def __str__(self):
        name = self.user.get_full_name() or self.user.email
        return f"{name} profile"


class AccessPermission(BaseModel):
    code = models.CharField(
        max_length=128,
        unique=True,
        help_text="Stable permission code, for example reports.view.",
    )
    name = models.CharField(max_length=255, help_text="Readable permission name.")
    module = models.CharField(
        max_length=64,
        blank=True,
        help_text="Application module this permission belongs to.",
    )
    description = models.TextField(
        blank=True,
        help_text="Optional permission description.",
    )
    is_active = models.BooleanField(default=True)

    class Meta(BaseModel.Meta):
        verbose_name = "access permission"
        verbose_name_plural = "access permissions"
        ordering = ("module", "code")
        indexes = [
            models.Index(fields=["code"]),
            models.Index(fields=["module", "is_active"]),
        ]

    def __str__(self):
        return self.code


class PermissionGroup(BaseModel):
    code = models.CharField(max_length=128, unique=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    permissions = models.ManyToManyField(
        AccessPermission,
        blank=True,
        related_name="permission_groups",
    )
    is_active = models.BooleanField(default=True)

    class Meta(BaseModel.Meta):
        verbose_name = "permission group"
        verbose_name_plural = "permission groups"
        ordering = ("name",)
        indexes = [
            models.Index(fields=["code"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self):
        return self.name


class Role(BaseModel):
    code = models.CharField(
        max_length=64,
        unique=True,
        help_text="Stable role code, for example owner, admin, manager, or cashier.",
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    permissions = models.ManyToManyField(
        AccessPermission,
        blank=True,
        related_name="roles",
    )
    permission_groups = models.ManyToManyField(
        PermissionGroup,
        blank=True,
        related_name="roles",
    )
    is_system = models.BooleanField(
        default=False,
        help_text="System roles are the built-in owner/admin/manager/cashier roles.",
    )
    is_active = models.BooleanField(default=True)

    class Meta(BaseModel.Meta):
        verbose_name = "role"
        verbose_name_plural = "roles"
        ordering = ("name",)
        indexes = [
            models.Index(fields=["code"]),
            models.Index(fields=["is_active", "is_system"]),
        ]

    def __str__(self):
        return self.name


class UserRoleAssignment(BaseModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="role_assignments",
    )
    role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        related_name="assignments",
    )
    branch = models.ForeignKey(
        "stores.Branch",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="role_assignments",
        help_text="Optional branch scope for this role assignment.",
    )
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_roles",
    )
    is_active = models.BooleanField(default=True)

    class Meta(BaseModel.Meta):
        verbose_name = "user role assignment"
        verbose_name_plural = "user role assignments"
        indexes = [
            models.Index(fields=["user", "is_active"]),
            models.Index(fields=["role", "is_active"]),
            models.Index(fields=["branch", "is_active"]),
        ]

    def __str__(self):
        scope = self.branch.name if self.branch_id else "all branches"
        return f"{self.user.email} - {self.role.code} ({scope})"


class LoginStatus(models.TextChoices):
    SUCCESS = "success", "Success"
    FAILED = "failed", "Failed"


class LoginHistory(BaseModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="login_history",
    )
    identifier = models.CharField(
        max_length=255,
        blank=True,
        help_text="Submitted login identifier, usually email.",
    )
    status = models.CharField(max_length=16, choices=LoginStatus.choices)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    failure_reason = models.CharField(max_length=255, blank=True)

    class Meta(BaseModel.Meta):
        verbose_name = "login history"
        verbose_name_plural = "login history"
        indexes = [
            models.Index(fields=["user", "status", "created_at"]),
            models.Index(fields=["identifier", "status", "created_at"]),
        ]

    def __str__(self):
        identifier = self.user.email if self.user_id else self.identifier
        return f"{identifier} - {self.status}"


class FailedLoginAttempt(BaseModel):
    identifier = models.CharField(max_length=255, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    failure_reason = models.CharField(max_length=255, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta(BaseModel.Meta):
        verbose_name = "failed login attempt"
        verbose_name_plural = "failed login attempts"
        indexes = [
            models.Index(fields=["identifier", "created_at"]),
            models.Index(fields=["ip_address", "created_at"]),
        ]

    def __str__(self):
        return f"{self.identifier} failed login"

    def mark_resolved(self):
        self.resolved_at = timezone.now()
        self.save(update_fields=("resolved_at", "updated_at"))


class AccountSession(BaseModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="account_sessions",
    )
    session_key = models.CharField(max_length=255, blank=True, db_index=True)
    token_jti = models.CharField(max_length=255, blank=True, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    device_name = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    last_seen_at = models.DateTimeField(default=timezone.now)
    logged_out_at = models.DateTimeField(null=True, blank=True)

    class Meta(BaseModel.Meta):
        verbose_name = "account session"
        verbose_name_plural = "account sessions"
        indexes = [
            models.Index(fields=["user", "is_active"]),
            models.Index(fields=["token_jti"]),
        ]

    def __str__(self):
        return f"{self.user.email} session"

    def mark_logged_out(self):
        self.is_active = False
        self.logged_out_at = timezone.now()
        self.save(update_fields=("is_active", "logged_out_at", "updated_at"))


class AuditAction(models.TextChoices):
    CREATE = "create", "Create"
    UPDATE = "update", "Update"
    DELETE = "delete", "Delete"
    LOGIN = "login", "Login"
    LOGOUT = "logout", "Logout"
    SALE = "sale", "Sale"
    PURCHASE = "purchase", "Purchase"
    REFUND = "refund", "Refund"
    STOCK = "stock", "Stock"
    FINANCE = "finance", "Finance"
    ADMIN = "admin", "Admin"
    SECURITY = "security", "Security"


class AuditLog(BaseModel):
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )
    action = models.CharField(max_length=32, choices=AuditAction.choices)
    entity_type = models.CharField(
        max_length=128,
        blank=True,
        help_text="Model or domain object type touched by the action.",
    )
    entity_id = models.UUIDField(null=True, blank=True)
    object_repr = models.CharField(max_length=255, blank=True)
    summary = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)

    class Meta(BaseModel.Meta):
        verbose_name = "audit log"
        verbose_name_plural = "audit logs"
        indexes = [
            models.Index(fields=["actor", "action", "created_at"]),
            models.Index(fields=["entity_type", "entity_id"]),
            models.Index(fields=["action", "created_at"]),
        ]

    def __str__(self):
        actor = self.actor.email if self.actor_id else "system"
        return f"{actor} {self.action} {self.entity_type}".strip()


class SubscriptionStatus(models.TextChoices):
    UNKNOWN = "unknown", "Unknown"
    TRIAL = "trial", "Trial"
    ACTIVE = "active", "Active"
    PAST_DUE = "past_due", "Past due"
    SUSPENDED = "suspended", "Suspended"


class SystemInstallation(BaseModel):
    installation_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        help_text="Local installation identifier for future central admin sync.",
    )
    license_key = models.CharField(
        max_length=255,
        blank=True,
        help_text="Placeholder for a future central license key.",
    )
    subscription_status = models.CharField(
        max_length=32,
        choices=SubscriptionStatus.choices,
        default=SubscriptionStatus.UNKNOWN,
        help_text="Placeholder subscription state for future central licensing.",
    )
    last_check_in = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Placeholder for the last future central admin check-in.",
    )
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta(BaseModel.Meta):
        verbose_name = "system installation"
        verbose_name_plural = "system installations"
        indexes = [
            models.Index(fields=["installation_id"]),
            models.Index(fields=["subscription_status", "is_active"]),
        ]

    def __str__(self):
        return str(self.installation_id)
