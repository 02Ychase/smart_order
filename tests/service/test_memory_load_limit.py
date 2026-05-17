"""Tests for Issue #5: memory loading limit & type consistency.

Covers:
- Repository list_for_user respects limit parameter
- Service list_memories reads limit from config
- Ordering: most recently updated memories come first (not truncated)
- Config default: max_memories_per_user = 100
- ALWAYS_LOAD_TYPES constant is defined
- Memory type names match between prompts and code consumers
"""

from service.config import AppConfig, set_config
from service.user_memory_service import ALWAYS_LOAD_TYPES, UserMemoryService


# ── Fake repository that honours limit ──────────────────────────────


class FakeMemoryRepo:
    """In-memory repo that mimics the real repository's limit + ordering."""

    def __init__(self, records: list[dict] | None = None):
        self.records = list(records or [])
        self.last_limit = None

    def list_for_user(self, user_id, limit=100):
        self.last_limit = limit
        results = [
            r for r in self.records
            if r.get("user_id") == user_id and r.get("status", "active") == "active"
        ]
        return results[:limit]

    def list_for_user_by_types(self, user_id, memory_types):
        self.last_always_types = memory_types
        return [
            r for r in self.records
            if (
                r.get("user_id") == user_id
                and r.get("status", "active") == "active"
                and r.get("memory_type") in memory_types
            )
        ]

    def list_for_user_excluding_types(self, user_id, memory_types, limit=100):
        self.last_excluded_types = memory_types
        self.last_limit = limit
        results = [
            r for r in self.records
            if (
                r.get("user_id") == user_id
                and r.get("status", "active") == "active"
                and r.get("memory_type") not in memory_types
            )
        ]
        return results[:limit]

    def upsert(self, user_id, memory_type, content, confidence):
        record = {
            "id": len(self.records) + 1,
            "user_id": user_id,
            "memory_type": memory_type,
            "content": content,
            "confidence": confidence,
            "status": "active",
        }
        self.records.append(record)
        return record


# ── Repository limit tests ──────────────────────────────────────────


def test_repo_limit_truncates_results() -> None:
    records = [
        {"id": i, "user_id": 1, "memory_type": "food_preference",
         "content": f"pref_{i}", "confidence": 0.9, "status": "active"}
        for i in range(1, 11)
    ]
    repo = FakeMemoryRepo(records)
    result = repo.list_for_user(1, limit=5)
    assert len(result) == 5


def test_repo_limit_returns_all_when_under_limit() -> None:
    records = [
        {"id": i, "user_id": 1, "memory_type": "food_preference",
         "content": f"pref_{i}", "confidence": 0.9, "status": "active"}
        for i in range(1, 4)
    ]
    repo = FakeMemoryRepo(records)
    result = repo.list_for_user(1, limit=100)
    assert len(result) == 3


# ── Service reads limit from config ─────────────────────────────────


def test_service_passes_config_limit_to_repo() -> None:
    cfg = AppConfig()
    cfg.memory.max_memories_per_user = 42
    set_config(cfg)

    repo = FakeMemoryRepo([
        {"id": i, "user_id": 1, "memory_type": "food_preference",
         "content": f"pref_{i}", "confidence": 0.9, "status": "active"}
        for i in range(1, 60)
    ])
    service = UserMemoryService(repository=repo)
    result = service.list_memories(1)

    assert repo.last_limit == 42
    assert len(result) == 42

    # Restore default
    set_config(AppConfig())


def test_service_default_config_limit_is_100() -> None:
    set_config(AppConfig())
    cfg = AppConfig()
    assert cfg.memory.max_memories_per_user == 100


# ── Ordering: most recent first survives truncation ──────────────────


