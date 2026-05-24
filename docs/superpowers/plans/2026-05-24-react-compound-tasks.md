# ReAct 复合任务增强 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the existing LangGraph evaluate→plan loop function as a true ReAct cycle so compound user requests (e.g. "recommend Sichuan dishes then add to cart") execute end-to-end.

**Architecture:** Enhance the existing graph without changing topology. Introduce `step_id` for per-call tracking, inject observation context into re-planning, make rag_node single-step, and add unfulfilled-intent detection in evaluate_node.

**Tech Stack:** Python 3.11, LangGraph, LangChain, Pydantic, pytest

---

## File Structure

| File | Action | Responsibility |
|---|---|---|
| `service/agent_runtime/state.py` | Modify | Add `step_id` field to `GraphToolCall` dataclass |
| `service/agent_runtime/schemas.py` | Modify | Add `step_id` field to `GraphToolCallSchema` Pydantic model |
| `service/agent_runtime/planner.py` | Modify | `_parse_tool_calls` step_id dedup; `_build_human_input` context injection; `_schema_to_plan`/`_parse` step_id passthrough |
| `service/agent_runtime/nodes.py` | Modify | `_normalize_tool_result` step_id; 6× step_id matching; `plan_node` reuse; `rag_node` single-step; evidence bridging; `evaluate_node` intent check; `respond_node` merging |
| `prompt/agent/planner.system.md` | Modify | Append continuation planning rules |
| `tests/service/test_compound_tasks.py` | Create | 12 unit tests covering all new behaviors |

---

### Task 1: Add step_id to GraphToolCall and GraphToolCallSchema

**Files:**
- Modify: `service/agent_runtime/state.py:22-25`
- Modify: `service/agent_runtime/schemas.py:15-20`
- Test: `tests/service/test_compound_tasks.py`

- [ ] **Step 1: Write failing test for step_id field existence**

```python
# tests/service/test_compound_tasks.py
"""Tests for ReAct compound task enhancements."""

from service.agent_runtime.state import GraphToolCall


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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/service/test_compound_tasks.py::test_graph_tool_call_has_step_id_field -v`
Expected: FAIL — `GraphToolCall.__init__()` got an unexpected keyword argument 'step_id' (or attribute missing)

- [ ] **Step 3: Add step_id to GraphToolCall**

In `service/agent_runtime/state.py`, change the `GraphToolCall` dataclass:

```python
@dataclass
class GraphToolCall:
    tool_name: str
    arguments: dict[str, Any] = field(default_factory=dict)
    writes_database: bool = False
    step_id: str = ""
```

- [ ] **Step 4: Add step_id to GraphToolCallSchema**

In `service/agent_runtime/schemas.py`, add the field to `GraphToolCallSchema`:

```python
class GraphToolCallSchema(BaseModel):
    """Schema for a single tool call in the agent plan."""

    tool_name: str = Field(default="", description="Exact tool name from the available tool set")
    arguments: dict[str, Any] = Field(default_factory=dict, description="Tool arguments as key-value pairs")
    writes_database: bool = Field(default=False, description="Whether this tool writes to the database")
    step_id: str = Field(default="", description="Optional step identifier, auto-generated if empty")
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/service/test_compound_tasks.py -v`
Expected: 2 tests PASS

- [ ] **Step 6: Commit**

```bash
git add service/agent_runtime/state.py service/agent_runtime/schemas.py tests/service/test_compound_tasks.py
git commit -m "feat: add step_id field to GraphToolCall and schema"
```

---

### Task 2: Rewrite _parse_tool_calls with step_id deduplication

**Files:**
- Modify: `service/agent_runtime/planner.py:198-224`
- Test: `tests/service/test_compound_tasks.py`

- [ ] **Step 1: Write failing tests for step_id dedup**

Append to `tests/service/test_compound_tasks.py`:

```python
from service.agent_runtime.planner import LangGraphAgentPlanner


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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/service/test_compound_tasks.py::test_parse_tool_calls_generates_unique_step_ids -v`
Expected: FAIL — only 1 call returned (old tool_name dedup drops duplicates)

- [ ] **Step 3: Rewrite _parse_tool_calls**

In `service/agent_runtime/planner.py`, replace the `_parse_tool_calls` method (lines 198-224):

```python
    def _parse_tool_calls(self, raw_calls: list[dict[str, Any]], intent: str) -> list[GraphToolCall]:
        calls: list[GraphToolCall] = []
        tool_name_counter: dict[str, int] = {}
        seen_step_ids: set[str] = set()
        for item in raw_calls:
            if not isinstance(item, dict):
                continue
            raw_name = str(item.get("tool_name") or item.get("name") or "")
            tool_name = self._normalize_tool_name(raw_name, intent)
            if tool_name is None:
                continue
            arguments = item.get("arguments") or item.get("parameters") or {}
            if not isinstance(arguments, dict):
                arguments = {}
            writes_database = self._parse_bool(item.get("writes_database", False))
            if tool_name in RAG_TOOL_NAMES:
                writes_database = False
            if tool_name in ACTION_TOOL_NAMES | UNDO_TOOL_NAMES:
                writes_database = True
            count = tool_name_counter.get(tool_name, 0)
            step_id = item.get("step_id") or f"{tool_name}_{count}"
            if step_id in seen_step_ids:
                continue
            tool_name_counter[tool_name] = count + 1
            seen_step_ids.add(step_id)
            calls.append(
                GraphToolCall(
                    tool_name=tool_name,
                    arguments=arguments,
                    writes_database=writes_database,
                    step_id=step_id,
                )
            )
        return calls
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/service/test_compound_tasks.py -v`
Expected: All 5 tests PASS

