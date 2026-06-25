import json
import re
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User, UserRole
from apps.ai_assistant.constants import (
    INTENT_CASHIER_ACTIVITY,
    INTENT_CUSTOMER_DEBT,
    INTENT_FINANCE_SUMMARY,
    INTENT_HELP,
    INTENT_LOW_STOCK,
    INTENT_PRODUCT_PRICE,
    INTENT_PRODUCT_STOCK,
    INTENT_REPORTS_SUMMARY,
    INTENT_SALES_MONTH,
    INTENT_SALES_TODAY,
    INTENT_TOP_PRODUCTS,
    INTENT_UNKNOWN,
    INTENTS,
    ROLE_ASSISTANT,
    SOURCE_ERROR,
    SOURCE_HELP,
)
from apps.ai_assistant.entity import extract_entities
from apps.ai_assistant.intent import detect_intent, normalize_text
from apps.ai_assistant.models import AIChatMessage, AIChatSession, AIFeedback
from apps.ai_assistant.permissions import can_use_intent
from apps.ai_assistant.services import answer_message
from apps.ai_assistant.templates import (
    ERROR_ANSWER,
    format_money,
    format_quantity,
    render_answer,
    render_response_metadata,
)
from apps.ai_assistant.tools import (
    get_cashier_activity,
    get_customer_debt,
    get_finance_summary,
    get_low_stock_products,
    get_monthly_sales,
    get_product_price,
    get_product_stock,
    get_reports_summary,
    get_today_sales,
    get_top_products,
    run_tool,
)
from apps.catalog.models import Category, Product, Unit
from apps.purchases.models import Supplier
from apps.sales.models import Customer, Sale, SaleItem, SalePayment, SalePaymentMethod, SaleStatus
from apps.stores.models import Branch, Store


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("Bugun qancha savdo bo'ldi?", INTENT_SALES_TODAY),
        ("Bugungi tushum qancha?", INTENT_SALES_TODAY),
        ("Bu oy savdo qancha?", INTENT_SALES_MONTH),
        ("Coca-Cola qoldig\u2018i qancha?", INTENT_PRODUCT_STOCK),
        ("Pepsi necha pul?", INTENT_PRODUCT_PRICE),
        ("Qaysi mahsulotlar kam qolgan?", INTENT_LOW_STOCK),
        ("Eng ko\u2018p sotilgan mahsulot qaysi?", INTENT_TOP_PRODUCTS),
        ("Bugungi foyda qancha?", INTENT_FINANCE_SUMMARY),
        ("Ali Valiyev qarzi qancha?", INTENT_CUSTOMER_DEBT),
        ("Qaysi kassir bugun ishlayapti?", INTENT_CASHIER_ACTIVITY),
        ("Menga hisobot ber", INTENT_REPORTS_SUMMARY),
        ("Nima qila olasan?", INTENT_HELP),
    ],
)
def test_detect_intent_supported_ai2_examples(message, expected):
    result = detect_intent(message)

    assert result["intent"] == expected
    assert result["confidence"] > 0
    assert result["matched_keywords"]
    assert expected in result["scores"]


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("Bugungi tushum qancha??", "bugungi tushum qancha"),
        ("Coca-Cola qoldig\u2018i qancha?", "coca cola qoldigi qancha"),
        ("Eng ko\u2018p sotilgan mahsulotlar", "eng kop sotilgan mahsulotlar"),
    ],
)
def test_normalize_text_handles_uzbek_business_phrases(message, expected):
    assert normalize_text(message) == expected


@pytest.mark.parametrize("message", ["Salom, ob-havo qanday?", "", "     "])
def test_detect_intent_unknown_fallback(message):
    result = detect_intent(message)

    assert result["intent"] == INTENT_UNKNOWN
    assert result["confidence"] == 0.0


def test_template_formatters_keep_uzbek_business_values_readable():
    assert format_money(Decimal("1540000.00")) == "1 540 000 so'm"
    assert format_money(1540000) == "1 540 000 so'm"
    assert format_money("1540000.25") == "1 540 000.25 so'm"
    assert format_money(Decimal("1234.50")) == "1 234.50 so'm"
    assert format_money(None) == "0 so'm"
    assert format_quantity(Decimal("18.000"), "dona") == "18 dona"


def test_template_sales_today_answer_is_polished():
    answer = render_answer(
        INTENT_SALES_TODAY,
        {
            "status": "ok",
            "data": {
                "sales_count": 3,
                "total_amount": "1540000.00",
                "average_check": "513333.33",
                "cash_amount": "1000000.00",
                "card_amount": "540000.00",
            },
        },
    )

    assert "Bugun 3 ta savdo bo'ldi" in answer
    assert "1 540 000 so'm" in answer
    assert "O'rtacha chek" in answer
    assert "naqd 1 000 000 so'm" in answer


def test_template_product_not_found_asks_for_clearer_product():
    tool_result = {"status": "not_found", "message": "Mahsulot topilmadi."}
    answer = render_answer(INTENT_PRODUCT_PRICE, tool_result)
    metadata = render_response_metadata(INTENT_PRODUCT_PRICE, tool_result)

    assert "Mahsulot topilmadi" in answer
    assert "SKU" in answer
    assert metadata["clarification_required"] is True
    assert metadata["display_type"] == "clarification"
    assert metadata["suggestions"]


def test_template_low_stock_empty_state_is_helpful():
    answer = render_answer(
        INTENT_LOW_STOCK,
        {"status": "ok", "data": {"count": 0, "products": []}},
    )
    metadata = render_response_metadata(
        INTENT_LOW_STOCK,
        {"status": "ok", "data": {"count": 0, "products": []}},
    )

    assert "Kam qolgan mahsulotlar topilmadi" in answer
    assert metadata["display_type"] == "list"
    assert metadata["items"] == []


