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


def test_rrf_deduplicates_same_route_stable_key_before_scoring() -> None:
    dense = [
        RecallCandidate(stable_key="dish:1", source_type="dish", source_id=1, route="dense", rank=1, score=0.9),
        RecallCandidate(stable_key="dish:1", source_type="dish", source_id=1, route="dense", rank=2, score=0.8),
        RecallCandidate(stable_key="dish:2", source_type="dish", source_id=2, route="dense", rank=1, score=0.7),
    ]

    fused = reciprocal_rank_fusion([dense], limit=2)

    by_key = {item.stable_key: item for item in fused}
    assert by_key["dish:1"].final_score == 1 / (60 + 1)
    assert by_key["dish:1"].final_score == by_key["dish:2"].final_score


def test_rrf_deduplicates_same_route_stable_key_across_batches() -> None:
    dense_a = [
        RecallCandidate(stable_key="dish:1", source_type="dish", source_id=1, route="dense", rank=1, score=0.9),
    ]
    dense_b = [
        RecallCandidate(stable_key="dish:1", source_type="dish", source_id=1, route="dense", rank=2, score=0.8),
        RecallCandidate(stable_key="dish:2", source_type="dish", source_id=2, route="dense", rank=1, score=0.7),
    ]

    fused = reciprocal_rank_fusion([dense_a, dense_b], limit=2)

    by_key = {item.stable_key: item for item in fused}
    assert by_key["dish:1"].final_score == 1 / (60 + 1)
    assert by_key["dish:1"].route_ranks["dense"] == 1
    assert by_key["dish:1"].final_score == by_key["dish:2"].final_score


def test_rrf_merges_structured_facts_from_later_routes() -> None:
    dense = [
        RecallCandidate(
            stable_key="dish:1",
            source_type="dish",
            source_id=1,
            route="dense",
            rank=1,
            score=0.9,
            facts={"dish_name": "辣椒炒肉", "cuisine_type": "湘菜"},
            citation="",
        ),
    ]
    sql = [
        RecallCandidate(
            stable_key="dish:1",
            source_type="dish",
            source_id=1,
            route="sql",
            rank=1,
            score=1.0,
            facts={
                "dish_name": "辣椒炒肉",
                "cuisine_type": "湘菜",
                "is_available": True,
                "allergens": [],
            },
            citation="鲜辣下饭",
        )
    ]

    fused = reciprocal_rank_fusion([dense, sql], limit=1)

    assert fused[0].facts["is_available"] is True
    assert fused[0].facts["allergens"] == []
    assert fused[0].citation == "鲜辣下饭"
