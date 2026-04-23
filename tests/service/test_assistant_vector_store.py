from pathlib import Path
import sys
from unittest.mock import MagicMock, patch

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.assistant_vector_store import AssistantVectorStore


def test_vector_store_is_ready_when_both_client_and_index_exist(monkeypatch) -> None:
    monkeypatch.setenv("PINECONE_API_KEY", "test-key")
    monkeypatch.setenv("PINECONE_ASSISTANT_INDEX", "test-index")

    mock_index = MagicMock()
    mock_pc = MagicMock()
    mock_pc.Index.return_value = mock_index

    with patch("tools.assistant_vector_store.Pinecone", return_value=mock_pc):
        store = AssistantVectorStore()

    assert store.is_ready() is True


def test_vector_store_is_not_ready_when_no_api_key(monkeypatch) -> None:
    monkeypatch.delenv("PINECONE_API_KEY", raising=False)
    store = AssistantVectorStore()
    assert store.is_ready() is False


def test_semantic_search_returns_candidates(monkeypatch) -> None:
    monkeypatch.setenv("PINECONE_API_KEY", "test-key")
    monkeypatch.setenv("PINECONE_ASSISTANT_INDEX", "test-index")
    monkeypatch.setenv("DASHSCOPE_API_KEY", "test-ds-key")

    mock_index = MagicMock()
    mock_index.query.return_value = {
        "matches": [
            {
                "id": "dish_11",
                "score": 0.92,
                "metadata": {
                    "source_type": "dish",
                    "source_id": 11,
                    "merchant_id": 1,
                    "dish_name": "鱼香肉丝",
                    "price": 28.0,
                    "cuisine_type": "川菜",
                },
            }
        ]
    }
    mock_pc = MagicMock()
    mock_pc.Index.return_value = mock_index

    fake_embedding = [0.1] * 1536
    mock_resp = MagicMock()
    mock_resp.__getitem__ = lambda self, key: {"status_code": 200}[key] if key == "status_code" else None
    mock_resp.get.side_effect = lambda key, default=None: {
        "output": {"embeddings": [{"embedding": fake_embedding}]}
    }.get(key, default)

    with patch("tools.assistant_vector_store.Pinecone", return_value=mock_pc):
        with patch("tools.assistant_vector_store.dashscope.TextEmbedding.call", return_value=mock_resp):
            store = AssistantVectorStore()
            results = store.semantic_search("下饭川菜", top_k=3)

    assert len(results) == 1
    assert results[0]["id"] == "dish_11"
    assert results[0]["score"] == 0.92
    assert results[0]["metadata"]["dish_name"] == "鱼香肉丝"


def test_semantic_search_returns_empty_on_embedding_failure(monkeypatch) -> None:
    monkeypatch.setenv("PINECONE_API_KEY", "test-key")
    monkeypatch.setenv("PINECONE_ASSISTANT_INDEX", "test-index")
    monkeypatch.setenv("DASHSCOPE_API_KEY", "test-ds-key")

    mock_index = MagicMock()
    mock_pc = MagicMock()
    mock_pc.Index.return_value = mock_index

    with patch("tools.assistant_vector_store.Pinecone", return_value=mock_pc):
        with patch("tools.assistant_vector_store.dashscope.TextEmbedding.call", return_value=None):
            store = AssistantVectorStore()
            results = store.semantic_search("query", top_k=3)

    assert results == []


def test_upsert_candidates_batches_vectors(monkeypatch) -> None:
    monkeypatch.setenv("PINECONE_API_KEY", "test-key")
    monkeypatch.setenv("PINECONE_ASSISTANT_INDEX", "test-index")
    monkeypatch.setenv("DASHSCOPE_API_KEY", "test-ds-key")

    mock_index = MagicMock()
    mock_pc = MagicMock()
    mock_pc.Index.return_value = mock_index

    fake_embedding = [0.1] * 1536
    mock_resp = MagicMock()
    mock_resp.__getitem__ = lambda self, key: {"status_code": 200}[key] if key == "status_code" else None
    mock_resp.get.side_effect = lambda key, default=None: {
        "output": {"embeddings": [{"embedding": fake_embedding}]}
    }.get(key, default)

    candidates = [
        {
            "id": "dish_11",
            "text": "鱼香肉丝 川菜",
            "metadata": {"source_type": "dish", "source_id": 11},
        },
        {
            "id": "merchant_1",
            "text": "兰姨小炒 家常热炒",
            "metadata": {"source_type": "merchant", "source_id": 1},
        },
    ]

    with patch("tools.assistant_vector_store.Pinecone", return_value=mock_pc):
        with patch("tools.assistant_vector_store.dashscope.TextEmbedding.call", return_value=mock_resp):
            store = AssistantVectorStore()
            store.upsert_candidates(candidates, batch_size=1)

    assert mock_index.upsert.call_count == 2
