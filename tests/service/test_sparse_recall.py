from __future__ import annotations

import pytest

from service.rag.fusion import reciprocal_rank_fusion
from service.rag.models import FusedCandidate, RagQueryPlan, RecallCandidate
from service.rag.recall import SparseVectorRecallRoute


class StubCatalog:
    def list_merchants(self) -> list[dict]:
        return [
            {
                "id": 1,
                "name": "川妹小炒",
                "description": "地道川味麻辣，现炒现卖",
                "rating": 4.8,
                "homepage_category": "川菜",
                "merchant_tags": ["川味", "麻辣", "现炒"],
            },
            {
                "id": 2,
                "name": "粤港烧腊",
                "description": "正宗烧鹅叉烧，老字号",
                "rating": 4.5,
                "homepage_category": "粤菜",
                "merchant_tags": ["烧腊", "粤式"],
            },
        ]

    def list_dishes_by_merchant(self, merchant_id: int) -> list[dict]:
        if merchant_id == 1:
            return [
                {
                    "id": 101,
                    "merchant_id": 1,
                    "name": "水煮牛肉",
                    "description": "麻辣鲜香，嫩滑可口",
                    "price": 58.0,
                    "is_recommended": True,
                    "is_available": True,
                    "cuisine_type": "川味麻辣",
                    "flavor_profile": "麻辣",
                    "tags": ["招牌", "下饭"],
                    "ingredients": ["牛肉", "豆芽", "花椒"],
                    "allergens": [],
                    "cooking_method": "水煮",
                },
                {
                    "id": 102,
                    "merchant_id": 1,
                    "name": "酸菜鱼",
                    "description": "酸辣开胃，鱼肉鲜嫩",
                    "price": 68.0,
                    "is_recommended": False,
                    "is_available": True,
                    "cuisine_type": "川味麻辣",
                    "flavor_profile": "酸辣",
                    "tags": ["招牌"],
                    "ingredients": ["鱼片", "酸菜", "辣椒"],
                    "allergens": [],
                    "cooking_method": "水煮",
                },
            ]
        if merchant_id == 2:
            return [
                {
                    "id": 201,
                    "merchant_id": 2,
                    "name": "蜜汁叉烧饭",
                    "description": "港式经典叉烧，甜而不腻",
                    "price": 32.0,
                    "is_recommended": True,
                    "is_available": True,
                    "cuisine_type": "粤式烧腊",
                    "flavor_profile": "甜咸",
                    "tags": ["烧腊", "招牌"],
                    "ingredients": ["猪肉", "蜜汁"],
                    "allergens": [],
                    "cooking_method": "烤制",
                },
            ]
        return []


class EmptyCatalog:
    def list_merchants(self) -> list[dict]:
        return []

    def list_dishes_by_merchant(self, merchant_id: int) -> list[dict]:
        return []


def _plan(query: str, source_types=None) -> RagQueryPlan:
    return RagQueryPlan(
        original_query=query,
        normalized_query=query,
        expansion_queries=[],
        source_types=source_types or ["dish", "merchant"],
    )