- [ ] **Step 5: Run existing planner tests to ensure no regressions**

Run: `python -m pytest tests/service/test_langgraph_agent_planner.py -v`
Expected: All existing tests PASS (step_id defaults to auto-generated, old behavior preserved)

- [ ] **Step 6: Commit**

```bash
git add service/agent_runtime/planner.py tests/service/test_compound_tasks.py
git commit -m "feat: replace tool_name dedup with step_id dedup in _parse_tool_calls"
```

---

### Task 3: Add step_id to _normalize_tool_result and all completion checks

**Files:**
- Modify: `service/agent_runtime/nodes.py:215-224,254-275,360-370,530-541,567-582`
- Test: `tests/service/test_compound_tasks.py`

- [ ] **Step 1: Write failing tests for step_id-based completion**

Append to `tests/service/test_compound_tasks.py`:

```python
from service.agent_runtime.nodes import _normalize_tool_result
from service.agent_runtime.state import AgentPlan, GraphToolCall


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
    completed_step_ids = {r.get("step_id", r.get("type", "")) for r in tool_results}
    remaining = [c for c in plan.tool_calls if c.step_id not in completed_step_ids]
    assert len(remaining) == 1
    assert remaining[0].step_id == "add_to_cart_1"
    assert remaining[0].arguments["dish_id"] == 35
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/service/test_compound_tasks.py::test_normalize_tool_result_includes_step_id -v`
Expected: FAIL — `_normalize_tool_result()` got unexpected keyword argument 'step_id'

- [ ] **Step 3: Update _normalize_tool_result to accept and record step_id**

In `service/agent_runtime/nodes.py`, replace `_normalize_tool_result` (lines 567-582):

```python
def _normalize_tool_result(result: dict, state: dict, executed_tool_name: str = "", step_id: str = "") -> dict:
    tool_name = executed_tool_name
    if not tool_name:
        plan = state.get("current_plan")
        if plan and plan.tool_calls:
            tool_name = plan.tool_calls[0].tool_name
    data = dict(result.get("data") or {})
    for key in ("action_id", "undo_available"):
        if key in result:
            data[key] = result[key]
    return {
        "type": result.get("type") or tool_name or "unknown",
        "step_id": step_id,
        "success": bool(result.get("success", False)),
        "message": result.get("message", ""),
        "data": data,
    }
```

- [ ] **Step 4: Update route_after_plan to use step_id matching and fix early-return**

In `service/agent_runtime/nodes.py`, replace lines 221-229 in `route_after_plan`. The early-return condition must also exclude remaining RAG calls (not just action calls), otherwise multi-RAG scenarios short-circuit to "respond" after the first RAG completes:

```python
    has_evidence = bool(state.get("recent_evidence"))
    completed_step_ids = {r.get("step_id", r.get("type", "")) for r in state.get("tool_results", [])}
    remaining_calls = [c for c in plan.tool_calls if c.step_id not in completed_step_ids]

    if has_evidence and plan.intent in {"recommendation", "knowledge"} and not any(
        c.tool_name in ACTION_TOOL_NAMES | RAG_TOOL_NAMES for c in remaining_calls
    ):
        logger.debug("Agent route: evidence already present, intent=%s → respond", plan.intent)
        return "respond"
```

- [ ] **Step 5: Update evaluate_node to use step_id matching**

In `service/agent_runtime/nodes.py`, replace lines 271-275 in `evaluate_node`:

```python
    completed_step_ids = {r.get("step_id", r.get("type", "")) for r in state.get("tool_results", [])}
    pending_calls = [
        call for call in plan.tool_calls
        if call.step_id not in completed_step_ids
    ]
```

- [ ] **Step 6: Update action_node to use step_id matching and pass step_id to _normalize_tool_result**

In `service/agent_runtime/nodes.py`, replace lines 535-547 in `action_node`:

```python
    # Determine which action tool will be executed next
    completed_step_ids = {r.get("step_id", r.get("type", "")) for r in state.get("tool_results", [])}
    next_action_call = next(
        (c for c in plan.tool_calls
         if c.tool_name in ACTION_TOOL_NAMES and c.step_id not in completed_step_ids),
        None,
    )
    executed_tool_name = next_action_call.tool_name if next_action_call else ""
    executed_step_id = next_action_call.step_id if next_action_call else ""

    result = executor.execute_action(plan, state)

    # Accumulate tool_results instead of replacing
    existing_results = list(state.get("tool_results", []))
    existing_results.append(_normalize_tool_result(result, state, executed_tool_name, step_id=executed_step_id))
```

