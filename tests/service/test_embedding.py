"""Tests for service.embedding — centralized local embedding service."""

import sys
from unittest.mock import ANY, MagicMock, patch

import numpy as np

from service.embedding import (
    DEFAULT_DIMENSION,
    DEFAULT_MODEL_NAME,
    reset_embedding_service,
)


def _make_mock_st_module():
    """Create a mock sentence_transformers module for sys.modules injection."""
    mock_module = MagicMock()
    return mock_module


def _fresh_service(mock_module=None, **kwargs):
    """Create an EmbeddingService with a mocked SentenceTransformer."""
    from service.embedding import EmbeddingService

    reset_embedding_service()
    if mock_module is None:
        mock_module = _make_mock_st_module()

    with patch.dict(sys.modules, {"sentence_transformers": mock_module}):
        svc = EmbeddingService(**kwargs)

    # svc._model == mock_module.SentenceTransformer.return_value
    mock_model = mock_module.SentenceTransformer.return_value
    return svc, mock_model, mock_module


# ── Constants ────────────────────────────────────────────────────────────


def test_default_dimension_is_1024() -> None:
    assert DEFAULT_DIMENSION == 1024


def test_default_model_is_bge_m3() -> None:
    assert DEFAULT_MODEL_NAME == "BAAI/bge-m3"


def test_module_defaults_hf_offline_when_unset(monkeypatch) -> None:
    """Importing the embedding module should default HF to offline mode when
    the env vars are unset (models are cached, hub access restricted)."""
    import importlib
    import os

    import service.embedding as embedding_module

    monkeypatch.delenv("HF_HUB_OFFLINE", raising=False)
    monkeypatch.delenv("TRANSFORMERS_OFFLINE", raising=False)
    importlib.reload(embedding_module)

    assert os.environ.get("HF_HUB_OFFLINE") == "1"
    assert os.environ.get("TRANSFORMERS_OFFLINE") == "1"


def test_explicit_hf_online_is_respected(monkeypatch) -> None:
    """An explicit HF_HUB_OFFLINE=0 must not be overridden by the default."""
    import importlib
    import os

    import service.embedding as embedding_module

    monkeypatch.setenv("HF_HUB_OFFLINE", "0")
    importlib.reload(embedding_module)

    assert os.environ.get("HF_HUB_OFFLINE") == "0"


# ── embed / embed_batch ──────────────────────────────────────────────────


def test_embed_returns_list_of_floats() -> None:
    svc, mock_model, _ = _fresh_service()
    fake_vector = np.array([0.1] * DEFAULT_DIMENSION, dtype=np.float32)
    mock_model.encode.return_value = fake_vector

    result = svc.embed("宫保鸡丁")

    assert isinstance(result, list)
    assert len(result) == DEFAULT_DIMENSION
    assert all(isinstance(v, float) for v in result)


def test_embed_batch_returns_list_of_vectors() -> None:
    svc, mock_model, _ = _fresh_service()
    fake_vectors = np.array([[0.1] * DEFAULT_DIMENSION] * 3, dtype=np.float32)
    mock_model.encode.return_value = fake_vectors

    result = svc.embed_batch(["a", "b", "c"])

    assert len(result) == 3
    assert all(len(v) == DEFAULT_DIMENSION for v in result)


def test_embed_batch_empty_input() -> None:
    svc, _, _ = _fresh_service()
    result = svc.embed_batch([])
    assert result == []


def test_encode_called_with_normalize() -> None:
    svc, mock_model, _ = _fresh_service()
    fake_vector = np.array([0.1] * DEFAULT_DIMENSION, dtype=np.float32)
    mock_model.encode.return_value = fake_vector

    svc.embed("test")

    mock_model.encode.assert_called_once_with("test", normalize_embeddings=True)


# ── Singleton ────────────────────────────────────────────────────────────


def test_singleton_returns_same_instance() -> None:
    from service.embedding import get_embedding_service

    reset_embedding_service()
    mock_module = _make_mock_st_module()

    with patch.dict(sys.modules, {"sentence_transformers": mock_module}):
        svc1 = get_embedding_service()
        svc2 = get_embedding_service()

    assert svc1 is svc2
    reset_embedding_service()


def test_reset_clears_singleton() -> None:
    from service.embedding import get_embedding_service

    reset_embedding_service()
    mock_module = _make_mock_st_module()

    with patch.dict(sys.modules, {"sentence_transformers": mock_module}):
        svc1 = get_embedding_service()
        reset_embedding_service()
        svc2 = get_embedding_service()

    assert svc1 is not svc2
    reset_embedding_service()


# ── Config override ──────────────────────────────────────────────────────


def test_custom_model_name_via_env(monkeypatch) -> None:
    reset_embedding_service()

    monkeypatch.setenv("EMBEDDING_MODEL", "custom/model")
    monkeypatch.setenv("EMBEDDING_DIMENSION", "768")

    svc, _, mock_module = _fresh_service()

    assert svc.model_name == "custom/model"
    assert svc.dimension == 768
    # device is resolved at load time (cpu/cuda); assert it is passed through.
    mock_module.SentenceTransformer.assert_called_once_with("custom/model", device=ANY)
    reset_embedding_service()