def test_template_error_state_is_safe_notice():
    tool_result = {"status": "error", "message": "database exploded"}

    assert render_answer(INTENT_REPORTS_SUMMARY, tool_result) == ERROR_ANSWER
    metadata = render_response_metadata(INTENT_REPORTS_SUMMARY, tool_result)
    assert metadata["clarification_required"] is False
    assert metadata["display_type"] == "notice"


def test_template_permission_denied_and_unknown_do_not_expose_internal_details():
    denied = render_answer(
        INTENT_FINANCE_SUMMARY,
        {"status": "permission_denied", "message": "cashbox balance is 900000"},
    )
    unknown = render_answer(INTENT_UNKNOWN, {"status": "ok", "data": {}})

    assert "ruxsat" in denied
    assert "900000" not in denied
    assert "cashbox" not in denied.lower()
    assert "Savolingizni aniq tushunmadim" in unknown
    assert "Bugun qancha savdo" in unknown


def test_run_tool_unknown_intent_returns_safe_not_supported_response():
    result = run_tool("future_unimplemented_intent", {}, user=None)
    answer = render_answer("future_unimplemented_intent", result)

    assert result["status"] == "not_supported"
    assert "hozircha" in answer


@pytest.mark.django_db
def test_chat_endpoint_requires_authentication():
    client = APIClient()

    response = client.post(
        "/api/v1/ai/chat/",
        {"message": "Bugun qancha savdo bo'ldi?"},
        format="json",
    )

    assert response.status_code in {401, 403}


@pytest.mark.django_db
def test_chat_endpoint_returns_safe_response():
    user = User.objects.create_user(
        email="ai-cashier@example.com",
        password="test-pass-123",
        role=UserRole.CASHIER,
    )
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.post(
        "/api/v1/ai/chat/",
        {"message": "Salom, ob-havo qanday?"},
        format="json",
    )

    assert response.status_code == 200
    assert response.data["intent"] == INTENT_UNKNOWN
    assert response.data["source"] == "fallback"
    assert "answer" in response.data
    assert response.data["clarification_required"] is True
    assert response.data["display_type"] == "clarification"
    assert response.data["suggestions"]
    assert {
        "answer",
        "intent",
        "confidence",
        "entities",
        "source",
        "session_id",
    }.issubset(response.data.keys())
    assert AIChatSession.objects.filter(user=user).exists()
    assert AIChatMessage.objects.filter(session__user=user).count() == 2


@pytest.mark.django_db
def test_chat_endpoint_returns_help_response():
    user = User.objects.create_user(
        email="ai-help@example.com",
        password="test-pass-123",
        role=UserRole.CASHIER,
    )
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.post(
        "/api/v1/ai/chat/",
        {"message": "Nima qila olasan?"},
        format="json",
    )

    assert response.status_code == 200
    assert response.data["intent"] == INTENT_HELP
    assert response.data["source"] == SOURCE_HELP
    assert "Bugun qancha savdo" in response.data["answer"]
    assert response.data["clarification_required"] is False
    assert response.data["suggestions"]


@pytest.mark.django_db
def test_chat_endpoint_returns_monthly_sales_tool_response():
    user = User.objects.create_user(
        email="ai-monthly-manager@example.com",
        password="test-pass-123",
        role=UserRole.MANAGER,
    )
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.post(
        "/api/v1/ai/chat/",
        {"message": "Bu oy savdo qancha?"},
        format="json",
    )

    assert response.status_code == 200
    assert response.data["intent"] == INTENT_SALES_MONTH
    assert response.data["source"] == "tool"
    assert response.data["entities"]["date_range"]
    assert "Jami tushum" in response.data["answer"]
    assert response.data["display_type"] == "summary"


@pytest.mark.django_db
def test_chat_endpoint_asks_for_missing_product_entity():
    user = User.objects.create_user(
        email="ai-missing-product@example.com",
        password="test-pass-123",
        role=UserRole.CASHIER,
    )
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.post(
        "/api/v1/ai/chat/",
        {"message": "Qoldiq qancha?"},
        format="json",
    )

    assert response.status_code == 200
    assert response.data["intent"] == INTENT_PRODUCT_STOCK
    assert response.data["source"] == "fallback"
    assert response.data["entities"]["product_id"] is None
    assert "Qaysi mahsulot" in response.data["answer"]
    assert response.data["clarification_required"] is True
    assert response.data["display_type"] == "clarification"
    assert response.data["suggestions"]


@pytest.mark.django_db
def test_chat_endpoint_returns_product_not_found_clarification(entity_context):
    user = User.objects.create_user(
        email="ai-product-not-found@example.com",
        password="test-pass-123",
        role=UserRole.CASHIER,
    )
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.post(
        "/api/v1/ai/chat/",
        {"message": "Mars qoldigi qancha?"},
        format="json",
    )

    assert response.status_code == 200
    assert response.data["intent"] == INTENT_PRODUCT_STOCK
    assert response.data["source"] == "tool"
    assert "Mahsulot topilmadi" in response.data["answer"]
    assert response.data["clarification_required"] is True
    assert response.data["display_type"] == "clarification"


@pytest.mark.django_db
def test_chat_endpoint_appends_messages_to_existing_session():
    user = User.objects.create_user(
        email="ai-session-append@example.com",
        password="test-pass-123",
        role=UserRole.CASHIER,
    )
    client = APIClient()
    client.force_authenticate(user=user)

    first_response = client.post(
        "/api/v1/ai/chat/",
        {"message": "Salom, ob-havo qanday?"},
        format="json",
    )
    session_id = first_response.data["session_id"]

    second_response = client.post(
        "/api/v1/ai/chat/",
        {"message": "Nima qila olasan?", "session_id": session_id},
        format="json",
    )

    assert second_response.status_code == 200
    assert second_response.data["session_id"] == session_id
    assert AIChatSession.objects.filter(user=user).count() == 1
    assert AIChatMessage.objects.filter(session_id=session_id).count() == 4
    assistant_messages = AIChatMessage.objects.filter(
        session_id=session_id,
        role=ROLE_ASSISTANT,
    ).order_by("created_at")
    assert assistant_messages.last().source == SOURCE_HELP


