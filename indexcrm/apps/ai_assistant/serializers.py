from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied

from apps.ai_assistant.constants import FEEDBACK_RATING_CHOICES, ROLE_ASSISTANT
from apps.ai_assistant.models import (
    AIChatMessage,
    AIChatSession,
    AIFeedback,
)
from apps.ai_assistant.permissions import can_view_ai_admin_data


class AIChatRequestSerializer(serializers.Serializer):
    message = serializers.CharField(allow_blank=False, trim_whitespace=True)
    session_id = serializers.UUIDField(required=False, allow_null=True)


class AIChatResponseSerializer(serializers.Serializer):
    answer = serializers.CharField()
    intent = serializers.CharField()
    confidence = serializers.FloatField()
    entities = serializers.JSONField()
    source = serializers.CharField()
    session_id = serializers.UUIDField(allow_null=True)
    suggestions = serializers.ListField(
        child=serializers.CharField(),
        required=False,
    )
    clarification_required = serializers.BooleanField(required=False)
    display_type = serializers.CharField(required=False)
    items = serializers.JSONField(required=False)


class AIChatMessageSerializer(serializers.ModelSerializer):
    tool_result = serializers.SerializerMethodField()

    class Meta:
        model = AIChatMessage
        fields = (
            "id",
            "session",
            "role",
            "content",
            "intent",
            "confidence",
            "entities",
            "tool_name",
            "tool_result",
            "source",
            "created_at",
        )
        read_only_fields = fields

    def get_tool_result(self, obj):
        request = self.context.get("request")
        if request is not None and can_view_ai_admin_data(request.user):
            return obj.tool_result
        return None

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if data.get("tool_result") is None:
            data.pop("tool_result", None)
        return data


class AIChatSessionSerializer(serializers.ModelSerializer):
    message_count = serializers.SerializerMethodField()
    last_message_preview = serializers.SerializerMethodField()

    class Meta:
        model = AIChatSession
        fields = (
            "id",
            "title",
            "is_active",
            "message_count",
            "last_message_preview",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_message_count(self, obj):
        if hasattr(obj, "message_count"):
            return obj.message_count
        return obj.messages.count()

    def get_last_message_preview(self, obj):
        prefetched = getattr(obj, "_prefetched_objects_cache", {}).get("messages")
        if prefetched is not None:
            last_message = max(prefetched, key=lambda message: message.created_at, default=None)
        else:
            last_message = obj.messages.order_by("-created_at").first()
        if last_message is None:
            return ""
        preview = " ".join(last_message.content.split())
        return preview[:120]


class AIChatSessionDetailSerializer(AIChatSessionSerializer):
    messages = AIChatMessageSerializer(many=True, read_only=True)

    class Meta(AIChatSessionSerializer.Meta):
        fields = AIChatSessionSerializer.Meta.fields + ("messages",)


class AIFeedbackSerializer(serializers.Serializer):
    message_id = serializers.UUIDField(write_only=True)
    rating = serializers.ChoiceField(choices=FEEDBACK_RATING_CHOICES)
    comment = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_message_id(self, value):
        message = (
            AIChatMessage.objects.select_related("session")
            .filter(id=value, role=ROLE_ASSISTANT)
            .first()
        )
        if message is None:
            raise serializers.ValidationError("Assistant message not found.")

        request = self.context.get("request")
        if request is None or message.session.user_id != request.user.id:
            raise PermissionDenied("You cannot leave feedback for this message.")

        self.context["feedback_message"] = message
        return value

    def create(self, validated_data):
        request = self.context["request"]
        message = self.context["feedback_message"]
        feedback, _created = AIFeedback.objects.update_or_create(
            message=message,
            created_by=request.user,
            defaults={
                "rating": validated_data["rating"],
                "comment": validated_data.get("comment", ""),
            },
        )
        return feedback

    def update(self, instance, validated_data):
        instance.rating = validated_data["rating"]
        instance.comment = validated_data.get("comment", "")
        instance.save(update_fields=("rating", "comment", "updated_at"))
        return instance


class AIUsageStatsSerializer(serializers.Serializer):
    total_sessions = serializers.IntegerField()
    total_messages = serializers.IntegerField()
    total_user_messages = serializers.IntegerField()
    total_assistant_messages = serializers.IntegerField()
    top_intents = serializers.ListField(child=serializers.DictField())
    feedback_good_count = serializers.IntegerField()
    feedback_bad_count = serializers.IntegerField()
    unknown_intent_count = serializers.IntegerField()
    error_count = serializers.IntegerField()
