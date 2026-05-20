"""Offline RAG pipeline evaluation: per-stage IR metrics + ablation experiments.

Usage:
    python tools/evaluate_rag_pipeline.py --benchmark tests/eval/rag_benchmark.jsonl
    python tools/evaluate_rag_pipeline.py --benchmark tests/eval/rag_benchmark.jsonl --ablation
"""
from __future__ import annotations

import argparse
import json
import logging
import statistics
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from service.rag.eval_metrics import compute_all
from service.rag.tracing import PipelineTrace, RagEvalOptions

logger = logging.getLogger(__name__)


@dataclass
class BenchmarkCase:
    id: str
    query: str
    normalized_query: str
    intent: str
    filters: dict
    relevant_keys: set[str]
    highly_relevant_keys: set[str]


@dataclass
class StageResult:
    metrics_per_case: list[dict[str, float]] = field(default_factory=list)
    latencies_ms: list[float] = field(default_factory=list)

    def mean_metrics(self) -> dict[str, float]:
        if not self.metrics_per_case:
            return {}
        keys = self.metrics_per_case[0].keys()
        return {k: statistics.mean(m[k] for m in self.metrics_per_case) for k in keys}

    def mean_latency_ms(self) -> float:
        return statistics.mean(self.latencies_ms) if self.latencies_ms else 0.0

    def p95_latency_ms(self) -> float:
        if not self.latencies_ms:
            return 0.0
        sorted_l = sorted(self.latencies_ms)
        idx = int(len(sorted_l) * 0.95)
        return sorted_l[min(idx, len(sorted_l) - 1)]


def load_benchmark(path: Path) -> list[BenchmarkCase]:
    cases: list[BenchmarkCase] = []
    with open(path, encoding="utf-8") as f:
        for i, line in enumerate(f):
            line = line.strip()
            if not line:
                continue
            raw = json.loads(line)
            cases.append(BenchmarkCase(
                id=raw.get("id", f"case_{i}"),
                query=raw["query"],
                normalized_query=raw.get("normalized_query", raw["query"]),
                intent=raw.get("intent", "recommendation"),
                filters=raw.get("filters", {}),
                relevant_keys=set(raw.get("relevant_keys", [])),
                highly_relevant_keys=set(raw.get("highly_relevant_keys", [])),
            ))
    return cases


def evaluate_single(
    retriever,
    case: BenchmarkCase,
    eval_options: RagEvalOptions,
    k_values: tuple[int, ...] = (5, 10, 20),
) -> tuple[PipelineTrace, dict[str, dict[str, float]]]:
    from service.agent_runtime.state import AgentPlan

    agent_plan = AgentPlan(
        intent=case.intent,
        normalized_query=case.normalized_query,
        requires_rag=True,
        filters=case.filters,
    )
    trace = PipelineTrace()
    retriever.retrieve(
        case.query,
        agent_plan,
        memories=[],
        limit=max(k_values),
        trace=trace,
        eval_options=eval_options,
    )

    relevant = case.relevant_keys
    highly = case.highly_relevant_keys

    stage_metrics: dict[str, dict[str, float]] = {}
    stages = [
        ("after_fusion", trace.after_fusion),
        ("after_hard_filter", trace.after_hard_filter),
        ("after_cross_encoder", trace.after_cross_encoder),
        ("after_weighted_rerank", trace.after_weighted_rerank),
        ("after_diversify", trace.after_diversify),
    ]
    for stage_name, items in stages:
        if not items:
            continue
        keys = [item.key for item in items]
        merged: dict[str, float] = {}
        for k in k_values:
            merged.update(compute_all(keys, relevant, highly, k=k))
        stage_metrics[stage_name] = merged

    for route_name, items in trace.recall_per_route.items():
        keys = [item.key for item in items]
        merged = {}
        for k in k_values:
            merged.update(compute_all(keys, relevant, highly, k=k))
        stage_metrics[f"recall:{route_name}"] = merged

    return trace, stage_metrics


@dataclass
class EvalSummary:
    stage_results: dict[str, StageResult]
    total_latencies_ms: list[float]

    def mean_total_latency_ms(self) -> float:
        return statistics.mean(self.total_latencies_ms) if self.total_latencies_ms else 0.0


def run_evaluation(
    retriever,
    cases: list[BenchmarkCase],
    eval_options: RagEvalOptions,
    k_values: tuple[int, ...] = (5, 10, 20),
) -> EvalSummary:
    results: dict[str, StageResult] = {}
    total_latencies: list[float] = []

    for case in cases:
        trace, stage_metrics = evaluate_single(retriever, case, eval_options, k_values)
        total_latencies.append(trace.total_latency_ms)

        latency_map = {
            "parallel_recall_total": trace.parallel_recall_total_ms,
            "after_fusion": trace.fusion_latency_ms,
            "after_hard_filter": trace.filter_latency_ms,
            "after_cross_encoder": trace.cross_encoder_latency_ms,
            "after_weighted_rerank": trace.weighted_rerank_latency_ms,
            "after_diversify": trace.diversify_latency_ms,
        }
        for route_name, latency in trace.recall_per_route_latency_ms.items():
            latency_map[f"recall:{route_name}"] = latency

        for stage_name, metrics in stage_metrics.items():
            if stage_name not in results:
                results[stage_name] = StageResult()
            results[stage_name].metrics_per_case.append(metrics)
            lat = latency_map.get(stage_name, 0.0)
            results[stage_name].latencies_ms.append(lat)

    return EvalSummary(stage_results=results, total_latencies_ms=total_latencies)