- [ ] **Step 7: Update LocalActionExecutor.execute_action to use step_id matching**

In `service/agent_runtime/nodes.py`, replace lines 366-370 in `execute_action`:

```python
        completed_step_ids = {r.get("step_id", r.get("type", "")) for r in state.get("tool_results", [])}
        call = next(
            (item for item in plan.tool_calls
             if item.tool_name in ACTION_TOOL_NAMES and item.step_id not in completed_step_ids),
            None,
        )
```

- [ ] **Step 8: Update undo_node to pass step_id**

In `service/agent_runtime/nodes.py`, update `undo_node` (line 563):

```python
    existing_results.append(_normalize_tool_result(result, state, "undo_last_action", step_id="undo_last_action_0"))
```

- [ ] **Step 9: Run tests to verify they pass**

Run: `python -m pytest tests/service/test_compound_tasks.py -v`
Expected: All 7 tests PASS

- [ ] **Step 10: Run existing node tests to ensure no regressions**

Run: `python -m pytest tests/service/test_langgraph_agent_graph.py tests/service/test_multistep_plan.py tests/service/test_langgraph_undo_flow.py -v`
Expected: All PASS (step_id defaults to empty string, backward compatible with old `r.get("type", "")` fallback)

- [ ] **Step 11: Commit**

```bash
git add service/agent_runtime/nodes.py tests/service/test_compound_tasks.py
git commit -m "feat: switch all completion checks from tool_name to step_id"
```

---

### Task 4: plan_node pending call reuse

**Files:**
- Modify: `service/agent_runtime/nodes.py:181-201`
- Test: `tests/service/test_compound_tasks.py`

- [ ] **Step 1: Write failing test for plan reuse**

Append to `tests/service/test_compound_tasks.py`:

```python
from service.agent_runtime.nodes import plan_node
from unittest.mock import MagicMock, patch


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

    # Mock get_runtime to return None so it uses default planner
    # But the plan should be reused, so planner.plan should NOT be called
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
```

Add the necessary import at the top of the test file:

```python
from langchain_core.messages import HumanMessage
from unittest.mock import MagicMock, patch
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/service/test_compound_tasks.py::test_plan_reuse_on_pending_calls -v`
Expected: FAIL — `plan_node` always calls planner.plan, does not check for pending calls

- [ ] **Step 3: Add pending-call reuse logic to plan_node**

In `service/agent_runtime/nodes.py`, replace `plan_node` (lines 181-201):

```python
def plan_node(state: dict, config: RunnableConfig | None = None) -> dict:
    # Reuse current plan if it still has pending (uncompleted) calls.
    # This prevents step_id collision from counter-reset on re-planning.
    current_plan = state.get("current_plan")
    if current_plan and current_plan.tool_calls:
        completed_step_ids = {
            r.get("step_id", r.get("type", ""))
            for r in state.get("tool_results", [])
        }
        pending = [c for c in current_plan.tool_calls if c.step_id not in completed_step_ids]
        if pending:
            return {"current_plan": current_plan}

    # All calls completed (or no plan) — call LLM for (re-)planning
    runtime = get_runtime(config)
    planner = (runtime.planner if runtime else None) or _get_default_planner()

    user_message = latest_user_message(state)
    conversation_history = _format_recent_turns(state.get("messages", []), max_turns=3)
    plan = planner.plan(
        user_message,
        {
            "session_id": state.get("session_id"),
            "user_id": state.get("user_id"),
            "loaded_user_memories": state.get("loaded_user_memories", []),
            "recent_action_ids": state.get("recent_action_ids", []),
            "iteration_count": state.get("iteration_count", 0),
            "recent_evidence": state.get("recent_evidence", []),
            "tool_results": state.get("tool_results", []),
            "conversation_history": conversation_history,
            "last_recommendations": state.get("last_recommendations", []),
        },
    )
    return {"current_plan": plan}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/service/test_compound_tasks.py -v`
Expected: All 9 tests PASS

- [ ] **Step 5: Commit**

```bash
git add service/agent_runtime/nodes.py tests/service/test_compound_tasks.py
git commit -m "feat: plan_node reuses current plan when pending calls exist"
```

---

### Task 5: ReAct context injection in _build_human_input

**Files:**
- Modify: `service/agent_runtime/planner.py:88-115`
- Test: `tests/service/test_compound_tasks.py`

- [ ] **Step 1: Write failing test for context injection**

Append to `tests/service/test_compound_tasks.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/service/test_compound_tasks.py::test_build_human_input_injects_evidence -v`
Expected: FAIL — "## 本轮已检索到的结果" not in output

- [ ] **Step 3: Extend _build_human_input with observation sections**

