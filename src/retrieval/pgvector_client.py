"""PostgreSQL + pgvector client for document embeddings."""
import logging
from typing import Any, Dict, List, Optional

from sentence_transformers import CrossEncoder
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from src.config.settings import settings

logger = logging.getLogger(__name__)


class PGVectorClient:
    """Client for PostgreSQL with pgvector extension."""

    def __init__(self, database_url: Optional[str] = None,
                 cross_encoder_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        """Initialize the pgvector client."""
        self.database_url = database_url or settings.database_url
        self.engine = create_engine(self.database_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        try:
            self.cross_encoder = CrossEncoder(cross_encoder_model)
            logger.info(f"Loaded cross-encoder model: {cross_encoder_model}")
        except Exception as e:
            logger.warning(f"Unable to load cross-encoder model {cross_encoder_model}: {e}")
            self.cross_encoder = None

    def store_document(self, filename: str, document_type: str, applicant_id: str,
                      content: str) -> int:
        """Store document metadata and return document ID."""
        with self.SessionLocal() as session:
            try:
                result = session.execute(
                    text("""
                        INSERT INTO documents (filename, document_type, applicant_id, content)
                        VALUES (:filename, :document_type, :applicant_id, :content)
                        RETURNING id
                    """),
                    {
                        "filename": filename,
                        "document_type": document_type,
                        "applicant_id": applicant_id,
                        "content": content
                    }
                )
                document_id = result.scalar()
                session.commit()
                logger.info(f"Stored document {filename} with ID {document_id}")
                return document_id
            except Exception as e:
                session.rollback()
                logger.error(f"Failed to store document: {e}")
                raise

    def store_embeddings(self, document_id: int, chunks: List[str],
                        embeddings: List[List[float]], metadata: Optional[List[dict]] = None) -> None:
        """Store document chunks and their embeddings."""
        if len(chunks) != len(embeddings):
            raise ValueError("Number of chunks must match number of embeddings")

        if metadata is None:
            metadata = [{}] * len(chunks)

        with self.SessionLocal() as session:
            try:
                for i, (chunk, embedding, meta) in enumerate(zip(chunks, embeddings, metadata)):
                    session.execute(
                        text("""
                            INSERT INTO embeddings (document_id, chunk_index, chunk_text, embedding, metadata)
                            VALUES (:document_id, :chunk_index, :chunk_text, :embedding, :metadata)
                        """),
                        {
                            "document_id": document_id,
                            "chunk_index": i,
                            "chunk_text": chunk,
                            "embedding": embedding,
                            "metadata": meta
                        }
                    )
                session.commit()
                logger.info(f"Stored {len(chunks)} embeddings for document {document_id}")
            except Exception as e:
                session.rollback()
                logger.error(f"Failed to store embeddings: {e}")
                raise

    def bm25_search(self, query: str,
                    applicant_id: Optional[str] = None,
                    document_types: Optional[List[str]] = None,
                    top_k: int = 20) -> List[dict]:
        """Search for document chunks using PostgreSQL full-text ranking (BM25-style)."""
        with self.SessionLocal() as session:
            try:
                query_parts = [
                    "SELECT e.chunk_text, e.metadata, d.document_type, d.applicant_id, d.filename,",
                    "ts_rank_cd(to_tsvector('english', e.chunk_text), plainto_tsquery('english', :query)) AS bm25_score",
                    "FROM embeddings e",
                    "JOIN documents d ON e.document_id = d.id",
                    "WHERE to_tsvector('english', e.chunk_text) @@ plainto_tsquery('english', :query)"
                ]

                params = {"query": query}
                if applicant_id:
                    query_parts.append("AND d.applicant_id = :applicant_id")
                    params["applicant_id"] = applicant_id

                if document_types:
                    placeholders = [f":doc_type_{i}" for i in range(len(document_types))]
                    query_parts.append(f"AND d.document_type IN ({', '.join(placeholders)})")
                    for i, doc_type in enumerate(document_types):
                        params[f"doc_type_{i}"] = doc_type

                query_parts.extend([
                    "ORDER BY bm25_score DESC",
                    "LIMIT :top_k"
                ])
                params["top_k"] = top_k

                full_query = " ".join(query_parts)
                result = session.execute(text(full_query), params)

                results = []
                for row in result:
                    results.append({
                        "chunk_text": row.chunk_text,
                        "metadata": row.metadata,
                        "document_type": row.document_type,
                        "applicant_id": row.applicant_id,
                        "filename": row.filename,
                        "bm25_score": float(row.bm25_score)
                    })

                logger.info(f"BM25 search found {len(results)} chunks for query '{query}'")
                return results

            except Exception as e:
                logger.error(f"Failed BM25 search: {e}")
                raise

    def _chunk_key(self, item: Dict[str, Any]) -> tuple:
        return (
            item.get("chunk_text"),
            item.get("document_type"),
            item.get("filename")
        )

    def _reciprocal_rank_fusion(self,
                                bm25_results: List[dict],
                                vector_results: List[dict],
                                k: int = 60) -> List[dict]:
        """Fuse BM25 and vector rankings using reciprocal rank fusion."""
        fused = {}

        def add_ranked_list(results: List[dict], key_name: str):
            for rank, item in enumerate(results, start=1):
                candidate_key = self._chunk_key(item)
                if candidate_key not in fused:
                    fused[candidate_key] = {
                        **item,
                        "rrf_score": 0.0,
                        "bm25_score": item.get("bm25_score", 0.0),
                        "similarity_score": item.get("similarity_score", 0.0)
                    }
                fused[candidate_key]["rrf_score"] += 1.0 / (k + rank)
                fused[candidate_key][key_name] = rank

        add_ranked_list(bm25_results, "bm25_rank")
        add_ranked_list(vector_results, "vector_rank")

        fused_results = sorted(
            fused.values(),
            key=lambda item: item["rrf_score"],
            reverse=True
        )

        logger.info(f"RRF fused {len(fused_results)} candidate chunks")
        return fused_results

    def cross_encoder_rerank(self,
                              query: str,
                              candidates: List[dict],
                              top_n: int = 10) -> List[dict]:
        """Re-rank candidate chunks using a cross-encoder model."""
        if not candidates or self.cross_encoder is None:
            return candidates[:top_n]

        pairs = [(query, candidate["chunk_text"]) for candidate in candidates]
        try:
            scores = self.cross_encoder.predict(pairs)
            for candidate, score in zip(candidates, scores):
                candidate["cross_score"] = float(score)

            reranked = sorted(candidates, key=lambda item: item["cross_score"], reverse=True)
            logger.info(f"Cross-encoder reranked top {min(len(reranked), top_n)} candidates")
            return reranked[:top_n]
        except Exception as e:
            logger.warning(f"Cross-encoder rerank failed: {e}")
            return candidates[:top_n]

    def hybrid_search(self,
                      query: str,
                      query_embedding: List[float],
                      applicant_id: Optional[str] = None,
                      document_types: Optional[List[str]] = None,
                      top_k: int = 10,
                      bm25_top_k: int = 40,
                      semantic_top_k: int = 40,
                      cross_top_k: int = 10) -> List[dict]:
        """Execute a hybrid retrieval pipeline using BM25, bi-encoder similarity, RRF, and cross-encoder re-ranking."""
        bm25_results = self.bm25_search(
            query=query,
            applicant_id=applicant_id,
            document_types=document_types,
            top_k=bm25_top_k
        )

        vector_results = self.search_similar_documents(
            query_embedding=query_embedding,
            applicant_id=applicant_id,
            document_types=document_types,
            top_k=semantic_top_k
        )

        fused_results = self._reciprocal_rank_fusion(bm25_results, vector_results)
        reranked_results = self.cross_encoder_rerank(query, fused_results, top_n=cross_top_k)

        return reranked_results[:top_k]

    def search_similar_documents(self, query_embedding: List[float],
                               applicant_id: Optional[str] = None,
                               document_types: Optional[List[str]] = None,
                               top_k: int = 5) -> List[dict]:
        """Search for similar documents using vector similarity."""
        with self.SessionLocal() as session:
            try:
                # Build the query
                query_parts = [
                    "SELECT e.chunk_text, e.metadata, d.document_type, d.applicant_id, d.filename,",
                    "1 - (e.embedding <=> :query_embedding) as similarity_score",
                    "FROM embeddings e",
                    "JOIN documents d ON e.document_id = d.id"
                ]

                where_conditions = []
                params = {"query_embedding": query_embedding}

                if applicant_id:
                    where_conditions.append("d.applicant_id = :applicant_id")
                    params["applicant_id"] = applicant_id

                if document_types:
                    placeholders = [f":doc_type_{i}" for i in range(len(document_types))]
                    where_conditions.append(f"d.document_type IN ({', '.join(placeholders)})")
                    for i, doc_type in enumerate(document_types):
                        params[f"doc_type_{i}"] = doc_type

                if where_conditions:
                    query_parts.append("WHERE " + " AND ".join(where_conditions))

                query_parts.extend([
                    "ORDER BY e.embedding <=> :query_embedding",
                    "LIMIT :top_k"
                ])
                params["top_k"] = top_k

                full_query = " ".join(query_parts)
                result = session.execute(text(full_query), params)

                results = []
                for row in result:
                    results.append({
                        "chunk_text": row.chunk_text,
                        "metadata": row.metadata,
                        "document_type": row.document_type,
                        "applicant_id": row.applicant_id,
                        "filename": row.filename,
                        "similarity_score": float(row.similarity_score)
                    })

                logger.info(f"Found {len(results)} similar documents")
                return results

            except Exception as e:
                logger.error(f"Failed to search documents: {e}")
                raise

    def get_applicant_documents(self, applicant_id: str) -> List[dict]:
        """Get all documents for a specific applicant."""
        with self.SessionLocal() as session:
            try:
                result = session.execute(
                    text("""
                        SELECT id, filename, document_type, uploaded_at, content
                        FROM documents
                        WHERE applicant_id = :applicant_id
                        ORDER BY uploaded_at DESC
                    """),
                    {"applicant_id": applicant_id}
                )

                documents = []
                for row in result:
                    documents.append({
                        "id": row.id,
                        "filename": row.filename,
                        "document_type": row.document_type,
                        "uploaded_at": row.uploaded_at,
                        "content": row.content
                    })

                return documents

            except Exception as e:
                logger.error(f"Failed to get applicant documents: {e}")
                raise

    def get_underwriting_decision(self, applicant_id: str) -> Optional[dict]:
        """Get cached underwriting decision for an applicant."""
        with self.SessionLocal() as session:
            try:
                result = session.execute(
                    text("""
                        SELECT decision, premium_amount, reasoning, created_at
                        FROM underwriting_decisions
                        WHERE applicant_id = :applicant_id
                        AND expires_at > CURRENT_TIMESTAMP
                        ORDER BY created_at DESC
                        LIMIT 1
                    """),
                    {"applicant_id": applicant_id}
                )

                row = result.fetchone()
                if row:
                    return {
                        "decision": row.decision,
                        "premium_amount": float(row.premium_amount) if row.premium_amount else None,
                        "reasoning": row.reasoning,
                        "created_at": row.created_at
                    }

                return None

            except Exception as e:
                logger.error(f"Failed to get underwriting decision: {e}")
                raise

    def cache_underwriting_decision(self, applicant_id: str, decision: str,
                                   premium_amount: Optional[float], reasoning: str) -> None:
        """Cache an underwriting decision."""
        with self.SessionLocal() as session:
            try:
                # First, delete any existing decision for this applicant
                session.execute(
                    text("DELETE FROM underwriting_decisions WHERE applicant_id = :applicant_id"),
                    {"applicant_id": applicant_id}
                )

                # Insert the new decision
                session.execute(
                    text("""
                        INSERT INTO underwriting_decisions (applicant_id, decision, premium_amount, reasoning)
                        VALUES (:applicant_id, :decision, :premium_amount, :reasoning)
                    """),
                    {
                        "applicant_id": applicant_id,
                        "decision": decision,
                        "premium_amount": premium_amount,
                        "reasoning": reasoning
                    }
                )

                session.commit()
                logger.info(f"Cached underwriting decision for applicant {applicant_id}")

            except Exception as e:
                session.rollback()
                logger.error(f"Failed to cache underwriting decision: {e}")
                raise

    def health_check(self) -> bool:
        """Check if the database connection is healthy."""
        try:
            with self.SessionLocal() as session:
                session.execute(text("SELECT 1"))
                return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False