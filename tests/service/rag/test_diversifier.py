from service.rag.diversifier import diversify
from service.rag.models import FusedCandidate


# ── Helpers ──────────────────────────────────────────────────────────

def _make_candidate(key: str, merchant_id: int, dish_name: str, score: float = 0.9) -> FusedCandidate:
    return FusedCandidate(
        stable_key=key,
        source_type="dish",
        source_id=int(key.split(":")[-1]),
        facts={"merchant_id": merchant_id, "dish_name": dish_name},
        final_score=score,
    )


# ── Existing test updated for new default (max_per_merchant=2) ────────

def test_diversifier_default_allows_two_per_merchant() -> None:
    """With default max_per_merchant=2, merchant 1 contributes both dishes."""
    candidates = [
        _make_candidate("dish:1", merchant_id=1, dish_name="A", score=0.9),
        _make_candidate("dish:2", merchant_id=1, dish_name="B", score=0.8),
        _make_candidate("dish:3", merchant_id=2, dish_name="C", score=0.7),
    ]

    result = diversify(candidates, limit=2, merchant_scoped=False)

    # Both from merchant 1 (higher scores) since limit is now 2 per merchant.
    assert [item.stable_key for item in result] == ["dish:1", "dish:2"]


def test_diversifier_default_constrains_third_from_same_merchant() -> None:
    """With max_per_merchant=2, the 3rd dish from same merchant is pushed out."""
    candidates = [
        _make_candidate("dish:1", merchant_id=1, dish_name="A", score=0.9),
        _make_candidate("dish:2", merchant_id=1, dish_name="B", score=0.8),
        _make_candidate("dish:3", merchant_id=1, dish_name="C", score=0.7),
        _make_candidate("dish:4", merchant_id=2, dish_name="D", score=0.6),
    ]

    result = diversify(candidates, limit=3, merchant_scoped=False)

    # dish:1, dish:2 from merchant 1, then dish:3 excluded (max 2), dish:4 from merchant 2.
    assert [item.stable_key for item in result] == ["dish:1", "dish:2", "dish:4"]


def test_diversifier_merchant_scoped_allows_three_per_merchant() -> None:
    """Merchant-scoped queries allow up to 3 dishes from the same merchant."""
    candidates = [
        _make_candidate("dish:1", merchant_id=1, dish_name="A", score=0.9),
        _make_candidate("dish:2", merchant_id=1, dish_name="B", score=0.8),
        _make_candidate("dish:3", merchant_id=1, dish_name="C", score=0.7),
        _make_candidate("dish:4", merchant_id=2, dish_name="D", score=0.6),
    ]

    result = diversify(candidates, limit=4, merchant_scoped=True)

    # All 3 from merchant 1 + dish:4 from merchant 2.
    assert [item.stable_key for item in result] == [
        "dish:1", "dish:2", "dish:3", "dish:4",
    ]


def test_diversifier_merchant_scoped_constrains_fourth_from_same_merchant() -> None:
    """Merchant-scoped queries still block the 4th dish from the same merchant."""
    candidates = [
        _make_candidate("dish:1", merchant_id=1, dish_name="A", score=0.9),
        _make_candidate("dish:2", merchant_id=1, dish_name="B", score=0.8),
        _make_candidate("dish:3", merchant_id=1, dish_name="C", score=0.7),
        _make_candidate("dish:4", merchant_id=1, dish_name="D", score=0.6),
        _make_candidate("dish:5", merchant_id=2, dish_name="E", score=0.5),
    ]

    result = diversify(candidates, limit=4, merchant_scoped=True)

    # dish:1-3 from merchant 1, dish:4 excluded (max 3 per merchant), dish:5 from merchant 2.
    assert [item.stable_key for item in result] == [
        "dish:1", "dish:2", "dish:3", "dish:5",
    ]


def test_diversifier_custom_max_per_merchant() -> None:
    """Custom max_per_merchant overrides the default."""
    candidates = [
        _make_candidate("dish:1", merchant_id=1, dish_name="A", score=0.9),
        _make_candidate("dish:2", merchant_id=1, dish_name="B", score=0.8),
        _make_candidate("dish:3", merchant_id=1, dish_name="C", score=0.7),
        _make_candidate("dish:4", merchant_id=1, dish_name="D", score=0.6),
        _make_candidate("dish:5", merchant_id=2, dish_name="E", score=0.5),
    ]

    result = diversify(candidates, limit=4, merchant_scoped=False, max_per_merchant=4)

    # All 4 from merchant 1 — custom limit of 4 overrides default 2.
    assert [item.stable_key for item in result] == [
        "dish:1", "dish:2", "dish:3", "dish:4",
    ]


