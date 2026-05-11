from __future__ import annotations

import logging
import os
from http import HTTPStatus

from service.rag.models import FusedCandidate

logger = logging.getLogger(__name__)


class CrossEncoderReranker:
    def __init__(self, scorer=None) -> None:
        self._scorer = scorer or _DashScopeReranker()

    def rerank(self, query: str, candidates: list[FusedCandidate], top_k: int = 10) -> list[FusedCandidate]:
        if not candidates:
            return []

        for candidate in candidates:
            text = self._candidate_to_text(candidate)
            try:
                score = self._scorer.score(query, text)
            except Exception:
                logger.warning("Cross-encoder scoring failed for %s", candidate.stable_key, exc_info=True)
                score = 0.0
            candidate.cross_encoder_score = score

        scored = sorted(candidates, key=lambda c: c.cross_encoder_score, reverse=True)
        return scored[:top_k]

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


class _DashScopeReranker:
    def __init__(self):
        import dashscope
        self._dashscope = dashscope
        self._api_key = os.getenv("DASHSCOPE_API_KEY")
        self._model = "gte-rerank"

    def score(self, query: str, text: str) -> float:
        if not self._api_key:
            return 0.0
        try:
            resp = self._dashscope.TextReRank.call(
                model=self._model,
                query=query,
                documents=[text],
                api_key=self._api_key,
            )
            if resp.status_code == HTTPStatus.OK:
                results = resp.output.get("results", [])
                if results:
                    return float(results[0].get("relevance_score", 0.0))
            return 0.0
        except Exception:
            logger.warning("DashScope rerank API call failed", exc_info=True)
            return 0.0
