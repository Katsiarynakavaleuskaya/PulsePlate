# -*- coding: utf-8 -*-
"""
Retrieval Augmented Generation (RAG) system for food database.
Based on Claude Cookbooks best practices for knowledge retrieval.
"""

import json
import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from pathlib import Path
import uuid

logger = logging.getLogger(__name__)


@dataclass
class FoodDocument:
    """Document representation for food items."""

    id: str
    name: str
    content: str
    metadata: Dict[str, Any]
    embedding: Optional[List[float]] = None


@dataclass
class SearchResult:
    """Search result with relevance score."""

    document: FoodDocument
    score: float
    relevance_reason: str


class FoodVectorStore:
    """Simple vector store for food documents."""

    def __init__(self, storage_path: Path) -> None:
        """Initialize vector store."""
        self.storage_path = storage_path
        self.storage_path.mkdir(exist_ok=True)
        self.documents: Dict[str, FoodDocument] = {}
        self.load_documents()

    def add_document(self, document: FoodDocument) -> None:
        """Add document to store."""
        self.documents[document.id] = document
        self._save_document(document)

    def search(self, query: str, top_k: int = 5) -> List[SearchResult]:
        """Search documents by query."""
        query_lower = query.lower()
        results = []

        for doc in self.documents.values():
            score = self._calculate_relevance_score(query_lower, doc)
            if score > 0:
                results.append(
                    SearchResult(
                        document=doc,
                        score=score,
                        relevance_reason=self._get_relevance_reason(query_lower, doc),
                    )
                )

        # Sort by score and return top_k
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:top_k]

    def _calculate_relevance_score(self, query: str, doc: FoodDocument) -> float:
        """Calculate relevance score between query and document."""
        score = 0.0

        # Name matching (highest weight)
        if query in doc.name.lower():
            score += 10.0

        # Content matching
        content_lower = doc.content.lower()
        query_words = query.split()

        for word in query_words:
            if word in content_lower:
                score += 1.0

        # Metadata matching
        for key, value in doc.metadata.items():
            if isinstance(value, str) and query in value.lower():
                score += 2.0
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, str) and query in item.lower():
                        score += 1.5

        return score

    def _get_relevance_reason(self, query: str, doc: FoodDocument) -> str:
        """Get human-readable relevance reason."""
        reasons = []

        if query in doc.name.lower():
            reasons.append("name match")

        content_lower = doc.content.lower()
        query_words = query.split()
        matched_words = [word for word in query_words if word in content_lower]

        if matched_words:
            reasons.append(f"content matches: {', '.join(matched_words)}")

        # Check metadata matches
        for key, value in doc.metadata.items():
            if isinstance(value, str) and query in value.lower():
                reasons.append(f"{key} match")

        return "; ".join(reasons) if reasons else "partial match"

    def _save_document(self, document: FoodDocument) -> None:
        """Save document to disk."""
        doc_path = self.storage_path / f"{document.id}.json"
        doc_data = {
            "id": document.id,
            "name": document.name,
            "content": document.content,
            "metadata": document.metadata,
            "embedding": document.embedding,
        }
        doc_path.write_text(json.dumps(doc_data, indent=2))

    def load_documents(self) -> None:
        """Load documents from disk."""
        for doc_path in self.storage_path.glob("*.json"):
            try:
                doc_data = json.loads(doc_path.read_text())
                document = FoodDocument(
                    id=doc_data["id"],
                    name=doc_data["name"],
                    content=doc_data["content"],
                    metadata=doc_data["metadata"],
                    embedding=doc_data.get("embedding"),
                )
                self.documents[document.id] = document
            except Exception as e:
                logger.warning(f"Failed to load document {doc_path}: {e}")


