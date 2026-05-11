from __future__ import annotations

import uuid
from typing import AsyncIterator

from langchain_core.messages import HumanMessage

from service.agent_runtime.graph import build_agent_graph
from service.agent_runtime.nodes import LocalActionExecutor
from service.rag.retriever import AdvancedRagRetriever
from service.user_memory_service import UserMemoryService


class AssistantStreamService:
    def __init__(self, session=None):
        self.session = session
        self._graph = None

    def _ensure_graph(self):
        if self._graph is None:
            graph_session = self.session if self.session is not None and hasattr(self.session, "scalars") else None
            self._graph = build_agent_graph(
                retriever=AdvancedRagRetriever(graph_session),
                action_executor=LocalActionExecutor(self.session),
                memory_service=UserMemoryService(self.session) if graph_session else None,
            )

    async def stream_chat_tokens(
        self, message: str, session_id: str | None = None, user_id: int | None = None,
    ) -> AsyncIterator[dict]:
        session_id = session_id or str(uuid.uuid4())
        self._ensure_graph()

        initial_state = {
            "messages": [HumanMessage(content=message)],
            "session_id": session_id,
            "user_id": user_id,
            "loaded_user_memories": [],
            "recent_evidence": [],
            "recent_action_ids": [],
            "tool_results": [],
            "iteration_count": 0,
            "max_iterations": 5,
        }

        config = {"configurable": {"thread_id": session_id}}

        async for event in self._graph.astream_events(initial_state, config=config, version="v2"):
            kind = event.get("event", "")
            if kind == "on_chat_model_stream":
                content = event.get("data", {}).get("chunk", {})
                if hasattr(content, "content") and content.content:
                    yield {"type": "token", "content": content.content}
            elif kind == "on_chain_end" and event.get("name") == "respond":
                output = event.get("data", {}).get("output", {})
                payload = output.get("response_payload")
                if payload:
                    yield {"type": "payload", "data": payload}

        yield {"type": "done"}
