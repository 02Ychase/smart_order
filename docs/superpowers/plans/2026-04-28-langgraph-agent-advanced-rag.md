# LangGraph Agent Advanced RAG Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the rule-heavy assistant backend with a LangGraph agent runtime, function-specific prompts, reversible local actions with undo, session and user memory, and an advanced RAG pipeline.

**Architecture:** LangGraph owns the assistant state machine and short-term session memory. LangChain remains the LLM and structured-output integration layer. Business writes are performed by existing services and recorded in a SQL action journal; RAG is refactored into a dedicated subsystem with query planning, multi-route recall, fusion, filtering, reranking, diversification, and evaluation.

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy, Alembic, LangGraph, LangChain, Pinecone, DashScope embeddings, pytest, Vue 3 frontend compatibility.

---

## File Structure

### Dependencies

- Modify: `pyproject.toml` — add `langgraph>=1.0.0`.
- Modify: `requirements.txt` — add `langgraph>=1.0.0`.
- Modify: `tests/test_project_dependencies.py` — assert the new dependency is declared.

### Agent Runtime

- Create: `service/agent_runtime/__init__.py`
- Create: `service/agent_runtime/state.py` — typed graph state and plan models.
- Create: `service/agent_runtime/prompts.py` — prompt registry and prompt loading.
- Create: `service/agent_runtime/planner.py` — LLM-first structured planner with deterministic fallback.
- Create: `service/agent_runtime/graph.py` — LangGraph graph builder and compiled app cache.
- Create: `service/agent_runtime/nodes.py` — graph node functions.
- Create: `tests/service/test_agent_runtime_state.py`
- Create: `tests/service/test_prompt_registry.py`
- Create: `tests/service/test_langgraph_agent_planner.py`
- Create: `tests/service/test_langgraph_agent_graph.py`

### Prompt Files

- Create: `prompt/agent/planner.system.md`
- Create: `prompt/agent/query_rewrite.system.md`
- Create: `prompt/agent/answer_grounded.system.md`
- Create: `prompt/agent/memory_writer.system.md`
- Create: `prompt/agent/undo_resolver.system.md`
- Create: `prompt/tools/cart_action.system.md`
- Create: `prompt/tools/address_action.system.md`
- Create: `prompt/tools/preference_action.system.md`
- Create: `prompt/tools/recommendation.system.md`
- Create: `prompt/tools/catalog_qa.system.md`

### Advanced RAG

- Create: `service/rag/__init__.py`
- Create: `service/rag/models.py` — query plan, recall candidates, fused candidates, evidence packs.
- Create: `service/rag/query_planner.py` — LLM-ready query planner wrapper and rule fallback.
- Create: `service/rag/recall.py` — dense, sparse, SQL, memory, and business recall routes.
- Create: `service/rag/fusion.py` — RRF fusion and candidate de-duplication.
- Create: `service/rag/filters.py` — hard filters and soft match annotations.
- Create: `service/rag/reranker.py` — rerank interface and weighted fallback.
- Create: `service/rag/diversifier.py` — merchant, dish, and category diversity rules.
- Create: `service/rag/retriever.py` — orchestrates the full retrieval pipeline.
- Modify: `service/tools/recommendation_tool.py` — call the new retriever.
- Modify: `service/tools/catalog_tool.py` — call the new retriever.
- Create: `tests/service/rag/test_query_planner.py`
- Create: `tests/service/rag/test_recall_routes.py`
- Create: `tests/service/rag/test_fusion.py`
- Create: `tests/service/rag/test_filters.py`
- Create: `tests/service/rag/test_reranker.py`
- Create: `tests/service/rag/test_diversifier.py`
- Create: `tests/service/rag/test_retriever_pipeline.py`

### Action Journal And Undo

- Modify: `api/models/__init__.py` — export new models.
- Create: `api/models/action_journal.py` — action journal table.
- Create: `database/migrations/versions/20260428_01_action_journal.py`
- Create: `repository/action_journal_repository.py`
- Create: `service/action_journal_service.py`
- Create: `service/tools/preference_tool.py`
- Modify: `service/tools/cart_tool.py` — add snapshot-based clear/restore helpers.
- Modify: `service/tools/address_tool.py` — add undo-friendly delete/update helpers.
- Create: `tests/service/test_action_journal_service.py`
- Create: `tests/service/test_undo_tools.py`

### User Memory

- Create: `api/models/user_memory.py`
- Modify: `api/models/__init__.py`
- Create: `database/migrations/versions/20260428_02_user_memory.py`
- Create: `repository/user_memory_repository.py`
- Create: `service/user_memory_service.py`
- Create: `tests/service/test_user_memory_service.py`

### Assistant Integration

- Modify: `service/assistant_service.py` — delegate `AssistantChatRequest` to LangGraph runtime.
- Modify: `api/schemas.py` — add `undo_available` and optional action summary fields without breaking existing frontend fields.
- Create: `tests/service/test_assistant_service_langgraph.py`
- Modify: `tests/api/test_assistant_routes.py`

### Evaluation And Documentation

- Modify: `tools/evaluate_assistant_rag.py`
- Modify: `tests/eval/assistant_rag_cases.jsonl`
- Create: `tests/service/rag/test_rag_metrics.py`
- Modify: `README.md`
- Modify: `ui/README.md`

---

### Task 1: Add LangGraph Dependency And Guard Tests

**Files:**
- Modify: `pyproject.toml`
- Modify: `requirements.txt`
- Modify: `tests/test_project_dependencies.py`

- [ ] **Step 1: Write the failing dependency test**

Update `tests/test_project_dependencies.py`:

```python
REQUIRED_REQUIREMENTS = {
    "sqlalchemy>=2.0.36",
    "alembic>=1.14.0",
    "passlib[bcrypt]>=1.7.4",
    "python-jose[cryptography]>=3.3.0",
    "pytest>=8.2.0",
    "httpx>=0.27.0",
    "langgraph>=1.0.0",
}

REQUIRED_PYPROJECT = {
    "SQLAlchemy>=2.0.36",
    "alembic>=1.14.0",
    "passlib[bcrypt]>=1.7.4",
    "python-jose[cryptography]>=3.3.0",
    "pytest>=8.2.0",
    "httpx>=0.27.0",
    "langgraph>=1.0.0",
}
```

- [ ] **Step 2: Run dependency test to verify failure**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_project_dependencies.py -q
```

Expected: FAIL because `langgraph>=1.0.0` is missing from dependency files.

- [ ] **Step 3: Add dependency declarations**

Add to `requirements.txt`:

```text
langgraph>=1.0.0
```

Add to `pyproject.toml` dependencies:

```toml
    "langgraph>=1.0.0",
```

- [ ] **Step 4: Run dependency test to verify pass**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_project_dependencies.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add pyproject.toml requirements.txt tests/test_project_dependencies.py
git commit -m "chore: add langgraph dependency"
```

---

### Task 2: Add Agent Runtime State Models

**Files:**
- Create: `service/agent_runtime/__init__.py`
- Create: `service/agent_runtime/state.py`
- Create: `tests/service/test_agent_runtime_state.py`

- [ ] **Step 1: Write the failing state model tests**

Create `tests/service/test_agent_runtime_state.py`:

```python
from service.agent_runtime.state import AgentPlan, GraphToolCall, SmartOrderAgentState


def test_agent_plan_defaults_answer_directly_for_recommendations() -> None:
    plan = AgentPlan(
        intent="recommendation",
        normalized_query="辣的湘菜",
        requires_rag=True,
    )

    assert plan.should_answer_directly is True
    assert plan.filters["cuisine_types"] == []
    assert plan.tool_calls == []


def test_graph_state_tracks_recent_evidence_and_actions() -> None:
    state = SmartOrderAgentState(
        messages=[],
        session_id="s1",
        user_id=7,
        recent_evidence=[{"source_type": "dish", "source_id": 11}],
        recent_action_ids=["act_1"],
    )

    assert state["session_id"] == "s1"
    assert state["user_id"] == 7
    assert state["recent_evidence"][0]["source_id"] == 11
    assert state["recent_action_ids"] == ["act_1"]


def test_tool_call_records_direct_write_flag() -> None:
    call = GraphToolCall(
        tool_name="cart_clear",
        arguments={"user_id": 7},
        writes_database=True,
    )

    assert call.writes_database is True
```

- [ ] **Step 2: Run state tests to verify failure**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/service/test_agent_runtime_state.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'service.agent_runtime'`.

- [ ] **Step 3: Create state models**

Create `service/agent_runtime/__init__.py`:

```python
"""LangGraph runtime for the smart_order assistant."""
```

Create `service/agent_runtime/state.py`:

```python
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, NotRequired, TypedDict

from langchain_core.messages import BaseMessage


AgentIntent = Literal[
    "greeting",
    "recommendation",
    "knowledge",
    "cart_action",
    "address_action",
    "preference_action",
    "undo_action",
    "unsupported",
]


@dataclass
class GraphToolCall:
    tool_name: str
    arguments: dict[str, Any] = field(default_factory=dict)
    writes_database: bool = False


@dataclass
class AgentPlan:
    intent: AgentIntent
    normalized_query: str = ""
    requires_rag: bool = False
    filters: dict[str, Any] = field(default_factory=lambda: {
        "cuisine_types": [],
        "flavor_preferences": [],
        "budget_max": None,
        "party_size": None,
        "exclude_allergens": [],
    })
    tool_calls: list[GraphToolCall] = field(default_factory=list)
    should_answer_directly: bool = True
    response_hint: str = ""


class SmartOrderAgentState(TypedDict):
    messages: list[BaseMessage]
    session_id: str
    user_id: NotRequired[int | None]
    active_topic: NotRequired[str | None]
    loaded_user_memories: NotRequired[list[dict[str, Any]]]
    recent_evidence: NotRequired[list[dict[str, Any]]]
    recent_action_ids: NotRequired[list[str]]
    current_plan: NotRequired[AgentPlan | None]
    tool_results: NotRequired[list[dict[str, Any]]]
    response_payload: NotRequired[dict[str, Any]]
```

- [ ] **Step 4: Run state tests to verify pass**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/service/test_agent_runtime_state.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add service/agent_runtime/__init__.py service/agent_runtime/state.py tests/service/test_agent_runtime_state.py
git commit -m "feat: add langgraph agent state models"
```

---

### Task 3: Add Prompt Registry And Prompt Files

**Files:**
- Create: `service/agent_runtime/prompts.py`
- Create: `prompt/agent/planner.system.md`
- Create: `prompt/agent/query_rewrite.system.md`
- Create: `prompt/agent/answer_grounded.system.md`
- Create: `prompt/agent/memory_writer.system.md`
- Create: `prompt/agent/undo_resolver.system.md`
- Create: `prompt/tools/cart_action.system.md`
- Create: `prompt/tools/address_action.system.md`
- Create: `prompt/tools/preference_action.system.md`
- Create: `prompt/tools/recommendation.system.md`
- Create: `prompt/tools/catalog_qa.system.md`
- Create: `tests/service/test_prompt_registry.py`

- [ ] **Step 1: Write the failing prompt registry tests**

Create `tests/service/test_prompt_registry.py`:

