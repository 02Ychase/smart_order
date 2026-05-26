"""Tests for ReAct compound task enhancements."""

from unittest.mock import MagicMock, patch

from langchain_core.messages import HumanMessage

from service.agent_runtime.graph import build_agent_graph
from service.agent_runtime.nodes import LocalActionExecutor, _normalize_tool_result, _successful_step_ids, evaluate_node, plan_node, rag_node, respond_node, route_after_plan
from service.agent_runtime.planner import ACTION_TOOL_NAMES, LangGraphAgentPlanner
from service.agent_runtime.runtime import AgentRuntimeContext
from service.agent_runtime.state import AgentPlan, GraphToolCall


def test_graph_tool_call_has_step_id_field():
    call = GraphToolCall(tool_name="add_to_cart", arguments={"dish_id": 1}, writes_database=True)
    assert hasattr(call, "step_id")
    assert call.step_id == ""


def test_graph_tool_call_step_id_can_be_set():
    call = GraphToolCall(
        tool_name="add_to_cart",
        arguments={"dish_id": 1},
        writes_database=True,
        step_id="add_to_cart_0",
    )
    assert call.step_id == "add_to_cart_0"


def test_parse_tool_calls_generates_unique_step_ids():
    """Same tool_name with different arguments must NOT be deduplicated."""
    planner = LangGraphAgentPlanner()
    raw_calls = [
        {"tool_name": "add_to_cart", "arguments": {"dish_id": 12, "quantity": 1}, "writes_database": True},
        {"tool_name": "add_to_cart", "arguments": {"dish_id": 35, "quantity": 1}, "writes_database": True},
        {"tool_name": "add_to_cart", "arguments": {"dish_id": 7, "quantity": 1}, "writes_database": True},
    ]
    calls = planner._parse_tool_calls(raw_calls, "cart_action")
    assert len(calls) == 3
    step_ids = [c.step_id for c in calls]
    assert step_ids == ["add_to_cart_0", "add_to_cart_1", "add_to_cart_2"]
    assert calls[0].arguments["dish_id"] == 12
    assert calls[1].arguments["dish_id"] == 35
    assert calls[2].arguments["dish_id"] == 7


def test_parse_tool_calls_deduplicates_by_step_id():
    """Calls with the same explicit step_id should be deduplicated."""
    planner = LangGraphAgentPlanner()
    raw_calls = [
        {"tool_name": "add_to_cart", "arguments": {"dish_id": 12}, "writes_database": True, "step_id": "add_to_cart_0"},
        {"tool_name": "add_to_cart", "arguments": {"dish_id": 12}, "writes_database": True, "step_id": "add_to_cart_0"},
    ]
    calls = planner._parse_tool_calls(raw_calls, "cart_action")
    assert len(calls) == 1


def test_parse_tool_calls_preserves_llm_step_id():
    """If the LLM provides a step_id, it should be preserved."""
    planner = LangGraphAgentPlanner()
    raw_calls = [
        {"tool_name": "recommend_dishes", "arguments": {"query": "川菜"}, "writes_database": False, "step_id": "rag_sichuan"},
    ]
    calls = planner._parse_tool_calls(raw_calls, "recommendation")
    assert calls[0].step_id == "rag_sichuan"


def test_normalize_tool_result_includes_step_id():
    result = {"success": True, "message": "done", "data": {}}
    state = {"current_plan": None}
    normalized = _normalize_tool_result(result, state, executed_tool_name="add_to_cart", step_id="add_to_cart_0")
    assert normalized["step_id"] == "add_to_cart_0"
    assert normalized["type"] == "add_to_cart"


def test_completed_tools_by_step_id_not_tool_name():
    """Two add_to_cart calls: completing step_id=add_to_cart_0 should NOT mark add_to_cart_1 as done."""
    plan = AgentPlan(
        intent="cart_action",
        tool_calls=[
            GraphToolCall("add_to_cart", {"dish_id": 12}, True, step_id="add_to_cart_0"),
            GraphToolCall("add_to_cart", {"dish_id": 35}, True, step_id="add_to_cart_1"),
        ],
    )
    tool_results = [
        {"type": "add_to_cart", "step_id": "add_to_cart_0", "success": True, "message": "done", "data": {}},
    ]
    completed_step_ids = {r.get("step_id") or r.get("type", "") for r in tool_results}
    remaining = [c for c in plan.tool_calls if c.step_id not in completed_step_ids]
    assert len(remaining) == 1
    assert remaining[0].step_id == "add_to_cart_1"
    assert remaining[0].arguments["dish_id"] == 35


def test_plan_reuse_on_pending_calls():
    """When current plan has pending (not-yet-completed) calls, plan_node should reuse it."""
    original_plan = AgentPlan(
        intent="cart_action",
        tool_calls=[
            GraphToolCall("add_to_cart", {"dish_id": 12}, True, step_id="add_to_cart_0"),
            GraphToolCall("add_to_cart", {"dish_id": 35}, True, step_id="add_to_cart_1"),
        ],
    )
    state = {
        "messages": [HumanMessage(content="把川菜都加入购物车")],
        "current_plan": original_plan,
        "tool_results": [
            {"type": "add_to_cart", "step_id": "add_to_cart_0", "success": True, "message": "done", "data": {}},
        ],
        "session_id": "s1",
        "user_id": 1,
        "loaded_user_memories": [],
        "recent_action_ids": [],
        "iteration_count": 0,
        "recent_evidence": [],
        "last_recommendations": [],
    }

    mock_planner = MagicMock()
    mock_runtime = MagicMock()
    mock_runtime.planner = mock_planner

    with patch("service.agent_runtime.nodes.get_runtime", return_value=mock_runtime):
        result = plan_node(state)

    assert result["current_plan"] is original_plan
    mock_planner.plan.assert_not_called()


def test_plan_replan_when_all_calls_completed():
    """When all calls are completed, plan_node should call LLM for re-planning."""
    original_plan = AgentPlan(
        intent="recommendation",
        tool_calls=[
            GraphToolCall("recommend_dishes", {"query": "川菜"}, False, step_id="recommend_dishes_0"),
        ],
    )
    state = {
        "messages": [HumanMessage(content="推荐几个川菜然后加入购物车")],
        "current_plan": original_plan,
        "tool_results": [
            {"type": "recommend_dishes", "step_id": "recommend_dishes_0", "success": True, "message": "done", "data": {}},
        ],
        "session_id": "s1",
        "user_id": 1,
        "loaded_user_memories": [],
        "recent_action_ids": [],
        "iteration_count": 1,
        "recent_evidence": [{"source_type": "dish", "facts": {"dish_id": 12}}],
        "last_recommendations": [],
    }

    new_plan = AgentPlan(
        intent="cart_action",
        tool_calls=[GraphToolCall("add_to_cart", {"dish_id": 12}, True, step_id="add_to_cart_0")],
    )
    mock_planner = MagicMock()
    mock_planner.plan.return_value = new_plan
    mock_runtime = MagicMock()
    mock_runtime.planner = mock_planner

    with patch("service.agent_runtime.nodes.get_runtime", return_value=mock_runtime):
        result = plan_node(state)

    assert result["current_plan"] is new_plan
    mock_planner.plan.assert_called_once()


def test_replan_deconflicts_step_ids():
    """When re-planning, new step_ids must not collide with already-completed ones."""
    original_plan = AgentPlan(
        intent="recommendation",
        tool_calls=[
            GraphToolCall("recommend_dishes", {"query": "川菜"}, False, step_id="recommend_dishes_0"),
        ],
    )
    state = {
        "messages": [HumanMessage(content="推荐一个川菜，再推荐一个湘菜")],
        "current_plan": original_plan,
        "tool_results": [
            {"type": "recommend_dishes", "step_id": "recommend_dishes_0", "success": True, "message": "done", "data": {}},
        ],
        "session_id": "s1",
        "user_id": 1,
        "loaded_user_memories": [],
        "recent_action_ids": [],
        "iteration_count": 1,
        "recent_evidence": [{"source_type": "dish", "source_id": 12, "facts": {"dish_id": 12, "cuisine_type": "川菜"}}],
        "last_recommendations": [],
    }

    # LLM returns a new plan with step_id that WOULD collide (recommend_dishes_0)
    colliding_plan = AgentPlan(
        intent="recommendation",
        requires_rag=True,
        tool_calls=[
            GraphToolCall("recommend_dishes", {"query": "湘菜", "cuisine_types": ["湘菜"]}, False, step_id="recommend_dishes_0"),
        ],
    )
    mock_planner = MagicMock()
    mock_planner.plan.return_value = colliding_plan
    mock_runtime = MagicMock()
    mock_runtime.planner = mock_planner

    with patch("service.agent_runtime.nodes.get_runtime", return_value=mock_runtime):
        result = plan_node(state)

    returned_plan = result["current_plan"]
    # step_id should have been reassigned to avoid collision
    assert returned_plan.tool_calls[0].step_id != "recommend_dishes_0"
    assert returned_plan.tool_calls[0].step_id == "recommend_dishes_1"


