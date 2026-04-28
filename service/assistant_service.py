import os

from langchain_core.messages import HumanMessage
from sqlalchemy.orm import Session

from api.schemas import AssistantChatRequest, AssistantChatResponse, AssistantHealthResponse
from service.agent_runtime.graph import build_agent_graph
from service.agent_core import AgentCore
from service.agent_loop import AgentLoop
from service.assistant_composer import compose_assistant_response
from service.assistant_orchestrator import AssistantOrchestrator
from service.assistant_retriever import AssistantRetriever
from service.assistant_session_store import InMemoryAssistantSessionStore
from service.grounded_responder import GroundedResponder
from service.intent_router import IntentRouter
from service.tool_registry import ToolRegistry, ToolSchema
from service.tools.address_tool import save_address_tool
from service.tools.cart_tool import add_to_cart_tool
from tools.assistant_vector_store import AssistantVectorStore

_SESSION_STORE = InMemoryAssistantSessionStore()


class AssistantService:
    def __init__(self, session: Session):
        self.session = session
        self.session_store = _SESSION_STORE
        self.retriever_cls = AssistantRetriever
        self.intent_router = IntentRouter()
        self.grounded_responder = GroundedResponder()
        self.agent_loop = AgentLoop(session)
        self.agent_core = AgentCore()
        self._graph = None
        self._setup_tool_registry()

    def _setup_tool_registry(self) -> None:
        """Register tools that the Agent Core can invoke."""
        self.tool_registry = ToolRegistry()
        self.tool_registry.register(
            ToolSchema(
                name="search_knowledge_base",
                description="Search merchants and dishes knowledge base",
                parameters={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                    },
                    "required": ["query"],
                },
            ),
            lambda query: self._search_knowledge(query),
        )
        self.tool_registry.register(
            ToolSchema(
                name="recommend_dishes",
                description="Recommend dishes based on constraints",
                parameters={
                    "type": "object",
                    "properties": {
                        "budget": {"type": "number"},
                        "party_size": {"type": "integer"},
                        "preferences": {"type": "string"},
                    },
                },
            ),
            lambda **kwargs: self._recommend_dishes(**kwargs),
        )
        self.tool_registry.register(
            ToolSchema(
                name="add_to_cart",
                description="Add a dish to the user's shopping cart",
                parameters={
                    "type": "object",
                    "properties": {
                        "dish_id": {"type": "integer"},
                        "quantity": {"type": "integer", "default": 1},
                    },
                    "required": ["dish_id"],
                },
            ),
            lambda **kwargs: add_to_cart_tool(session=self.session, **kwargs),
        )
        self.tool_registry.register(
            ToolSchema(
                name="save_address",
                description="Save a new delivery address for the user",
                parameters={
                    "type": "object",
                    "properties": {
                        "user_id": {"type": "integer"},
                        "label": {"type": "string"},
                        "contact_name": {"type": "string"},
                        "contact_phone": {"type": "string"},
                        "city": {"type": "string"},
                        "district": {"type": "string"},
                        "detail_address": {"type": "string"},
                        "longitude": {"type": "number"},
                        "latitude": {"type": "number"},
                        "is_default": {"type": "boolean", "default": False},
                    },
                    "required": ["user_id", "label", "contact_name", "contact_phone", "city", "district", "detail_address", "longitude", "latitude"],
                },
            ),
            lambda **kwargs: save_address_tool(session=self.session, **kwargs),
        )

    def _search_knowledge(self, query: str) -> list[dict]:
        """Execute knowledge search via retriever."""
        retriever = self.retriever_cls(self.session)
        from service.assistant_models import AssistantParsedQuery
        parsed = AssistantParsedQuery(
            raw_message=query,
            query_type="knowledge",
        )
        candidates = retriever.retrieve(parsed)
        return [c.to_dict() for c in candidates] if candidates else []

    def _recommend_dishes(self, budget: float = None, party_size: int = None, preferences: str = "") -> list[dict]:
        """Execute recommendation via retriever."""
        retriever = self.retriever_cls(self.session)
        from service.assistant_models import AssistantParsedQuery
        parsed = AssistantParsedQuery(
            raw_message=preferences,
            query_type="recommendation",
            budget_max=budget,
            party_size=party_size,
        )
        candidates = retriever.retrieve(parsed)
        return [c.to_dict() for c in candidates] if candidates else []

    def chat(self, request: AssistantChatRequest) -> AssistantChatResponse:
        if not isinstance(request, AssistantChatRequest):
            return self._legacy_chat(request)

        session_id = request.session_id or self.session_store.get_or_create(
            None,
            user_id=request.user_id,
        ).session_id
        if self._graph is None:
            self._graph = build_agent_graph()
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

    def _legacy_chat(self, request) -> dict:
        state = self.session_store.get_or_create(request.session_id)

        decision = self.agent_core.decide(request.message)

        if decision.intent == "greeting":
            response = self.grounded_responder.respond(
                intent="greeting",
                user_message=request.message,
                constraints=None,
                evidence=[],
                session_context=[],
            )
            self.session_store.update(
                session_id=state.session_id,
                user_message=request.message,
                parsed_query=None,
                candidate_ids=[],
            )
            return {**response, "session_id": state.session_id}

        if decision.needs_clarification:
            return {
                "session_id": state.session_id,
                "message": decision.clarification_question or "请告诉我这顿大概几个人吃、预算多少？",
                "response_type": "clarification",
                "needs_clarification": True,
                "clarification_question": decision.clarification_question or "请告诉我这顿大概几个人吃、预算多少？",
                "extracted_constraints": None,
                "recommendations": [],
                "comparisons": [],
                "citations": [],
                "suggested_actions": [],
            }

        if decision.intent == "action":
            user_id = getattr(request, "user_id", None)
            if user_id and decision.tool_calls:
                try:
                    tool_call = decision.tool_calls[0]
                    params = tool_call.get("parameters", {})
                    if "user_id" not in params:
                        params["user_id"] = user_id
                    result = self.tool_registry.execute(tool_call["name"], params)
                    return {
                        "session_id": state.session_id,
                        "message": f"操作已完成: {result}",
                        "response_type": "action_completed",
                        "needs_clarification": False,
                        "clarification_question": None,
                        "extracted_constraints": None,
                        "recommendations": [],
                        "comparisons": [],
                        "citations": [],
                        "suggested_actions": [],
                    }
                except Exception:
                    pass

            response = self.grounded_responder.respond(
                intent="action_intent",
                user_message=request.message,
                constraints=None,
                evidence=[],
                session_context=[],
            )
            self.session_store.update(
                session_id=state.session_id,
                user_message=request.message,
                parsed_query=None,
                candidate_ids=[],
            )
            return {**response, "session_id": state.session_id}

        if decision.intent == "unsupported":
            response = self.grounded_responder.respond(
                intent="unsupported",
                user_message=request.message,
                constraints=None,
                evidence=[],
                session_context=[],
            )
            self.session_store.update(
                session_id=state.session_id,
                user_message=request.message,
                parsed_query=None,
                candidate_ids=[],
            )
            return {**response, "session_id": state.session_id}

        tool_results = []
        if decision.tool_calls:
            for tool_call in decision.tool_calls:
                try:
                    result = self.tool_registry.execute(
                        tool_call["name"],
                        tool_call.get("parameters", {}),
                    )
                    tool_results.append({"tool": tool_call["name"], "result": result})
                except Exception as e:
                    tool_results.append({"tool": tool_call["name"], "error": str(e)})

        candidates = []
        if decision.intent in ("knowledge", "recommendation") and not tool_results:
            from service.assistant_models import AssistantParsedQuery
            parsed = AssistantParsedQuery(
                raw_message=request.message,
                query_type=decision.intent,
            )
            retriever = self.retriever_cls(self.session)
            candidates = retriever.retrieve(parsed)

        response = self.grounded_responder.respond(
            intent=decision.intent,
            user_message=request.message,
            constraints=None,
            evidence=candidates,
            session_context=[],
            tool_results=tool_results,
        )

        self.session_store.update(
            session_id=state.session_id,
            user_message=request.message,
            parsed_query=None,
            candidate_ids=[candidate.source_id for candidate in candidates],
        )

        return {**response, "session_id": state.session_id}


class AssistantCandidate:
    """Helper to ensure candidates have a to_dict method."""
    pass


def build_assistant_health() -> AssistantHealthResponse:
    vector_store_ready = AssistantVectorStore().is_ready()
    llm_ready = bool(os.getenv("MODEL_NAME"))
    return {
        "status": "ok",
        "llm_ready": llm_ready,
        "vector_store_ready": vector_store_ready,
        "degraded_mode": not vector_store_ready,
    }
