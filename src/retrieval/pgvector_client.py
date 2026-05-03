"""PostgreSQL + pgvector client for document embeddings."""
import logging
from typing import List, Optional, Tuple

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from src.config.settings import settings

logger = logging.getLogger(__name__)


class PGVectorClient:
    """Client for PostgreSQL with pgvector extension."""

    def __init__(self, database_url: Optional[str] = None):
        """Initialize the pgvector client."""
        self.database_url = database_url or settings.database_url
        self.engine = create_engine(self.database_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

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