def test_deconflict_assigns_step_id_when_empty():
    """_rule_plan creates GraphToolCall without step_id; _deconflict should assign one."""
    from service.agent_runtime.nodes import _deconflict_step_ids

    plan = AgentPlan(
        intent="cart_action",
        tool_calls=[
            GraphToolCall("add_to_cart", {"dish_id": 12}, True, step_id=""),
        ],
    )
    used_step_ids: set[str] = set()
    _deconflict_step_ids(plan, used_step_ids)
    assert plan.tool_calls[0].step_id == "add_to_cart_0"
    assert "add_to_cart_0" in used_step_ids


def test_build_human_input_injects_evidence():
    context = {
        "recent_evidence": [
            {
                "source_type": "dish",
                "facts": {"dish_id": 12, "dish_name": "宫保鸡丁", "merchant_name": "川味坊", "price": 28.0, "cuisine_type": "川菜", "flavor_profile": "麻辣"},
            },
        ],
        "tool_results": [],
    }
    result = LangGraphAgentPlanner._build_human_input("加入购物车", context)
    assert "## 本轮已检索到的结果" in result
    assert "宫保鸡丁" in result
    assert "dish_id=12" in result


def test_build_human_input_injects_tool_results():
    context = {
        "recent_evidence": [],
        "tool_results": [
            {"type": "add_to_cart", "step_id": "add_to_cart_0", "success": True, "message": "已将宫保鸡丁加入购物车"},
        ],
    }
    result = LangGraphAgentPlanner._build_human_input("还有吗", context)
    assert "## 本轮已完成的操作" in result
    assert "add_to_cart_0" in result
    assert "成功" in result


def test_build_human_input_no_injection_when_empty():
    context = {"recent_evidence": [], "tool_results": []}
    result = LangGraphAgentPlanner._build_human_input("推荐几个川菜", context)
    assert "## 本轮已检索到的结果" not in result
    assert "## 本轮已完成的操作" not in result
    assert "推荐几个川菜" in result


# ── RAG single-step execution tests ─────────────────────────────────

class StubEvidenceItem:
    """Mimics the return type of retriever.retrieve()."""
    def __init__(self, source_type, source_id, merchant_id, title, facts, why_matched, citation, score):
        self.source_type = source_type
        self.source_id = source_id
        self.merchant_id = merchant_id
        self.title = title
        self.facts = facts
        self.why_matched = why_matched
        self.citation = citation
        self.score = score


class FakeRetriever:
    """Returns fixed evidence; records calls for assertions."""
    def __init__(self, items):
        self.items = items
        self.calls = []

    def retrieve(self, query, agent_plan=None, memories=None, limit=5, **kwargs):
        self.calls.append({"query": query, "plan_filters": dict(agent_plan.filters) if agent_plan else {}})
        return self.items


def _make_rag_runtime(retriever):
    """Helper to create a mock runtime with a given retriever."""
    mock_runtime = MagicMock()
    mock_runtime.retriever = retriever
    return mock_runtime


def test_rag_node_batch_execution():
    """rag_node should batch-execute ALL pending RAG calls in one invocation."""
    plan = AgentPlan(
        intent="recommendation",
        normalized_query="川菜",
        requires_rag=True,
        tool_calls=[
            GraphToolCall("recommend_dishes", {"query": "川菜", "cuisine_types": ["川菜"]}, False, step_id="recommend_dishes_0"),
            GraphToolCall("recommend_dishes", {"query": "湘菜", "cuisine_types": ["湘菜"]}, False, step_id="recommend_dishes_1"),
        ],
    )
    sichuan_item = StubEvidenceItem(
        "dish", 12, 1, "宫保鸡丁",
        {"dish_id": 12, "dish_name": "宫保鸡丁", "cuisine_type": "川菜", "price": 28.0, "merchant_name": "川味坊", "flavor_profile": "麻辣"},
        ["川菜"], "经典川菜", 0.9,
    )
    retriever = FakeRetriever([sichuan_item])
    state = {
        "current_plan": plan,
        "tool_results": [],
        "recent_evidence": [],
        "loaded_user_memories": [],
        "messages": [HumanMessage(content="推荐一个川菜，再推荐一个湘菜")],
    }

    runtime = _make_rag_runtime(retriever)
    with patch("service.agent_runtime.nodes.get_runtime", return_value=runtime), \
         patch("service.config.get_config") as mock_cfg:
        mock_cfg.return_value.rag.output_limit_default = 5
        mock_cfg.return_value.rag.output_limit_max = 10
        result = rag_node(state)

    # Both calls should complete in one invocation (batch behavior)
    completed_step_ids = {r["step_id"] for r in result["tool_results"]}
    assert "recommend_dishes_0" in completed_step_ids
    assert "recommend_dishes_1" in completed_step_ids
    assert len(retriever.calls) == 2


def test_rag_node_batch_executes_all_pending_calls():
    """rag_node should batch-execute all 3 pending RAG calls in a single invocation."""
    plan = AgentPlan(
        intent="recommendation",
        normalized_query="推荐菜品",
        requires_rag=True,
        tool_calls=[
            GraphToolCall("recommend_dishes", {"query": "川菜", "cuisine_types": ["川菜"]}, False, step_id="recommend_dishes_0"),
            GraphToolCall("recommend_dishes", {"query": "素菜", "required_keywords": ["素"]}, False, step_id="recommend_dishes_1"),
            GraphToolCall("recommend_dishes", {"query": "甜品", "cuisine_types": ["甜品"]}, False, step_id="recommend_dishes_2"),
        ],
    )

    # Each call returns a different item (the retriever returns all 3 regardless,
    # but deduplication ensures each unique item appears once)
    items = [
        StubEvidenceItem("dish", 10, 1, "宫保鸡丁", {"dish_id": 10}, ["川菜"], "川菜", 0.9),
        StubEvidenceItem("dish", 20, 2, "清炒时蔬", {"dish_id": 20}, ["素菜"], "素菜", 0.8),
        StubEvidenceItem("dish", 30, 3, "芒果布丁", {"dish_id": 30}, ["甜品"], "甜品", 0.7),
    ]
    retriever = FakeRetriever(items)

    state = {
        "current_plan": plan,
        "tool_results": [],
        "recent_evidence": [],
        "loaded_user_memories": [],
        "messages": [HumanMessage(content="推荐一荤一素加甜品")],
    }

    runtime = _make_rag_runtime(retriever)
    with patch("service.agent_runtime.nodes.get_runtime", return_value=runtime), \
         patch("service.config.get_config") as mock_cfg:
        mock_cfg.return_value.rag.output_limit_default = 5
        mock_cfg.return_value.rag.output_limit_max = 10
        result = rag_node(state)

    # All 3 step_ids should be completed
    completed_step_ids = {r["step_id"] for r in result["tool_results"]}
    assert completed_step_ids == {"recommend_dishes_0", "recommend_dishes_1", "recommend_dishes_2"}

    # Retriever should have been called 3 times
    assert len(retriever.calls) == 3

    # Evidence should contain items from all 3 calls (deduplicated)
    evidence_ids = {e["source_id"] for e in result["recent_evidence"]}
    assert evidence_ids == {10, 20, 30}


def test_rag_node_batch_skips_already_completed_and_preserves_evidence():
    """rag_node should skip already-completed steps and preserve existing evidence."""
    plan = AgentPlan(
        intent="recommendation",
        normalized_query="推荐菜品",
        requires_rag=True,
        tool_calls=[
            GraphToolCall("recommend_dishes", {"query": "川菜"}, False, step_id="recommend_dishes_0"),
            GraphToolCall("recommend_dishes", {"query": "湘菜"}, False, step_id="recommend_dishes_1"),
        ],
    )

    hunan_item = StubEvidenceItem(
        "dish", 20, 2, "剁椒鱼头",
        {"dish_id": 20, "dish_name": "剁椒鱼头"},
        ["湘菜"], "湘菜", 0.85,
    )
    retriever = FakeRetriever([hunan_item])

    # Step 0 already completed; existing evidence from prior step
    existing_evidence = [
        {"source_type": "dish", "source_id": 12, "merchant_id": 1, "title": "宫保鸡丁",
         "facts": {"dish_id": 12}, "why_matched": ["川菜"], "citation": "川菜", "score": 0.9},
    ]
    state = {
        "current_plan": plan,
        "tool_results": [
            {"type": "recommend_dishes", "step_id": "recommend_dishes_0", "success": True, "message": "done", "data": {}},
        ],
        "recent_evidence": existing_evidence,
        "loaded_user_memories": [],
        "messages": [HumanMessage(content="推荐一个川菜，再推荐一个湘菜")],
    }

    runtime = _make_rag_runtime(retriever)
    with patch("service.agent_runtime.nodes.get_runtime", return_value=runtime), \
         patch("service.config.get_config") as mock_cfg:
        mock_cfg.return_value.rag.output_limit_default = 5
        mock_cfg.return_value.rag.output_limit_max = 10
        result = rag_node(state)

    # Only step 1 should be newly executed (step 0 was already done)
    completed_step_ids = {r["step_id"] for r in result["tool_results"]}
    assert "recommend_dishes_0" in completed_step_ids  # preserved from state
    assert "recommend_dishes_1" in completed_step_ids  # newly completed
    assert len(retriever.calls) == 1  # only 1 new call

    # Old evidence preserved alongside new evidence
    evidence_ids = {e["source_id"] for e in result["recent_evidence"]}
    assert 12 in evidence_ids  # old
    assert 20 in evidence_ids  # new


