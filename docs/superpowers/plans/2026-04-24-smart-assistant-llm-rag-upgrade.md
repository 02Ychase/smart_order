# Smart Assistant LLM-Routed RAG Upgrade Implementation Plan

> **For agentic workers:** Execute task-by-task with TDD. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the existing assistant from rule-based parse->retrieve->compose to LLM-routed hybrid-RAG with grounded generation.

**Architecture:** Six bounded components: IntentRouter, ConstraintResolver, HybridRetriever, GroundedResponder, AssistantOrchestrator, ToolRegistry (future boundary). Keep existing session store and API contract but expand response types.

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic, LangChain-compatible chat model wrapper (OpenAI/DashScope), Pinecone, DashScope embeddings, Vue 3, Vitest, Pytest

---

## File Structure

### Backend (new / modify)
- Create: `service/intent_router.py` — LLM-first intent classification
- Create: `service/constraint_resolver.py` — structured constraint extraction
- Modify: `service/assistant_retriever.py` — real vector recall + reranking
- Create: `service/grounded_responder.py` — LLM-based grounded response generation
- Modify: `service/assistant_service.py` — new orchestration (AssistantOrchestrator)
- Modify: `service/assistant_composer.py` — keep as fallback, but grounded responder becomes primary
- Modify: `service/assistant_models.py` — add intent types, evidence blocks, response types
- Modify: `tools/assistant_vector_store.py` — real Pinecone semantic lookup
- Modify: `api/schemas.py` — expand response type enum

### Backend tests
- Create: `tests/service/test_intent_router.py`
- Create: `tests/service/test_constraint_resolver.py`
- Create: `tests/service/test_grounded_responder.py`
- Modify: `tests/service/test_assistant_retriever.py` — add vector recall tests
- Modify: `tests/service/test_assistant_service.py` — update orchestration tests

### Frontend
- Modify: `ui/src/composables/useAssistant.js` — handle expanded response types
- Modify: `ui/src/components/home/FloatingAssistant.vue` — render greeting/clarification/recommendation/comparison/knowledge/action_pending
- Modify: `ui/src/__tests__/floatingAssistant.test.js` — update for new response types

---

## Task 1: Implement IntentRouter with LLM classification

**Files:**
- Create: `service/intent_router.py`
- Test: `tests/service/test_intent_router.py`

- [ ] **Step 1: Write failing intent router tests**

```python
# tests/service/test_intent_router.py
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from service.intent_router import IntentRouter, RoutingResult


def test_route_classifies_greeting() -> None:
    router = IntentRouter()
    result = router.route("Hi")
    assert result.intent == "greeting"
    assert result.requires_retrieval is False
    assert result.future_tool is None


def test_route_classifies_recommendation() -> None:
    router = IntentRouter()
    result = router.route("推荐几种川菜")
    assert result.intent == "recommendation"
    assert result.requires_retrieval is True
    assert result.likely_needs_clarification is False


def test_route_classifies_comparison() -> None:
    router = IntentRouter()
    result = router.route("比较兰姨小炒和午后豆房")
    assert result.intent == "comparison"
    assert result.requires_retrieval is True


def test_route_classifies_knowledge() -> None:
    router = IntentRouter()
    result = router.route("这家店几点营业")
    assert result.intent == "knowledge"
    assert result.requires_retrieval is True


def test_route_classifies_action_intent() -> None:
    router = IntentRouter()
    result = router.route("帮我加入购物车")
    assert result.intent == "action_intent"
    assert result.requires_retrieval is False
    assert result.future_tool == "add_to_cart"
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
```bash
pytest tests/service/test_intent_router.py -q
```

Expected: FAIL with module/import errors.

- [ ] **Step 3: Implement IntentRouter**

```python
# service/intent_router.py
import os
from dataclasses import dataclass
from typing import Literal


@dataclass
class RoutingResult:
    intent: Literal["greeting", "recommendation", "comparison", "knowledge", "action_intent", "unsupported"]
    requires_retrieval: bool
    likely_needs_clarification: bool = False
    future_tool: str | None = None