```python
from service.agent_runtime.prompts import PromptRegistry


def test_prompt_registry_loads_planner_prompt() -> None:
    registry = PromptRegistry()

    prompt = registry.load("agent.planner")

    assert "smart_order" in prompt
    assert "should_answer_directly" in prompt
    assert "只返回" in prompt


def test_prompt_registry_rejects_unknown_prompt_key() -> None:
    registry = PromptRegistry()

    try:
        registry.load("agent.missing")
    except KeyError as exc:
        assert "agent.missing" in str(exc)
    else:
        raise AssertionError("unknown prompt key should raise KeyError")
```

- [ ] **Step 2: Run prompt tests to verify failure**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/service/test_prompt_registry.py -q
```

Expected: FAIL because `service.agent_runtime.prompts` does not exist.

- [ ] **Step 3: Create prompt registry**

Create `service/agent_runtime/prompts.py`:

```python
from __future__ import annotations

from pathlib import Path


class PromptRegistry:
    def __init__(self, project_root: Path | None = None) -> None:
        self.project_root = project_root or Path(__file__).resolve().parents[2]
        self._mapping = {
            "agent.planner": "prompt/agent/planner.system.md",
            "agent.query_rewrite": "prompt/agent/query_rewrite.system.md",
            "agent.answer_grounded": "prompt/agent/answer_grounded.system.md",
            "agent.memory_writer": "prompt/agent/memory_writer.system.md",
            "agent.undo_resolver": "prompt/agent/undo_resolver.system.md",
            "tools.cart_action": "prompt/tools/cart_action.system.md",
            "tools.address_action": "prompt/tools/address_action.system.md",
            "tools.preference_action": "prompt/tools/preference_action.system.md",
            "tools.recommendation": "prompt/tools/recommendation.system.md",
            "tools.catalog_qa": "prompt/tools/catalog_qa.system.md",
        }

    def load(self, key: str) -> str:
        relative_path = self._mapping.get(key)
        if relative_path is None:
            raise KeyError(f"unknown prompt key: {key}")
        prompt_path = self.project_root / relative_path
        return prompt_path.read_text(encoding="utf-8").strip()
```

- [ ] **Step 4: Create prompt files**

Create `prompt/agent/planner.system.md`:

```markdown
你是 smart_order 的 LangGraph Agent Planner。

你只负责理解用户请求并输出结构化计划，不直接回答用户，不直接写数据库。

必须只返回 JSON，字段如下：
{
  "intent": "greeting | recommendation | knowledge | cart_action | address_action | preference_action | undo_action | unsupported",
  "normalized_query": "适合检索的简短查询",
  "requires_rag": true,
  "filters": {
    "cuisine_types": [],
    "flavor_preferences": [],
    "budget_max": null,
    "party_size": null,
    "exclude_allergens": []
  },
  "tool_calls": [
    {"tool_name": "工具名", "arguments": {}, "writes_database": false}
  ],
  "should_answer_directly": true,
  "response_hint": "给回答节点的简短提示"
}

规则：
- 推荐和知识查询默认直接回答，不因为缺少预算、人数、口味而追问。
- 预算、人数、过敏原、菜系是可选过滤条件。
- 购物车、地址、用户偏好这类本地可逆写操作可以直接执行。
- 撤回、恢复、刚才那个不要了，都归类为 undo_action。
- 订单、支付、退款等不可逆或外部副作用操作返回 unsupported。
- 用户语言可能是中文、英文或混合表达，需要根据语义理解。
```

Create `prompt/agent/query_rewrite.system.md`:

```markdown
你是 smart_order 的 RAG 查询规划器。

输入包括用户原始问题、Planner 计划、短期会话上下文和用户长期记忆。

输出 JSON：
{
  "original_query": "用户原文",
  "normalized_query": "适合 dense retrieval 的简短查询",
  "expansion_queries": [],
  "must_filters": {},
  "should_filters": {},
  "source_types": ["dish", "merchant"],
  "answer_mode": "recommendation | knowledge | comparison | action_support"
}

要求：
- must_filters 只放必须满足的硬约束，例如明确过敏原排除、指定商家、下架过滤。
- should_filters 放偏好，例如辣、清淡、下饭、高评分、配送快。
- 不要因为用户没有预算或人数而生成追问。
```

Create `prompt/agent/answer_grounded.system.md`:

```markdown
你是 smart_order 的证据化回答生成器。

你必须基于 evidence 中的商家、菜品、价格、口味、引用片段回答用户。
不能编造 evidence 里不存在的商家、菜品、价格、营业时间或配送信息。

如果 evidence 为空，直接说明没有找到足够匹配的结果，并建议用户换一种说法。
如果 evidence 有结果，给出简洁自然的推荐理由。
```

Create `prompt/agent/memory_writer.system.md`:

```markdown
你是 smart_order 的用户记忆提取器。

从当前对话中提取可以长期保存的用户偏好事实。
只输出 JSON：
{
  "memories": [
    {"memory_type": "food_preference | dietary_constraint | merchant_affinity | response_style", "content": "结构化事实", "confidence": 0.0}
  ]
}

只保存可复用偏好，不保存一次性的临时需求。
```

Create `prompt/agent/undo_resolver.system.md`:

```markdown
你是 smart_order 的撤回意图解析器。

根据用户消息和最近 action journal 摘要，判断用户要撤回哪一个本地可逆操作。
只输出 JSON：
{
  "target": "last_undoable_action | action_id | none",
  "action_id": null,
  "reason": "简短理由"
}
```

Create `prompt/tools/cart_action.system.md`:

```markdown
你把用户购物车相关请求转换成工具参数。
支持 add_item、remove_item、clear_cart、restore_cart_snapshot。
只输出 JSON，不写解释。
```

Create `prompt/tools/address_action.system.md`:

```markdown
你把用户地址相关请求转换成工具参数。
支持 create_address、update_address、delete_address、set_default_address、restore_address_snapshot。
只输出 JSON，不写解释。
```

Create `prompt/tools/preference_action.system.md`:

```markdown
你把用户偏好设置请求转换成工具参数。
支持 create_preference、update_preference、delete_preference。
只输出 JSON，不写解释。
```

Create `prompt/tools/recommendation.system.md`:

```markdown
你是菜品推荐工具的专用提示词。
你负责把用户需求转成推荐检索参数，回答必须依赖 RAG evidence。
```

Create `prompt/tools/catalog_qa.system.md`:

```markdown
你是商家和菜品事实问答工具的专用提示词。
你负责把用户查询转成目录检索参数，回答必须依赖 RAG evidence。
```

- [ ] **Step 5: Run prompt tests to verify pass**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/service/test_prompt_registry.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add service/agent_runtime/prompts.py prompt/agent prompt/tools tests/service/test_prompt_registry.py
git commit -m "feat: add assistant prompt registry"
```

---

### Task 4: Add LLM-First Planner With No Mandatory Recommendation Clarification

**Files:**
- Create: `service/agent_runtime/planner.py`
- Create: `tests/service/test_langgraph_agent_planner.py`

- [ ] **Step 1: Write failing planner tests**

Create `tests/service/test_langgraph_agent_planner.py`:

```python
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
```

- [ ] **Step 2: Run planner tests to verify failure**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/service/test_langgraph_agent_planner.py -q
```

Expected: FAIL because `service.agent_runtime.planner` does not exist.

- [ ] **Step 3: Create planner implementation**

Create `service/agent_runtime/planner.py`:

```python
from __future__ import annotations

import json
import os
from typing import Any

from service.agent_runtime.prompts import PromptRegistry
from service.agent_runtime.state import AgentPlan, GraphToolCall
from tools.llm_tool import call_llm


class LangGraphAgentPlanner:
    def __init__(self, prompts: PromptRegistry | None = None) -> None:
        self.prompts = prompts or PromptRegistry()
        self._model_name = os.getenv("MODEL_NAME")
        self._llm = None

    def plan(self, user_message: str, context: dict[str, Any]) -> AgentPlan:
        if self._llm is not None:
            raw = self._llm.call(user_message, self.prompts.load("agent.planner"))
            return self._parse(raw)

        if self._model_name:
            try:
                raw = call_llm(
                    query=json.dumps({"message": user_message, "context": context}, ensure_ascii=False),
                    system_instruction=self.prompts.load("agent.planner"),
                )
                return self._parse(raw)
            except Exception:
                return self._rule_plan(user_message)

        return self._rule_plan(user_message)

    def _parse(self, raw: str | dict[str, Any]) -> AgentPlan:
        parsed = raw if isinstance(raw, dict) else json.loads(self._clean_json(raw))
        filters = {
            "cuisine_types": [],
            "flavor_preferences": [],
            "budget_max": None,
            "party_size": None,
            "exclude_allergens": [],
        }
        filters.update(parsed.get("filters") or {})
        return AgentPlan(
            intent=parsed.get("intent", "unsupported"),
            normalized_query=parsed.get("normalized_query", ""),
            requires_rag=bool(parsed.get("requires_rag", False)),
            filters=filters,
            tool_calls=[
                GraphToolCall(
                    tool_name=item.get("tool_name", ""),
                    arguments=item.get("arguments", {}),
                    writes_database=bool(item.get("writes_database", False)),
                )
                for item in parsed.get("tool_calls", [])
            ],
            should_answer_directly=bool(parsed.get("should_answer_directly", True)),
            response_hint=parsed.get("response_hint", ""),
        )

    @staticmethod
    def _clean_json(raw: str) -> str:
        text = raw.strip()
        if text.startswith("```"):
            text = text.replace("```json", "").replace("```", "").strip()
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            return text[start : end + 1]
        return text

    def _rule_plan(self, user_message: str) -> AgentPlan:
        message = user_message.strip().lower()

        if message in {"hi", "hello", "你好", "嗨", "在吗"}:
            return AgentPlan(intent="greeting", should_answer_directly=True)

        if any(term in message for term in ("撤回", "恢复", "刚才那个不要", "undo")):
            return AgentPlan(
                intent="undo_action",
                tool_calls=[GraphToolCall(tool_name="undo_last_action", writes_database=True)],
                should_answer_directly=True,
            )

        if "购物车" in message and any(term in message for term in ("清空", "删除全部", "全部删除")):
            return AgentPlan(
                intent="cart_action",
                tool_calls=[GraphToolCall(tool_name="cart_clear", writes_database=True)],
                should_answer_directly=True,
            )

        if any(term in message for term in ("推荐", "吃什么", "来几个")):
            filters = {
                "cuisine_types": ["湘菜"] if "湘菜" in user_message else [],
                "flavor_preferences": ["辣"] if "辣" in user_message else [],
                "budget_max": None,
                "party_size": None,
                "exclude_allergens": [],
            }
            return AgentPlan(
                intent="recommendation",
                normalized_query=user_message,
                requires_rag=True,
                filters=filters,
                should_answer_directly=True,
            )

        if any(term in message for term in ("商家", "店", "营业", "电话", "地址", "多少钱", "价格")):
            return AgentPlan(
                intent="knowledge",
                normalized_query=user_message,
                requires_rag=True,
                should_answer_directly=True,
            )

        return AgentPlan(intent="unsupported", should_answer_directly=True)
```

- [ ] **Step 4: Run planner tests to verify pass**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/service/test_langgraph_agent_planner.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add service/agent_runtime/planner.py tests/service/test_langgraph_agent_planner.py
git commit -m "feat: add langgraph assistant planner"
```

---

### Task 5: Add RAG Models, Query Planner, Fusion, Filters, Reranker, And Diversifier

