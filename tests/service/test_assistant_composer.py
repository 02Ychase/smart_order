from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from service.assistant_composer import compose_assistant_response
from service.assistant_models import AssistantCandidate, AssistantParsedQuery


def test_compose_assistant_response_builds_recommendation_payload() -> None:
    parsed = AssistantParsedQuery(
        raw_message="推荐几种川菜，2个人吃，100元以内，不要花生",
        query_type="recommendation",
        cuisine_types=["川菜"],
        budget_max=100.0,
        party_size=2,
        exclude_allergens=["花生"],
        comparison_targets=[],
        needs_clarification=False,
        clarification_question=None,
    )
    candidates = [
        AssistantCandidate(
            source_type="dish",
            source_id=11,
            merchant_id=1,
            merchant_name="兰姨小炒",
            dish_id=11,
            dish_name="鱼香肉丝",
            price=28.0,
            score=0.93,
            summary="酸甜微辣，下饭感强，适合两人晚餐",
            reason_facts=["川菜", "28元", "不含花生"],
            citation_title="鱼香肉丝｜兰姨小炒",
            citation_snippet="川菜；酸甜微辣；配料为猪里脊、木耳、胡萝卜、青椒",
        )
    ]

    response = compose_assistant_response("session-1", parsed, candidates)

    assert response["session_id"] == "session-1"
    assert response["needs_clarification"] is False
    assert response["recommendations"][0]["dish_name"] == "鱼香肉丝"
    assert response["recommendations"][0]["reason"] == "匹配川菜偏好，单价 28 元，且未命中花生过敏原。"
    assert response["citations"][0]["title"] == "鱼香肉丝｜兰姨小炒"


def test_compose_assistant_response_builds_clarification_payload() -> None:
    parsed = AssistantParsedQuery(
        raw_message="推荐几种川菜",
        query_type="recommendation",
        cuisine_types=["川菜"],
        budget_max=None,
        party_size=None,
        exclude_allergens=[],
        comparison_targets=[],
        needs_clarification=True,
        clarification_question="请告诉我这顿大概几个人吃、预算多少？",
    )

    response = compose_assistant_response("session-1", parsed, [])

    assert response["needs_clarification"] is True
    assert response["clarification_question"] == "请告诉我这顿大概几个人吃、预算多少？"
    assert response["recommendations"] == []
