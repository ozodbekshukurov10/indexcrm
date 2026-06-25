from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from apps.common.models import BaseModel


class IntegrationProviderType(models.TextChoices):
    FISCAL_CHECK = "fiscal_check", "Fiscal/check system"
    RECEIPT_PRINTER = "receipt_printer", "Receipt printer"
    UZUM_MARKET = "uzum_market", "Uzum Market"
    PAYMENT_PROVIDER = "payment_provider", "Payment provider"
    TELEGRAM = "telegram", "Telegram"
    SMS = "sms", "SMS"
    OFFLINE_SYNC = "offline_sync", "Offline sync"
    CENTRAL_LICENSING = "central_licensing", "Central licensing"
    OTHER = "other", "Other"


class IntegrationStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    ACTIVE = "active", "Active"
    PAUSED = "paused", "Paused"
    DISABLED = "disabled", "Disabled"


class IntegrationProvider(BaseModel):
    code = models.SlugField(
        max_length=128,
        unique=True,
        help_text="Stable provider code, for example uzum_market or telegram_bot.",
    )
    name = models.CharField(max_length=255, help_text="Readable provider name.")
    provider_type = models.CharField(
        max_length=32,
        choices=IntegrationProviderType.choices,
        help_text="Integration category placeholder.",
    )
    status = models.CharField(
        max_length=16,
        choices=IntegrationStatus.choices,
        default=IntegrationStatus.DRAFT,
    )
    base_url = models.URLField(
        blank=True,
        help_text="Optional remote API base URL. Real API calls are not implemented yet.",
    )
    description = models.TextField(blank=True)
    settings = models.JSONField(
        default=dict,
        blank=True,
        help_text="Non-secret provider settings and feature flags.",
    )
    branch = models.ForeignKey(
        "stores.Branch",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="integration_providers",
        help_text="Optional branch scope for branch-specific integrations.",
    )
    is_active = models.BooleanField(default=True)

    class Meta(BaseModel.Meta):
        verbose_name = "integration provider"
        verbose_name_plural = "integration providers"
        ordering = ("name",)
        indexes = [
            models.Index(fields=["code"]),
            models.Index(fields=["provider_type", "status"]),
            models.Index(fields=["branch", "is_active"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.provider_type})"


class IntegrationCredential(BaseModel):
    provider = models.ForeignKey(
        IntegrationProvider,
        on_delete=models.CASCADE,
        related_name="credentials",
    )
    key = models.CharField(
        max_length=128,
        help_text="Credential key, for example api_key, token, username, or password.",
    )
    value = models.TextField(
        help_text="Credential value. Never expose this through API responses or admin lists.",
    )
    is_secret = models.BooleanField(default=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_integration_credentials",
    )

    class Meta(BaseModel.Meta):
        verbose_name = "integration credential"
        verbose_name_plural = "integration credentials"
        ordering = ("provider__name", "key")
        indexes = [
            models.Index(fields=["provider", "key"]),
            models.Index(fields=["expires_at"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "key"],
                condition=models.Q(deleted_at__isnull=True),
                name="unique_active_integration_credential_key",
            )
        ]

    @property
    def masked_value(self):
        if not self.value:
            return ""
        return "********"

    def mark_used(self):
        self.last_used_at = timezone.now()
        self.save(update_fields=("last_used_at", "updated_at"))

    def __str__(self):
        return f"{self.provider.code}:{self.key}"


class IntegrationTaskStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    RUNNING = "running", "Running"
    SUCCESS = "success", "Success"
    FAILED = "failed", "Failed"
    RETRYING = "retrying", "Retrying"
    CANCELLED = "cancelled", "Cancelled"


class IntegrationDirection(models.TextChoices):
    INBOUND = "inbound", "Inbound"
    OUTBOUND = "outbound", "Outbound"


class IntegrationTask(BaseModel):
    provider = models.ForeignKey(
        IntegrationProvider,
        on_delete=models.CASCADE,
        related_name="tasks",
    )
    task_type = models.CharField(
        max_length=128,
        help_text="Placeholder task type, for example sync_products or send_receipt.",
    )
    status = models.CharField(
        max_length=16,
        choices=IntegrationTaskStatus.choices,
        default=IntegrationTaskStatus.PENDING,
        db_index=True,
    )
    direction = models.CharField(
        max_length=16,
        choices=IntegrationDirection.choices,
        default=IntegrationDirection.OUTBOUND,
    )
    payload = models.JSONField(default=dict, blank=True)
    result = models.JSONField(default=dict, blank=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    max_attempts = models.PositiveSmallIntegerField(
        default=3,
        validators=[MinValueValidator(1)],
    )
    next_retry_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_integration_tasks",
    )

    class Meta(BaseModel.Meta):
        verbose_name = "integration task"
        verbose_name_plural = "integration tasks"
        indexes = [
            models.Index(fields=["provider", "status"]),
            models.Index(fields=["task_type", "status"]),
            models.Index(fields=["next_retry_at"]),
        ]

    def __str__(self):
        return f"{self.provider.code} {self.task_type} {self.status}"


class SyncLogStatus(models.TextChoices):
    STARTED = "started", "Started"
    SUCCESS = "success", "Success"
    FAILED = "failed", "Failed"
    RETRYING = "retrying", "Retrying"


class SyncLog(BaseModel):
    provider = models.ForeignKey(
        IntegrationProvider,
        on_delete=models.CASCADE,
        related_name="sync_logs",
    )
    task = models.ForeignKey(
        IntegrationTask,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sync_logs",
    )
    status = models.CharField(
        max_length=16,
        choices=SyncLogStatus.choices,
        default=SyncLogStatus.STARTED,
        db_index=True,
    )
    operation = models.CharField(max_length=128)
    message = models.CharField(max_length=255, blank=True)
    request_payload = models.JSONField(default=dict, blank=True)
    response_payload = models.JSONField(default=dict, blank=True)
    error_code = models.CharField(max_length=64, blank=True)
    error_message = models.TextField(blank=True)
    started_at = models.DateTimeField(default=timezone.now)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta(BaseModel.Meta):
        verbose_name = "sync log"
        verbose_name_plural = "sync logs"
        indexes = [
            models.Index(fields=["provider", "status", "created_at"]),
            models.Index(fields=["operation", "created_at"]),
        ]

    def __str__(self):
        return f"{self.provider.code} {self.operation} {self.status}"


class WebhookEventStatus(models.TextChoices):
    RECEIVED = "received", "Received"
    PROCESSED = "processed", "Processed"
    FAILED = "failed", "Failed"
    IGNORED = "ignored", "Ignored"


class WebhookEvent(BaseModel):
    provider = models.ForeignKey(
        IntegrationProvider,
        on_delete=models.CASCADE,
        related_name="webhook_events",
    )
    event_type = models.CharField(max_length=128)
    external_event_id = models.CharField(max_length=255, blank=True)
    status = models.CharField(
        max_length=16,
        choices=WebhookEventStatus.choices,
        default=WebhookEventStatus.RECEIVED,
        db_index=True,
    )
    headers = models.JSONField(default=dict, blank=True)
    payload = models.JSONField(default=dict, blank=True)
    signature = models.CharField(
        max_length=255,
        blank=True,
        help_text="Webhook signature placeholder. Real verification is deferred.",
    )
    received_at = models.DateTimeField(default=timezone.now)
    processed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)

    class Meta(BaseModel.Meta):
        verbose_name = "webhook event"
        verbose_name_plural = "webhook events"
        indexes = [
            models.Index(fields=["provider", "status", "received_at"]),
            models.Index(fields=["event_type", "received_at"]),
            models.Index(fields=["external_event_id"]),
        ]

    def __str__(self):
        return f"{self.provider.code} {self.event_type}"


