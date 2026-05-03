from __future__ import annotations

import argparse
import inspect
import json
import logging
import math
import statistics
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

logger = logging.getLogger(__name__)


# ── Constraint / citation / diversity helpers ──────────────────────

def _evidence_text(evidence) -> str:
    facts = getattr(evidence, "facts", {}) or {}
    parts = [
        str(getattr(evidence, "title", "")),
        str(getattr(evidence, "citation", "")),
        " ".join(str(item) for item in getattr(evidence, "why_matched", []) or []),
    ]
    parts.extend(str(value) for value in facts.values())
    return " ".join(parts)


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
    citation = getattr(evidence, "citation", None)
    if citation is None:
        return False
    return bool(str(citation).strip())


# ── Ranking metrics ────────────────────────────────────────────────

def _get_relevance(rid: str, grades: dict[str, int]) -> int:
    """Get relevance grade for a retrieved item id.

    Supports wildcard matching: 'dish:*' matches any key starting with 'dish:'.
    Exact match takes priority over wildcard.
    """
    if rid in grades:
        return grades[rid]
    prefix = rid.split(":")[0] + ":*"
    return grades.get(prefix, 0)


def _compute_hit_rate(retrieved_ids: list[str], relevance_grades: dict[str, int]) -> float:
    return 1.0 if any(_get_relevance(rid, relevance_grades) >= 1 for rid in retrieved_ids) else 0.0


def _count_total_relevant(grades: dict[str, int], retrieved_ids: list[str]) -> int:
    """Count total relevant documents, handling wildcard grades.

    When grades contain wildcards (e.g. 'dish:*'), the total relevant count
    is derived from the retrieved results since we can't know the full DB size.
    Without wildcards, this is the count of grade values >= 1.
    """
    has_wildcard = any(k.endswith(":*") for k in grades)
    if not has_wildcard:
        return sum(1 for grade in grades.values() if grade >= 1)
    return sum(1 for rid in retrieved_ids if _get_relevance(rid, grades) >= 1)


def _compute_recall_at_k(retrieved_ids: list[str], relevance_grades: dict[str, int], k: int = 5) -> float:
    total_relevant = _count_total_relevant(relevance_grades, retrieved_ids[:k])
    if total_relevant == 0:
        return 0.0
    hits = sum(1 for rid in retrieved_ids[:k] if _get_relevance(rid, relevance_grades) >= 1)
    return min(hits / total_relevant, 1.0)


def _compute_precision_at_k(retrieved_ids: list[str], relevance_grades: dict[str, int], k: int = 5) -> float:
    if k <= 0:
        return 0.0
    hits = sum(1 for rid in retrieved_ids[:k] if _get_relevance(rid, relevance_grades) >= 1)
    return hits / k


def _compute_average_precision(retrieved_ids: list[str], relevance_grades: dict[str, int]) -> float:
    total_relevant = _count_total_relevant(relevance_grades, retrieved_ids)
    if total_relevant == 0:
        return 0.0
    hits = 0
    ap = 0.0
    for i, rid in enumerate(retrieved_ids, 1):
        if _get_relevance(rid, relevance_grades) >= 1:
            hits += 1
            ap += hits / i
    return ap / total_relevant


def _compute_ndcg_at_k(retrieved_ids: list[str], relevance_grades: dict[str, int], k: int = 5) -> float:
    def _dcg(ids: list[str]) -> float:
        dcg = 0.0
        for i, rid in enumerate(ids[:k]):
            rel = _get_relevance(rid, relevance_grades)
            dcg += (2 ** rel - 1) / math.log2(i + 2)
        return dcg
    dcg = _dcg(retrieved_ids)
    ideal_order = sorted(retrieved_ids, key=lambda rid: _get_relevance(rid, relevance_grades), reverse=True)
    idcg = _dcg(ideal_order)
    if idcg == 0.0:
        return 0.0
    return dcg / idcg


def _compute_mrr(retrieved_ids: list[str], relevance_grades: dict[str, int]) -> float:
    for rank, rid in enumerate(retrieved_ids, 1):
        if _get_relevance(rid, relevance_grades) >= 1:
            return 1.0 / rank
    return 0.0


# ── Latency tracker ────────────────────────────────────────────────

