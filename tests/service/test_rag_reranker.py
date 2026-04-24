from service.agent_state import EvidencePack
from service.rag_reranker import RagReranker


def test_reranker_sorts_by_blended_score() -> None:
    candidates = [
        EvidencePack(
            source_type="dish",
            source_id=11,
            merchant_id=1,
            title="低分菜",
            facts={
                "semantic_score": 0.2,
                "keyword_score": 0.1,
                "merchant_rating": 4.0,
                "is_recommended": False,
                "constraint_match_score": 1.0,
            },
        ),
        EvidencePack(
            source_type="dish",
            source_id=12,
            merchant_id=1,
            title="高分菜",
            facts={
                "semantic_score": 0.9,
                "keyword_score": 0.8,
                "merchant_rating": 4.8,
                "is_recommended": True,
                "constraint_match_score": 1.0,
            },
        ),
    ]

    reranked = RagReranker().rerank(candidates)

    assert reranked[0].source_id == 12
    assert reranked[0].score > reranked[1].score
