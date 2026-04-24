# Smart Assistant Agent RAG Highlight Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a resume-ready smart ordering assistant that uses an LLM Agent, controlled tool calling, Hybrid RAG, confirmation guardrails, and retrieval evaluation metrics.

**Architecture:** Keep `service/assistant_service.py` as the FastAPI-facing facade and move orchestration into focused backend units. The LLM planner produces structured tool plans, deterministic tools perform retrieval and mutations, and a confirmation manager gates side-effect operations. Hybrid RAG combines query rewrite, Pinecone dense recall, SQL/metadata/keyword recall, hard filters, reranking, and evidence packs.

**Tech Stack:** FastAPI, Pydantic, SQLAlchemy, LangChain-compatible OpenAI chat model, DashScope embeddings, Pinecone, pytest, Vue 3, Vitest.

---

## File Structure

Create or modify these backend files:

- Create `service/agent_state.py`: dataclasses for planner decisions, tool calls, tool results, evidence packs, pending actions, and assistant session state.
- Create `service/confirmation_manager.py`: decides direct execution versus pending confirmation and stores/commits pending actions.
- Create `service/agent_planner.py`: LLM planner with rule fallback and strict JSON output.
- Create `service/rag_query_rewriter.py`: rewrites user messages into semantic queries and hard filters.
- Create `service/rag_reranker.py`: scores and sorts retrieved evidence.
- Create `service/rag_retriever.py`: combines dense, metadata, keyword, SQL filters, rerank, and evidence pack creation.
- Create `service/tools/catalog_tool.py`: catalog search tool for merchant/dish facts and explicit dish resolution.
- Create `service/tools/recommendation_tool.py`: recommendation tool backed by `RagRetriever`.
- Modify `service/tools/cart_tool.py`: add direct add helper and staged cart action commit helper.
- Modify `service/tools/address_tool.py`: add validated address payload support and staged address action commit helper.
- Modify `service/tool_registry.py`: add schema metadata, side-effect class, parameter validation boundary, and structured tool result handling.
- Modify `service/assistant_session_store.py`: persist slots, pending action, and evidence IDs.
- Create `service/assistant_orchestrator.py`: main workflow coordinator.
- Modify `service/assistant_service.py`: delegate to `AssistantOrchestrator` and keep health endpoint support.
- Modify `api/schemas.py`: add pending action and executed action response models.
- Modify `tools/assistant_sync.py`: produce richer semantic indexing text.
- Create `tools/evaluate_assistant_rag.py`: run retrieval and flow metrics over eval cases.
- Create `tests/eval/assistant_rag_cases.jsonl`: fixed retrieval and flow evaluation cases.

Create or modify these frontend files:

- Modify `ui/src/composables/useAssistant.js`: store pending actions and executed actions.
- Modify `ui/src/components/home/FloatingAssistant.vue`: render confirmation blocks and action results.
- Modify `ui/src/__tests__/floatingAssistant.test.js`: cover pending confirmation and action completion.

The existing `service/agent_core.py` and `service/assistant_retriever.py` should remain during migration until the orchestrator is fully wired. After the new path passes tests, they can become compatibility wrappers or be removed in a separate cleanup task.

---

## Task 1: Define Agent State Models

**Files:**
- Create: `service/agent_state.py`
- Test: `tests/service/test_agent_state.py`

- [ ] **Step 1: Write failing state model tests**

Create `tests/service/test_agent_state.py`:

```python
from service.agent_state import (
    AgentDecision,
    EvidencePack,
    PendingAction,
    ToolCall,
    ToolResult,
    AssistantTurnState,
)


def test_tool_result_success_contract() -> None:
    evidence = EvidencePack(
        source_type="dish",
        source_id=11,
        merchant_id=1,
        title="鱼香肉丝｜兰姨小炒",
        facts={"price": 28.0, "cuisine_type": "川味麻辣"},
        why_matched=["匹配川菜"],
        citation="川味麻辣；酸甜微辣",
    )

    result = ToolResult.ok_result(
        tool_name="recommend_dishes",
        data={"count": 1},
        evidence=[evidence],
    )

    assert result.ok is True
    assert result.error is None
    assert result.evidence[0].source_id == 11


def test_pending_action_expires_and_serializes_items() -> None:
    action = PendingAction(
        action_id="pa_1",
        action_type="cart_add",
        summary="将鱼香肉丝 1 份加入购物车",
        payload={"items": [{"dish_id": 11, "quantity": 1}]},
        requires_user_id=True,
    )

    assert action.action_type == "cart_add"
    assert action.payload["items"][0]["dish_id"] == 11
    assert action.requires_user_id is True


def test_turn_state_tracks_slots_and_pending_action() -> None:
    state = AssistantTurnState(session_id="s1", user_id=1)
    state.slots["budget"] = 100
    state.pending_action = PendingAction(
        action_id="pa_2",
        action_type="address_save",
        summary="保存地址",
        payload={"label": "家"},
        requires_user_id=True,
    )

    assert state.slots["budget"] == 100
    assert state.pending_action.action_type == "address_save"


def test_agent_decision_contains_tool_plan() -> None:
    decision = AgentDecision(
        intent="mixed_task",
        reasoning_summary="推荐川菜并准备加购",
        tool_plan=[
            ToolCall(
                tool_name="recommend_dishes",
                arguments={"query": "川菜 下饭"},
                requires_confirmation=False,
            )
        ],
        missing_slots=["budget", "party_size"],
        needs_confirmation=False,
    )

    assert decision.intent == "mixed_task"
    assert decision.tool_plan[0].tool_name == "recommend_dishes"
    assert "budget" in decision.missing_slots
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python -m pytest tests/service/test_agent_state.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'service.agent_state'`.

- [ ] **Step 3: Implement state models**

Create `service/agent_state.py`:

```python
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Literal
from uuid import uuid4


IntentType = Literal[
    "greeting",
    "knowledge",
    "recommendation",
    "cart_action",
    "address_action",
    "mixed_task",
    "unsupported",
]

ResponseType = Literal[
    "greeting",
    "knowledge",
    "recommendation",
    "clarification",
    "confirmation_required",
    "action_completed",
    "unsupported",
]


@dataclass
class ToolCall:
    tool_name: str
    arguments: dict[str, Any] = field(default_factory=dict)
    requires_confirmation: bool = False


@dataclass
class AgentDecision:
    intent: IntentType
    reasoning_summary: str = ""
    tool_plan: list[ToolCall] = field(default_factory=list)
    missing_slots: list[str] = field(default_factory=list)
    clarification_question: str | None = None
    needs_confirmation: bool = False


@dataclass
class EvidencePack:
    source_type: Literal["dish", "merchant"]
    source_id: int
    merchant_id: int
    title: str
    facts: dict[str, Any]
    why_matched: list[str] = field(default_factory=list)
    citation: str = ""
    score: float = 0.0


@dataclass
class ToolError:
    code: str
    message: str
    candidates: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class ToolResult:
    ok: bool
    tool_name: str
    data: dict[str, Any] = field(default_factory=dict)
    evidence: list[EvidencePack] = field(default_factory=list)
    requires_confirmation: bool = False
    error: ToolError | None = None

    @classmethod
    def ok_result(
        cls,
        *,
        tool_name: str,
        data: dict[str, Any] | None = None,
        evidence: list[EvidencePack] | None = None,
        requires_confirmation: bool = False,
    ) -> "ToolResult":
        return cls(
            ok=True,
            tool_name=tool_name,
            data=data or {},
            evidence=evidence or [],
            requires_confirmation=requires_confirmation,
        )

    @classmethod
    def error_result(
        cls,
        *,
        tool_name: str,
        code: str,
        message: str,
        candidates: list[dict[str, Any]] | None = None,
    ) -> "ToolResult":
        return cls(
            ok=False,
            tool_name=tool_name,
            error=ToolError(code=code, message=message, candidates=candidates or []),
        )


@dataclass
class PendingAction:
    action_type: Literal["cart_add", "address_save"]
    summary: str
    payload: dict[str, Any]
    requires_user_id: bool
    action_id: str = field(default_factory=lambda: f"pa_{uuid4().hex[:12]}")
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc) + timedelta(minutes=10))

    def is_expired(self, now: datetime | None = None) -> bool:
        return (now or datetime.now(timezone.utc)) >= self.expires_at


@dataclass
class AssistantTurnState:
    session_id: str
    user_id: int | None = None
    last_intent: IntentType | None = None
    slots: dict[str, Any] = field(default_factory=dict)
    last_evidence_ids: list[str] = field(default_factory=list)
    pending_action: PendingAction | None = None
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
python -m pytest tests/service/test_agent_state.py -q
```

Expected: PASS with 4 tests.

- [ ] **Step 5: Commit**

```bash
git add service/agent_state.py tests/service/test_agent_state.py
git commit -m "feat: add assistant agent state models"
```

---

## Task 2: Add Confirmation Manager

**Files:**
- Create: `service/confirmation_manager.py`
- Test: `tests/service/test_confirmation_manager.py`

- [ ] **Step 1: Write failing confirmation manager tests**

Create `tests/service/test_confirmation_manager.py`:

```python
from datetime import datetime, timedelta, timezone

from service.agent_state import AssistantTurnState, PendingAction
from service.confirmation_manager import ConfirmationManager


def test_recommendation_cart_action_requires_confirmation() -> None:
    manager = ConfirmationManager()
    assert manager.requires_confirmation(
        action_type="cart_add",
        payload={"source": "recommendation", "items": [{"dish_id": 11, "quantity": 1}]},
    ) is True


def test_explicit_unique_small_cart_action_can_execute_directly() -> None:
    manager = ConfirmationManager()
    assert manager.requires_confirmation(
        action_type="cart_add",
        payload={"source": "explicit", "items": [{"dish_id": 11, "quantity": 1}], "unique_match": True},
    ) is False


def test_address_save_requires_confirmation() -> None:
    manager = ConfirmationManager()
    assert manager.requires_confirmation(
        action_type="address_save",
        payload={"label": "家", "contact_phone": "13800000000"},
    ) is True


def test_store_and_consume_pending_action() -> None:
    manager = ConfirmationManager()
    state = AssistantTurnState(session_id="s1", user_id=1)
    action = PendingAction(
        action_type="cart_add",
        summary="加入购物车",
        payload={"items": [{"dish_id": 11, "quantity": 1}]},
        requires_user_id=True,
    )

    manager.store_pending_action(state, action)
    consumed = manager.consume_pending_action(state, user_message="确认")

    assert consumed is action
    assert state.pending_action is None


def test_expired_pending_action_is_not_consumed() -> None:
    manager = ConfirmationManager()
    expired = PendingAction(
        action_type="cart_add",
        summary="过期动作",
        payload={"items": [{"dish_id": 11, "quantity": 1}]},
        requires_user_id=True,
        expires_at=datetime.now(timezone.utc) - timedelta(seconds=1),
    )
    state = AssistantTurnState(session_id="s1", pending_action=expired)

    consumed = manager.consume_pending_action(state, user_message="确认")

    assert consumed is None
    assert state.pending_action is None
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python -m pytest tests/service/test_confirmation_manager.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'service.confirmation_manager'`.

