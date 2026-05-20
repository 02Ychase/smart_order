from __future__ import annotations

import math


def recall_at_k(ranked_keys: list[str], relevant: set[str], k: int) -> float:
    if not relevant:
        return 0.0
    hits = len(set(ranked_keys[:k]) & relevant)
    return hits / len(relevant)


def precision_at_k(ranked_keys: list[str], relevant: set[str], k: int) -> float:
    if k <= 0:
        return 0.0
    hits = len(set(ranked_keys[:k]) & relevant)
    return hits / k


def hit_rate(ranked_keys: list[str], relevant: set[str], k: int) -> float:
    return 1.0 if set(ranked_keys[:k]) & relevant else 0.0


def mrr(ranked_keys: list[str], relevant: set[str]) -> float:
    for i, key in enumerate(ranked_keys):
        if key in relevant:
            return 1.0 / (i + 1)
    return 0.0


def ndcg_at_k(
    ranked_keys: list[str],
    relevant: set[str],
    highly_relevant: set[str] | None = None,
    k: int = 10,
) -> float:
    highly_relevant = highly_relevant or set()

    def gain(key: str) -> float:
        if key in highly_relevant:
            return 2.0
        if key in relevant:
            return 1.0
        return 0.0

    dcg = sum(gain(key) / math.log2(i + 2) for i, key in enumerate(ranked_keys[:k]))

    ideal_gains = sorted(
        [gain(key) for key in relevant | highly_relevant],
        reverse=True,
    )[:k]
    idcg = sum(g / math.log2(i + 2) for i, g in enumerate(ideal_gains))

    if idcg == 0.0:
        return 0.0
    return dcg / idcg


def compute_all(
    ranked_keys: list[str],
    relevant: set[str],
    highly_relevant: set[str] | None = None,
    k: int = 5,
) -> dict[str, float]:
    return {
        f"recall@{k}": recall_at_k(ranked_keys, relevant, k),
        f"precision@{k}": precision_at_k(ranked_keys, relevant, k),
        f"hit_rate@{k}": hit_rate(ranked_keys, relevant, k),
        "mrr": mrr(ranked_keys, relevant),
        f"ndcg@{k}": ndcg_at_k(ranked_keys, relevant, highly_relevant, k),
    }
