from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from secrets import token_hex
from typing import Any, Literal


IntentType = Literal[
    "greeting",
    "knowledge",
    "recommendation",
    "cart_action",
    "address_action",
    "mixed_task",
    "unsupported",
]

ResponseType = Literal[
    "greeting",
    "knowledge",
    "recommendation",
    "clarification",
    "confirmation_required",
    "action_completed",
    "unsupported",
]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _pending_action_id() -> str:
    return f"pa_{token_hex(6)}"


@dataclass
class ToolCall:
    tool_name: str
    arguments: dict[str, Any] = field(default_factory=dict)
    requires_confirmation: bool = False


@dataclass
class AgentDecision:
    intent: IntentType
    reasoning_summary: str = ""
    tool_plan: list[ToolCall] = field(default_factory=list)
    missing_slots: list[str] = field(default_factory=list)
    clarification_question: str | None = None
    needs_confirmation: bool = False


@dataclass
class EvidencePack:
    source_type: str
    source_id: str | int
    merchant_id: str | int
    title: str
    facts: dict[str, Any]
    why_matched: list[str] = field(default_factory=list)
    citation: str = ""
    score: float = 0.0


@dataclass
class ToolError:
    code: str
    message: str
    candidates: list[Any] = field(default_factory=list)


@dataclass
class ToolResult:
    ok: bool
    tool_name: str
    data: dict[str, Any] = field(default_factory=dict)
    evidence: list[EvidencePack] = field(default_factory=list)
    requires_confirmation: bool = False
    error: ToolError | None = None

    @classmethod
    def ok_result(
        cls,
        tool_name: str,
        data: dict[str, Any] | None = None,
        evidence: list[EvidencePack] | None = None,
        requires_confirmation: bool = False,
    ) -> "ToolResult":
        return cls(
            ok=True,
            tool_name=tool_name,
            data=data or {},
            evidence=evidence or [],
            requires_confirmation=requires_confirmation,
            error=None,
        )

    @classmethod
    def error_result(
        cls,
        tool_name: str,
        error: ToolError,
        data: dict[str, Any] | None = None,
        evidence: list[EvidencePack] | None = None,
        requires_confirmation: bool = False,
    ) -> "ToolResult":
        return cls(
            ok=False,
            tool_name=tool_name,
            data=data or {},
            evidence=evidence or [],
            requires_confirmation=requires_confirmation,
            error=error,
        )


@dataclass
class PendingAction:
    action_type: str
    summary: str
    payload: dict[str, Any]
    requires_user_id: bool
    action_id: str = field(default_factory=_pending_action_id)
    created_at: datetime = field(default_factory=_utc_now)
    expires_at: datetime = field(
        default_factory=lambda: _utc_now() + timedelta(minutes=10)
    )

    def is_expired(self, now: datetime | None = None) -> bool:
        checked_at = now or _utc_now()
        if checked_at.tzinfo is None:
            checked_at = checked_at.replace(tzinfo=timezone.utc)
        return checked_at >= self.expires_at


@dataclass
class AssistantTurnState:
    session_id: str
    user_id: str | int | None = None
    last_intent: IntentType | None = None
    slots: dict[str, Any] = field(default_factory=dict)
    last_evidence_ids: list[str | int] = field(default_factory=list)
    pending_action: PendingAction | None = None
