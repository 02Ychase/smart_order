from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from service.assistant_models import AssistantParsedQuery
from service.assistant_retriever import AssistantRetriever


def _make_mock_catalog(merchants, dishes_by_merchant):
    mock = MagicMock()
    mock.list_merchants.return_value = merchants
    mock.list_dishes_by_merchant.side_effect = lambda mid: dishes_by_merchant.get(mid, [])
    return mock


def test_hybrid_retriever_uses_query_refiner(monkeypatch) -> None:
    """Should use QueryRefiner to convert user message to refined query."""

    def mock_refiner(message: str) -> str:
        return "下饭 川菜"

    monkeypatch.setattr("service.assistant_retriever.QueryRefiner", lambda: SimpleNamespace(refine=mock_refiner))

    parsed = AssistantParsedQuery(
        raw_message="想吃下饭一点的川菜",
        query_type="recommendation",
        cuisine_types=["川菜"],
    )

    mock_catalog = _make_mock_catalog(
        merchants=[{"id": 1, "name": "川菜馆", "rating": 4.5, "merchant_tags": ["川菜"], "business_hours": "10:00-22:00", "description": "正宗川菜"}],
        dishes_by_merchant={
            1: [
                {"id": 11, "name": "鱼香肉丝", "price": 28.0, "cuisine_type": "川菜", "flavor_profile": "酸甜微辣", "ingredients": ["猪肉", "木耳"], "allergens": [], "description": "下饭神器"},
            ]
        },
    )
    monkeypatch.setattr("service.assistant_retriever.CatalogService", lambda session: mock_catalog)

    retriever = AssistantRetriever(MagicMock())

    with patch.object(retriever.vector_store, "semantic_search", return_value=[]) as mock_search:
        with patch.object(retriever.vector_store, "is_ready", return_value=True):
            retriever.retrieve(parsed)

    mock_search.assert_called_once()
    call_args = mock_search.call_args
    assert "下饭" in call_args[0][0], "should use refined query"


def test_hybrid_retriever_applies_hard_constraints_as_post_filter(monkeypatch) -> None:
    """Should filter vector results by hard constraints (budget, allergens)."""

    def mock_refiner(message: str) -> str:
        return "川菜"

    monkeypatch.setattr("service.assistant_retriever.QueryRefiner", lambda: SimpleNamespace(refine=mock_refiner))

    parsed = AssistantParsedQuery(
        raw_message="推荐川菜",
        query_type="recommendation",
        cuisine_types=["川菜"],
        budget_max=100.0,
        party_size=2,
        exclude_allergens=["花生"],
    )

    mock_vector_results = [
        {"id": "dish_11", "score": 0.92, "metadata": {"dish_id": 11, "price": 28.0, "cuisine_type": "川菜"}},
        {"id": "dish_12", "score": 0.85, "metadata": {"dish_id": 12, "price": 60.0, "cuisine_type": "川菜"}},
        {"id": "dish_13", "score": 0.88, "metadata": {"dish_id": 13, "price": 28.0, "cuisine_type": "川菜"}},
    ]

    mock_catalog = _make_mock_catalog(
        merchants=[{"id": 1, "name": "川菜馆", "rating": 4.5, "merchant_tags": ["川菜"], "business_hours": "10:00-22:00", "description": "正宗川菜"}],
        dishes_by_merchant={
            1: [
                {"id": 11, "name": "鱼香肉丝", "price": 28.0, "cuisine_type": "川菜", "flavor_profile": "酸甜微辣", "ingredients": ["猪肉", "木耳"], "allergens": [], "description": "下饭"},
                {"id": 12, "name": "宫保鸡丁", "price": 60.0, "cuisine_type": "川菜", "flavor_profile": "麻辣", "ingredients": ["鸡肉", "花生"], "allergens": ["花生"], "description": "经典"},
                {"id": 13, "name": "麻婆豆腐", "price": 28.0, "cuisine_type": "川菜", "flavor_profile": "麻辣", "ingredients": ["豆腐"], "allergens": ["花生"], "description": "嫩滑"},
            ]
        },
    )
    monkeypatch.setattr("service.assistant_retriever.CatalogService", lambda session: mock_catalog)

    retriever = AssistantRetriever(MagicMock())

    with patch.object(retriever.vector_store, "semantic_search", return_value=mock_vector_results):
        with patch.object(retriever.vector_store, "is_ready", return_value=True):
            candidates = retriever.retrieve(parsed)

    # dish_11: 28*2=56 <= 100, no allergen -> pass
    # dish_12: 60*2=120 > 100 -> filtered by budget
    # dish_13: 28*2=56 <= 100, but has allergen 花生 -> filtered by allergen
    dish_ids = [c.dish_id for c in candidates]
    assert 11 in dish_ids
    assert 12 not in dish_ids
    assert 13 not in dish_ids


def test_hybrid_retriever_reranks_by_combined_score(monkeypatch) -> None:
    """Should combine vector semantic score with business signals for re-ranking."""

    def mock_refiner(message: str) -> str:
        return "推荐"

    monkeypatch.setattr("service.assistant_retriever.QueryRefiner", lambda: SimpleNamespace(refine=mock_refiner))

    parsed = AssistantParsedQuery(
        raw_message="推荐几个菜",
        query_type="recommendation",
    )

    mock_vector_results = [
        {"id": "dish_11", "score": 0.95, "metadata": {"dish_id": 11, "price": 28.0, "cuisine_type": "川菜"}},
        {"id": "dish_12", "score": 0.85, "metadata": {"dish_id": 12, "price": 28.0, "cuisine_type": "川菜"}},
        {"id": "dish_13", "score": 0.90, "metadata": {"dish_id": 13, "price": 28.0, "cuisine_type": "川菜"}},
    ]

    mock_catalog = _make_mock_catalog(
        merchants=[{"id": 1, "name": "川菜馆", "rating": 4.5, "merchant_tags": ["川菜"], "business_hours": "10:00-22:00", "description": "正宗川菜"}],
        dishes_by_merchant={
            1: [
                {"id": 11, "name": "鱼香肉丝", "price": 28.0, "cuisine_type": "川菜", "flavor_profile": "酸甜微辣", "ingredients": ["猪肉", "木耳"], "allergens": [], "description": "下饭"},
                {"id": 12, "name": "宫保鸡丁", "price": 28.0, "cuisine_type": "川菜", "flavor_profile": "麻辣", "ingredients": ["鸡肉", "花生"], "allergens": ["花生"], "description": "经典"},
                {"id": 13, "name": "麻婆豆腐", "price": 28.0, "cuisine_type": "川菜", "flavor_profile": "麻辣", "ingredients": ["豆腐"], "allergens": [], "description": "嫩滑"},
            ]
        },
    )
    monkeypatch.setattr("service.assistant_retriever.CatalogService", lambda session: mock_catalog)

    retriever = AssistantRetriever(MagicMock())

    with patch.object(retriever.vector_store, "semantic_search", return_value=mock_vector_results):
        with patch.object(retriever.vector_store, "is_ready", return_value=True):
            candidates = retriever.retrieve(parsed)

    # Check that candidates are returned and have reasonable scores
    assert len(candidates) <= 3
    # Top candidate should have highest score due to re-ranking
    if len(candidates) > 1:
        assert candidates[0].score >= candidates[1].score