@pytest.mark.django_db
def test_chat_endpoint_with_another_users_session_id_creates_safe_new_session():
    owner = User.objects.create_user(
        email="ai-session-owner@example.com",
        password="test-pass-123",
        role=UserRole.CASHIER,
    )
    other_user = User.objects.create_user(
        email="ai-session-intruder@example.com",
        password="test-pass-123",
        role=UserRole.CASHIER,
    )
    foreign_session = AIChatSession.objects.create(user=owner, title="Private")
    client = APIClient()
    client.force_authenticate(user=other_user)

    response = client.post(
        "/api/v1/ai/chat/",
        {"message": "Nima qila olasan?", "session_id": str(foreign_session.id)},
        format="json",
    )

    assert response.status_code == 200
    assert response.data["session_id"] != str(foreign_session.id)
    assert AIChatMessage.objects.filter(session=foreign_session).count() == 0
    assert AIChatSession.objects.filter(user=other_user).count() == 1


@pytest.mark.django_db
def test_session_list_returns_only_current_users_sessions():
    first_user = User.objects.create_user(
        email="ai-session-list-1@example.com",
        password="test-pass-123",
        role=UserRole.CASHIER,
    )
    second_user = User.objects.create_user(
        email="ai-session-list-2@example.com",
        password="test-pass-123",
        role=UserRole.CASHIER,
    )
    own_session = AIChatSession.objects.create(user=first_user, title="Own session")
    other_session = AIChatSession.objects.create(user=second_user, title="Other session")
    AIChatMessage.objects.create(
        session=own_session,
        role=ROLE_ASSISTANT,
        content="Own answer",
        intent=INTENT_HELP,
        source=SOURCE_HELP,
    )
    AIChatMessage.objects.create(
        session=other_session,
        role=ROLE_ASSISTANT,
        content="Other answer",
        intent=INTENT_HELP,
        source=SOURCE_HELP,
    )

    client = APIClient()
    client.force_authenticate(user=first_user)
    response = client.get("/api/v1/ai/sessions/")

    assert response.status_code == 200
    results = response.data["results"]
    assert len(results) == 1
    assert results[0]["id"] == str(own_session.id)
    assert results[0]["message_count"] == 1
    assert results[0]["last_message_preview"] == "Own answer"


@pytest.mark.django_db
def test_session_detail_is_scoped_and_hides_tool_result_for_owner():
    owner = User.objects.create_user(
        email="ai-session-detail-owner@example.com",
        password="test-pass-123",
        role=UserRole.CASHIER,
    )
    other_user = User.objects.create_user(
        email="ai-session-detail-other@example.com",
        password="test-pass-123",
        role=UserRole.CASHIER,
    )
    session = AIChatSession.objects.create(user=owner, title="Private session")
    AIChatMessage.objects.create(
        session=session,
        role="user",
        content="Savol",
    )
    AIChatMessage.objects.create(
        session=session,
        role=ROLE_ASSISTANT,
        content="Javob",
        intent=INTENT_HELP,
        tool_result={"status": "ok", "secret": "internal"},
        source=SOURCE_HELP,
    )
    client = APIClient()
    client.force_authenticate(user=owner)

    detail_response = client.get(f"/api/v1/ai/sessions/{session.id}/")
    assert detail_response.status_code == 200
    assert len(detail_response.data["messages"]) == 2
    assistant_message = detail_response.data["messages"][1]
    assert assistant_message["source"] == SOURCE_HELP
    assert "tool_result" not in assistant_message

    client.force_authenticate(user=other_user)
    other_response = client.get(f"/api/v1/ai/sessions/{session.id}/")
    assert other_response.status_code == 404


@pytest.mark.django_db
def test_session_detail_staff_can_inspect_tool_result_for_support():
    owner = User.objects.create_user(
        email="ai-session-support-owner@example.com",
        password="test-pass-123",
        role=UserRole.CASHIER,
    )
    staff = User.objects.create_user(
        email="ai-session-support-staff@example.com",
        password="test-pass-123",
        role=UserRole.ADMIN,
        is_staff=True,
    )
    session = AIChatSession.objects.create(user=owner, title="Support session")
    AIChatMessage.objects.create(
        session=session,
        role=ROLE_ASSISTANT,
        content="Javob",
        intent=INTENT_HELP,
        tool_result={"status": "ok", "debug": "visible-to-staff"},
        source=SOURCE_HELP,
    )
    client = APIClient()
    client.force_authenticate(user=staff)

    response = client.get(f"/api/v1/ai/sessions/{session.id}/")

    assert response.status_code == 200
    assert response.data["messages"][0]["tool_result"]["debug"] == "visible-to-staff"


@pytest.mark.django_db
def test_session_close_marks_session_inactive():
    user = User.objects.create_user(
        email="ai-session-close@example.com",
        password="test-pass-123",
        role=UserRole.CASHIER,
    )
    session = AIChatSession.objects.create(user=user, title="Close me")
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.post(f"/api/v1/ai/sessions/{session.id}/close/")
    session.refresh_from_db()

    assert response.status_code == 200
    assert session.is_active is False


