from rest_framework import serializers

from apps.integrations.models import (
    ExternalMapping,
    IntegrationCredential,
    IntegrationProvider,
    IntegrationTask,
    SyncLog,
    WebhookEvent,
)


class IntegrationProviderSerializer(serializers.ModelSerializer):
    branch_name = serializers.CharField(source="branch.name", read_only=True)

    class Meta:
        model = IntegrationProvider
        fields = (
            "id",
            "code",
            "name",
            "provider_type",
            "status",
            "base_url",
            "description",
            "settings",
            "branch",
            "branch_name",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "branch_name", "created_at", "updated_at")

    def validate_settings(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("Provider settings must be an object.")
        return value


class IntegrationCredentialSerializer(serializers.ModelSerializer):
    provider_code = serializers.CharField(source="provider.code", read_only=True)
    masked_value = serializers.CharField(read_only=True)
    value = serializers.CharField(
        write_only=True, required=False, trim_whitespace=False
    )

    class Meta:
        model = IntegrationCredential
        fields = (
            "id",
            "provider",
            "provider_code",
            "key",
            "value",
            "masked_value",
            "is_secret",
            "expires_at",
            "last_used_at",
            "created_by",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "provider_code",
            "masked_value",
            "last_used_at",
            "created_by",
            "created_at",
            "updated_at",
        )

    def validate(self, attrs):
        if self.instance is None and not attrs.get("value"):
            raise serializers.ValidationError(
                {"value": "Credential value is required."}
            )
        return attrs


class IntegrationTaskSerializer(serializers.ModelSerializer):
    provider_code = serializers.CharField(source="provider.code", read_only=True)
    created_by_email = serializers.EmailField(source="created_by.email", read_only=True)

    class Meta:
        model = IntegrationTask
        fields = (
            "id",
            "provider",
            "provider_code",
            "task_type",
            "status",
            "direction",
            "payload",
            "result",
            "attempts",
            "max_attempts",
            "next_retry_at",
            "started_at",
            "finished_at",
            "created_by",
            "created_by_email",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "provider_code",
            "result",
            "attempts",
            "started_at",
            "finished_at",
            "created_by",
            "created_by_email",
            "created_at",
            "updated_at",
        )

    def validate_payload(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("Task payload must be an object.")
        return value


class IntegrationTaskRetrySerializer(serializers.Serializer):
    next_retry_at = serializers.DateTimeField(required=False)
    result = serializers.JSONField(required=False)


class SyncLogSerializer(serializers.ModelSerializer):
    provider_code = serializers.CharField(source="provider.code", read_only=True)

    class Meta:
        model = SyncLog
        fields = (
            "id",
            "provider",
            "provider_code",
            "task",
            "status",
            "operation",
            "message",
            "request_payload",
            "response_payload",
            "error_code",
            "error_message",
            "started_at",
            "finished_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "provider_code", "created_at", "updated_at")


class WebhookEventSerializer(serializers.ModelSerializer):
    provider_code = serializers.CharField(source="provider.code", read_only=True)

    class Meta:
        model = WebhookEvent
        fields = (
            "id",
            "provider",
            "provider_code",
            "event_type",
            "external_event_id",
            "status",
            "headers",
            "payload",
            "signature",
            "received_at",
            "processed_at",
            "error_message",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "provider_code",
            "received_at",
            "processed_at",
            "created_at",
            "updated_at",
        )
        extra_kwargs = {"signature": {"write_only": True, "required": False}}


class ExternalMappingSerializer(serializers.ModelSerializer):
    provider_code = serializers.CharField(source="provider.code", read_only=True)

    class Meta:
        model = ExternalMapping
        fields = (
            "id",
            "provider",
            "provider_code",
            "local_model",
            "local_id",
            "external_id",
            "external_type",
            "metadata",
            "last_synced_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "provider_code", "created_at", "updated_at")

    def validate_metadata(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("Mapping metadata must be an object.")
        return value
