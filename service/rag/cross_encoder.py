from __future__ import annotations

import logging
import math
import os
import threading

from langsmith import traceable

from service.rag.models import FusedCandidate

logger = logging.getLogger(__name__)

# ── Singleton for local cross-encoder model ──────────────────────────────

_DEFAULT_RERANKER_MODEL = "BAAI/bge-reranker-v2-m3"

_reranker_lock = threading.Lock()
_reranker_instance: _LocalCrossEncoder | None = None  # type: ignore[name-defined]


class CrossEncoderReranker:
    def __init__(self, scorer=None) -> None:
        self._scorer = scorer or _get_local_cross_encoder()

    @traceable(name="cross_encoder_rerank")
    def rerank(self, query: str, candidates: list[FusedCandidate], top_k: int = 10) -> list[FusedCandidate]:
        if not candidates:
            return []

        texts = [self._candidate_to_text(candidate) for candidate in candidates]
        scores = self._score_texts(query, texts)
        for candidate, score in zip(candidates, scores):
            candidate.cross_encoder_score = score

        scored = sorted(candidates, key=lambda c: c.cross_encoder_score, reverse=True)
        return scored[:top_k]

    def _score_texts(self, query: str, texts: list[str]) -> list[float]:
        """Score all texts against the query in a single batched call when the
        scorer supports it, falling back to per-item scoring otherwise.

        Batching is the key cost win for the real model (one forward pass for
        the whole pool instead of one per candidate). Scorers that only
        implement ``score`` (e.g. test doubles, simple custom scorers) still
        work via the per-item path, which also isolates per-candidate errors.
        """
        score_batch = getattr(self._scorer, "score_batch", None)
        if callable(score_batch):
            try:
                return list(score_batch(query, texts))
            except Exception:
                logger.warning(
                    "Cross-encoder batch scoring failed; falling back to per-item",
                    exc_info=True,
                )

        scores: list[float] = []
        for text in texts:
            try:
                scores.append(self._scorer.score(query, text))
            except Exception:
                logger.warning("Cross-encoder scoring failed", exc_info=True)
                scores.append(0.0)
        return scores

    @staticmethod
    def _candidate_to_text(candidate: FusedCandidate) -> str:
        facts = candidate.facts
        parts = [
            str(facts.get("dish_name", "")),
            str(facts.get("merchant_name", "")),
            str(facts.get("cuisine_type", "")),
            str(facts.get("flavor_profile", "")),
            str(facts.get("description", "")),
            candidate.citation,
        ]
        return " ".join(part for part in parts if part)


# ── Local cross-encoder scorer ───────────────────────────────────────────


class _LocalCrossEncoder:
    """Scores (query, text) relevance using a local cross-encoder model.

    Uses ``sentence_transformers.CrossEncoder`` to load ``BAAI/bge-reranker-v2-m3``.
    Raw logits are passed through sigmoid to produce a score in [0, 1].

    The model is loaded **lazily** on first ``score()`` call, so constructing
    the object is cheap and won't fail in test environments without
    the real model installed.
    """

    def __init__(self, model_name: str | None = None) -> None:
        self.model_name = model_name or os.getenv(
            "RERANKER_MODEL", _DEFAULT_RERANKER_MODEL
        )
        self._model = None
        self._device: str | None = None
        self._model_lock = threading.Lock()

    def _ensure_model(self) -> None:
        if self._model is not None:
            return
        with self._model_lock:
            if self._model is None:
                from sentence_transformers import CrossEncoder

                from service.torch_device import resolve_device

                self._device = resolve_device("RERANKER_DEVICE")
                self._model = CrossEncoder(self.model_name, device=self._device)
                logger.info(
                    "Loaded cross-encoder model: %s (device=%s)",
                    self.model_name, self._device,
                )

    def score(self, query: str, text: str) -> float:
        """Return relevance score in [0, 1] for a (query, text) pair."""
        self._ensure_model()
        logit = self._model.predict([(query, text)])[0]
        return _sigmoid(float(logit))

    def score_batch(self, query: str, texts: list[str]) -> list[float]:
        """Score multiple texts against a single query (more efficient)."""
        if not texts:
            return []
        self._ensure_model()
        pairs = [(query, t) for t in texts]
        logits = self._model.predict(pairs)
        return [_sigmoid(float(s)) for s in logits]


def _sigmoid(x: float) -> float:
    """Numerically stable sigmoid."""
    if x >= 0:
        return 1.0 / (1.0 + math.exp(-x))
    exp_x = math.exp(x)
    return exp_x / (1.0 + exp_x)


def _get_local_cross_encoder() -> _LocalCrossEncoder:
    """Return the module-level singleton, creating it on first call."""
    global _reranker_instance  # noqa: PLW0603
    if _reranker_instance is not None:
        return _reranker_instance
    with _reranker_lock:
        if _reranker_instance is None:
            _reranker_instance = _LocalCrossEncoder()
    return _reranker_instance


def reset_cross_encoder() -> None:
    """Tear down the singleton (useful in tests)."""
    global _reranker_instance  # noqa: PLW0603
    _reranker_instance = None