@pytest.mark.django_db
def test_feedback_can_be_created_and_duplicate_updates_own_message():
    user = User.objects.create_user(
        email="ai-feedback-owner@example.com",
        password="test-pass-123",
        role=UserRole.CASHIER,
    )
    session = AIChatSession.objects.create(user=user, title="Feedback session")
    message = AIChatMessage.objects.create(
        session=session,
        role=ROLE_ASSISTANT,
        content="Yordamchi javob",
        intent=INTENT_HELP,
        source=SOURCE_HELP,
    )
    client = APIClient()
    client.force_authenticate(user=user)

    first_response = client.post(
        "/api/v1/ai/feedback/",
        {"message_id": str(message.id), "rating": "good", "comment": "Foydali"},
        format="json",
    )
    second_response = client.post(
        "/api/v1/ai/feedback/",
        {"message_id": str(message.id), "rating": "bad", "comment": "Aniq emas"},
        format="json",
    )

    assert first_response.status_code == 200
    assert first_response.data == {"status": "ok", "message": "Fikringiz saqlandi."}
    assert second_response.status_code == 200
    assert AIFeedback.objects.filter(message=message, created_by=user).count() == 1
    feedback = AIFeedback.objects.get(message=message, created_by=user)
    assert feedback.rating == "bad"
    assert feedback.comment == "Aniq emas"


@pytest.mark.django_db
def test_feedback_invalid_rating_is_rejected():
    user = User.objects.create_user(
        email="ai-feedback-invalid@example.com",
        password="test-pass-123",
        role=UserRole.CASHIER,
    )
    session = AIChatSession.objects.create(user=user, title="Feedback session")
    message = AIChatMessage.objects.create(
        session=session,
        role=ROLE_ASSISTANT,
        content="Yordamchi javob",
        intent=INTENT_HELP,
        source=SOURCE_HELP,
    )
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.post(
        "/api/v1/ai/feedback/",
        {"message_id": str(message.id), "rating": "neutral"},
        format="json",
    )

    assert response.status_code == 400


@pytest.mark.django_db
def test_feedback_on_another_users_message_is_rejected():
    owner = User.objects.create_user(
        email="ai-feedback-message-owner@example.com",
        password="test-pass-123",
        role=UserRole.CASHIER,
    )
    other_user = User.objects.create_user(
        email="ai-feedback-other@example.com",
        password="test-pass-123",
        role=UserRole.CASHIER,
    )
    session = AIChatSession.objects.create(user=owner, title="Private feedback session")
    message = AIChatMessage.objects.create(
        session=session,
        role=ROLE_ASSISTANT,
        content="Yordamchi javob",
        intent=INTENT_HELP,
        source=SOURCE_HELP,
    )
    client = APIClient()
    client.force_authenticate(user=other_user)

    response = client.post(
        "/api/v1/ai/feedback/",
        {"message_id": str(message.id), "rating": "good"},
        format="json",
    )

    assert response.status_code == 403
    assert AIFeedback.objects.count() == 0


@pytest.mark.django_db
def test_stats_endpoint_is_admin_only():
    cashier = User.objects.create_user(
        email="ai-stats-cashier@example.com",
        password="test-pass-123",
        role=UserRole.CASHIER,
    )
    admin = User.objects.create_user(
        email="ai-stats-admin@example.com",
        password="test-pass-123",
        role=UserRole.ADMIN,
    )
    session = AIChatSession.objects.create(user=cashier, title="Stats session")
    AIChatMessage.objects.create(session=session, role="user", content="Savol")
    AIChatMessage.objects.create(
        session=session,
        role=ROLE_ASSISTANT,
        content="Javob",
        intent=INTENT_UNKNOWN,
        source="fallback",
    )
    client = APIClient()
    client.force_authenticate(user=cashier)

    denied_response = client.get("/api/v1/ai/stats/")
    client.force_authenticate(user=admin)
    allowed_response = client.get("/api/v1/ai/stats/")

    assert denied_response.status_code == 403
    assert allowed_response.status_code == 200
    assert allowed_response.data["total_sessions"] >= 1
    assert allowed_response.data["total_user_messages"] >= 1
    assert allowed_response.data["unknown_intent_count"] >= 1


@pytest.mark.django_db
def test_follow_up_product_question_reuses_previous_session_entity(tool_context):
    user = tool_context["owner"]
    client = APIClient()
    client.force_authenticate(user=user)

    first_response = client.post(
        "/api/v1/ai/chat/",
        {"message": "Coca-Cola qoldigi qancha?"},
        format="json",
    )
    second_response = client.post(
        "/api/v1/ai/chat/",
        {
            "message": "narxini ham ayt",
            "session_id": first_response.data["session_id"],
        },
        format="json",
    )

    assert second_response.status_code == 200
    assert second_response.data["intent"] == INTENT_PRODUCT_PRICE
    assert second_response.data["entities"]["product_id"] == str(tool_context["product"].id)
    assert second_response.data["entities"]["context_reused"]["type"] == "product"
    assert "sotuv narxi" in second_response.data["answer"]


@pytest.mark.django_db
def test_answer_message_masks_internal_tool_exception(monkeypatch):
    user = User.objects.create_user(
        email="ai-service-error@example.com",
        password="test-pass-123",
        role=UserRole.MANAGER,
    )

    def broken_tool(*args, **kwargs):
        raise RuntimeError("sensitive stack details")

    monkeypatch.setattr("apps.ai_assistant.services.run_tool", broken_tool)

    response = answer_message(user, "Bugun qancha savdo bo'ldi?")

    assert response["answer"] == ERROR_ANSWER
    assert response["source"] == SOURCE_ERROR
    assert "sensitive" not in response["answer"].lower()
    assert "traceback" not in response["answer"].lower()
    assistant_message = AIChatMessage.objects.get(
        session_id=response["session_id"],
        role=ROLE_ASSISTANT,
    )
    assert assistant_message.source == SOURCE_ERROR
    assert assistant_message.tool_result == {"status": "error"}


