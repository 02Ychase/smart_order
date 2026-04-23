from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from service.constraint_resolver import ConstraintResolver, ResolvedConstraints


def test_resolve_recommendation_constraints() -> None:
    resolver = ConstraintResolver()
    result = resolver.resolve("推荐几种川菜，2个人吃，100元以内，不要花生")

    assert result.cuisine_types == ["川菜"]
    assert result.party_size == 2
    assert result.budget_max == 100.0
    assert result.exclude_allergens == ["花生"]
    assert result.is_sufficient_for_recommendation() is True


def test_resolve_requests_clarification_when_sparse() -> None:
    resolver = ConstraintResolver()
    result = resolver.resolve("推荐几种川菜")

    assert result.cuisine_types == ["川菜"]
    assert result.is_sufficient_for_recommendation() is False


def test_resolve_comparison_targets() -> None:
    resolver = ConstraintResolver()
    result = resolver.resolve("比较兰姨小炒和午后豆房")

    assert result.comparison_targets == ["兰姨小炒", "午后豆房"]
    assert result.is_sufficient_for_comparison() is True