class _LatencyTracker:
    def __init__(self):
        self._times: list[float] = []

    def record(self, ms: float) -> None:
        self._times.append(ms)

    def stats(self) -> dict:
        if not self._times:
            return {"p50_ms": 0, "p95_ms": 0, "p99_ms": 0, "mean_ms": 0, "count": 0}
        sorted_times = sorted(self._times)
        if len(sorted_times) < 2:
            return {
                "p50_ms": round(sorted_times[0], 2),
                "p95_ms": round(sorted_times[0], 2),
                "p99_ms": round(sorted_times[0], 2),
                "mean_ms": round(sorted_times[0], 2),
                "min_ms": round(sorted_times[0], 2),
                "max_ms": round(sorted_times[0], 2),
                "count": len(sorted_times),
            }
        quantiles = statistics.quantiles(sorted_times, n=20, method="inclusive")
        return {
            "p50_ms": round(quantiles[9], 2),
            "p95_ms": round(quantiles[18], 2),
            "p99_ms": round(max(sorted_times), 2),
            "mean_ms": round(statistics.mean(sorted_times), 2),
            "min_ms": round(sorted_times[0], 2),
            "max_ms": round(sorted_times[-1], 2),
            "count": len(sorted_times),
        }


# ── LLM-as-judge ──────────────────────────────────────────────────

_JUDGE_PROMPT = """你是检索结果相关性评估器。根据用户查询和检索到的菜品/商家结果，评估该结果的相关性（1-5分）：

5 = 完美匹配，正是用户所问
4 = 高度相关，仅有微小不匹配
3 = 部分相关但不是最理想的
2 = 勉强相关
1 = 完全不相关

只回复一个整数分数，不要其他任何字符。"""


def _llm_relevance_score(query: str, evidence, model_name: str | None = None) -> int:
    try:
        from tools.llm_tool import call_llm

        facts = getattr(evidence, "facts", {})
        evidence_text = json.dumps({
            "title": getattr(evidence, "title", ""),
            "dish_name": facts.get("dish_name", ""),
            "merchant_name": facts.get("merchant_name", ""),
            "cuisine_type": facts.get("cuisine_type", ""),
            "flavor_profile": facts.get("flavor_profile", ""),
            "price": facts.get("price"),
            "why_matched": getattr(evidence, "why_matched", []),
            "citation": getattr(evidence, "citation", ""),
        }, ensure_ascii=False)
        prompt = f"用户查询：{query}\n\n检索结果：\n{evidence_text}\n\n请对该结果打分（1-5）。"
        raw = call_llm(query=prompt, system_instruction=_JUDGE_PROMPT)
        score = int(raw.strip())
        return max(1, min(5, score))
    except Exception:
        logger.warning("LLM judge scoring failed for query=%s", query, exc_info=True)
        return 0


# ── Ablation ───────────────────────────────────────────────────────

def _run_ablation(case: dict, retriever, catalog_service=None) -> dict:
    query = case["query"]
    agent_plan = _agent_plan_for_case(case)
    results: dict[str, list[str]] = {}

    try:
        full_evidence = _retrieve_case_with_retriever(retriever, case, limit=5)
        results["full_pipeline"] = [f"{e.source_type}:{e.source_id}" for e in full_evidence]
    except Exception as e:
        logger.warning("Full pipeline ablation failed: %s", e)
        results["full_pipeline"] = []

    route_names = _collect_route_names(retriever)
    for route_name in route_names:
        try:
            single_route_retriever = _build_single_route_retriever(route_name, retriever, catalog_service)
            if single_route_retriever is None:
                continue
            evidence = _retrieve_case_with_retriever(single_route_retriever, case, limit=5)
            results[route_name] = [f"{e.source_type}:{e.source_id}" for e in evidence]
        except Exception as e:
            logger.warning("Ablation route %s failed: %s", route_name, e)
            results[route_name] = []

    return {"query": query, "route_results": results}


def _collect_route_names(retriever) -> list[str]:
    from service.rag.recall import (
        BusinessRecallRoute,
        DenseVectorRecallRoute,
        SparseVectorRecallRoute,
        SqlCatalogRecallRoute,
    )
    name_map = {
        DenseVectorRecallRoute: "dense",
        SparseVectorRecallRoute: "sparse",
        SqlCatalogRecallRoute: "sql",
        BusinessRecallRoute: "business",
    }
    names = []
    for route in retriever.recall_routes:
        names.append(name_map.get(type(route), type(route).__name__))
    return names


