from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, NotRequired, TypedDict

from langchain_core.messages import BaseMessage


AgentIntent = Literal[
    "greeting",
    "recommendation",
    "knowledge",
    "cart_action",
    "address_action",
    "preference_action",
    "undo_action",
    "unsupported",
]


@dataclass
class GraphToolCall:
    tool_name: str
    arguments: dict[str, Any] = field(default_factory=dict)
    writes_database: bool = False


@dataclass
class AgentPlan:
    intent: AgentIntent
    normalized_query: str = ""
    requires_rag: bool = False
    filters: dict[str, Any] = field(default_factory=lambda: {
        "cuisine_types": [],
        "flavor_preferences": [],
        "budget_max": None,
        "party_size": None,
        "exclude_allergens": [],
    })
    tool_calls: list[GraphToolCall] = field(default_factory=list)
    should_answer_directly: bool = True
    response_hint: str = ""


class SmartOrderAgentState(TypedDict):
    messages: list[BaseMessage]
    session_id: str
    user_id: NotRequired[int | None]
    active_topic: NotRequired[str | None]
    loaded_user_memories: NotRequired[list[dict[str, Any]]]
    memory_candidates: NotRequired[list[dict[str, Any]]]
    saved_memories: NotRequired[list[dict[str, Any]]]
    recent_evidence: NotRequired[list[dict[str, Any]]]
    recent_action_ids: NotRequired[list[str]]
    current_plan: NotRequired[AgentPlan | None]
    tool_results: NotRequired[list[dict[str, Any]]]
    response_payload: NotRequired[dict[str, Any]]
