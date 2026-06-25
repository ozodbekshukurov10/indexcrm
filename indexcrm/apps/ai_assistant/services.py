import logging

from django.db.models import Count
from django.utils import timezone

from apps.ai_assistant.constants import (
    FEEDBACK_BAD,
    FEEDBACK_GOOD,
    INTENT_HELP,
    INTENT_PRODUCT_PRICE,
    INTENT_PRODUCT_STOCK,
    INTENT_UNKNOWN,
    ROLE_ASSISTANT,
    ROLE_USER,
    SOURCE_ERROR,
    SOURCE_FALLBACK,
    SOURCE_HELP,
    SOURCE_NOT_SUPPORTED,
    SOURCE_PERMISSION_DENIED,
    SOURCE_TOOL,
)
from apps.ai_assistant.entity import extract_entities
from apps.ai_assistant.intent import detect_intent
from apps.ai_assistant.models import AIChatMessage, AIChatSession, AIFeedback
from apps.ai_assistant.permissions import can_use_intent
from apps.ai_assistant.templates import (
    EMPTY_MESSAGE_ANSWER,
    ERROR_ANSWER,
    render_answer,
    render_response_metadata,
)
from apps.ai_assistant.tools import get_tool_name, run_tool

logger = logging.getLogger(__name__)

GENERIC_SESSION_TITLES = {"", "Yangi suhbat", "New chat"}
FOLLOWUP_PRODUCT_REFERENCES = {"", "ham", "uni", "uning", "shu", "shuni", "buni"}


def _session_title(message: str) -> str:
    title = " ".join(message.strip().split())
    return title[:80] or "Yangi suhbat"


def _get_or_create_session(user, message: str, session_id=None):
    if session_id:
        session = AIChatSession.objects.filter(
            id=session_id,
            user=user,
            is_active=True,
        ).first()
        if session:
            return session
    return AIChatSession.objects.create(user=user, title=_session_title(message))


def _ensure_session_title(session, message: str):
    if session.title not in GENERIC_SESSION_TITLES:
        return
    session.title = _session_title(message)
    session.save(update_fields=("title", "updated_at"))


def _missing_entity_result(entity: str) -> dict:
    return {"status": "missing_entity", "entity": entity}


def _source_for_tool_result(intent: str, tool_name: str, tool_result: dict) -> str:
    if intent == INTENT_HELP:
        return SOURCE_HELP
    status = (tool_result or {}).get("status")
    if status == "permission_denied":
        return SOURCE_PERMISSION_DENIED
    if status == "not_supported":
        return SOURCE_NOT_SUPPORTED
    if status == "error":
        return SOURCE_ERROR
    return SOURCE_TOOL if tool_name else SOURCE_FALLBACK


def _render_answer_safely(intent: str, tool_result: dict, entities: dict | None = None):
    try:
        return render_answer(intent, tool_result, entities), False
    except Exception:
        logger.exception(
            "AI assistant template rendering error.",
            extra={"intent": intent, "tool_status": (tool_result or {}).get("status")},
        )
        return ERROR_ANSWER, True


def _last_product_entity(session) -> dict:
    messages = (
        session.messages.filter(role=ROLE_ASSISTANT)
        .exclude(entities={})
        .order_by("-created_at")[:10]
    )
    for message in messages:
        entities = message.entities or {}
        if entities.get("product_id"):
            return {
                "product_id": entities.get("product_id"),
                "product_name": entities.get("product_name"),
                "raw_product_query": entities.get("raw_product_query")
                or entities.get("product_name"),
            }
    return {}


def _apply_session_context(session, intent: str, entities: dict) -> dict:
    if intent not in {INTENT_PRODUCT_STOCK, INTENT_PRODUCT_PRICE}:
        return entities
    if entities.get("product_id"):
        return entities

    raw_query = (entities.get("raw_product_query") or "").strip().lower()
    if raw_query not in FOLLOWUP_PRODUCT_REFERENCES:
        return entities

    product_context = _last_product_entity(session)
    if not product_context:
        return entities

    entities.update(product_context)
    entities["context_reused"] = {
        "type": "product",
        "source": "previous_session_message",
    }
    return entities


def _response_payload(
    *,
    answer: str,
    intent: str,
    confidence: float,
    entities: dict,
    source: str,
    session_id,
    tool_result: dict,
) -> dict:
    return {
        "answer": answer,
        "intent": intent,
        "confidence": confidence,
        "entities": entities,
        "source": source,
        "session_id": session_id,
        **render_response_metadata(intent, tool_result, entities),
    }


def _save_assistant_message(
    session,
    *,
    answer: str,
    intent: str,
    confidence: float,
    entities: dict,
    tool_result: dict,
    tool_name: str = "",
    source: str = "",
):
    AIChatMessage.objects.create(
        session=session,
        role=ROLE_ASSISTANT,
        content=answer,
        intent=intent,
        confidence=confidence,
        entities=entities,
        tool_name=tool_name,
        tool_result=tool_result,
        source=source,
    )
    session.updated_at = timezone.now()
    session.save(update_fields=("updated_at",))