@pytest.fixture
def entity_context(db):
    owner = User.objects.create_user(
        email="ai-entity-owner@example.com",
        password="test-pass-123",
        role=UserRole.OWNER,
    )
    cashier = User.objects.create_user(
        email="cashier.demo@example.com",
        password="test-pass-123",
        role=UserRole.CASHIER,
        first_name="Kassir",
        last_name="Demo",
    )
    category = Category.objects.create(name="Ichimliklar")
    unit = Unit.objects.create(name="ai-entity-piece", short_name="ai-pcs")
    cola = Product.objects.create(
        category=category,
        name="Coca-Cola 1L",
        sku="COLA-AI-1L",
        barcode="478000000001",
        selling_price=Decimal("12000.00"),
        unit=unit,
        created_by=owner,
    )
    pepsi = Product.objects.create(
        category=category,
        name="Pepsi 1L",
        sku="PEPSI-AI-1L",
        barcode="478000000002",
        selling_price=Decimal("11000.00"),
        unit=unit,
        created_by=owner,
    )
    customer = Customer.objects.create(
        full_name="Ali Valiyev",
        phone="+998901112233",
    )
    supplier = Supplier.objects.create(
        company_name="Toshkent Ichimlik Savdo",
        full_name="Dilshod Akramov",
        phone="+998909998877",
        email="supplier@example.com",
    )
    return {
        "cashier": cashier,
        "category": category,
        "cola": cola,
        "customer": customer,
        "pepsi": pepsi,
        "supplier": supplier,
    }


@pytest.fixture
def tool_context(entity_context):
    owner = User.objects.create_user(
        email="ai-tool-owner@example.com",
        password="test-pass-123",
        role=UserRole.OWNER,
        is_staff=True,
    )
    store = Store.objects.create(name="AI Tool Store", owner=owner)
    branch = Branch.objects.create(store=store, name="AI Tool Branch")
    second_branch = Branch.objects.create(store=store, name="AI Tool Second Branch")
    warehouse = branch.warehouses.create(name="AI Tool Warehouse")
    second_warehouse = second_branch.warehouses.create(name="AI Tool Second Warehouse")
    Branch.objects.filter(id=branch.id).update(
        created_at=timezone.now() - timedelta(minutes=2)
    )
    Branch.objects.filter(id=second_branch.id).update(
        created_at=timezone.now() - timedelta(minutes=1)
    )
    warehouse.__class__.objects.filter(id=warehouse.id).update(
        created_at=timezone.now() - timedelta(minutes=2)
    )
    warehouse.__class__.objects.filter(id=second_warehouse.id).update(
        created_at=timezone.now() - timedelta(minutes=1)
    )
    product = entity_context["cola"]
    second_product = entity_context["pepsi"]
    stock = warehouse.stocks.create(
        product=product,
        quantity=Decimal("12.000"),
        reserved_quantity=Decimal("0.000"),
        low_stock_limit=Decimal("5.000"),
    )
    low_stock = second_warehouse.stocks.create(
        product=second_product,
        quantity=Decimal("1.000"),
        reserved_quantity=Decimal("0.000"),
        low_stock_limit=Decimal("5.000"),
    )
    sale = Sale.objects.create(
        branch=branch,
        warehouse=warehouse,
        cashier=owner,
        status=SaleStatus.COMPLETED,
        sale_date=timezone.now(),
        subtotal=Decimal("12000.00"),
        total_amount=Decimal("12000.00"),
        paid_amount=Decimal("12000.00"),
    )
    second_sale = Sale.objects.create(
        branch=second_branch,
        warehouse=second_warehouse,
        cashier=owner,
        status=SaleStatus.COMPLETED,
        sale_date=timezone.now(),
        subtotal=Decimal("22000.00"),
        total_amount=Decimal("22000.00"),
        paid_amount=Decimal("22000.00"),
    )
    SaleItem.objects.bulk_create(
        [
            SaleItem(
                sale=sale,
                product=product,
                quantity=Decimal("1.000"),
                price=Decimal("12000.00"),
                total_price=Decimal("12000.00"),
            ),
            SaleItem(
                sale=second_sale,
                product=second_product,
                quantity=Decimal("2.000"),
                price=Decimal("11000.00"),
                total_price=Decimal("22000.00"),
            ),
        ]
    )
    SalePayment.objects.create(
        sale=sale,
        payment_method=SalePaymentMethod.CASH,
        amount=Decimal("12000.00"),
    )
    SalePayment.objects.create(
        sale=second_sale,
        payment_method=SalePaymentMethod.CARD,
        amount=Decimal("22000.00"),
    )
    return {
        "branch": branch,
        "low_stock": low_stock,
        "owner": owner,
        "product": product,
        "sale": sale,
        "second_branch": second_branch,
        "second_product": second_product,
        "second_sale": second_sale,
        "second_warehouse": second_warehouse,
        "stock": stock,
        "warehouse": warehouse,
    }


@pytest.mark.django_db
def test_product_stock_tool_returns_safe_response(tool_context):
    result = get_product_stock(
        product_id=str(tool_context["product"].id),
        user=tool_context["owner"],
    )

    assert result["status"] == "ok"
    assert result["data"]["product_name"] == "Coca-Cola 1L"
    assert result["data"]["quantity"] == "12.000"
    assert result["data"]["status"] == "enough"


@pytest.mark.django_db
def test_product_stock_tool_filters_by_warehouse(tool_context):
    result = get_product_stock(
        product_id=str(tool_context["second_product"].id),
        warehouse_id=str(tool_context["second_warehouse"].id),
        user=tool_context["owner"],
    )

    assert result["status"] == "ok"
    assert result["data"]["product_name"] == "Pepsi 1L"
    assert result["data"]["quantity"] == "1.000"
    assert result["data"]["warehouse_name"] == "AI Tool Second Warehouse"
    assert result["data"]["filters"]["warehouse_name"] == "AI Tool Second Warehouse"