In `service/agent_runtime/planner.py`, replace `_build_human_input` (lines 88-115):

```python
    @staticmethod
    def _build_human_input(user_message: str, context: dict[str, Any]) -> str:
        """Build composite human message that includes conversation history,
        last recommendations, and ReAct observation context so both structured
        and fallback LLM paths receive the same multi-turn context."""
        parts: list[str] = []

        conversation_history = context.get("conversation_history", "")
        if conversation_history:
            parts.append(f"## 对话历史\n{conversation_history}")

        last_recs = context.get("last_recommendations", [])
        if last_recs:
            rec_lines = []
            for idx, rec in enumerate(last_recs, 1):
                name = rec.get("dish_name") or rec.get("merchant_name") or ""
                dish_id = rec.get("dish_id", "")
                price = rec.get("price", "")
                line = f"{idx}. {name}"
                if dish_id:
                    line += f" (dish_id={dish_id})"
                if price:
                    line += f" {price}元"
                rec_lines.append(line)
            parts.append("## 上一轮推荐结果\n" + "\n".join(rec_lines))

        # ReAct observation: evidence from completed RAG calls
        recent_evidence = context.get("recent_evidence", [])
        if recent_evidence:
            evidence_lines = []
            for idx, item in enumerate(recent_evidence, 1):
                facts = item.get("facts", {})
                source_type = item.get("source_type", "")
                if source_type == "dish":
                    line = (
                        f"{idx}. {facts.get('dish_name', '')} "
                        f"(dish_id={facts.get('dish_id', '')}, "
                        f"商家={facts.get('merchant_name', '')}, "
                        f"{facts.get('price', '')}元, "
                        f"{facts.get('cuisine_type', '')}/{facts.get('flavor_profile', '')})"
                    )
                else:
                    line = (
                        f"{idx}. {facts.get('merchant_name', facts.get('name', ''))} "
                        f"(merchant_id={facts.get('merchant_id', facts.get('id', ''))})"
                    )
                evidence_lines.append(line)
            parts.append("## 本轮已检索到的结果\n" + "\n".join(evidence_lines))

        # ReAct observation: completed tool actions
        tool_results = context.get("tool_results", [])
        if tool_results:
            result_lines = []
            for r in tool_results:
                status = "成功" if r.get("success") else "失败"
                result_lines.append(
                    f"- {r.get('step_id', r.get('type', ''))}: {status} - {r.get('message', '')}"
                )
            parts.append("## 本轮已完成的操作\n" + "\n".join(result_lines))

        parts.append(f"## 用户最新消息\n{user_message}")
        return "\n\n".join(parts)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/service/test_compound_tasks.py -v`
Expected: All 12 tests PASS

- [ ] **Step 5: Run existing planner tests for regressions**

Run: `python -m pytest tests/service/test_langgraph_agent_planner.py -v`
Expected: All PASS

- [ ] **Step 6: Commit**

```bash
git add service/agent_runtime/planner.py tests/service/test_compound_tasks.py
git commit -m "feat: inject ReAct observation context into planner _build_human_input"
```

---

### Task 6: Planner prompt continuation rules

**Files:**
- Modify: `prompt/agent/planner.system.md`

- [ ] **Step 1: Append continuation planning rules to the prompt**

Add the following block to the end of `prompt/agent/planner.system.md`:

```markdown

续接规划规则（ReAct 循环）：
- 当输入中包含"## 本轮已检索到的结果"时，说明本轮内 RAG 检索已经完成。
- 当输入中包含"## 本轮已完成的操作"时，不要输出已完成的 step_id 对应的 tool_call。
- 如果用户的原始请求包含后续操作（如"加入购物车""记住偏好"），你应当：
  - intent 设为后续操作对应的类型（如 cart_action、preference_action）
  - 从"## 本轮已检索到的结果"中提取需要的参数（如 dish_id）填入 tool_call arguments
  - 如果用户没有指定具体哪个结果，默认选择排名第 1 的
  - 如果用户说"都加入购物车"，为每个菜品生成一条 add_to_cart，每条携带不同的 dish_id
- 如果用户请求多个独立子查询（如"推荐一个川菜，再推荐一个湘菜"），而当前检索结果只覆盖了部分，
  则应当为未满足的部分生成新的 recommend_dishes 调用，更新 normalized_query 和 filters。
- 续接规划时，如果 RAG 阶段已完成且后续只有 action，requires_rag 设为 false。
```

- [ ] **Step 2: Verify the prompt file is well-formed**

Run: `python -c "from service.agent_runtime.prompts import PromptRegistry; p = PromptRegistry(); print(len(p.load('agent.planner')), 'chars loaded')"`
Expected: Prints char count > 0, no errors

- [ ] **Step 3: Commit**

```bash
git add prompt/agent/planner.system.md
git commit -m "feat: add ReAct continuation planning rules to planner prompt"
```

---

### Task 7: rag_node single-step execution + evidence accumulation

