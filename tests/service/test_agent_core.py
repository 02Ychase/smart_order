from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from service.agent_core import AgentCore, AgentDecision


class StubLLM:
    def __init__(self, response: dict):
        self._response = response

    def call(self, query: str, system_instruction: str = "", tools: list = None) -> dict:
        return self._response


def test_agent_core_decides_greeting() -> None:
    core = AgentCore()
    core._llm = StubLLM({
        "reasoning": "用户说你好，是问候",
        "intent": "greeting",
        "needs_clarification": False,
        "tool_calls": [],
        "search_query": None,
    })

    decision = core.decide("你好")

    assert decision.intent == "greeting"
    assert decision.needs_clarification is False
    assert len(decision.tool_calls) == 0


def test_agent_core_decides_knowledge_query() -> None:
    core = AgentCore()
    core._llm = StubLLM({
        "reasoning": "用户想找卖咖啡的店，属于查询类需求，不需要预算和人数",
        "intent": "knowledge",
        "needs_clarification": False,
        "tool_calls": [{"name": "search_knowledge_base", "parameters": {"query": "咖啡店"}}],
        "search_query": "咖啡店",
    })

    decision = core.decide("推荐几个卖咖啡的店")

    assert decision.intent == "knowledge"
    assert decision.needs_clarification is False
    assert len(decision.tool_calls) == 1
    assert decision.tool_calls[0]["name"] == "search_knowledge_base"


def test_agent_core_decides_recommendation_needs_clarification() -> None:
    core = AgentCore()
    core._llm = StubLLM({
        "reasoning": "用户想要推荐，但缺少预算和人数",
        "intent": "recommendation",
        "needs_clarification": True,
        "clarification_question": "请告诉我这顿大概几个人吃、预算多少？",
        "tool_calls": [],
        "search_query": None,
    })

    decision = core.decide("推荐几个川菜")

    assert decision.intent == "recommendation"
    assert decision.needs_clarification is True
    assert decision.clarification_question == "请告诉我这顿大概几个人吃、预算多少？"


def test_agent_core_decides_action_intent() -> None:
    core = AgentCore()
    core._llm = StubLLM({
        "reasoning": "用户想要加菜到购物车",
        "intent": "action",
        "needs_clarification": False,
        "tool_calls": [{"name": "add_to_cart", "parameters": {"dish_id": 11, "quantity": 1}}],
        "search_query": None,
    })

    decision = core.decide("帮我加一份鱼香肉丝到购物车")

    assert decision.intent == "action"
    assert len(decision.tool_calls) == 1
    assert decision.tool_calls[0]["name"] == "add_to_cart"


def test_agent_core_rule_based_fallback_for_knowledge() -> None:
    """当没有MODEL_NAME时，rule-based应正确识别知识查询"""
    import os
    os.environ.pop("MODEL_NAME", None)
    core = AgentCore()
    core._llm = None  # 确保不走注入的LLM
    core._model_name = None

    decision = core.decide("有哪些卖咖啡的店")

    assert decision.intent == "knowledge"
    assert decision.needs_clarification is False


def test_agent_core_rule_based_fallback_for_recommendation() -> None:
    """当没有MODEL_NAME时，rule-based应正确识别推荐并询问约束"""
    core = AgentCore()
    core._llm = None
    core._model_name = None

    decision = core.decide("推荐几个川菜")

    assert decision.intent == "recommendation"
    assert decision.needs_clarification is True