- [ ] **Step 3: Implement confirmation manager**

Create `service/confirmation_manager.py`:

```python
from __future__ import annotations

from typing import Any

from service.agent_state import AssistantTurnState, PendingAction


CONFIRM_MESSAGES = {"确认", "好的", "可以", "是", "yes", "ok", "加吧", "保存吧"}
CANCEL_MESSAGES = {"取消", "不要", "算了", "否", "no", "cancel"}


class ConfirmationManager:
    def requires_confirmation(self, action_type: str, payload: dict[str, Any]) -> bool:
        if action_type == "address_save":
            return True

        if action_type != "cart_add":
            return True

        if payload.get("source") == "recommendation":
            return True

        if not payload.get("unique_match", False):
            return True

        items = payload.get("items", [])
        if len(items) != 1:
            return True

        quantity = int(items[0].get("quantity", 0))
        return quantity < 1 or quantity > 3

    def store_pending_action(self, state: AssistantTurnState, action: PendingAction) -> PendingAction:
        state.pending_action = action
        return action

    def consume_pending_action(self, state: AssistantTurnState, user_message: str) -> PendingAction | None:
        normalized = user_message.strip().lower()
        pending = state.pending_action
        if pending is None:
            return None

        if pending.is_expired():
            state.pending_action = None
            return None

        if normalized in CANCEL_MESSAGES:
            state.pending_action = None
            return None

        if normalized in CONFIRM_MESSAGES:
            state.pending_action = None
            return pending

        return None

    def is_confirmation_message(self, user_message: str) -> bool:
        return user_message.strip().lower() in CONFIRM_MESSAGES
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
python -m pytest tests/service/test_confirmation_manager.py -q
```

Expected: PASS with 5 tests.

- [ ] **Step 5: Commit**

```bash
git add service/confirmation_manager.py tests/service/test_confirmation_manager.py
git commit -m "feat: add assistant confirmation manager"
```

---

## Task 3: Implement Planner Contract

**Files:**
- Create: `service/agent_planner.py`
- Test: `tests/service/test_agent_planner.py`

- [ ] **Step 1: Write failing planner tests**

Create `tests/service/test_agent_planner.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python -m pytest tests/service/test_agent_planner.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'service.agent_planner'`.

- [ ] **Step 3: Implement planner**

Create `service/agent_planner.py`:

```python
from __future__ import annotations

import json
import logging
import os
from typing import Any

from service.agent_state import AgentDecision, ToolCall
from tools.llm_tool import call_llm

logger = logging.getLogger(__name__)


PLANNER_PROMPT = """你是 smart_order 的智能点餐 Agent Planner。
你只能返回 JSON，不要返回 Markdown。

可用工具：
- search_catalog: 查询商家和菜品事实
- recommend_dishes: 基于预算、人数、口味、过敏原推荐菜品
- prepare_cart_action: 准备加入购物车动作，不直接写库
- parse_address: 从自然语言中解析地址字段
- prepare_address_action: 准备保存地址动作，不直接写库

意图必须是：
greeting, knowledge, recommendation, cart_action, address_action, mixed_task, unsupported

返回格式：
{
  "intent": "...",
  "reasoning_summary": "...",
  "tool_plan": [{"tool": "...", "arguments": {}, "requires_confirmation": false}],
  "missing_slots": [],
  "clarification_question": null,
  "needs_confirmation": false
}

关键规则：
- 查询有哪些店、多少钱、营业时间属于 knowledge。
- 个性化推荐如果缺少预算或人数，应填 missing_slots 并给 clarification_question。
- 推荐后加入购物车属于 mixed_task，需要先推荐，再准备确认动作。
- 保存地址属于 address_action，保存前需要确认。
"""


class AgentPlanner:
    def __init__(self) -> None:
        self._model_name = os.getenv("MODEL_NAME")
        self._llm = None

    def plan(self, user_message: str, session_context: dict[str, Any]) -> AgentDecision:
        if self._llm is not None:
            raw = self._llm.call(user_message, PLANNER_PROMPT)
            return self._parse_decision(raw)

        if self._model_name:
            try:
                raw = call_llm(
                    query=json.dumps(
                        {"message": user_message, "session_context": session_context},
                        ensure_ascii=False,
                    ),
                    system_instruction=PLANNER_PROMPT,
                )
                return self._parse_decision(raw)
            except Exception as exc:
                logger.warning("planner LLM failed, using rules: %s", exc)

        return self._rule_plan(user_message)

    def _parse_decision(self, raw: str | dict[str, Any]) -> AgentDecision:
        parsed = raw if isinstance(raw, dict) else json.loads(self._clean_json(raw))
        return AgentDecision(
            intent=parsed.get("intent", "unsupported"),
            reasoning_summary=parsed.get("reasoning_summary", ""),
            tool_plan=[
                ToolCall(
                    tool_name=item.get("tool", ""),
                    arguments=item.get("arguments", {}),
                    requires_confirmation=bool(item.get("requires_confirmation", False)),
                )
                for item in parsed.get("tool_plan", [])
            ],
            missing_slots=list(parsed.get("missing_slots", [])),
            clarification_question=parsed.get("clarification_question"),
            needs_confirmation=bool(parsed.get("needs_confirmation", False)),
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

    def _rule_plan(self, user_message: str) -> AgentDecision:
        msg = user_message.strip().lower()
        if msg in {"hi", "hello", "你好", "嗨", "在吗"}:
            return AgentDecision(intent="greeting", reasoning_summary="问候")

        if "地址" in msg and any(word in msg for word in ("保存", "加入", "添加", "地址管理")):
            return AgentDecision(
                intent="address_action",
                reasoning_summary="保存地址",
                tool_plan=[ToolCall(tool_name="parse_address", arguments={"message": user_message})],
                needs_confirmation=True,
            )

        if "购物车" in msg or "加一份" in msg or "加入" in msg:
            if "推荐" in msg:
                return AgentDecision(
                    intent="mixed_task",
                    reasoning_summary="推荐后加购",
                    missing_slots=["budget", "party_size"],
                    clarification_question="请告诉我这顿几个人吃、预算多少？",
                    needs_confirmation=True,
                )
            return AgentDecision(
                intent="cart_action",
                reasoning_summary="明确加购",
                tool_plan=[ToolCall(tool_name="search_catalog", arguments={"query": user_message})],
            )

        if "推荐" in msg or "吃什么" in msg:
            return AgentDecision(
                intent="recommendation",
                reasoning_summary="个性化推荐",
                missing_slots=["budget", "party_size"],
                clarification_question="请告诉我这顿几个人吃、预算多少？",
            )

        if any(word in msg for word in ("有哪些", "有什么", "几点", "营业", "多少钱", "价格", "电话")):
            return AgentDecision(
                intent="knowledge",
                reasoning_summary="查询信息",
                tool_plan=[ToolCall(tool_name="search_catalog", arguments={"query": user_message})],
            )

        return AgentDecision(intent="unsupported", reasoning_summary="无法识别")
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
python -m pytest tests/service/test_agent_planner.py -q
```

Expected: PASS with 3 tests.

- [ ] **Step 5: Commit**

```bash
git add service/agent_planner.py tests/service/test_agent_planner.py
git commit -m "feat: add assistant agent planner"
```

---

## Task 4: Add Query Rewrite And Reranking

**Files:**
- Create: `service/rag_query_rewriter.py`
- Create: `service/rag_reranker.py`
- Test: `tests/service/test_rag_query_rewriter.py`
- Test: `tests/service/test_rag_reranker.py`

- [ ] **Step 1: Write failing query rewriter tests**

Create `tests/service/test_rag_query_rewriter.py`:

```python
from service.rag_query_rewriter import RagQueryRewriter


def test_rewriter_extracts_budget_party_and_allergen() -> None:
    rewriter = RagQueryRewriter()
    request = rewriter.rewrite("推荐几种川菜，2个人吃，100元以内，不要花生")

    assert request.hard_filters["budget_max"] == 100.0
    assert request.hard_filters["party_size"] == 2
    assert request.hard_filters["exclude_allergens"] == ["花生"]
    assert "川菜" in request.hard_filters["cuisine_types"]
    assert len(request.semantic_queries) >= 2


def test_rewriter_detects_merchant_knowledge_query() -> None:
    rewriter = RagQueryRewriter()
    request = rewriter.rewrite("有哪些咖啡甜品店？几点营业？")

    assert request.source_types == ["merchant"]
    assert any("咖啡" in query for query in request.semantic_queries)
```

- [ ] **Step 2: Write failing reranker tests**

Create `tests/service/test_rag_reranker.py`:

```python
from service.agent_state import EvidencePack
from service.rag_reranker import RagReranker


def test_reranker_sorts_by_blended_score() -> None:
    candidates = [
        EvidencePack(
            source_type="dish",
            source_id=11,
            merchant_id=1,
            title="低分菜",
            facts={"semantic_score": 0.2, "keyword_score": 0.1, "merchant_rating": 4.0, "is_recommended": False, "constraint_match_score": 1.0},
        ),
        EvidencePack(
            source_type="dish",
            source_id=12,
            merchant_id=1,
            title="高分菜",
            facts={"semantic_score": 0.9, "keyword_score": 0.8, "merchant_rating": 4.8, "is_recommended": True, "constraint_match_score": 1.0},
        ),
    ]

    reranked = RagReranker().rerank(candidates)

    assert reranked[0].source_id == 12
    assert reranked[0].score > reranked[1].score
```