**Files:**
- Modify: `service/agent_runtime/nodes.py:303-347`
- Test: `tests/service/test_compound_tasks.py`

- [ ] **Step 1: Write failing tests for single-step RAG and evidence accumulation**

Append to `tests/service/test_compound_tasks.py`:

```python
from service.agent_runtime.nodes import rag_node


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


def test_rag_node_single_step_execution():
    """rag_node should only execute the NEXT pending RAG call, not all of them."""
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

    # Should only mark recommend_dishes_0 complete
    completed_step_ids = {r["step_id"] for r in result["tool_results"]}
    assert "recommend_dishes_0" in completed_step_ids
    assert "recommend_dishes_1" not in completed_step_ids
    assert len(retriever.calls) == 1


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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/service/test_compound_tasks.py::test_rag_node_single_step_execution -v`
Expected: FAIL — current rag_node marks ALL RAG calls complete in one pass

- [ ] **Step 3: Add helper function _build_call_scoped_plan**

In `service/agent_runtime/nodes.py`, add this function before `rag_node` (around line 302):

```python
def _build_call_scoped_plan(plan, call_args):
    """Create a shallow copy of plan with filters overridden by a specific tool_call's arguments.

    This allows each RAG sub-task to search with its own cuisine/flavor/keyword constraints
    rather than the plan-level filters.
    """
    import copy
    scoped = copy.copy(plan)
    filters = dict(plan.filters or {})

    for key in ("cuisine_types", "flavor_preferences", "required_keywords",
                "forbidden_keywords", "exclude_allergens", "source_types",
                "limit", "sort_by", "price_preference", "budget_max"):
        if key in call_args and call_args[key] is not None:
            filters[key] = call_args[key]

    if call_args.get("query"):
        scoped.normalized_query = call_args["query"]

    scoped.filters = filters
    return scoped
```

- [ ] **Step 4: Rewrite rag_node for single-step execution**

In `service/agent_runtime/nodes.py`, replace `rag_node` (lines 303-347):

```python
def rag_node(state: dict, config: RunnableConfig | None = None) -> dict:
    from service.config import get_config

    runtime = get_runtime(config)
    retriever = (runtime.retriever if runtime else None) or AdvancedRagRetriever()

    rag_cfg = get_config().rag
    plan = state["current_plan"]

    # Find the NEXT pending RAG call (single-step execution)
    completed_step_ids = {
        r.get("step_id", r.get("type", ""))
        for r in state.get("tool_results", [])
    }
    next_rag_call = next(
        (c for c in plan.tool_calls
         if c.tool_name in RAG_TOOL_NAMES and c.step_id not in completed_step_ids),
        None,
    )

    if next_rag_call is None:
        return {}  # No pending RAG call

    # Use this call's arguments to determine retrieval parameters
    call_args = next_rag_call.arguments or {}
    effective_query = (
        call_args.get("query")
        or plan.normalized_query
        or latest_user_message(state)
    )

    # Build a scoped plan with this call's filters
    call_plan = _build_call_scoped_plan(plan, call_args)

    evidence = retriever.retrieve(
        effective_query,
        agent_plan=call_plan,
        memories=state.get("loaded_user_memories", []),
        limit=rag_cfg.output_limit_default,
        max_limit=rag_cfg.output_limit_max,
    )
    serialized = [
        {
            "source_type": item.source_type,
            "source_id": item.source_id,
            "merchant_id": item.merchant_id,
            "title": item.title,
            "facts": item.facts,
            "why_matched": item.why_matched,
            "citation": item.citation,
            "score": item.score,
        }
        for item in evidence
    ]

    # Evidence accumulation — append, don't replace
    existing_evidence = list(state.get("recent_evidence", []))
    seen_keys = {(e.get("source_type"), e.get("source_id")) for e in existing_evidence}
    for item in serialized:
        key = (item["source_type"], item["source_id"])
        if key not in seen_keys:
            existing_evidence.append(item)
            seen_keys.add(key)

    # Mark only THIS step complete
    existing_results = list(state.get("tool_results", []))
    existing_results.append({
        "type": next_rag_call.tool_name,
        "step_id": next_rag_call.step_id,
        "success": True,
        "message": f"检索到 {len(serialized)} 条结果",
        "data": {},
    })

    return {"recent_evidence": existing_evidence, "tool_results": existing_results}
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/service/test_compound_tasks.py -v`
Expected: All 14 tests PASS

- [ ] **Step 6: Run existing RAG-related tests for regressions**

Run: `python -m pytest tests/service/test_langgraph_agent_graph.py tests/service/test_multistep_plan.py -v`
Expected: All PASS

- [ ] **Step 7: Commit**

```bash
git add service/agent_runtime/nodes.py tests/service/test_compound_tasks.py
git commit -m "feat: rag_node single-step execution with evidence accumulation"
```

---

### Task 8: Evidence bridging fallback for add_to_cart

**Files:**
- Modify: `service/agent_runtime/nodes.py:398-408`
- Test: `tests/service/test_compound_tasks.py`

