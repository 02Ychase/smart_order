from service.agent_runtime.state import AgentPlan
from service.rag.query_planner import (
    RagQueryPlanner,
    _extract_dish_preferences,
    _extract_merchant_preferences,
)


def test_query_planner_generates_expansion_queries_for_spicy_hunan() -> None:
    planner = RagQueryPlanner()
    agent_plan = AgentPlan(
        intent="recommendation",
        normalized_query="辣的湘菜",
        filters={"cuisine_types": ["湘菜"], "flavor_preferences": ["辣"], "budget_max": None, "party_size": None, "exclude_allergens": []},
        requires_rag=True,
    )

    plan = planner.plan("帮我推荐几个比较辣的湘菜", agent_plan, memories=[])

    assert plan.normalized_query == "辣的湘菜"
    assert "辣的湘菜" in plan.expansion_queries
    assert "帮我推荐几个比较辣的湘菜" in plan.expansion_queries
    assert plan.source_types == ["dish"]
    assert plan.should_filters["cuisine_types"] == ["湘菜"]
    assert plan.should_filters["flavor_preferences"] == ["辣"]
    assert "湘菜" in plan.must_filters["cuisine_types"]
    assert plan.preferred_dishes == []
    assert plan.preferred_merchants == []


def test_query_planner_routes_merchant_knowledge_queries_to_merchants() -> None:
    planner = RagQueryPlanner()
    agent_plan = AgentPlan(
        intent="knowledge",
        normalized_query="有哪些咖啡甜品店？几点营业？",
        requires_rag=True,
    )

    plan = planner.plan("有哪些咖啡甜品店？几点营业？", agent_plan, memories=[])

    assert plan.source_types == ["merchant"]
    assert plan.preferred_dishes == []
    assert plan.preferred_merchants == []


# ── Dish preference extraction tests ─────────────────────────────────────────


def test_extract_dish_preferences_simple_like() -> None:
    result = _extract_dish_preferences("用户喜欢宫保鸡丁，也爱吃鱼香肉丝")
    assert "宫保鸡丁" in result
    assert "鱼香肉丝" in result


def test_extract_dish_preferences_often_order() -> None:
    result = _extract_dish_preferences("经常点水煮鱼，偶尔点麻辣香锅")
    assert "水煮鱼" in result
    assert "麻辣香锅" in result


def test_extract_dish_preferences_want_to_eat() -> None:
    result = _extract_dish_preferences("想吃酸菜鱼，还要小炒黄牛肉")
    assert "酸菜鱼" in result
    assert "小炒黄牛肉" in result


def test_extract_dish_preferences_recommend() -> None:
    result = _extract_dish_preferences("推荐麻婆豆腐")
    assert "麻婆豆腐" in result


def test_extract_dish_preferences_no_match_returns_empty() -> None:
    result = _extract_dish_preferences("今天天气真好")
    assert result == []


def test_extract_dish_preferences_strips_whitespace() -> None:
    result = _extract_dish_preferences("喜欢吃  回锅肉  ，还可以")
    assert "回锅肉" in result


# ── Merchant preference extraction tests ─────────────────────────────────────


def test_extract_merchant_preferences_often_go_to() -> None:
    result = _extract_merchant_preferences("用户经常去麦当劳，也喜欢去海底捞")
    assert "麦当劳" in result
    assert "海底捞" in result


def test_extract_merchant_preferences_like_go_to() -> None:
    result = _extract_merchant_preferences("喜欢去星巴克，常去必胜客")
    assert "星巴克" in result
    assert "必胜客" in result


def test_extract_merchant_preferences_recommend() -> None:
    result = _extract_merchant_preferences("推荐兰姨小炒")
    assert "兰姨小炒" in result


def test_extract_merchant_preferences_no_match_returns_empty() -> None:
    result = _extract_merchant_preferences("今天天气真好")
    assert result == []


# ── Query plan integration tests with memories ───────────────────────────────