**Files:**
- Create: `service/rag/__init__.py`
- Create: `service/rag/models.py`
- Create: `service/rag/query_planner.py`
- Create: `service/rag/fusion.py`
- Create: `service/rag/filters.py`
- Create: `service/rag/reranker.py`
- Create: `service/rag/diversifier.py`
- Create: `tests/service/rag/test_query_planner.py`
- Create: `tests/service/rag/test_fusion.py`
- Create: `tests/service/rag/test_filters.py`
- Create: `tests/service/rag/test_reranker.py`
- Create: `tests/service/rag/test_diversifier.py`

- [ ] **Step 1: Write failing RAG core tests**

Create `tests/service/rag/test_query_planner.py`:

```python
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
```

Create `tests/service/rag/test_fusion.py`:

```python
from service.rag.fusion import reciprocal_rank_fusion
from service.rag.models import RecallCandidate


def test_rrf_merges_candidates_by_stable_key() -> None:
    dense = [
        RecallCandidate(stable_key="dish:1", source_type="dish", source_id=1, route="dense", rank=1, score=0.8),
        RecallCandidate(stable_key="dish:2", source_type="dish", source_id=2, route="dense", rank=2, score=0.7),
    ]
    sparse = [
        RecallCandidate(stable_key="dish:2", source_type="dish", source_id=2, route="sparse", rank=1, score=1.0),
        RecallCandidate(stable_key="dish:3", source_type="dish", source_id=3, route="sparse", rank=2, score=0.9),
    ]

    fused = reciprocal_rank_fusion([dense, sparse], limit=3)

    assert [item.stable_key for item in fused] == ["dish:2", "dish:1", "dish:3"]
    assert fused[0].route_scores["dense"] > 0
    assert fused[0].route_scores["sparse"] > 0
```

Create `tests/service/rag/test_filters.py`:

```python
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
```

Create `tests/service/rag/test_reranker.py`:

```python
from service.rag.models import FusedCandidate
from service.rag.reranker import WeightedReranker


def test_weighted_reranker_prefers_relevance_and_constraints() -> None:
    candidates = [
        FusedCandidate(stable_key="dish:1", source_type="dish", source_id=1, facts={"merchant_rating": 4.9}, dense_score=0.2, lexical_score=0.1, constraint_match=0.2),
        FusedCandidate(stable_key="dish:2", source_type="dish", source_id=2, facts={"merchant_rating": 4.5}, dense_score=0.8, lexical_score=0.7, constraint_match=1.0),
    ]

    ranked = WeightedReranker().rerank(candidates, original_query="辣的湘菜")

    assert ranked[0].stable_key == "dish:2"
    assert ranked[0].final_score > ranked[1].final_score
```

Create `tests/service/rag/test_diversifier.py`:

```python
from service.rag.diversifier import diversify
from service.rag.models import FusedCandidate


def test_diversifier_limits_same_merchant_when_not_scoped() -> None:
    candidates = [
        FusedCandidate(stable_key="dish:1", source_type="dish", source_id=1, facts={"merchant_id": 1, "dish_name": "A"}, final_score=0.9),
        FusedCandidate(stable_key="dish:2", source_type="dish", source_id=2, facts={"merchant_id": 1, "dish_name": "B"}, final_score=0.8),
        FusedCandidate(stable_key="dish:3", source_type="dish", source_id=3, facts={"merchant_id": 2, "dish_name": "C"}, final_score=0.7),
    ]

    result = diversify(candidates, limit=2, merchant_scoped=False)

    assert [item.stable_key for item in result] == ["dish:1", "dish:3"]
```

- [ ] **Step 2: Run RAG core tests to verify failure**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/service/rag/test_query_planner.py tests/service/rag/test_fusion.py tests/service/rag/test_filters.py tests/service/rag/test_reranker.py tests/service/rag/test_diversifier.py -q
```

Expected: FAIL because `service.rag` package does not exist.

- [ ] **Step 3: Create RAG models and query planner**

Create `service/rag/__init__.py`:

```python
"""Advanced RAG subsystem for smart_order."""
```

Create `service/rag/models.py`:

```python
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


SourceType = Literal["dish", "merchant", "memory"]


@dataclass
class RagQueryPlan:
    original_query: str
    normalized_query: str
    expansion_queries: list[str] = field(default_factory=list)
    must_filters: dict[str, Any] = field(default_factory=dict)
    should_filters: dict[str, Any] = field(default_factory=dict)
    source_types: list[SourceType] = field(default_factory=lambda: ["dish", "merchant"])
    answer_mode: str = "recommendation"


@dataclass
class RecallCandidate:
    stable_key: str
    source_type: SourceType
    source_id: int
    route: str
    rank: int
    score: float
    facts: dict[str, Any] = field(default_factory=dict)
    citation: str = ""


@dataclass
class FusedCandidate:
    stable_key: str
    source_type: SourceType
    source_id: int
    facts: dict[str, Any] = field(default_factory=dict)
    citation: str = ""
    route_scores: dict[str, float] = field(default_factory=dict)
    route_ranks: dict[str, int] = field(default_factory=dict)
    dense_score: float = 0.0
    lexical_score: float = 0.0
    constraint_match: float = 1.0
    final_score: float = 0.0


@dataclass
class RagEvidence:
    source_type: SourceType
    source_id: int
    merchant_id: int
    title: str
    facts: dict[str, Any]
    why_matched: list[str] = field(default_factory=list)
    citation: str = ""
    score: float = 0.0
```

Create `service/rag/query_planner.py`:

```python
from __future__ import annotations

from service.agent_runtime.state import AgentPlan
from service.rag.models import RagQueryPlan


class RagQueryPlanner:
    def plan(self, original_query: str, agent_plan: AgentPlan, memories: list[dict]) -> RagQueryPlan:
        normalized = agent_plan.normalized_query or original_query
        filters = agent_plan.filters or {}
        cuisine_types = filters.get("cuisine_types") or []
        flavor_preferences = filters.get("flavor_preferences") or []
        exclude_allergens = filters.get("exclude_allergens") or []

        expansion_queries = [normalized, original_query]
        if "湘菜" in cuisine_types and "辣" in flavor_preferences:
            expansion_queries.append("湘菜 香辣 下饭")
            expansion_queries.append("湖南菜 小炒 剁椒")
        if exclude_allergens:
            expansion_queries.append("不含" + " ".join(exclude_allergens))

        must_filters = {"is_available": True}
        if exclude_allergens:
            must_filters["exclude_allergens"] = exclude_allergens

        source_types = ["dish"]
        if agent_plan.intent == "knowledge":
            source_types = ["dish", "merchant"]

        return RagQueryPlan(
            original_query=original_query,
            normalized_query=normalized,
            expansion_queries=list(dict.fromkeys(query for query in expansion_queries if query)),
            must_filters=must_filters,
            should_filters={
                "cuisine_types": cuisine_types,
                "flavor_preferences": flavor_preferences,
                "budget_max": filters.get("budget_max"),
                "party_size": filters.get("party_size"),
            },
            source_types=source_types,
            answer_mode=agent_plan.intent,
        )
```

- [ ] **Step 4: Create fusion, filters, reranker, and diversifier**

Create `service/rag/fusion.py`:

```python
from __future__ import annotations

from service.rag.models import FusedCandidate, RecallCandidate


def reciprocal_rank_fusion(route_results: list[list[RecallCandidate]], limit: int = 50, k: int = 60) -> list[FusedCandidate]:
    by_key: dict[str, FusedCandidate] = {}
    totals: dict[str, float] = {}

    for candidates in route_results:
        for candidate in candidates:
            fused = by_key.get(candidate.stable_key)
            if fused is None:
                fused = FusedCandidate(
                    stable_key=candidate.stable_key,
                    source_type=candidate.source_type,
                    source_id=candidate.source_id,
                    facts=dict(candidate.facts),
                    citation=candidate.citation,
                )
                by_key[candidate.stable_key] = fused
            fused.route_scores[candidate.route] = candidate.score
            fused.route_ranks[candidate.route] = candidate.rank
            if candidate.route == "dense":
                fused.dense_score = max(fused.dense_score, candidate.score)
            if candidate.route in {"sparse", "sql"}:
                fused.lexical_score = max(fused.lexical_score, candidate.score)
            totals[candidate.stable_key] = totals.get(candidate.stable_key, 0.0) + 1.0 / (k + candidate.rank)

    fused_items = list(by_key.values())
    for item in fused_items:
        item.final_score = totals[item.stable_key]
    return sorted(fused_items, key=lambda item: item.final_score, reverse=True)[:limit]
```

Create `service/rag/filters.py`:

```python
from __future__ import annotations

from service.rag.models import FusedCandidate, RagQueryPlan


def apply_hard_filters(candidates: list[FusedCandidate], plan: RagQueryPlan) -> list[FusedCandidate]:
    filters = plan.must_filters or {}
    exclude_allergens = set(filters.get("exclude_allergens") or [])
    require_available = bool(filters.get("is_available", False))
    merchant_name = filters.get("merchant_name")

    kept = []
    for candidate in candidates:
        facts = candidate.facts
        if require_available and facts.get("is_available") is False:
            continue
        if exclude_allergens and any(item in set(facts.get("allergens") or []) for item in exclude_allergens):
            continue
        if merchant_name and facts.get("merchant_name") != merchant_name:
            continue
        kept.append(candidate)
    return kept
```

Create `service/rag/reranker.py`:

```python
from __future__ import annotations

from service.rag.models import FusedCandidate


class WeightedReranker:
    def rerank(self, candidates: list[FusedCandidate], original_query: str) -> list[FusedCandidate]:
        for candidate in candidates:
            merchant_rating = float(candidate.facts.get("merchant_rating") or 0.0) / 5.0
            business_boost = 1.0 if candidate.facts.get("is_recommended") else 0.0
            user_preference_match = float(candidate.facts.get("user_preference_match") or 0.0)
            candidate.final_score = (
                0.45 * max(candidate.dense_score, candidate.final_score)
                + 0.10 * candidate.dense_score
                + 0.10 * candidate.lexical_score
                + 0.10 * candidate.constraint_match
                + 0.05 * merchant_rating
                + 0.05 * user_preference_match
                + 0.05 * business_boost
            )
        return sorted(candidates, key=lambda item: item.final_score, reverse=True)
```

Create `service/rag/diversifier.py`:

```python
from __future__ import annotations

from service.rag.models import FusedCandidate


def diversify(candidates: list[FusedCandidate], limit: int, merchant_scoped: bool = False) -> list[FusedCandidate]:
    if merchant_scoped:
        return candidates[:limit]

    selected = []
    seen_dish_names = set()
    merchant_counts: dict[int, int] = {}

    for candidate in candidates:
        dish_name = candidate.facts.get("dish_name")
        merchant_id = candidate.facts.get("merchant_id")
        if dish_name and dish_name in seen_dish_names:
            continue
        if merchant_id is not None and merchant_counts.get(int(merchant_id), 0) >= 1:
            continue
        selected.append(candidate)
        if dish_name:
            seen_dish_names.add(dish_name)
        if merchant_id is not None:
            merchant_counts[int(merchant_id)] = merchant_counts.get(int(merchant_id), 0) + 1
        if len(selected) >= limit:
            return selected

    for candidate in candidates:
        if candidate not in selected:
            selected.append(candidate)
        if len(selected) >= limit:
            break
    return selected