def _build_single_route_retriever(route_name: str, original_retriever, catalog_service=None):
    from service.rag.recall import (
        BusinessRecallRoute,
        DenseVectorRecallRoute,
        SparseVectorRecallRoute,
        SqlCatalogRecallRoute,
    )
    from service.rag.retriever import AdvancedRagRetriever

    route_cls_map = {
        "dense": DenseVectorRecallRoute,
        "sparse": SparseVectorRecallRoute,
        "sql": SqlCatalogRecallRoute,
        "business": BusinessRecallRoute,
    }
    cls = route_cls_map.get(route_name)
    if cls is None:
        return None
    try:
        route_instance = cls(catalog_service) if cls in {SqlCatalogRecallRoute, BusinessRecallRoute, SparseVectorRecallRoute} else cls()
    except Exception:
        return None
    return AdvancedRagRetriever(
        recall_routes=[route_instance],
        query_planner=original_retriever.query_planner,
        reranker=original_retriever.reranker,
    )


# ── Core evaluation ────────────────────────────────────────────────

def _agent_plan_for_case(case: dict):
    try:
        from service.agent_runtime.state import AgentPlan
    except ImportError:
        AgentPlan = _FallbackAgentPlan
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
            "limit": constraints.get("limit"),
            "sort_by": constraints.get("sort_by"),
            "price_preference": constraints.get("price_preference"),
        },
    )


class _FallbackAgentPlan:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


def _retrieve_case_with_retriever(retriever, case: dict, limit: int) -> list:
    parameters = inspect.signature(retriever.retrieve).parameters
    if "agent_plan" not in parameters:
        return retriever.retrieve(case["query"], limit=limit)
    return retriever.retrieve(
        case["query"],
        agent_plan=_agent_plan_for_case(case),
        memories=[],
        limit=limit,
    )


