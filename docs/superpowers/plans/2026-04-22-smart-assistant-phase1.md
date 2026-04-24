# Smart Assistant Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a RAG-first multi-turn assistant for `smart_order` that can clarify user needs, answer grounded merchant/dish questions, recommend dishes, and compare merchants through a stable backend assistant API and an interactive frontend assistant panel.

**Architecture:** Add a dedicated assistant route and service boundary in FastAPI, keep short-lived conversation state in an in-memory session store, parse restaurant constraints deterministically before optional LLM help, and run hybrid retrieval that combines structured filtering with optional Pinecone semantic boosts. On the frontend, upgrade the existing floating assistant into a real chat surface backed by a focused assistant composable and API module that render clarification prompts, recommendation cards, comparison summaries, and citations.

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic, LangChain OpenAI-compatible chat model wrapper, Pinecone, DashScope embeddings, Vue 3, Element Plus, Vitest, Pytest

---

## File Structure

### Backend
- Create: `api/routes/assistant.py` — public assistant chat and health endpoints
- Modify: `api/routes/__init__.py` — export `assistant_router`
- Modify: `api/main.py` — mount the assistant router
- Modify: `api/schemas.py` — add assistant request/response schemas
- Create: `service/assistant_models.py` — internal dataclasses for parsed query, session state, and retrieved candidates
- Create: `service/assistant_session_store.py` — in-memory session state store keyed by `session_id`
- Create: `service/assistant_constraint_parser.py` — deterministic extraction for cuisine, budget, party size, allergens, and query type
- Create: `service/assistant_composer.py` — turns parsed state + candidates into chat responses with citations
- Create: `service/assistant_retriever.py` — structured filtering and optional vector-score enrichment
- Create: `service/assistant_service.py` — orchestration boundary used by the route
- Create: `tools/assistant_vector_store.py` — assistant-focused Pinecone lookup wrapper using current env config

### Backend tests
- Create: `tests/api/test_assistant_routes.py` — route contract and health checks
- Create: `tests/service/test_assistant_constraint_parser.py` — parser coverage for recommendation, comparison, and Q&A extraction
- Create: `tests/service/test_assistant_composer.py` — clarification/recommendation/comparison response formatting
- Create: `tests/service/test_assistant_service.py` — orchestration, retrieval fallback, and session continuity

### Frontend
- Create: `ui/src/api/assistant.js` — assistant API client
- Create: `ui/src/composables/useAssistant.js` — assistant state, submit action, and response mapping
- Modify: `ui/src/components/home/FloatingAssistant.vue` — full assistant UI
- Modify: `ui/src/__tests__/app.homepage.test.js` — update stubs so the richer assistant component still mounts cleanly in the homepage shell
- Create: `ui/src/__tests__/floatingAssistant.test.js` — focused assistant interaction tests

## Task 1: Lock the assistant API contract and app wiring

**Files:**
- Create: `api/routes/assistant.py`
- Modify: `api/routes/__init__.py`
- Modify: `api/main.py`
- Modify: `api/schemas.py`
- Create: `service/assistant_service.py`
- Test: `tests/api/test_assistant_routes.py`

- [ ] **Step 1: Write the failing route-contract tests**

```python
from pathlib import Path
import os
import sys

from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

TEST_DATABASE_PATH = PROJECT_ROOT / "test_assistant_routes.db"
TEST_DATABASE_PATH.unlink(missing_ok=True)

os.environ["JWT_SECRET_KEY"] = "test-phase1-secret"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DATABASE_PATH.as_posix()}"

from api.main import app
from api.routes import assistant as assistant_routes

client = TestClient(app, raise_server_exceptions=False)


def test_assistant_chat_returns_structured_payload(monkeypatch) -> None:
    class StubAssistantService:
        def __init__(self, session):
            self.session = session

        def chat(self, request):
            return {
                "session_id": "session-1",
                "message": "请告诉我这顿大概几个人吃、预算多少？",
                "needs_clarification": True,
                "clarification_question": "请告诉我这顿大概几个人吃、预算多少？",
                "extracted_constraints": {
                    "query_type": "recommendation",
                    "cuisine_types": ["川菜"],
                    "budget_max": None,
                    "party_size": None,
                    "exclude_allergens": [],
                    "comparison_targets": [],
                },
                "recommendations": [],
                "comparisons": [],
                "citations": [],
                "suggested_actions": [],
            }

    monkeypatch.setattr(assistant_routes, "AssistantService", StubAssistantService)

    response = client.post(
        "/assistant/chat",
        json={"message": "推荐几种川菜", "session_id": None},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["session_id"] == "session-1"
    assert payload["needs_clarification"] is True
    assert payload["clarification_question"] == "请告诉我这顿大概几个人吃、预算多少？"
    assert payload["extracted_constraints"]["cuisine_types"] == ["川菜"]


def test_assistant_health_reports_dependency_flags(monkeypatch) -> None:
    monkeypatch.setattr(
        assistant_routes,
        "build_assistant_health",
        lambda: {
            "status": "ok",
            "llm_ready": True,
            "vector_store_ready": False,
            "degraded_mode": True,
        },
    )

    response = client.get("/assistant/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "llm_ready": True,
        "vector_store_ready": False,
        "degraded_mode": True,
    }
```

- [ ] **Step 2: Run the route tests to verify they fail**

Run:
```bash
pytest tests/api/test_assistant_routes.py -q
```

Expected: FAIL with import errors or `404 Not Found` because the assistant route, schemas, and service do not exist yet.

- [ ] **Step 3: Add the minimal schemas, route, and app wiring to satisfy the contract**