```

- [ ] **Step 5: Run RAG core tests to verify pass**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/service/rag/test_query_planner.py tests/service/rag/test_fusion.py tests/service/rag/test_filters.py tests/service/rag/test_reranker.py tests/service/rag/test_diversifier.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add service/rag tests/service/rag/test_query_planner.py tests/service/rag/test_fusion.py tests/service/rag/test_filters.py tests/service/rag/test_reranker.py tests/service/rag/test_diversifier.py
git commit -m "feat: add advanced rag core pipeline units"
```

---

### Task 6: Add Multi-Route RAG Retriever And Tool Integration

**Files:**
- Create: `service/rag/recall.py`
- Create: `service/rag/retriever.py`
- Create: `tests/service/rag/test_recall_routes.py`
- Create: `tests/service/rag/test_retriever_pipeline.py`
- Modify: `service/tools/recommendation_tool.py`
- Modify: `service/tools/catalog_tool.py`
- Modify: `tests/service/test_assistant_tools.py`

- [ ] **Step 1: Write failing recall and retriever tests**

Create `tests/service/rag/test_recall_routes.py`:

```python
from service.rag.models import RagQueryPlan
from service.rag.recall import SqlCatalogRecallRoute


class StubCatalogService:
    def list_merchants(self):
        return [{"id": 1, "name": "兰姨小炒", "rating": 4.7, "merchant_tags": ["湘菜"], "business_hours": "10:00-21:30"}]

    def list_dishes_by_merchant(self, merchant_id):
        return [
            {"id": 11, "merchant_id": 1, "name": "小炒黄牛肉", "price": 42.0, "cuisine_type": "湘菜", "flavor_profile": "鲜辣下饭", "allergens": [], "is_recommended": True, "is_available": True}
        ]


def test_sql_recall_returns_dish_candidates_for_cuisine_and_flavor() -> None:
    plan = RagQueryPlan(
        original_query="辣的湘菜",
        normalized_query="辣的湘菜",
        should_filters={"cuisine_types": ["湘菜"], "flavor_preferences": ["辣"]},
        source_types=["dish"],
    )

    candidates = SqlCatalogRecallRoute(StubCatalogService()).recall(plan, limit=10)

    assert candidates[0].stable_key == "dish:11"
    assert candidates[0].facts["dish_name"] == "小炒黄牛肉"
    assert candidates[0].route == "sql"
```

Create `tests/service/rag/test_retriever_pipeline.py`:

```python
from service.agent_runtime.state import AgentPlan
from service.rag.retriever import AdvancedRagRetriever


class StubRecallRoute:
    def recall(self, plan, limit):
        from service.rag.models import RecallCandidate
        return [
            RecallCandidate(
                stable_key="dish:11",
                source_type="dish",
                source_id=11,
                route="sql",
                rank=1,
                score=1.0,
                facts={"dish_id": 11, "dish_name": "小炒黄牛肉", "merchant_id": 1, "merchant_name": "兰姨小炒", "price": 42.0, "cuisine_type": "湘菜", "flavor_profile": "鲜辣下饭", "allergens": [], "is_available": True, "merchant_rating": 4.7},
                citation="黄牛肉片现炒，芹菜和小米椒提香提辣。",
            )
        ]


def test_retriever_returns_grounded_evidence() -> None:
    retriever = AdvancedRagRetriever(recall_routes=[StubRecallRoute()])
    agent_plan = AgentPlan(
        intent="recommendation",
        normalized_query="辣的湘菜",
        requires_rag=True,
        filters={"cuisine_types": ["湘菜"], "flavor_preferences": ["辣"], "budget_max": None, "party_size": None, "exclude_allergens": []},
    )

    evidence = retriever.retrieve("帮我推荐几个比较辣的湘菜", agent_plan, memories=[], limit=3)

    assert evidence[0].facts["dish_name"] == "小炒黄牛肉"
    assert "湘菜" in evidence[0].why_matched
    assert evidence[0].citation
```

- [ ] **Step 2: Run recall and retriever tests to verify failure**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/service/rag/test_recall_routes.py tests/service/rag/test_retriever_pipeline.py -q
```

Expected: FAIL because recall and retriever modules do not exist.

- [ ] **Step 3: Create recall routes**

Create `service/rag/recall.py`:

```python
from __future__ import annotations

from service.catalog_service import CatalogService
from service.rag.models import RagQueryPlan, RecallCandidate
from tools.assistant_vector_store import AssistantVectorStore


class DenseVectorRecallRoute:
    def __init__(self, vector_store: AssistantVectorStore | None = None) -> None:
        self.vector_store = vector_store or AssistantVectorStore()

    def recall(self, plan: RagQueryPlan, limit: int) -> list[RecallCandidate]:
        if not self.vector_store.is_ready():
            return []
        candidates = []
        rank = 1
        for query in plan.expansion_queries or [plan.normalized_query]:
            for namespace in ("dishes", "merchants"):
                if namespace == "dishes" and "dish" not in plan.source_types:
                    continue
                if namespace == "merchants" and "merchant" not in plan.source_types:
                    continue
                for match in self.vector_store.semantic_search(query, top_k=limit, namespace=namespace):
                    metadata = match.get("metadata", {})
                    source_type = metadata.get("source_type", "dish")
                    source_id = int(metadata.get("source_id") or metadata.get("dish_id") or metadata.get("merchant_id"))
                    candidates.append(
                        RecallCandidate(
                            stable_key=f"{source_type}:{source_id}",
                            source_type=source_type,
                            source_id=source_id,
                            route="dense",
                            rank=rank,
                            score=float(match.get("score", 0.0)),
                            facts=dict(metadata),
                            citation=str(metadata.get("content", ""))[:180],
                        )
                    )
                    rank += 1
        return candidates[:limit]


class SqlCatalogRecallRoute:
    def __init__(self, catalog_service: CatalogService) -> None:
        self.catalog_service = catalog_service

    def recall(self, plan: RagQueryPlan, limit: int) -> list[RecallCandidate]:
        candidates = []
        cuisine_types = set(plan.should_filters.get("cuisine_types") or [])
        flavor_preferences = plan.should_filters.get("flavor_preferences") or []
        source_types = set(plan.source_types)

        rank = 1
        for merchant in self.catalog_service.list_merchants():
            if "merchant" in source_types:
                candidates.append(
                    RecallCandidate(
                        stable_key=f"merchant:{merchant['id']}",
                        source_type="merchant",
                        source_id=merchant["id"],
                        route="sql",
                        rank=rank,
                        score=float(merchant.get("rating") or 0.0) / 5.0,
                        facts={**merchant, "merchant_id": merchant["id"], "merchant_name": merchant["name"], "is_available": True},
                        citation=merchant.get("description", ""),
                    )
                )
                rank += 1
            if "dish" not in source_types:
                continue
            for dish in self.catalog_service.list_dishes_by_merchant(merchant["id"]):
                if cuisine_types and dish.get("cuisine_type") not in cuisine_types and merchant.get("homepage_category") not in cuisine_types:
                    continue
                text = " ".join([dish.get("name", ""), dish.get("description", ""), dish.get("flavor_profile", ""), dish.get("cuisine_type", "")])
                if flavor_preferences and not any(pref in text for pref in flavor_preferences):
                    continue
                candidates.append(
                    RecallCandidate(
                        stable_key=f"dish:{dish['id']}",
                        source_type="dish",
                        source_id=dish["id"],
                        route="sql",
                        rank=rank,
                        score=1.0,
                        facts={
                            **dish,
                            "dish_id": dish["id"],
                            "dish_name": dish["name"],
                            "merchant_id": merchant["id"],
                            "merchant_name": merchant["name"],
                            "merchant_rating": merchant.get("rating", 0.0),
                            "is_available": dish.get("is_available", True),
                        },
                        citation=dish.get("description", ""),
                    )
                )
                rank += 1
        return candidates[:limit]


class BusinessRecallRoute:
    def __init__(self, catalog_service: CatalogService) -> None:
        self.catalog_service = catalog_service

    def recall(self, plan: RagQueryPlan, limit: int) -> list[RecallCandidate]:
        candidates = []
        rank = 1
        for merchant in self.catalog_service.list_merchants():
            for dish in self.catalog_service.list_dishes_by_merchant(merchant["id"]):
                if not dish.get("is_recommended"):
                    continue
                candidates.append(
                    RecallCandidate(
                        stable_key=f"dish:{dish['id']}",
                        source_type="dish",
                        source_id=dish["id"],
                        route="business",
                        rank=rank,
                        score=float(merchant.get("rating") or 0.0) / 5.0,
                        facts={**dish, "dish_id": dish["id"], "dish_name": dish["name"], "merchant_id": merchant["id"], "merchant_name": merchant["name"], "merchant_rating": merchant.get("rating", 0.0), "is_available": True},
                        citation=dish.get("description", ""),
                    )
                )
                rank += 1
        return candidates[:limit]
```

- [ ] **Step 4: Create advanced retriever**

Create `service/rag/retriever.py`:

```python
from __future__ import annotations

from service.agent_runtime.state import AgentPlan
from service.catalog_service import CatalogService
from service.rag.diversifier import diversify
from service.rag.filters import apply_hard_filters
from service.rag.fusion import reciprocal_rank_fusion
from service.rag.models import FusedCandidate, RagEvidence
from service.rag.query_planner import RagQueryPlanner
from service.rag.recall import BusinessRecallRoute, DenseVectorRecallRoute, SqlCatalogRecallRoute
from service.rag.reranker import WeightedReranker


class AdvancedRagRetriever:
    def __init__(self, session=None, recall_routes=None, query_planner=None, reranker=None) -> None:
        catalog_service = CatalogService(session) if session is not None else None
        self.query_planner = query_planner or RagQueryPlanner()
        self.recall_routes = recall_routes or [
            DenseVectorRecallRoute(),
            SqlCatalogRecallRoute(catalog_service),
            BusinessRecallRoute(catalog_service),
        ]
        self.reranker = reranker or WeightedReranker()

    def retrieve(self, original_query: str, agent_plan: AgentPlan, memories: list[dict] | None = None, limit: int = 5) -> list[RagEvidence]:
        plan = self.query_planner.plan(original_query, agent_plan, memories or [])
        route_results = [route.recall(plan, limit=50) for route in self.recall_routes]
        fused = reciprocal_rank_fusion(route_results, limit=50)
        filtered = apply_hard_filters(fused, plan)
        ranked = self.reranker.rerank(filtered, original_query=original_query)
        merchant_scoped = bool(plan.must_filters.get("merchant_name"))
        diversified = diversify(ranked, limit=limit, merchant_scoped=merchant_scoped)
        return [self._to_evidence(item) for item in diversified]

    def _to_evidence(self, candidate: FusedCandidate) -> RagEvidence:
        facts = candidate.facts
        merchant_id = int(facts.get("merchant_id") or facts.get("id") or 0)
        if candidate.source_type == "dish":
            title = f"{facts.get('dish_name', facts.get('name', '菜品'))}｜{facts.get('merchant_name', '')}"
            why = [
                str(facts.get("cuisine_type", "")),
                str(facts.get("flavor_profile", "")),
                f"{float(facts.get('price', 0.0)):.0f}元" if facts.get("price") is not None else "",
            ]
        else:
            title = str(facts.get("merchant_name") or facts.get("name") or "商家")
            why = [str(item) for item in facts.get("merchant_tags", [])[:3]]

        return RagEvidence(
            source_type=candidate.source_type,
            source_id=candidate.source_id,
            merchant_id=merchant_id,
            title=title,
            facts=facts,
            why_matched=[item for item in why if item],
            citation=candidate.citation,
            score=candidate.final_score,
        )