def load_cases(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def evaluate_cases(
    cases: list[dict],
    retriever,
    *,
    enable_llm_judge: bool = False,
    enable_ablation: bool = False,
    catalog_service=None,
) -> dict:
    latency_tracker = _LatencyTracker()
    cache_hits = 0
    cache_size_before = len(getattr(retriever, "_cache", {}))
    ablation_results: list[dict] = []

    recall_hits = 0
    constraint_passes = 0
    diversity_passes = 0
    citation_scores: list[float] = []

    ndcg_scores: list[float] = []
    mrr_scores: list[float] = []
    precision_scores: list[float] = []
    ap_scores: list[float] = []
    hit_scores: list[float] = []
    recall_k_scores: list[float] = []
    ranking_case_count = 0

    llm_scores: list[float] = []
    llm_correlation_pairs: list[tuple[float, float]] = []
    llm_case_count = 0

    for case in cases:
        # ── latency measurement ──
        cache_key_before = None
        if hasattr(retriever, "_cache_key"):
            plan = _agent_plan_for_case(case)
            try:
                cache_key_before = retriever._cache_key(
                    retriever.query_planner.plan(case["query"], plan, [])
                )
                cache_hit_occurred = retriever._cache_get(cache_key_before) is not None
            except Exception:
                cache_hit_occurred = False
        else:
            cache_hit_occurred = False
        if cache_hit_occurred:
            cache_hits += 1

        t0 = time.monotonic()
        evidence = _retrieve_case_with_retriever(retriever, case, limit=5)
        latency_ms = (time.monotonic() - t0) * 1000
        latency_tracker.record(latency_ms)

        # ── recall / constraint / diversity / citation ──
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

        # ── ranking metrics (require relevance_grades) ──
        relevance_grades = case.get("relevance_grades")
        if relevance_grades:
            ranking_case_count += 1
            retrieved_key_ids = [f"{item.source_type}:{item.source_id}" for item in evidence]
            ndcg_scores.append(_compute_ndcg_at_k(retrieved_key_ids, relevance_grades, k=5))
            mrr_scores.append(_compute_mrr(retrieved_key_ids, relevance_grades))
            precision_scores.append(_compute_precision_at_k(retrieved_key_ids, relevance_grades, k=5))
            ap_scores.append(_compute_average_precision(retrieved_key_ids, relevance_grades))
            hit_scores.append(_compute_hit_rate(retrieved_key_ids, relevance_grades))
            recall_k_scores.append(_compute_recall_at_k(retrieved_key_ids, relevance_grades, k=5))

        # ── LLM judge ──
        if enable_llm_judge and evidence:
            llm_case_count += 1
            human_grades = case.get("relevance_grades") or {}
            for item in evidence:
                key = f"{item.source_type}:{item.source_id}"
                llm_score = _llm_relevance_score(case["query"], item)
                llm_scores.append(float(llm_score))
                human = human_grades.get(key)
                if human is not None and llm_score > 0:
                    llm_correlation_pairs.append((float(llm_score), float(human)))

        # ── ablation ──
        if enable_ablation:
            ablation_results.append(_run_ablation(case, retriever, catalog_service))

    cache_size_after = len(getattr(retriever, "_cache", {}))
    case_count = len(cases)

    result: dict = {
        "case_count": case_count,
        "recall_metrics": {
            "recall_at_5": round(recall_hits / case_count, 4) if case_count else 0.0,
            "constraint_pass_rate": round(constraint_passes / case_count, 4) if case_count else 0.0,
            "diversity_pass_rate": round(diversity_passes / case_count, 4) if case_count else 0.0,
            "citation_coverage": round(sum(citation_scores) / case_count, 4) if case_count else 0.0,
        },
        "latency": latency_tracker.stats(),
        "cache": {
            "hit_rate": round(cache_hits / case_count, 4) if case_count else 0.0,
            "size_before": cache_size_before,
            "size_after": cache_size_after,
        },
    }

    if ranking_case_count > 0:
        result["ranking_metrics"] = {
            "cases_with_grades": ranking_case_count,
            "ndcg_at_5": round(sum(ndcg_scores) / ranking_case_count, 4),
            "mrr": round(sum(mrr_scores) / ranking_case_count, 4),
            "precision_at_5": round(sum(precision_scores) / ranking_case_count, 4),
            "map": round(sum(ap_scores) / ranking_case_count, 4),
            "hit_rate": round(sum(hit_scores) / ranking_case_count, 4),
            "recall_at_5_detail": round(sum(recall_k_scores) / ranking_case_count, 4),
        }

    if enable_llm_judge and llm_case_count > 0:
        llm_mean = sum(llm_scores) / len(llm_scores) if llm_scores else 0.0
        correlation = _pearson_correlation(llm_correlation_pairs) if len(llm_correlation_pairs) >= 3 else None
        result["llm_judge"] = {
            "cases_scored": llm_case_count,
            "scores_collected": len(llm_scores),
            "mean_score": round(llm_mean, 2),
            "human_correlation": round(correlation, 4) if correlation is not None else None,
        }

    if enable_ablation:
        result["ablation"] = _summarize_ablation(ablation_results)

    return result


def _summarize_ablation(ablation_results: list[dict]) -> dict:
    route_keys: set[str] = set()
    for entry in ablation_results:
        route_keys.update(entry["route_results"].keys())
    totals: dict[str, int] = {k: 0 for k in route_keys}
    for entry in ablation_results:
        for route_name, retrieved_ids in entry["route_results"].items():
            if retrieved_ids:
                totals[route_name] += 1
    n = len(ablation_results)
    summary = {}
    for name in sorted(totals.keys()):
        summary[f"{name}_contribution"] = round(totals[name] / n, 4) if n else 0.0
    return summary


def _pearson_correlation(pairs: list[tuple[float, float]]) -> float:
    n = len(pairs)
    if n < 2:
        return 0.0
    xs = [p[0] for p in pairs]
    ys = [p[1] for p in pairs]
    mean_x = statistics.mean(xs)
    mean_y = statistics.mean(ys)
    num = sum((x - mean_x) * (y - mean_y) for x, y in pairs)
    denom_x = math.sqrt(sum((x - mean_x) ** 2 for x in xs))
    denom_y = math.sqrt(sum((y - mean_y) ** 2 for y in ys))
    if denom_x == 0 or denom_y == 0:
        return 0.0
    return num / (denom_x * denom_y)


# ── CLI ────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate RAG retrieval quality")
    parser.add_argument("--cases", type=str, default="tests/eval/assistant_rag_cases.jsonl",
                        help="Path to JSONL eval cases file")
    parser.add_argument("--llm-judge", action="store_true",
                        help="Enable LLM-as-judge relevance scoring")
    parser.add_argument("--ablation", action="store_true",
                        help="Enable per-route ablation analysis")
    parser.add_argument("--output", type=str, default=None,
                        help="Write JSON report to file instead of stdout")
    parser.add_argument("--limit", type=int, default=None,
                        help="Limit number of eval cases to process")
    args = parser.parse_args()

    cases_path = Path(args.cases)
    if not cases_path.exists():
        print(f"Error: cases file not found: {cases_path}")
        return 1

    cases = load_cases(cases_path)
    if args.limit:
        cases = cases[: args.limit]

    from api.db import SessionLocal
    from service.rag.retriever import AdvancedRagRetriever

    session = SessionLocal()
    try:
        retriever = AdvancedRagRetriever(session=session)
        metrics = evaluate_cases(
            cases,
            retriever,
            enable_llm_judge=args.llm_judge,
            enable_ablation=args.ablation,
        )
    finally:
        session.close()

    output = json.dumps(metrics, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
        print(f"Report written to {args.output}")
    else:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