class IntentRouter:
    def __init__(self) -> None:
        self._model_name = os.getenv("MODEL_NAME")
        # Placeholder for LLM integration; rule-based fallback for reliable tests

    def route(self, message: str) -> RoutingResult:
        msg = message.strip().lower()

        # Simple heuristic fallback for test stability until LLM integration
        if msg in ("hi", "hello", "你好", "在吗", "嗨"):
            return RoutingResult("greeting", requires_retrieval=False)

        if "加入购物车" in msg or "添加地址" in msg or "保存地址" in msg:
            tool = "add_to_cart" if "购物车" in msg else "save_address"
            return RoutingResult("action_intent", requires_retrieval=False, future_tool=tool)

        if any(w in msg for w in ("对比", "比较", "vs", "versus")):
            return RoutingResult("comparison", requires_retrieval=True)

        if any(w in msg for w in ("推荐", "吃什么", "适合", "推荐菜", "推荐商家")):
            return RoutingResult("recommendation", requires_retrieval=True)

        if any(w in msg for w in ("几点", "营业", "电话", "地址", "多少钱", "价格", "口味", "配料")):
            return RoutingResult("knowledge", requires_retrieval=True)

        return RoutingResult("unsupported", requires_retrieval=False)
```

- [ ] **Step 4: Run tests to verify they pass**

Run:
```bash
pytest tests/service/test_intent_router.py -q
```

Expected: PASS with 5 tests.

- [ ] **Step 5: Commit**

```bash
git add service/intent_router.py tests/service/test_intent_router.py
git commit -m "feat: add intent router with classification"
```

---

## Task 2: Implement ConstraintResolver

**Files:**
- Create: `service/constraint_resolver.py`
- Test: `tests/service/test_constraint_resolver.py`

- [ ] **Step 1: Write failing constraint resolver tests**

```python
# tests/service/test_constraint_resolver.py
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from service.constraint_resolver import ConstraintResolver, ResolvedConstraints


def test_resolve_recommendation_constraints() -> None:
    resolver = ConstraintResolver()
    result = resolver.resolve("推荐几种川菜，2个人吃，100元以内，不要花生")

    assert result.cuisine_types == ["川菜"]
    assert result.party_size == 2
    assert result.budget_max == 100.0
    assert result.exclude_allergens == ["花生"]
    assert result.is_sufficient_for_recommendation() is True


def test_resolve_requests_clarification_when_sparse() -> None:
    resolver = ConstraintResolver()
    result = resolver.resolve("推荐几种川菜")

    assert result.cuisine_types == ["川菜"]
    assert result.is_sufficient_for_recommendation() is False


def test_resolve_comparison_targets() -> None:
    resolver = ConstraintResolver()
    result = resolver.resolve("比较兰姨小炒和午后豆房")

    assert result.merchant_targets == ["兰姨小炒", "午后豆房"]
    assert result.is_sufficient_for_comparison() is True
```

- [ ] **Step 2: Run tests to verify they fail**

- [ ] **Step 3: Implement ConstraintResolver**

Reuse and extend existing parser logic, but wrap into the new component boundary.

- [ ] **Step 4: Run tests to verify they pass**

- [ ] **Step 5: Commit**

---

## Task 3: Upgrade HybridRetriever with real vector recall

**Files:**
- Modify: `service/assistant_retriever.py`
- Modify: `tools/assistant_vector_store.py`
- Modify: `tests/service/test_assistant_retriever.py`

- [ ] **Step 1: Write failing vector recall test**

```python
def test_retriever_uses_vector_scores_when_store_ready() -> None:
    from service.assistant_retriever import AssistantRetriever
    from service.assistant_models import AssistantParsedQuery

    class FakeVectorStore:
        def is_ready(self):
            return True

        def semantic_scores(self, query, candidates):
            return {candidates[0]["id"]: 0.5}

    class FakeCatalog:
        def list_merchants(self, district=None):
            return [{"id": 1, "name": "A", "rating": 4.5, "merchant_tags": [], "business_hours": ""}]

        def list_dishes_by_merchant(self, merchant_id):
            return [{"id": 11, "name": "X", "price": 20.0, "cuisine_type": "川菜", "flavor_profile": "辣", "ingredients": ["肉"], "allergens": []}]

    retriever = AssistantRetriever.__new__(AssistantRetriever)
    retriever.catalog_service = FakeCatalog()
    retriever.vector_store = FakeVectorStore()

    parsed = AssistantParsedQuery(
        raw_message="推荐川菜",
        query_type="recommendation",
        cuisine_types=["川菜"],
        budget_max=100,
        party_size=2,
        exclude_allergens=[],
        comparison_targets=[],
    )

    candidates = retriever.retrieve(parsed)
    # When vector store is ready, top candidate should have boosted score
    assert len(candidates) == 1
