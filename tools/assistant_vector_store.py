import os

from pinecone import Pinecone


class AssistantVectorStore:
    def __init__(self) -> None:
        self.api_key = os.getenv("PINECONE_API_KEY")
        self.index_name = os.getenv("PINECONE_ASSISTANT_INDEX", "smart-order-assistant")
        self._client = Pinecone(api_key=self.api_key) if self.api_key else None

    def is_ready(self) -> bool:
        return self._client is not None

    def semantic_scores(self, query: str, candidates: list[dict]) -> dict[int, float]:
        if not self.is_ready() or not candidates:
            return {}
        return {}
