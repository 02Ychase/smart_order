import logging
import os

from pinecone import Pinecone, ServerlessSpec

from service.embedding import DEFAULT_DIMENSION, get_embedding_service

logger = logging.getLogger(__name__)


class AssistantVectorStore:
    def __init__(self, auto_create_index: bool = True) -> None:
        self.api_key = os.getenv("PINECONE_API_KEY")
        self.index_name = os.getenv("PINECONE_ASSISTANT_INDEX", "smart-order-assistant")
        self.pinecone_env = os.getenv("PINECONE_ENY", "us-east-1")
        self.dimension = DEFAULT_DIMENSION

        self._client = None
        self._index = None

        if self.api_key:
            try:
                self._client = Pinecone(api_key=self.api_key)
                if self._client.has_index(self.index_name):
                    self._index = self._client.Index(self.index_name)
                    logger.info(f"Pinecone index ready: {self.index_name}")
                elif auto_create_index:
                    logger.info(f"Creating Pinecone index: {self.index_name}")
                    self._client.create_index(
                        name=self.index_name,
                        vector_type="dense",
                        dimension=self.dimension,
                        metric="cosine",
                        spec=ServerlessSpec(cloud="aws", region=self.pinecone_env),
                    )
                    self._index = self._client.Index(self.index_name)
                    logger.info(f"Pinecone index ready: {self.index_name}")
                else:
                    logger.info(f"Pinecone index '{self.index_name}' not found (auto_create disabled)")
            except Exception as e:
                logger.warning(f"Failed to initialize Pinecone index: {e}")

    def is_ready(self) -> bool:
        return self._client is not None and self._index is not None

    def _embed(self, text: str) -> list[float] | None:
        try:
            svc = get_embedding_service()
            return svc.embed(text)
        except Exception as e:
            logger.error(f"Embedding request failed: {e}")
            return None

    def semantic_search(self, query: str, top_k: int = 5, namespace: str = "") -> list[dict]:
        if not self.is_ready():
            return []

        query_vector = self._embed(query)
        if not query_vector or len(query_vector) != self.dimension:
            return []

        try:
            kwargs = {"vector": query_vector, "top_k": top_k, "include_metadata": True}
            if namespace:
                kwargs["namespace"] = namespace
            result = self._index.query(**kwargs)
            matches = result.get("matches", [])
            return [
                {
                    "id": m["id"],
                    "score": m["score"],
                    "metadata": m.get("metadata", {}),
                }
                for m in matches
            ]
        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            return []

    def clear_namespace(self, namespace: str = "") -> bool:
        if not self.is_ready():
            return False
        try:
            kwargs = {"delete_all": True}
            if namespace:
                kwargs["namespace"] = namespace
            self._index.delete(**kwargs)
            logger.info(f"Cleared namespace: {namespace or '(default)'}")
            return True
        except Exception as e:
            logger.warning(f"Failed to clear namespace {namespace}: {e}")
            return False

    def upsert_candidates(self, candidates: list[dict], batch_size: int = 30, namespace: str = "") -> bool:
        if not self.is_ready():
            return False

        batch = []
        for candidate in candidates:
            text = candidate.get("text", "")
            vector = self._embed(text)
            if not vector or len(vector) != self.dimension:
                logger.error("Invalid embedding for candidate")
                return False

            metadata = candidate.get("metadata", {})
            metadata["content"] = text
            batch.append((candidate["id"], vector, metadata))

            if len(batch) >= batch_size:
                kwargs = {"vectors": batch}
                if namespace:
                    kwargs["namespace"] = namespace
                self._index.upsert(**kwargs)
                batch = []

        if batch:
            kwargs = {"vectors": batch}
            if namespace:
                kwargs["namespace"] = namespace
            self._index.upsert(**kwargs)

        return True

    def semantic_scores(self, query: str, candidates: list[dict]) -> dict[int, float]:
        if not self.is_ready() or not candidates:
            return {}
        return {}
