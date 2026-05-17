from __future__ import annotations

import asyncio
import uuid
from typing import AsyncIterator

from langchain_core.messages import AIMessage, HumanMessage

from service.agent_runtime.graph import get_agent_graph
from service.assistant_service import _build_runtime, _conversation_store


class AssistantStreamService:
    def __init__(self, session=None):
        self.session = session
        # Allow test override
        self._graph = None

    async def stream_chat_tokens(
        self, message: str, session_id: str | None = None, user_id: int | None = None,
    ) -> AsyncIterator[dict]:
        session_id = session_id or str(uuid.uuid4())
        graph = self._graph or get_agent_graph()

        history = _conversation_store.get_history(session_id)
        new_message = HumanMessage(content=message)
        messages = history + [new_message]

        last_recs = _conversation_store.get_metadata(session_id, "last_recommendations", [])
        initial_state = {
            "messages": messages,
            "session_id": session_id,
            "user_id": user_id,
            "loaded_user_memories": [],
            "recent_evidence": [],
            "recent_action_ids": [],
            "tool_results": [],
            "last_recommendations": last_recs,
            "iteration_count": 0,
            "max_iterations": 5,
        }

        runtime = _build_runtime(self.session, use_llm_response=False)
        config = {
            "configurable": {
                "thread_id": session_id,
                "runtime": runtime,
            },
        }

        response_message = ""

        result = await asyncio.to_thread(graph.invoke, initial_state, config)
        payload = dict(result.get("response_payload") or {})
        response_message = payload.get("message", "")

        # Build conversation context for the streaming LLM response
        from service.agent_runtime.nodes import _format_recent_turns
        conversation_history = _format_recent_turns(messages, max_turns=2)

        if result.get("recent_evidence"):
            streamed_message = ""
            async for token in self._stream_grounded_response(
                user_message=message,
                response_type=payload.get("response_type", "recommendation"),
                evidence=result.get("recent_evidence") or [],
                conversation_history=conversation_history,
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
        # Persist recommendations for next-turn ordinal resolution
        recs = payload.get("recommendations") or result.get("last_recommendations", [])
        if recs:
            _conversation_store.set_metadata(session_id, "last_recommendations", recs)

        yield {"type": "done"}

    async def _stream_grounded_response(
        self,
        *,
        user_message: str,
        response_type: str,
        evidence: list[dict],
        conversation_history: str = "",
    ) -> AsyncIterator[str]:
        try:
            from langchain.chat_models import init_chat_model
            from langchain_core.prompts import ChatPromptTemplate

            from service.agent_runtime.nodes import _build_structured_data, _format_evidence_for_llm, _template_recommendation
            from service.agent_runtime.prompts import PromptRegistry
            from service.config import get_config
            import os

            model_name = os.getenv("MODEL_NAME")
            if not model_name:
                raise ValueError("MODEL_NAME not configured")

            evidence_text = _format_evidence_for_llm(evidence)
            system_prompt = PromptRegistry().load("agent.answer_grounded")
            parts = []
            if conversation_history:
                parts.append(f"对话历史：\n{conversation_history}\n")
            parts.append(f"用户最新消息：{user_message}")
            parts.append(f"意图：{response_type}")
            parts.append(f"\n检索到的证据：\n{evidence_text}")
            parts.append("\n请基于证据生成自然回复。")
            prompt = "\n".join(parts)

            if get_config().guardrails.enable_output_guardrail:
                chain = ChatPromptTemplate.from_messages([
                    ("system", "{system_instruction}"),
                    ("human", "{query}"),
                ]) | init_chat_model(model=model_name, model_provider="openai")

                result = await asyncio.to_thread(
                    chain.invoke, {"system_instruction": system_prompt, "query": prompt}
                )
                llm_response = getattr(result, "content", str(result))

                from service.guardrails import OutputGuardrail
                output_result = OutputGuardrail().check(llm_response, evidence)
                if not output_result.allowed:
                    recommendations, _ = _build_structured_data(evidence)
                    llm_response = _template_recommendation(recommendations)

                async for token in self._stream_text(llm_response):
                    yield token
            else:
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
