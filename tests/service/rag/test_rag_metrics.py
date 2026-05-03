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

    assert "recall_metrics" in metrics
    assert "diversity_pass_rate" in metrics["recall_metrics"]
    assert "citation_coverage" in metrics["recall_metrics"]
    assert metrics["recall_metrics"]["citation_coverage"] == 1.0


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


def test_evaluator_computes_ranking_metrics_with_relevance_grades() -> None:
    from tools.evaluate_assistant_rag import (
        _compute_ndcg_at_k,
        _compute_mrr,
        _compute_precision_at_k,
        _compute_average_precision,
        _compute_hit_rate,
    )

    retrieved = ["dish:1", "dish:2", "dish:3", "dish:4", "dish:5"]
    grades = {"dish:1": 5, "dish:2": 3, "dish:3": 1, "dish:4": 0, "dish:5": 4}

    ndcg = _compute_ndcg_at_k(retrieved, grades, k=5)
    mrr = _compute_mrr(retrieved, grades)
    precision = _compute_precision_at_k(retrieved, grades, k=5)
    ap = _compute_average_precision(retrieved, grades)
    hit = _compute_hit_rate(retrieved, grades)

    assert 0.0 <= ndcg <= 1.0
    assert mrr == 1.0  # dish:1 at rank 1
    assert precision == 4.0 / 5.0  # 4 relevant out of 5
    assert 0.0 < ap <= 1.0
    assert hit == 1.0


def test_evaluator_ranking_metrics_skip_when_no_grades() -> None:
    from tools.evaluate_assistant_rag import evaluate_cases

    class MinimalRetriever:
        def retrieve(self, query, limit=5):
            return [
                type("Evidence", (), {
                    "source_type": "dish",
                    "source_id": 1,
                    "facts": {},
                    "title": "",
                    "citation": "",
                    "why_matched": [],
                })()
            ]

    cases = [{"query": "test", "expected_source_type": "dish", "constraints": {}}]
    metrics = evaluate_cases(cases, MinimalRetriever())

    assert "ranking_metrics" not in metrics
    assert "recall_metrics" in metrics


def test_evaluator_backward_compat_old_format() -> None:
    from tools.evaluate_assistant_rag import evaluate_cases

    class OldCompatRetriever:
        def retrieve(self, query, limit=5):
            return [
                type("Evidence", (), {
                    "source_type": "dish",
                    "source_id": 11,
                    "facts": {"price": 28.0, "allergens": [], "cuisine_type": "川味麻辣"},
                    "title": "",
                    "citation": "test citation",
                    "why_matched": [],
                })()
            ]

    case = {
        "query": "推荐几种川菜，2个人吃，100元以内，不要花生",
        "expected_source_ids": [11],
        "constraints": {"budget_max": 100, "party_size": 2, "exclude_allergens": ["花生"]},
    }
    metrics = evaluate_cases([case], OldCompatRetriever())
    assert metrics["case_count"] == 1
    assert metrics["recall_metrics"]["recall_at_5"] == 1.0
    assert metrics["recall_metrics"]["constraint_pass_rate"] == 1.0


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

    assert metrics["recall_metrics"]["constraint_pass_rate"] == 1.0