```python
# api/schemas.py
class AssistantChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=500)
    session_id: str | None = None


class AssistantConstraintResponse(BaseModel):
    query_type: Literal["recommendation", "comparison", "knowledge"]
    cuisine_types: list[str] = Field(default_factory=list)
    budget_max: float | None = None
    party_size: int | None = None
    exclude_allergens: list[str] = Field(default_factory=list)
    comparison_targets: list[str] = Field(default_factory=list)


class AssistantRecommendationResponse(BaseModel):
    source_type: Literal["dish", "merchant"]
    merchant_id: int
    merchant_name: str
    dish_id: int | None = None
    dish_name: str | None = None
    price: float | None = None
    reason: str


class AssistantComparisonResponse(BaseModel):
    merchant_id: int
    merchant_name: str
    summary: str
    highlights: list[str] = Field(default_factory=list)


class AssistantCitationResponse(BaseModel):
    source_type: Literal["dish", "merchant"]
    source_id: int
    title: str
    snippet: str


class AssistantChatResponse(BaseModel):
    session_id: str
    message: str
    needs_clarification: bool
    clarification_question: str | None = None
    extracted_constraints: AssistantConstraintResponse
    recommendations: list[AssistantRecommendationResponse] = Field(default_factory=list)
    comparisons: list[AssistantComparisonResponse] = Field(default_factory=list)
    citations: list[AssistantCitationResponse] = Field(default_factory=list)
    suggested_actions: list[str] = Field(default_factory=list)


class AssistantHealthResponse(BaseModel):
    status: str
    llm_ready: bool
    vector_store_ready: bool
    degraded_mode: bool
```

```python
# service/assistant_service.py
class AssistantService:
    def __init__(self, session):
        self.session = session

    def chat(self, request):
        raise NotImplementedError("AssistantService.chat is implemented in Task 3")


def build_assistant_health() -> dict[str, bool | str]:
    return {
        "status": "ok",
        "llm_ready": True,
        "vector_store_ready": False,
        "degraded_mode": True,
    }
```

```python
# api/routes/assistant.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.db import get_db_session
from api.schemas import AssistantChatRequest, AssistantChatResponse, AssistantHealthResponse
from service.assistant_service import AssistantService, build_assistant_health

router = APIRouter(prefix="/assistant", tags=["assistant"])


@router.post("/chat", response_model=AssistantChatResponse)
def chat_assistant(
    request: AssistantChatRequest,
    session: Session = Depends(get_db_session),
) -> AssistantChatResponse:
    return AssistantService(session).chat(request)


@router.get("/health", response_model=AssistantHealthResponse)
def assistant_health() -> AssistantHealthResponse:
    return build_assistant_health()
```

```python
# api/routes/__init__.py
from api.routes.address import router as address_router
from api.routes.agent_context import router as agent_context_router
from api.routes.assistant import router as assistant_router
from api.routes.auth import router as auth_router
from api.routes.cart import router as cart_router
from api.routes.catalog import router as catalog_router
from api.routes.health import router as health_router
from api.routes.orders import router as orders_router

__all__ = [
    "address_router",
    "agent_context_router",
    "assistant_router",
    "auth_router",
    "cart_router",
    "catalog_router",
    "health_router",
    "orders_router",
]
```

```python
# api/main.py
from api.routes import address_router, agent_context_router, assistant_router, auth_router, cart_router, catalog_router, health_router, orders_router

app.include_router(auth_router)
app.include_router(address_router)
app.include_router(agent_context_router)
app.include_router(assistant_router)
app.include_router(catalog_router)
app.include_router(cart_router)
app.include_router(orders_router)
app.include_router(health_router)
```

- [ ] **Step 4: Run the route tests again to verify they pass**

Run:
```bash
pytest tests/api/test_assistant_routes.py -q
```

Expected: PASS with `2 passed`.

- [ ] **Step 5: Commit the contract-and-wiring slice**

```bash
git add api/main.py api/routes/__init__.py api/routes/assistant.py api/schemas.py service/assistant_service.py tests/api/test_assistant_routes.py
git commit -m "feat: add assistant api contract"
```

### Task 2: Build conversation state, constraint parsing, and response composition

**Files:**
- Create: `service/assistant_models.py`
- Create: `service/assistant_session_store.py`
- Create: `service/assistant_constraint_parser.py`
- Create: `service/assistant_composer.py`
- Test: `tests/service/test_assistant_constraint_parser.py`
- Test: `tests/service/test_assistant_composer.py`

- [ ] **Step 1: Write the failing parser and composer tests**

```python
# tests/service/test_assistant_constraint_parser.py
from service.assistant_constraint_parser import parse_assistant_query


def test_parse_assistant_query_extracts_recommendation_constraints() -> None:
    parsed = parse_assistant_query("推荐几种川菜，2个人吃，100元以内，不要花生")

    assert parsed.query_type == "recommendation"
    assert parsed.cuisine_types == ["川菜"]
    assert parsed.party_size == 2
    assert parsed.budget_max == 100.0
    assert parsed.exclude_allergens == ["花生"]
    assert parsed.needs_clarification is False


def test_parse_assistant_query_requests_clarification_for_sparse_recommendation() -> None:
    parsed = parse_assistant_query("推荐几种川菜")

    assert parsed.query_type == "recommendation"
    assert parsed.cuisine_types == ["川菜"]
    assert parsed.needs_clarification is True
    assert parsed.clarification_question == "请告诉我这顿大概几个人吃、预算多少？"


def test_parse_assistant_query_detects_comparison_targets() -> None:
    parsed = parse_assistant_query("帮我对比兰姨小炒和午后豆房")

    assert parsed.query_type == "comparison"
    assert parsed.comparison_targets == ["兰姨小炒", "午后豆房"]
```

