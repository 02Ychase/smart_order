from tools.rag_evaluation import RagEvaluator, EvalResult


def test_eval_result_metrics():
    result = EvalResult(
        case_id="test_01",
        query="辣的湘菜",
        expected_keywords=["湘菜", "辣"],
        retrieved_texts=["湘菜 辣椒炒肉 鲜辣", "粤菜 白切鸡 清淡"],
        retrieved_source_types=["dish", "dish"],
    )
    assert result.keyword_recall() == 1.0


def test_eval_result_no_results():
    result = EvalResult(
        case_id="test_02",
        query="测试",
        expected_keywords=["不存在"],
        retrieved_texts=[],
        retrieved_source_types=[],
    )
    assert result.keyword_recall() == 0.0


def test_evaluator_runs_batch():
    test_cases = [
        {
            "id": "t1",
            "query": "辣的湘菜",
            "intent": "recommendation",
            "expected_source_type": "dish",
            "expected_keywords": ["湘菜"],
            "min_results": 1,
        }
    ]

    class FakeRetriever:
        def retrieve(self, query, agent_plan, memories, limit):
            return [type("E", (), {
                "source_type": "dish", "source_id": 1, "merchant_id": 1,
                "title": "辣椒炒肉", "facts": {"dish_name": "辣椒炒肉", "cuisine_type": "湘菜"},
                "why_matched": ["湘菜"], "citation": "湘菜经典", "score": 0.9,
            })()]

    evaluator = RagEvaluator(retriever=FakeRetriever())
    results = evaluator.evaluate(test_cases)

    assert len(results) == 1
    assert results[0].keyword_recall() == 1.0
