from service.rag_query_rewriter import RagQueryRewriter


def test_rewriter_extracts_budget_party_and_allergen() -> None:
    rewriter = RagQueryRewriter()
    request = rewriter.rewrite("推荐几种川菜，2个人吃，100元以内，不要花生")

    assert request.hard_filters["budget_max"] == 100.0
    assert request.hard_filters["party_size"] == 2
    assert request.hard_filters["exclude_allergens"] == ["花生"]
    assert "川菜" in request.hard_filters["cuisine_types"]
    assert len(request.semantic_queries) >= 2


def test_rewriter_detects_merchant_knowledge_query() -> None:
    rewriter = RagQueryRewriter()
    request = rewriter.rewrite("有哪些咖啡甜品店？几点营业？")

    assert request.source_types == ["merchant"]
    assert any("咖啡" in query for query in request.semantic_queries)
