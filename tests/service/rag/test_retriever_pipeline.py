from service.agent_runtime.state import AgentPlan
from service.rag.cross_encoder import CrossEncoderReranker
from service.rag.retriever import AdvancedRagRetriever


class _StubScorer:
    """Lightweight scorer that avoids loading the real cross-encoder model."""
    def score(self, query: str, text: str) -> float:
        return 0.5


def _stub_cross_encoder() -> CrossEncoderReranker:
    return CrossEncoderReranker(scorer=_StubScorer())


class StubRecallRoute:
    def __init__(self, candidates=None):
        self.candidates = candidates

    def recall(self, plan, limit):
        from service.rag.models import RecallCandidate

        return self.candidates or [
            RecallCandidate(
                stable_key="dish:11",
                source_type="dish",
                source_id=11,
                route="sql",
                rank=1,
                score=1.0,
                facts={"dish_id": 11, "dish_name": "小炒黄牛肉", "merchant_id": 1, "merchant_name": "兰姨小炒", "price": 42.0, "cuisine_type": "湘菜", "flavor_profile": "鲜辣下饭", "allergens": [], "is_available": True, "merchant_rating": 4.7},
                citation="黄牛肉片现炒，芹菜和小米椒提香提辣。",
            )
        ]


def test_retriever_returns_grounded_evidence() -> None:
    retriever = AdvancedRagRetriever(recall_routes=[StubRecallRoute()], cross_encoder=_stub_cross_encoder())
    agent_plan = AgentPlan(
        intent="recommendation",
        normalized_query="辣的湘菜",
        requires_rag=True,
        filters={"cuisine_types": ["湘菜"], "flavor_preferences": ["辣"], "budget_max": None, "party_size": None, "exclude_allergens": []},
    )

    evidence = retriever.retrieve("帮我推荐几个比较辣的湘菜", agent_plan, memories=[], limit=3)

    assert evidence[0].facts["dish_name"] == "小炒黄牛肉"
    assert "湘菜" in evidence[0].why_matched
    assert evidence[0].citation


def test_retriever_without_session_skips_catalog_routes() -> None:
    retriever = AdvancedRagRetriever(cross_encoder=_stub_cross_encoder())

    route_names = [type(route).__name__ for route in retriever.recall_routes]
    assert "SqlCatalogRecallRoute" not in route_names
    assert "BusinessRecallRoute" not in route_names


def test_retriever_applies_price_desc_and_limit_after_recall() -> None:
    from service.rag.models import RecallCandidate

    retriever = AdvancedRagRetriever(
        cross_encoder=_stub_cross_encoder(),
        recall_routes=[
            StubRecallRoute([
                RecallCandidate(
                    stable_key="dish:1",
                    source_type="dish",
                    source_id=1,
                    route="dense",
                    rank=1,
                    score=0.99,
                    facts={"dish_id": 1, "dish_name": "辣椒炒肉", "merchant_id": 1, "merchant_name": "A", "price": 29.0, "cuisine_type": "湘菜", "is_available": True},
                    citation="辣椒炒肉",
                ),
                RecallCandidate(
                    stable_key="dish:2",
                    source_type="dish",
                    source_id=2,
                    route="dense",
                    rank=2,
                    score=0.80,
                    facts={"dish_id": 2, "dish_name": "剁椒鱼块", "merchant_id": 2, "merchant_name": "B", "price": 38.0, "cuisine_type": "湘菜", "is_available": True},
                    citation="剁椒鱼块",
                ),
                RecallCandidate(
                    stable_key="dish:3",
                    source_type="dish",
                    source_id=3,
                    route="dense",
                    rank=3,
                    score=0.95,
                    facts={"dish_id": 3, "dish_name": "外婆菜炒鸡蛋", "merchant_id": 3, "merchant_name": "C", "price": 24.0, "cuisine_type": "湘菜", "is_available": True},
                    citation="外婆菜炒鸡蛋",
                ),
            ])
        ]
    )
    agent_plan = AgentPlan(
        intent="recommendation",
        normalized_query="最贵的湘菜",
        requires_rag=True,
        filters={
            "cuisine_types": ["湘菜"],
            "flavor_preferences": [],
            "budget_max": None,
            "party_size": None,
            "exclude_allergens": [],
            "sort_by": "price_desc",
            "limit": 1,
        },
    )

    evidence = retriever.retrieve("推荐一个最贵的湘菜", agent_plan, memories=[], limit=3)

    assert len(evidence) == 1
    assert evidence[0].facts["dish_name"] == "剁椒鱼块"


def test_cross_encoder_and_reranker_receive_normalized_query() -> None:
    """Cross-encoder and weighted reranker should receive normalized_query, not the raw multi-step original."""
    from service.rag.models import RecallCandidate

    candidates = [
        RecallCandidate(
            stable_key=f"dish:{i}",
            source_type="dish",
            source_id=i,
            route="dense",
            rank=i,
            score=1.0 - i * 0.1,
            facts={"dish_id": i, "dish_name": f"川菜{i}", "merchant_id": 1, "merchant_name": "A", "price": 30.0, "cuisine_type": "川菜", "is_available": True},
            citation=f"川菜{i}",
        )
        for i in range(1, 6)
    ]

    retriever = AdvancedRagRetriever(recall_routes=[StubRecallRoute(candidates)], cross_encoder=_stub_cross_encoder())

    captured_queries: dict[str, str] = {}
    orig_ce_rerank = retriever.cross_encoder.rerank
    orig_wr_rerank = retriever.reranker.rerank

    def spy_ce_rerank(query, *a, **kw):
        captured_queries["cross_encoder"] = query
        return orig_ce_rerank(query, *a, **kw)

    def spy_wr_rerank(*a, original_query=None, **kw):
        captured_queries["reranker"] = original_query
        return orig_wr_rerank(*a, original_query=original_query, **kw)

    retriever.cross_encoder.rerank = spy_ce_rerank
    retriever.reranker.rerank = spy_wr_rerank

    agent_plan = AgentPlan(
        intent="recommendation",
        normalized_query="川菜推荐",
        requires_rag=True,
        filters={"cuisine_types": ["川菜"]},
    )

    retriever.retrieve(
        "推荐几个川菜，再帮我加入购物车",
        agent_plan,
        memories=[],
        limit=5,
    )

    assert captured_queries["cross_encoder"] == "川菜推荐"
    assert captured_queries["reranker"] == "川菜推荐"
