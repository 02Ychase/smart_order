from service.rag.fusion import reciprocal_rank_fusion
from service.rag.models import RecallCandidate


def test_rrf_merges_candidates_by_stable_key() -> None:
    dense = [
        RecallCandidate(stable_key="dish:1", source_type="dish", source_id=1, route="dense", rank=1, score=0.8),
        RecallCandidate(stable_key="dish:2", source_type="dish", source_id=2, route="dense", rank=2, score=0.7),
    ]
    sparse = [
        RecallCandidate(stable_key="dish:2", source_type="dish", source_id=2, route="sparse", rank=1, score=1.0),
        RecallCandidate(stable_key="dish:3", source_type="dish", source_id=3, route="sparse", rank=2, score=0.9),
    ]

    fused = reciprocal_rank_fusion([dense, sparse], limit=3)

    assert [item.stable_key for item in fused] == ["dish:2", "dish:1", "dish:3"]
    assert fused[0].route_scores["dense"] > 0
    assert fused[0].route_scores["sparse"] > 0