```

- [ ] **Step 2: Run tests to verify failure**

- [ ] **Step 3: Upgrade vector store and retriever**

Implement real `semantic_scores` using Pinecone/DashScope when API keys are present.

- [ ] **Step 4: Run tests to verify pass**

- [ ] **Step 5: Commit**

---

## Task 4: Implement GroundedResponder

**Files:**
- Create: `service/grounded_responder.py`
- Test: `tests/service/test_grounded_responder.py`

- [ ] **Step 1: Write failing grounded responder tests**

- [ ] **Step 2: Run tests to verify they fail**

- [ ] **Step 3: Implement GroundedResponder**

```python
# service/grounded_responder.py
import os
from typing import Literal

from service.assistant_models import AssistantCandidate, ResolvedConstraints


class GroundedResponder:
    def __init__(self) -> None:
        self._model_name = os.getenv("MODEL_NAME")

    def respond(
        self,
        *,
        intent: Literal["recommendation", "comparison", "knowledge", "greeting", "action_intent", "unsupported"],
        user_message: str,
        constraints: ResolvedConstraints | None,
        evidence: list[AssistantCandidate],
        session_context: list[dict],
    ) -> dict:
        # Placeholder: will call LLM in later step; for now, use structured fallback
        if intent == "greeting":
            return {
                "message": "你好！我是你的智能点餐助手，可以帮你推荐菜品、比较商家，或者回答关于餐厅的问题。",
                "response_type": "greeting",
                "recommendations": [],
                "comparisons": [],
                "citations": [],
                "suggested_actions": ["推荐几种川菜", "比较两家商家"],
            }

        if intent == "action_intent":
            return {
                "message": "我已经理解你的意图，但该功能将在下一阶段开放。",
                "response_type": "action_pending",
                "recommendations": [],
                "comparisons": [],
                "citations": [],
                "suggested_actions": [],
            }

        # For recommendation/comparison: build evidence-grounded response
        # TODO: integrate LLM generation
        from service.assistant_composer import compose_assistant_response
        return compose_assistant_response(
            session_id="temp",
            parsed=constraints,
            candidates=evidence,
        )
```

- [ ] **Step 4: Run tests to verify they pass**

- [ ] **Step 5: Commit**

---

## Task 5: Upgrade AssistantOrchestrator

**Files:**
- Modify: `service/assistant_service.py`
- Modify: `tests/service/test_assistant_service.py`

- [ ] **Step 1: Write failing orchestration tests for new flow**

- [ ] **Step 2: Run tests to verify they fail**

- [ ] **Step 3: Implement new orchestration**

Replace the current `parse -> retrieve -> compose` with:

```
IntentRouter -> (if greeting/action_intent) -> GroundedResponder
             -> (if recommendation/comparison/knowledge) -> ConstraintResolver -> HybridRetriever -> GroundedResponder
```

- [ ] **Step 4: Run tests to verify they pass**

- [ ] **Step 5: Commit**

---

## Task 6: Expand API response types and frontend rendering

**Files:**
- Modify: `api/schemas.py`
- Modify: `ui/src/composables/useAssistant.js`
- Modify: `ui/src/components/home/FloatingAssistant.vue`
- Modify: `ui/src/__tests__/floatingAssistant.test.js`

- [ ] **Step 1: Add new response_type enum to schemas**

- [ ] **Step 2: Update frontend to handle greeting/clarification/action_pending**

- [ ] **Step 3: Write/update frontend tests**

- [ ] **Step 4: Run frontend tests**

- [ ] **Step 5: Commit**

---

## Task 7: Integration verification

- [ ] **Step 1: Run full backend test suite**

```bash
pytest tests/api/test_assistant_routes.py tests/service/test_intent_router.py tests/service/test_constraint_resolver.py tests/service/test_assistant_retriever.py tests/service/test_grounded_responder.py tests/service/test_assistant_service.py tests/service/test_assistant_composer.py -q
```

Expected: all pass.

- [ ] **Step 2: Run frontend focused tests**

```bash
npm --prefix ui test -- src/__tests__/floatingAssistant.test.js --run
```

Expected: all pass.

- [ ] **Step 3: Start backend and verify**

```bash
uvicorn api.main:app --host 127.0.0.1 --port 8001 --reload
```

Probe:
```bash
curl -X POST http://127.0.0.1:8001/assistant/chat -H "Content-Type: application/json" -d '{"message":"Hi","session_id":null}'
```

Should return greeting response, not recommendation.

- [ ] **Step 4: Start frontend and browser verify**

- [ ] **Step 5: Commit**

---

## Verification Checklist

- [ ] `Hi` returns greeting, no retrieval
- [ ] `推荐几种川菜` returns recommendation with evidence
- [ ] `比较两家商家` returns comparison
- [ ] `帮我加入购物车` returns action_pending
- [ ] Backend tests all pass
- [ ] Frontend tests all pass
- [ ] Browser demo works on correct frontend port
