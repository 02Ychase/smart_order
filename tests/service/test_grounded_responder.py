from pathlib import Path
import sys
from unittest.mock import MagicMock, patch

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from service.grounded_responder import GroundedResponder
from service.assistant_models import AssistantCandidate
from service.constraint_resolver import ResolvedConstraints


def test_respond_to_greeting() -> None:
    responder = GroundedResponder()
    result = responder.respond(
        intent="greeting",
        user_message="Hi",
        constraints=None,
        evidence=[],
        session_context=[],
    )

    assert result["response_type"] == "greeting"
    assert result["message"] != ""
    assert result["recommendations"] == []


def test_respond_to_action_intent() -> None:
    responder = GroundedResponder()
    result = responder.respond(
        intent="action_intent",
        user_message="帮我加入购物车",
        constraints=None,
        evidence=[],
        session_context=[],
    )

    assert result["response_type"] == "action_pending"
    assert "下一阶段" in result["message"] or "尚未" in result["message"]


def test_respond_to_recommendation_with_evidence() -> None:
    responder = GroundedResponder()
    evidence = [
        AssistantCandidate(
            source_type="dish",
            source_id=11,
            merchant_id=1,
            merchant_name="兰姨小炒",
            dish_id=11,
            dish_name="鱼香肉丝",
            price=28.0,
            score=0.93,
            summary="酸甜微辣，下饭感强",
            reason_facts=["川菜", "28元"],
            citation_title="鱼香肉丝｜兰姨小炒",
            citation_snippet="川菜；酸甜微辣",
        )
    ]
    result = responder.respond(
        intent="recommendation",
        user_message="推荐几种川菜",
        constraints=ResolvedConstraints(
            raw_message="推荐几种川菜",
            query_type="recommendation",
            cuisine_types=["川菜"],
            budget_max=100.0,
            party_size=2,
        ),
        evidence=evidence,
        session_context=[],
    )

    assert result["response_type"] == "recommendation"
    assert len(result["recommendations"]) >= 1
    assert result["recommendations"][0]["dish_name"] == "鱼香肉丝"
    assert len(result["citations"]) >= 1


def test_respond_uses_llm_when_model_available() -> None:
    responder = GroundedResponder()
    responder._model_name = "gpt-test"

    evidence = [
        AssistantCandidate(
            source_type="dish",
            source_id=11,
            merchant_id=1,
            merchant_name="兰姨小炒",
            dish_id=11,
            dish_name="鱼香肉丝",
            price=28.0,
            score=0.93,
            summary="酸甜微辣，下饭感强",
            reason_facts=["川菜", "28元"],
            citation_title="鱼香肉丝｜兰姨小炒",
            citation_snippet="川菜；酸甜微辣",
        )
    ]

    llm_response = '{"message": "为您推荐兰姨小炒的鱼香肉丝，酸甜微辣很下饭！", "suggested_actions": ["加入购物车"]}'

    with patch("service.grounded_responder.call_llm", return_value=llm_response):
        result = responder.respond(
            intent="recommendation",
            user_message="推荐几种川菜",
            constraints=ResolvedConstraints(
                raw_message="推荐几种川菜",
                query_type="recommendation",
                cuisine_types=["川菜"],
                budget_max=100.0,
                party_size=2,
            ),
            evidence=evidence,
            session_context=[],
        )

    assert result["response_type"] == "recommendation"
    assert "鱼香肉丝" in result["message"]
    assert result["suggested_actions"] == ["加入购物车"]
    assert len(result["citations"]) >= 1


def test_respond_falls_back_to_template_on_llm_failure() -> None:
    responder = GroundedResponder()
    responder._model_name = "gpt-test"

    evidence = [
        AssistantCandidate(
            source_type="dish",
            source_id=11,
            merchant_id=1,
            merchant_name="兰姨小炒",
            dish_id=11,
            dish_name="鱼香肉丝",
            price=28.0,
            score=0.93,
            summary="酸甜微辣，下饭感强",
            reason_facts=["川菜", "28元"],
            citation_title="鱼香肉丝｜兰姨小炒",
            citation_snippet="川菜；酸甜微辣",
        )
    ]

    with patch("service.grounded_responder.call_llm", side_effect=Exception("LLM timeout")):
        result = responder.respond(
            intent="recommendation",
            user_message="推荐几种川菜",
            constraints=ResolvedConstraints(
                raw_message="推荐几种川菜",
                query_type="recommendation",
                cuisine_types=["川菜"],
                budget_max=100.0,
                party_size=2,
            ),
            evidence=evidence,
            session_context=[],
        )

    assert result["response_type"] == "recommendation"
    assert len(result["recommendations"]) >= 1
    assert result["recommendations"][0]["dish_name"] == "鱼香肉丝"
    assert len(result["citations"]) >= 1