- [ ] **Step 1: Write failing test for evidence bridging**

Append to `tests/service/test_compound_tasks.py`:

```python
from service.agent_runtime.nodes import LocalActionExecutor


def test_evidence_bridging_fallback_for_add_to_cart():
    """When LLM omits dish_id, action executor should fall back to evidence."""
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

    with patch("service.tools.cart_tool.add_to_cart_tool", return_value={"item_id": 1}) as mock_tool, \
         patch("service.action_journal_service.ActionJournalService") as mock_journal_cls:
        mock_journal = MagicMock()
        mock_journal.record_completed_action.return_value = {"action_id": "act_1"}
        mock_journal_cls.return_value = mock_journal

        result = executor.execute_action(plan, state)

    assert result["success"] is True
    # The tool should have been called with dish_id=12 (first from evidence)
    mock_tool.assert_called_once()
    _, call_kwargs = mock_tool.call_args
    assert call_kwargs["dish_id"] == 12
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/service/test_compound_tasks.py::test_evidence_bridging_fallback_for_add_to_cart -v`
Expected: FAIL — current code returns `{"success": False, "message": "缺少 dish_id 参数"}` when dish_id is None

- [ ] **Step 3: Add evidence bridging to add_to_cart branch**

In `service/agent_runtime/nodes.py`, update the `add_to_cart` branch in `execute_action` (around lines 398-408). Replace this section:

```python
        if call.tool_name == "add_to_cart":
            from service.tools.cart_tool import add_to_cart_tool

            dish_id = call.arguments.get("dish_id")
            quantity = call.arguments.get("quantity", 1)
            if dish_id is None:
                return {
                    "success": False,
                    "message": "缺少 dish_id 参数",
                    "undo_available": False,
                }
```

With:

```python
        if call.tool_name == "add_to_cart":
            from service.tools.cart_tool import add_to_cart_tool

            dish_id = call.arguments.get("dish_id")
            quantity = call.arguments.get("quantity", 1)

            # Evidence bridging fallback: if LLM omitted dish_id, pick from evidence
            if dish_id is None:
                dish_evidence = [
                    e for e in state.get("recent_evidence", [])
                    if e.get("source_type") == "dish"
                ]
                if dish_evidence:
                    dish_id = dish_evidence[0].get("facts", {}).get("dish_id")

            if dish_id is None:
                return {
                    "success": False,
                    "message": "缺少 dish_id 参数",
                    "undo_available": False,
                }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/service/test_compound_tasks.py::test_evidence_bridging_fallback_for_add_to_cart -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add service/agent_runtime/nodes.py tests/service/test_compound_tasks.py
git commit -m "feat: evidence bridging fallback when LLM omits dish_id in add_to_cart"
```

---

### Task 9: evaluate_node unfulfilled intent detection

**Files:**
- Modify: `service/agent_runtime/nodes.py:254-296`
- Test: `tests/service/test_compound_tasks.py`

- [ ] **Step 1: Write failing tests for unfulfilled intent detection**

Append to `tests/service/test_compound_tasks.py`:

```python
from service.agent_runtime.nodes import evaluate_node


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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/service/test_compound_tasks.py::test_unfulfilled_action_intent_triggers_replan -v`
Expected: FAIL — evaluate_node returns `_next=respond` because all plan.tool_calls are completed

- [ ] **Step 3: Add unfulfilled intent detection functions**

In `service/agent_runtime/nodes.py`, add these functions before `evaluate_node` (around line 253):

```python
# ── Unfulfilled intent detection ─────────────────────────────────────

_ACTION_INTENT_MAPPING = {
    "add_to_cart": ["加入购物车", "加购物车", "加到购物车", "都加入", "加购", "买"],
    "remove_from_cart": ["移除", "从购物车删", "去掉"],
    "cart_clear": ["清空购物车", "全部删除"],
    "upsert_preference": ["记住", "偏好", "不吃", "过敏"],
    "save_address": ["保存地址", "加入地址"],
}

_COMPOUND_QUERY_MARKERS = ["再推荐", "再来", "还要", "另外推荐", "还推荐", "同时推荐"]

_CUISINE_KEYWORDS = {
    "川菜": "川菜", "湘菜": "湘菜", "粤菜": "粤菜", "日料": "日韩料理",
    "韩餐": "日韩料理", "西餐": "西餐", "火锅": "火锅", "烧烤": "烧烤",
    "咖啡": "咖啡甜品", "甜品": "咖啡甜品", "轻食": "轻食",
}


def _has_unfulfilled_intent(state: dict) -> bool:
    return _has_unfulfilled_action_intent(state) or _has_unfulfilled_retrieval_intent(state)


def _has_unfulfilled_action_intent(state: dict) -> bool:
    user_message = latest_user_message(state)
    completed_action_tools = {
        r.get("type", "")
        for r in state.get("tool_results", [])
        if r.get("success", False) and r.get("type", "") in ACTION_TOOL_NAMES
    }
    for tool_name, keywords in _ACTION_INTENT_MAPPING.items():
        if any(kw in user_message for kw in keywords):
            if tool_name not in completed_action_tools:
                return True
    return False


def _has_unfulfilled_retrieval_intent(state: dict) -> bool:
    user_message = latest_user_message(state)

    if not any(marker in user_message for marker in _COMPOUND_QUERY_MARKERS):
        return False

    mentioned = set()
    for keyword, cuisine in _CUISINE_KEYWORDS.items():
        if keyword in user_message:
            mentioned.add(cuisine)

    if len(mentioned) < 2:
        return False

    evidence = state.get("recent_evidence", [])
    covered = {
        e.get("facts", {}).get("cuisine_type", "")
        for e in evidence
        if e.get("source_type") == "dish"
    }
    return not mentioned.issubset(covered)
```

