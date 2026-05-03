from tools.evaluate_assistant_rag import (
    _compute_average_precision,
    _compute_hit_rate,
    _compute_mrr,
    _compute_ndcg_at_k,
    _compute_precision_at_k,
    _compute_recall_at_k,
    _get_relevance,
    _passes_constraints,
    _passes_diversity,
    _has_citation,
)


# ── _get_relevance ─────────────────────────────────────────────────

def test_get_relevance_exact_match():
    grades = {"dish:11": 5, "merchant:3": 3}
    assert _get_relevance("dish:11", grades) == 5
    assert _get_relevance("merchant:3", grades) == 3
    assert _get_relevance("dish:99", grades) == 0


def test_get_relevance_wildcard_match():
    grades = {"dish:*": 3, "merchant:*": 2}
    assert _get_relevance("dish:11", grades) == 3
    assert _get_relevance("merchant:5", grades) == 2
    assert _get_relevance("memory:1", grades) == 0


def test_get_relevance_exact_takes_priority_over_wildcard():
    grades = {"dish:*": 1, "dish:42": 5}
    assert _get_relevance("dish:42", grades) == 5
    assert _get_relevance("dish:99", grades) == 1


# ── _compute_hit_rate ──────────────────────────────────────────────

def test_hit_rate_all_relevant():
    ids = ["dish:1", "dish:2", "dish:3"]
    grades = {"dish:*": 3}
    assert _compute_hit_rate(ids, grades) == 1.0


def test_hit_rate_none_relevant():
    ids = ["dish:1", "dish:2", "dish:3"]
    grades = {"dish:*": 0}
    assert _compute_hit_rate(ids, grades) == 0.0


def test_hit_rate_partial():
    ids = ["dish:1", "merchant:2"]
    grades = {"dish:*": 3, "merchant:*": 0}
    assert _compute_hit_rate(ids, grades) == 1.0


# ── _compute_recall_at_k ───────────────────────────────────────────

def test_recall_perfect():
    ids = ["dish:1", "dish:2", "dish:3"]
    grades = {"dish:1": 5, "dish:2": 3, "dish:3": 2}
    assert _compute_recall_at_k(ids, grades, k=3) == 1.0


def test_recall_partial():
    ids = ["dish:1", "dish:4"]
    grades = {"dish:1": 5, "dish:2": 5, "dish:3": 5}
    assert _compute_recall_at_k(ids, grades, k=5) == 1.0 / 3.0


def test_recall_zero_relevant():
    ids = ["dish:1", "dish:2"]
    grades = {}
    assert _compute_recall_at_k(ids, grades, k=5) == 0.0


def test_recall_with_wildcard():
    ids = ["dish:1", "dish:2", "merchant:1"]
    grades = {"dish:*": 3}
    # With wildcards: total_relevant = count of matching retrieved items = 2 (both dish:*)
    # hits at k=2 = 2, recall = 2/2 = 1.0 (capped)
    assert _compute_recall_at_k(ids, grades, k=2) == 1.0


# ── _compute_precision_at_k ────────────────────────────────────────

def test_precision_perfect():
    ids = ["dish:1", "dish:2", "dish:3"]
    grades = {"dish:*": 5}
    assert _compute_precision_at_k(ids, grades, k=3) == 1.0


def test_precision_half():
    ids = ["dish:1", "merchant:1"]
    grades = {"dish:*": 5, "merchant:*": 0}
    assert _compute_precision_at_k(ids, grades, k=2) == 0.5


def test_precision_empty():
    assert _compute_precision_at_k([], {}, k=5) == 0.0


# ── _compute_average_precision ─────────────────────────────────────

def test_ap_perfect_ranking():
    ids = ["dish:1", "dish:2", "dish:3"]
    grades = {"dish:1": 5, "dish:2": 4, "dish:3": 3}
    # P@1=1, P@2=1, P@3=1 => AP = (1*1 + 1*1 + 1*1) / 3 = 1.0
    assert _compute_average_precision(ids, grades) == 1.0


def test_ap_interleaved():
    ids = ["dish:1", "merchant:1", "dish:2"]
    grades = {"dish:*": 5, "merchant:*": 0}
    # total_relevant from wildcard: 2 items match dish:* (dish:1, dish:2)
    # P@1=1, P@2=0.5(P@2 unchanged since merchant not relevant), P@3=2/3
    # AP = (1*1 + 0*0.5 + 1*2/3) / 2 = (1 + 0.6667) / 2 = 0.8333
    ap = _compute_average_precision(ids, grades)
    expected = (1.0 + 2.0 / 3.0) / 2.0  # = (1.6667)/2 = 0.8333...
    assert abs(ap - expected) < 0.001


def test_ap_no_relevant():
    ids = ["dish:1", "dish:2"]
    grades = {}
    assert _compute_average_precision(ids, grades) == 0.0


# ── _compute_ndcg_at_k ─────────────────────────────────────────────

def test_ndcg_perfect_ordering():
    ids = ["dish:1", "dish:2", "dish:3"]
    grades = {"dish:1": 5, "dish:2": 3, "dish:3": 1}
    assert _compute_ndcg_at_k(ids, grades, k=3) == 1.0


def test_ndcg_suboptimal_ordering():
    ids = ["dish:3", "dish:2", "dish:1"]
    grades = {"dish:1": 5, "dish:2": 3, "dish:3": 1}
    ndcg = _compute_ndcg_at_k(ids, grades, k=3)
    assert 0.0 < ndcg < 1.0


