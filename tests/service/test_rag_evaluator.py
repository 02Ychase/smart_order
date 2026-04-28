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


def test_main_uses_advanced_retriever_with_case_constraints(monkeypatch) -> None:
    import tools.evaluate_assistant_rag as evaluator

    calls = {}

    class Session:
        def close(self):
            calls["closed"] = True

    class AdvancedRetriever:
        def __init__(self, session):
            calls["session"] = session

        def retrieve(self, original_query, agent_plan, memories, limit):
            calls["query"] = original_query
            calls["agent_plan"] = agent_plan
            return [
                type(
                    "Evidence",
                    (),
                    {
                        "source_type": "dish",
                        "source_id": 11,
                        "facts": {"cuisine_type": "湘菜", "dish_name": "辣椒炒肉"},
                        "title": "辣椒炒肉",
                        "citation": "鲜辣下饭",
                        "why_matched": ["湘菜", "辣"],
                    },
                )()
            ]

    session = Session()
    monkeypatch.setattr(evaluator, "SessionLocal", lambda: session)
    monkeypatch.setattr(evaluator, "AdvancedRagRetriever", AdvancedRetriever)
    monkeypatch.setattr(
        evaluator,
        "load_cases",
        lambda path: [
            {
                "query": "帮我推荐几个比较辣的湘菜",
                "expected_source_type": "dish",
                "constraints": {
                    "allowed_cuisine_types": ["湘菜"],
                    "required_keywords": ["辣"],
                },
            }
        ],
    )

    assert evaluator.main() == 0

    assert calls["session"] is session
    assert calls["closed"] is True
    assert calls["query"] == "帮我推荐几个比较辣的湘菜"
    assert calls["agent_plan"].filters["cuisine_types"] == ["湘菜"]
    assert calls["agent_plan"].filters["flavor_preferences"] == ["辣"]
