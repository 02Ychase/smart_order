from service.agent_runtime.planner import LangGraphAgentPlanner


class StubLLM:
    def __init__(self, payload):
        self.payload = payload

    def call(self, query: str, system_instruction: str):
        return self.payload


def test_planner_recommends_directly_without_budget_or_party_size() -> None:
    planner = LangGraphAgentPlanner()
    planner._llm = StubLLM({
        "intent": "recommendation",
        "normalized_query": "辣的湘菜",
        "requires_rag": True,
        "filters": {"cuisine_types": ["湘菜"], "flavor_preferences": ["辣"]},
        "tool_calls": [],
        "should_answer_directly": True,
        "response_hint": "推荐辣味湘菜",
    })

    plan = planner.plan("帮我推荐几个比较辣的湘菜", {"loaded_user_memories": []})

    assert plan.intent == "recommendation"
    assert plan.should_answer_directly is True
    assert plan.requires_rag is True
    assert plan.filters["cuisine_types"] == ["湘菜"]
    assert plan.filters["party_size"] is None
    assert plan.filters["budget_max"] is None


def test_planner_rule_fallback_detects_undo() -> None:
    planner = LangGraphAgentPlanner()
    planner._llm = None
    planner._model_name = None

    plan = planner.plan("帮我撤回刚才的删除", {"recent_action_ids": ["act_1"]})

    assert plan.intent == "undo_action"
    assert plan.tool_calls[0].tool_name == "undo_last_action"


def test_planner_rule_fallback_routes_cart_clear_as_direct_write() -> None:
    planner = LangGraphAgentPlanner()
    planner._llm = None
    planner._model_name = None

    plan = planner.plan("清空购物车", {"user_id": 9})

    assert plan.intent == "cart_action"
    assert plan.tool_calls[0].tool_name == "cart_clear"
    assert plan.tool_calls[0].writes_database is True
