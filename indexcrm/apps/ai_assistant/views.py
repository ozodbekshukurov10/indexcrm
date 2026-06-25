from django.db.models import Count, Prefetch
from drf_spectacular.utils import extend_schema
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.ai_assistant.models import AIChatMessage, AIChatSession
from apps.ai_assistant.permissions import can_access_session, can_view_ai_admin_data
from apps.ai_assistant.serializers import (
    AIChatRequestSerializer,
    AIChatResponseSerializer,
    AIChatSessionDetailSerializer,
    AIChatSessionSerializer,
    AIFeedbackSerializer,
    AIUsageStatsSerializer,
)
from apps.ai_assistant.services import answer_message, get_usage_stats


class AIChatAPIView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        summary="Ask the internal AI assistant",
        request=AIChatRequestSerializer,
        responses=AIChatResponseSerializer,
    )
    def post(self, request):
        request_serializer = AIChatRequestSerializer(data=request.data)
        request_serializer.is_valid(raise_exception=True)
        result = answer_message(
            request.user,
            request_serializer.validated_data["message"],
            session_id=request_serializer.validated_data.get("session_id"),
        )
        response_serializer = AIChatResponseSerializer(result)
        return Response(response_serializer.data)


class AIChatSessionListAPIView(ListAPIView):
    serializer_class = AIChatSessionSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return (
            AIChatSession.objects.filter(user=self.request.user, is_active=True)
            .annotate(message_count=Count("messages"))
            .prefetch_related(
                Prefetch(
                    "messages",
                    queryset=AIChatMessage.objects.only(
                        "id",
                        "session_id",
                        "content",
                        "created_at",
                    ).order_by("-created_at"),
                )
            )
            .order_by("-updated_at")
        )


class AIChatSessionDetailAPIView(RetrieveAPIView):
    serializer_class = AIChatSessionDetailSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        queryset = AIChatSession.objects.prefetch_related(
            Prefetch(
                "messages",
                queryset=AIChatMessage.objects.order_by("created_at"),
            )
        )
        if can_view_ai_admin_data(self.request.user):
            return queryset
        return queryset.filter(user=self.request.user)


class AIChatSessionCloseAPIView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(summary="Close an AI chat session")
    def post(self, request, pk):
        session = AIChatSession.objects.filter(id=pk).first()
        if session is None or not can_access_session(request.user, session):
            from rest_framework.exceptions import NotFound

            raise NotFound("Session not found.")
        session.is_active = False
        session.save(update_fields=("is_active", "updated_at"))
        return Response({"status": "ok", "message": "Suhbat yopildi."})


class AIFeedbackCreateAPIView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        summary="Leave feedback for an assistant message",
        request=AIFeedbackSerializer,
        responses=AIFeedbackSerializer,
    )
    def post(self, request):
        serializer = AIFeedbackSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"status": "ok", "message": "Fikringiz saqlandi."})


class AIUsageStatsAPIView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        summary="Get AI assistant usage stats",
        responses=AIUsageStatsSerializer,
    )
    def get(self, request):
        if not can_view_ai_admin_data(request.user):
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied("You cannot view AI assistant usage stats.")
        serializer = AIUsageStatsSerializer(get_usage_stats())
        return Response(serializer.data)