- [ ] **Step 3: Run tests to verify they fail**

Run:

```bash
python -m pytest tests/service/test_rag_query_rewriter.py tests/service/test_rag_reranker.py -q
```

Expected: FAIL with missing modules.

- [ ] **Step 4: Implement query rewriter and reranker**

Create `service/rag_query_rewriter.py`:

```python
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal


CUISINE_KEYWORDS = ["川菜", "湘菜", "粤菜", "轻食", "咖啡甜品", "麻辣烫", "披萨意面"]
ALLERGEN_KEYWORDS = ["花生", "麸质", "牛奶", "鸡蛋", "海鲜"]
BUDGET_PATTERN = re.compile(r"(?:预算\s*)?(\d+(?:\.\d+)?)\s*(?:元|块)(?:以内|以下|之内)?")
PARTY_SIZE_PATTERN = re.compile(r"(\d+)\s*(?:个人|人)")


@dataclass
class RagRewriteRequest:
    original_query: str
    semantic_queries: list[str]
    hard_filters: dict
    source_types: list[Literal["dish", "merchant"]] = field(default_factory=lambda: ["dish", "merchant"])


class RagQueryRewriter:
    def rewrite(self, message: str) -> RagRewriteRequest:
        cuisine_types = [item for item in CUISINE_KEYWORDS if item in message]
        exclude_allergens = [
            item for item in ALLERGEN_KEYWORDS
            if f"不要{item}" in message or f"不含{item}" in message or f"不能吃{item}" in message
        ]
        budget_match = BUDGET_PATTERN.search(message)
        party_match = PARTY_SIZE_PATTERN.search(message)

        source_types: list[Literal["dish", "merchant"]] = ["dish", "merchant"]
        if any(word in message for word in ("店", "商家", "营业", "电话", "地址")):
            source_types = ["merchant"]

        base_terms = []
        base_terms.extend(cuisine_types)
        if "下饭" in message:
            base_terms.append("下饭")
        if "咖啡" in message:
            base_terms.extend(["咖啡", "甜品", "饮品"])

        semantic_queries = [
            " ".join(base_terms) if base_terms else message,
            message,
        ]
        if cuisine_types and party_match:
            semantic_queries.append(f"{cuisine_types[0]} 适合{party_match.group(1)}人")
        if exclude_allergens:
            semantic_queries.append(f"不含{' '.join(exclude_allergens)}")

        hard_filters = {
            "original_query": message,
            "cuisine_types": cuisine_types,
            "exclude_allergens": exclude_allergens,
            "budget_max": float(budget_match.group(1)) if budget_match else None,
            "party_size": int(party_match.group(1)) if party_match else None,
        }

        return RagRewriteRequest(
            original_query=message,
            semantic_queries=[query for query in semantic_queries if query.strip()],
            hard_filters=hard_filters,
            source_types=source_types,
        )
```

Create `service/rag_reranker.py`:

```python
from __future__ import annotations

from service.agent_state import EvidencePack


class RagReranker:
    def rerank(self, candidates: list[EvidencePack], limit: int = 5) -> list[EvidencePack]:
        for candidate in candidates:
            facts = candidate.facts
            semantic_score = float(facts.get("semantic_score", 0.0))
            keyword_score = float(facts.get("keyword_score", 0.0))
            merchant_rating = float(facts.get("merchant_rating", 0.0)) / 5.0
            recommendation_boost = 1.0 if facts.get("is_recommended") else 0.0
            constraint_match_score = float(facts.get("constraint_match_score", 0.0))
            candidate.score = (
                0.45 * semantic_score
                + 0.20 * keyword_score
                + 0.15 * merchant_rating
                + 0.10 * recommendation_boost
                + 0.10 * constraint_match_score
            )
        return sorted(candidates, key=lambda item: item.score, reverse=True)[:limit]
```

- [ ] **Step 5: Run tests to verify they pass**

Run:

```bash
python -m pytest tests/service/test_rag_query_rewriter.py tests/service/test_rag_reranker.py -q
```

Expected: PASS with 3 tests.

- [ ] **Step 6: Commit**

```bash
git add service/rag_query_rewriter.py service/rag_reranker.py tests/service/test_rag_query_rewriter.py tests/service/test_rag_reranker.py
git commit -m "feat: add rag query rewrite and rerank"
```

---

## Task 5: Implement Hybrid RAG Retriever

**Files:**
- Create: `service/rag_retriever.py`
- Modify: `tools/assistant_sync.py`
- Test: `tests/service/test_rag_retriever.py`
- Test: `tests/service/test_assistant_sync.py`

- [ ] **Step 1: Write failing retriever tests**

Create `tests/service/test_rag_retriever.py`:

```python
from service.rag_retriever import RagRetriever


class StubCatalog:
    def list_merchants(self, district=None):
        return [
            {
                "id": 1,
                "name": "兰姨小炒",
                "description": "现炒川湘下饭菜",
                "rating": 4.8,
                "business_hours": "10:00-21:30",
                "merchant_tags": ["川湘", "下饭"],
                "homepage_category": "湘菜",
                "delivery_fee": 4.0,
                "min_order_amount": 20.0,
                "district": "静安",
            }
        ]

    def list_dishes_by_merchant(self, merchant_id):
        return [
            {
                "id": 11,
                "merchant_id": 1,
                "name": "鱼香肉丝",
                "description": "酸甜微辣，下饭",
                "price": 28.0,
                "is_recommended": True,
                "cuisine_type": "川味麻辣",
                "flavor_profile": "酸甜微辣",
                "ingredients": ["猪里脊", "木耳"],
                "allergens": [],
                "cooking_method": "爆炒",
            },
            {
                "id": 12,
                "merchant_id": 1,
                "name": "宫保鸡丁",
                "description": "花生香辣",
                "price": 60.0,
                "is_recommended": True,
                "cuisine_type": "川味麻辣",
                "flavor_profile": "香辣",
                "ingredients": ["鸡肉", "花生"],
                "allergens": ["花生"],
                "cooking_method": "爆炒",
            },
        ]


class StubVectorStore:
    def is_ready(self):
        return True

    def semantic_search(self, query, top_k=5, namespace=""):
        if namespace == "dishes":
            return [
                {"id": "dish_11", "score": 0.9, "metadata": {"dish_id": 11}},
                {"id": "dish_12", "score": 0.8, "metadata": {"dish_id": 12}},
            ]
        return []


def test_rag_retriever_filters_budget_and_allergens() -> None:
    retriever = RagRetriever(
        catalog_service=StubCatalog(),
        vector_store=StubVectorStore(),
    )

    evidence = retriever.retrieve("推荐几种川菜，2个人吃，100元以内，不要花生", limit=3)

    assert [item.source_id for item in evidence] == [11]
    assert evidence[0].facts["price"] == 28.0
    assert "未命中花生过敏原" in evidence[0].why_matched


def test_rag_retriever_returns_merchant_evidence_for_knowledge() -> None:
    retriever = RagRetriever(
        catalog_service=StubCatalog(),
        vector_store=StubVectorStore(),
    )

    evidence = retriever.retrieve("有哪些湘菜店？几点营业？", limit=3)

    assert evidence[0].source_type == "merchant"
    assert evidence[0].merchant_id == 1
    assert "10:00-21:30" in evidence[0].citation
```

- [ ] **Step 2: Run retriever test to verify it fails**

Run:

```bash
python -m pytest tests/service/test_rag_retriever.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'service.rag_retriever'`.

- [ ] **Step 3: Implement retriever**

Create `service/rag_retriever.py`:

```python
from __future__ import annotations

from service.agent_state import EvidencePack
from service.catalog_service import CatalogService
from service.rag_query_rewriter import RagQueryRewriter
from service.rag_reranker import RagReranker
from tools.assistant_vector_store import AssistantVectorStore


CUISINE_ALIASES = {
    "川菜": {"川菜", "川味麻辣"},
    "湘菜": {"湘菜", "川湘"},
    "粤菜": {"粤菜"},
    "轻食": {"轻食"},
    "咖啡甜品": {"咖啡", "甜点", "烘焙", "饮品", "咖啡甜品"},
}


class RagRetriever:
    def __init__(self, session=None, catalog_service=None, vector_store=None) -> None:
        self.catalog_service = catalog_service or CatalogService(session)
        self.vector_store = vector_store or AssistantVectorStore()
        self.rewriter = RagQueryRewriter()
        self.reranker = RagReranker()

    def retrieve(self, message: str, limit: int = 5) -> list[EvidencePack]:
        rewrite = self.rewriter.rewrite(message)
        merchants = self.catalog_service.list_merchants()
        semantic_scores = self._semantic_scores(rewrite.semantic_queries)

        candidates: list[EvidencePack] = []
        if rewrite.source_types == ["merchant"]:
            for merchant in merchants:
                candidates.append(self._merchant_evidence(merchant, semantic_scores))
            return self.reranker.rerank(candidates, limit=limit)

        filters = rewrite.hard_filters
        for merchant in merchants:
            for dish in self.catalog_service.list_dishes_by_merchant(merchant["id"]):
                if not self._passes_filters(dish, filters):
                    continue
                candidates.append(self._dish_evidence(merchant, dish, semantic_scores, filters))

        return self.reranker.rerank(candidates, limit=limit)

    def _semantic_scores(self, semantic_queries: list[str]) -> dict[str, float]:
        scores: dict[str, float] = {}
        if not self.vector_store.is_ready():
            return scores
        for query in semantic_queries:
            for namespace in ("dishes", "merchants"):
                for match in self.vector_store.semantic_search(query, top_k=20, namespace=namespace):
                    scores[match["id"]] = max(scores.get(match["id"], 0.0), float(match.get("score", 0.0)))
        return scores

    def _passes_filters(self, dish: dict, filters: dict) -> bool:
        cuisine_types = filters.get("cuisine_types") or []
        if cuisine_types:
            allowed = set()
            for cuisine in cuisine_types:
                allowed.update(CUISINE_ALIASES.get(cuisine, {cuisine}))
            if dish.get("cuisine_type") not in allowed:
                return False

        exclude_allergens = filters.get("exclude_allergens") or []
        dish_allergens = set(dish.get("allergens") or [])
        if any(allergen in dish_allergens for allergen in exclude_allergens):
            return False

        budget_max = filters.get("budget_max")
        party_size = filters.get("party_size") or 1
        if budget_max is not None and float(dish["price"]) * int(party_size) > float(budget_max):
            return False

        return True

    def _dish_evidence(self, merchant: dict, dish: dict, semantic_scores: dict[str, float], filters: dict) -> EvidencePack:
        dish_key = f"dish_{dish['id']}"
        exclude_allergens = filters.get("exclude_allergens") or []
        why = [dish.get("cuisine_type", "")]
        why.append(f"{float(dish['price']):.0f}元")
        if exclude_allergens:
            why.extend([f"未命中{item}过敏原" for item in exclude_allergens])
        return EvidencePack(
            source_type="dish",
            source_id=dish["id"],
            merchant_id=merchant["id"],
            title=f"{dish['name']}｜{merchant['name']}",
            facts={
                "dish_id": dish["id"],
                "dish_name": dish["name"],
                "merchant_name": merchant["name"],
                "price": float(dish["price"]),
                "cuisine_type": dish.get("cuisine_type", ""),
                "flavor_profile": dish.get("flavor_profile", ""),
                "allergens": list(dish.get("allergens") or []),
                "semantic_score": semantic_scores.get(dish_key, 0.0),
                "keyword_score": 1.0 if dish["name"] in filters.get("original_query", "") else 0.0,
                "merchant_rating": float(merchant.get("rating", 0.0)),
                "is_recommended": bool(dish.get("is_recommended")),
                "constraint_match_score": 1.0,
            },
            why_matched=[item for item in why if item],
            citation=f"{dish.get('cuisine_type', '')}；{dish.get('flavor_profile', '')}；配料为{'、'.join(dish.get('ingredients') or [])}",
        )

    def _merchant_evidence(self, merchant: dict, semantic_scores: dict[str, float]) -> EvidencePack:
        key = f"merchant_{merchant['id']}"
        return EvidencePack(
            source_type="merchant",
            source_id=merchant["id"],
            merchant_id=merchant["id"],
            title=merchant["name"],
            facts={
                "merchant_name": merchant["name"],
                "business_hours": merchant.get("business_hours", ""),
                "delivery_fee": float(merchant.get("delivery_fee", 0.0)),
                "min_order_amount": float(merchant.get("min_order_amount", 0.0)),
                "merchant_rating": float(merchant.get("rating", 0.0)),
                "semantic_score": semantic_scores.get(key, 0.0),
                "keyword_score": 0.5,
                "is_recommended": False,
                "constraint_match_score": 1.0,
            },
            why_matched=list((merchant.get("merchant_tags") or [])[:3]),
            citation=f"{merchant.get('description', '')}；营业时间 {merchant.get('business_hours', '')}",
        )
```

