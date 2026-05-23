"""Centralized embedding service using a local model (BAAI/bge-m3).

Provides a singleton ``EmbeddingService`` that loads the model once and
is shared across all consumers (AssistantVectorStore, PineconeVectorDB,
WeightedReranker, etc.).

Usage::

    from service.embedding import get_embedding_service

    svc = get_embedding_service()
    vector = svc.embed("宫保鸡丁")           # single text
    vectors = svc.embed_batch(["a", "b"])    # batch
"""
from __future__ import annotations

import logging
import os
import threading

logger = logging.getLogger(__name__)

DEFAULT_MODEL_NAME = "BAAI/bge-m3"
DEFAULT_DIMENSION = 1024

_lock = threading.Lock()
_instance: EmbeddingService | None = None


class EmbeddingService:
    """Local embedding service backed by *sentence-transformers*."""

    def __init__(
        self,
        model_name: str | None = None,
        dimension: int | None = None,
    ) -> None:
        self.model_name = model_name or os.getenv(
            "EMBEDDING_MODEL", DEFAULT_MODEL_NAME
        )
        self.dimension = dimension or int(
            os.getenv("EMBEDDING_DIMENSION", str(DEFAULT_DIMENSION))
        )

        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(self.model_name)
        logger.info(
            "Loaded embedding model: %s (dim=%d)", self.model_name, self.dimension
        )

    # ── public API ────────────────────────────────────────────────────

    def embed(self, text: str) -> list[float]:
        """Embed a single text string. Returns a normalised vector."""
        vector = self._model.encode(text, normalize_embeddings=True)
        return vector.tolist()

    def embed_batch(
        self, texts: list[str], batch_size: int = 32
    ) -> list[list[float]]:
        """Embed multiple texts in one call. Returns list of normalised vectors."""
        if not texts:
            return []
        vectors = self._model.encode(
            texts, normalize_embeddings=True, batch_size=batch_size
        )
        return [v.tolist() for v in vectors]


def get_embedding_service() -> EmbeddingService:
    """Return the module-level singleton, creating it on first call."""
    global _instance  # noqa: PLW0603
    if _instance is not None:
        return _instance
    with _lock:
        if _instance is None:
            _instance = EmbeddingService()
    return _instance


def reset_embedding_service() -> None:
    """Tear down the singleton (useful in tests)."""
    global _instance  # noqa: PLW0603
    _instance = None
