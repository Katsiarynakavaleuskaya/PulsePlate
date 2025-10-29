"""
Simple tests for core/rag_system.py to improve coverage.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, AsyncMock
from core.rag_system import FoodDocument, SearchResult, FoodVectorStore, FoodRAGSystem


class TestFoodDocument:
    """Test FoodDocument basic functionality."""

    def test_init(self) -> None:
        """Test FoodDocument initialization."""
        doc = FoodDocument(
            id="apple_001",
            name="Apple",
            content="A red fruit",
            metadata={"type": "fruit", "color": "red"},
        )
        assert doc.id == "apple_001"
        assert doc.name == "Apple"
        assert doc.content == "A red fruit"
        assert doc.metadata == {"type": "fruit", "color": "red"}

    def test_str_representation(self) -> None:
        """Test string representation."""
        doc = FoodDocument(
            id="apple_001", name="Apple", content="A red fruit", metadata={"type": "fruit"}
        )
        str_repr = str(doc)
        assert "Apple" in str_repr


class TestSearchResult:
    """Test SearchResult basic functionality."""

    def test_init(self) -> None:
        """Test SearchResult initialization."""
        doc = FoodDocument(
            id="apple_001", name="Apple", content="A red fruit", metadata={"type": "fruit"}
        )
        result = SearchResult(document=doc, score=0.95, relevance_reason="High relevance")

        assert result.document == doc
        assert result.score == 0.95
        assert result.relevance_reason == "High relevance"

    def test_str_representation(self) -> None:
        """Test string representation."""
        doc = FoodDocument(
            id="apple_001", name="Apple", content="A red fruit", metadata={"type": "fruit"}
        )
        result = SearchResult(document=doc, score=0.95, relevance_reason="High relevance")
        str_repr = str(result)
        assert "0.95" in str_repr


class TestFoodVectorStore:
    """Test FoodVectorStore basic functionality."""

    def test_init(self) -> None:
        """Test FoodVectorStore initialization."""
        store = FoodVectorStore(storage_path=Path("/tmp/test"))
        assert store.storage_path == Path("/tmp/test")
        assert isinstance(store.documents, dict)

    def test_add_document(self) -> None:
        """Test adding document."""
        store = FoodVectorStore(storage_path=Path("/tmp/test"))
        doc = FoodDocument(
            id="test_apple_002",
            name="Test Apple 2",
            content="A red fruit",
            metadata={"type": "fruit"},
        )

        initial_count = len(store.documents)
        store.add_document(doc)
        # Проверим, что документ добавлен (может быть перезаписан существующий)
        assert store.documents["test_apple_002"] == doc

    def test_search_empty(self) -> None:
        """Test search with empty store."""
        store = FoodVectorStore(storage_path=Path("/tmp/test"))
        results = store.search("nonexistent_query", top_k=5)
        assert isinstance(results, list)

    def test_search_with_docs(self) -> None:
        """Test search with documents."""
        store = FoodVectorStore(storage_path=Path("/tmp/test"))
        doc1 = FoodDocument(
            id="test_apple_001",
            name="Test Apple",
            content="A red fruit",
            metadata={"type": "fruit"},
        )
        doc2 = FoodDocument(
            id="test_banana_001",
            name="Test Banana",
            content="A yellow fruit",
            metadata={"type": "fruit"},
        )

        store.add_document(doc1)
        store.add_document(doc2)

        results = store.search("test apple", top_k=5)
        assert len(results) >= 1
        assert any(result.document.name == "Test Apple" for result in results)

    def test_calculate_relevance(self) -> None:
        """Test relevance calculation."""
        store = FoodVectorStore(storage_path=Path("/tmp/test"))
        doc = FoodDocument(
            id="test_apple_001",
            name="Test Apple",
            content="A red fruit",
            metadata={"type": "fruit"},
        )

        # Simple relevance calculation
        relevance = store._calculate_relevance_score("test apple", doc)
        assert relevance >= 0

    def test_prepare_context(self) -> None:
        """Test context preparation."""
        from core.rag_system import FoodRAGSystem

        store = FoodVectorStore(storage_path=Path("/tmp/test"))
        rag = FoodRAGSystem(vector_store=store, llm_provider=Mock())

        doc = FoodDocument(
            id="test_apple_001",
            name="Test Apple",
            content="A red fruit",
            metadata={"type": "fruit"},
        )
        result = SearchResult(document=doc, score=0.95, relevance_reason="High relevance")

        context = rag._prepare_context([result])
        assert "Test Apple" in context
        assert "0.95" in context


class TestFoodRAGSystem:
    """Test FoodRAGSystem basic functionality."""

    def test_init(self) -> None:
        """Test FoodRAGSystem initialization."""
        mock_llm = Mock()
        vector_store = FoodVectorStore(storage_path=Path("/tmp/test"))
        rag = FoodRAGSystem(vector_store=vector_store, llm_provider=mock_llm)
        assert rag.llm_provider == mock_llm
        assert rag.vector_store == vector_store

    def test_add_document(self) -> None:
        """Test adding document to RAG system."""
        mock_llm = Mock()
        vector_store = FoodVectorStore(storage_path=Path("/tmp/test"))
        rag = FoodRAGSystem(vector_store=vector_store, llm_provider=mock_llm)

        doc = FoodDocument(
            id="apple_003", name="Apple 3", content="A red fruit", metadata={"type": "fruit"}
        )
        initial_count = len(rag.vector_store.documents)
        rag.vector_store.add_document(doc)

        # Проверим, что документ добавлен (может быть перезаписан существующий)
        assert rag.vector_store.documents["apple_003"] == doc

    @pytest.mark.asyncio
    async def test_query_success(self) -> None:
        """Test successful query."""
        mock_llm = Mock()
        mock_llm.generate_text = AsyncMock(return_value="Apples are red fruits.")

        vector_store = FoodVectorStore(storage_path=Path("/tmp/test"))
        rag = FoodRAGSystem(vector_store=vector_store, llm_provider=mock_llm)

        # Add a document
        doc = FoodDocument(
            id="apple_001", name="Apple", content="A red fruit", metadata={"type": "fruit"}
        )
        rag.vector_store.add_document(doc)

        result = await rag.query("What is an apple?")

        assert "answer" in result
        assert "sources" in result
        assert "confidence" in result

    @pytest.mark.asyncio
    async def test_query_no_docs(self) -> None:
        """Test query with no documents."""
        mock_llm = Mock()
        mock_llm.generate_text = AsyncMock(return_value="No information available.")

        vector_store = FoodVectorStore(storage_path=Path("/tmp/test"))
        rag = FoodRAGSystem(vector_store=vector_store, llm_provider=mock_llm)

        result = await rag.query("What is an apple?")

        assert "answer" in result
        assert "sources" in result
        assert "confidence" in result
        assert result["confidence"] == 0.0

    @pytest.mark.asyncio
    async def test_query_error(self) -> None:
        """Test query with error."""
        mock_llm = Mock()
        mock_llm.generate_text = AsyncMock(side_effect=Exception("LLM error"))

        vector_store = FoodVectorStore(storage_path=Path("/tmp/test"))
        rag = FoodRAGSystem(vector_store=vector_store, llm_provider=mock_llm)

        result = await rag.query("What is an apple?")

        assert "answer" in result
        assert "sources" in result
        assert "confidence" in result
