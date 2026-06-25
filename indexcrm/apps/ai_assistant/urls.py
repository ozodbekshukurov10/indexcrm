from django.urls import path

from apps.ai_assistant.views import (
    AIChatAPIView,
    AIChatSessionCloseAPIView,
    AIChatSessionDetailAPIView,
    AIChatSessionListAPIView,
    AIFeedbackCreateAPIView,
    AIUsageStatsAPIView,
)

urlpatterns = [
    path("chat/", AIChatAPIView.as_view(), name="ai-chat"),
    path("sessions/", AIChatSessionListAPIView.as_view(), name="ai-chat-sessions"),
    path(
        "sessions/<uuid:pk>/",
        AIChatSessionDetailAPIView.as_view(),
        name="ai-chat-session-detail",
    ),
    path(
        "sessions/<uuid:pk>/close/",
        AIChatSessionCloseAPIView.as_view(),
        name="ai-chat-session-close",
    ),
    path("feedback/", AIFeedbackCreateAPIView.as_view(), name="ai-feedback"),
    path("stats/", AIUsageStatsAPIView.as_view(), name="ai-stats"),
]