def test_diversifier_merchant_scoped_respects_custom_max_when_larger() -> None:
    """merchant_scoped=True with a custom max_per_merchant > 3 keeps the custom value."""
    candidates = [
        _make_candidate("dish:1", merchant_id=1, dish_name="A", score=0.9),
        _make_candidate("dish:2", merchant_id=1, dish_name="B", score=0.8),
        _make_candidate("dish:3", merchant_id=1, dish_name="C", score=0.7),
        _make_candidate("dish:4", merchant_id=1, dish_name="D", score=0.6),
        _make_candidate("dish:5", merchant_id=2, dish_name="E", score=0.5),
    ]

    result = diversify(candidates, limit=5, merchant_scoped=True, max_per_merchant=5)

    # All 4 from merchant 1 — custom 5 is larger than the default merchant_scoped floor of 3.
    assert [item.stable_key for item in result] == [
        "dish:1", "dish:2", "dish:3", "dish:4", "dish:5",
    ]


def test_diversifier_still_deduplicates_dish_names() -> None:
    """Duplicate dish names are still removed regardless of max_per_merchant."""
    candidates = [
        _make_candidate("dish:1", merchant_id=1, dish_name="A", score=0.9),
        _make_candidate("dish:2", merchant_id=1, dish_name="A", score=0.8),  # duplicate name
        _make_candidate("dish:3", merchant_id=1, dish_name="B", score=0.7),
    ]

    result = diversify(candidates, limit=3, merchant_scoped=False)

    # dish:1 (first pass), dish:3 (first pass, different name), dish:2 (second pass fill).
    assert [item.stable_key for item in result] == ["dish:1", "dish:3", "dish:2"]


def test_diversifier_empty_candidates() -> None:
    """Empty candidate list returns empty."""
    assert diversify([], limit=5) == []


def test_diversifier_second_pass_fills_remaining() -> None:
    """Second pass fills slots when first pass can't reach limit due to constraints."""
    candidates = [
        _make_candidate("dish:1", merchant_id=1, dish_name="A", score=0.9),
        _make_candidate("dish:2", merchant_id=1, dish_name="B", score=0.8),
        _make_candidate("dish:3", merchant_id=1, dish_name="C", score=0.7),  # 3rd from merchant 1
    ]

    result = diversify(candidates, limit=3, merchant_scoped=False)

    # First pass gets dish:1 and dish:2 (max 2 per merchant).
    # dish:3 excluded in first pass (merchant limit).
    # Second pass fills with dish:3.
    assert [item.stable_key for item in result] == ["dish:1", "dish:2", "dish:3"]


def test_diversifier_multiple_merchants_interleaved() -> None:
    """Candidates from multiple merchants are interleaved by score order."""
    candidates = [
        _make_candidate("dish:1", merchant_id=1, dish_name="A", score=0.9),
        _make_candidate("dish:2", merchant_id=2, dish_name="B", score=0.85),
        _make_candidate("dish:3", merchant_id=1, dish_name="C", score=0.8),
        _make_candidate("dish:4", merchant_id=3, dish_name="D", score=0.75),
        _make_candidate("dish:5", merchant_id=2, dish_name="E", score=0.7),
    ]

    result = diversify(candidates, limit=4, merchant_scoped=False)

    # With max_per_merchant=2, the result should be:
    # dish:1 (m1), dish:2 (m2), dish:3 (m1, second slot), dish:4 (m3)
    assert [item.stable_key for item in result] == [
        "dish:1", "dish:2", "dish:3", "dish:4",
    ]


def test_diversifier_no_merchant_id_no_limit() -> None:
    """Candidates without merchant_id are not constrained by per-merchant limit."""
    candidates = [
        _make_candidate("dish:1", merchant_id=0, dish_name="A", score=0.9),
        _make_candidate("dish:2", merchant_id=0, dish_name="B", score=0.8),
        _make_candidate("dish:3", merchant_id=0, dish_name="C", score=0.7),
    ]

    result = diversify(candidates, limit=3, merchant_scoped=False)

    # No merchant_id constraint; all pass via dish-name uniqueness.
    assert [item.stable_key for item in result] == ["dish:1", "dish:2", "dish:3"]


def test_diversifier_no_dish_name_no_dedup() -> None:
    """Candidates without dish_name are not deduplicated (but still subject to merchant limit)."""
    candidates = [
        _make_candidate("dish:1", merchant_id=1, dish_name="", score=0.9),
        _make_candidate("dish:2", merchant_id=1, dish_name="", score=0.8),
        _make_candidate("dish:3", merchant_id=2, dish_name="", score=0.7),
    ]

    result = diversify(candidates, limit=3, merchant_scoped=False)

    # dish:1, dish:2 both from merchant 1 — max 2, so both in. dish:3 from merchant 2.
    assert [item.stable_key for item in result] == ["dish:1", "dish:2", "dish:3"]


def test_diversifier_merchant_scoped_candidate_count_less_than_limit() -> None:
    """When fewer candidates than limit, all are returned."""
    candidates = [
        _make_candidate("dish:1", merchant_id=1, dish_name="A", score=0.9),
    ]

    result = diversify(candidates, limit=5, merchant_scoped=True)

    assert len(result) == 1
    assert result[0].stable_key == "dish:1"