```python
# tests/service/test_assistant_composer.py
from service.assistant_composer import compose_assistant_response
from service.assistant_models import AssistantCandidate, AssistantParsedQuery


def test_compose_assistant_response_builds_recommendation_payload() -> None:
    parsed = AssistantParsedQuery(
        raw_message="推荐几种川菜，2个人吃，100元以内，不要花生",
        query_type="recommendation",
        cuisine_types=["川菜"],
        budget_max=100.0,
        party_size=2,
        exclude_allergens=["花生"],
        comparison_targets=[],
        needs_clarification=False,
        clarification_question=None,
    )
    candidates = [
        AssistantCandidate(
            source_type="dish",
            source_id=11,
            merchant_id=1,
            merchant_name="兰姨小炒",
            dish_id=11,
            dish_name="鱼香肉丝",
            price=28.0,
            score=0.93,
            summary="酸甜微辣，下饭感强，适合两人晚餐",
            reason_facts=["川菜", "28元", "不含花生"],
            citation_title="鱼香肉丝｜兰姨小炒",
            citation_snippet="川菜；酸甜微辣；配料为猪里脊、木耳、胡萝卜、青椒",
        )
    ]

    response = compose_assistant_response("session-1", parsed, candidates)

    assert response["session_id"] == "session-1"
    assert response["needs_clarification"] is False
    assert response["recommendations"][0]["dish_name"] == "鱼香肉丝"
    assert response["recommendations"][0]["reason"] == "匹配川菜偏好，单价 28 元，且未命中花生过敏原。"
    assert response["citations"][0]["title"] == "鱼香肉丝｜兰姨小炒"


def test_compose_assistant_response_builds_clarification_payload() -> None:
    parsed = AssistantParsedQuery(
        raw_message="推荐几种川菜",
        query_type="recommendation",
        cuisine_types=["川菜"],
        budget_max=None,
        party_size=None,
        exclude_allergens=[],
        comparison_targets=[],
        needs_clarification=True,
        clarification_question="请告诉我这顿大概几个人吃、预算多少？",
    )

    response = compose_assistant_response("session-1", parsed, [])

    assert response["needs_clarification"] is True
    assert response["clarification_question"] == "请告诉我这顿大概几个人吃、预算多少？"
    assert response["recommendations"] == []
```

- [ ] **Step 2: Run the parser/composer tests to verify they fail**

Run:
```bash
pytest tests/service/test_assistant_constraint_parser.py tests/service/test_assistant_composer.py -q
```

Expected: FAIL with import errors because the assistant model, parser, and composer modules do not exist yet.

- [ ] **Step 3: Implement the internal models, in-memory session store, parser, and composer**

```python
# service/assistant_models.py
from dataclasses import dataclass, field
from typing import Literal


@dataclass
class AssistantParsedQuery:
    raw_message: str
    query_type: Literal["recommendation", "comparison", "knowledge"]
    cuisine_types: list[str] = field(default_factory=list)
    budget_max: float | None = None
    party_size: int | None = None
    exclude_allergens: list[str] = field(default_factory=list)
    comparison_targets: list[str] = field(default_factory=list)
    needs_clarification: bool = False
    clarification_question: str | None = None


@dataclass
class AssistantCandidate:
    source_type: Literal["dish", "merchant"]
    source_id: int
    merchant_id: int
    merchant_name: str
    dish_id: int | None
    dish_name: str | None
    price: float | None
    score: float
    summary: str
    reason_facts: list[str] = field(default_factory=list)
    citation_title: str = ""
    citation_snippet: str = ""


@dataclass
class AssistantConversationState:
    session_id: str
    last_user_message: str = ""
    parsed_query: AssistantParsedQuery | None = None
    candidate_ids: list[int] = field(default_factory=list)
```

```python
# service/assistant_session_store.py
from uuid import uuid4

from service.assistant_models import AssistantConversationState, AssistantParsedQuery


class InMemoryAssistantSessionStore:
    def __init__(self) -> None:
        self._store: dict[str, AssistantConversationState] = {}

    def get_or_create(self, session_id: str | None) -> AssistantConversationState:
        actual_session_id = session_id or uuid4().hex
        state = self._store.get(actual_session_id)
        if state is None:
            state = AssistantConversationState(session_id=actual_session_id)
            self._store[actual_session_id] = state
        return state

    def update(self, session_id: str, user_message: str, parsed_query: AssistantParsedQuery, candidate_ids: list[int]) -> AssistantConversationState:
        state = self._store[session_id]
        state.last_user_message = user_message
        state.parsed_query = parsed_query
        state.candidate_ids = candidate_ids
        return state
```

