from __future__ import annotations

from service.agent_runtime.state import AgentPlan
from service.agent_state import EvidencePack, ToolResult
from service.rag.retriever import AdvancedRagRetriever


def _to_legacy_evidence(item):
    if isinstance(item, EvidencePack):
        return item
    return EvidencePack(
        source_type=item.source_type,
        source_id=item.source_id,
        merchant_id=item.merchant_id,
        title=item.title,
        facts=item.facts,
        why_matched=item.why_matched,
        citation=item.citation,
        score=item.score,
    )


def search_catalog_tool(query: str, limit: int = 5, session=None, _retriever=None) -> ToolResult:
    retriever = _retriever or AdvancedRagRetriever(session=session)
    agent_plan = AgentPlan(intent="knowledge", normalized_query=query, requires_rag=True)
    try:
        rag_evidence = retriever.retrieve(query, agent_plan=agent_plan, memories=[], limit=limit)
    except TypeError:
        rag_evidence = retriever.retrieve(query, limit=limit)
    evidence = [_to_legacy_evidence(item) for item in rag_evidence]
    return ToolResult.ok_result(
        tool_name="search_catalog",
        data={"count": len(evidence)},
        evidence=evidence,
    )
