from service.rag.filters import apply_hard_filters
from service.rag.models import FusedCandidate, RagQueryPlan


def test_hard_filters_remove_allergen_matches() -> None:
    candidates = [
        FusedCandidate(stable_key="dish:1", source_type="dish", source_id=1, facts={"allergens": ["花生"], "is_available": True}),
        FusedCandidate(stable_key="dish:2", source_type="dish", source_id=2, facts={"allergens": [], "is_available": True}),
    ]
    plan = RagQueryPlan(
        original_query="不要花生",
        normalized_query="湘菜",
        must_filters={"exclude_allergens": ["花生"], "is_available": True},
        should_filters={},
        source_types=["dish"],
    )

    filtered = apply_hard_filters(candidates, plan)

    assert [item.stable_key for item in filtered] == ["dish:2"]