def test_dish_preference_memories_populate_preferred_dishes() -> None:
    planner = RagQueryPlanner()
    agent_plan = AgentPlan(
        intent="recommendation",
        normalized_query="推荐一些菜",
        requires_rag=True,
    )
    memories = [
        {"memory_type": "dish_preference", "content": "用户喜欢宫保鸡丁，爱吃鱼香肉丝"},
    ]

    plan = planner.plan("推荐一些菜", agent_plan, memories=memories)

    assert "宫保鸡丁" in plan.preferred_dishes
    assert "鱼香肉丝" in plan.preferred_dishes


def test_merchant_preference_memories_populate_preferred_merchants() -> None:
    planner = RagQueryPlanner()
    agent_plan = AgentPlan(
        intent="recommendation",
        normalized_query="推荐一些店",
        requires_rag=True,
    )
    memories = [
        {"memory_type": "merchant_preference", "content": "用户经常去麦当劳"},
    ]

    plan = planner.plan("推荐一些店", agent_plan, memories=memories)

    assert "麦当劳" in plan.preferred_merchants


def test_food_preference_memories_also_extract_dish_and_merchant() -> None:
    planner = RagQueryPlanner()
    agent_plan = AgentPlan(
        intent="recommendation",
        normalized_query="推荐辣的",
        requires_rag=True,
    )
    memories = [
        {"memory_type": "food_preference", "content": "很喜欢吃宫保鸡丁，经常去海底捞"},
    ]

    plan = planner.plan("推荐辣的", agent_plan, memories=memories)

    assert "宫保鸡丁" in plan.preferred_dishes
    assert "海底捞" in plan.preferred_merchants


def test_multiple_memory_types_combined() -> None:
    planner = RagQueryPlanner()
    agent_plan = AgentPlan(
        intent="recommendation",
        normalized_query="推荐好吃的",
        requires_rag=True,
    )
    memories = [
        {"memory_type": "dish_preference", "content": "爱吃麻婆豆腐"},
        {"memory_type": "merchant_preference", "content": "推荐必胜客"},
        {"memory_type": "food_preference", "content": "喜欢辣的湘菜，经常点宫保鸡丁"},
        {"memory_type": "dietary_constraint", "content": "不吃花生"},
    ]

    plan = planner.plan("推荐好吃的", agent_plan, memories=memories)

    assert "麻婆豆腐" in plan.preferred_dishes
    assert "宫保鸡丁" in plan.preferred_dishes
    assert "必胜客" in plan.preferred_merchants
    # Allergen extraction still works
    assert "花生" in plan.must_filters["exclude_allergens"]


def test_preferred_dishes_deduplicated() -> None:
    planner = RagQueryPlanner()
    agent_plan = AgentPlan(
        intent="recommendation",
        normalized_query="推荐",
        requires_rag=True,
    )
    memories = [
        {"memory_type": "dish_preference", "content": "喜欢吃宫保鸡丁"},
        {"memory_type": "food_preference", "content": "爱吃宫保鸡丁和鱼香肉丝"},
    ]

    plan = planner.plan("推荐", agent_plan, memories=memories)

    assert plan.preferred_dishes.count("宫保鸡丁") == 1
    assert "鱼香肉丝" in plan.preferred_dishes


def test_backward_compatible_no_new_memory_types() -> None:
    """Existing memory types without dish/merchant preferences should still work."""
    planner = RagQueryPlanner()
    agent_plan = AgentPlan(
        intent="recommendation",
        normalized_query="辣的湘菜",
        filters={"cuisine_types": [], "flavor_preferences": [], "exclude_allergens": []},
        requires_rag=True,
    )
    memories = [
        {"memory_type": "dietary_constraint", "content": "对海鲜过敏"},
        {"memory_type": "food_preference", "content": "喜欢辣的川菜"},
    ]

    plan = planner.plan("帮我推荐菜", agent_plan, memories=memories)

    assert "海鲜" in plan.must_filters["exclude_allergens"]
    assert "川菜" in plan.must_filters["cuisine_types"]
    assert "辣" in plan.should_filters["flavor_preferences"]
    assert plan.preferred_dishes == []
    assert plan.preferred_merchants == []
