from service.rag.diversifier import diversify
from service.rag.models import FusedCandidate


def test_diversifier_limits_same_merchant_when_not_scoped() -> None:
    candidates = [
        FusedCandidate(stable_key="dish:1", source_type="dish", source_id=1, facts={"merchant_id": 1, "dish_name": "A"}, final_score=0.9),
        FusedCandidate(stable_key="dish:2", source_type="dish", source_id=2, facts={"merchant_id": 1, "dish_name": "B"}, final_score=0.8),
        FusedCandidate(stable_key="dish:3", source_type="dish", source_id=3, facts={"merchant_id": 2, "dish_name": "C"}, final_score=0.7),
    ]

    result = diversify(candidates, limit=2, merchant_scoped=False)

    assert [item.stable_key for item in result] == ["dish:1", "dish:3"]
