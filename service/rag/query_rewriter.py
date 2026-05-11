from __future__ import annotations

import json
import logging

logger = logging.getLogger(__name__)


class QueryRewriter:
    def __init__(self, llm=None, prompt_key: str = "agent.query_rewrite") -> None:
        self._llm = llm
        self._prompt_key = prompt_key

    def rewrite(self, original_query: str, max_queries: int = 3) -> list[str]:
        if self._llm is None:
            try:
                self._llm = _DefaultLLM()
            except Exception:
                logger.warning("No LLM available for query rewriting, returning original")
                return [original_query]

        try:
            from service.agent_runtime.prompts import PromptRegistry
            system_prompt = PromptRegistry().load(self._prompt_key)
            raw = self._llm.call(original_query, system_prompt)
            queries = self._parse_queries(raw, max_queries)
            if not queries:
                return [original_query]
            return queries
        except Exception:
            logger.warning("Query rewriting failed, returning original", exc_info=True)
            return [original_query]

    @staticmethod
    def _parse_queries(raw: str, max_queries: int) -> list[str]:
        text = raw.strip()
        if text.startswith("```"):
            text = text.replace("```json", "").replace("```", "").strip()
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            text = text[start:end + 1]
        parsed = json.loads(text)
        queries = parsed.get("queries", [])
        seen = set()
        deduplicated = []
        for q in queries:
            q = str(q).strip()
            if q and q not in seen:
                seen.add(q)
                deduplicated.append(q)
        return deduplicated[:max_queries]


class _DefaultLLM:
    def __init__(self):
        from tools.llm_tool import call_llm
        self._call_llm = call_llm

    def call(self, query: str, system_instruction: str) -> str:
        return self._call_llm(query=query, system_instruction=system_instruction)
