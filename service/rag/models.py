from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


SourceType = Literal["dish", "merchant", "memory"]


@dataclass
class RagQueryPlan:
    original_query: str
    normalized_query: str
    expansion_queries: list[str] = field(default_factory=list)
    must_filters: dict[str, Any] = field(default_factory=dict)
    should_filters: dict[str, Any] = field(default_factory=dict)
    source_types: list[SourceType] = field(default_factory=lambda: ["dish", "merchant"])
    answer_mode: str = "recommendation"
    preferred_dishes: list[str] = field(default_factory=list)
    preferred_merchants: list[str] = field(default_factory=list)


@dataclass
class RecallCandidate:
    stable_key: str
    source_type: SourceType
    source_id: int
    route: str
    rank: int
    score: float
    facts: dict[str, Any] = field(default_factory=dict)
    citation: str = ""


@dataclass
class FusedCandidate:
    stable_key: str
    source_type: SourceType
    source_id: int
    facts: dict[str, Any] = field(default_factory=dict)
    citation: str = ""
    route_scores: dict[str, float] = field(default_factory=dict)
    route_ranks: dict[str, int] = field(default_factory=dict)
    dense_score: float = 0.0
    lexical_score: float = 0.0
    constraint_match: float = 1.0
    final_score: float = 0.0


@dataclass
class RagEvidence:
    source_type: SourceType
    source_id: int
    merchant_id: int
    title: str
    facts: dict[str, Any]
    why_matched: list[str] = field(default_factory=list)
    citation: str = ""
    score: float = 0.0
