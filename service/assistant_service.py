import asyncio
import os
import threading
import uuid

from langchain_core.messages import AIMessage, HumanMessage
from sqlalchemy.orm import Session

from api.schemas import AssistantChatRequest, AssistantChatResponse, AssistantHealthResponse
from service.agent_runtime.graph import get_agent_graph
from service.agent_runtime.nodes import LocalActionExecutor
from service.agent_runtime.runtime import AgentRuntimeContext
from service.config import get_config
from service.conversation_store import InMemoryConversationStore
from service.rag.retriever import AdvancedRagRetriever
from service.user_memory_service import UserMemoryService
from tools.assistant_vector_store import AssistantVectorStore

# ── Cached stateless components (module-level singletons) ───────────
# These are expensive to create but don't depend on a DB session.

_dense_route = None
_cross_encoder = None
_query_planner = None
_reranker = None
_components_lock = threading.Lock()


def _get_cached_components():
    """Lazily initialise and return cached RAG sub-components (thread-safe)."""
    global _dense_route, _cross_encoder, _query_planner, _reranker

    # Fast path: all already initialised
    if _dense_route is not None and _cross_encoder is not None and _query_planner is not None and _reranker is not None:
        return _dense_route, _cross_encoder, _query_planner, _reranker

    with _components_lock:
        if _dense_route is None:
            from service.rag.recall import DenseVectorRecallRoute
            _dense_route = DenseVectorRecallRoute()
        if _cross_encoder is None:
            from service.rag.cross_encoder import CrossEncoderReranker
            _cross_encoder = CrossEncoderReranker()
        if _query_planner is None:
            from service.rag.query_planner import RagQueryPlanner
            _query_planner = RagQueryPlanner()
        if _reranker is None:
            from service.rag.reranker import WeightedReranker
            _reranker = WeightedReranker()

    return _dense_route, _cross_encoder, _query_planner, _reranker


def _build_retriever(session):
    """Build a per-request retriever reusing cached stateless sub-components."""
    dense_route, cross_encoder, query_planner, reranker = _get_cached_components()

    from api.db import SessionLocal
    from service.catalog_service import CatalogService
    from service.rag.recall import BusinessRecallRoute, SparseVectorRecallRoute, SqlCatalogRecallRoute

    catalog_service = CatalogService(session) if session is not None else None
    recall_routes = [dense_route]
    if catalog_service is not None:
        recall_routes.extend([
            SparseVectorRecallRoute(catalog_service),
            SqlCatalogRecallRoute(catalog_service),
            BusinessRecallRoute(catalog_service),
        ])

    return AdvancedRagRetriever(
        session=session,
        recall_routes=recall_routes,
        query_planner=query_planner,
        reranker=reranker,
        cross_encoder=cross_encoder,
        session_factory=SessionLocal,
    )


def _build_runtime(session, *, use_llm_response: bool = True) -> AgentRuntimeContext:
    """Assemble the per-request runtime context."""
    graph_session = session if session is not None and hasattr(session, "scalars") else None
    return AgentRuntimeContext(
        retriever=_build_retriever(graph_session),
        action_executor=LocalActionExecutor(session),
        memory_service=UserMemoryService(session) if graph_session is not None else None,
        use_llm_response=use_llm_response,
    )


# ── Conversation store (shared across services) ────────────────────

def _create_conversation_store() -> InMemoryConversationStore:
    cfg = get_config().agent
    return InMemoryConversationStore(
        max_messages=cfg.conversation_max_messages,
        max_sessions=cfg.conversation_max_sessions,
    )


_conversation_store = _create_conversation_store()


# ── AssistantService ────────────────────────────────────────────────

class AssistantService:
    def __init__(self, session: Session):
        self.session = session
        # Allow test override: set self._graph to a StubGraph to bypass the singleton
        self._graph = None

    def _build_invoke_input(self, request: AssistantChatRequest, session_id: str) -> tuple[dict, dict]:
        new_message = HumanMessage(content=request.message)
        history = _conversation_store.get_history(session_id)
        messages = history + [new_message]
        last_recs = _conversation_store.get_metadata(session_id, "last_recommendations", [])

        state = {
            "messages": messages,
            "session_id": session_id,
            "user_id": request.user_id,
            "loaded_user_memories": [],
            "recent_evidence": [],
            "recent_action_ids": [],
            "tool_results": [],
            "last_recommendations": last_recs,
            "iteration_count": 0,
            "max_iterations": 5,
        }

        runtime = _build_runtime(self.session, use_llm_response=True)
        config = {
            "configurable": {
                "thread_id": session_id,
                "runtime": runtime,
            },
        }
        return state, config

    @staticmethod
    def _save_conversation(session_id: str, request_message: str, result: dict):
        _conversation_store.append(session_id, HumanMessage(content=request_message))
        payload = result.get("response_payload") or {}
        response_msg = payload.get("message", "")
        if response_msg:
            _conversation_store.append(session_id, AIMessage(content=response_msg))
        # Persist structured recommendations so the next turn can resolve
        # ordinal references ("第一个") to concrete dish_ids.
        recommendations = payload.get("recommendations") or result.get("last_recommendations", [])
        if recommendations:
            _conversation_store.set_metadata(session_id, "last_recommendations", recommendations)

    def chat(self, request: AssistantChatRequest) -> AssistantChatResponse:
        session_id = request.session_id or str(uuid.uuid4())
        graph = self._graph or get_agent_graph()
        state, config = self._build_invoke_input(request, session_id)
        result = graph.invoke(state, config=config)
        self._save_conversation(session_id, request.message, result)
        return result["response_payload"]

    async def async_chat(self, request: AssistantChatRequest) -> AssistantChatResponse:
        session_id = request.session_id or str(uuid.uuid4())
        graph = self._graph or get_agent_graph()
        state, config = self._build_invoke_input(request, session_id)
        result = await asyncio.to_thread(graph.invoke, state, config)
        self._save_conversation(session_id, request.message, result)
        return result["response_payload"]


# ── Health check ────────────────────────────────────────────────────

_health_vector_store: AssistantVectorStore | None = None


def build_assistant_health() -> AssistantHealthResponse:
    global _health_vector_store
    if _health_vector_store is None:
        _health_vector_store = AssistantVectorStore(auto_create_index=False)
    vector_store_ready = _health_vector_store.is_ready()
    llm_ready = bool(os.getenv("MODEL_NAME"))
    return {
        "status": "ok",
        "llm_ready": llm_ready,
        "vector_store_ready": vector_store_ready,
        "degraded_mode": not vector_store_ready,
    }
