from drf_spectacular.utils import OpenApiExample, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.services.health import get_health_status, get_system_status


class HealthCheckView(APIView):
    permission_classes = (AllowAny,)
    authentication_classes = ()

    @extend_schema(
        summary="Health check",
        responses=inline_serializer(
            name="HealthCheckResponse",
            fields={
                "status": serializers.CharField(),
                "checks": serializers.DictField(child=serializers.CharField()),
            },
        ),
        examples=[
            OpenApiExample(
                "Healthy response",
                value={"status": "ok", "checks": {"database": "ok", "cache": "ok"}},
                response_only=True,
            )
        ],
    )
    def get(self, request):
        payload, http_status = get_health_status()
        return Response(payload, status=http_status)


class SystemStatusView(APIView):
    permission_classes = (AllowAny,)
    authentication_classes = ()

    @extend_schema(
        summary="System status",
        responses=inline_serializer(
            name="SystemStatusResponse",
            fields={
                "status": serializers.CharField(),
                "checks": serializers.DictField(child=serializers.CharField()),
                "environment": serializers.CharField(),
                "version": serializers.CharField(),
                "debug": serializers.BooleanField(),
                "timestamp": serializers.DateTimeField(),
            },
        ),
        examples=[
            OpenApiExample(
                "System status response",
                value={
                    "status": "ok",
                    "checks": {"database": "ok", "cache": "ok"},
                    "environment": "production",
                    "version": "0.1.0",
                    "debug": False,
                    "timestamp": "2026-05-29T00:00:00Z",
                },
                response_only=True,
            )
        ],
    )
    def get(self, request):
        payload, http_status = get_system_status()
        return Response(payload, status=http_status)