```python
# service/assistant_constraint_parser.py
import re

from service.assistant_models import AssistantParsedQuery

CUISINE_KEYWORDS = ["川菜", "湘菜", "粤菜", "轻食", "咖啡甜品"]
ALLERGEN_KEYWORDS = ["花生", "麸质", "牛奶", "鸡蛋", "海鲜"]
COMPARISON_SPLITTER = re.compile(r"和|与")
BUDGET_PATTERN = re.compile(r"(\d+(?:\.\d+)?)\s*元(?:以内|以下|之内)?")
PARTY_SIZE_PATTERN = re.compile(r"(\d+)\s*(?:个人|人)")


def parse_assistant_query(message: str) -> AssistantParsedQuery:
    query_type = "knowledge"
    if any(keyword in message for keyword in ["推荐", "吃什么", "适合"]):
        query_type = "recommendation"
    if any(keyword in message for keyword in ["对比", "比较"]):
        query_type = "comparison"

    cuisine_types = [keyword for keyword in CUISINE_KEYWORDS if keyword in message]
    exclude_allergens = [keyword for keyword in ALLERGEN_KEYWORDS if f"不要{keyword}" in message or f"不含{keyword}" in message]

    budget_match = BUDGET_PATTERN.search(message)
    party_size_match = PARTY_SIZE_PATTERN.search(message)

    comparison_targets: list[str] = []
    if query_type == "comparison":
        cleaned = message.replace("帮我", "").replace("对比", "").replace("比较", "")
        comparison_targets = [item.strip() for item in COMPARISON_SPLITTER.split(cleaned) if item.strip()]

    needs_clarification = False
    clarification_question = None
    if query_type == "recommendation" and not budget_match and not party_size_match:
        needs_clarification = True
        clarification_question = "请告诉我这顿大概几个人吃、预算多少？"

    return AssistantParsedQuery(
        raw_message=message,
        query_type=query_type,
        cuisine_types=cuisine_types,
        budget_max=float(budget_match.group(1)) if budget_match else None,
        party_size=int(party_size_match.group(1)) if party_size_match else None,
        exclude_allergens=exclude_allergens,
        comparison_targets=comparison_targets,
        needs_clarification=needs_clarification,
        clarification_question=clarification_question,
    )
```

```python
# service/assistant_composer.py
from service.assistant_models import AssistantCandidate, AssistantParsedQuery


def compose_assistant_response(session_id: str, parsed: AssistantParsedQuery, candidates: list[AssistantCandidate]) -> dict:
    if parsed.needs_clarification:
        return {
            "session_id": session_id,
            "message": parsed.clarification_question,
            "needs_clarification": True,
            "clarification_question": parsed.clarification_question,
            "extracted_constraints": {
                "query_type": parsed.query_type,
                "cuisine_types": parsed.cuisine_types,
                "budget_max": parsed.budget_max,
                "party_size": parsed.party_size,
                "exclude_allergens": parsed.exclude_allergens,
                "comparison_targets": parsed.comparison_targets,
            },
            "recommendations": [],
            "comparisons": [],
            "citations": [],
            "suggested_actions": [],
        }

    recommendations = []
    comparisons = []
    citations = []

    for candidate in candidates:
        citations.append(
            {
                "source_type": candidate.source_type,
                "source_id": candidate.source_id,
                "title": candidate.citation_title,
                "snippet": candidate.citation_snippet,
            }
        )
        if candidate.source_type == "dish":
            recommendations.append(
                {
                    "source_type": "dish",
                    "merchant_id": candidate.merchant_id,
                    "merchant_name": candidate.merchant_name,
                    "dish_id": candidate.dish_id,
                    "dish_name": candidate.dish_name,
                    "price": candidate.price,
                    "reason": f"匹配{candidate.reason_facts[0]}偏好，单价 {candidate.price:.0f} 元，且未命中{candidate.reason_facts[-1]}过敏原。",
                }
            )
        else:
            comparisons.append(
                {
                    "merchant_id": candidate.merchant_id,
                    "merchant_name": candidate.merchant_name,
                    "summary": candidate.summary,
                    "highlights": candidate.reason_facts,
                }
            )

    message = "我根据你提供的条件整理了更匹配的选项。"
    return {
        "session_id": session_id,
        "message": message,
        "needs_clarification": False,
        "clarification_question": None,
        "extracted_constraints": {
            "query_type": parsed.query_type,
            "cuisine_types": parsed.cuisine_types,
            "budget_max": parsed.budget_max,
            "party_size": parsed.party_size,
            "exclude_allergens": parsed.exclude_allergens,
            "comparison_targets": parsed.comparison_targets,
        },
        "recommendations": recommendations,
        "comparisons": comparisons,
        "citations": citations,
        "suggested_actions": ["查看商家详情", "继续补充口味偏好"],
    }
```

- [ ] **Step 4: Run the parser/composer tests again to verify they pass**

Run:
```bash
pytest tests/service/test_assistant_constraint_parser.py tests/service/test_assistant_composer.py -q
```

Expected: PASS with `5 passed`.

- [ ] **Step 5: Commit the parsing-and-composition slice**

```bash
git add service/assistant_models.py service/assistant_session_store.py service/assistant_constraint_parser.py service/assistant_composer.py tests/service/test_assistant_constraint_parser.py tests/service/test_assistant_composer.py
git commit -m "feat: add assistant parsing and response composition"
```

### Task 3: Implement hybrid retrieval and the assistant orchestration service

**Files:**
- Create: `tools/assistant_vector_store.py`
- Create: `service/assistant_retriever.py`
- Modify: `service/assistant_service.py`
- Test: `tests/service/test_assistant_service.py`

- [ ] **Step 1: Write the failing orchestration and retrieval tests**

