"""Optional Pinecone integration for embedding storage and similarity search."""
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

try:
    import pinecone
except ImportError:
    pinecone = None


class PineconeClient:
    """Pinecone vector store client wrapper."""

    def __init__(self, api_key: Optional[str] = None, environment: Optional[str] = None, index_name: str = "insurance-docs"):
        self.api_key = api_key
        self.environment = environment
        self.index_name = index_name
        self.index = None

        if pinecone is None:
            logger.warning("pinecone package is not installed; Pinecone integration disabled")
            return

        if self.api_key and self.environment:
            pinecone.init(api_key=self.api_key, environment=self.environment)
            if self.index_name not in pinecone.list_indexes():
                pinecone.create_index(self.index_name, dimension=1536, metric="cosine")
            self.index = pinecone.Index(self.index_name)
            logger.info(f"Initialized Pinecone index {self.index_name}")
        else:
            logger.warning("Pinecone API key or environment missing; Pinecone integration disabled")

    def upsert(self, vectors: List[Dict[str, Any]], namespace: Optional[str] = None) -> None:
        if not self.index:
            return
        self.index.upsert(vectors=vectors, namespace=namespace)
        logger.info(f"Upserted {len(vectors)} vectors into Pinecone")

    def query(self, vector: List[float], top_k: int = 5, namespace: Optional[str] = None) -> List[Dict[str, Any]]:
        if not self.index:
            return []
        response = self.index.query(vector=vector, top_k=top_k, namespace=namespace, include_metadata=True)
        matches = []
        for match in response.matches:
            matches.append({
                "id": match.id,
                "score": match.score,
                "metadata": match.metadata
            })
        return matches

    def delete_all(self) -> None:
        if not self.index:
            return
        self.index.delete(delete_all=True)
        logger.info(f"Deleted all vectors from Pinecone index {self.index_name}")
