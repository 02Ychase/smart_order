from pathlib import Path
import sys
from unittest.mock import MagicMock

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from service.query_refiner import QueryRefiner


def test_refiner_extracts_searchable_keywords(monkeypatch) -> None:
    def mock_call_llm(query: str, system_instruction: str) -> str:
        return '{"refined_query": "下饭 川菜 口味重 米饭搭档"}'

    monkeypatch.setattr("service.query_refiner.call_llm", mock_call_llm)
    refiner = QueryRefiner()
    result = refiner.refine("想吃下饭一点的川菜")

    assert result == "下饭 川菜 口味重 米饭搭档"


def test_refiner_falls_back_to_original_on_llm_failure(monkeypatch) -> None:
    def mock_call_llm(query: str, system_instruction: str) -> str:
        raise RuntimeError("LLM error")

    monkeypatch.setattr("service.query_refiner.call_llm", mock_call_llm)
    refiner = QueryRefiner()
    result = refiner.refine("想吃下饭一点的川菜")

    assert result == "想吃下饭一点的川菜"


def test_refiner_falls_back_when_no_model_configured(monkeypatch) -> None:
    monkeypatch.setenv("MODEL_NAME", "")
    refiner = QueryRefiner()
    result = refiner.refine("推荐几个湘菜")

    assert result == "推荐几个湘菜"
