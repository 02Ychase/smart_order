from tools.evaluate_assistant_rag import evaluate_cases


class Evidence:
    def __init__(
        self,
        source_id,
        source_type="dish",
        facts=None,
        title="",
        citation="citation",
    ):
        self.source_id = source_id
        self.source_type = source_type
        self.facts = facts or {}
        self.title = title
        self.citation = citation
        self.why_matched = ["match"]


class DiverseRetriever:
    def retrieve(self, query, limit=5):
        return [
            Evidence(1, facts={"merchant_id": 1, "dish_name": "A", "cuisine_type": "湘菜"}),
            Evidence(2, facts={"merchant_id": 1, "dish_name": "B", "cuisine_type": "湘菜"}),
            Evidence(3, facts={"merchant_id": 2, "dish_name": "C", "cuisine_type": "湘菜"}),
        ]


def test_evaluator_reports_diversity_and_citation_coverage() -> None:
    cases = [
        {
            "query": "湘菜",
            "expected_source_type": "dish",
            "constraints": {"allowed_cuisine_types": ["湘菜"]},
        }
    ]

    metrics = evaluate_cases(cases, DiverseRetriever())

    assert "diversity_pass_rate" in metrics
    assert "citation_coverage" in metrics
    assert metrics["citation_coverage"] == 1.0


class KeywordRetriever:
    def retrieve(self, query, limit=5):
        return [
            Evidence(
                1,
                facts={
                    "merchant_id": 1,
                    "dish_name": "芝士披萨",
                    "cuisine_type": "意式",
                    "description": "浓郁芝士披萨",
                },
            )
        ]


def test_evaluator_checks_allowed_cuisine_and_keyword_constraints() -> None:
    cases = [
        {
            "query": "recommend some cheesy pizza",
            "expected_source_type": "dish",
            "constraints": {
                "allowed_cuisine_types": ["意式"],
                "required_keywords": ["披萨", "芝士"],
                "forbidden_keywords": ["麻辣浓郁"],
            },
        }
    ]

    metrics = evaluate_cases(cases, KeywordRetriever())

    assert metrics["constraint_pass_rate"] == 1.0