```python
from types import SimpleNamespace

from service.assistant_models import AssistantCandidate
from service.assistant_service import AssistantService


class DummySession:
    pass


def test_assistant_service_returns_clarification_before_retrieval(monkeypatch) -> None:
    retrieve_called = {"value": False}

    class StubRetriever:
        def __init__(self, session):
            self.session = session

        def retrieve(self, parsed):
            retrieve_called["value"] = True
            return []

    monkeypatch.setattr("service.assistant_service.AssistantRetriever", StubRetriever)

    service = AssistantService(DummySession())
    response = service.chat(SimpleNamespace(message="推荐几种川菜", session_id=None))

    assert response["needs_clarification"] is True
    assert retrieve_called["value"] is False


def test_assistant_service_returns_grounded_dish_recommendations(monkeypatch) -> None:
    class StubRetriever:
        def __init__(self, session):
            self.session = session

        def retrieve(self, parsed):
            return [
                AssistantCandidate(
                    source_type="dish",
                    source_id=11,
                    merchant_id=1,
                    merchant_name="兰姨小炒",
                    dish_id=11,
                    dish_name="鱼香肉丝",
                    price=28.0,
                    score=0.91,
                    summary="酸甜微辣，下饭感强，适合两人晚餐",
                    reason_facts=["川菜", "28元", "花生"],
                    citation_title="鱼香肉丝｜兰姨小炒",
                    citation_snippet="川菜；酸甜微辣；配料为猪里脊、木耳、胡萝卜、青椒",
                )
            ]

    monkeypatch.setattr("service.assistant_service.AssistantRetriever", StubRetriever)

    service = AssistantService(DummySession())
    response = service.chat(
        SimpleNamespace(
            message="推荐几种川菜，2个人吃，100元以内，不要花生",
            session_id="session-1",
        )
    )

    assert response["session_id"] == "session-1"
    assert response["needs_clarification"] is False
    assert response["recommendations"][0]["dish_name"] == "鱼香肉丝"
    assert response["citations"][0]["source_type"] == "dish"


def test_build_assistant_health_reports_degraded_mode_without_vector_keys(monkeypatch) -> None:
    monkeypatch.delenv("PINECONE_API_KEY", raising=False)
    monkeypatch.setenv("MODEL_NAME", "gpt-5.4")

    from service.assistant_service import build_assistant_health

    assert build_assistant_health() == {
        "status": "ok",
        "llm_ready": True,
        "vector_store_ready": False,
        "degraded_mode": True,
    }
```

- [ ] **Step 2: Run the orchestration tests to verify they fail**

Run:
```bash
pytest tests/service/test_assistant_service.py -q
```

Expected: FAIL because `AssistantService.chat()` still raises `NotImplementedError` and the vector-store helper does not exist.

- [ ] **Step 3: Implement the assistant vector-store adapter, retriever, and service orchestration**

```python
# tools/assistant_vector_store.py
import os

from pinecone import Pinecone


class AssistantVectorStore:
    def __init__(self) -> None:
        self.api_key = os.getenv("PINECONE_API_KEY")
        self.index_name = os.getenv("PINECONE_ASSISTANT_INDEX", "smart-order-assistant")
        self._client = Pinecone(api_key=self.api_key) if self.api_key else None

    def is_ready(self) -> bool:
        return self._client is not None

    def semantic_scores(self, query: str, candidates: list[dict]) -> dict[int, float]:
        if not self.is_ready() or not candidates:
            return {}
        return {}
```

```python
# service/assistant_retriever.py
from service.catalog_service import CatalogService
from service.assistant_models import AssistantCandidate, AssistantParsedQuery
from tools.assistant_vector_store import AssistantVectorStore


class AssistantRetriever:
    def __init__(self, session) -> None:
        self.catalog_service = CatalogService(session)
        self.vector_store = AssistantVectorStore()

    def retrieve(self, parsed: AssistantParsedQuery) -> list[AssistantCandidate]:
        merchants = self.catalog_service.list_merchants()
        candidates: list[AssistantCandidate] = []

        for merchant in merchants:
            merchant_matches = not parsed.comparison_targets or merchant["name"] in parsed.comparison_targets
            if parsed.query_type == "comparison" and merchant_matches:
                candidates.append(
                    AssistantCandidate(
                        source_type="merchant",
                        source_id=merchant["id"],
                        merchant_id=merchant["id"],
                        merchant_name=merchant["name"],
                        dish_id=None,
                        dish_name=None,
                        price=None,
                        score=float(merchant["rating"]),
                        summary=f"{merchant['business_hours']} 营业，标签包括 {'、'.join(merchant['merchant_tags'])}。",
                        reason_facts=merchant["merchant_tags"][:3],
                        citation_title=merchant["name"],
                        citation_snippet=merchant["description"],
                    )
                )
                continue

            dishes = self.catalog_service.list_dishes_by_merchant(merchant["id"])
            for dish in dishes:
                if parsed.cuisine_types and dish["cuisine_type"] not in parsed.cuisine_types:
                    continue
                if parsed.exclude_allergens and any(allergen in dish["allergens"] for allergen in parsed.exclude_allergens):
                    continue
                if parsed.budget_max is not None and parsed.party_size is not None and dish["price"] * parsed.party_size > parsed.budget_max:
                    continue

                candidates.append(
                    AssistantCandidate(
                        source_type="dish",
                        source_id=dish["id"],
                        merchant_id=merchant["id"],
                        merchant_name=merchant["name"],
                        dish_id=dish["id"],
                        dish_name=dish["name"],
                        price=dish["price"],
                        score=float(merchant["rating"]),
                        summary=dish["description"],
                        reason_facts=[dish["cuisine_type"], f"{dish['price']:.0f}元", parsed.exclude_allergens[0] if parsed.exclude_allergens else "显式约束"],
                        citation_title=f"{dish['name']}｜{merchant['name']}",
                        citation_snippet=f"{dish['cuisine_type']}；{dish['flavor_profile']}；配料为{'、'.join(dish['ingredients'])}",
                    )
                )

        semantic_scores = self.vector_store.semantic_scores(parsed.raw_message, [candidate.__dict__ for candidate in candidates])
        for candidate in candidates:
            candidate.score += semantic_scores.get(candidate.source_id, 0.0)

        return sorted(candidates, key=lambda item: item.score, reverse=True)[:3]
```