def test_service_ordering_preserves_most_recent() -> None:
    """With limit applied, the first returned items should be the most recent."""
    cfg = AppConfig()
    cfg.memory.max_memories_per_user = 3
    set_config(cfg)

    # Records ordered newest first (simulating repository's ORDER BY updated_at DESC)
    records = [
        {"id": 5, "user_id": 1, "memory_type": "food_preference",
         "content": "newest", "confidence": 0.9, "status": "active"},
        {"id": 4, "user_id": 1, "memory_type": "dietary_constraint",
         "content": "花生过敏", "confidence": 1.0, "status": "active"},
        {"id": 3, "user_id": 1, "memory_type": "food_preference",
         "content": "middle", "confidence": 0.8, "status": "active"},
        {"id": 2, "user_id": 1, "memory_type": "food_preference",
         "content": "old", "confidence": 0.7, "status": "active"},
        {"id": 1, "user_id": 1, "memory_type": "food_preference",
         "content": "oldest", "confidence": 0.6, "status": "active"},
    ]
    repo = FakeMemoryRepo(records)
    service = UserMemoryService(repository=repo)
    result = service.list_memories(1)

    assert len(result) == 3
    assert result[0]["content"] == "花生过敏"
    assert result[1]["content"] == "newest"
    assert result[2]["content"] == "middle"

    # Restore default
    set_config(AppConfig())


# ── ALWAYS_LOAD_TYPES constant ──────────────────────────────────────


def test_service_always_loads_dietary_constraints_beyond_limit() -> None:
    cfg = AppConfig()
    cfg.memory.max_memories_per_user = 3
    set_config(cfg)

    records = [
        {"id": i, "user_id": 1, "memory_type": "food_preference",
         "content": f"pref_{i}", "confidence": 0.9, "status": "active"}
        for i in range(1, 8)
    ]
    records.append({
        "id": 99,
        "user_id": 1,
        "memory_type": "dietary_constraint",
        "content": "花生过敏",
        "confidence": 1.0,
        "status": "active",
    })
    repo = FakeMemoryRepo(records)
    service = UserMemoryService(repository=repo)

    result = service.list_memories(1)

    assert any(item["memory_type"] == "dietary_constraint" for item in result)
    assert repo.last_excluded_types == ALWAYS_LOAD_TYPES
    assert repo.last_limit == 2
    assert len(result) == 3

    # Restore default
    set_config(AppConfig())


def test_always_load_types_includes_dietary_constraint() -> None:
    assert "dietary_constraint" in ALWAYS_LOAD_TYPES


def test_always_load_types_is_frozenset() -> None:
    assert isinstance(ALWAYS_LOAD_TYPES, frozenset)


# ── Memory type consistency ─────────────────────────────────────────


def test_query_planner_consumes_merchant_preference_type() -> None:
    """Verify _apply_memory_hints recognizes 'merchant_preference' (not 'merchant_affinity')."""
    from service.rag.query_planner import _apply_memory_hints

    cuisine_types: list[str] = []
    flavor_prefs: list[str] = []
    allergens: list[str] = []
    preferred_dishes: list[str] = []
    preferred_merchants: list[str] = []

    memories = [
        {"memory_type": "merchant_preference", "content": "用户经常去兰姨小炒"},
    ]
    _apply_memory_hints(memories, cuisine_types, flavor_prefs, allergens,
                        preferred_dishes, preferred_merchants)

    assert "兰姨小炒" in preferred_merchants


def test_query_planner_accepts_legacy_merchant_affinity_type() -> None:
    """Old 'merchant_affinity' rows remain compatible with code consumers."""
    from service.rag.query_planner import _apply_memory_hints

    cuisine_types: list[str] = []
    flavor_prefs: list[str] = []
    allergens: list[str] = []
    preferred_dishes: list[str] = []
    preferred_merchants: list[str] = []

    memories = [
        {"memory_type": "merchant_affinity", "content": "用户经常去兰姨小炒"},
    ]
    _apply_memory_hints(memories, cuisine_types, flavor_prefs, allergens,
                        preferred_dishes, preferred_merchants)

    assert "兰姨小炒" in preferred_merchants


def test_prompt_memory_types_match_code_consumers() -> None:
    """memory_writer prompt should only list types that code actually consumes."""
    import pathlib

    prompt_path = pathlib.Path(__file__).resolve().parents[2] / "prompt" / "agent" / "memory_writer.system.md"
    prompt_text = prompt_path.read_text(encoding="utf-8")

    # Types consumed by _apply_memory_hints in query_planner.py
    consumed_types = {"food_preference", "dietary_constraint", "merchant_preference", "dish_preference"}

    for mt in consumed_types:
        assert mt in prompt_text, f"memory_writer prompt should list consumed type '{mt}'"

    # Retired types should NOT appear
    assert "merchant_affinity" not in prompt_text, "merchant_affinity should be replaced by merchant_preference"
    assert "response_style" not in prompt_text, "response_style has no consumer and should be removed"
