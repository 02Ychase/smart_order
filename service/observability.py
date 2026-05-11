from __future__ import annotations

import logging
import time
from contextlib import contextmanager
from typing import Any

logger = logging.getLogger("smart_order.metrics")


class MetricsCollector:
    def __init__(self) -> None:
        self._timings: dict[str, float] = {}
        self._counters: dict[str, int] = {}
        self._metadata: dict[str, Any] = {}

    def record_timing(self, name: str, duration: float) -> None:
        self._timings[name] = duration

    @contextmanager
    def timer(self, name: str):
        start = time.perf_counter()
        try:
            yield
        finally:
            self._timings[name] = time.perf_counter() - start

    def increment(self, name: str, amount: int = 1) -> None:
        self._counters[name] = self._counters.get(name, 0) + amount

    def set_metadata(self, key: str, value: Any) -> None:
        self._metadata[key] = value

    def get_metrics(self) -> dict[str, Any]:
        return {**self._timings, **self._counters}

    def get_metadata(self) -> dict[str, Any]:
        return dict(self._metadata)

    def to_log_dict(self) -> dict[str, Any]:
        return {
            "timings": dict(self._timings),
            "counters": dict(self._counters),
            "metadata": dict(self._metadata),
        }

    def emit(self, event_name: str = "agent_turn") -> None:
        logger.info(
            "%s %s",
            event_name,
            self.to_log_dict(),
        )
