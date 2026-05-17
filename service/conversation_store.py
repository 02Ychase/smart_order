from __future__ import annotations

import threading
from collections import OrderedDict
from typing import Any

from langchain_core.messages import BaseMessage


class InMemoryConversationStore:
    def __init__(self, max_messages: int = 20, max_sessions: int = 1000) -> None:
        self._max_messages = max_messages
        self._max_sessions = max_sessions
        self._store: OrderedDict[str, list[BaseMessage]] = OrderedDict()
        self._metadata: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()

    def append(self, session_id: str, message: BaseMessage) -> None:
        with self._lock:
            if session_id not in self._store:
                if len(self._store) >= self._max_sessions:
                    evicted_key, _ = self._store.popitem(last=False)
                    self._metadata.pop(evicted_key, None)
                self._store[session_id] = []
            self._store[session_id].append(message)
            if len(self._store[session_id]) > self._max_messages:
                self._store[session_id] = self._store[session_id][-self._max_messages:]
            self._store.move_to_end(session_id)

    def get_history(self, session_id: str) -> list[BaseMessage]:
        with self._lock:
            return list(self._store.get(session_id, []))

    def set_metadata(self, session_id: str, key: str, value: Any) -> None:
        with self._lock:
            if session_id not in self._metadata:
                self._metadata[session_id] = {}
            self._metadata[session_id][key] = value

    def get_metadata(self, session_id: str, key: str, default: Any = None) -> Any:
        with self._lock:
            return self._metadata.get(session_id, {}).get(key, default)

    def clear(self, session_id: str) -> None:
        with self._lock:
            self._store.pop(session_id, None)
            self._metadata.pop(session_id, None)