def test_rag_node_evidence_accumulation():
    """Second rag_node call should APPEND to evidence, not replace."""
    plan = AgentPlan(
        intent="recommendation",
        normalized_query="湘菜",
        requires_rag=True,
        tool_calls=[
            GraphToolCall("recommend_dishes", {"query": "川菜"}, False, step_id="recommend_dishes_0"),
            GraphToolCall("recommend_dishes", {"query": "湘菜"}, False, step_id="recommend_dishes_1"),
        ],
    )
    hunan_item = StubEvidenceItem(
        "dish", 20, 2, "剁椒鱼头",
        {"dish_id": 20, "dish_name": "剁椒鱼头", "cuisine_type": "湘菜", "price": 58.0, "merchant_name": "湘味馆", "flavor_profile": "辣"},
        ["湘菜"], "湘菜名菜", 0.85,
    )
    retriever = FakeRetriever([hunan_item])

    # Simulate: first RAG call already completed
    existing_evidence = [
        {"source_type": "dish", "source_id": 12, "facts": {"dish_id": 12, "dish_name": "宫保鸡丁", "cuisine_type": "川菜"}},
    ]
    state = {
        "current_plan": plan,
        "tool_results": [
            {"type": "recommend_dishes", "step_id": "recommend_dishes_0", "success": True, "message": "done", "data": {}},
        ],
        "recent_evidence": existing_evidence,
        "loaded_user_memories": [],
        "messages": [HumanMessage(content="推荐一个川菜，再推荐一个湘菜")],
    }

    runtime = _make_rag_runtime(retriever)
    with patch("service.agent_runtime.nodes.get_runtime", return_value=runtime), \
         patch("service.config.get_config") as mock_cfg:
        mock_cfg.return_value.rag.output_limit_default = 5
        mock_cfg.return_value.rag.output_limit_max = 10
        result = rag_node(state)

    # Evidence should have both items
    assert len(result["recent_evidence"]) == 2
    source_ids = {e["source_id"] for e in result["recent_evidence"]}
    assert 12 in source_ids  # old
    assert 20 in source_ids  # new
    # recommend_dishes_1 now completed
    step_ids = {r["step_id"] for r in result["tool_results"]}
    assert "recommend_dishes_0" in step_ids
    assert "recommend_dishes_1" in step_ids


def test_call_scoped_plan_no_filter_leakage():
    """_build_call_scoped_plan must NOT leak plan-level list filters to unrelated calls.

    Scenario: plan has required_keywords=["咖啡"] (merged from coffee call),
    but the sichuan call doesn't have required_keywords in its args.
    The scoped plan for sichuan should have required_keywords=[] (empty), NOT ["咖啡"].
    """
    from service.agent_runtime.nodes import _build_call_scoped_plan

    plan = AgentPlan(
        intent="recommendation",
        normalized_query="川菜和咖啡",
        requires_rag=True,
        filters={
            "cuisine_types": ["川菜"],       # merged from both calls
            "required_keywords": ["咖啡"],   # merged from coffee call only
            "flavor_preferences": [],
            "forbidden_keywords": [],
            "exclude_allergens": [],
            "source_types": [],
            "limit": 1,
            "sort_by": None,
            "price_preference": None,
            "budget_max": None,
        },
        tool_calls=[
            GraphToolCall("recommend_dishes", {"query": "川菜", "cuisine_types": ["川菜"], "limit": 1}, False, step_id="recommend_dishes_0"),
            GraphToolCall("recommend_dishes", {"query": "咖啡", "required_keywords": ["咖啡"], "limit": 1}, False, step_id="recommend_dishes_1"),
        ],
    )

    # Scoped plan for sichuan call — should NOT have required_keywords from coffee call
    sichuan_scoped = _build_call_scoped_plan(plan, plan.tool_calls[0].arguments)
    assert sichuan_scoped.filters.get("required_keywords") == [], \
        f"川菜 scoped plan leaked required_keywords: {sichuan_scoped.filters.get('required_keywords')}"
    assert sichuan_scoped.filters.get("cuisine_types") == ["川菜"]
    assert sichuan_scoped.normalized_query == "川菜"

    # Scoped plan for coffee call — should have required_keywords=["咖啡"]
    coffee_scoped = _build_call_scoped_plan(plan, plan.tool_calls[1].arguments)
    assert coffee_scoped.filters.get("required_keywords") == ["咖啡"]
    assert coffee_scoped.filters.get("cuisine_types") == [], \
        f"咖啡 scoped plan leaked cuisine_types: {coffee_scoped.filters.get('cuisine_types')}"
    assert coffee_scoped.normalized_query == "咖啡"


def test_evidence_bridging_removed_for_add_to_cart():
    """Evidence bridging removed: missing items+dish_id should fail, not bridge from evidence."""
    plan = AgentPlan(
        intent="cart_action",
        tool_calls=[
            GraphToolCall("add_to_cart", {}, True, step_id="add_to_cart_0"),  # no dish_id!
        ],
    )
    state = {
        "user_id": 1,
        "session_id": "s1",
        "tool_results": [],
        "recent_evidence": [
            {"source_type": "dish", "source_id": 12, "facts": {"dish_id": 12, "dish_name": "宫保鸡丁"}},
            {"source_type": "dish", "source_id": 35, "facts": {"dish_id": 35, "dish_name": "水煮鱼"}},
        ],
    }
    executor = LocalActionExecutor(session=None)

    result = executor.execute_action(plan, state)

    assert result["success"] is False
    assert "items" in result["message"]


def test_unfulfilled_action_intent_triggers_replan():
    """User said '加入购物车' but no add_to_cart completed → re-plan."""
    plan = AgentPlan(
        intent="recommendation",
        tool_calls=[
            GraphToolCall("recommend_dishes", {"query": "川菜"}, False, step_id="recommend_dishes_0"),
        ],
    )
    state = {
        "messages": [HumanMessage(content="推荐几个川菜，然后加入购物车")],
        "current_plan": plan,
        "tool_results": [
            {"type": "recommend_dishes", "step_id": "recommend_dishes_0", "success": True, "message": "done", "data": {}},
        ],
        "recent_evidence": [
            {"source_type": "dish", "source_id": 12, "facts": {"dish_id": 12}},
        ],
        "iteration_count": 0,
        "max_iterations": 5,
        "metrics": {},
    }
    result = evaluate_node(state)
    assert result["_next"] == "plan"


def test_fulfilled_action_intent_goes_to_respond():
    """User said '加入购物车' and add_to_cart succeeded → respond."""
    plan = AgentPlan(
        intent="cart_action",
        tool_calls=[
            GraphToolCall("add_to_cart", {"dish_id": 12}, True, step_id="add_to_cart_0"),
        ],
    )
    state = {
        "messages": [HumanMessage(content="推荐几个川菜，然后加入购物车")],
        "current_plan": plan,
        "tool_results": [
            {"type": "recommend_dishes", "step_id": "recommend_dishes_0", "success": True, "message": "done", "data": {}},
            {"type": "add_to_cart", "step_id": "add_to_cart_0", "success": True, "message": "done", "data": {}},
        ],
        "recent_evidence": [
            {"source_type": "dish", "source_id": 12, "facts": {"dish_id": 12}},
        ],
        "iteration_count": 1,
        "max_iterations": 5,
        "metrics": {},
    }
    result = evaluate_node(state)
    assert result["_next"] == "respond"