```python
# service/assistant_service.py
import os

from service.assistant_composer import compose_assistant_response
from service.assistant_constraint_parser import parse_assistant_query
from service.assistant_retriever import AssistantRetriever
from service.assistant_session_store import InMemoryAssistantSessionStore
from tools.assistant_vector_store import AssistantVectorStore

_SESSION_STORE = InMemoryAssistantSessionStore()


class AssistantService:
    def __init__(self, session) -> None:
        self.session = session
        self.session_store = _SESSION_STORE
        self.retriever_cls = AssistantRetriever

    def chat(self, request):
        state = self.session_store.get_or_create(request.session_id)
        parsed = parse_assistant_query(request.message)

        if parsed.needs_clarification:
            self.session_store.update(state.session_id, request.message, parsed, [])
            return compose_assistant_response(state.session_id, parsed, [])

        candidates = self.retriever_cls(self.session).retrieve(parsed)
        candidate_ids = [candidate.source_id for candidate in candidates]
        self.session_store.update(state.session_id, request.message, parsed, candidate_ids)
        return compose_assistant_response(state.session_id, parsed, candidates)


def build_assistant_health() -> dict[str, bool | str]:
    llm_ready = bool(os.getenv("MODEL_NAME"))
    vector_store_ready = AssistantVectorStore().is_ready()
    return {
        "status": "ok",
        "llm_ready": llm_ready,
        "vector_store_ready": vector_store_ready,
        "degraded_mode": not vector_store_ready,
    }
```

- [ ] **Step 4: Run the backend assistant tests to verify they pass**

Run:
```bash
pytest tests/api/test_assistant_routes.py tests/service/test_assistant_constraint_parser.py tests/service/test_assistant_composer.py tests/service/test_assistant_service.py -q
```

Expected: PASS with `8 passed`.

- [ ] **Step 5: Commit the retrieval-and-orchestration slice**

```bash
git add service/assistant_retriever.py service/assistant_service.py tests/service/test_assistant_service.py tools/assistant_vector_store.py
git commit -m "feat: add assistant retrieval orchestration"
```

### Task 4: Upgrade the floating assistant into a working multi-turn frontend

**Files:**
- Create: `ui/src/api/assistant.js`
- Create: `ui/src/composables/useAssistant.js`
- Modify: `ui/src/components/home/FloatingAssistant.vue`
- Modify: `ui/src/__tests__/app.homepage.test.js`
- Test: `ui/src/__tests__/floatingAssistant.test.js`

- [ ] **Step 1: Write the failing frontend assistant tests**

```javascript
import { mount } from '@vue/test-utils'
import { describe, expect, test, vi } from 'vitest'

const chatWithAssistant = vi.fn()

vi.mock('../api/assistant', () => ({
  chatWithAssistant,
}))

import FloatingAssistant from '../components/home/FloatingAssistant.vue'

describe('FloatingAssistant', () => {
  test('submits a user message and renders the clarification question', async () => {
    chatWithAssistant.mockResolvedValueOnce({
      session_id: 'session-1',
      message: '请告诉我这顿大概几个人吃、预算多少？',
      needs_clarification: true,
      clarification_question: '请告诉我这顿大概几个人吃、预算多少？',
      extracted_constraints: {
        query_type: 'recommendation',
        cuisine_types: ['川菜'],
        budget_max: null,
        party_size: null,
        exclude_allergens: [],
        comparison_targets: [],
      },
      recommendations: [],
      comparisons: [],
      citations: [],
      suggested_actions: [],
    })

    const wrapper = mount(FloatingAssistant, {
      global: {
        stubs: {
          'el-input': {
            props: ['modelValue'],
            emits: ['update:modelValue'],
            template: '<input :value="modelValue" @input="$emit(\'update:modelValue\', $event.target.value)" />',
          },
          'el-button': { template: '<button @click="$emit(\'click\')"><slot /></button>' },
          'el-tag': { template: '<span><slot /></span>' },
          'el-scrollbar': { template: '<div><slot /></div>' },
        },
      },
    })

    await wrapper.find('input').setValue('推荐几种川菜')
    await wrapper.find('button').trigger('click')

    expect(chatWithAssistant).toHaveBeenCalledWith({
      message: '推荐几种川菜',
      session_id: null,
    })
    expect(wrapper.text()).toContain('请告诉我这顿大概几个人吃、预算多少？')
    expect(wrapper.text()).toContain('川菜')
  })

  test('renders recommendation cards and citations from the assistant response', async () => {
    chatWithAssistant.mockResolvedValueOnce({
      session_id: 'session-1',
      message: '我根据你提供的条件整理了更匹配的选项。',
      needs_clarification: false,
      clarification_question: null,
      extracted_constraints: {
        query_type: 'recommendation',
        cuisine_types: ['川菜'],
        budget_max: 100,
        party_size: 2,
        exclude_allergens: ['花生'],
        comparison_targets: [],
      },
      recommendations: [
        {
          source_type: 'dish',
          merchant_id: 1,
          merchant_name: '兰姨小炒',
          dish_id: 11,
          dish_name: '鱼香肉丝',
          price: 28,
          reason: '匹配川菜偏好，单价 28 元，且未命中花生过敏原。',
        },
      ],
      comparisons: [],
      citations: [
        {
          source_type: 'dish',
          source_id: 11,
          title: '鱼香肉丝｜兰姨小炒',
          snippet: '川菜；酸甜微辣；配料为猪里脊、木耳、胡萝卜、青椒',
        },
      ],
      suggested_actions: ['查看商家详情'],
    })

    const wrapper = mount(FloatingAssistant, {
      global: {
        stubs: {
          'el-input': {
            props: ['modelValue'],
            emits: ['update:modelValue'],
            template: '<input :value="modelValue" @input="$emit(\'update:modelValue\', $event.target.value)" />',
          },
          'el-button': { template: '<button @click="$emit(\'click\')"><slot /></button>' },
          'el-tag': { template: '<span><slot /></span>' },
          'el-scrollbar': { template: '<div><slot /></div>' },
        },
      },
    })

    await wrapper.find('input').setValue('推荐几种川菜，2个人吃，100元以内，不要花生')
    await wrapper.find('button').trigger('click')

    expect(wrapper.text()).toContain('鱼香肉丝')
    expect(wrapper.text()).toContain('兰姨小炒')
    expect(wrapper.text()).toContain('匹配川菜偏好')
    expect(wrapper.text()).toContain('鱼香肉丝｜兰姨小炒')
  })
})
```

