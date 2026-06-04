"""Startup warmup for heavy, lazily-loaded components.

The embedding model, the cross-encoder model and the BM25 index all load
lazily on first use, so without warmup the *first* real user request pays the
cold-start cost (model load + index build). This module preloads them at
application startup (FastAPI lifespan) so steady-state latency starts from the
first request.

Everything here is best-effort: a failure to warm up (missing model, no DB,
offline) is logged and never crashes startup — the component will simply load
lazily later as before.
"""
from __future__ import annotations

import logging
import os
import sys

logger = logging.getLogger(__name__)


def should_warmup() -> bool:
    """Whether to run startup warmup.

    Controlled by ``ASSISTANT_WARMUP`` (``0/false/no/off`` disables). When the
    variable is unset, warmup runs by default **except** under pytest, so the
    test suite never loads the heavy models.
    """
    val = os.getenv("ASSISTANT_WARMUP")
    if val is not None:
        return val.strip().lower() not in ("0", "false", "no", "off", "")
    return "pytest" not in sys.modules


def run_startup_warmup() -> dict[str, bool]:
    """Preload heavy components. Returns a per-component success map and never
    raises."""
    results: dict[str, bool] = {}
    for name, fn in (
        ("embedding", _warmup_embedding),
        ("cross_encoder", _warmup_cross_encoder),
        ("bm25", _warmup_bm25),
    ):
        try:
            results[name] = fn()
        except Exception:  # noqa: BLE001 - warmup must never crash startup
            logger.warning("Warmup step %s raised", name, exc_info=True)
            results[name] = False

    logger.info("Startup warmup complete: %s", results)
    return results


def _warmup_embedding() -> bool:
    from service.embedding import get_embedding_service

    get_embedding_service().embed("预热")
    return True


def _warmup_cross_encoder() -> bool:
    from service.rag.cross_encoder import CrossEncoderReranker
    from service.rag.models import FusedCandidate

    dummy = FusedCandidate(
        stable_key="warmup:0",
        source_type="dish",
        source_id=0,
        facts={"dish_name": "预热"},
        citation="预热",
    )
    CrossEncoderReranker().rerank("预热", [dummy], top_k=1)
    return True


def _warmup_bm25() -> bool:
    from service.assistant_service import _get_shared_sparse_route

    route = _get_shared_sparse_route(catalog_service=None)
    return bool(getattr(route, "_built", False))