class FoodRAGSystem:
    """RAG system for food database queries."""

    def __init__(self, vector_store: FoodVectorStore, llm_provider: Any) -> None:
        """Initialize RAG system."""
        self.vector_store = vector_store
        self.llm_provider = llm_provider

    async def query(self, question: str, context_limit: int = 3) -> Dict[str, Any]:
        """
        Answer question using RAG approach.

        Args:
            question: User question about food/nutrition
            context_limit: Maximum number of relevant documents to use

        Returns:
            Structured response with answer and sources
        """
        # Retrieve relevant documents
        search_results = self.vector_store.search(question, top_k=context_limit)

        if not search_results:
            return {
                "answer": "I couldn't find relevant information in the food database.",
                "sources": [],
                "confidence": 0.0,
            }

        # Prepare context for LLM
        context = self._prepare_context(search_results)

        # Generate answer using LLM
        prompt = self._create_prompt(question, context)

        try:
            if hasattr(self.llm_provider, "generate"):
                answer = await self.llm_provider.generate(prompt)
            else:
                answer = "LLM provider not available"
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            answer = "I encountered an error while generating the answer."

        return {
            "answer": answer,
            "sources": [
                {
                    "name": result.document.name,
                    "relevance_score": result.score,
                    "relevance_reason": result.relevance_reason,
                    "metadata": result.document.metadata,
                }
                for result in search_results
            ],
            "confidence": self._normalize_confidence(search_results),
        }

    def _normalize_confidence(self, search_results: List[SearchResult]) -> float:
        """Normalize confidence score based on relative top score with clamping.

        The top result is normalized relative to the maximum score among results.
        Guards against division by zero and clamps to [0.0, 1.0].
        """
        if not search_results:
            return 0.0
        max_score = max((r.score for r in search_results), default=0.0)
        if max_score <= 0.0:
            return 0.0
        top_score = search_results[0].score
        confidence = top_score / max_score
        return float(min(1.0, max(0.0, confidence)))

    def _prepare_context(self, search_results: List[SearchResult]) -> str:
        """Prepare context from search results."""
        context_parts = []

        for i, result in enumerate(search_results, 1):
            doc = result.document
            context_parts.append(
                f"""
Document {i}: {doc.name}
Relevance: {result.relevance_reason} (score: {result.score:.2f})
Content: {doc.content}
Metadata: {json.dumps(doc.metadata, indent=2)}
"""
            )

        return "\n".join(context_parts)

    def _create_prompt(self, question: str, context: str) -> str:
        """Create prompt for LLM with context."""
        return f"""
You are a nutrition expert. Answer the user's question based on the provided food database context.

Question: {question}

Context from food database:
{context}

Instructions:
1. Provide a clear, accurate answer based on the context
2. If the context doesn't contain enough information, say so
3. Include specific details from the relevant documents
4. Be helpful and informative
5. If there are multiple relevant foods, mention the key differences

Answer:
"""


def create_food_document(food_item: Dict[str, Any]) -> FoodDocument:
    """Create FoodDocument from food item data."""
    # Generate a collision-resistant, deterministic ID (UUIDv5) from canonicalized fields
    # Stable namespace derived from project URL for consistency across environments
    RAG_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, "https://pulseplate.ai/rag")

    normalized_name = str(food_item.get("name", "")).strip().lower()
    source = str(food_item.get("source", "")).strip().lower()
    source_id = str(food_item.get("source_id", "")).strip().lower()
    brand = str(food_item.get("brand", "")).strip().lower()
    namespace_data = "|".join([source, source_id, brand, normalized_name])
    food_id = uuid.uuid5(RAG_NAMESPACE, namespace_data).hex

    # Create content for search
    content_parts = [
        f"Name: {food_item.get('name', 'Unknown')}",
        f"Source: {food_item.get('source', 'Unknown')}",
    ]

    # Add nutrition information
    nutrients = food_item.get("nutrients_per_100g", {})
    if nutrients:
        content_parts.append("Nutrition per 100g:")
        for nutrient, value in nutrients.items():
            content_parts.append(f"  {nutrient}: {value}")

    # Add other relevant information
    if "tags" in food_item:
        content_parts.append(f"Tags: {', '.join(food_item['tags'])}")

    if "availability_regions" in food_item:
        content_parts.append(f"Available in: {', '.join(food_item['availability_regions'])}")

    content = "\n".join(content_parts)

    # Extract metadata
    metadata = {
        "source": food_item.get("source", ""),
        "source_id": food_item.get("source_id", ""),
        "cost_per_100g": food_item.get("cost_per_100g", 0),
        "tags": food_item.get("tags", []),
        "availability_regions": food_item.get("availability_regions", []),
    }

    return FoodDocument(
        id=food_id, name=food_item.get("name", "Unknown"), content=content, metadata=metadata
    )


# Integration functions
def initialize_rag_system(storage_path: Path, llm_provider: Any) -> FoodRAGSystem:
    """Initialize RAG system with storage and LLM provider."""
    vector_store = FoodVectorStore(storage_path)
    return FoodRAGSystem(vector_store, llm_provider)


def populate_vector_store_from_foods(vector_store: FoodVectorStore, foods: Dict[str, Any]) -> None:
    """Populate vector store with food items."""
    for food_name, food_data in foods.items():
        document = create_food_document(food_data)
        vector_store.add_document(document)

    logger.info(f"Populated vector store with {len(foods)} food items")