```

- [ ] **Step 5: Run recall and retriever tests to verify pass**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/service/rag/test_recall_routes.py tests/service/rag/test_retriever_pipeline.py -q
```

Expected: PASS.

- [ ] **Step 6: Integrate recommendation and catalog tools**

Modify `service/tools/recommendation_tool.py` so it imports `AdvancedRagRetriever` and converts its `RagEvidence` objects to existing `ToolResult` evidence-compatible records. Use a helper that maps `RagEvidence` to `service.agent_state.EvidencePack`:

```python
from service.agent_state import EvidencePack, ToolResult
from service.rag.retriever import AdvancedRagRetriever


def _to_legacy_evidence(item):
    return EvidencePack(
        source_type=item.source_type,
        source_id=item.source_id,
        merchant_id=item.merchant_id,
        title=item.title,
        facts=item.facts,
        why_matched=item.why_matched,
        citation=item.citation,
        score=item.score,
    )
```

Inside `recommend_dishes_tool`, build an `AgentPlan` from structured arguments and call:

```python
retriever = _retriever or AdvancedRagRetriever(session=session)
rag_evidence = retriever.retrieve(full_message, agent_plan=agent_plan, memories=[], limit=int(limit or 3))
evidence = [_to_legacy_evidence(item) for item in rag_evidence]
```

Modify `service/tools/catalog_tool.py` the same way, with an `AgentPlan(intent="knowledge", requires_rag=True, normalized_query=query)`.

- [ ] **Step 7: Run assistant tool tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/service/test_assistant_tools.py tests/service/rag -q
```

Expected: PASS.

- [ ] **Step 8: Commit**

```powershell
git add service/rag/recall.py service/rag/retriever.py service/tools/recommendation_tool.py service/tools/catalog_tool.py tests/service/rag tests/service/test_assistant_tools.py
git commit -m "feat: integrate advanced rag retriever"
```

---

### Task 7: Add Action Journal Storage And Service

**Files:**
- Create: `api/models/action_journal.py`
- Modify: `api/models/__init__.py`
- Create: `database/migrations/versions/20260428_01_action_journal.py`
- Create: `repository/action_journal_repository.py`
- Create: `service/action_journal_service.py`
- Create: `tests/service/test_action_journal_service.py`

- [ ] **Step 1: Write failing action journal tests**

Create `tests/service/test_action_journal_service.py`:

```python
from service.action_journal_service import ActionJournalService


class InMemoryRepo:
    def __init__(self):
        self.records = []

    def create(self, **kwargs):
        record = {"id": len(self.records) + 1, **kwargs}
        self.records.append(record)
        return record

    def find_last_undoable(self, user_id):
        for record in reversed(self.records):
            if record["user_id"] == user_id and record["undo_policy"] != "not_undoable" and record["status"] == "completed":
                return record
        return None

    def mark_undone(self, action_id):
        for record in self.records:
            if record["action_id"] == action_id:
                record["status"] = "undone"
                return record
        return None


def test_action_journal_records_snapshot_action() -> None:
    service = ActionJournalService(repository=InMemoryRepo())

    record = service.record_completed_action(
        session_id="s1",
        user_id=9,
        action_type="cart_clear",
        undo_policy="snapshot_restore",
        before_snapshot={"items": [{"dish_id": 11, "quantity": 1}]},
        after_snapshot={"items": []},
        undo_tool="restore_cart_snapshot",
        natural_summary="清空购物车",
    )

    assert record["action_id"].startswith("act_")
    assert record["undo_policy"] == "snapshot_restore"


def test_action_journal_finds_last_undoable_action() -> None:
    repo = InMemoryRepo()
    service = ActionJournalService(repository=repo)
    service.record_completed_action("s1", 9, "cart_clear", "snapshot_restore", {"items": [1]}, {"items": []}, "restore_cart_snapshot", "清空购物车")

    record = service.find_last_undoable(user_id=9)

    assert record["action_type"] == "cart_clear"
```

- [ ] **Step 2: Run action journal tests to verify failure**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/service/test_action_journal_service.py -q
```

Expected: FAIL because `service.action_journal_service` does not exist.

- [ ] **Step 3: Create model and migration**

Create `api/models/action_journal.py`:

```python
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from api.db import Base


class ActionJournal(Base):
    __tablename__ = "action_journal"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    action_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    session_id: Mapped[str] = mapped_column(String(64), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    action_type: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(32), default="completed")
    undo_policy: Mapped[str] = mapped_column(String(64))
    undo_tool: Mapped[str] = mapped_column(String(128), default="")
    before_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    after_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    natural_summary: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```

Modify `api/models/__init__.py`:

```python
from api.models.action_journal import ActionJournal
```

Add `"ActionJournal"` to `__all__`.

Create `database/migrations/versions/20260428_01_action_journal.py`:

```python
from alembic import op
import sqlalchemy as sa


revision = "20260428_01"
down_revision = "20260422_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "action_journal",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("action_id", sa.String(length=64), nullable=False),
        sa.Column("session_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("action_type", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("undo_policy", sa.String(length=64), nullable=False),
        sa.Column("undo_tool", sa.String(length=128), nullable=False, server_default=""),
        sa.Column("before_snapshot", sa.JSON(), nullable=False),
        sa.Column("after_snapshot", sa.JSON(), nullable=False),
        sa.Column("natural_summary", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("action_id"),
    )
    op.create_index("ix_action_journal_action_id", "action_journal", ["action_id"], unique=True)
    op.create_index("ix_action_journal_session_id", "action_journal", ["session_id"])
    op.create_index("ix_action_journal_user_id", "action_journal", ["user_id"])
    op.create_index("ix_action_journal_action_type", "action_journal", ["action_type"])


def downgrade() -> None:
    op.drop_index("ix_action_journal_action_type", table_name="action_journal")
    op.drop_index("ix_action_journal_user_id", table_name="action_journal")
    op.drop_index("ix_action_journal_session_id", table_name="action_journal")
    op.drop_index("ix_action_journal_action_id", table_name="action_journal")
    op.drop_table("action_journal")
```

- [ ] **Step 4: Create repository and service**

Create `repository/action_journal_repository.py`:

```python
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.models.action_journal import ActionJournal


class ActionJournalRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(self, **kwargs) -> ActionJournal:
        record = ActionJournal(**kwargs)
        self.session.add(record)
        self.session.commit()
        self.session.refresh(record)
        return record

    def find_last_undoable(self, user_id: int) -> ActionJournal | None:
        statement = (
            select(ActionJournal)
            .where(
                ActionJournal.user_id == user_id,
                ActionJournal.status == "completed",
                ActionJournal.undo_policy != "not_undoable",
            )
            .order_by(ActionJournal.id.desc())
        )
        return self.session.scalar(statement)

    def mark_undone(self, action_id: str) -> ActionJournal | None:
        statement = select(ActionJournal).where(ActionJournal.action_id == action_id)
        record = self.session.scalar(statement)
        if record is None:
            return None
        record.status = "undone"
        self.session.commit()
        self.session.refresh(record)
        return record
```

Create `service/action_journal_service.py`:

```python
from __future__ import annotations

from uuid import uuid4

from repository.action_journal_repository import ActionJournalRepository


class ActionJournalService:
    def __init__(self, session=None, repository=None) -> None:
        self.repository = repository or ActionJournalRepository(session)

    def record_completed_action(
        self,
        session_id: str,
        user_id: int,
        action_type: str,
        undo_policy: str,
        before_snapshot: dict,
        after_snapshot: dict,
        undo_tool: str,
        natural_summary: str,
    ):
        return self.repository.create(
            action_id=f"act_{uuid4().hex[:12]}",
            session_id=session_id,
            user_id=user_id,
            action_type=action_type,
            status="completed",
            undo_policy=undo_policy,
            before_snapshot=before_snapshot,
            after_snapshot=after_snapshot,
            undo_tool=undo_tool,
            natural_summary=natural_summary,
        )

    def find_last_undoable(self, user_id: int):
        return self.repository.find_last_undoable(user_id)

    def mark_undone(self, action_id: str):
        return self.repository.mark_undone(action_id)
```

- [ ] **Step 5: Run action journal tests to verify pass**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/service/test_action_journal_service.py -q
```

Expected: PASS.

- [ ] **Step 6: Run model metadata tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_models_metadata.py tests/test_alembic_env.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

```powershell
git add api/models/action_journal.py api/models/__init__.py database/migrations/versions/20260428_01_action_journal.py repository/action_journal_repository.py service/action_journal_service.py tests/service/test_action_journal_service.py
git commit -m "feat: add action journal for undoable actions"
```

---

### Task 8: Add Direct Local Actions And Undo Tools

**Files:**
- Modify: `service/tools/cart_tool.py`
- Modify: `service/tools/address_tool.py`
- Create: `service/tools/preference_tool.py`
- Create: `tests/service/test_undo_tools.py`

- [ ] **Step 1: Write failing undo tool tests**

Create `tests/service/test_undo_tools.py`:

```python
from service.tools.cart_tool import clear_cart_tool, restore_cart_snapshot_tool


class StubCartService:
    def __init__(self):
        self.cart = {
            "items": [
                {"merchant_id": 1, "merchant_name": "兰姨小炒", "items": [{"dish_id": 11, "dish_name": "小炒黄牛肉", "quantity": 2, "unit_price": 42.0}], "subtotal": 84.0}
            ],
            "goods_amount": 84.0,
        }
        self.added = []
        self.removed = []

    def get_grouped_cart(self, user_id):
        return self.cart

    def remove_item(self, user_id, dish_id):
        self.removed.append(dish_id)
        self.cart = {"items": [], "goods_amount": 0}
        return {"success": True, "dish_id": dish_id}

    def add_item(self, user_id, payload):
        self.added.append({"dish_id": payload.dish_id, "quantity": payload.quantity})
        return {"success": True, "dish_id": payload.dish_id, "quantity": payload.quantity}


def test_clear_cart_tool_returns_before_and_after_snapshots() -> None:
    service = StubCartService()

    result = clear_cart_tool(user_id=9, _cart_service=service)

    assert result["success"] is True
    assert result["before_snapshot"]["items"][0]["items"][0]["dish_id"] == 11
    assert result["after_snapshot"]["items"] == []


def test_restore_cart_snapshot_readds_previous_items() -> None:
    service = StubCartService()
    snapshot = {"items": [{"merchant_id": 1, "items": [{"dish_id": 11, "quantity": 2}]}]}

    result = restore_cart_snapshot_tool(user_id=9, snapshot=snapshot, _cart_service=service)

    assert result["success"] is True
    assert service.added == [{"dish_id": 11, "quantity": 2}]
```

- [ ] **Step 2: Run undo tool tests to verify failure**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/service/test_undo_tools.py -q
```

Expected: FAIL because `clear_cart_tool` and `restore_cart_snapshot_tool` do not exist.

- [ ] **Step 3: Add cart clear and restore tools**

Modify `service/tools/cart_tool.py`:

```python
def clear_cart_tool(user_id: int, session=None, _cart_service=None) -> dict:
    service = _cart_service or CartService(session)
    before_snapshot = service.get_grouped_cart(user_id)
    for group in before_snapshot.get("items", []):
        for item in group.get("items", []):
            service.remove_item(user_id, int(item["dish_id"]))
    after_snapshot = service.get_grouped_cart(user_id)
    return {
        "success": True,
        "before_snapshot": before_snapshot,
        "after_snapshot": after_snapshot,
        "undo_policy": "snapshot_restore",
        "undo_tool": "restore_cart_snapshot",
        "natural_summary": "清空购物车",
    }


def restore_cart_snapshot_tool(user_id: int, snapshot: dict, session=None, _cart_service=None) -> dict:
    service = _cart_service or CartService(session)
    restored = []
    for group in snapshot.get("items", []):
        for item in group.get("items", []):
            payload = SimpleNamespace(
                dish_id=int(item["dish_id"]),
                quantity=int(item.get("quantity", 1)),
            )
            restored.append(service.add_item(user_id, payload))
    return {"success": True, "restored": restored}
```

- [ ] **Step 4: Create preference tool skeleton**

Create `service/tools/preference_tool.py`:

```python
from __future__ import annotations


def upsert_preference_tool(user_id: int, memory_type: str, content: str, session=None, _memory_service=None) -> dict:
    service = _memory_service
    if service is None:
        from service.user_memory_service import UserMemoryService
        service = UserMemoryService(session)
    before_snapshot = service.list_memories(user_id)
    memory = service.upsert_memory(user_id=user_id, memory_type=memory_type, content=content, confidence=1.0)
    after_snapshot = service.list_memories(user_id)
    return {
        "success": True,
        "memory": memory,
        "before_snapshot": before_snapshot,
        "after_snapshot": after_snapshot,
        "undo_policy": "snapshot_restore",
        "undo_tool": "restore_user_memory_snapshot",
        "natural_summary": "更新用户偏好",
    }
```

- [ ] **Step 5: Run undo tool tests to verify pass**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/service/test_undo_tools.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add service/tools/cart_tool.py service/tools/address_tool.py service/tools/preference_tool.py tests/service/test_undo_tools.py
git commit -m "feat: add direct local action undo tools"
```

---

### Task 9: Add User Memory Storage

**Files:**
- Create: `api/models/user_memory.py`
- Modify: `api/models/__init__.py`
- Create: `database/migrations/versions/20260428_02_user_memory.py`
- Create: `repository/user_memory_repository.py`
- Create: `service/user_memory_service.py`
- Create: `tests/service/test_user_memory_service.py`

- [ ] **Step 1: Write failing user memory tests**

Create `tests/service/test_user_memory_service.py`:

```python
from service.user_memory_service import UserMemoryService


class InMemoryRepo:
    def __init__(self):
        self.records = []

    def list_for_user(self, user_id):
        return [record for record in self.records if record["user_id"] == user_id and record["status"] == "active"]

    def upsert(self, user_id, memory_type, content, confidence):
        for record in self.records:
            if record["user_id"] == user_id and record["memory_type"] == memory_type and record["content"] == content:
                record["confidence"] = confidence
                return record
        record = {"id": len(self.records) + 1, "user_id": user_id, "memory_type": memory_type, "content": content, "confidence": confidence, "status": "active"}
        self.records.append(record)
        return record


def test_user_memory_upserts_structured_preference() -> None:
    service = UserMemoryService(repository=InMemoryRepo())

    memory = service.upsert_memory(9, "food_preference", "prefers spicy Hunan dishes", 0.9)

    assert memory["memory_type"] == "food_preference"
    assert service.list_memories(9)[0]["content"] == "prefers spicy Hunan dishes"
```

- [ ] **Step 2: Run user memory tests to verify failure**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/service/test_user_memory_service.py -q
```

Expected: FAIL because `service.user_memory_service` does not exist.

- [ ] **Step 3: Create user memory model and migration**

Create `api/models/user_memory.py`:

```python
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from api.db import Base


class UserMemory(Base):
    __tablename__ = "user_memories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    memory_type: Mapped[str] = mapped_column(String(64), index=True)
    content: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    status: Mapped[str] = mapped_column(String(32), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```

Create `database/migrations/versions/20260428_02_user_memory.py`:

```python
from alembic import op
import sqlalchemy as sa


revision = "20260428_02"
down_revision = "20260428_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_memories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("memory_type", sa.String(length=64), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_user_memories_user_id", "user_memories", ["user_id"])
    op.create_index("ix_user_memories_memory_type", "user_memories", ["memory_type"])


def downgrade() -> None:
    op.drop_index("ix_user_memories_memory_type", table_name="user_memories")
    op.drop_index("ix_user_memories_user_id", table_name="user_memories")
    op.drop_table("user_memories")
```

- [ ] **Step 4: Create repository and service**

Create `repository/user_memory_repository.py`:

```python
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from api.models.user_memory import UserMemory


class UserMemoryRepository:
    def __init__(self, session: Session):
        self.session = session

    def list_for_user(self, user_id: int) -> list[UserMemory]:
        statement = (
            select(UserMemory)
            .where(UserMemory.user_id == user_id, UserMemory.status == "active")
            .order_by(UserMemory.updated_at.desc(), UserMemory.id.desc())
        )
        return list(self.session.scalars(statement))

    def upsert(self, user_id: int, memory_type: str, content: str, confidence: float):
        statement = select(UserMemory).where(
            UserMemory.user_id == user_id,
            UserMemory.memory_type == memory_type,
            UserMemory.content == content,
            UserMemory.status == "active",
        )
        record = self.session.scalar(statement)
        if record is None:
            record = UserMemory(user_id=user_id, memory_type=memory_type, content=content, confidence=confidence)
            self.session.add(record)
        else:
            record.confidence = confidence
            record.updated_at = datetime.utcnow()
        self.session.commit()
        self.session.refresh(record)
        return record
```

Create `service/user_memory_service.py`:

```python
from __future__ import annotations

from repository.user_memory_repository import UserMemoryRepository


class UserMemoryService:
    def __init__(self, session=None, repository=None) -> None:
        self.repository = repository or UserMemoryRepository(session)

    def _serialize(self, record) -> dict:
        if isinstance(record, dict):
            return dict(record)
        return {
            "id": record.id,
            "user_id": record.user_id,
            "memory_type": record.memory_type,
            "content": record.content,
            "confidence": record.confidence,
            "status": record.status,
        }

    def list_memories(self, user_id: int) -> list[dict]:
        return [self._serialize(record) for record in self.repository.list_for_user(user_id)]

    def upsert_memory(self, user_id: int, memory_type: str, content: str, confidence: float) -> dict:
        return self._serialize(self.repository.upsert(user_id, memory_type, content, confidence))
```

Modify `api/models/__init__.py`:

```python
from api.models.user_memory import UserMemory
```

Add `"UserMemory"` to `__all__`.

- [ ] **Step 5: Run user memory tests to verify pass**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/service/test_user_memory_service.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add api/models/user_memory.py api/models/__init__.py database/migrations/versions/20260428_02_user_memory.py repository/user_memory_repository.py service/user_memory_service.py tests/service/test_user_memory_service.py
git commit -m "feat: add structured user memory store"
```

---

### Task 10: Build LangGraph Nodes And Graph Wiring

**Files:**
- Create: `service/agent_runtime/nodes.py`
- Create: `service/agent_runtime/graph.py`
- Create: `tests/service/test_langgraph_agent_graph.py`

- [ ] **Step 1: Write failing graph tests**

Create `tests/service/test_langgraph_agent_graph.py`:

```python
from langchain_core.messages import HumanMessage

from service.agent_runtime.graph import build_agent_graph
from service.agent_runtime.state import AgentPlan


class StubPlanner:
    def plan(self, message, context):
        return AgentPlan(intent="recommendation", normalized_query="辣的湘菜", requires_rag=True)


class StubRetriever:
    def retrieve(self, original_query, agent_plan, memories, limit):
        return [
            type("Evidence", (), {
                "source_type": "dish",
                "source_id": 11,
                "merchant_id": 1,
                "title": "小炒黄牛肉｜兰姨小炒",
                "facts": {"dish_id": 11, "dish_name": "小炒黄牛肉", "merchant_name": "兰姨小炒", "price": 42.0},
                "why_matched": ["湘菜", "鲜辣下饭"],
                "citation": "黄牛肉片现炒",
                "score": 0.9,
            })()
        ]


def test_graph_returns_recommendation_response() -> None:
    graph = build_agent_graph(planner=StubPlanner(), retriever=StubRetriever())
    result = graph.invoke(
        {"messages": [HumanMessage(content="帮我推荐几个比较辣的湘菜")], "session_id": "s1", "user_id": 9},
        config={"configurable": {"thread_id": "s1"}},
    )

    assert result["response_payload"]["response_type"] == "recommendation"
    assert result["response_payload"]["recommendations"][0]["dish_name"] == "小炒黄牛肉"
```

- [ ] **Step 2: Run graph tests to verify failure**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/service/test_langgraph_agent_graph.py -q
```

Expected: FAIL because graph module does not exist.

- [ ] **Step 3: Create graph nodes**

Create `service/agent_runtime/nodes.py`:

```python
from __future__ import annotations

from langchain_core.messages import AIMessage, HumanMessage

from service.agent_runtime.planner import LangGraphAgentPlanner
from service.rag.retriever import AdvancedRagRetriever


def latest_user_message(state: dict) -> str:
    for message in reversed(state.get("messages", [])):
        if isinstance(message, HumanMessage):
            return str(message.content)
    return ""


def plan_node(state: dict, planner: LangGraphAgentPlanner) -> dict:
    user_message = latest_user_message(state)
    plan = planner.plan(
        user_message,
        {
            "session_id": state.get("session_id"),
            "user_id": state.get("user_id"),
            "loaded_user_memories": state.get("loaded_user_memories", []),
            "recent_action_ids": state.get("recent_action_ids", []),
        },
    )
    return {"current_plan": plan}


def route_after_plan(state: dict) -> str:
    plan = state.get("current_plan")
    if plan is None:
        return "respond"
    if plan.intent == "undo_action":
        return "undo"
    if plan.tool_calls:
        return "action"
    if plan.requires_rag:
        return "rag"
    return "respond"


def rag_node(state: dict, retriever: AdvancedRagRetriever) -> dict:
    user_message = latest_user_message(state)
    evidence = retriever.retrieve(
        user_message,
        agent_plan=state["current_plan"],
        memories=state.get("loaded_user_memories", []),
        limit=3,
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
    return {"recent_evidence": serialized}


def action_node(state: dict) -> dict:
    return {"tool_results": [{"success": False, "message": "action node not configured"}]}


def undo_node(state: dict) -> dict:
    return {"tool_results": [{"success": False, "message": "undo node not configured"}]}


def respond_node(state: dict) -> dict:
    plan = state.get("current_plan")
    evidence = state.get("recent_evidence", [])
    response_type = plan.intent if plan else "unsupported"
    recommendations = []
    citations = []
    for item in evidence:
        facts = item.get("facts", {})
        if item.get("source_type") == "dish":
            recommendations.append({
                "source_type": "dish",
                "merchant_id": item.get("merchant_id"),
                "merchant_name": facts.get("merchant_name", ""),
                "dish_id": facts.get("dish_id"),
                "dish_name": facts.get("dish_name"),
                "price": facts.get("price"),
                "reason": "、".join(item.get("why_matched", [])),
            })
        citations.append({
            "source_type": item.get("source_type"),
            "source_id": item.get("source_id"),
            "title": item.get("title"),
            "snippet": item.get("citation", ""),
        })

    if recommendations:
        message = "结合商家数据和匹配理由，我推荐：\n" + "\n".join(
            f"{index}. {item['dish_name']}（{item['merchant_name']}）"
            for index, item in enumerate(recommendations, start=1)
        )
    elif response_type == "greeting":
        message = "你好！我是你的智能点餐助手。"
    else:
        message = "我没有找到足够匹配的结果，可以换个说法再试。"

    payload = {
        "session_id": state.get("session_id"),
        "message": message,
        "response_type": response_type,
        "needs_clarification": False,
        "clarification_question": None,
        "extracted_constraints": None,
        "recommendations": recommendations,
        "comparisons": [],
        "citations": citations,
        "suggested_actions": [],
        "pending_action": None,
        "executed_actions": state.get("tool_results", []),
        "undo_available": bool(state.get("recent_action_ids")),
    }
    return {"messages": state.get("messages", []) + [AIMessage(content=message)], "response_payload": payload}
```

