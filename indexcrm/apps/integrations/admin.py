from django import forms
from django.contrib import admin

from apps.integrations.models import (
    ExternalMapping,
    IntegrationCredential,
    IntegrationProvider,
    IntegrationTask,
    SyncLog,
    WebhookEvent,
)


class IntegrationCredentialAdminForm(forms.ModelForm):
    credential_value = forms.CharField(
        required=False,
        widget=forms.PasswordInput(render_value=False),
        help_text="Enter a new credential value. Existing values are never displayed.",
    )

    class Meta:
        model = IntegrationCredential
        exclude = ("value",)

    def clean(self):
        cleaned_data = super().clean()
        if self.instance.pk is None and not cleaned_data.get("credential_value"):
            raise forms.ValidationError(
                "Credential value is required for new credentials."
            )
        return cleaned_data


@admin.register(IntegrationProvider)
class IntegrationProviderAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "provider_type", "status", "branch", "is_active")
    list_filter = ("provider_type", "status", "is_active", "branch")
    search_fields = ("name", "code", "description", "branch__name")
    readonly_fields = ("id", "created_at", "updated_at", "deleted_at")
    ordering = ("name",)


@admin.register(IntegrationCredential)
class IntegrationCredentialAdmin(admin.ModelAdmin):
    form = IntegrationCredentialAdminForm
    list_display = (
        "provider",
        "key",
        "masked_value",
        "is_secret",
        "expires_at",
        "last_used_at",
    )
    list_filter = ("provider", "is_secret", "expires_at")
    search_fields = ("provider__code", "provider__name", "key", "created_by__email")
    readonly_fields = (
        "id",
        "masked_value",
        "last_used_at",
        "created_at",
        "updated_at",
        "deleted_at",
    )
    ordering = ("provider__name", "key")

    def save_model(self, request, obj, form, change):
        credential_value = form.cleaned_data.get("credential_value")
        if credential_value:
            obj.value = credential_value
        if obj.created_by_id is None:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(IntegrationTask)
class IntegrationTaskAdmin(admin.ModelAdmin):
    list_display = (
        "provider",
        "task_type",
        "status",
        "attempts",
        "next_retry_at",
        "created_at",
    )
    list_filter = ("provider", "status", "direction", "task_type")
    search_fields = (
        "provider__code",
        "provider__name",
        "task_type",
        "created_by__email",
    )
    readonly_fields = ("id", "created_at", "updated_at", "deleted_at")
    ordering = ("-created_at",)


@admin.register(SyncLog)
class SyncLogAdmin(admin.ModelAdmin):
    list_display = ("provider", "operation", "status", "started_at", "finished_at")
    list_filter = ("provider", "status", "operation")
    search_fields = ("provider__code", "provider__name", "operation", "message")
    readonly_fields = ("id", "created_at", "updated_at", "deleted_at")
    ordering = ("-created_at",)


@admin.register(WebhookEvent)
class WebhookEventAdmin(admin.ModelAdmin):
    list_display = (
        "provider",
        "event_type",
        "external_event_id",
        "status",
        "received_at",
    )
    list_filter = ("provider", "status", "event_type")
    search_fields = (
        "provider__code",
        "provider__name",
        "event_type",
        "external_event_id",
    )
    readonly_fields = (
        "id",
        "received_at",
        "processed_at",
        "created_at",
        "updated_at",
        "deleted_at",
    )
    exclude = ("signature",)
    ordering = ("-received_at",)


@admin.register(ExternalMapping)
class ExternalMappingAdmin(admin.ModelAdmin):
    list_display = (
        "provider",
        "local_model",
        "local_id",
        "external_id",
        "external_type",
    )
    list_filter = ("provider", "local_model", "external_type")
    search_fields = ("provider__code", "provider__name", "local_model", "external_id")
    readonly_fields = ("id", "created_at", "updated_at", "deleted_at")
    ordering = ("provider__name", "local_model")
