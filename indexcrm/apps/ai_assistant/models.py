from django.conf import settings
from django.db import models
from django.db.models import Q

from apps.ai_assistant.constants import (
    FEEDBACK_RATING_CHOICES,
    INTENT_CHOICES,
    ROLE_ASSISTANT,
    ROLE_CHOICES,
    SOURCE_CHOICES,
)
from apps.common.models import BaseModel


class AIChatSession(BaseModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ai_chat_sessions",
    )
    title = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta(BaseModel.Meta):
        verbose_name = "AI chat session"
        verbose_name_plural = "AI chat sessions"
        indexes = [
            models.Index(fields=["user", "is_active"]),
            models.Index(fields=["updated_at"]),
        ]

    def __str__(self):
        return self.title or f"AI chat session {self.id}"


class AIChatMessage(BaseModel):
    session = models.ForeignKey(
        AIChatSession,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    content = models.TextField()
    intent = models.CharField(max_length=64, choices=INTENT_CHOICES, blank=True)
    confidence = models.FloatField(default=0.0)
    entities = models.JSONField(default=dict, blank=True)
    tool_name = models.CharField(max_length=128, blank=True)
    tool_result = models.JSONField(default=dict, blank=True)
    source = models.CharField(max_length=32, choices=SOURCE_CHOICES, blank=True)

    class Meta(BaseModel.Meta):
        verbose_name = "AI chat message"
        verbose_name_plural = "AI chat messages"
        indexes = [
            models.Index(fields=["session", "created_at"]),
            models.Index(fields=["role", "created_at"]),
            models.Index(fields=["intent"]),
            models.Index(fields=["source", "created_at"]),
        ]

    def __str__(self):
        return f"{self.role}: {self.content[:60]}"


class AITrainingExample(BaseModel):
    text = models.TextField()
    intent = models.CharField(max_length=64, choices=INTENT_CHOICES)
    entities = models.JSONField(default=dict, blank=True)
    expected_answer = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta(BaseModel.Meta):
        verbose_name = "AI training example"
        verbose_name_plural = "AI training examples"
        indexes = [
            models.Index(fields=["intent", "is_active"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.intent}: {self.text[:60]}"


class AIFeedback(BaseModel):
    message = models.ForeignKey(
        AIChatMessage,
        on_delete=models.CASCADE,
        related_name="feedback",
        limit_choices_to={"role": ROLE_ASSISTANT},
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="ai_feedback",
        null=True,
        blank=True,
    )
    rating = models.CharField(max_length=16, choices=FEEDBACK_RATING_CHOICES)
    comment = models.TextField(blank=True)

    class Meta(BaseModel.Meta):
        verbose_name = "AI feedback"
        verbose_name_plural = "AI feedback"
        indexes = [
            models.Index(fields=["message", "rating"]),
            models.Index(fields=["created_by", "created_at"]),
            models.Index(fields=["created_at"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["message", "created_by"],
                condition=Q(created_by__isnull=False, deleted_at__isnull=True),
                name="unique_ai_feedback_per_user_message",
            )
        ]

    def __str__(self):
        return f"{self.rating} feedback for {self.message_id}"
