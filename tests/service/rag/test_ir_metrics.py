import math

from service.rag.eval_metrics import (
    compute_all,
    hit_rate,
    mrr,
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
)


class TestRecallAtK:
    def test_basic(self) -> None:
        assert recall_at_k(["a", "b", "c", "d", "e"], {"a", "c", "f"}, k=5) == 2 / 3

    def test_partial_window(self) -> None:
        assert recall_at_k(["a", "b", "c", "d", "e"], {"a", "c", "f"}, k=2) == 1 / 3

    def test_empty_relevant(self) -> None:
        assert recall_at_k(["a", "b"], set(), k=5) == 0.0

    def test_all_relevant(self) -> None:
        assert recall_at_k(["a", "b", "c"], {"a", "b", "c"}, k=3) == 1.0


class TestPrecisionAtK:
    def test_basic(self) -> None:
        assert precision_at_k(["a", "b", "c", "d", "e"], {"a", "c"}, k=5) == 2 / 5

    def test_zero_k(self) -> None:
        assert precision_at_k(["a", "b"], {"a"}, k=0) == 0.0

    def test_empty_relevant(self) -> None:
        assert precision_at_k(["a", "b"], set(), k=5) == 0.0


class TestHitRate:
    def test_positive(self) -> None:
        assert hit_rate(["a", "b", "c"], {"b"}, k=3) == 1.0

    def test_negative(self) -> None:
        assert hit_rate(["a", "b", "c"], {"d"}, k=3) == 0.0

    def test_outside_k(self) -> None:
        assert hit_rate(["a", "b", "c"], {"c"}, k=2) == 0.0


class TestMRR:
    def test_first(self) -> None:
        assert mrr(["a", "b", "c"], {"a"}) == 1.0

    def test_second(self) -> None:
        assert mrr(["a", "b", "c"], {"b"}) == 0.5

    def test_third(self) -> None:
        assert abs(mrr(["a", "b", "c"], {"c"}) - 1 / 3) < 1e-9

    def test_none_found(self) -> None:
        assert mrr(["a", "b", "c"], {"d"}) == 0.0


class TestNDCG:
    def test_perfect_order(self) -> None:
        assert ndcg_at_k(["a", "b", "c"], {"a", "b", "c"}, {"a"}, k=3) == 1.0

    def test_reversed_order(self) -> None:
        result = ndcg_at_k(["c", "b", "a"], {"a", "b", "c"}, {"a"}, k=3)
        assert 0.0 < result < 1.0

    def test_no_relevant(self) -> None:
        assert ndcg_at_k(["a", "b"], set(), k=5) == 0.0

    def test_graded_relevance(self) -> None:
        ranked = ["h1", "r1", "x"]
        relevant = {"h1", "r1"}
        highly = {"h1"}
        result = ndcg_at_k(ranked, relevant, highly, k=3)
        ideal_dcg = 2.0 / math.log2(2) + 1.0 / math.log2(3)
        actual_dcg = 2.0 / math.log2(2) + 1.0 / math.log2(3)
        assert abs(result - actual_dcg / ideal_dcg) < 1e-9

    def test_highly_relevant_at_wrong_position(self) -> None:
        ranked = ["r1", "h1"]
        relevant = {"h1", "r1"}
        highly = {"h1"}
        result = ndcg_at_k(ranked, relevant, highly, k=2)
        assert result < 1.0


class TestComputeAll:
    def test_returns_expected_keys(self) -> None:
        result = compute_all(["a", "b", "c"], {"a", "c"}, k=3)
        assert "recall@3" in result
        assert "precision@3" in result
        assert "hit_rate@3" in result
        assert "mrr" in result
        assert "ndcg@3" in result
        assert len(result) == 5

    def test_values_consistent(self) -> None:
        ranked = ["a", "b", "c"]
        relevant = {"a", "c"}
        result = compute_all(ranked, relevant, k=3)
        assert result["recall@3"] == recall_at_k(ranked, relevant, 3)
        assert result["precision@3"] == precision_at_k(ranked, relevant, 3)