- [ ] **Step 4: Update evaluate_node to call unfulfilled intent check**

In `service/agent_runtime/nodes.py`, update `evaluate_node`. Replace lines 288-293 (the `has_evidence or has_tool_results` block):

```python
    has_evidence = bool(state.get("recent_evidence"))
    has_tool_results = bool(state.get("tool_results"))

    if has_evidence or has_tool_results:
        # Check for unfulfilled follow-up intent before going to respond
        if _has_unfulfilled_intent(state):
            logger.debug("Agent evaluate: unfulfilled intent detected → plan (continuation)")
            return {"iteration_count": iteration, "_next": "plan", "metrics": existing_metrics}
        logger.debug("Agent evaluate: all steps done → respond")
        return {"iteration_count": iteration, "_next": "respond", "metrics": existing_metrics}
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/service/test_compound_tasks.py -v`
Expected: All 17 tests PASS

- [ ] **Step 6: Run existing evaluate tests for regressions**

Run: `python -m pytest tests/service/test_langgraph_agent_graph.py tests/service/test_agent_loop.py -v`
Expected: All PASS

- [ ] **Step 7: Commit**

```bash
git add service/agent_runtime/nodes.py tests/service/test_compound_tasks.py
git commit -m "feat: evaluate_node detects unfulfilled action and retrieval intent"
```

---

### Task 10: respond_node action merging

**Files:**
- Modify: `service/agent_runtime/nodes.py:585-686,725-749,788-798`
- Test: `tests/service/test_compound_tasks.py`

- [ ] **Step 1: Write failing test for respond merging**

Append to `tests/service/test_compound_tasks.py`:

```python
from service.agent_runtime.nodes import respond_node


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
    assert "✅" in message
    assert "已将宫保鸡丁加入购物车" in message
    assert result["response_payload"]["response_type"] == "action_completed"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/service/test_compound_tasks.py::test_respond_merges_action_results_with_evidence -v`
Expected: FAIL — current template path doesn't append action results; response_type is "cart_action" not "action_completed"

- [ ] **Step 3: Update _external_response_type for compound scenarios**

In `service/agent_runtime/nodes.py`, replace `_external_response_type` (lines 788-798):

```python
def _external_response_type(plan, state: dict) -> str:
    if plan is None:
        return "unsupported"
    # Compound scenario: evidence + successful action → action_completed
    tool_results = state.get("tool_results", [])
    has_successful_action = any(
        r.get("success") and r.get("type", "") in ACTION_TOOL_NAMES
        for r in tool_results
    )
    if has_successful_action:
        return "action_completed"
    if state.get("tool_results") and plan.intent in {
        "cart_action",
        "address_action",
        "preference_action",
        "undo_action",
    }:
        return "action_completed"
    return plan.intent
```

- [ ] **Step 4: Update template fallback path to append action confirmation**

In `service/agent_runtime/nodes.py`, update the `elif evidence:` branch in `respond_node` (around line 631-632):

Replace:
```python
    elif evidence:
        message = _template_recommendation(recommendations)
```

With:
```python
    elif evidence:
        message = _template_recommendation(recommendations)
        # Append action confirmation when both evidence and action results exist
        if tool_results:
            action_msgs = [
                r.get("message", "")
                for r in tool_results
                if r.get("success") and r.get("type", "") in ACTION_TOOL_NAMES
            ]
            if action_msgs:
                message += "\n\n" + "\n".join(f"✅ {m}" for m in action_msgs)
```

- [ ] **Step 5: Update LLM response path to inject tool_results**

In `service/agent_runtime/nodes.py`, update the `if evidence and use_llm:` branch (around line 629-630):

Replace:
```python
    if evidence and use_llm:
        message = _generate_llm_response(user_message, response_type, evidence, conversation_history)
```

With:
```python
    if evidence and use_llm:
        message = _generate_llm_response(
            user_message, response_type, evidence, conversation_history,
            tool_results=tool_results,
        )
```

- [ ] **Step 6: Update _generate_llm_response to accept tool_results**

In `service/agent_runtime/nodes.py`, replace `_generate_llm_response` (lines 725-749):