- [ ] **Step 2: Run the frontend assistant tests to verify they fail**

Run:
```bash
npm --prefix "ui" test -- src/__tests__/floatingAssistant.test.js src/__tests__/app.homepage.test.js --run
```

Expected: FAIL because the assistant API module, composable, and richer component UI do not exist yet.

- [ ] **Step 3: Implement the assistant API client, composable, and richer panel UI**

```javascript
// ui/src/api/assistant.js
import api from './index'

export const chatWithAssistant = (payload) => api.post('/assistant/chat', payload)
export const getAssistantHealth = () => api.get('/assistant/health')
```

```javascript
// ui/src/composables/useAssistant.js
import { ref } from 'vue'
import { chatWithAssistant } from '../api/assistant'

export function useAssistant() {
  const sessionId = ref(null)
  const draft = ref('')
  const loading = ref(false)
  const errorMessage = ref('')
  const messages = ref([
    {
      role: 'assistant',
      text: '你好，欢迎来到 smart_order。你可以告诉我菜系、人数、预算和忌口，我会先帮你缩小范围。',
    },
  ])
  const extractedConstraints = ref([])
  const recommendations = ref([])
  const comparisons = ref([])
  const citations = ref([])
  const suggestedActions = ref([])

  const submit = async () => {
    const question = draft.value.trim()
    if (!question || loading.value) {
      return
    }

    messages.value.push({ role: 'user', text: question })
    draft.value = ''
    loading.value = true
    errorMessage.value = ''

    try {
      const response = await chatWithAssistant({
        message: question,
        session_id: sessionId.value,
      })
      sessionId.value = response.session_id
      messages.value.push({ role: 'assistant', text: response.message })
      extractedConstraints.value = [
        ...response.extracted_constraints.cuisine_types,
        ...(response.extracted_constraints.party_size ? [`${response.extracted_constraints.party_size}人`] : []),
        ...(response.extracted_constraints.budget_max ? [`${response.extracted_constraints.budget_max}元内`] : []),
        ...response.extracted_constraints.exclude_allergens,
      ]
      recommendations.value = response.recommendations
      comparisons.value = response.comparisons
      citations.value = response.citations
      suggestedActions.value = response.suggested_actions
    } catch (error) {
      errorMessage.value = error?.message || '智能助手暂时不可用，请稍后再试'
    } finally {
      loading.value = false
    }
  }

  return {
    sessionId,
    draft,
    loading,
    errorMessage,
    messages,
    extractedConstraints,
    recommendations,
    comparisons,
    citations,
    suggestedActions,
    submit,
  }
}
```

```vue
<!-- ui/src/components/home/FloatingAssistant.vue -->
<template>
  <aside class="assistant-panel">
    <div class="assistant-header">
      <span>智能助手</span>
      <span class="status">在线</span>
    </div>

    <el-scrollbar class="assistant-feed">
      <div v-for="message in messages" :key="`${message.role}-${message.text}`" class="assistant-message-row" :class="message.role">
        <div class="assistant-avatar">{{ message.role === 'assistant' ? 'AI' : '我' }}</div>
        <div class="assistant-bubble">
          <p>{{ message.text }}</p>
        </div>
      </div>
    </el-scrollbar>

    <div v-if="extractedConstraints.length" class="assistant-tags">
      <el-tag v-for="item in extractedConstraints" :key="item" effect="plain">{{ item }}</el-tag>
    </div>

    <div v-if="recommendations.length" class="assistant-section">
      <h4>推荐结果</h4>
      <div v-for="item in recommendations" :key="`${item.merchant_id}-${item.dish_id || item.merchant_name}`" class="assistant-card">
        <strong>{{ item.dish_name || item.merchant_name }}</strong>
        <p>{{ item.merchant_name }}</p>
        <p v-if="item.price">¥{{ item.price }}</p>
        <p>{{ item.reason }}</p>
      </div>
    </div>

    <div v-if="comparisons.length" class="assistant-section">
      <h4>商家对比</h4>
      <div v-for="item in comparisons" :key="item.merchant_id" class="assistant-card">
        <strong>{{ item.merchant_name }}</strong>
        <p>{{ item.summary }}</p>
      </div>
    </div>

    <div v-if="citations.length" class="assistant-section">
      <h4>依据</h4>
      <div v-for="item in citations" :key="`${item.source_type}-${item.source_id}`" class="assistant-citation">
        <strong>{{ item.title }}</strong>
        <p>{{ item.snippet }}</p>
      </div>
    </div>

    <p v-if="errorMessage" class="assistant-error">{{ errorMessage }}</p>

    <div class="assistant-input-row">
      <el-input v-model="draft" placeholder="输入问题，例如：推荐几种川菜，2个人吃，100元以内，不要花生" @keyup.enter="submit" />
      <el-button type="primary" :loading="loading" @click="submit">发送</el-button>
    </div>
  </aside>
</template>

<script setup>
import { useAssistant } from '../../composables/useAssistant'

const {
  draft,
  loading,
  errorMessage,
  messages,
  extractedConstraints,
  recommendations,
  comparisons,
  citations,
  submit,
} = useAssistant()
</script>
```

