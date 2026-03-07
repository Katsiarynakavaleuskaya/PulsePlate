"""Regression tests for RAG public contract surface.

RU: Проверяем, что удалённые мёртвые экспорты не возвращаются в public API.
EN: Ensure removed dead exports do not reappear in the public package surface.
"""

from __future__ import annotations


class TestDeadExceptionCleanup:
    """Tests that removed RAG exception exports stay removed."""

    def test_contract_module_does_not_export_dead_exception(self) -> None:
        """core.rag.contracts should not keep unused dead exception exports."""
        import core.rag.contracts as contracts

        assert not hasattr(contracts, "CorpusNotIndexedError")
        assert "CorpusNotIndexedError" not in getattr(contracts, "__all__", ())
        assert "CorpusNotIndexedError" not in getattr(contracts, "__all__", ())

    def test_package_surface_does_not_reexport_dead_exception(self) -> None:
        """core.rag package surface should not expose removed dead exceptions."""
        import core.rag as rag

        assert "CorpusNotIndexedError" not in rag.__all__
        assert not hasattr(rag, "CorpusNotIndexedError")
