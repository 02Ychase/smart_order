from __future__ import annotations

from service.agent_state import ToolResult
from service.rag_retriever import RagRetriever


def search_catalog_tool(query: str, limit: int = 5, session=None, _retriever=None) -> ToolResult:
    retriever = _retriever or RagRetriever(session=session)
    evidence = retriever.retrieve(query, limit=limit)
    return ToolResult.ok_result(
        tool_name="search_catalog",
        data={"count": len(evidence)},
        evidence=evidence,
    )
