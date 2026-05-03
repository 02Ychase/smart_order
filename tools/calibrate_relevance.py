"""Calibrate relevance_grades by running real RAG retrieval and auto-scoring results.

For each case, retrieves results from the full RAG pipeline, then assigns
a relevance grade (1-5) based on how well each result matches the case constraints.

Usage:
    uv run tools/calibrate_relevance.py              # calibrate all cases
    uv run tools/calibrate_relevance.py --limit 20   # calibrate first 20
    uv run tools/calibrate_relevance.py --dry-run    # preview without writing
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def _score_result(item: dict, case: dict) -> int:
    """Score a retrieved result 1-5 based on how well it matches the case.

    5 = perfect match (right cuisine + meets all constraints)
    4 = very relevant (right cuisine, most constraints met)
    3 = somewhat relevant (right source_type, some constraints)
    2 = marginally relevant (right source_type only)
    1 = not relevant (wrong source_type)
    """
    constraints = case.get("constraints") or {}
    facts = item.get("facts", {})
    score = 3  # base score for existing

    # Source type match
    expected_type = case.get("expected_source_type")
    actual_type = item.get("source_type", "")
    if expected_type and actual_type != expected_type:
        return 1

    # Cuisine match (strong signal)
    cuisine_types = (
        constraints.get("cuisine_types")
        or constraints.get("allowed_cuisine_types")
        or []
    )
    if cuisine_types:
        cuisine = str(facts.get("cuisine_type", ""))
        if any(c in cuisine for c in cuisine_types):
            score = 5
        else:
            score = max(2, score - 1)

    # Flavor match
    flavor_prefs = constraints.get("flavor_preferences") or []
    if flavor_prefs:
        text = " ".join(str(v) for v in facts.values())
        if any(f in text for f in flavor_prefs):
            score = min(5, score + 1)
        else:
            score = max(1, score - 1)

    # Budget match
    budget_max = constraints.get("budget_max")
    price = facts.get("price")
    if budget_max is not None and price is not None:
        party = int(constraints.get("party_size") or 1)
        if float(price) * party <= float(budget_max):
            score = min(5, score + 1)
        else:
            score = max(1, score - 1)

    # Allergen match (penalty for containing excluded allergens)
    exclude_allergens = constraints.get("exclude_allergens") or []
    if exclude_allergens:
        allergens = set(str(a) for a in (facts.get("allergens") or []))
        if any(a in allergens for a in exclude_allergens):
            score = max(1, score - 2)

    # Required keywords bonus
    required_kw = constraints.get("required_keywords") or []
    if required_kw:
        text = " ".join(str(v) for v in facts.values())
        if all(kw in text for kw in required_kw):
            score = min(5, score + 1)

    # Sort/preference alignment
    if constraints.get("sort_by") or constraints.get("price_preference"):
        score = min(5, score + 1)

    # Forbidden keywords penalty
    forbidden_kw = constraints.get("forbidden_keywords") or []
    if forbidden_kw:
        text = " ".join(str(v) for v in facts.values())
        if any(kw in text for kw in forbidden_kw):
            score = max(1, score - 2)

    return max(1, min(5, score))


def _serialize_evidence(e) -> dict:
    """Convert RagEvidence to dict."""
    return {
        "source_type": getattr(e, "source_type", ""),
        "source_id": getattr(e, "source_id", 0),
        "merchant_id": getattr(e, "merchant_id", 0),
        "title": getattr(e, "title", ""),
        "facts": dict(getattr(e, "facts", {})),
        "why_matched": list(getattr(e, "why_matched", [])),
        "citation": str(getattr(e, "citation", "")),
        "score": getattr(e, "score", 0.0),
    }


def calibrate(cases_path: str, output_path: str | None = None,
              limit: int | None = None, dry_run: bool = False):
    from api.db import SessionLocal
    from service.rag.retriever import AdvancedRagRetriever
    from tools.evaluate_assistant_rag import _agent_plan_for_case

    cases_path = Path(cases_path)
    cases = [json.loads(line) for line in
             cases_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if limit:
        cases = cases[:limit]

    output_path = Path(output_path) if output_path else None

    session = SessionLocal()
    retriever = AdvancedRagRetriever(session=session)

    updated_cases = []
    stats = {"total": len(cases), "scored": 0, "skipped": 0}

    try:
        for case in cases:
            try:
                agent_plan = _agent_plan_for_case(case)
                evidence = retriever.retrieve(
                    case["query"], agent_plan, memories=[], limit=5
                )
                serialized = [_serialize_evidence(e) for e in evidence]

                if serialized:
                    grades = {}
                    for item in serialized:
                        key = f"{item['source_type']}:{item['source_id']}"
                        grade = _score_result(item, case)
                        grades[key] = grade
                    case["relevance_grades"] = grades
                    stats["scored"] += 1
                else:
                    # Keep existing grades or set empty
                    case.setdefault("relevance_grades", {})
                    stats["skipped"] += 1

            except Exception as e:
                print(f"  WARN: case '{case.get('id', case['query'][:30])}' failed: {e}")
                case.setdefault("relevance_grades", {})
                stats["skipped"] += 1

            updated_cases.append(case)

    finally:
        session.close()

    if not dry_run and output_path:
        lines = [json.dumps(c, ensure_ascii=False) + "\n" for c in updated_cases]
        output_path.write_text("".join(lines), encoding="utf-8")
        print(f"\nWrote {len(updated_cases)} cases to {output_path}")

    # Print summary
    print(f"\nCalibration summary:")
    print(f"  Total cases:     {stats['total']}")
    print(f"  Scored (grades): {stats['scored']}")
    print(f"  Skipped (empty): {stats['skipped']}")

    # Print a few examples
    print("\nExample calibrated grades:")
    for case in updated_cases[:3]:
        q = case["query"]
        grades = case.get("relevance_grades", {})
        print(f"  '{q}': {grades}")


def main():
    args = sys.argv[1:]
    dry_run = "--dry-run" in args
    limit = None
    for i, a in enumerate(args):
        if a == "--limit" and i + 1 < len(args):
            limit = int(args[i + 1])

    cases_path = PROJECT_ROOT / "tests/eval/assistant_rag_cases.jsonl"
    output_path = cases_path  # overwrite in-place
    if dry_run:
        output_path = None

    calibrate(
        cases_path=str(cases_path),
        output_path=str(output_path) if output_path else None,
        limit=limit,
        dry_run=dry_run,
    )


if __name__ == "__main__":
    main()
