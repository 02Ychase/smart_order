from dataclasses import dataclass, field
from typing import Literal

from service.assistant_constraint_parser import parse_assistant_query
from service.assistant_models import AssistantParsedQuery


@dataclass
class ResolvedConstraints:
    raw_message: str
    query_type: Literal["recommendation", "comparison", "knowledge"]
    cuisine_types: list[str] = field(default_factory=list)
    budget_max: float | None = None
    party_size: int | None = None
    exclude_allergens: list[str] = field(default_factory=list)
    comparison_targets: list[str] = field(default_factory=list)
    needs_clarification: bool = False
    clarification_question: str | None = None

    @classmethod
    def from_parsed(cls, parsed: AssistantParsedQuery) -> "ResolvedConstraints":
        return cls(
            raw_message=parsed.raw_message,
            query_type=parsed.query_type,
            cuisine_types=parsed.cuisine_types,
            budget_max=parsed.budget_max,
            party_size=parsed.party_size,
            exclude_allergens=parsed.exclude_allergens,
            comparison_targets=parsed.comparison_targets,
            needs_clarification=parsed.needs_clarification,
            clarification_question=parsed.clarification_question,
        )

    def is_sufficient_for_recommendation(self) -> bool:
        return self.budget_max is not None and self.party_size is not None

    def is_sufficient_for_comparison(self) -> bool:
        return len(self.comparison_targets) >= 2 or self.query_type == "comparison"


class ConstraintResolver:
    def resolve(self, message: str) -> ResolvedConstraints:
        parsed = parse_assistant_query(message)
        return ResolvedConstraints.from_parsed(parsed)