class ExternalMapping(BaseModel):
    provider = models.ForeignKey(
        IntegrationProvider,
        on_delete=models.CASCADE,
        related_name="external_mappings",
    )
    local_model = models.CharField(
        max_length=128,
        help_text="Local model label, for example catalog.Product.",
    )
    local_id = models.UUIDField()
    external_id = models.CharField(max_length=255)
    external_type = models.CharField(
        max_length=128,
        blank=True,
        help_text="External entity type, for example product, order, or receipt.",
    )
    metadata = models.JSONField(default=dict, blank=True)
    last_synced_at = models.DateTimeField(null=True, blank=True)

    class Meta(BaseModel.Meta):
        verbose_name = "external mapping"
        verbose_name_plural = "external mappings"
        indexes = [
            models.Index(fields=["provider", "local_model", "local_id"]),
            models.Index(fields=["provider", "external_id"]),
            models.Index(fields=["external_type"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "local_model", "local_id"],
                condition=models.Q(deleted_at__isnull=True),
                name="unique_active_external_mapping_local",
            ),
            models.UniqueConstraint(
                fields=["provider", "external_id"],
                condition=models.Q(deleted_at__isnull=True),
                name="unique_active_external_mapping_external",
            ),
        ]

    def __str__(self):
        return f"{self.provider.code}: {self.local_model} -> {self.external_id}"