def answer_message(user, message: str, session_id=None) -> dict:
    clean_message = (message or "").strip()
    if not clean_message:
        tool_result = _missing_entity_result("message")
        return _response_payload(
            answer=EMPTY_MESSAGE_ANSWER,
            intent=INTENT_UNKNOWN,
            confidence=0.0,
            entities={},
            source=SOURCE_FALLBACK,
            session_id=None,
            tool_result=tool_result,
        )

    session = None
    try:
        session = _get_or_create_session(user, clean_message, session_id=session_id)
        _ensure_session_title(session, clean_message)
        AIChatMessage.objects.create(
            session=session,
            role=ROLE_USER,
            content=clean_message,
        )

        try:
            detected = detect_intent(clean_message)
        except Exception:
            logger.exception("AI assistant intent detection error.")
            raise
        intent = detected["intent"]
        confidence = detected["confidence"]

        if not can_use_intent(user, intent):
            tool_result = {"status": "permission_denied"}
            answer, render_failed = _render_answer_safely(intent, tool_result)
            source = SOURCE_ERROR if render_failed else SOURCE_PERMISSION_DENIED
            _save_assistant_message(
                session=session,
                answer=answer,
                intent=intent,
                confidence=confidence,
                entities={},
                tool_result=tool_result,
                source=source,
            )
            return _response_payload(
                answer=answer,
                intent=intent,
                confidence=confidence,
                entities={},
                source=source,
                session_id=session.id,
                tool_result=tool_result,
            )

        try:
            entities = extract_entities(clean_message, intent, user=user)
        except Exception:
            logger.exception("AI assistant entity extraction error.", extra={"intent": intent})
            raise
        entities = _apply_session_context(session, intent, entities)
        if (
            intent in {INTENT_PRODUCT_STOCK, INTENT_PRODUCT_PRICE}
            and not entities.get("product_id")
            and not entities.get("raw_product_query")
        ):
            tool_result = _missing_entity_result("product")
            answer, render_failed = _render_answer_safely(intent, tool_result, entities)
            source = SOURCE_ERROR if render_failed else SOURCE_FALLBACK
            _save_assistant_message(
                session=session,
                answer=answer,
                intent=intent,
                confidence=confidence,
                entities=entities,
                tool_result=tool_result,
                source=source,
            )
            return _response_payload(
                answer=answer,
                intent=intent,
                confidence=confidence,
                entities=entities,
                source=source,
                session_id=session.id,
                tool_result=tool_result,
            )

        tool_name = get_tool_name(intent)
        try:
            tool_result = run_tool(intent, entities, user=user)
        except Exception:
            logger.exception("AI assistant tool dispatch error.", extra={"intent": intent})
            raise
        source = _source_for_tool_result(intent, tool_name, tool_result)
        answer, render_failed = _render_answer_safely(intent, tool_result, entities)
        if render_failed:
            source = SOURCE_ERROR

        _save_assistant_message(
            session=session,
            answer=answer,
            intent=intent,
            confidence=confidence,
            entities=entities,
            tool_name=tool_name,
            tool_result=tool_result,
            source=source,
        )
        return _response_payload(
            answer=answer,
            intent=intent,
            confidence=confidence,
            entities=entities,
            source=source,
            session_id=session.id,
            tool_result=tool_result,
        )
    except Exception:  # pragma: no cover - defensive API guard.
        logger.exception("AI assistant failed to answer message.")
        if session is not None:
            AIChatMessage.objects.create(
                session=session,
                role=ROLE_ASSISTANT,
                content=ERROR_ANSWER,
                intent=INTENT_UNKNOWN,
                confidence=0.0,
                entities={},
                tool_result={"status": "error"},
                source=SOURCE_ERROR,
            )
            session.updated_at = timezone.now()
            session.save(update_fields=("updated_at",))
        return _response_payload(
            answer=ERROR_ANSWER,
            intent=INTENT_UNKNOWN,
            confidence=0.0,
            entities={},
            source=SOURCE_ERROR,
            session_id=session.id if session is not None else None,
            tool_result={"status": "error"},
        )


def get_usage_stats() -> dict:
    messages = AIChatMessage.objects.all()
    assistant_messages = messages.filter(role=ROLE_ASSISTANT)
    return {
        "total_sessions": AIChatSession.objects.count(),
        "total_messages": messages.count(),
        "total_user_messages": messages.filter(role=ROLE_USER).count(),
        "total_assistant_messages": assistant_messages.count(),
        "top_intents": list(
            assistant_messages.exclude(intent="")
            .values("intent")
            .annotate(count=Count("id"))
            .order_by("-count", "intent")[:10]
        ),
        "feedback_good_count": AIFeedback.objects.filter(rating=FEEDBACK_GOOD).count(),
        "feedback_bad_count": AIFeedback.objects.filter(rating=FEEDBACK_BAD).count(),
        "unknown_intent_count": assistant_messages.filter(intent=INTENT_UNKNOWN).count(),
        "error_count": assistant_messages.filter(source=SOURCE_ERROR).count(),
    }
