from service.agent_runtime.state import AgentPlan
from service.rag.query_planner import RagQueryPlanner


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
    assert "湘菜 香辣 下饭" in plan.expansion_queries
    assert plan.source_types == ["dish"]
    assert plan.should_filters["cuisine_types"] == ["湘菜"]


def test_query_planner_routes_merchant_knowledge_queries_to_merchants() -> None:
    planner = RagQueryPlanner()
    agent_plan = AgentPlan(
        intent="knowledge",
        normalized_query="有哪些咖啡甜品店？几点营业？",
        requires_rag=True,
    )

    plan = planner.plan("有哪些咖啡甜品店？几点营业？", agent_plan, memories=[])

    assert plan.source_types == ["merchant"]
