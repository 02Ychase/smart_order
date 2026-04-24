from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from api.db import SessionLocal
from service.rag_retriever import RagRetriever


def _passes_constraints(evidence, constraints: dict) -> bool:
    facts = getattr(evidence, "facts", {})
    budget = constraints.get("budget_max")
    party_size = constraints.get("party_size") or 1
    if budget is not None and facts.get("price") is not None:
        if float(facts["price"]) * int(party_size) > float(budget):
            return False

    exclude_allergens = constraints.get("exclude_allergens") or []
    allergens = set(facts.get("allergens") or [])
    if any(item in allergens for item in exclude_allergens):
        return False

    cuisine_types = constraints.get("cuisine_types") or []
    if cuisine_types and facts.get("cuisine_type") not in cuisine_types:
        return False

    return True


def evaluate_cases(cases: list[dict], retriever) -> dict:
    recall_hits = 0
    constraint_passes = 0
    for case in cases:
        evidence = retriever.retrieve(case["query"], limit=5)
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

    case_count = len(cases)
    return {
        "case_count": case_count,
        "recall_at_5": recall_hits / case_count if case_count else 0.0,
        "constraint_pass_rate": constraint_passes / case_count if case_count else 0.0,
    }


def load_cases(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> int:
    cases_path = Path("tests/eval/assistant_rag_cases.jsonl")
    cases = load_cases(cases_path)
    session = SessionLocal()
    try:
        metrics = evaluate_cases(cases, retriever=RagRetriever(session=session))
    finally:
        session.close()
    print(json.dumps(metrics, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
