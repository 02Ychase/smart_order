from service.rag.models import FusedCandidate
from service.rag.reranker import WeightedReranker


def test_weighted_reranker_prefers_relevance_and_constraints() -> None:
    candidates = [
        FusedCandidate(stable_key="dish:1", source_type="dish", source_id=1, facts={"merchant_rating": 4.9}, dense_score=0.2, lexical_score=0.1, constraint_match=0.2),
        FusedCandidate(stable_key="dish:2", source_type="dish", source_id=2, facts={"merchant_rating": 4.5}, dense_score=0.8, lexical_score=0.7, constraint_match=1.0),
    ]

    ranked = WeightedReranker().rerank(candidates, original_query="辣的湘菜")

    assert ranked[0].stable_key == "dish:2"
    assert ranked[0].final_score > ranked[1].final_score