@pytest.mark.django_db
def test_product_price_tool_returns_safe_response(tool_context):
    result = get_product_price(
        product_id=str(tool_context["product"].id),
        user=tool_context["owner"],
    )

    assert result["status"] == "ok"
    assert result["data"]["sale_price"] == "12000.00"
    assert result["data"]["purchase_price"] == "0.00"


@pytest.mark.django_db
def test_product_price_tool_hides_purchase_price_from_cashier(tool_context):
    cashier = User.objects.create_user(
        email="ai-price-cashier@example.com",
        password="test-pass-123",
        role=UserRole.CASHIER,
    )

    result = get_product_price(
        product_id=str(tool_context["product"].id),
        user=cashier,
    )

    assert result["status"] == "ok"
    assert "sale_price" in result["data"]
    assert "purchase_price" not in result["data"]


@pytest.mark.django_db
def test_unknown_product_tool_returns_not_found(tool_context):
    result = get_product_stock(product_name="Mars", user=tool_context["owner"])

    assert result["status"] == "not_found"


@pytest.mark.django_db
def test_unknown_warehouse_filter_returns_safe_message(tool_context):
    result = get_product_stock(
        product_id=str(tool_context["product"].id),
        warehouse="Mavjud emas ombor",
        user=tool_context["owner"],
    )

    assert result["status"] == "not_found"
    assert result["entity"] == "warehouse"
    assert "Ombor topilmadi" in render_answer(INTENT_PRODUCT_STOCK, result)


@pytest.mark.django_db
def test_sales_today_tool_returns_ok(tool_context):
    result = get_today_sales(user=tool_context["owner"])

    assert result["status"] == "ok"
    assert result["data"]["sales_count"] >= 1
    assert Decimal(result["data"]["total_amount"]) >= Decimal("12000.00")


@pytest.mark.django_db
def test_sales_today_tool_filters_by_branch(tool_context):
    result = get_today_sales(
        user=tool_context["owner"],
        branch_id=str(tool_context["second_branch"].id),
    )

    assert result["status"] == "ok"
    assert result["data"]["sales_count"] == 1
    assert result["data"]["total_amount"] == "22000.00"
    assert result["data"]["filters"]["branch_name"] == "AI Tool Second Branch"


@pytest.mark.django_db
def test_unknown_branch_filter_returns_safe_message(tool_context):
    result = get_today_sales(user=tool_context["owner"], branch="Mavjud emas filial")

    assert result["status"] == "not_found"
    assert result["entity"] == "branch"
    assert "Filial topilmadi" in render_answer(INTENT_SALES_TODAY, result)


@pytest.mark.django_db
def test_ai_permission_matrix_keeps_sensitive_intents_admin_only():
    cashier = User.objects.create_user(
        email="ai-permission-cashier@example.com",
        password="test-pass-123",
        role=UserRole.CASHIER,
    )
    staff = User.objects.create_user(
        email="ai-permission-staff@example.com",
        password="test-pass-123",
        role=UserRole.CASHIER,
        is_staff=True,
    )
    superuser = User.objects.create_superuser(
        email="ai-permission-superuser@example.com",
        password="test-pass-123",
    )

    assert can_use_intent(cashier, INTENT_PRODUCT_STOCK)
    assert can_use_intent(cashier, INTENT_PRODUCT_PRICE)
    assert not can_use_intent(cashier, INTENT_FINANCE_SUMMARY)
    assert not can_use_intent(cashier, INTENT_REPORTS_SUMMARY)
    assert all(can_use_intent(staff, intent) for intent in INTENTS)
    assert all(can_use_intent(superuser, intent) for intent in INTENTS)


@pytest.mark.django_db
def test_finance_summary_is_denied_to_cashier():
    user = User.objects.create_user(
        email="ai-finance-cashier@example.com",
        password="test-pass-123",
        role=UserRole.CASHIER,
    )
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.post(
        "/api/v1/ai/chat/",
        {"message": "Bugungi foyda qancha?"},
        format="json",
    )

    assert response.status_code == 200
    assert response.data["intent"] == INTENT_FINANCE_SUMMARY
    assert response.data["source"] == "permission_denied"
    assert "ruxsat" in response.data["answer"]
    assert "tushum" not in response.data["answer"].lower()
    assert response.data["display_type"] == "notice"


@pytest.mark.django_db
def test_reports_summary_tool_returns_safe_response(tool_context):
    result = get_reports_summary(user=tool_context["owner"])

    assert result["status"] == "ok"
    assert "sales" in result["data"]
    assert "top_products" in result["data"]
    assert len(result["data"]["top_products"]) <= 5
    assert len(result["data"]["low_stock_products"]) <= 5


@pytest.mark.django_db
def test_low_stock_tool_filters_by_warehouse(tool_context):
    result = get_low_stock_products(
        user=tool_context["owner"],
        warehouse_id=str(tool_context["second_warehouse"].id),
    )

    assert result["status"] == "ok"
    assert result["data"]["count"] == 1
    assert result["data"]["products"][0]["product_name"] == "Pepsi 1L"
    assert result["data"]["filters"]["warehouse_name"] == "AI Tool Second Warehouse"


@pytest.mark.django_db
def test_top_products_tool_filters_by_branch_and_date(tool_context):
    today = timezone.localdate()

    result = get_top_products(
        user=tool_context["owner"],
        branch_id=str(tool_context["second_branch"].id),
        date_from=today.isoformat(),
        date_to=today.isoformat(),
    )

    assert result["status"] == "ok"
    assert result["data"]["products"][0]["product_name"] == "Pepsi 1L"
    assert result["data"]["products"][0]["quantity_sold"] == "2.000"
    assert result["data"]["filters"]["branch_name"] == "AI Tool Second Branch"


