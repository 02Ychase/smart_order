import asyncio
import os
import uuid

from langchain_core.messages import AIMessage, HumanMessage
from sqlalchemy.orm import Session

from api.schemas import AssistantChatRequest, AssistantChatResponse, AssistantHealthResponse
from service.agent_runtime.graph import build_agent_graph
from service.agent_runtime.nodes import LocalActionExecutor
from service.conversation_store import InMemoryConversationStore
from service.rag.retriever import AdvancedRagRetriever
from service.user_memory_service import UserMemoryService
from tools.assistant_vector_store import AssistantVectorStore

_conversation_store = InMemoryConversationStore()


class AssistantService:
    def __init__(self, session: Session):
        self.session = session
        self._graph = None

    def chat(self, request: AssistantChatRequest) -> AssistantChatResponse:
        session_id = request.session_id or str(uuid.uuid4())
        if self._graph is None:
            graph_session = self.session if self.session is not None and hasattr(self.session, "scalars") else None
            self._graph = build_agent_graph(
                retriever=AdvancedRagRetriever(graph_session),
                action_executor=LocalActionExecutor(self.session),
                memory_service=UserMemoryService(self.session) if graph_session is not None else None,
            )

        new_message = HumanMessage(content=request.message)
        history = _conversation_store.get_history(session_id)
        messages = history + [new_message]

        result = self._graph.invoke(
            {
                "messages": messages,
                "session_id": session_id,
                "user_id": request.user_id,
                "loaded_user_memories": [],
                "recent_evidence": [],
                "recent_action_ids": [],
                "tool_results": [],
                "iteration_count": 0,
                "max_iterations": 5,
            },
            config={"configurable": {"thread_id": session_id}},
        )

        _conversation_store.append(session_id, new_message)
        response_msg = result.get("response_payload", {}).get("message", "")
        if response_msg:
            _conversation_store.append(session_id, AIMessage(content=response_msg))

        return result["response_payload"]

    async def async_chat(self, request: AssistantChatRequest) -> AssistantChatResponse:
        session_id = request.session_id or str(uuid.uuid4())
        if self._graph is None:
            graph_session = self.session if self.session is not None and hasattr(self.session, "scalars") else None
            self._graph = build_agent_graph(
                retriever=AdvancedRagRetriever(graph_session),
                action_executor=LocalActionExecutor(self.session),
                memory_service=UserMemoryService(self.session) if graph_session is not None else None,
            )

        new_message = HumanMessage(content=request.message)
        history = _conversation_store.get_history(session_id)
        messages = history + [new_message]

        result = await asyncio.to_thread(
            self._graph.invoke,
            {
                "messages": messages,
                "session_id": session_id,
                "user_id": request.user_id,
                "loaded_user_memories": [],
                "recent_evidence": [],
                "recent_action_ids": [],
                "tool_results": [],
                "iteration_count": 0,
                "max_iterations": 5,
            },
            {"configurable": {"thread_id": session_id}},
        )

        _conversation_store.append(session_id, new_message)
        response_msg = result.get("response_payload", {}).get("message", "")
        if response_msg:
            _conversation_store.append(session_id, AIMessage(content=response_msg))

        return result["response_payload"]


def build_assistant_health() -> AssistantHealthResponse:
    vector_store_ready = AssistantVectorStore().is_ready()
    llm_ready = bool(os.getenv("MODEL_NAME"))
    return {
        "status": "ok",
        "llm_ready": llm_ready,
        "vector_store_ready": vector_store_ready,
        "degraded_mode": not vector_store_ready,
    }