- [ ] **Step 4: Run retriever test to verify it passes**

Run:

```bash
python -m pytest tests/service/test_rag_retriever.py -q
```

Expected: PASS with 2 tests.

- [ ] **Step 5: Update semantic indexing text test**

Modify `tests/test_seed_payload.py` or add a new test in `tests/service/test_assistant_sync.py`:

```python
from tools.assistant_sync import _build_dish_text


def test_dish_text_contains_search_scenarios_and_allergen_copy() -> None:
    merchant = {"name": "兰姨小炒"}
    dish = {
        "name": "鱼香肉丝",
        "cuisine_type": "川味麻辣",
        "flavor_profile": "酸甜微辣",
        "price": 28.0,
        "ingredients": ["猪里脊", "木耳"],
        "allergens": [],
        "description": "酸甜微辣，下饭感强",
        "cooking_method": "爆炒",
    }

    text = _build_dish_text(dish, merchant)

    assert "适合场景" in text
    assert "无显式过敏原" in text
```

- [ ] **Step 6: Run sync text test to verify it fails**

Run:

```bash
python -m pytest tests/service/test_assistant_sync.py -q
```

Expected: FAIL because `_build_dish_text` does not include `适合场景` or `无显式过敏原`.

- [ ] **Step 7: Modify `tools/assistant_sync.py` dish text builder**

Update `_build_dish_text` to include scenario and allergen text:

```python
def _build_dish_text(dish: dict, merchant: dict) -> str:
    allergens = dish["allergens"] if dish["allergens"] else ["无显式过敏原"]
    scenario_terms = []
    if "下饭" in dish["description"] or "辣" in dish["flavor_profile"]:
        scenario_terms.append("工作餐")
        scenario_terms.append("米饭搭配")
    if dish["price"] <= 35:
        scenario_terms.append("单人简餐")
    if not scenario_terms:
        scenario_terms.append("日常点餐")

    parts = [
        f"菜品:{dish['name']}",
        f"商家:{merchant['name']}",
        f"菜系:{dish['cuisine_type'] or '其他'}",
        f"口味:{dish['flavor_profile'] or '未知'}",
        f"价格:{dish['price']:.0f}元",
        f"适合场景:{','.join(scenario_terms)}",
        f"食材:{','.join(dish['ingredients']) if dish['ingredients'] else '未注明'}",
        f"过敏原:{','.join(allergens)}",
        f"特色:{dish['description'][:50] if dish['description'] else '无描述'}",
        f"烹饪方式:{dish['cooking_method'] or '未知'}",
    ]
    return "。".join(parts)
```

- [ ] **Step 8: Run tests to verify they pass**

Run:

```bash
python -m pytest tests/service/test_rag_retriever.py tests/service/test_assistant_sync.py -q
```

Expected: PASS.

- [ ] **Step 9: Commit**

```bash
git add service/rag_retriever.py tools/assistant_sync.py tests/service/test_rag_retriever.py tests/service/test_assistant_sync.py
git commit -m "feat: add hybrid rag retriever"
```

---

## Task 6: Add Catalog And Recommendation Tools

**Files:**
- Create: `service/tools/catalog_tool.py`
- Create: `service/tools/recommendation_tool.py`
- Modify: `service/tool_registry.py`
- Test: `tests/service/test_assistant_tools.py`
- Test: `tests/service/test_tool_registry.py`

- [ ] **Step 1: Write failing tool tests**

Create `tests/service/test_assistant_tools.py`:

```python
from service.agent_state import EvidencePack
from service.tools.catalog_tool import search_catalog_tool
from service.tools.recommendation_tool import recommend_dishes_tool


class StubRagRetriever:
    def retrieve(self, message, limit=5):
        return [
            EvidencePack(
                source_type="dish",
                source_id=11,
                merchant_id=1,
                title="鱼香肉丝｜兰姨小炒",
                facts={"dish_id": 11, "dish_name": "鱼香肉丝", "merchant_name": "兰姨小炒", "price": 28.0},
                why_matched=["匹配川菜"],
                citation="川味麻辣；酸甜微辣",
                score=0.91,
            )
        ]


def test_recommend_dishes_tool_returns_evidence_and_cart_candidates() -> None:
    result = recommend_dishes_tool(
        query="川菜 下饭",
        budget=100,
        party_size=2,
        exclude_allergens=["花生"],
        _retriever=StubRagRetriever(),
    )

    assert result.ok is True
    assert result.data["cart_candidate_items"] == [{"dish_id": 11, "quantity": 1}]
    assert result.evidence[0].source_id == 11


def test_search_catalog_tool_returns_evidence() -> None:
    result = search_catalog_tool(query="鱼香肉丝", _retriever=StubRagRetriever())

    assert result.ok is True
    assert result.evidence[0].title == "鱼香肉丝｜兰姨小炒"
```

- [ ] **Step 2: Run tool tests to verify they fail**

Run:

```bash
python -m pytest tests/service/test_assistant_tools.py -q
```

Expected: FAIL with missing modules.

- [ ] **Step 3: Implement catalog and recommendation tools**

Create `service/tools/catalog_tool.py`:

```python
from __future__ import annotations

from service.agent_state import ToolResult
from service.rag_retriever import RagRetriever


def search_catalog_tool(query: str, limit: int = 5, session=None, _retriever=None) -> ToolResult:
    retriever = _retriever or RagRetriever(session=session)
    evidence = retriever.retrieve(query, limit=limit)
    return ToolResult.ok_result(
        tool_name="search_catalog",
        data={"count": len(evidence)},
        evidence=evidence,
    )
```

Create `service/tools/recommendation_tool.py`:

```python
from __future__ import annotations

from service.agent_state import ToolResult
from service.rag_retriever import RagRetriever


def recommend_dishes_tool(
    query: str,
    budget: float | None = None,
    party_size: int | None = None,
    exclude_allergens: list[str] | None = None,
    limit: int = 3,
    session=None,
    _retriever=None,
) -> ToolResult:
    retriever = _retriever or RagRetriever(session=session)
    message_parts = [query]
    if party_size:
        message_parts.append(f"{party_size}个人")
    if budget:
        message_parts.append(f"{budget}元以内")
    for allergen in exclude_allergens or []:
        message_parts.append(f"不要{allergen}")

    evidence = retriever.retrieve("，".join(message_parts), limit=limit)
    cart_items = [
        {"dish_id": item.source_id, "quantity": 1}
        for item in evidence
        if item.source_type == "dish"
    ]
    return ToolResult.ok_result(
        tool_name="recommend_dishes",
        data={
            "count": len(evidence),
            "cart_candidate_items": cart_items,
        },
        evidence=evidence,
    )
```

- [ ] **Step 4: Run tool tests to verify they pass**

Run:

```bash
python -m pytest tests/service/test_assistant_tools.py -q
```

Expected: PASS with 2 tests.

- [ ] **Step 5: Extend ToolRegistry tests**

Modify `tests/service/test_tool_registry.py` with:

```python
from service.tool_registry import ToolRegistry, ToolSchema


def test_registry_schema_tracks_side_effect_and_confirmation_policy() -> None:
    registry = ToolRegistry()
    registry.register(
        ToolSchema(
            name="prepare_cart_action",
            description="Prepare cart action",
            parameters={"type": "object"},
            side_effect="pending_write",
            requires_confirmation=True,
        ),
        lambda **kwargs: {"ok": True},
    )

    schema = registry.list_schemas()[0]

    assert schema.side_effect == "pending_write"
    assert schema.requires_confirmation is True
```

- [ ] **Step 6: Run registry test to verify it fails**

Run:

