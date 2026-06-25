from django.contrib import admin

from apps.ai_assistant.models import (
    AIChatMessage,
    AIChatSession,
    AIFeedback,
    AITrainingExample,
)


@admin.register(AIChatSession)
class AIChatSessionAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "title", "is_active", "created_at", "updated_at")
    list_filter = ("is_active", "created_at", "updated_at")
    search_fields = ("id", "title", "user__email")
    readonly_fields = ("id", "created_at", "updated_at", "deleted_at")
    ordering = ("-updated_at",)


@admin.register(AIChatMessage)
class AIChatMessageAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "session",
        "role",
        "intent",
        "confidence",
        "source",
        "short_content",
        "created_at",
    )
    list_filter = ("role", "intent", "source", "created_at")
    search_fields = ("id", "content", "session__title", "session__user__email")
    readonly_fields = ("id", "created_at", "updated_at", "deleted_at")
    ordering = ("-created_at",)

    @admin.display(description="Content")
    def short_content(self, obj):
        return obj.content[:80]


@admin.register(AITrainingExample)
class AITrainingExampleAdmin(admin.ModelAdmin):
    list_display = ("id", "intent", "is_active", "created_at", "updated_at")
    list_filter = ("intent", "is_active", "created_at")
    search_fields = ("text", "expected_answer")
    readonly_fields = ("id", "created_at", "updated_at", "deleted_at")
    ordering = ("-created_at",)


@admin.register(AIFeedback)
class AIFeedbackAdmin(admin.ModelAdmin):
    list_display = ("id", "message", "rating", "created_by", "short_comment", "created_at")
    list_filter = ("rating", "created_at")
    search_fields = (
        "id",
        "comment",
        "created_by__email",
        "message__content",
        "message__session__user__email",
    )
    readonly_fields = ("id", "created_at", "updated_at", "deleted_at")
    ordering = ("-created_at",)

    @admin.display(description="Comment")
    def short_comment(self, obj):
        return obj.comment[:80]
