import json

from service.agent_planner import AgentPlanner


class StubLLM:
    def __init__(self, payload: dict):
        self.payload = payload

    def call(self, query: str, system_instruction: str) -> str:
        return json.dumps(self.payload, ensure_ascii=False)


def test_planner_routes_sparse_recommendation_to_clarification() -> None:
    planner = AgentPlanner()
    planner._llm = StubLLM({
        "intent": "recommendation",
        "reasoning_summary": "缺少人数和预算",
        "tool_plan": [],
        "missing_slots": ["budget", "party_size"],
        "clarification_question": "请告诉我这顿几个人吃、预算多少？",
        "needs_confirmation": False,
    })

    decision = planner.plan("推荐几种川菜", session_context={})

    assert decision.intent == "recommendation"
    assert decision.missing_slots == ["budget", "party_size"]
    assert "预算" in decision.clarification_question


def test_planner_builds_mixed_task_plan() -> None:
    planner = AgentPlanner()
    planner._llm = StubLLM({
        "intent": "mixed_task",
        "reasoning_summary": "推荐并准备加购",
        "tool_plan": [
            {
                "tool": "recommend_dishes",
                "arguments": {"query": "川菜", "budget": 100, "party_size": 2},
                "requires_confirmation": False,
            }
        ],
        "missing_slots": [],
        "needs_confirmation": True,
    })

    decision = planner.plan("2个人100元以内推荐川菜并加入购物车", session_context={})

    assert decision.intent == "mixed_task"
    assert decision.tool_plan[0].tool_name == "recommend_dishes"
    assert decision.needs_confirmation is True


def test_planner_rule_fallback_detects_address_action() -> None:
    planner = AgentPlanner()
    planner._model_name = None

    decision = planner.plan(
        "帮我将以下地址加入地址管理：上海市静安区南京西路818号，联系人张三，电话13800000000",
        session_context={},
    )

    assert decision.intent == "address_action"
    assert decision.tool_plan[0].tool_name == "parse_address"