def test_ndcg_all_zero():
    ids = ["dish:1", "dish:2"]
    grades = {}
    assert _compute_ndcg_at_k(ids, grades, k=3) == 0.0


# ── _compute_mrr ───────────────────────────────────────────────────

def test_mrr_first_relevant_at_1():
    ids = ["dish:1", "dish:2", "dish:3"]
    grades = {"dish:*": 5}
    assert _compute_mrr(ids, grades) == 1.0


def test_mrr_first_relevant_at_3():
    ids = ["merchant:1", "merchant:2", "dish:1"]
    grades = {"dish:*": 5, "merchant:*": 0}
    assert _compute_mrr(ids, grades) == 1.0 / 3.0


def test_mrr_no_relevant():
    ids = ["dish:1", "dish:2"]
    grades = {}
    assert _compute_mrr(ids, grades) == 0.0


# ── _passes_constraints ────────────────────────────────────────────

class _FakeEvidence:
    def __init__(self, facts):
        self.facts = facts
        self.title = facts.get("dish_name", "")
        self.citation = ""
        self.why_matched = []


def test_constraint_budget_pass():
    ev = _FakeEvidence({"price": 28, "cuisine_type": "湘菜"})
    assert _passes_constraints(ev, {"budget_max": 50, "party_size": 1})


def test_constraint_budget_fail():
    ev = _FakeEvidence({"price": 60, "cuisine_type": "湘菜"})
    assert not _passes_constraints(ev, {"budget_max": 50, "party_size": 1})


def test_constraint_allergen_pass():
    ev = _FakeEvidence({"allergens": ["花生"], "cuisine_type": "湘菜"})
    assert _passes_constraints(ev, {"exclude_allergens": ["牛奶"]})


def test_constraint_allergen_fail():
    ev = _FakeEvidence({"allergens": ["花生", "牛奶"], "cuisine_type": "湘菜"})
    assert not _passes_constraints(ev, {"exclude_allergens": ["花生"]})


def test_constraint_cuisine_pass():
    ev = _FakeEvidence({"cuisine_type": "湘菜"})
    assert _passes_constraints(ev, {"cuisine_types": ["湘菜"]})


def test_constraint_cuisine_fail():
    ev = _FakeEvidence({"cuisine_type": "粤菜"})
    assert not _passes_constraints(ev, {"cuisine_types": ["湘菜"]})


def test_constraint_required_keyword_pass():
    ev = _FakeEvidence({"dish_name": "辣椒炒肉", "description": "鲜辣下饭"})
    assert _passes_constraints(ev, {"required_keywords": ["辣"]})


def test_constraint_required_keyword_fail():
    ev = _FakeEvidence({"dish_name": "白粥", "description": "清淡暖胃"})
    assert not _passes_constraints(ev, {"required_keywords": ["辣"]})


def test_constraint_forbidden_keyword_pass():
    ev = _FakeEvidence({"dish_name": "辣椒炒肉"})
    assert _passes_constraints(ev, {"forbidden_keywords": ["甜"]})


def test_constraint_forbidden_keyword_fail():
    ev = _FakeEvidence({"dish_name": "辣子鸡"})
    assert not _passes_constraints(ev, {"forbidden_keywords": ["辣"]})


# ── _passes_diversity ──────────────────────────────────────────────

def test_diversity_three_different_merchants():
    ev = [
        _FakeEvidence({"merchant_id": 1, "dish_name": "A"}),
        _FakeEvidence({"merchant_id": 2, "dish_name": "B"}),
        _FakeEvidence({"merchant_id": 3, "dish_name": "C"}),
    ]
    for e in ev:
        e.source_type = "dish"
    assert _passes_diversity(ev)


def test_diversity_single_merchant_two_dishes():
    """When only 1 unique merchant exists in results, diversity trivially passes."""
    ev = [
        _FakeEvidence({"merchant_id": 1, "dish_name": "A"}),
        _FakeEvidence({"merchant_id": 1, "dish_name": "B"}),
    ]
    for e in ev:
        e.source_type = "dish"
    assert _passes_diversity(ev)


def test_diversity_mixed_merchants_fails_when_too_few():
    """3+ unique merchants in total but only 1 in first 3 positions: fails."""
    ev = [
        _FakeEvidence({"merchant_id": 1, "dish_name": "A"}),
        _FakeEvidence({"merchant_id": 1, "dish_name": "B"}),
        _FakeEvidence({"merchant_id": 1, "dish_name": "C"}),
        _FakeEvidence({"merchant_id": 2, "dish_name": "D"}),
    ]
    for e in ev:
        e.source_type = "dish"
    assert not _passes_diversity(ev)


def test_diversity_single_dish():
    ev = [_FakeEvidence({"merchant_id": 1, "dish_name": "A"})]
    ev[0].source_type = "dish"
    assert _passes_diversity(ev)


# ── _has_citation ──────────────────────────────────────────────────

def test_has_citation_true():
    ev = _FakeEvidence({})
    ev.citation = "黄牛肉片现炒"
    assert _has_citation(ev)


def test_has_citation_false():
    ev = _FakeEvidence({})
    ev.citation = ""
    assert not _has_citation(ev)


def test_has_citation_none():
    ev = _FakeEvidence({})
    ev.citation = None
    assert not _has_citation(ev)
