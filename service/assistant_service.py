import os

from sqlalchemy.orm import Session

from api.schemas import AssistantChatRequest, AssistantChatResponse, AssistantHealthResponse
from service.assistant_composer import compose_assistant_response
from service.assistant_constraint_parser import parse_assistant_query
from service.assistant_retriever import AssistantRetriever
from service.assistant_session_store import InMemoryAssistantSessionStore
from service.constraint_resolver import ConstraintResolver
from service.grounded_responder import GroundedResponder
from service.intent_router import IntentRouter
from tools.assistant_vector_store import AssistantVectorStore

_SESSION_STORE = InMemoryAssistantSessionStore()


class AssistantService:
    def __init__(self, session: Session):
        self.session = session
        self.session_store = _SESSION_STORE
        self.retriever_cls = AssistantRetriever
        self.intent_router = IntentRouter()
        self.constraint_resolver = ConstraintResolver()
        self.grounded_responder = GroundedResponder()

    def chat(self, request: AssistantChatRequest) -> AssistantChatResponse:
        state = self.session_store.get_or_create(request.session_id)

        # Step 1: Route intent
        routing = self.intent_router.route(request.message)

        # Step 2: Handle greeting directly
        if routing.intent == "greeting":
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

        # Step 3: Handle action intent
        if routing.intent == "action_intent":
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

        # Step 4: Handle unsupported
        if routing.intent == "unsupported":
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

        # Step 5: Resolve constraints for recommendation/comparison/knowledge
        constraints = self.constraint_resolver.resolve(request.message)

        # Step 6: Check if clarification needed
        if routing.intent == "recommendation" and not constraints.is_sufficient_for_recommendation():
            return {
                "session_id": state.session_id,
                "message": "请告诉我这顿大概几个人吃、预算多少？",
                "response_type": "clarification",
                "needs_clarification": True,
                "clarification_question": "请告诉我这顿大概几个人吃、预算多少？",
                "extracted_constraints": None,
                "recommendations": [],
                "comparisons": [],
                "citations": [],
                "suggested_actions": [],
            }

        # Step 7: Retrieve evidence
        candidates = []
        if routing.requires_retrieval:
            retriever = self.retriever_cls(self.session)
            candidates = retriever.retrieve(constraints)

        # Step 8: Generate grounded response
        response = self.grounded_responder.respond(
            intent=routing.intent,
            user_message=request.message,
            constraints=constraints,
            evidence=candidates,
            session_context=[],
        )

        self.session_store.update(
            session_id=state.session_id,
            user_message=request.message,
            parsed_query=constraints,
            candidate_ids=[candidate.source_id for candidate in candidates],
        )

        return {**response, "session_id": state.session_id}


def build_assistant_health() -> AssistantHealthResponse:
    vector_store_ready = AssistantVectorStore().is_ready()
    llm_ready = bool(os.getenv("MODEL_NAME"))
    return {
        "status": "ok",
        "llm_ready": llm_ready,
        "vector_store_ready": vector_store_ready,
        "degraded_mode": not vector_store_ready,
    }
