from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

from service.agent_runtime.state import AgentPlan

logger = logging.getLogger(__name__)


@dataclass
class EvalResult:
    case_id: str
    query: str
    expected_keywords: list[str]
    retrieved_texts: list[str]
    retrieved_source_types: list[str]
    expected_absent: list[str] = field(default_factory=list)

    def keyword_recall(self) -> float:
        if not self.expected_keywords:
            return 1.0
        combined = " ".join(self.retrieved_texts)
        hits = sum(1 for kw in self.expected_keywords if kw in combined)
        return hits / len(self.expected_keywords)

    def absence_check(self) -> bool:
        if not self.expected_absent:
            return True
        combined = " ".join(self.retrieved_texts)
        return not any(kw in combined for kw in self.expected_absent)

    def has_results(self, min_results: int = 1) -> bool:
        return len(self.retrieved_texts) >= min_results


class RagEvaluator:
    def __init__(self, retriever=None) -> None:
        self._retriever = retriever

    def evaluate(self, test_cases: list[dict]) -> list[EvalResult]:
        results = []
        for case in test_cases:
            query = case["query"]
            intent = case.get("intent", "recommendation")
            agent_plan = AgentPlan(
                intent=intent,
                normalized_query=query,
                requires_rag=True,
            )
            try:
                evidence = self._retriever.retrieve(query, agent_plan=agent_plan, memories=[], limit=5)
            except Exception as e:
                logger.warning("Eval failed for case %s: %s", case["id"], e)
                evidence = []

            retrieved_texts = []
            retrieved_source_types = []
            for item in evidence:
                facts = item.facts if hasattr(item, "facts") else {}
                text_parts = [
                    str(facts.get("dish_name", "")),
                    str(facts.get("merchant_name", "")),
                    str(facts.get("cuisine_type", "")),
                    str(facts.get("flavor_profile", "")),
                    str(getattr(item, "citation", "")),
                ]
                retrieved_texts.append(" ".join(part for part in text_parts if part))
                retrieved_source_types.append(getattr(item, "source_type", ""))

            results.append(EvalResult(
                case_id=case["id"],
                query=query,
                expected_keywords=case.get("expected_keywords", []),
                retrieved_texts=retrieved_texts,
                retrieved_source_types=retrieved_source_types,
                expected_absent=case.get("expected_absent", []),
            ))
        return results

    def summary(self, results: list[EvalResult]) -> dict:
        total = len(results)
        if total == 0:
            return {"total": 0}
        avg_recall = sum(r.keyword_recall() for r in results) / total
        has_results_count = sum(1 for r in results if r.has_results())
        absence_pass = sum(1 for r in results if r.absence_check())
        return {
            "total": total,
            "avg_keyword_recall": round(avg_recall, 3),
            "has_results_rate": round(has_results_count / total, 3),
            "absence_check_pass_rate": round(absence_pass / total, 3),
        }


def run_evaluation(golden_set_path: str | None = None, retriever=None) -> dict:
    path = Path(golden_set_path or "tools/eval_golden_set.json")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    evaluator = RagEvaluator(retriever=retriever)
    results = evaluator.evaluate(data["test_cases"])
    return evaluator.summary(results)
