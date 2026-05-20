from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class TraceItem:
    key: str
    score: float | None = None


@dataclass
class RagEvalOptions:
    disable_cache: bool = True
    skip_cross_encoder: bool = False
    skip_weighted_rerank: bool = False
    top_k_values: tuple[int, ...] = (5, 10, 20)


@dataclass
class PipelineTrace:
    cache_hit: bool = False
    recall_per_route: dict[str, list[TraceItem]] = field(default_factory=dict)
    parallel_recall_total_ms: float = 0.0
    recall_per_route_latency_ms: dict[str, float] = field(default_factory=dict)
    after_fusion: list[TraceItem] = field(default_factory=list)
    fusion_latency_ms: float = 0.0
    after_hard_filter: list[TraceItem] = field(default_factory=list)
    filter_latency_ms: float = 0.0
    after_cross_encoder: list[TraceItem] = field(default_factory=list)
    cross_encoder_latency_ms: float = 0.0
    after_weighted_rerank: list[TraceItem] = field(default_factory=list)
    weighted_rerank_latency_ms: float = 0.0
    after_diversify: list[TraceItem] = field(default_factory=list)
    diversify_latency_ms: float = 0.0
    total_latency_ms: float = 0.0

    def keys_at(self, stage: str) -> list[str]:
        items: list[TraceItem] = getattr(self, stage, [])
        return [item.key for item in items]
