from __future__ import annotations

import json
import inspect
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from api.db import SessionLocal
from service.agent_runtime.state import AgentPlan
from service.rag.retriever import AdvancedRagRetriever


def _passes_constraints(evidence, constraints: dict) -> bool:
    facts = getattr(evidence, "facts", {})
    text = _evidence_text(evidence)
    budget = constraints.get("budget_max")
    party_size = constraints.get("party_size") or 1
    if budget is not None and facts.get("price") is not None:
        if float(facts["price"]) * int(party_size) > float(budget):
            return False

    exclude_allergens = constraints.get("exclude_allergens") or []
    allergens = set(facts.get("allergens") or [])
    if any(item in allergens for item in exclude_allergens):
        return False

    cuisine_types = (
        constraints.get("cuisine_types")
        or constraints.get("allowed_cuisine_types")
        or []
    )
    if cuisine_types and facts.get("cuisine_type") not in cuisine_types:
        cuisine = str(facts.get("cuisine_type") or "")
        if not any(item in cuisine for item in cuisine_types):
            return False

    required_keywords = constraints.get("required_keywords") or []
    if required_keywords and not all(keyword in text for keyword in required_keywords):
        return False

    forbidden_keywords = constraints.get("forbidden_keywords") or []
    if forbidden_keywords and any(keyword in text for keyword in forbidden_keywords):
        return False

    return True


def _evidence_text(evidence) -> str:
    facts = getattr(evidence, "facts", {}) or {}
    parts = [
        str(getattr(evidence, "title", "")),
        str(getattr(evidence, "citation", "")),
        " ".join(str(item) for item in getattr(evidence, "why_matched", []) or []),
    ]
    parts.extend(str(value) for value in facts.values())
    return " ".join(parts)


def _passes_diversity(evidence: list) -> bool:
    merchant_ids = [
        getattr(item, "facts", {}).get("merchant_id")
        for item in evidence
        if getattr(item, "source_type", "") == "dish"
    ]
    merchant_ids = [item for item in merchant_ids if item is not None]
    if len(merchant_ids) <= 1:
        return True
    return len(set(merchant_ids[:3])) >= min(2, len(set(merchant_ids)))


def _has_citation(evidence) -> bool:
    return bool(str(getattr(evidence, "citation", "")).strip())


def evaluate_cases(cases: list[dict], retriever) -> dict:
    recall_hits = 0
    constraint_passes = 0
    diversity_passes = 0
    citation_scores = []
    for case in cases:
        evidence = _retrieve_case(case, retriever, limit=5)
        expected_ids = set(case.get("expected_source_ids") or [])
        if expected_ids:
            retrieved_ids = {item.source_id for item in evidence}
            recall_hits += int(bool(expected_ids & retrieved_ids))
        elif case.get("expected_source_type"):
            recall_hits += int(any(item.source_type == case["expected_source_type"] for item in evidence))
        else:
            recall_hits += int(bool(evidence))

        constraints = case.get("constraints") or {}
        constraint_passes += int(all(_passes_constraints(item, constraints) for item in evidence))
        diversity_passes += int(_passes_diversity(evidence))
        citation_scores.append(
            sum(1 for item in evidence if _has_citation(item)) / len(evidence)
            if evidence
            else 0.0
        )

    case_count = len(cases)
    return {
        "case_count": case_count,
        "recall_at_5": recall_hits / case_count if case_count else 0.0,
        "constraint_pass_rate": constraint_passes / case_count if case_count else 0.0,
        "diversity_pass_rate": diversity_passes / case_count if case_count else 0.0,
        "citation_coverage": sum(citation_scores) / case_count if case_count else 0.0,
    }


def _retrieve_case(case: dict, retriever, limit: int) -> list:
    parameters = inspect.signature(retriever.retrieve).parameters
    if "agent_plan" not in parameters:
        return retriever.retrieve(case["query"], limit=limit)

    return retriever.retrieve(
        case["query"],
        agent_plan=_agent_plan_for_case(case),
        memories=[],
        limit=limit,
    )


def _agent_plan_for_case(case: dict) -> AgentPlan:
    constraints = case.get("constraints") or {}
    cuisine_types = (
        constraints.get("cuisine_types")
        or constraints.get("allowed_cuisine_types")
        or []
    )
    required_keywords = constraints.get("required_keywords") or []
    expected_type = case.get("expected_source_type")
    intent = "knowledge" if expected_type == "merchant" else "recommendation"
    return AgentPlan(
        intent=intent,
        normalized_query=case["query"],
        requires_rag=True,
        filters={
            "cuisine_types": cuisine_types,
            "flavor_preferences": required_keywords,
            "required_keywords": required_keywords,
            "forbidden_keywords": constraints.get("forbidden_keywords") or [],
            "budget_max": constraints.get("budget_max"),
            "party_size": constraints.get("party_size"),
            "exclude_allergens": constraints.get("exclude_allergens") or [],
        },
    )


def load_cases(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> int:
    cases_path = Path("tests/eval/assistant_rag_cases.jsonl")
    cases = load_cases(cases_path)
    session = SessionLocal()
    try:
        metrics = evaluate_cases(cases, retriever=AdvancedRagRetriever(session=session))
    finally:
        session.close()
    print(json.dumps(metrics, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