class TestSparseVectorRecallRoute:
    def test_build_index_and_basic_recall(self) -> None:
        route = SparseVectorRecallRoute(StubCatalog())
        candidates = route.recall(_plan("川味 麻辣"), limit=5)

        assert len(candidates) >= 1
        scores = [c.score for c in candidates]
        assert all(0.0 <= s <= 1.0 for s in scores), f"scores out of [0,1]: {scores}"
        assert candidates[0].score >= candidates[-1].score

    def test_all_candidates_have_sparse_route(self) -> None:
        route = SparseVectorRecallRoute(StubCatalog())
        candidates = route.recall(_plan("水煮牛肉"), limit=5)

        assert len(candidates) >= 1
        for c in candidates:
            assert c.route == "sparse", f"expected sparse, got {c.route}"

    def test_recall_filters_by_source_type(self) -> None:
        route = SparseVectorRecallRoute(StubCatalog())
        candidates = route.recall(_plan("叉烧", source_types=["dish"]), limit=10)

        for c in candidates:
            assert c.source_type == "dish", f"expected dish, got {c.source_type}"

    def test_recall_limits_results(self) -> None:
        route = SparseVectorRecallRoute(StubCatalog())
        candidates = route.recall(_plan("麻辣"), limit=2)

        assert len(candidates) <= 2

    def test_empty_catalog_returns_empty(self) -> None:
        route = SparseVectorRecallRoute(EmptyCatalog())
        candidates = route.recall(_plan("川味"), limit=5)

        assert candidates == []

    def test_empty_query_returns_empty(self) -> None:
        route = SparseVectorRecallRoute(StubCatalog())
        plan = RagQueryPlan(
            original_query="",
            normalized_query="",
            expansion_queries=[],
        )
        candidates = route.recall(plan, limit=5)
        assert candidates == []

    def test_expansion_queries_used(self) -> None:
        route = SparseVectorRecallRoute(StubCatalog())
        plan = RagQueryPlan(
            original_query="找菜",
            normalized_query="找菜",
            expansion_queries=["水煮牛肉", "蜜汁叉烧"],
        )
        candidates = route.recall(plan, limit=10)

        found_dish_names = {c.facts.get("dish_name", "") for c in candidates}
        assert "水煮牛肉" in found_dish_names or "蜜汁叉烧饭" in found_dish_names

    def test_score_normalization(self) -> None:
        route = SparseVectorRecallRoute(StubCatalog())
        candidates = route.recall(_plan("麻辣"), limit=5)

        if candidates:
            assert max(c.score for c in candidates) == pytest.approx(1.0, abs=1e-9)

    def test_stable_key_format(self) -> None:
        route = SparseVectorRecallRoute(StubCatalog())
        candidates = route.recall(_plan("牛肉"), limit=5)

        for c in candidates:
            key = c.stable_key
            assert key.startswith("dish:") or key.startswith("merchant:"), f"bad key: {key}"
            assert int(key.split(":")[1]) > 0


class TestSparseLexicalScoreInFusion:
    def test_fusion_sets_lexical_score_from_sparse_route(self) -> None:
        route = SparseVectorRecallRoute(StubCatalog())
        sparse_candidates = route.recall(_plan("水煮牛肉"), limit=5)

        fused: list[FusedCandidate] = reciprocal_rank_fusion(
            [[], sparse_candidates], limit=50
        )

        assert len(fused) >= 1
        for item in fused:
            assert item.lexical_score > 0.0, (
                f"lexical_score should be >0 for sparse candidates, "
                f"got {item.lexical_score} (key={item.stable_key})"
            )

    def test_fusion_preserves_sparse_route_scores(self) -> None:
        route = SparseVectorRecallRoute(StubCatalog())
        sparse_candidates = route.recall(_plan("叉烧"), limit=5)

        fused: list[FusedCandidate] = reciprocal_rank_fusion(
            [[], sparse_candidates], limit=50
        )

        for item in fused:
            assert "sparse" in item.route_scores, (
                f"missing sparse in route_scores for {item.stable_key}"
            )
            assert item.route_scores["sparse"] > 0

    def test_sparse_sql_both_contribute_to_lexical_score(self) -> None:
        route = SparseVectorRecallRoute(StubCatalog())
        sparse = route.recall(_plan("水煮牛肉"), limit=5)

        sql = [
            RecallCandidate(
                stable_key="dish:101",
                source_type="dish",
                source_id=101,
                route="sql",
                rank=1,
                score=0.3,
                facts={"dish_id": 101, "dish_name": "水煮牛肉"},
                citation="",
            ),
        ]

        fused: list[FusedCandidate] = reciprocal_rank_fusion([sql, sparse], limit=50)

        dish_101 = next((f for f in fused if f.stable_key == "dish:101"), None)
        assert dish_101 is not None
        assert dish_101.lexical_score >= 0.3