```python
def _generate_llm_response(
    user_message: str,
    response_type: str,
    evidence: list[dict],
    conversation_history: str = "",
    tool_results: list[dict] | None = None,
) -> str:
    try:
        from service.agent_runtime.prompts import PromptRegistry
        from tools.llm_tool import call_llm

        evidence_text = _format_evidence_for_llm(evidence)
        system_prompt = PromptRegistry().load("agent.answer_grounded")
        parts = []
        if conversation_history:
            parts.append(f"对话历史：\n{conversation_history}\n")
        parts.append(f"用户最新消息：{user_message}")
        parts.append(f"意图：{response_type}")
        parts.append(f"\n检索到的证据：\n{evidence_text}")

        # Inject completed action results for compound scenarios
        if tool_results:
            action_lines = []
            for r in tool_results:
                if r.get("type", "") in ACTION_TOOL_NAMES:
                    status = "成功" if r.get("success") else "失败"
                    action_lines.append(f"- {r.get('message', '')}（{status}）")
            if action_lines:
                parts.append(f"\n已完成的操作：\n" + "\n".join(action_lines))

        parts.append("\n请基于证据和已完成操作生成自然回复。")
        prompt = "\n".join(parts)
        return call_llm(query=prompt, system_instruction=system_prompt)
    except Exception:
        logger.warning("LLM response generation failed, falling back to template", exc_info=True)
        recommendations, _ = _build_structured_data(evidence)
        return _template_recommendation(recommendations)
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `python -m pytest tests/service/test_compound_tasks.py -v`
Expected: All 18 tests PASS

- [ ] **Step 8: Run existing respond tests for regressions**

Run: `python -m pytest tests/service/test_langgraph_agent_graph.py tests/service/test_multistep_plan.py tests/service/test_assistant_service_langgraph.py -v`
Expected: All PASS

- [ ] **Step 9: Commit**

```bash
git add service/agent_runtime/nodes.py tests/service/test_compound_tasks.py
git commit -m "feat: respond_node merges action confirmation with recommendation output"
```

---

### Task 11: Integration tests — 3 compound scenarios

**Files:**
- Test: `tests/service/test_compound_tasks.py`

These tests use the full graph (`build_agent_graph`) with mock planner/retriever/executor to verify end-to-end ReAct loop behavior.

- [ ] **Step 1: Write integration test for "recommend then add to cart"**

Append to `tests/service/test_compound_tasks.py`:

```python
from service.agent_runtime.graph import build_agent_graph
from service.agent_runtime.runtime import AgentRuntimeContext


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
        completed_step_ids = {r.get("step_id", r.get("type", "")) for r in state.get("tool_results", [])}
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
    assert "✅" in message
```

- [ ] **Step 2: Write integration test for "recommend then add ALL to cart"**

Append to `tests/service/test_compound_tasks.py`:

```python
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
```

- [ ] **Step 3: Write integration test for "multi-cuisine RAG"**

Append to `tests/service/test_compound_tasks.py`:

```python
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
```

- [ ] **Step 4: Run all tests**

Run: `python -m pytest tests/service/test_compound_tasks.py -v`
Expected: All 21 tests PASS

- [ ] **Step 5: Run the full test suite for regressions**

Run: `python -m pytest tests/ -v --timeout=60`
Expected: All existing tests PASS

- [ ] **Step 6: Commit**

```bash
git add tests/service/test_compound_tasks.py
git commit -m "test: add integration tests for 3 compound task scenarios"
```

---

## Full Test File Import Header

The `tests/service/test_compound_tasks.py` file needs these imports at the top (accumulated from all tasks):

```python
"""Tests for ReAct compound task enhancements."""

from unittest.mock import MagicMock, patch

from langchain_core.messages import HumanMessage

from service.agent_runtime.graph import build_agent_graph
from service.agent_runtime.nodes import (
    LocalActionExecutor,
    _normalize_tool_result,
    evaluate_node,
    plan_node,
    rag_node,
    respond_node,
)
from service.agent_runtime.planner import ACTION_TOOL_NAMES, LangGraphAgentPlanner
from service.agent_runtime.runtime import AgentRuntimeContext
from service.agent_runtime.state import AgentPlan, GraphToolCall
```

## Summary of All Commits (in order)

1. `feat: add step_id field to GraphToolCall and schema`
2. `feat: replace tool_name dedup with step_id dedup in _parse_tool_calls`
3. `feat: switch all completion checks from tool_name to step_id`
4. `feat: plan_node reuses current plan when pending calls exist`
5. `feat: inject ReAct observation context into planner _build_human_input`
6. `feat: add ReAct continuation planning rules to planner prompt`
7. `feat: rag_node single-step execution with evidence accumulation`
8. `feat: evidence bridging fallback when LLM omits dish_id in add_to_cart`
9. `feat: evaluate_node detects unfulfilled action and retrieval intent`
10. `feat: respond_node merges action confirmation with recommendation output`
11. `test: add integration tests for 3 compound task scenarios`