def print_report(summary: EvalSummary, label: str = "Full Pipeline") -> None:
    results = summary.stage_results
    print(f"\n{'=' * 80}")
    print(f"  {label}")
    print(f"{'=' * 80}")

    header = f"{'Stage':<30} {'Recall@5':>9} {'Prec@5':>9} {'MRR':>9} {'NDCG@5':>9} {'Lat(ms)':>9} {'P95(ms)':>9}"
    print(header)
    print("-" * len(header))

    stage_order = sorted(results.keys(), key=lambda s: (
        0 if s.startswith("recall:") else
        1 if s == "after_fusion" else
        2 if s == "after_hard_filter" else
        3 if s == "after_cross_encoder" else
        4 if s == "after_weighted_rerank" else
        5
    ))

    for stage in stage_order:
        sr = results[stage]
        m = sr.mean_metrics()
        print(
            f"{stage:<30} "
            f"{m.get('recall@5', 0):>9.3f} "
            f"{m.get('precision@5', 0):>9.3f} "
            f"{m.get('mrr', 0):>9.3f} "
            f"{m.get('ndcg@5', 0):>9.3f} "
            f"{sr.mean_latency_ms():>9.1f} "
            f"{sr.p95_latency_ms():>9.1f}"
        )

    print(f"{'total_pipeline':<30} {'':>9} {'':>9} {'':>9} {'':>9} {summary.mean_total_latency_ms():>9.1f}")


def run_ablation(retriever, cases: list[BenchmarkCase], k_values: tuple[int, ...] = (5, 10, 20)) -> None:
    configs = {
        "full": RagEvalOptions(top_k_values=k_values),
        "no_cross_encoder": RagEvalOptions(skip_cross_encoder=True, top_k_values=k_values),
        "no_weighted_rerank": RagEvalOptions(skip_weighted_rerank=True, top_k_values=k_values),
    }

    ablation_summary: dict[str, dict[str, float]] = {}

    for config_name, opts in configs.items():
        print(f"\nRunning config: {config_name} ...")
        t0 = time.perf_counter()
        summary = run_evaluation(retriever, cases, opts, k_values)
        elapsed = (time.perf_counter() - t0) * 1000
        print(f"  completed in {elapsed:.0f}ms")

        print_report(summary, label=config_name)

        final = summary.stage_results.get("after_diversify") or summary.stage_results.get("after_weighted_rerank")
        if final:
            m = final.mean_metrics()
            ablation_summary[config_name] = {
                "ndcg@5": m.get("ndcg@5", 0),
                "mrr": m.get("mrr", 0),
                "mean_total_latency_ms": summary.mean_total_latency_ms(),
            }

    if ablation_summary:
        print(f"\n{'=' * 80}")
        print("  Ablation Summary")
        print(f"{'=' * 80}")
        baseline = ablation_summary.get("full", {})
        for name, m in ablation_summary.items():
            delta_ndcg = m["ndcg@5"] - baseline.get("ndcg@5", 0)
            delta_mrr = m["mrr"] - baseline.get("mrr", 0)
            delta_str = "" if name == "full" else f"  (ΔNDCG={delta_ndcg:+.3f}, ΔMRR={delta_mrr:+.3f})"
            print(
                f"  {name:<25} NDCG@5={m['ndcg@5']:.3f}  MRR={m['mrr']:.3f}  "
                f"Total={m['mean_total_latency_ms']:.0f}ms{delta_str}"
            )


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate RAG pipeline per-stage")
    parser.add_argument("--benchmark", type=Path, required=True, help="Path to benchmark .jsonl")
    parser.add_argument("--ablation", action="store_true", help="Run ablation experiments")
    parser.add_argument("--db-url", type=str, default=None, help="SQLAlchemy DB URL (uses env if not set)")
    parser.add_argument("-k", type=int, nargs="+", default=[5, 10, 20], help="K values for metrics")
    parser.add_argument("-v", action="store_true", help="Verbose logging")
    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.v else logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    cases = load_benchmark(args.benchmark)
    print(f"Loaded {len(cases)} benchmark cases from {args.benchmark}")

    import os
    if args.db_url:
        os.environ["DATABASE_URL"] = args.db_url

    from api.db import SessionLocal
    from service.rag.retriever import AdvancedRagRetriever

    session = SessionLocal()
    try:
        retriever = AdvancedRagRetriever(session=session, session_factory=SessionLocal)
        route_names = [type(r).__name__ for r in retriever.recall_routes]
        print(f"Active recall routes: {route_names}")

        k_values = tuple(args.k)

        if args.ablation:
            run_ablation(retriever, cases, k_values)
        else:
            opts = RagEvalOptions(top_k_values=k_values)
            summary = run_evaluation(retriever, cases, opts, k_values)
            print_report(summary)
    finally:
        session.close()


if __name__ == "__main__":
    main()
