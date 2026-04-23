from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from service.assistant_constraint_parser import parse_assistant_query


def test_parse_assistant_query_extracts_recommendation_constraints() -> None:
    parsed = parse_assistant_query("推荐几种川菜，2个人吃，100元以内，不要花生")

    assert parsed.query_type == "recommendation"
    assert parsed.cuisine_types == ["川菜"]
    assert parsed.party_size == 2
    assert parsed.budget_max == 100.0
    assert parsed.exclude_allergens == ["花生"]
    assert parsed.needs_clarification is False


def test_parse_assistant_query_requests_clarification_for_sparse_recommendation() -> None:
    parsed = parse_assistant_query("推荐几种川菜")

    assert parsed.query_type == "recommendation"
    assert parsed.cuisine_types == ["川菜"]
    assert parsed.needs_clarification is True
    assert parsed.clarification_question == "请告诉我这顿大概几个人吃、预算多少？"


def test_parse_assistant_query_detects_comparison_targets() -> None:
    parsed = parse_assistant_query("帮我对比兰姨小炒和午后豆房")

    assert parsed.query_type == "comparison"
    assert parsed.comparison_targets == ["兰姨小炒", "午后豆房"]


def test_parse_assistant_query_leaves_generic_comparison_without_literal_targets() -> None:
    parsed = parse_assistant_query("比较两家商家")

    assert parsed.query_type == "comparison"
    assert parsed.comparison_targets == []