def test_unfulfilled_retrieval_intent_multi_cuisine():
    """User asked for 川菜+湘菜, but evidence only covers 川菜 → re-plan."""
    plan = AgentPlan(
        intent="recommendation",
        tool_calls=[
            GraphToolCall("recommend_dishes", {"query": "川菜"}, False, step_id="recommend_dishes_0"),
        ],
    )
    state = {
        "messages": [HumanMessage(content="推荐一个川菜，再推荐一个湘菜")],
        "current_plan": plan,
        "tool_results": [
            {"type": "recommend_dishes", "step_id": "recommend_dishes_0", "success": True, "message": "done", "data": {}},
        ],
        "recent_evidence": [
            {"source_type": "dish", "source_id": 12, "facts": {"dish_id": 12, "cuisine_type": "川菜"}},
        ],
        "iteration_count": 0,
        "max_iterations": 5,
        "metrics": {},
    }
    result = evaluate_node(state)
    assert result["_next"] == "plan"


def test_evaluate_node_grace_for_pending_action():
    """When max_iterations reached but pending action exists, should continue to plan."""
    plan = AgentPlan(
        intent="cart_action",
        tool_calls=[
            GraphToolCall("recommend_dishes", {"query": "川菜"}, False, step_id="recommend_dishes_0"),
            GraphToolCall("add_to_cart", {"items": [{"dish_id": 12, "quantity": 1}]}, True, step_id="add_to_cart_0"),
        ],
    )
    state = {
        "messages": [HumanMessage(content="推荐川菜然后加购物车")],
        "current_plan": plan,
        "tool_results": [
            {"type": "recommend_dishes", "step_id": "recommend_dishes_0", "success": True, "message": "done", "data": {}},
        ],
        "recent_evidence": [{"source_type": "dish", "source_id": 12, "facts": {"dish_id": 12}}],
        "iteration_count": 4,  # Will become 5, equal to max_iterations
        "max_iterations": 5,
        "metrics": {},
    }
    result = evaluate_node(state)
    # Should allow action to proceed, not force respond
    assert result["_next"] == "plan"


def test_evaluate_node_grace_expires():
    """Grace iterations should be limited — eventually must respond."""
    plan = AgentPlan(
        intent="cart_action",
        tool_calls=[
            GraphToolCall("add_to_cart", {"items": [{"dish_id": 12, "quantity": 1}]}, True, step_id="add_to_cart_0"),
        ],
    )
    state = {
        "messages": [HumanMessage(content="加购物车")],
        "current_plan": plan,
        "tool_results": [],
        "recent_evidence": [],
        "iteration_count": 6,  # Will become 7, max_iter=5, grace=2 → 5+2=7 → exhausted
        "max_iterations": 5,
        "metrics": {},
    }
    result = evaluate_node(state)
    assert result["_next"] == "respond"


def test_respond_merges_action_results_with_evidence():
    """When both evidence and action tool_results exist, response should mention both."""
    plan = AgentPlan(
        intent="cart_action",
        tool_calls=[
            GraphToolCall("recommend_dishes", {"query": "川菜"}, False, step_id="recommend_dishes_0"),
            GraphToolCall("add_to_cart", {"dish_id": 12}, True, step_id="add_to_cart_0"),
        ],
    )
    state = {
        "messages": [HumanMessage(content="推荐几个川菜然后加入购物车")],
        "current_plan": plan,
        "recent_evidence": [
            {
                "source_type": "dish", "source_id": 12, "merchant_id": 1,
                "title": "宫保鸡丁",
                "facts": {"dish_id": 12, "dish_name": "宫保鸡丁", "price": 28.0, "merchant_name": "川味坊"},
                "why_matched": ["川菜"], "citation": "经典川菜", "score": 0.9,
            },
        ],
        "tool_results": [
            {"type": "recommend_dishes", "step_id": "recommend_dishes_0", "success": True, "message": "检索到 1 条结果", "data": {}},
            {"type": "add_to_cart", "step_id": "add_to_cart_0", "success": True, "message": "已将宫保鸡丁加入购物车", "data": {}},
        ],
        "session_id": "s1",
        "user_id": 1,
        "loaded_user_memories": [],
        "recent_action_ids": ["act_1"],
        "iteration_count": 2,
        "max_iterations": 5,
        "metrics": {},
        "guardrail_blocked": False,
    }

    runtime = MagicMock()
    runtime.use_llm_response = False  # Use template path for deterministic test

    with patch("service.agent_runtime.nodes.get_runtime", return_value=runtime):
        result = respond_node(state)

    message = result["response_payload"]["message"]
    # Should contain both recommendation text AND action confirmation
    assert "宫保鸡丁" in message
    assert "已将宫保鸡丁加入购物车" in message
    assert result["response_payload"]["response_type"] == "action_completed"


def test_respond_node_passes_response_hint_to_llm():
    """respond_node should pass plan.response_hint to _generate_llm_response."""
    plan = AgentPlan(
        intent="recommendation",
        response_hint="推荐辣椒炒肉作为荤菜，总价约50元",
    )
    state = {
        "messages": [HumanMessage(content="推荐一个荤菜")],
        "current_plan": plan,
        "recent_evidence": [
            {"source_type": "dish", "source_id": 12, "facts": {"dish_id": 12, "dish_name": "辣椒炒肉", "merchant_name": "湘味馆", "price": 29.0, "cuisine_type": "湘菜", "flavor_profile": "辣"}, "why_matched": ["湘菜"], "citation": "", "score": 0.9},
        ],
        "tool_results": [],
        "session_id": "s1",
        "metrics": {},
    }

    captured_kwargs = {}

    def fake_generate(user_message, response_type, evidence, conversation_history="", tool_results=None, response_hint=""):
        captured_kwargs["response_hint"] = response_hint
        return "测试回复"

    mock_runtime = MagicMock()
    mock_runtime.use_llm_response = True

    with patch("service.agent_runtime.nodes.get_runtime", return_value=mock_runtime), \
         patch("service.agent_runtime.nodes._generate_llm_response", side_effect=fake_generate), \
         patch("service.agent_runtime.nodes._external_response_type", return_value="recommendation"), \
         patch("service.config.get_config") as mock_cfg:
        mock_cfg.return_value.guardrails.enable_output_guardrail = False
        respond_node(state)

    assert captured_kwargs["response_hint"] == "推荐辣椒炒肉作为荤菜，总价约50元"