```bash
python -m pytest tests/service/test_tool_registry.py::test_registry_schema_tracks_side_effect_and_confirmation_policy -q
```

Expected: FAIL because `ToolSchema` does not accept `side_effect` and `requires_confirmation`.

- [ ] **Step 7: Modify `service/tool_registry.py`**

Update `ToolSchema`:

```python
from dataclasses import dataclass
from typing import Literal


@dataclass
class ToolSchema:
    name: str
    description: str
    parameters: dict
    side_effect: Literal["none", "pending_write", "direct_write"] = "none"
    requires_confirmation: bool = False
```

Keep the existing `ToolRegistry.register`, `execute`, and `list_schemas` method names to avoid breaking current tests.

- [ ] **Step 8: Run registry and tool tests**

Run:

```bash
python -m pytest tests/service/test_tool_registry.py tests/service/test_assistant_tools.py -q
```

Expected: PASS.

- [ ] **Step 9: Commit**

```bash
git add service/tool_registry.py service/tools/catalog_tool.py service/tools/recommendation_tool.py tests/service/test_tool_registry.py tests/service/test_assistant_tools.py
git commit -m "feat: add catalog and recommendation tools"
```

---

## Task 7: Add Cart And Address Staged Tool Helpers

**Files:**
- Modify: `service/tools/cart_tool.py`
- Modify: `service/tools/address_tool.py`
- Test: `tests/service/test_action_tools.py`

- [ ] **Step 1: Write failing staged action tool tests**

Create `tests/service/test_action_tools.py`:

```python
from service.tools.address_tool import build_address_payload, commit_address_action_tool
from service.tools.cart_tool import commit_cart_action_tool


class StubCartService:
    def __init__(self):
        self.added = []

    def add_item(self, user_id, payload):
        self.added.append((user_id, payload.dish_id, payload.quantity))
        return {"success": True, "dish_id": payload.dish_id, "quantity": payload.quantity}


class StubProfileService:
    def create_address(self, user_id, payload):
        return {"id": 7, "label": payload.label, "contact_phone": payload.contact_phone}


def test_commit_cart_action_adds_each_item() -> None:
    service = StubCartService()

    result = commit_cart_action_tool(
        user_id=1,
        items=[{"dish_id": 11, "quantity": 1}, {"dish_id": 12, "quantity": 2}],
        _cart_service=service,
    )

    assert result["success"] is True
    assert service.added == [(1, 11, 1), (1, 12, 2)]


def test_build_address_payload_has_model_dump() -> None:
    payload = build_address_payload(
        label="家",
        contact_name="张三",
        contact_phone="13800000000",
        city="上海市",
        district="静安区",
        detail_address="南京西路818号",
        longitude=121.45,
        latitude=31.22,
        is_default=False,
    )

    assert payload.model_dump()["contact_name"] == "张三"


def test_commit_address_action_uses_profile_service() -> None:
    result = commit_address_action_tool(
        user_id=1,
        address={
            "label": "家",
            "contact_name": "张三",
            "contact_phone": "13800000000",
            "city": "上海市",
            "district": "静安区",
            "detail_address": "南京西路818号",
            "longitude": 121.45,
            "latitude": 31.22,
            "is_default": False,
        },
        _profile_service=StubProfileService(),
    )

    assert result["id"] == 7
    assert result["contact_phone"] == "13800000000"
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python -m pytest tests/service/test_action_tools.py -q
```

Expected: FAIL because helper functions are missing.

- [ ] **Step 3: Modify cart tool**

Append to `service/tools/cart_tool.py`:

```python
def commit_cart_action_tool(
    user_id: int,
    items: list[dict],
    session=None,
    _cart_service=None,
) -> dict:
    service = _cart_service or CartService(session)
    results = []
    for item in items:
        payload = SimpleNamespace(
            dish_id=int(item["dish_id"]),
            quantity=int(item.get("quantity", 1)),
        )
        results.append(service.add_item(user_id, payload))
    return {"success": True, "items": results}
```

- [ ] **Step 4: Modify address tool**

Replace the dynamic `type("AddressPayload", ...)()` approach in `service/tools/address_tool.py` with a payload object that supports `model_dump()`:

```python
from dataclasses import asdict, dataclass

from service.user_profile_service import UserProfileService


@dataclass
class AddressPayload:
    label: str
    contact_name: str
    contact_phone: str
    city: str
    district: str
    detail_address: str
    longitude: float
    latitude: float
    is_default: bool = False

    def model_dump(self) -> dict:
        return asdict(self)


def build_address_payload(**kwargs) -> AddressPayload:
    return AddressPayload(**kwargs)


def commit_address_action_tool(
    user_id: int,
    address: dict,
    session=None,
    _profile_service=None,
) -> dict:
    service = _profile_service or UserProfileService(session)
    payload = build_address_payload(**address)
    return service.create_address(user_id, payload)
```

Keep the existing `save_address_tool()` public function and implement it by delegating to `commit_address_action_tool()`:

```python
def save_address_tool(
    user_id: int,
    label: str,
    contact_name: str,
    contact_phone: str,
    city: str,
    district: str,
    detail_address: str,
    longitude: float,
    latitude: float,
    is_default: bool = False,
    session=None,
    _profile_service=None,
) -> dict:
    return commit_address_action_tool(
        user_id=user_id,
        address={
            "label": label,
            "contact_name": contact_name,
            "contact_phone": contact_phone,
            "city": city,
            "district": district,
            "detail_address": detail_address,
            "longitude": longitude,
            "latitude": latitude,
            "is_default": is_default,
        },
        session=session,
        _profile_service=_profile_service,
    )
```

- [ ] **Step 5: Run tests to verify they pass**

Run:

```bash
python -m pytest tests/service/test_action_tools.py tests/service/test_tool_registry.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add service/tools/cart_tool.py service/tools/address_tool.py tests/service/test_action_tools.py
git commit -m "feat: add staged cart and address action tools"
```

---

## Task 8: Expand Session Store

**Files:**
- Modify: `service/assistant_session_store.py`
- Test: `tests/service/test_assistant_session_store.py`

- [ ] **Step 1: Write failing session store tests**

Create `tests/service/test_assistant_session_store.py`:

```python
from service.agent_state import PendingAction
from service.assistant_session_store import InMemoryAssistantSessionStore


def test_session_store_tracks_slots_and_pending_action() -> None:
    store = InMemoryAssistantSessionStore()
    state = store.get_or_create("s1", user_id=1)
    action = PendingAction(
        action_type="cart_add",
        summary="加入购物车",
        payload={"items": [{"dish_id": 11, "quantity": 1}]},
        requires_user_id=True,
    )

    store.update_agent_state(
        session_id="s1",
        user_id=1,
        last_intent="mixed_task",
        slots={"budget": 100},
        last_evidence_ids=["dish_11"],
        pending_action=action,
    )
    updated = store.get_or_create("s1")

    assert updated.user_id == 1
    assert updated.slots["budget"] == 100
    assert updated.pending_action.action_type == "cart_add"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python -m pytest tests/service/test_assistant_session_store.py -q
```

Expected: FAIL because `get_or_create` does not accept `user_id` and `update_agent_state` is missing.

- [ ] **Step 3: Modify session store**

Update `service/assistant_session_store.py` to use `AssistantTurnState` while keeping the old `update()` method for compatibility:

```python
from uuid import uuid4

from service.agent_state import AssistantTurnState, PendingAction
from service.assistant_models import AssistantParsedQuery


class InMemoryAssistantSessionStore:
    def __init__(self) -> None:
        self._store: dict[str, AssistantTurnState] = {}

    def get_or_create(self, session_id: str | None, user_id: int | None = None) -> AssistantTurnState:
        actual_session_id = session_id or uuid4().hex
        state = self._store.get(actual_session_id)
        if state is None:
            state = AssistantTurnState(session_id=actual_session_id, user_id=user_id)
            self._store[actual_session_id] = state
        elif user_id is not None:
            state.user_id = user_id
        return state

    def update_agent_state(
        self,
        *,
        session_id: str,
        user_id: int | None = None,
        last_intent: str | None = None,
        slots: dict | None = None,
        last_evidence_ids: list[str] | None = None,
        pending_action: PendingAction | None = None,
    ) -> AssistantTurnState:
        state = self._store[session_id]
        if user_id is not None:
            state.user_id = user_id
        if last_intent is not None:
            state.last_intent = last_intent
        if slots:
            state.slots.update(slots)
        if last_evidence_ids is not None:
            state.last_evidence_ids = last_evidence_ids
        if pending_action is not None:
            state.pending_action = pending_action
        return state

    def update(
        self,
        session_id: str,
        user_message: str,
        parsed_query: AssistantParsedQuery | None,
        candidate_ids: list[int],
    ) -> AssistantTurnState:
        return self.update_agent_state(
            session_id=session_id,
            last_evidence_ids=[str(item) for item in candidate_ids],
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
python -m pytest tests/service/test_assistant_session_store.py tests/service/test_assistant_service_v2.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add service/assistant_session_store.py tests/service/test_assistant_session_store.py
git commit -m "feat: expand assistant session state"
```

---

## Task 9: Implement Assistant Orchestrator

**Files:**
- Create: `service/assistant_orchestrator.py`
- Modify: `service/assistant_service.py`
- Modify: `api/schemas.py`
- Test: `tests/service/test_assistant_orchestrator.py`
- Test: `tests/api/test_assistant_routes.py`

- [ ] **Step 1: Add response schema tests**

Modify `tests/api/test_assistant_routes.py` with:

```python
def test_assistant_chat_can_return_pending_action(assistant_test_context, monkeypatch) -> None:
    client, _ = assistant_test_context

    class StubAssistantService:
        def __init__(self, session):
            pass

        def chat(self, request):
            return {
                "session_id": request.session_id or "s1",
                "message": "是否加入购物车？",
                "response_type": "confirmation_required",
                "needs_clarification": False,
                "clarification_question": None,
                "extracted_constraints": None,
                "recommendations": [],
                "comparisons": [],
                "citations": [],
                "suggested_actions": [],
                "pending_action": {
                    "action_id": "pa_1",
                    "type": "cart_add",
                    "summary": "加入 1 道菜",
                    "items": [{"dish_id": 11, "quantity": 1}],
                },
                "executed_actions": [],
            }

    monkeypatch.setattr("api.routes.assistant.AssistantService", StubAssistantService)

    response = client.post("/assistant/chat", json={"message": "确认加购"})

    assert response.status_code == 200
    assert response.json()["response_type"] == "confirmation_required"
    assert response.json()["pending_action"]["action_id"] == "pa_1"
```

