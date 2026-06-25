from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any


class IntegrationError(Exception):
    pass


@dataclass(slots=True)
class IntegrationResult:
    success: bool
    external_id: str | None = None
    payload: Mapping[str, Any] = field(default_factory=dict)
    message: str = ""


class ExternalIntegrationClient:
    code = "base"

    def __init__(self, credentials: Mapping[str, str] | None = None):
        self.credentials = credentials or {}

    def health_check(self) -> IntegrationResult:
        raise NotImplementedError(
            "Integration health checks must be implemented by subclasses."
        )