- [ ] **Step 4: Create graph builder**

Create `service/agent_runtime/graph.py`:

```python
from __future__ import annotations

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, StateGraph

from service.agent_runtime.nodes import action_node, plan_node, rag_node, respond_node, route_after_plan, undo_node
from service.agent_runtime.planner import LangGraphAgentPlanner
from service.agent_runtime.state import SmartOrderAgentState
from service.rag.retriever import AdvancedRagRetriever


def build_agent_graph(planner=None, retriever=None, checkpointer=None):
    planner = planner or LangGraphAgentPlanner()
    retriever = retriever or AdvancedRagRetriever()
    checkpointer = checkpointer or InMemorySaver()

    workflow = StateGraph(SmartOrderAgentState)
    workflow.add_node("plan", lambda state: plan_node(state, planner))
    workflow.add_node("rag", lambda state: rag_node(state, retriever))
    workflow.add_node("action", action_node)
    workflow.add_node("undo", undo_node)
    workflow.add_node("respond", respond_node)

    workflow.set_entry_point("plan")
    workflow.add_conditional_edges(
        "plan",
        route_after_plan,
        {
            "rag": "rag",
            "action": "action",
            "undo": "undo",
            "respond": "respond",
        },
    )
    workflow.add_edge("rag", "respond")
    workflow.add_edge("action", "respond")
    workflow.add_edge("undo", "respond")
    workflow.add_edge("respond", END)
    return workflow.compile(checkpointer=checkpointer)
```

- [ ] **Step 5: Run graph tests to verify pass**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/service/test_langgraph_agent_graph.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add service/agent_runtime/nodes.py service/agent_runtime/graph.py tests/service/test_langgraph_agent_graph.py
git commit -m "feat: add langgraph assistant runtime"
```

---

### Task 11: Delegate AssistantService To LangGraph Runtime

**Files:**
- Modify: `service/assistant_service.py`
- Modify: `api/schemas.py`
- Create: `tests/service/test_assistant_service_langgraph.py`
- Modify: `tests/api/test_assistant_routes.py`

- [ ] **Step 1: Write failing AssistantService delegation test**

Create `tests/service/test_assistant_service_langgraph.py`:

```python
from api.schemas import AssistantChatRequest
from service.assistant_service import AssistantService


class StubGraph:
    def __init__(self):
        self.calls = []

    def invoke(self, state, config):
        self.calls.append((state, config))
        return {
            "response_payload": {
                "session_id": state["session_id"],
                "message": "推荐结果",
                "response_type": "recommendation",
                "needs_clarification": False,
                "clarification_question": None,
                "extracted_constraints": None,
                "recommendations": [],
                "comparisons": [],
                "citations": [],
                "suggested_actions": [],
                "pending_action": None,
                "executed_actions": [],
                "undo_available": False,
            }
        }


def test_assistant_service_invokes_langgraph_runtime() -> None:
    graph = StubGraph()
    service = AssistantService(session=None)
    service._graph = graph

    response = service.chat(AssistantChatRequest(message="推荐几个湘菜", session_id="s1", user_id=9))

    assert response["message"] == "推荐结果"
    assert graph.calls[0][1]["configurable"]["thread_id"] == "s1"
```

- [ ] **Step 2: Run delegation test to verify failure**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/service/test_assistant_service_langgraph.py -q
```

Expected: FAIL because `AssistantService` does not use `_graph`.

- [ ] **Step 3: Extend response schema without breaking old fields**

Modify `api/schemas.py` `AssistantChatResponse`:

```python
    undo_available: bool = False
```

If a dedicated action summary model is added, keep it optional and keep existing `executed_actions` intact.

- [ ] **Step 4: Delegate service chat to graph**

Modify `service/assistant_service.py`:

```python
from langchain_core.messages import HumanMessage
from service.agent_runtime.graph import build_agent_graph
```

Inside `AssistantService.__init__`:

```python
self._graph = build_agent_graph()
```

Replace the `AssistantChatRequest` branch in `chat`:

```python
def chat(self, request: AssistantChatRequest) -> AssistantChatResponse:
    if not isinstance(request, AssistantChatRequest):
        return self._legacy_chat(request)

    session_id = request.session_id or self.session_store.get_or_create(None, user_id=request.user_id).session_id
    result = self._graph.invoke(
        {
            "messages": [HumanMessage(content=request.message)],
            "session_id": session_id,
            "user_id": request.user_id,
            "loaded_user_memories": [],
            "recent_evidence": [],
            "recent_action_ids": [],
            "tool_results": [],
        },
        config={"configurable": {"thread_id": session_id}},
    )
    return result["response_payload"]
```

- [ ] **Step 5: Run service and route tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/service/test_assistant_service_langgraph.py tests/api/test_assistant_routes.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add service/assistant_service.py api/schemas.py tests/service/test_assistant_service_langgraph.py tests/api/test_assistant_routes.py
git commit -m "feat: route assistant chat through langgraph"
```

---

### Task 12: Wire Action Journal Into Graph Actions And Undo

**Files:**
- Modify: `service/agent_runtime/nodes.py`
- Modify: `service/agent_runtime/graph.py`
- Create: `tests/service/test_langgraph_undo_flow.py`

- [ ] **Step 1: Write failing undo flow test**

Create `tests/service/test_langgraph_undo_flow.py`:

```python
from langchain_core.messages import HumanMessage

from service.agent_runtime.graph import build_agent_graph
from service.agent_runtime.state import AgentPlan, GraphToolCall


class SequencePlanner:
    def __init__(self):
        self.calls = 0

    def plan(self, message, context):
        self.calls += 1
        if self.calls == 1:
            return AgentPlan(intent="cart_action", tool_calls=[GraphToolCall("cart_clear", {}, True)])
        return AgentPlan(intent="undo_action", tool_calls=[GraphToolCall("undo_last_action", {}, True)])


class StubActionExecutor:
    def __init__(self):
        self.undone = False

    def execute_action(self, plan, state):
        return {"success": True, "action_id": "act_1", "message": "清空购物车", "undo_available": True}

    def undo_last(self, state):
        self.undone = True
        return {"success": True, "action_id": "act_1", "message": "已撤回清空购物车"}


def test_graph_executes_action_then_undo() -> None:
    executor = StubActionExecutor()
    graph = build_agent_graph(planner=SequencePlanner(), action_executor=executor)

    first = graph.invoke({"messages": [HumanMessage(content="清空购物车")], "session_id": "s1", "user_id": 9}, config={"configurable": {"thread_id": "s1"}})
    second = graph.invoke({"messages": [HumanMessage(content="撤回刚才的操作")], "session_id": "s1", "user_id": 9, "recent_action_ids": ["act_1"]}, config={"configurable": {"thread_id": "s1"}})

    assert first["response_payload"]["undo_available"] is True
    assert second["response_payload"]["executed_actions"][0]["success"] is True
    assert executor.undone is True
```

- [ ] **Step 2: Run undo flow test to verify failure**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/service/test_langgraph_undo_flow.py -q
```

Expected: FAIL because `build_agent_graph` does not accept `action_executor`.

- [ ] **Step 3: Add action executor interface**

Create implementation inside `service/agent_runtime/nodes.py`:

```python
class LocalActionExecutor:
    def __init__(self, session=None):
        self.session = session

    def execute_action(self, plan, state):
        from service.action_journal_service import ActionJournalService
        from service.tools.cart_tool import clear_cart_tool

        user_id = state.get("user_id")
        session_id = state.get("session_id")
        call = plan.tool_calls[0]
        if call.tool_name == "cart_clear":
            result = clear_cart_tool(user_id=user_id, session=self.session)
            journal = ActionJournalService(self.session).record_completed_action(
                session_id=session_id,
                user_id=user_id,
                action_type="cart_clear",
                undo_policy=result["undo_policy"],
                before_snapshot=result["before_snapshot"],
                after_snapshot=result["after_snapshot"],
                undo_tool=result["undo_tool"],
                natural_summary=result["natural_summary"],
            )
            action_id = journal["action_id"] if isinstance(journal, dict) else journal.action_id
            return {"success": True, "action_id": action_id, "message": result["natural_summary"], "undo_available": True}
        return {"success": False, "message": f"unsupported action tool: {call.tool_name}", "undo_available": False}

    def undo_last(self, state):
        from service.action_journal_service import ActionJournalService
        from service.tools.cart_tool import restore_cart_snapshot_tool

        user_id = state.get("user_id")
        journal = ActionJournalService(self.session)
        record = journal.find_last_undoable(user_id)
        if record is None:
            return {"success": False, "message": "没有可撤回的操作"}
        action_type = record["action_type"] if isinstance(record, dict) else record.action_type
        before_snapshot = record["before_snapshot"] if isinstance(record, dict) else record.before_snapshot
        action_id = record["action_id"] if isinstance(record, dict) else record.action_id
        if action_type == "cart_clear":
            restore_cart_snapshot_tool(user_id=user_id, snapshot=before_snapshot, session=self.session)
            journal.mark_undone(action_id)
            return {"success": True, "action_id": action_id, "message": "已撤回清空购物车"}
        return {"success": False, "message": f"该操作暂不支持撤回: {action_type}"}
```

Modify `action_node` and `undo_node`:

```python
def action_node(state: dict, action_executor=None) -> dict:
    executor = action_executor or LocalActionExecutor()
    result = executor.execute_action(state["current_plan"], state)
    recent_ids = list(state.get("recent_action_ids", []))
    if result.get("action_id"):
        recent_ids.append(result["action_id"])
    return {"tool_results": [result], "recent_action_ids": recent_ids}


def undo_node(state: dict, action_executor=None) -> dict:
    executor = action_executor or LocalActionExecutor()
    result = executor.undo_last(state)
    return {"tool_results": [result]}
```

Modify `service/agent_runtime/graph.py`:

```python
def build_agent_graph(planner=None, retriever=None, action_executor=None, checkpointer=None):
```

Use:

```python
workflow.add_node("action", lambda state: action_node(state, action_executor))
workflow.add_node("undo", lambda state: undo_node(state, action_executor))
```