- [ ] **Step 2: Run schema test to verify it fails**

Run:

```bash
python -m pytest tests/api/test_assistant_routes.py::test_assistant_chat_can_return_pending_action -q
```

Expected: FAIL because `AssistantChatResponse` does not accept `pending_action`.

- [ ] **Step 3: Modify `api/schemas.py`**

Add response models:

```python
class AssistantPendingActionResponse(BaseModel):
    action_id: str
    type: Literal["cart_add", "address_save"]
    summary: str
    items: list[dict] = Field(default_factory=list)


class AssistantExecutedActionResponse(BaseModel):
    type: str
    success: bool
    message: str
    data: dict = Field(default_factory=dict)
```

Extend `AssistantChatResponse.response_type` literal with `confirmation_required` and add:

```python
    pending_action: AssistantPendingActionResponse | None = None
    executed_actions: list[AssistantExecutedActionResponse] = Field(default_factory=list)
```

- [ ] **Step 4: Run schema test to verify it passes**

Run:

```bash
python -m pytest tests/api/test_assistant_routes.py::test_assistant_chat_can_return_pending_action -q
```

Expected: PASS.

- [ ] **Step 5: Write failing orchestrator tests**

Create `tests/service/test_assistant_orchestrator.py`:

```python
from service.agent_state import AgentDecision, EvidencePack, PendingAction, ToolCall, ToolResult
from service.assistant_orchestrator import AssistantOrchestrator
from service.assistant_session_store import InMemoryAssistantSessionStore


class StubPlanner:
    def __init__(self, decision):
        self.decision = decision

    def plan(self, user_message, session_context):
        return self.decision


class StubRegistry:
    def __init__(self, result):
        self.result = result
        self.executed = []

    def execute(self, name, params):
        self.executed.append((name, params))
        return self.result


def test_orchestrator_returns_clarification_for_missing_slots() -> None:
    store = InMemoryAssistantSessionStore()
    orchestrator = AssistantOrchestrator(
        session=None,
        session_store=store,
        planner=StubPlanner(AgentDecision(
            intent="recommendation",
            missing_slots=["budget", "party_size"],
            clarification_question="请告诉我这顿几个人吃、预算多少？",
        )),
    )

    response = orchestrator.chat(message="推荐川菜", session_id=None, user_id=1)

    assert response["response_type"] == "clarification"
    assert "预算" in response["message"]


def test_orchestrator_creates_pending_cart_action_for_mixed_task() -> None:
    evidence = EvidencePack(
        source_type="dish",
        source_id=11,
        merchant_id=1,
        title="鱼香肉丝｜兰姨小炒",
        facts={"dish_id": 11, "dish_name": "鱼香肉丝", "merchant_name": "兰姨小炒", "price": 28.0},
        why_matched=["匹配川菜"],
        citation="川味麻辣",
    )
    result = ToolResult.ok_result(
        tool_name="recommend_dishes",
        data={"cart_candidate_items": [{"dish_id": 11, "quantity": 1}]},
        evidence=[evidence],
    )
    store = InMemoryAssistantSessionStore()
    orchestrator = AssistantOrchestrator(
        session=None,
        session_store=store,
        planner=StubPlanner(AgentDecision(
            intent="mixed_task",
            tool_plan=[ToolCall(tool_name="recommend_dishes", arguments={"query": "川菜"})],
            needs_confirmation=True,
        )),
        tool_registry=StubRegistry(result),
    )

    response = orchestrator.chat(message="2人100元推荐川菜并加入购物车", session_id="s1", user_id=1)

    assert response["response_type"] == "confirmation_required"
    assert response["pending_action"]["type"] == "cart_add"
    assert store.get_or_create("s1").pending_action is not None


def test_orchestrator_commits_pending_cart_action_on_confirm() -> None:
    store = InMemoryAssistantSessionStore()
    state = store.get_or_create("s1", user_id=1)
    state.pending_action = PendingAction(
        action_type="cart_add",
        summary="加入购物车",
        payload={"items": [{"dish_id": 11, "quantity": 1}]},
        requires_user_id=True,
    )

    class CommitRegistry:
        def execute(self, name, params):
            return {"success": True, "items": [{"dish_id": 11}]}

    orchestrator = AssistantOrchestrator(
        session=None,
        session_store=store,
        planner=StubPlanner(AgentDecision(intent="greeting")),
        tool_registry=CommitRegistry(),
    )

    response = orchestrator.chat(message="确认", session_id="s1", user_id=1)

    assert response["response_type"] == "action_completed"
    assert response["executed_actions"][0]["success"] is True
```

- [ ] **Step 6: Run orchestrator tests to verify they fail**

Run:

```bash
python -m pytest tests/service/test_assistant_orchestrator.py -q
```

Expected: FAIL with missing module.

- [ ] **Step 7: Implement `service/assistant_orchestrator.py`**

Create `service/assistant_orchestrator.py`:

```python
from __future__ import annotations

from service.agent_planner import AgentPlanner
from service.agent_state import EvidencePack, PendingAction, ToolResult
from service.assistant_session_store import InMemoryAssistantSessionStore
from service.confirmation_manager import ConfirmationManager
from service.grounded_responder import GroundedResponder
from service.tool_registry import ToolRegistry, ToolSchema
from service.tools.cart_tool import commit_cart_action_tool
from service.tools.catalog_tool import search_catalog_tool
from service.tools.recommendation_tool import recommend_dishes_tool


class AssistantOrchestrator:
    def __init__(
        self,
        session,
        session_store: InMemoryAssistantSessionStore | None = None,
        planner: AgentPlanner | None = None,
        tool_registry=None,
        confirmation_manager: ConfirmationManager | None = None,
        responder: GroundedResponder | None = None,
    ) -> None:
        self.session = session
        self.session_store = session_store or InMemoryAssistantSessionStore()
        self.planner = planner or AgentPlanner()
        self.confirmation_manager = confirmation_manager or ConfirmationManager()
        self.responder = responder or GroundedResponder()
        self.tool_registry = tool_registry or self._build_registry()

    def _build_registry(self):
        registry = ToolRegistry()
        registry.register(
            ToolSchema("search_catalog", "Search catalog", {"type": "object"}),
            lambda **kwargs: search_catalog_tool(session=self.session, **kwargs),
        )
        registry.register(
            ToolSchema("recommend_dishes", "Recommend dishes", {"type": "object"}),
            lambda **kwargs: recommend_dishes_tool(session=self.session, **kwargs),
        )
        registry.register(
            ToolSchema("commit_cart_action", "Commit cart action", {"type": "object"}, side_effect="direct_write"),
            lambda **kwargs: commit_cart_action_tool(session=self.session, **kwargs),
        )
        return registry

    def chat(self, *, message: str, session_id: str | None, user_id: int | None = None) -> dict:
        state = self.session_store.get_or_create(session_id, user_id=user_id)

        pending = self.confirmation_manager.consume_pending_action(state, message)
        if pending is not None:
            return self._commit_pending_action(state.session_id, user_id, pending)

        decision = self.planner.plan(
            message,
            session_context={
                "slots": state.slots,
                "pending_action": state.pending_action.action_type if state.pending_action else None,
            },
        )

        if decision.intent == "greeting":
            return self._base_response(state.session_id, "你好！我是你的智能点餐助手。", "greeting")

        if decision.intent == "unsupported":
            return self._base_response(state.session_id, "抱歉，我暂时还无法处理这个请求。", "unsupported")

        if decision.missing_slots:
            return self._base_response(
                state.session_id,
                decision.clarification_question or "请补充预算、人数或口味偏好。",
                "clarification",
                needs_clarification=True,
                clarification_question=decision.clarification_question,
            )

        tool_results = []
        evidence: list[EvidencePack] = []
        for call in decision.tool_plan:
            result = self.tool_registry.execute(call.tool_name, call.arguments)
            tool_results.append(result)
            if isinstance(result, ToolResult):
                evidence.extend(result.evidence)

        if decision.intent == "mixed_task" and tool_results:
            cart_items = []
            for result in tool_results:
                if isinstance(result, ToolResult):
                    cart_items.extend(result.data.get("cart_candidate_items", []))
            action = PendingAction(
                action_type="cart_add",
                summary=f"将 {len(cart_items)} 道推荐菜加入购物车",
                payload={"items": cart_items, "source": "recommendation"},
                requires_user_id=True,
            )
            self.confirmation_manager.store_pending_action(state, action)
            return self._recommendation_response(
                state.session_id,
                evidence,
                response_type="confirmation_required",
                pending_action=action,
            )

        if decision.intent in {"recommendation", "knowledge"}:
            return self._recommendation_response(
                state.session_id,
                evidence,
                response_type="recommendation" if decision.intent == "recommendation" else "knowledge",
            )

        return self._base_response(state.session_id, "我已理解你的请求，请补充更多细节。", "clarification")

    def _commit_pending_action(self, session_id: str, user_id: int | None, pending: PendingAction) -> dict:
        if pending.requires_user_id and user_id is None:
            return self._base_response(session_id, "请先登录后再执行该操作。", "clarification")

        if pending.action_type == "cart_add":
            result = self.tool_registry.execute(
                "commit_cart_action",
                {"user_id": user_id, "items": pending.payload["items"]},
            )
            return {
                **self._base_response(session_id, "操作已完成。", "action_completed"),
                "executed_actions": [{
                    "type": "cart_add",
                    "success": bool(result.get("success")),
                    "message": pending.summary,
                    "data": result,
                }],
            }

        return self._base_response(session_id, "暂不支持该确认动作。", "unsupported")

    def _recommendation_response(
        self,
        session_id: str,
        evidence: list[EvidencePack],
        response_type: str,
        pending_action: PendingAction | None = None,
    ) -> dict:
        recommendations = [
            {
                "source_type": item.source_type,
                "merchant_id": item.merchant_id,
                "merchant_name": item.facts.get("merchant_name", item.title),
                "dish_id": item.facts.get("dish_id") if item.source_type == "dish" else None,
                "dish_name": item.facts.get("dish_name") if item.source_type == "dish" else None,
                "price": item.facts.get("price") if item.source_type == "dish" else None,
                "reason": "、".join(item.why_matched),
            }
            for item in evidence
        ]
        citations = [
            {
                "source_type": item.source_type,
                "source_id": item.source_id,
                "title": item.title,
                "snippet": item.citation,
            }
            for item in evidence
        ]
        message = "我根据你的需求找到了这些结果。"
        if pending_action:
            message = f"{message} {pending_action.summary}，是否确认？"
        return {
            **self._base_response(session_id, message, response_type),
            "recommendations": recommendations,
            "citations": citations,
            "pending_action": self._serialize_pending_action(pending_action),
        }

    def _base_response(
        self,
        session_id: str,
        message: str,
        response_type: str,
        needs_clarification: bool = False,
        clarification_question: str | None = None,
    ) -> dict:
        return {
            "session_id": session_id,
            "message": message,
            "response_type": response_type,
            "needs_clarification": needs_clarification,
            "clarification_question": clarification_question,
            "extracted_constraints": None,
            "recommendations": [],
            "comparisons": [],
            "citations": [],
            "suggested_actions": [],
            "pending_action": None,
            "executed_actions": [],
        }

    def _serialize_pending_action(self, pending_action: PendingAction | None) -> dict | None:
        if pending_action is None:
            return None
        return {
            "action_id": pending_action.action_id,
            "type": pending_action.action_type,
            "summary": pending_action.summary,
            "items": pending_action.payload.get("items", []),
        }
```

