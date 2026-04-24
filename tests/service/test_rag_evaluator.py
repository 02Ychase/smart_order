from tools.evaluate_assistant_rag import evaluate_cases


class StubRetriever:
    def retrieve(self, query, limit=5):
        return [
            type("Evidence", (), {
                "source_type": "dish",
                "source_id": 11,
                "facts": {"price": 28.0, "allergens": [], "cuisine_type": "川味麻辣"},
            })()
        ]


def test_evaluate_cases_reports_recall_and_constraint_pass_rate() -> None:
    cases = [
        {
            "query": "推荐几种川菜，2个人吃，100元以内，不要花生",
            "expected_source_ids": [11],
            "constraints": {"budget_max": 100, "party_size": 2, "exclude_allergens": ["花生"]},
        }
    ]

    metrics = evaluate_cases(cases, retriever=StubRetriever())

    assert metrics["case_count"] == 1
    assert metrics["recall_at_5"] == 1.0
    assert metrics["constraint_pass_rate"] == 1.0