- [ ] **Step 4: Run undo flow test to verify pass**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/service/test_langgraph_undo_flow.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add service/agent_runtime/nodes.py service/agent_runtime/graph.py tests/service/test_langgraph_undo_flow.py
git commit -m "feat: wire undoable actions into graph"
```

---

### Task 13: Add Memory Writer Node And User Memory Loading

**Files:**
- Modify: `service/agent_runtime/nodes.py`
- Modify: `service/agent_runtime/graph.py`
- Modify: `service/assistant_service.py`
- Create: `tests/service/test_agent_memory_flow.py`

- [ ] **Step 1: Write failing memory flow tests**

Create `tests/service/test_agent_memory_flow.py`:

```python
from service.agent_runtime.nodes import load_memory_node, memory_writer_node


class StubMemoryService:
    def __init__(self):
        self.saved = []

    def list_memories(self, user_id):
        return [{"memory_type": "food_preference", "content": "prefers spicy Hunan dishes", "confidence": 0.9}]

    def upsert_memory(self, user_id, memory_type, content, confidence):
        self.saved.append({"user_id": user_id, "memory_type": memory_type, "content": content, "confidence": confidence})
        return self.saved[-1]


def test_load_memory_node_loads_user_memories() -> None:
    state = {"user_id": 9}

    result = load_memory_node(state, memory_service=StubMemoryService())

    assert result["loaded_user_memories"][0]["content"] == "prefers spicy Hunan dishes"


def test_memory_writer_saves_high_confidence_memory_candidates() -> None:
    state = {"user_id": 9, "memory_candidates": [{"memory_type": "food_preference", "content": "prefers spicy Hunan dishes", "confidence": 0.9}]}
    service = StubMemoryService()

    memory_writer_node(state, memory_service=service)

    assert service.saved[0]["content"] == "prefers spicy Hunan dishes"
```

- [ ] **Step 2: Run memory flow tests to verify failure**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/service/test_agent_memory_flow.py -q
```

Expected: FAIL because memory node functions do not exist.

- [ ] **Step 3: Add memory nodes**

Modify `service/agent_runtime/nodes.py`:

```python
def load_memory_node(state: dict, memory_service=None) -> dict:
    user_id = state.get("user_id")
    if user_id is None:
        return {"loaded_user_memories": []}
    if memory_service is None:
        from service.user_memory_service import UserMemoryService
        memory_service = UserMemoryService()
    return {"loaded_user_memories": memory_service.list_memories(user_id)}


def memory_writer_node(state: dict, memory_service=None) -> dict:
    user_id = state.get("user_id")
    if user_id is None:
        return {}
    if memory_service is None:
        from service.user_memory_service import UserMemoryService
        memory_service = UserMemoryService()
    saved = []
    for candidate in state.get("memory_candidates", []):
        if float(candidate.get("confidence", 0.0)) < 0.75:
            continue
        saved.append(
            memory_service.upsert_memory(
                user_id=user_id,
                memory_type=candidate["memory_type"],
                content=candidate["content"],
                confidence=float(candidate["confidence"]),
            )
        )
    return {"saved_memories": saved}
```

- [ ] **Step 4: Wire memory nodes into graph**

Modify `service/agent_runtime/graph.py`:

```python
from service.agent_runtime.nodes import load_memory_node, memory_writer_node
```

Add parameters:

```python
def build_agent_graph(planner=None, retriever=None, action_executor=None, memory_service=None, checkpointer=None):
```

Add nodes and edges:

```python
workflow.add_node("load_memory", lambda state: load_memory_node(state, memory_service))
workflow.add_node("write_memory", lambda state: memory_writer_node(state, memory_service))
workflow.set_entry_point("load_memory")
workflow.add_edge("load_memory", "plan")
workflow.add_edge("respond", "write_memory")
workflow.add_edge("write_memory", END)
```

Remove the direct `respond -> END` edge.

- [ ] **Step 5: Run memory and graph tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/service/test_agent_memory_flow.py tests/service/test_langgraph_agent_graph.py tests/service/test_langgraph_undo_flow.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add service/agent_runtime/nodes.py service/agent_runtime/graph.py service/assistant_service.py tests/service/test_agent_memory_flow.py
git commit -m "feat: add agent memory loading and writing"
```

---

### Task 14: Expand RAG Evaluation Metrics And Cases

**Files:**
- Modify: `tools/evaluate_assistant_rag.py`
- Modify: `tests/eval/assistant_rag_cases.jsonl`
- Create: `tests/service/rag/test_rag_metrics.py`

- [ ] **Step 1: Write failing metric tests**

Create `tests/service/rag/test_rag_metrics.py`:

```python
from tools.evaluate_assistant_rag import evaluate_cases


class Evidence:
    def __init__(self, source_id, source_type="dish", facts=None, title=""):
        self.source_id = source_id
        self.source_type = source_type
        self.facts = facts or {}
        self.title = title
        self.citation = "citation"
        self.why_matched = ["match"]


class Retriever:
    def retrieve(self, query, limit=5):
        return [
            Evidence(1, facts={"merchant_id": 1, "dish_name": "A", "cuisine_type": "湘菜"}),
            Evidence(2, facts={"merchant_id": 1, "dish_name": "B", "cuisine_type": "湘菜"}),
            Evidence(3, facts={"merchant_id": 2, "dish_name": "C", "cuisine_type": "湘菜"}),
        ]


def test_evaluator_reports_diversity_and_citation_coverage() -> None:
    cases = [{"query": "湘菜", "expected_source_type": "dish", "constraints": {"allowed_cuisine_types": ["湘菜"]}}]

    metrics = evaluate_cases(cases, Retriever())

    assert "diversity_pass_rate" in metrics
    assert "citation_coverage" in metrics
    assert metrics["citation_coverage"] == 1.0
```

- [ ] **Step 2: Run metric tests to verify failure**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/service/rag/test_rag_metrics.py -q
```

Expected: FAIL because metrics are not reported.

- [ ] **Step 3: Add diversity and citation metrics**

Modify `tools/evaluate_assistant_rag.py`:

```python
def _passes_diversity(evidence: list) -> bool:
    merchant_ids = [getattr(item, "facts", {}).get("merchant_id") for item in evidence if getattr(item, "source_type", "") == "dish"]
    merchant_ids = [item for item in merchant_ids if item is not None]
    if len(merchant_ids) <= 1:
        return True
    return len(set(merchant_ids[:3])) >= min(2, len(set(merchant_ids)))


def _has_citation(evidence) -> bool:
    return bool(str(getattr(evidence, "citation", "")).strip())
```

Inside `evaluate_cases` initialize:

```python
diversity_passes = 0
citation_scores = []
```

After retrieval:

```python
diversity_passes += int(_passes_diversity(evidence))
citation_scores.append(sum(1 for item in evidence if _has_citation(item)) / len(evidence) if evidence else 0.0)
```

Add metrics:

```python
"diversity_pass_rate": diversity_passes / case_count if case_count else 0.0,
"citation_coverage": sum(citation_scores) / case_count if case_count else 0.0,
```

- [ ] **Step 4: Expand evaluation cases**

Append cases to `tests/eval/assistant_rag_cases.jsonl`:

```jsonl
{"id":"spicy_hunan_direct","query":"帮我推荐几个比较辣的湘菜","expected_source_type":"dish","constraints":{"allowed_cuisine_types":["湘菜","川湘"],"required_keywords":["辣"]}}
{"id":"mixed_language_pizza","query":"recommend some cheesy pizza","expected_source_type":"dish","constraints":{"required_keywords":["披萨","芝士"],"allowed_cuisine_types":["意式"]}}
{"id":"session_followup_less_spicy","query":"换几个没那么辣的","expected_source_type":"dish","constraints":{"forbidden_keywords":["麻辣浓郁"]}}
```

- [ ] **Step 5: Run evaluation tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/service/rag/test_rag_metrics.py tests/service/test_rag_evaluator.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add tools/evaluate_assistant_rag.py tests/eval/assistant_rag_cases.jsonl tests/service/rag/test_rag_metrics.py
git commit -m "feat: expand rag evaluation metrics"
```

---

### Task 15: Final Regression, Docs, And Cleanup Notes

**Files:**
- Modify: `README.md`
- Modify: `ui/README.md`
- Review-only: `agent/assistant.py`, `service/assistant_orchestrator.py`, `service/rag_retriever.py`

- [ ] **Step 1: Update README architecture section**

Add a section to `README.md`:

```markdown
## LangGraph Agent + Advanced RAG

The assistant uses LangGraph as the runtime state machine. Each chat session maps to a LangGraph thread ID, so short-term messages and recent actions are checkpointed per session.

The main flow is:

1. Load short-term and long-term memory.
2. Use an LLM planner to create a structured plan.
3. Route to RAG, local write action, undo, or direct answer.
4. Record reversible cart/address/preference writes in the action journal.
5. Generate grounded answers from evidence.

RAG uses multi-route recall, RRF fusion, hard filters, weighted reranking, diversification, and citation-backed evidence packs.
```

- [ ] **Step 2: Update frontend README API section**

Add to `ui/README.md`:

```markdown
The assistant response can include `undo_available`. Local reversible actions such as cart clear, address delete, and user preference changes execute immediately and can be undone by sending a follow-up message such as “撤回刚才的操作”.
```

- [ ] **Step 3: Run focused backend tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/service/test_agent_runtime_state.py tests/service/test_prompt_registry.py tests/service/test_langgraph_agent_planner.py tests/service/test_langgraph_agent_graph.py tests/service/test_langgraph_undo_flow.py tests/service/test_agent_memory_flow.py tests/service/rag tests/service/test_action_journal_service.py tests/service/test_user_memory_service.py tests/service/test_undo_tools.py -q
```

Expected: PASS.

- [ ] **Step 4: Run assistant API tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/api/test_assistant_routes.py tests/service/test_assistant_service_langgraph.py -q
```

Expected: PASS.

- [ ] **Step 5: Run full Python collection and regression**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest --collect-only -q
.\.venv\Scripts\python.exe -m pytest -q
```

Expected: collection succeeds and the full backend suite passes.

- [ ] **Step 6: Run frontend assistant tests**

Run:

```powershell
cd ui
npm run test -- floatingAssistant.test.js app.homepage.test.js api.interceptor.test.js
```

Expected: PASS.

- [ ] **Step 7: Run RAG evaluation script**

Run:

```powershell
.\.venv\Scripts\python.exe tools\evaluate_assistant_rag.py
```

Expected JSON includes:

```json
{
  "recall_at_5": 0.9,
  "constraint_pass_rate": 0.95,
  "citation_coverage": 1.0
}
```

The exact values can exceed these targets. If a metric is lower, inspect failed cases and tune recall route weights or expansion query rules before merging.

- [ ] **Step 8: Commit docs and final verification**

```powershell
git add README.md ui/README.md
git commit -m "docs: document langgraph agent rag architecture"
```

---

## Execution Notes

This plan intentionally avoids deleting old modules in the first implementation pass. Keep `service/assistant_orchestrator.py`, `service/rag_retriever.py`, and `agent/assistant.py` available until the LangGraph path passes assistant route tests and RAG evaluation. After that, create a separate cleanup plan to remove or mark legacy modules.

Do not commit local database files, logs, `.env`, `output/`, or generated caches.

Before each commit, run:

```powershell
git status --short
git diff --cached --name-only
```

The staged file list must contain only files owned by that task.