- [ ] **Step 8: Modify `service/assistant_service.py` to delegate**

Replace the body of `AssistantService.chat()` with:

```python
    def chat(self, request: AssistantChatRequest) -> AssistantChatResponse:
        orchestrator = AssistantOrchestrator(
            session=self.session,
            session_store=self.session_store,
        )
        return orchestrator.chat(
            message=request.message,
            session_id=request.session_id,
            user_id=request.user_id,
        )
```

Add import:

```python
from service.assistant_orchestrator import AssistantOrchestrator
```

Keep `build_assistant_health()` unchanged.

- [ ] **Step 9: Run orchestrator and assistant route tests**

Run:

```bash
python -m pytest tests/service/test_assistant_orchestrator.py tests/api/test_assistant_routes.py -q
```

Expected: PASS.

- [ ] **Step 10: Commit**

```bash
git add service/assistant_orchestrator.py service/assistant_service.py api/schemas.py tests/service/test_assistant_orchestrator.py tests/api/test_assistant_routes.py
git commit -m "feat: orchestrate assistant agent workflow"
```

---

## Task 10: Add Address Agent Flow

**Files:**
- Modify: `service/assistant_orchestrator.py`
- Modify: `service/agent_planner.py`
- Modify: `service/tools/address_tool.py`
- Test: `tests/service/test_address_agent_flow.py`

- [ ] **Step 1: Write failing address flow tests**

Create `tests/service/test_address_agent_flow.py`:

```python
from service.agent_state import AgentDecision, PendingAction, ToolCall, ToolResult
from service.assistant_orchestrator import AssistantOrchestrator
from service.assistant_session_store import InMemoryAssistantSessionStore


class StubPlanner:
    def plan(self, user_message, session_context):
        return AgentDecision(
            intent="address_action",
            tool_plan=[ToolCall(tool_name="parse_address", arguments={"message": user_message})],
            needs_confirmation=True,
        )


class StubRegistry:
    def execute(self, name, params):
        if name == "parse_address":
            return ToolResult.ok_result(
                tool_name="parse_address",
                data={
                    "address": {
                        "label": "家",
                        "contact_name": "张三",
                        "contact_phone": "13800000000",
                        "city": "上海市",
                        "district": "静安区",
                        "detail_address": "南京西路818号",
                        "longitude": 121.45,
                        "latitude": 31.22,
                        "is_default": False,
                    }
                },
            )
        if name == "commit_address_action":
            return {"id": 7, "label": "家"}
        raise AssertionError(name)


def test_address_request_creates_pending_address_action() -> None:
    store = InMemoryAssistantSessionStore()
    orchestrator = AssistantOrchestrator(
        session=None,
        session_store=store,
        planner=StubPlanner(),
        tool_registry=StubRegistry(),
    )

    response = orchestrator.chat(
        message="帮我将以下地址加入地址管理：上海市静安区南京西路818号，联系人张三，电话13800000000",
        session_id="s1",
        user_id=1,
    )

    assert response["response_type"] == "confirmation_required"
    assert response["pending_action"]["type"] == "address_save"
    assert store.get_or_create("s1").pending_action.action_type == "address_save"


def test_confirm_address_action_commits_address() -> None:
    store = InMemoryAssistantSessionStore()
    state = store.get_or_create("s1", user_id=1)
    state.pending_action = PendingAction(
        action_type="address_save",
        summary="保存地址",
        payload={"address": {"label": "家"}},
        requires_user_id=True,
    )
    orchestrator = AssistantOrchestrator(
        session=None,
        session_store=store,
        planner=StubPlanner(),
        tool_registry=StubRegistry(),
    )

    response = orchestrator.chat(message="确认", session_id="s1", user_id=1)

    assert response["response_type"] == "action_completed"
    assert response["executed_actions"][0]["type"] == "address_save"
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python -m pytest tests/service/test_address_agent_flow.py -q
```

Expected: FAIL because orchestrator does not yet handle `address_action`.

- [ ] **Step 3: Add parse address helper**

Add to `service/tools/address_tool.py`:

```python
import re

from service.agent_state import ToolResult


PHONE_PATTERN = re.compile(r"1[3-9]\d{9}")


def parse_address_tool(message: str) -> ToolResult:
    phone_match = PHONE_PATTERN.search(message)
    contact_phone = phone_match.group(0) if phone_match else ""
    contact_name = ""
    name_match = re.search(r"联系人[:：]?([\u4e00-\u9fa5]{2,4})", message)
    if name_match:
        contact_name = name_match.group(1)

    city = "上海市" if "上海" in message else ""
    district = "静安区" if "静安" in message else ""
    detail = message
    for token in ("帮我将以下地址加入地址管理：", "帮我将以下地址加入地址管理:", f"联系人{contact_name}", contact_phone):
        detail = detail.replace(token, "")
    detail = detail.strip(" ，,。")

    missing = []
    if not contact_phone:
        missing.append("contact_phone")
    if not contact_name:
        missing.append("contact_name")
    if not detail:
        missing.append("detail_address")

    if missing:
        return ToolResult.error_result(
            tool_name="parse_address",
            code="MISSING_ADDRESS_FIELDS",
            message=f"缺少字段：{', '.join(missing)}",
        )

    return ToolResult.ok_result(
        tool_name="parse_address",
        data={
            "address": {
                "label": "家",
                "contact_name": contact_name,
                "contact_phone": contact_phone,
                "city": city or "上海市",
                "district": district or "静安区",
                "detail_address": detail,
                "longitude": 121.45,
                "latitude": 31.22,
                "is_default": False,
            }
        },
    )
```

- [ ] **Step 4: Register and handle address actions in orchestrator**

In `_build_registry()`, register:

```python
from service.tools.address_tool import commit_address_action_tool, parse_address_tool

registry.register(
    ToolSchema("parse_address", "Parse address", {"type": "object"}),
    lambda **kwargs: parse_address_tool(**kwargs),
)
registry.register(
    ToolSchema("commit_address_action", "Commit address action", {"type": "object"}, side_effect="direct_write"),
    lambda **kwargs: commit_address_action_tool(session=self.session, **kwargs),
)
```

In `chat()`, after tool execution, add:

```python
        if decision.intent == "address_action" and tool_results:
            first = tool_results[0]
            if isinstance(first, ToolResult) and not first.ok:
                return self._base_response(state.session_id, first.error.message, "clarification", needs_clarification=True)
            address = first.data["address"]
            action = PendingAction(
                action_type="address_save",
                summary=f"保存地址：{address['city']}{address['district']}{address['detail_address']}",
                payload={"address": address},
                requires_user_id=True,
            )
            self.confirmation_manager.store_pending_action(state, action)
            return {
                **self._base_response(state.session_id, f"{action.summary}，是否确认？", "confirmation_required"),
                "pending_action": self._serialize_pending_action(action),
            }
```

In `_commit_pending_action()`, add:

```python
        if pending.action_type == "address_save":
            result = self.tool_registry.execute(
                "commit_address_action",
                {"user_id": user_id, "address": pending.payload["address"]},
            )
            return {
                **self._base_response(session_id, "地址已保存。", "action_completed"),
                "executed_actions": [{
                    "type": "address_save",
                    "success": True,
                    "message": pending.summary,
                    "data": result,
                }],
            }
```

- [ ] **Step 5: Run address flow tests**

Run:

```bash
python -m pytest tests/service/test_address_agent_flow.py tests/service/test_action_tools.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add service/assistant_orchestrator.py service/tools/address_tool.py tests/service/test_address_agent_flow.py
git commit -m "feat: add address agent flow"
```

---

## Task 11: Frontend Confirmation Rendering

**Files:**
- Modify: `ui/src/composables/useAssistant.js`
- Modify: `ui/src/components/home/FloatingAssistant.vue`
- Modify: `ui/src/__tests__/floatingAssistant.test.js`

- [ ] **Step 1: Write failing frontend tests**

Modify `ui/src/__tests__/floatingAssistant.test.js` with:

```javascript
import { mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'
import FloatingAssistant from '../components/home/FloatingAssistant.vue'
import { chatWithAssistant } from '../api/assistant'

vi.mock('../api/assistant', () => ({
  chatWithAssistant: vi.fn(),
}))

describe('FloatingAssistant pending actions', () => {
  it('renders pending action confirmation', async () => {
    chatWithAssistant.mockResolvedValueOnce({
      session_id: 's1',
      message: '是否加入购物车？',
      response_type: 'confirmation_required',
      recommendations: [],
      comparisons: [],
      citations: [],
      suggested_actions: [],
      pending_action: {
        action_id: 'pa_1',
        type: 'cart_add',
        summary: '将 1 道菜加入购物车',
        items: [{ dish_id: 11, quantity: 1 }],
      },
      executed_actions: [],
    })

    const wrapper = mount(FloatingAssistant, {
      global: {
        stubs: ['el-scrollbar', 'el-input', 'el-button', 'el-tag'],
      },
    })

    await wrapper.find('input').setValue('推荐川菜并加入购物车')
    await wrapper.find('button').trigger('click')
    await Promise.resolve()
    await Promise.resolve()

    expect(wrapper.text()).toContain('待确认操作')
    expect(wrapper.text()).toContain('将 1 道菜加入购物车')
  })
})
```

