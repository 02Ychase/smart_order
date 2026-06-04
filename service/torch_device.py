"""Resolve the torch device for local model inference.

Centralizes the "use the GPU when available" decision so the embedding model
and the cross-encoder pick the same device and can be overridden per
deployment without code changes.
"""
from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)


def resolve_device(env_var: str | None = None) -> str:
    """Return the torch device string for model inference.

    - If ``env_var`` is given and set to a non-empty value, it is used verbatim
      (e.g. ``"cpu"``, ``"cuda"``, ``"cuda:0"``) — an explicit deployment
      override.
    - Otherwise auto-detect: ``"cuda"`` when a CUDA device is available, else
      ``"cpu"``.
    """
    if env_var:
        override = os.getenv(env_var)
        if override and override.strip():
            return override.strip()

    try:
        import torch

        if torch.cuda.is_available():
            return "cuda"
    except Exception:  # noqa: BLE001 - torch missing / probe failure → cpu
        logger.debug("CUDA probe failed; falling back to cpu", exc_info=True)

    return "cpu"
