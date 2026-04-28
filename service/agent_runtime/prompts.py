from __future__ import annotations

from pathlib import Path


class PromptRegistry:
    def __init__(self, project_root: Path | None = None) -> None:
        self.project_root = project_root or Path(__file__).resolve().parents[2]
        self._mapping = {
            "agent.planner": "prompt/agent/planner.system.md",
            "agent.query_rewrite": "prompt/agent/query_rewrite.system.md",
            "agent.answer_grounded": "prompt/agent/answer_grounded.system.md",
            "agent.memory_writer": "prompt/agent/memory_writer.system.md",
            "agent.undo_resolver": "prompt/agent/undo_resolver.system.md",
            "tools.cart_action": "prompt/tools/cart_action.system.md",
            "tools.address_action": "prompt/tools/address_action.system.md",
            "tools.preference_action": "prompt/tools/preference_action.system.md",
            "tools.recommendation": "prompt/tools/recommendation.system.md",
            "tools.catalog_qa": "prompt/tools/catalog_qa.system.md",
        }

    def load(self, key: str) -> str:
        relative_path = self._mapping.get(key)
        if relative_path is None:
            raise KeyError(f"unknown prompt key: {key}")
        prompt_path = self.project_root / relative_path
        return prompt_path.read_text(encoding="utf-8").strip()
