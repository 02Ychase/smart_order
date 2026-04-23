from dataclasses import dataclass, field
from typing import Literal


@dataclass
class AssistantParsedQuery:
    raw_message: str
    query_type: Literal["recommendation", "comparison", "knowledge"]
    cuisine_types: list[str] = field(default_factory=list)
    budget_max: float | None = None
    party_size: int | None = None
    exclude_allergens: list[str] = field(default_factory=list)
    comparison_targets: list[str] = field(default_factory=list)
    needs_clarification: bool = False
    clarification_question: str | None = None


@dataclass
class AssistantCandidate:
    source_type: Literal["dish", "merchant"]
    source_id: int
    merchant_id: int
    merchant_name: str
    dish_id: int | None
    dish_name: str | None
    price: float | None
    score: float
    summary: str
    reason_facts: list[str] = field(default_factory=list)
    citation_title: str = ""
    citation_snippet: str = ""


@dataclass
class AssistantConversationState:
    session_id: str
    last_user_message: str = ""
    parsed_query: AssistantParsedQuery | None = None
    candidate_ids: list[int] = field(default_factory=list)
