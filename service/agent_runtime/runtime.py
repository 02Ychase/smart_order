from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class AgentRuntimeContext:
    """Per-request runtime dependencies injected via config["configurable"]["runtime"].

    Keeps SmartOrderAgentState as pure business data, free of infrastructure concerns.
    """

    retriever: Any = None
    action_executor: Any = None
    memory_service: Any = None
    planner: Any = None
    use_llm_response: bool = True


def get_runtime(config: dict | None) -> AgentRuntimeContext | None:
    """Safely extract runtime context from LangGraph config."""
    if config is None:
        return None
    configurable = config.get("configurable") or {}
    return configurable.get("runtime")