- [ ] **Step 2: Run frontend test to verify it fails**

Run:

```bash
npm --prefix ui test -- src/__tests__/floatingAssistant.test.js --run
```

Expected: FAIL because pending action is not rendered.

- [ ] **Step 3: Modify `ui/src/composables/useAssistant.js`**

Add refs:

```javascript
  const pendingAction = ref(null)
  const executedActions = ref([])
```

Clear before request:

```javascript
    pendingAction.value = null
    executedActions.value = []
```

Set after response:

```javascript
      pendingAction.value = response.pending_action || null
      executedActions.value = response.executed_actions || []
```

Return them:

```javascript
    pendingAction,
    executedActions,
```

- [ ] **Step 4: Modify `FloatingAssistant.vue`**

Destructure:

```javascript
  pendingAction,
  executedActions,
```

Add template block before suggested actions:

```vue
      <div v-if="pendingAction" class="assistant-section">
        <div class="assistant-section-title">待确认操作</div>
        <div class="assistant-card">
          <div class="assistant-card-title">{{ pendingAction.summary }}</div>
          <div class="assistant-card-body">回复“确认”执行，或回复“取消”放弃。</div>
        </div>
      </div>

      <div v-if="executedActions.length" class="assistant-section">
        <div class="assistant-section-title">已完成操作</div>
        <div v-for="item in executedActions" :key="`${item.type}-${item.message}`" class="assistant-card">
          <div class="assistant-card-title">{{ item.message }}</div>
          <div class="assistant-card-body">{{ item.success ? '操作成功' : '操作失败' }}</div>
        </div>
      </div>
```

- [ ] **Step 5: Run frontend test**

Run:

```bash
npm --prefix ui test -- src/__tests__/floatingAssistant.test.js --run
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add ui/src/composables/useAssistant.js ui/src/components/home/FloatingAssistant.vue ui/src/__tests__/floatingAssistant.test.js
git commit -m "feat: render assistant pending actions"
```

---

## Task 12: RAG Evaluation Script

**Files:**
- Create: `tests/eval/assistant_rag_cases.jsonl`
- Create: `tools/evaluate_assistant_rag.py`
- Test: `tests/service/test_rag_evaluator.py`

- [ ] **Step 1: Write failing evaluator test**

Create `tests/service/test_rag_evaluator.py`:

```python
from tools.evaluate_assistant_rag import evaluate_cases


class StubRetriever:
    def retrieve(self, query, limit=5):
        return [
            type("Evidence", (), {
                "source_type": "dish",
                "source_id": 11,
                "facts": {"price": 28.0, "allergens": [], "cuisine_type": "川味麻辣"},
            })()
        ]


def test_evaluate_cases_reports_recall_and_constraint_pass_rate() -> None:
    cases = [
        {
            "query": "推荐几种川菜，2个人吃，100元以内，不要花生",
            "expected_source_ids": [11],
            "constraints": {"budget_max": 100, "party_size": 2, "exclude_allergens": ["花生"]},
        }
    ]

    metrics = evaluate_cases(cases, retriever=StubRetriever())

    assert metrics["case_count"] == 1
    assert metrics["recall_at_5"] == 1.0
    assert metrics["constraint_pass_rate"] == 1.0
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python -m pytest tests/service/test_rag_evaluator.py -q
```

Expected: FAIL because evaluator module is missing.

- [ ] **Step 3: Create eval cases**

Create `tests/eval/assistant_rag_cases.jsonl`:

```jsonl
{"query":"推荐几种川菜，2个人吃，100元以内，不要花生","expected_source_ids":[11],"constraints":{"budget_max":100,"party_size":2,"exclude_allergens":["花生"]}}
{"query":"有哪些咖啡甜品店？几点营业？","expected_source_type":"merchant","constraints":{}}
{"query":"想吃下饭一点的湘菜","expected_source_type":"dish","constraints":{"cuisine_types":["湘菜"]}}
```

- [ ] **Step 4: Implement evaluator**

Create `tools/evaluate_assistant_rag.py`:

```python
from __future__ import annotations

import json
from pathlib import Path

from api.db import SessionLocal
from service.rag_retriever import RagRetriever


def _passes_constraints(evidence, constraints: dict) -> bool:
    facts = getattr(evidence, "facts", {})
    budget = constraints.get("budget_max")
    party_size = constraints.get("party_size") or 1
    if budget is not None and facts.get("price") is not None:
        if float(facts["price"]) * int(party_size) > float(budget):
            return False

    exclude_allergens = constraints.get("exclude_allergens") or []
    allergens = set(facts.get("allergens") or [])
    if any(item in allergens for item in exclude_allergens):
        return False

    cuisine_types = constraints.get("cuisine_types") or []
    if cuisine_types and facts.get("cuisine_type") not in cuisine_types:
        return False

    return True


def evaluate_cases(cases: list[dict], retriever) -> dict:
    recall_hits = 0
    constraint_passes = 0
    for case in cases:
        evidence = retriever.retrieve(case["query"], limit=5)
        expected_ids = set(case.get("expected_source_ids") or [])
        if expected_ids:
            retrieved_ids = {item.source_id for item in evidence}
            recall_hits += int(bool(expected_ids & retrieved_ids))
        elif case.get("expected_source_type"):
            recall_hits += int(any(item.source_type == case["expected_source_type"] for item in evidence))
        else:
            recall_hits += int(bool(evidence))

        constraints = case.get("constraints") or {}
        constraint_passes += int(all(_passes_constraints(item, constraints) for item in evidence))

    case_count = len(cases)
    return {
        "case_count": case_count,
        "recall_at_5": recall_hits / case_count if case_count else 0.0,
        "constraint_pass_rate": constraint_passes / case_count if case_count else 0.0,
    }


def load_cases(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> int:
    cases_path = Path("tests/eval/assistant_rag_cases.jsonl")
    cases = load_cases(cases_path)
    session = SessionLocal()
    try:
        metrics = evaluate_cases(cases, retriever=RagRetriever(session=session))
    finally:
        session.close()
    print(json.dumps(metrics, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 5: Run evaluator test**

Run:

```bash
python -m pytest tests/service/test_rag_evaluator.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add tools/evaluate_assistant_rag.py tests/eval/assistant_rag_cases.jsonl tests/service/test_rag_evaluator.py
git commit -m "feat: add assistant rag evaluation"
```

---

## Task 13: Integration Verification And Documentation

**Files:**
- Modify: `README.md`
- Modify: `ui/README.md`
- Test: existing backend and frontend suites

- [ ] **Step 1: Update root README with assistant architecture**

Add this section to `README.md`:

```markdown
## Smart Assistant Agent + RAG

The assistant uses a controlled LLM Agent architecture:

1. Agent Planner classifies intent and emits a structured tool plan.
2. Tool Registry executes catalog search, recommendation, cart, and address tools.
3. Hybrid RAG combines query rewrite, Pinecone dense recall, metadata/keyword recall, SQL hard filters, reranking, and citation evidence.
4. Confirmation Manager gates side-effect operations such as cart updates and address saves.
5. Evaluation cases report recall@5 and constraint pass rate.

Focused verification:

```bash
python -m pytest tests/service/test_assistant_orchestrator.py tests/service/test_rag_retriever.py -q
python tools/evaluate_assistant_rag.py
npm --prefix ui test -- src/__tests__/floatingAssistant.test.js --run
```
```

- [ ] **Step 2: Update `ui/README.md` current API section**

Replace old API paths with:

```markdown
## API 对接

前端通过 `/api` 代理访问后端：

- `POST /api/auth/login`
- `POST /api/auth/register`
- `GET /api/catalog/merchants`
- `GET /api/catalog/merchants/{merchant_id}/dishes`
- `GET /api/cart`
- `POST /api/cart/items`
- `GET /api/addresses`
- `POST /api/addresses`
- `POST /api/assistant/chat`
- `GET /api/assistant/health`
```

- [ ] **Step 3: Run backend focused tests**

Run:

```bash
python -m pytest tests/service/test_agent_state.py tests/service/test_confirmation_manager.py tests/service/test_agent_planner.py tests/service/test_rag_query_rewriter.py tests/service/test_rag_reranker.py tests/service/test_rag_retriever.py tests/service/test_assistant_tools.py tests/service/test_action_tools.py tests/service/test_assistant_session_store.py tests/service/test_assistant_orchestrator.py tests/service/test_address_agent_flow.py tests/service/test_rag_evaluator.py tests/api/test_assistant_routes.py -q
```

Expected: PASS.

- [ ] **Step 4: Run frontend focused tests**

Run:

```bash
npm --prefix ui test -- src/__tests__/floatingAssistant.test.js --run
```

Expected: PASS.

- [ ] **Step 5: Run RAG evaluation script**

Run:

```bash
python tools/evaluate_assistant_rag.py
```

Expected: prints JSON containing `case_count`, `recall_at_5`, and `constraint_pass_rate`.

- [ ] **Step 6: Commit**

```bash
git add README.md ui/README.md
git commit -m "docs: document assistant agent rag architecture"
```

---

## Final Verification Checklist

- [ ] `POST /assistant/chat` with `推荐川菜` returns clarification.
- [ ] Follow-up `2个人，100以内，不要花生` returns valid recommendations with citations.
- [ ] `推荐川菜并加入购物车` creates `pending_action`.
- [ ] `确认` commits pending cart action.
- [ ] Explicit unique dish add updates cart directly.
- [ ] Address save request creates pending address action.
- [ ] Address confirmation writes an address.
- [ ] RAG evaluator reports recall and constraint metrics.
- [ ] Frontend renders recommendations, citations, pending actions, and executed actions.
- [ ] Existing unrelated user changes in `run.py`, `service/agent_core.py`, `service/assistant_retriever.py`, and `tools/assistant_vector_store.py` are not reverted.
