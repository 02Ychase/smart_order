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


def test_hard_filters_keep_missing_allergens_when_excluding_allergens() -> None:
    """Missing allergens (None or absent) means 'unknown', not 'contains allergen'."""
    candidates = [
        FusedCandidate(stable_key="dish:1", source_type="dish", source_id=1, facts={}),
        FusedCandidate(stable_key="dish:2", source_type="dish", source_id=2, facts={"allergens": []}),
        FusedCandidate(stable_key="dish:3", source_type="dish", source_id=3, facts={"allergens": None}),
    ]
    plan = RagQueryPlan(
        original_query="不要花生",
        normalized_query="不要花生",
        must_filters={"exclude_allergens": ["花生"]},
        should_filters={},
        source_types=["dish"],
    )

    filtered = apply_hard_filters(candidates, plan)

    # All three should pass — none of them declare containing "花生"
    assert [item.stable_key for item in filtered] == ["dish:1", "dish:2", "dish:3"]


def test_hard_filters_remove_only_confirmed_allergen_matches() -> None:
    """Only dishes that explicitly list a matching allergen get filtered."""
    candidates = [
        FusedCandidate(stable_key="dish:1", source_type="dish", source_id=1, facts={"allergens": ["花生", "牛奶"]}),
        FusedCandidate(stable_key="dish:2", source_type="dish", source_id=2, facts={"allergens": ["虾"]}),
        FusedCandidate(stable_key="dish:3", source_type="dish", source_id=3, facts={}),
        FusedCandidate(stable_key="dish:4", source_type="dish", source_id=4, facts={"allergens": []}),
    ]
    plan = RagQueryPlan(
        original_query="不要花生",
        normalized_query="推荐菜品",
        must_filters={"exclude_allergens": ["花生"]},
        should_filters={},
        source_types=["dish"],
    )

    filtered = apply_hard_filters(candidates, plan)

    # dish:1 removed (contains 花生), others kept
    assert [item.stable_key for item in filtered] == ["dish:2", "dish:3", "dish:4"]


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
        },
        should_filters={},
        source_types=["dish"],
    )

    filtered = apply_hard_filters(candidates, plan)

    # dish:2 removed (forbidden keyword), dish:3 removed (wrong cuisine)
    # dish:1 (42元) and dish:4 (88元) both under budget_max=100 → kept
    assert [item.stable_key for item in filtered] == ["dish:1", "dish:4"]


def test_budget_filter_only_excludes_single_dish_exceeding_budget() -> None:
    """Budget filter should only exclude a dish whose price alone exceeds budget."""
    candidates = [
        FusedCandidate(stable_key="dish:1", source_type="dish", source_id=1,
                       facts={"price": 30.0}),
        FusedCandidate(stable_key="dish:2", source_type="dish", source_id=2,
                       facts={"price": 80.0}),
        FusedCandidate(stable_key="dish:3", source_type="dish", source_id=3,
                       facts={"price": 150.0}),
        FusedCandidate(stable_key="dish:4", source_type="dish", source_id=4,
                       facts={}),
    ]
    plan = RagQueryPlan(
        original_query="预算100",
        normalized_query="推荐菜品",
        must_filters={"budget_max": 100, "party_size": 4},
        should_filters={},
        source_types=["dish"],
    )

    filtered = apply_hard_filters(candidates, plan)

    # dish:3 (150元 > 100) removed; dish:4 (no price) kept; party_size ignored
    assert [item.stable_key for item in filtered] == ["dish:1", "dish:2", "dish:4"]
