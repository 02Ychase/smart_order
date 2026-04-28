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


def test_hard_filters_remove_missing_availability_when_required() -> None:
    candidates = [
        FusedCandidate(stable_key="dish:1", source_type="dish", source_id=1, facts={}),
        FusedCandidate(stable_key="dish:2", source_type="dish", source_id=2, facts={"is_available": True}),
    ]
    plan = RagQueryPlan(
        original_query="可售菜品",
        normalized_query="可售菜品",
        must_filters={"is_available": True},
        should_filters={},
        source_types=["dish"],
    )

    filtered = apply_hard_filters(candidates, plan)

    assert [item.stable_key for item in filtered] == ["dish:2"]


def test_hard_filters_remove_missing_allergens_when_excluding_allergens() -> None:
    candidates = [
        FusedCandidate(stable_key="dish:1", source_type="dish", source_id=1, facts={}),
        FusedCandidate(stable_key="dish:2", source_type="dish", source_id=2, facts={"allergens": []}),
    ]
    plan = RagQueryPlan(
        original_query="不要花生",
        normalized_query="不要花生",
        must_filters={"exclude_allergens": ["花生"]},
        should_filters={},
        source_types=["dish"],
    )

    filtered = apply_hard_filters(candidates, plan)

    assert [item.stable_key for item in filtered] == ["dish:2"]


def test_hard_filters_apply_cuisine_budget_and_keyword_constraints() -> None:
    candidates = [
        FusedCandidate(
            stable_key="dish:1",
            source_type="dish",
            source_id=1,
            facts={
                "dish_name": "芝士披萨",
                "cuisine_type": "意式",
                "description": "浓郁芝士披萨",
                "price": 42.0,
                "is_available": True,
            },
        ),
        FusedCandidate(
            stable_key="dish:2",
            source_type="dish",
            source_id=2,
            facts={
                "dish_name": "麻辣披萨",
                "cuisine_type": "意式",
                "description": "麻辣浓郁",
                "price": 42.0,
                "is_available": True,
            },
        ),
        FusedCandidate(
            stable_key="dish:3",
            source_type="dish",
            source_id=3,
            facts={
                "dish_name": "芝士焗饭",
                "cuisine_type": "轻食",
                "description": "浓郁芝士",
                "price": 42.0,
                "is_available": True,
            },
        ),
        FusedCandidate(
            stable_key="dish:4",
            source_type="dish",
            source_id=4,
            facts={
                "dish_name": "芝士披萨",
                "cuisine_type": "意式",
                "description": "浓郁芝士披萨",
                "price": 88.0,
                "is_available": True,
            },
        ),
    ]
    plan = RagQueryPlan(
        original_query="recommend some cheesy pizza",
        normalized_query="芝士披萨",
        must_filters={
            "is_available": True,
            "cuisine_types": ["意式"],
            "required_keywords": ["披萨", "芝士"],
            "forbidden_keywords": ["麻辣浓郁"],
            "budget_max": 100,
            "party_size": 2,
        },
        should_filters={},
        source_types=["dish"],
    )

    filtered = apply_hard_filters(candidates, plan)

    assert [item.stable_key for item in filtered] == ["dish:1"]
