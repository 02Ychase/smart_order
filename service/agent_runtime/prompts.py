from __future__ import annotations

from pathlib import Path


class PromptRegistry:
    _cache: dict[str, str] = {}

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
        """Load prompt with in-memory caching to avoid repeated disk reads."""
        if key in self._cache:
            return self._cache[key]

        relative_path = self._mapping.get(key)
        if relative_path is None:
            raise KeyError(f"unknown prompt key: {key}")

        prompt_path = self.project_root / relative_path
        content = prompt_path.read_text(encoding="utf-8").strip()
        self._cache[key] = content
        return content

    @classmethod
    def clear_cache(cls) -> None:
        """Clear the shared prompt cache."""
        cls._cache.clear()

    @classmethod
    def cache_info(cls) -> dict:
        """Get cache statistics (size and cached keys)."""
        return {"size": len(cls._cache), "keys": list(cls._cache.keys())}