@pytest.mark.django_db
def test_chat_endpoint_supports_branch_filtered_sales_question(tool_context):
    client = APIClient()
    client.force_authenticate(user=tool_context["owner"])

    response = client.post(
        "/api/v1/ai/chat/",
        {"message": "Bugun AI Tool Second Branch filialida qancha savdo bo'ldi?"},
        format="json",
    )

    assert response.status_code == 200
    assert response.data["intent"] == INTENT_SALES_TODAY
    assert response.data["source"] == "tool"
    assert response.data["entities"]["branch_id"] == str(tool_context["second_branch"].id)
    assert "Filial: AI Tool Second Branch" in response.data["answer"]


@pytest.mark.django_db
def test_finance_summary_with_branch_filter_is_still_denied_to_cashier(tool_context):
    cashier = User.objects.create_user(
        email="ai-finance-branch-cashier@example.com",
        password="test-pass-123",
        role=UserRole.CASHIER,
    )
    client = APIClient()
    client.force_authenticate(user=cashier)

    response = client.post(
        "/api/v1/ai/chat/",
        {"message": "Bugungi foyda AI Tool Branch filialida qancha?"},
        format="json",
    )

    assert response.status_code == 200
    assert response.data["intent"] == INTENT_FINANCE_SUMMARY
    assert response.data["source"] == "permission_denied"
    assert "ruxsat" in response.data["answer"]


@pytest.mark.django_db
def test_all_ai_tools_return_json_serializable_safe_empty_database_results():
    user = User.objects.create_user(
        email="ai-empty-tools-admin@example.com",
        password="test-pass-123",
        role=UserRole.ADMIN,
        is_staff=True,
    )
    tool_results = [
        get_today_sales(user=user),
        get_monthly_sales(user=user),
        get_product_stock(product_name="missing", user=user),
        get_product_price(product_name="missing", user=user),
        get_low_stock_products(user=user),
        get_top_products(user=user),
        get_cashier_activity(user=user),
        get_finance_summary(user=user),
        get_customer_debt(user=user),
        get_reports_summary(user=user),
    ]

    for result in tool_results:
        json.dumps(result)
        assert result["status"] in {
            "ok",
            "not_found",
            "not_supported",
            "permission_denied",
            "error",
        }

    finance_data = tool_results[7]["data"]
    assert finance_data["estimated_profit"] is None
    assert "tannarx" in finance_data["profit_message"]


@pytest.mark.django_db
def test_extract_entities_product_stock(entity_context):
    entities = extract_entities(
        "Coca-Cola qoldig\u2018i qancha?",
        INTENT_PRODUCT_STOCK,
    )

    assert entities["product_id"] == str(entity_context["cola"].id)
    assert entities["product_name"] == "Coca-Cola 1L"
    assert entities["raw_product_query"] == "coca cola"
    assert entities["product_match_score"] >= 70


@pytest.mark.django_db
def test_extract_entities_product_price(entity_context):
    entities = extract_entities("Pepsi necha pul?", INTENT_PRODUCT_PRICE)

    assert entities["product_id"] == str(entity_context["pepsi"].id)
    assert entities["product_name"] == "Pepsi 1L"


@pytest.mark.django_db
def test_extract_entities_customer_debt(entity_context):
    entities = extract_entities("Ali Valiyev qarzi qancha?", INTENT_CUSTOMER_DEBT)

    assert entities["customer_id"] == str(entity_context["customer"].id)
    assert entities["customer_name"] == "Ali Valiyev"
    assert entities["customer_match_score"] == 100.0


def test_extract_entities_today_date():
    entities = extract_entities("Bugun qancha savdo bo'ldi?", INTENT_SALES_TODAY)

    assert entities["date"] == timezone.localdate().isoformat()


def test_extract_entities_yesterday_date():
    entities = extract_entities("Kecha qancha tushum bo'ldi?", INTENT_SALES_TODAY)

    assert entities["date"] == (timezone.localdate() - timedelta(days=1)).isoformat()


def test_extract_entities_current_month_range():
    today = timezone.localdate()

    entities = extract_entities("Bu oy savdo qancha?", INTENT_SALES_MONTH)

    assert entities["date_range"] == {
        "from": today.replace(day=1).isoformat(),
        "to": today.isoformat(),
    }


def test_extract_entities_last_7_days_range():
    today = timezone.localdate()

    entities = extract_entities("Oxirgi 7 kun savdo qancha?", INTENT_SALES_MONTH)

    assert entities["date_range"] == {
        "from": (today - timedelta(days=6)).isoformat(),
        "to": today.isoformat(),
    }


@pytest.mark.parametrize(
    ("message", "expected_from", "expected_to"),
    [
        ("Today sales", 0, 0),
        ("Yesterday sales", 1, 1),
        ("This week sales", "week_start", 0),
        ("Shu oy savdo qancha?", "month_start", 0),
        ("Last 7 days sales", 6, 0),
    ],
)
def test_extract_entities_ai9_date_phrases(message, expected_from, expected_to):
    today = timezone.localdate()

    def resolve(value):
        if value == "week_start":
            return today - timedelta(days=today.weekday())
        if value == "month_start":
            return today.replace(day=1)
        return today - timedelta(days=value)

    entities = extract_entities(message, INTENT_SALES_MONTH)

    assert entities["date_from"] == resolve(expected_from).isoformat()
    assert entities["date_to"] == resolve(expected_to).isoformat()


def test_extract_entities_low_stock_without_product_does_not_crash():
    entities = extract_entities("Qaysi mahsulotlar kam qolgan?", INTENT_LOW_STOCK)

    assert entities["raw_query"] == "qaysi mahsulotlar kam qolgan"
    assert "product_id" not in entities


