"""Ragas integration for RAG quality assessment."""
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class RagasClient:
    """Client for Ragas RAG assessment integration."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize the Ragas client."""
        self.api_key = api_key

    def evaluate_retrieval(self, query: str, retrieved_documents: List[Dict]) -> Dict[str, str]:
        """Evaluate retrieval quality for a query and retrieved documents."""
        try:
            logger.info(f"Evaluating retrieval quality for query: {query}")

            if not retrieved_documents:
                return {
                    "query": query,
                    "quality_score": 0.0,
                    "quality": "poor",
                    "notes": "No documents retrieved",
                    "metrics": {
                        "retrieval_count": 0,
                        "avg_similarity": 0.0
                    }
                }

            # Calculate basic quality metrics
            similarities = [doc.get("similarity_score", 0.0) for doc in retrieved_documents if doc.get("similarity_score") is not None]
            avg_similarity = sum(similarities) / len(similarities) if similarities else 0.0

            # Assess quality based on similarity scores and document count
            quality_score = self._calculate_quality_score(retrieved_documents, avg_similarity)
            quality_level = self._get_quality_level(quality_score)

            # Generate assessment notes
            notes = self._generate_assessment_notes(retrieved_documents, quality_score)

            return {
                "query": query,
                "quality_score": quality_score,
                "quality": quality_level,
                "notes": notes,
                "metrics": {
                    "retrieval_count": len(retrieved_documents),
                    "avg_similarity": round(avg_similarity, 3),
                    "max_similarity": max(similarities) if similarities else 0.0,
                    "min_similarity": min(similarities) if similarities else 0.0
                }
            }

        except Exception as e:
            logger.error(f"Ragas evaluation failed: {e}")
            return {
                "query": query,
                "quality_score": 0.0,
                "quality": "error",
                "notes": f"Evaluation failed: {str(e)}",
                "metrics": {
                    "retrieval_count": len(retrieved_documents) if retrieved_documents else 0,
                    "avg_similarity": 0.0
                }
            }

    def _calculate_quality_score(self, documents: List[Dict], avg_similarity: float) -> float:
        """Calculate a quality score from 0-1 based on retrieval metrics."""
        if not documents:
            return 0.0

        # Base score from average similarity (0-0.5 points)
        similarity_score = min(avg_similarity, 1.0) * 0.5

        # Bonus for document count (0-0.3 points)
        count_score = min(len(documents) / 10.0, 1.0) * 0.3

        # Bonus for document diversity (different sources/types) (0-0.2 points)
        sources = set(doc.get("document_type", "") for doc in documents)
        diversity_score = min(len(sources) / 3.0, 1.0) * 0.2

        total_score = similarity_score + count_score + diversity_score

        return round(total_score, 3)

    def _get_quality_level(self, score: float) -> str:
        """Convert quality score to descriptive level."""
        if score >= 0.8:
            return "excellent"
        elif score >= 0.6:
            return "good"
        elif score >= 0.4:
            return "fair"
        elif score >= 0.2:
            return "poor"
        else:
            return "very_poor"

    def _generate_assessment_notes(self, documents: List[Dict], quality_score: float) -> str:
        """Generate human-readable assessment notes."""
        notes = []

        doc_count = len(documents)
        if doc_count == 0:
            return "No documents retrieved for this query"
        elif doc_count < 3:
            notes.append(f"Low retrieval count ({doc_count} documents)")
        elif doc_count > 10:
            notes.append(f"High retrieval count ({doc_count} documents)")

        # Check similarity distribution
        similarities = [doc.get("similarity_score", 0.0) for doc in documents]
        if similarities:
            max_sim = max(similarities)
            min_sim = min(similarities)

            if max_sim > 0.8:
                notes.append("High-quality matches found")
            elif max_sim < 0.3:
                notes.append("Low similarity scores across retrieved documents")

            if max_sim - min_sim > 0.5:
                notes.append("Wide variation in document relevance")

        # Check document type diversity
        doc_types = set(doc.get("document_type", "") for doc in documents)
        if len(doc_types) > 1:
            notes.append(f"Diverse document types: {', '.join(doc_types)}")
        elif len(doc_types) == 1:
            notes.append(f"Single document type: {list(doc_types)[0]}")

        if quality_score >= 0.7:
            notes.append("Strong retrieval performance")
        elif quality_score < 0.3:
            notes.append("Retrieval performance needs improvement")

        return "; ".join(notes) if notes else "Standard retrieval quality"
