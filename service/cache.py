from __future__ import annotations

import threading
from collections import OrderedDict
from typing import Any


class TieredCache:
    def __init__(self, l1_max_size: int = 2048) -> None:
        self._l1: OrderedDict[str, Any] = OrderedDict()
        self._l1_max = l1_max_size
        self._lock = threading.Lock()
        self._l1_hits = 0
        self._l1_misses = 0

    def get(self, key: str) -> Any | None:
        with self._lock:
            if key in self._l1:
                self._l1.move_to_end(key)
                self._l1_hits += 1
                return self._l1[key]
            self._l1_misses += 1
            return None

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            if key in self._l1:
                self._l1.move_to_end(key)
                self._l1[key] = value
            else:
                while len(self._l1) >= self._l1_max:
                    self._l1.popitem(last=False)
                self._l1[key] = value

    def stats(self) -> dict[str, int]:
        with self._lock:
            return {
                "l1_size": len(self._l1),
                "l1_hits": self._l1_hits,
                "l1_misses": self._l1_misses,
            }

    def clear(self) -> None:
        with self._lock:
            self._l1.clear()
            self._l1_hits = 0
            self._l1_misses = 0