@pytest.mark.django_db
def test_extract_entities_empty_catalog_returns_safe_unknown_product():
    entities = extract_entities("Coca-Cola qoldigi qancha?", INTENT_PRODUCT_STOCK)

    assert entities["product_id"] is None
    assert entities["product_name"] is None
    assert entities["raw_product_query"] == "coca cola"
    assert entities["product_match_status"] in {"not_found", "uncertain"}


@pytest.mark.django_db
def test_extract_entities_unknown_product_is_uncertain(entity_context):
    entities = extract_entities("Mars qoldigi qancha?", INTENT_PRODUCT_STOCK)

    assert entities["product_id"] is None
    assert entities["product_name"] is None
    assert entities["raw_product_query"] == "mars"
    assert entities["product_match_status"] in {"not_found", "uncertain"}


@pytest.mark.django_db
def test_extract_entities_cashier_user(entity_context):
    entities = extract_entities(
        "Kassir Demo bugun qancha savdo qildi?",
        INTENT_CASHIER_ACTIVITY,
    )

    assert entities["cashier_id"] == str(entity_context["cashier"].id)
    assert entities["cashier_name"] == "Kassir Demo"


@pytest.mark.django_db
def test_extract_entities_category(entity_context):
    entities = extract_entities(
        "Ichimliklardan qaysilari kam qolgan?",
        INTENT_LOW_STOCK,
    )

    assert entities["category_id"] == str(entity_context["category"].id)
    assert entities["category_name"] == "Ichimliklar"


@pytest.mark.django_db
def test_extract_entities_supplier(entity_context):
    entities = extract_entities(
        "Toshkent Ichimlik Savdo bo'yicha ma'lumot ber",
        INTENT_REPORTS_SUMMARY,
    )

    assert entities["supplier_id"] == str(entity_context["supplier"].id)
    assert entities["supplier_name"] == "Toshkent Ichimlik Savdo"


@pytest.mark.django_db
def test_extract_entities_branch_by_name(tool_context):
    entities = extract_entities(
        "Bugun AI Tool Branch filialida qancha savdo bo'ldi?",
        INTENT_SALES_TODAY,
        user=tool_context["owner"],
    )

    assert entities["branch_id"] == str(tool_context["branch"].id)
    assert entities["branch_name"] == "AI Tool Branch"


@pytest.mark.django_db
def test_extract_entities_branch_by_number(tool_context):
    entities = extract_entities(
        "Shu oy filial 2 da savdo qancha?",
        INTENT_SALES_MONTH,
        user=tool_context["owner"],
    )

    assert entities["branch_id"] == str(tool_context["second_branch"].id)
    assert entities["branch_number"] == 2


@pytest.mark.django_db
def test_extract_entities_warehouse_by_name(tool_context):
    entities = extract_entities(
        "Kecha AI Tool Warehouse omborda Coca-Cola qoldigi qancha?",
        INTENT_PRODUCT_STOCK,
        user=tool_context["owner"],
    )

    assert entities["warehouse_id"] == str(tool_context["warehouse"].id)
    assert entities["warehouse_name"] == "AI Tool Warehouse"
    assert entities["product_id"] == str(tool_context["product"].id)


@pytest.mark.django_db
def test_extract_entities_warehouse_by_number(tool_context):
    entities = extract_entities(
        "Ombor 2 da kam qolgan mahsulotlarni korsat",
        INTENT_LOW_STOCK,
        user=tool_context["owner"],
    )

    assert entities["warehouse_id"] == str(tool_context["second_warehouse"].id)
    assert entities["warehouse_number"] == 2


def test_ai_business_tools_remain_read_only_at_source_level():
    audited_files = [
        Path("apps/ai_assistant/tools.py"),
        Path("apps/ai_assistant/entity.py"),
        Path("apps/ai_assistant/intent.py"),
        Path("apps/ai_assistant/templates.py"),
        Path("apps/ai_assistant/permissions.py"),
    ]
    forbidden_patterns = [
        r"\.save\s*\(",
        r"\.delete\s*\(",
        r"\bbulk_create\s*\(",
        r"\bbulk_update\s*\(",
        r"\bupdate_or_create\s*\(",
        r"\.objects\.create\s*\(",
        r"\.objects\.update\s*\(",
        r"\.filter\([^)]*\)\.update\s*\(",
    ]

    for path in audited_files:
        source = path.read_text(encoding="utf-8")
        for pattern in forbidden_patterns:
            assert not re.search(pattern, source), f"{pattern} found in {path}"


def test_ai_dependency_manifests_do_not_add_external_ai_or_vector_packages():
    manifest_paths = [
        Path("requirements.txt"),
        Path("requirements/dev.txt"),
        Path("frontend/pos/package.json"),
    ]
    forbidden_terms = {
        "openai",
        "anthropic",
        "claude",
        "gemini",
        "google-generativeai",
        "ollama",
        "langchain",
        "chromadb",
        "pinecone",
        "weaviate",
        "qdrant",
        "faiss",
        "llama-index",
    }
    combined = "\n".join(
        path.read_text(encoding="utf-8").lower()
        for path in manifest_paths
        if path.exists()
    )

    for term in forbidden_terms:
        assert term not in combined


def test_frontend_ai_client_uses_existing_api_config_and_hides_raw_tool_result():
    ai_client = Path("frontend/pos/src/services/api/ai.ts").read_text(encoding="utf-8")
    ai_components = "\n".join(
        path.read_text(encoding="utf-8")
        for path in Path("frontend/pos/src/components/ai").glob("*.tsx")
    )

    assert "apiRequest" in ai_client
    assert "localhost" not in ai_client
    assert "127.0.0.1" not in ai_client
    assert "tool_result" not in ai_components
    assert "traceback" not in ai_components.lower()
    assert "Intent:" not in ai_components