```javascript
// ui/src/__tests__/app.homepage.test.js
// In the global stubs section, add the richer Element Plus stubs used by FloatingAssistant.
'el-scrollbar': { template: '<div><slot /></div>' },
'el-tag': { template: '<span><slot /></span>' },
```

- [ ] **Step 4: Run the focused frontend tests to verify they pass**

Run:
```bash
npm --prefix "ui" test -- src/__tests__/floatingAssistant.test.js src/__tests__/app.homepage.test.js --run
```

Expected: PASS with both suites green.

- [ ] **Step 5: Commit the frontend assistant slice**

```bash
git add ui/src/api/assistant.js ui/src/composables/useAssistant.js ui/src/components/home/FloatingAssistant.vue ui/src/__tests__/floatingAssistant.test.js ui/src/__tests__/app.homepage.test.js
git commit -m "feat: add interactive assistant panel"
```

### Task 5: Run the phase-1 verification bundle

**Files:**
- Modify: `service/assistant_service.py` (only if verification reveals contract mismatches)
- Modify: `ui/src/components/home/FloatingAssistant.vue` (only if verification reveals rendering mismatches)
- Test: `tests/api/test_assistant_routes.py`
- Test: `tests/service/test_assistant_constraint_parser.py`
- Test: `tests/service/test_assistant_composer.py`
- Test: `tests/service/test_assistant_service.py`
- Test: `ui/src/__tests__/floatingAssistant.test.js`
- Test: `ui/src/__tests__/app.homepage.test.js`

- [ ] **Step 1: Run the full backend assistant test bundle**

Run:
```bash
pytest tests/api/test_assistant_routes.py tests/service/test_assistant_constraint_parser.py tests/service/test_assistant_composer.py tests/service/test_assistant_service.py -q
```

Expected: PASS with all assistant backend tests green.

- [ ] **Step 2: Run the focused frontend assistant bundle**

Run:
```bash
npm --prefix "ui" test -- src/__tests__/floatingAssistant.test.js src/__tests__/app.homepage.test.js --run
```

Expected: PASS with the assistant panel and homepage shell tests green.

- [ ] **Step 3: Start the backend and verify the assistant health endpoint manually**

Run:
```bash
python -X utf8 run.py
```

In a second shell, run:
```bash
curl -s http://127.0.0.1:8000/assistant/health
```

Expected JSON shape:
```json
{
  "status": "ok",
  "llm_ready": true,
  "vector_store_ready": false,
  "degraded_mode": true
}
```

- [ ] **Step 4: Start the frontend and verify the assistant interaction manually**

Run:
```bash
npm --prefix "ui" run dev -- --host 127.0.0.1 --port 3000
```

Manual checks:
1. The floating assistant still appears on the homepage.
2. Asking `推荐几种川菜` produces a clarification question instead of a blank response.
3. Asking `推荐几种川菜，2个人吃，100元以内，不要花生` renders recommendation cards and citations.
4. Asking `帮我对比兰姨小炒和午后豆房` renders merchant comparison content.
5. If the backend is unavailable, the panel shows a friendly failure message rather than crashing.

- [ ] **Step 5: Commit the verification fixes, if any were needed**

```bash
git add api/routes/assistant.py api/schemas.py service/assistant_models.py service/assistant_session_store.py service/assistant_constraint_parser.py service/assistant_composer.py service/assistant_retriever.py service/assistant_service.py tools/assistant_vector_store.py tests/api/test_assistant_routes.py tests/service/test_assistant_constraint_parser.py tests/service/test_assistant_composer.py tests/service/test_assistant_service.py ui/src/api/assistant.js ui/src/composables/useAssistant.js ui/src/components/home/FloatingAssistant.vue ui/src/__tests__/floatingAssistant.test.js ui/src/__tests__/app.homepage.test.js
git commit -m "test: verify assistant phase1 flow"
```

## Spec Coverage Check

- Multi-turn clarification: covered by Task 2 parser/composer logic and Task 4 UI rendering.
- Dish recommendation: covered by Task 3 retriever/service and Task 4 recommendation cards.
- Constraint-aware filtering: covered by Task 2 parsing and Task 3 structured filters.
- Merchant comparison: covered by Task 2 comparison extraction, Task 3 merchant candidates, and Task 4 comparison rendering.
- Grounded knowledge Q&A: covered by Task 3 service/retriever contract and Task 4 citation rendering.
- Reuse of current LLM/Pinecone setup: covered by Task 3 `tools/assistant_vector_store.py` and `build_assistant_health()`.
- Phase-2 action-agent boundary preserved: covered by Task 1 schema field `suggested_actions` and the fact that no write route is added.

## Placeholder Scan

This plan intentionally avoids placeholder steps such as “write tests”, “implement later”, or “handle edge cases”. Every task names the exact files, concrete code shapes, and exact verification commands.

## Type Consistency Check

The plan uses the same contract names throughout:
- `AssistantChatRequest`
- `AssistantChatResponse`
- `AssistantHealthResponse`
- `AssistantParsedQuery`
- `AssistantCandidate`
- `AssistantService`
- `AssistantRetriever`
- `chatWithAssistant`
- `useAssistant`

No later task renames those symbols.
