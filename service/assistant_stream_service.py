from __future__ import annotations

import asyncio
import uuid
from typing import AsyncIterator

from langchain_core.messages import AIMessage, HumanMessage

from service.agent_runtime.graph import build_agent_graph
from service.agent_runtime.nodes import LocalActionExecutor
from service.assistant_service import _conversation_store
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
                use_llm_response=False,
            )

    async def stream_chat_tokens(
        self, message: str, session_id: str | None = None, user_id: int | None = None,
    ) -> AsyncIterator[dict]:
        session_id = session_id or str(uuid.uuid4())
        self._ensure_graph()

        history = _conversation_store.get_history(session_id)
        new_message = HumanMessage(content=message)
        messages = history + [new_message]

        initial_state = {
            "messages": messages,
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
        response_message = ""

        result = await asyncio.to_thread(self._graph.invoke, initial_state, config)
        payload = dict(result.get("response_payload") or {})
        response_message = payload.get("message", "")

        if result.get("recent_evidence"):
            streamed_message = ""
            async for token in self._stream_grounded_response(
                user_message=message,
                response_type=payload.get("response_type", "recommendation"),
                evidence=result.get("recent_evidence") or [],
            ):
                streamed_message += token
                yield {"type": "token", "content": token}

            if streamed_message:
                response_message = streamed_message
                payload["message"] = streamed_message
        else:
            async for token in self._stream_text(response_message):
                yield {"type": "token", "content": token}

        if payload:
            yield {"type": "payload", "data": payload}

        _conversation_store.append(session_id, new_message)
        if response_message:
            _conversation_store.append(session_id, AIMessage(content=response_message))

        yield {"type": "done"}

    async def _stream_grounded_response(
        self,
        *,
        user_message: str,
        response_type: str,
        evidence: list[dict],
    ) -> AsyncIterator[str]:
        try:
            from langchain.chat_models import init_chat_model
            from langchain_core.prompts import ChatPromptTemplate

            from service.agent_runtime.nodes import _build_structured_data, _format_evidence_for_llm, _template_recommendation
            from service.agent_runtime.prompts import PromptRegistry
            from service.config import get_config
            import os

            if get_config().guardrails.enable_output_guardrail:
                recommendations, _ = _build_structured_data(evidence)
                async for token in self._stream_text(_template_recommendation(recommendations)):
                    yield token
                return

            model_name = os.getenv("MODEL_NAME")
            if not model_name:
                raise ValueError("MODEL_NAME not configured")

            evidence_text = _format_evidence_for_llm(evidence)
            system_prompt = PromptRegistry().load("agent.answer_grounded")
            prompt = f"用户消息：{user_message}\n意图：{response_type}\n\n检索到的证据：\n{evidence_text}\n\n请基于证据生成自然回复。"
            chain = ChatPromptTemplate.from_messages([
                ("system", "{system_instruction}"),
                ("human", "{query}"),
            ]) | init_chat_model(model=model_name, model_provider="openai")

            async for chunk in chain.astream({"system_instruction": system_prompt, "query": prompt}):
                content = getattr(chunk, "content", "")
                if content:
                    yield content
        except Exception:
            from service.agent_runtime.nodes import _build_structured_data, _template_recommendation

            recommendations, _ = _build_structured_data(evidence)
            async for token in self._stream_text(_template_recommendation(recommendations)):
                yield token

    async def _stream_text(self, text: str) -> AsyncIterator[str]:
        for char in text or "":
            yield char
            await asyncio.sleep(0.02)