def test_rag_node_batch_isolates_failures():
    """If one RAG call fails, others should still succeed."""
    plan = AgentPlan(
        intent="recommendation",
        normalized_query="川菜和甜品",
        requires_rag=True,
        tool_calls=[
            GraphToolCall("recommend_dishes", {"query": "川菜"}, False, step_id="recommend_dishes_0"),
            GraphToolCall("recommend_dishes", {"query": "甜品"}, False, step_id="recommend_dishes_1"),
        ],
    )

    sichuan_item = StubEvidenceItem(
        "dish", 12, 1, "宫保鸡丁",
        {"dish_id": 12, "dish_name": "宫保鸡丁", "cuisine_type": "川菜"},
        ["川菜"], "川菜", 0.9,
    )

    call_count = {"n": 0}
    def flaky_retrieve(query, agent_plan=None, memories=None, limit=5, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 2:
            raise RuntimeError("Pinecone timeout")
        return [sichuan_item]

    mock_runtime = MagicMock()
    mock_runtime.retriever = MagicMock()
    mock_runtime.retriever.retrieve = flaky_retrieve

    state = {
        "current_plan": plan,
        "tool_results": [],
        "recent_evidence": [],
        "loaded_user_memories": [],
        "messages": [HumanMessage(content="推荐川菜和甜品")],
    }

    with patch("service.agent_runtime.nodes.get_runtime", return_value=mock_runtime), \
         patch("service.config.get_config") as mock_cfg:
        mock_cfg.return_value.rag.output_limit_default = 5
        mock_cfg.return_value.rag.output_limit_max = 10
        result = rag_node(state)

    # One call succeeded, one failed
    successful = [r for r in result["tool_results"] if r["success"]]
    failed = [r for r in result["tool_results"] if not r["success"]]
    assert len(successful) == 1
    assert len(failed) == 1
    assert "检索失败" in failed[0]["message"]
    # Evidence from the successful call should be present
    assert len(result["recent_evidence"]) > 0


def test_compound_request_batch_rag_and_batch_cart():
    """Full flow: compound request should batch RAG → replan → batch add_to_cart."""
    # Phase 1: Initial plan with 2 RAG calls
    initial_plan = AgentPlan(
        intent="cart_action",
        normalized_query="川菜荤菜和甜品",
        requires_rag=True,
        tool_calls=[
            GraphToolCall("recommend_dishes", {"query": "川菜荤菜", "cuisine_types": ["川菜"]}, False, step_id="recommend_dishes_0"),
            GraphToolCall("recommend_dishes", {"query": "甜品", "required_keywords": ["甜品"]}, False, step_id="recommend_dishes_1"),
        ],
    )

    state_before_rag = {
        "messages": [HumanMessage(content="推荐一个川菜荤菜和一个甜品，加入购物车")],
        "current_plan": initial_plan,
        "tool_results": [],
        "recent_evidence": [],
        "loaded_user_memories": [],
        "iteration_count": 0,
        "max_iterations": 5,
        "metrics": {},
        "session_id": "s1",
        "user_id": 1,
    }

    # route_after_plan should send to rag (first remaining call is recommend_dishes)
    assert route_after_plan(state_before_rag) == "rag"

    # Simulate batch RAG completion (both calls done in one pass)
    state_after_rag = {
        **state_before_rag,
        "tool_results": [
            {"type": "recommend_dishes", "step_id": "recommend_dishes_0", "success": True, "message": "3 results", "data": {}},
            {"type": "recommend_dishes", "step_id": "recommend_dishes_1", "success": True, "message": "3 results", "data": {}},
        ],
        "recent_evidence": [
            {"source_type": "dish", "source_id": 100, "facts": {"dish_id": 100, "cuisine_type": "川菜"}},
            {"source_type": "dish", "source_id": 200, "facts": {"dish_id": 200, "cuisine_type": "甜品"}},
        ],
        "iteration_count": 0,
    }

    # evaluate should detect unfulfilled action intent → plan
    eval_result = evaluate_node(state_after_rag)
    assert eval_result["_next"] == "plan"

    # Phase 2: Replan produces batch add_to_cart with items list
    cart_plan = AgentPlan(
        intent="cart_action",
        requires_rag=False,
        tool_calls=[
            GraphToolCall("add_to_cart", {
                "items": [{"dish_id": 100, "quantity": 1}, {"dish_id": 200, "quantity": 1}]
            }, True, step_id="add_to_cart_0"),
        ],
    )

    state_after_replan = {**state_after_rag, "current_plan": cart_plan}

    # route_after_plan should send to action (first remaining call is add_to_cart)
    assert route_after_plan(state_after_replan) == "action"

    # Phase 3: After action completes
    state_after_action = {
        **state_after_replan,
        "tool_results": state_after_rag["tool_results"] + [
            {"type": "add_to_cart", "step_id": "add_to_cart_0", "success": True, "message": "已将 2 道菜品加入购物车", "data": {}},
        ],
        "iteration_count": 2,
    }

    # evaluate should see all steps done → respond
    eval_result2 = evaluate_node(state_after_action)
    assert eval_result2["_next"] == "respond"


# ── Integration Test Helpers ──────────────────────────────────────────

class CompoundPlanner:
    """Planner that simulates LLM behavior for compound task testing.

    First call: returns RAG plan (recommendation).
    Subsequent calls: checks context for evidence/tool_results and returns
    appropriate continuation plan (action).
    """
    def __init__(self, continuation_plan_fn=None):
        self.call_count = 0
        self._continuation_plan_fn = continuation_plan_fn

    def plan(self, message, context):
        self.call_count += 1
        evidence = context.get("recent_evidence", [])
        tool_results = context.get("tool_results", [])

        if self.call_count == 1:
            # First call: always recommend
            return AgentPlan(
                intent="recommendation",
                normalized_query="川菜",
                requires_rag=True,
                tool_calls=[
                    GraphToolCall("recommend_dishes", {"query": "川菜", "cuisine_types": ["川菜"]}, False, step_id="recommend_dishes_0"),
                ],
            )

        # Subsequent calls: use continuation function
        if self._continuation_plan_fn:
            return self._continuation_plan_fn(self.call_count, evidence, tool_results, message)

        return AgentPlan(intent="recommendation")


class CompoundRetriever:
    """Retriever that returns different results based on query/filters."""
    def __init__(self, items_by_cuisine=None):
        self._items = items_by_cuisine or {}
        self.calls = []

    def retrieve(self, query, agent_plan=None, memories=None, limit=5, **kwargs):
        self.calls.append(query)
        cuisine_types = (agent_plan.filters or {}).get("cuisine_types", []) if agent_plan else []
        for cuisine in cuisine_types:
            if cuisine in self._items:
                return self._items[cuisine]
        # Default: return all items from first cuisine
        if self._items:
            return list(self._items.values())[0]
        return []


class CompoundExecutor:
    """Action executor that tracks calls."""
    def __init__(self):
        self.executed = []

    def execute_action(self, plan, state):
        completed_step_ids = {r.get("step_id") or r.get("type", "") for r in state.get("tool_results", [])}
        call = next(
            (c for c in plan.tool_calls
             if c.tool_name in ACTION_TOOL_NAMES and c.step_id not in completed_step_ids),
            None,
        )
        if call is None:
            return {"success": False, "message": "无操作", "undo_available": False}

        dish_id = call.arguments.get("dish_id")
        # Evidence bridging fallback
        if dish_id is None:
            evidence = state.get("recent_evidence", [])
            dish_ev = [e for e in evidence if e.get("source_type") == "dish"]
            if dish_ev:
                dish_id = dish_ev[0].get("facts", {}).get("dish_id")

        self.executed.append({"tool": call.tool_name, "step_id": call.step_id, "dish_id": dish_id})
        return {
            "success": True,
            "action_id": f"act_{len(self.executed)}",
            "message": f"已将菜品(dish_id={dish_id})加入购物车",
            "undo_available": True,
        }

    def undo_last(self, state):
        return {"success": False, "message": "无操作"}


def _make_evidence_items(items_data):
    """Create StubEvidenceItem list from simple dicts."""
    return [
        StubEvidenceItem(
            source_type="dish",
            source_id=d["dish_id"],
            merchant_id=d.get("merchant_id", 1),
            title=d["dish_name"],
            facts=d,
            why_matched=[d.get("cuisine_type", "")],
            citation="test",
            score=0.9,
        )
        for d in items_data
    ]


def test_integration_recommend_then_add_to_cart():
    """E2E: '推荐几个川菜，然后加入购物车' → RAG → evaluate → plan → action → respond."""
    sichuan_dishes = _make_evidence_items([
        {"dish_id": 12, "dish_name": "宫保鸡丁", "price": 28.0, "merchant_name": "川味坊", "cuisine_type": "川菜", "flavor_profile": "麻辣"},
    ])

    def continuation(call_count, evidence, tool_results, message):
        if evidence and not any(r.get("type") in ACTION_TOOL_NAMES for r in tool_results):
            dish_id = evidence[0].get("facts", {}).get("dish_id", 12)
            return AgentPlan(
                intent="cart_action",
                requires_rag=False,
                tool_calls=[
                    GraphToolCall("add_to_cart", {"dish_id": dish_id, "quantity": 1}, True, step_id="add_to_cart_0"),
                ],
            )
        return AgentPlan(intent="cart_action")

    planner = CompoundPlanner(continuation_plan_fn=continuation)
    retriever = CompoundRetriever({"川菜": sichuan_dishes})
    executor = CompoundExecutor()

    graph = build_agent_graph()
    runtime = AgentRuntimeContext(
        planner=planner, retriever=retriever,
        action_executor=executor, use_llm_response=False,
    )

    result = graph.invoke({
        "messages": [HumanMessage(content="推荐几个川菜，然后加入购物车")],
        "session_id": "test_compound_1",
        "user_id": 1,
        "loaded_user_memories": [],
        "recent_evidence": [],
        "recent_action_ids": [],
        "tool_results": [],
        "iteration_count": 0,
        "max_iterations": 5,
    }, config={"configurable": {"thread_id": "t1", "runtime": runtime}})

    # Verify: evidence exists (RAG completed)
    assert result.get("recent_evidence")
    # Verify: action executed
    assert len(executor.executed) == 1
    assert executor.executed[0]["dish_id"] == 12
    # Verify: response mentions both recommendation and action
    message = result["response_payload"]["message"]
    assert "宫保鸡丁" in message
    assert "已将菜品" in message  # action confirmation present


def test_integration_recommend_then_add_all_to_cart():
    """E2E: '推荐几个川菜，然后都加入购物车' → RAG → 3× action → respond."""
    sichuan_dishes = _make_evidence_items([
        {"dish_id": 12, "dish_name": "宫保鸡丁", "price": 28.0, "merchant_name": "川味坊", "cuisine_type": "川菜", "flavor_profile": "麻辣"},
        {"dish_id": 35, "dish_name": "水煮鱼", "price": 45.0, "merchant_name": "川味坊", "cuisine_type": "川菜", "flavor_profile": "辣"},
        {"dish_id": 7, "dish_name": "干煸四季豆", "price": 18.0, "merchant_name": "川味坊", "cuisine_type": "川菜", "flavor_profile": "咸"},
    ])

    def continuation(call_count, evidence, tool_results, message):
        if evidence and not any(r.get("type") in ACTION_TOOL_NAMES for r in tool_results):
            # Generate one add_to_cart per dish
            calls = []
            for idx, e in enumerate(evidence):
                if e.get("source_type") == "dish":
                    did = e.get("facts", {}).get("dish_id")
                    calls.append(GraphToolCall("add_to_cart", {"dish_id": did, "quantity": 1}, True, step_id=f"add_to_cart_{idx}"))
            return AgentPlan(intent="cart_action", requires_rag=False, tool_calls=calls)
        return AgentPlan(intent="cart_action")

    planner = CompoundPlanner(continuation_plan_fn=continuation)
    retriever = CompoundRetriever({"川菜": sichuan_dishes})
    executor = CompoundExecutor()

    graph = build_agent_graph()
    runtime = AgentRuntimeContext(
        planner=planner, retriever=retriever,
        action_executor=executor, use_llm_response=False,
    )

    result = graph.invoke({
        "messages": [HumanMessage(content="推荐几个川菜，然后都加入购物车")],
        "session_id": "test_compound_2",
        "user_id": 1,
        "loaded_user_memories": [],
        "recent_evidence": [],
        "recent_action_ids": [],
        "tool_results": [],
        "iteration_count": 0,
        "max_iterations": 10,  # Allow enough iterations for 3 actions
    }, config={"configurable": {"thread_id": "t2", "runtime": runtime}})

    # All 3 dishes should have been added to cart
    assert len(executor.executed) == 3
    executed_dish_ids = {e["dish_id"] for e in executor.executed}
    assert executed_dish_ids == {12, 35, 7}
    # Each should have unique step_id
    executed_step_ids = {e["step_id"] for e in executor.executed}
    assert len(executed_step_ids) == 3


def test_integration_multi_cuisine_rag():
    """E2E: '推荐一个川菜，再推荐一个湘菜' → RAG(川菜) → RAG(湘菜) → respond."""
    sichuan = _make_evidence_items([
        {"dish_id": 12, "dish_name": "宫保鸡丁", "price": 28.0, "merchant_name": "川味坊", "cuisine_type": "川菜", "flavor_profile": "麻辣"},
    ])
    hunan = _make_evidence_items([
        {"dish_id": 20, "dish_name": "剁椒鱼头", "price": 58.0, "merchant_name": "湘味馆", "cuisine_type": "湘菜", "flavor_profile": "辣"},
    ])

    class MultiCuisinePlanner:
        def __init__(self):
            self.call_count = 0

        def plan(self, message, context):
            self.call_count += 1
            if self.call_count == 1:
                # Path A: LLM decomposes into two RAG calls upfront
                return AgentPlan(
                    intent="recommendation",
                    normalized_query="川菜和湘菜",
                    requires_rag=True,
                    tool_calls=[
                        GraphToolCall("recommend_dishes", {"query": "川菜", "cuisine_types": ["川菜"], "limit": 1}, False, step_id="recommend_dishes_0"),
                        GraphToolCall("recommend_dishes", {"query": "湘菜", "cuisine_types": ["湘菜"], "limit": 1}, False, step_id="recommend_dishes_1"),
                    ],
                )
            return AgentPlan(intent="recommendation")

    planner = MultiCuisinePlanner()
    retriever = CompoundRetriever({"川菜": sichuan, "湘菜": hunan})
    executor = CompoundExecutor()

    graph = build_agent_graph()
    runtime = AgentRuntimeContext(
        planner=planner, retriever=retriever,
        action_executor=executor, use_llm_response=False,
    )

    result = graph.invoke({
        "messages": [HumanMessage(content="推荐一个川菜，再推荐一个湘菜")],
        "session_id": "test_compound_3",
        "user_id": 1,
        "loaded_user_memories": [],
        "recent_evidence": [],
        "recent_action_ids": [],
        "tool_results": [],
        "iteration_count": 0,
        "max_iterations": 5,
    }, config={"configurable": {"thread_id": "t3", "runtime": runtime}})

    # Evidence should contain both cuisines
    evidence = result.get("recent_evidence", [])
    cuisine_types = {e.get("facts", {}).get("cuisine_type") for e in evidence}
    assert "川菜" in cuisine_types
    assert "湘菜" in cuisine_types
    # Two retrieval calls made
    assert len(retriever.calls) == 2
    # Response mentions both dishes
    message = result["response_payload"]["message"]
    assert "宫保鸡丁" in message
    assert "剁椒鱼头" in message


def test_integration_multi_cuisine_path_b_replan():
    """E2E Path B: LLM only generates one RAG call, evaluate detects missing cuisine → re-plan → second RAG."""
    sichuan = _make_evidence_items([
        {"dish_id": 12, "dish_name": "宫保鸡丁", "price": 28.0, "merchant_name": "川味坊", "cuisine_type": "川菜", "flavor_profile": "麻辣"},
    ])
    hunan = _make_evidence_items([
        {"dish_id": 20, "dish_name": "剁椒鱼头", "price": 58.0, "merchant_name": "湘味馆", "cuisine_type": "湘菜", "flavor_profile": "辣"},
    ])

    class PathBPlanner:
        """First call: only Sichuan RAG. Second call (after evaluate triggers re-plan): Hunan RAG."""
        def __init__(self):
            self.call_count = 0

        def plan(self, message, context):
            self.call_count += 1
            if self.call_count == 1:
                # Only generate ONE RAG call — intentionally incomplete
                return AgentPlan(
                    intent="recommendation",
                    normalized_query="川菜",
                    requires_rag=True,
                    tool_calls=[
                        GraphToolCall("recommend_dishes", {"query": "川菜", "cuisine_types": ["川菜"], "limit": 1}, False, step_id="recommend_dishes_0"),
                    ],
                )
            # Second call: evaluate detected missing 湘菜 → generate second RAG call
            return AgentPlan(
                intent="recommendation",
                normalized_query="湘菜",
                requires_rag=True,
                tool_calls=[
                    GraphToolCall("recommend_dishes", {"query": "湘菜", "cuisine_types": ["湘菜"], "limit": 1}, False, step_id="recommend_dishes_1"),
                ],
            )

    planner = PathBPlanner()
    retriever = CompoundRetriever({"川菜": sichuan, "湘菜": hunan})
    executor = CompoundExecutor()

    graph = build_agent_graph()
    runtime = AgentRuntimeContext(
        planner=planner, retriever=retriever,
        action_executor=executor, use_llm_response=False,
    )

    result = graph.invoke({
        "messages": [HumanMessage(content="推荐一个川菜，再推荐一个湘菜")],
        "session_id": "test_compound_4",
        "user_id": 1,
        "loaded_user_memories": [],
        "recent_evidence": [],
        "recent_action_ids": [],
        "tool_results": [],
        "iteration_count": 0,
        "max_iterations": 5,
    }, config={"configurable": {"thread_id": "t4", "runtime": runtime}})

    # Planner should have been called twice (initial + continuation after evaluate)
    assert planner.call_count == 2
    # Evidence should contain both cuisines
    evidence = result.get("recent_evidence", [])
    cuisine_types = {e.get("facts", {}).get("cuisine_type") for e in evidence}
    assert "川菜" in cuisine_types
    assert "湘菜" in cuisine_types
    # Two retrieval calls made
    assert len(retriever.calls) == 2
    # Response mentions both dishes
    message = result["response_payload"]["message"]
    assert "宫保鸡丁" in message
    assert "剁椒鱼头" in message


# ── Codex review round 2 — Issue 5: _successful_step_ids ──────────────


def test_successful_step_ids_excludes_retryable_failures():
    """Only retryable failures should remain pending for retry."""
    state = {
        "tool_results": [
            {"step_id": "rag_0", "success": True, "type": "recommend_dishes"},
            {"step_id": "rag_1", "success": False, "retryable": True, "type": "recommend_dishes"},
            {"step_id": "add_to_cart_0", "success": True, "type": "add_to_cart"},
            {"step_id": "act_bad", "success": False, "type": "add_to_cart"},  # no retryable → done
        ]
    }
    ids = _successful_step_ids(state)
    assert "rag_0" in ids
    assert "add_to_cart_0" in ids
    assert "act_bad" in ids, "Non-retryable failure should be treated as done"
    assert "rag_1" not in ids, "Retryable failure should remain pending"


def test_successful_step_ids_non_retryable_failure_is_done():
    """Deterministic failure (retryable=False or missing) counts as completed."""
    state = {
        "tool_results": [
            {"step_id": "act_0", "success": False, "retryable": False, "type": "add_to_cart"},
        ]
    }
    ids = _successful_step_ids(state)
    assert "act_0" in ids


def test_successful_step_ids_defaults_true_when_missing():
    """Legacy tool_results without 'success' key should default to completed."""
    state = {
        "tool_results": [
            {"step_id": "rag_0", "type": "recommend_dishes"},
        ]
    }
    ids = _successful_step_ids(state)
    assert "rag_0" in ids


def test_evaluate_node_retries_retryable_rag_step():
    """evaluate_node should route back to plan when a retryable RAG step failed."""
    plan = AgentPlan(
        intent="recommendation",
        tool_calls=[
            GraphToolCall(tool_name="recommend_dishes", step_id="rag_0"),
            GraphToolCall(tool_name="recommend_dishes", step_id="rag_1"),
        ],
        requires_rag=True,
    )
    state = {
        "current_plan": plan,
        "iteration_count": 1,
        "max_iterations": 5,
        "tool_results": [
            {"step_id": "rag_0", "success": True, "type": "recommend_dishes"},
            {"step_id": "rag_1", "success": False, "retryable": True, "type": "recommend_dishes"},
        ],
        "recent_evidence": [{"source_type": "dish", "source_id": 1}],
        "messages": [HumanMessage(content="推荐一些菜")],
    }
    result = evaluate_node(state)
    assert result["_next"] == "plan", "Retryable RAG failure should trigger re-plan"


def test_evaluate_node_does_not_retry_deterministic_failure():
    """Deterministic action failure (no retryable flag) should go to respond, not loop."""
    plan = AgentPlan(
        intent="cart_action",
        tool_calls=[
            GraphToolCall(tool_name="add_to_cart", step_id="act_0", writes_database=True),
        ],
    )
    state = {
        "current_plan": plan,
        "iteration_count": 1,
        "max_iterations": 5,
        "tool_results": [
            {"step_id": "act_0", "success": False, "type": "add_to_cart"},  # no retryable → done
        ],
        "recent_evidence": [],
        "messages": [HumanMessage(content="加入购物车")],
    }
    result = evaluate_node(state)
    assert result["_next"] == "respond", "Non-retryable failure should go to respond"


def test_route_after_plan_does_not_retry_non_retryable_action():
    """Non-retryable action failure should route to respond, not action."""
    plan = AgentPlan(
        intent="cart_action",
        tool_calls=[
            GraphToolCall(tool_name="add_to_cart", step_id="act_0", writes_database=True),
        ],
    )
    state = {
        "current_plan": plan,
        "tool_results": [
            {"step_id": "act_0", "success": False, "type": "add_to_cart"},
        ],
        "recent_evidence": [],
    }
    route = route_after_plan(state)
    assert route == "respond", "Non-retryable failure should NOT be retried"


# ── Codex review round 2 — Issue 2: undo add_to_cart ──────────────────


def test_undo_last_add_to_cart_restores_quantities():
    """undo_last should restore pre-add quantities from before_snapshot."""
    executor = LocalActionExecutor(session=None)

    mock_journal = MagicMock()
    mock_journal.find_last_undoable.return_value = {
        "action_type": "add_to_cart",
        "action_id": "act_123",
        "before_snapshot": {"items": [
            {"dish_id": 11, "quantity": 2},   # existed before with qty=2
            {"dish_id": 22, "quantity": 0},   # new item (qty=0 → remove)
        ]},
        "after_snapshot": {"items": [
            {"dish_id": 11, "quantity": 1},
            {"dish_id": 22, "quantity": 1},
        ]},
    }
    mock_journal.mark_undone.return_value = None

    mock_cart_service = MagicMock()

    state = {"user_id": 1}

    with patch("service.action_journal_service.ActionJournalService", return_value=mock_journal), \
         patch("service.cart_service.CartService", return_value=mock_cart_service):
        result = executor.undo_last(state)

    assert result["success"] is True
    assert "2 道菜品" in result["message"]
    # dish_id=11 should be restored to qty=2 via update_item
    mock_cart_service.update_item.assert_called_once_with(1, 11, 2)
    # dish_id=22 was new, should be removed
    mock_cart_service.remove_item.assert_called_once_with(1, 22)
    mock_journal.mark_undone.assert_called_once_with("act_123")


def test_undo_last_add_to_cart_partial_failure_does_not_mark_undone():
    """If any item fails to restore, undo should fail and NOT mark undone."""
    executor = LocalActionExecutor(session=None)

    mock_journal = MagicMock()
    mock_journal.find_last_undoable.return_value = {
        "action_type": "add_to_cart",
        "action_id": "act_456",
        "before_snapshot": {"items": [
            {"dish_id": 11, "quantity": 0},
            {"dish_id": 22, "quantity": 0},
        ]},
        "after_snapshot": {"items": [
            {"dish_id": 11, "quantity": 1},
            {"dish_id": 22, "quantity": 1},
        ]},
    }
    mock_journal.mark_undone.return_value = None

    mock_cart_service = MagicMock()
    # First remove succeeds, second fails
    mock_cart_service.remove_item.side_effect = [None, ValueError("already removed")]

    state = {"user_id": 1}

    with patch("service.action_journal_service.ActionJournalService", return_value=mock_journal), \
         patch("service.cart_service.CartService", return_value=mock_cart_service):
        result = executor.undo_last(state)

    assert result["success"] is False
    assert "失败" in result["message"]
    mock_journal.mark_undone.assert_not_called()


# ── Codex review round 2+3 — cart_tool batch atomicity ────────────────


def test_add_to_cart_tool_rollback_restores_existing_quantity():
    """Rollback should restore pre-add quantity for existing items, not delete."""
    from service.tools.cart_tool import add_to_cart_tool

    mock_service = MagicMock()
    # dish_id=11 existed with qty=2 → add 1 → post_qty=3
    mock_service.add_item.side_effect = [
        {"dish_id": 11, "quantity": 3},
        ValueError("dish not found"),
    ]
    mock_service.update_item.return_value = {"success": True}

    result = add_to_cart_tool(
        user_id=1,
        items=[
            {"dish_id": 11, "quantity": 1},
            {"dish_id": 999, "quantity": 1},
        ],
        _cart_service=mock_service,
    )

    assert result["success"] is False
    assert "999" in result["message"]
    # Pre-add qty was 3-1=2 → restore via update_item, not remove
    mock_service.update_item.assert_called_once_with(1, 11, 2)
    mock_service.remove_item.assert_not_called()
    assert result["rolled_back"] == [11]


def test_add_to_cart_tool_rollback_removes_new_item():
    """Rollback should remove items that didn't exist before (pre_qty=0)."""
    from service.tools.cart_tool import add_to_cart_tool

    mock_service = MagicMock()
    # dish_id=11 is new → add 1 → post_qty=1, pre_qty=0
    mock_service.add_item.side_effect = [
        {"dish_id": 11, "quantity": 1},
        ValueError("dish not found"),
    ]
    mock_service.remove_item.return_value = {"success": True}

    result = add_to_cart_tool(
        user_id=1,
        items=[
            {"dish_id": 11, "quantity": 1},
            {"dish_id": 999, "quantity": 1},
        ],
        _cart_service=mock_service,
    )

    assert result["success"] is False
    # Pre-add qty was 1-1=0 → new item → remove
    mock_service.remove_item.assert_called_once_with(1, 11)


def test_add_to_cart_tool_all_succeed_returns_before_quantities():
    """Successful batch should include before_quantities for journal."""
    from service.tools.cart_tool import add_to_cart_tool

    mock_service = MagicMock()
    mock_service.add_item.side_effect = [
        {"dish_id": 11, "quantity": 3},   # was 2, added 1
        {"dish_id": 22, "quantity": 2},   # was 0, added 2
    ]

    result = add_to_cart_tool(
        user_id=1,
        items=[
            {"dish_id": 11, "quantity": 1},
            {"dish_id": 22, "quantity": 2},
        ],
        _cart_service=mock_service,
    )

    assert result["success"] is True
    assert len(result["items"]) == 2
    assert result["before_quantities"] == {11: 2, 22: 0}
    mock_service.remove_item.assert_not_called()


def test_add_to_cart_tool_duplicate_dish_id_rejected():
    """Duplicate dish_ids in items should be rejected."""
    from service.tools.cart_tool import add_to_cart_tool

    mock_service = MagicMock()
    result = add_to_cart_tool(
        user_id=1,
        items=[
            {"dish_id": 11, "quantity": 1},
            {"dish_id": 11, "quantity": 2},
        ],
        _cart_service=mock_service,
    )

    assert result["success"] is False
    assert "重复" in result["message"]
    mock_service.add_item.assert_not_called()


def test_add_to_cart_tool_rollback_failure_reported():
    """When rollback itself fails, rollback_failed should be in the result."""
    from service.tools.cart_tool import add_to_cart_tool

    mock_service = MagicMock()
    # dish 11 new (post_qty=1, pre=0), dish 22 new (post_qty=1, pre=0), dish 999 fails
    mock_service.add_item.side_effect = [
        {"dish_id": 11, "quantity": 1},
        {"dish_id": 22, "quantity": 1},
        ValueError("dish not found"),
    ]
    # First rollback succeeds, second fails
    mock_service.remove_item.side_effect = [{"success": True}, Exception("db error")]

    result = add_to_cart_tool(
        user_id=1,
        items=[
            {"dish_id": 11, "quantity": 1},
            {"dish_id": 22, "quantity": 1},
            {"dish_id": 999, "quantity": 1},
        ],
        _cart_service=mock_service,
    )

    assert result["success"] is False
    assert result["rolled_back"] == [11]
    assert result["rollback_failed"] == [22]


def test_add_to_cart_tool_deprecated_single_mode():
    """Single dish_id mode should still work but log deprecation warning."""
    from service.tools.cart_tool import add_to_cart_tool

    mock_service = MagicMock()
    mock_service.add_item.return_value = {"dish_id": 11, "quantity": 1}

    result = add_to_cart_tool(
        user_id=1,
        dish_id=11,
        quantity=1,
        _cart_service=mock_service,
    )

    assert result == {"dish_id": 11, "quantity": 1}
    mock_service.add_item.assert_called_once()


# ── Codex review round 2 — Issue 3: _rule_plan evidence fallback ──────


def test_rule_plan_uses_recent_evidence_when_no_recommendations():
    """_rule_plan should extract dish_ids from recent_evidence when
    last_recommendations is empty."""
    planner = LangGraphAgentPlanner()
    context = {
        "last_recommendations": [],
        "recent_evidence": [
            {"source_type": "dish", "facts": {"dish_id": 10, "dish_name": "宫保鸡丁"}},
            {"source_type": "dish", "facts": {"dish_id": 20, "dish_name": "清蒸鲈鱼"}},
            {"source_type": "merchant", "facts": {"merchant_id": 5}},
        ],
    }
    plan = planner._rule_plan("帮我加入购物车", context)
    assert plan.intent == "cart_action"
    assert len(plan.tool_calls) == 1
    call = plan.tool_calls[0]
    assert call.tool_name == "add_to_cart"
    items = call.arguments["items"]
    dish_ids = {it["dish_id"] for it in items}
    assert dish_ids == {10, 20}


def test_rule_plan_prefers_last_recommendations_over_evidence():
    """When both last_recommendations and recent_evidence exist,
    last_recommendations should be preferred."""
    planner = LangGraphAgentPlanner()
    context = {
        "last_recommendations": [{"dish_id": 99}],
        "recent_evidence": [
            {"source_type": "dish", "facts": {"dish_id": 10}},
        ],
    }
    plan = planner._rule_plan("加入购物车", context)
    assert plan.intent == "cart_action"
    call = plan.tool_calls[0]
    assert call.tool_name == "add_to_cart"
    assert call.arguments["items"] == [{"dish_id": 99, "quantity": 1}]


def test_rule_plan_falls_back_to_rag_when_no_evidence():
    """When both last_recommendations and recent_evidence are empty,
    _rule_plan should generate a RAG call."""
    planner = LangGraphAgentPlanner()
    context = {
        "last_recommendations": [],
        "recent_evidence": [],
    }
    plan = planner._rule_plan("帮我加入购物车", context)
    assert plan.intent == "cart_action"
    assert plan.requires_rag is True
    assert plan.tool_calls[0].tool_name == "recommend_dishes"


# ── Codex review round 5 — items structure validation & rollback msg ───


def test_add_to_cart_tool_rejects_item_missing_dish_id():
    """items=[{}] should return a clean failure, not throw KeyError."""
    from service.tools.cart_tool import add_to_cart_tool

    mock_service = MagicMock()
    result = add_to_cart_tool(
        user_id=1,
        items=[{}],
        _cart_service=mock_service,
    )

    assert result["success"] is False
    assert "格式错误" in result["message"]
    mock_service.add_item.assert_not_called()


def test_add_to_cart_tool_rejects_non_dict_item():
    """items=[1] should return a clean failure, not throw TypeError."""
    from service.tools.cart_tool import add_to_cart_tool

    mock_service = MagicMock()
    result = add_to_cart_tool(
        user_id=1,
        items=[1],
        _cart_service=mock_service,
    )

    assert result["success"] is False
    assert "格式错误" in result["message"]
    mock_service.add_item.assert_not_called()


def test_add_to_cart_tool_rejects_non_integer_dish_id():
    """items=[{"dish_id": "abc"}] should return a clean failure."""
    from service.tools.cart_tool import add_to_cart_tool

    mock_service = MagicMock()
    result = add_to_cart_tool(
        user_id=1,
        items=[{"dish_id": "abc"}],
        _cart_service=mock_service,
    )

    assert result["success"] is False
    assert "无法解析为整数" in result["message"]
    mock_service.add_item.assert_not_called()


def test_execute_action_surfaces_rollback_failure_in_message():
    """When add_to_cart fails with rollback_failed, the message should warn the user."""
    from service.agent_runtime.nodes import LocalActionExecutor

    executor = LocalActionExecutor.__new__(LocalActionExecutor)
    executor.session = None

    state = {
        "user_id": 1,
        "session_id": "s1",
        "recent_evidence": [],
        "tool_results": [],
        "current_plan": AgentPlan(
            intent="cart_action",
            tool_calls=[
                GraphToolCall("add_to_cart", {"items": [{"dish_id": 11, "quantity": 1}]}, True, step_id="add_0"),
            ],
        ),
    }

    # The local import `from service.tools.cart_tool import add_to_cart_tool`
    # resolves via service.tools.cart_tool, so we patch the module-level attr.
    import service.tools.cart_tool as _cart_mod

    original = _cart_mod.add_to_cart_tool
    _cart_mod.add_to_cart_tool = MagicMock(return_value={
        "success": False,
        "message": "添加菜品失败(dish_id=999): dish not found",
        "rolled_back": [11],
        "rollback_failed": [22],
    })
    try:
        result = executor.execute_action(state["current_plan"], state)
    finally:
        _cart_mod.add_to_cart_tool = original

    assert result["success"] is False
    assert "部分回滚失败" in result["message"]
    assert "22" in result["message"]


# ── Codex review round 6 — quantity validation & rollback warning path ──


def test_add_to_cart_tool_rejects_zero_quantity():
    """quantity=0 should be rejected before reaching CartService."""
    from service.tools.cart_tool import add_to_cart_tool

    mock_service = MagicMock()
    result = add_to_cart_tool(
        user_id=1,
        items=[{"dish_id": 11, "quantity": 0}],
        _cart_service=mock_service,
    )

    assert result["success"] is False
    assert "quantity 必须 >= 1" in result["message"]
    mock_service.add_item.assert_not_called()


def test_add_to_cart_tool_rejects_negative_quantity():
    """Negative quantity should be rejected before reaching CartService."""
    from service.tools.cart_tool import add_to_cart_tool

    mock_service = MagicMock()
    result = add_to_cart_tool(
        user_id=1,
        items=[{"dish_id": 11, "quantity": -3}],
        _cart_service=mock_service,
    )

    assert result["success"] is False
    assert "quantity 必须 >= 1" in result["message"]
    mock_service.add_item.assert_not_called()


def test_add_to_cart_tool_rejects_non_integer_quantity():
    """Non-integer quantity should be rejected."""
    from service.tools.cart_tool import add_to_cart_tool

    mock_service = MagicMock()
    result = add_to_cart_tool(
        user_id=1,
        items=[{"dish_id": 11, "quantity": "abc"}],
        _cart_service=mock_service,
    )

    assert result["success"] is False
    assert "quantity 无法解析为整数" in result["message"]
    mock_service.add_item.assert_not_called()


def test_append_action_confirmations_surfaces_rollback_warning():
    """_append_action_confirmations should include failed action warnings
    when rollback_failed is present, not just success messages."""
    from service.agent_runtime.nodes import _append_action_confirmations

    tool_results = [
        {
            "type": "add_to_cart",
            "success": False,
            "message": "添加失败(dish_id=999)（注意：部分回滚失败 dish_id=[22]，购物车可能已被部分修改，请检查）",
            "data": {"rollback_failed": [22]},
        },
    ]
    result = _append_action_confirmations("推荐了几道菜", tool_results)
    assert "部分回滚失败" in result
    assert "推荐了几道菜" in result


def test_append_action_confirmations_no_warning_for_normal_failure():
    """Normal failures without rollback_failed should NOT be appended."""
    from service.agent_runtime.nodes import _append_action_confirmations

    tool_results = [
        {
            "type": "add_to_cart",
            "success": False,
            "message": "添加失败(dish_id=999): dish not found",
            "data": {},
        },
    ]
    result = _append_action_confirmations("推荐了几道菜", tool_results)
    # Normal failure doesn't get appended — only rollback_failed does
    assert result == "推荐了几道菜"
