from core.rag import simple_rag as RAG


def test_rag_uses_docs_folder_rglob(tmp_path):
    docs_dir = tmp_path / "docs" / "nested"
    docs_dir.mkdir(parents=True, exist_ok=True)
    f = docs_dir / "note.md"
    f.write_text("Vitamin D context paragraph.")

    RAG.ROOT = tmp_path
    RAG.invalidate_index()
    out = RAG.retrieve_context("vitamin")
    assert "note.md" in out


def test_chunk_splits_and_emits_on_overflow():
    # Two paras that cannot be merged given tiny max_chars → triggers append at lines 43-44
    text = "para1\n\nlongparagraphtwo"
    parts = RAG._chunk(text, max_chars=5)
    assert len(parts) == 2 and parts[0] == "para1"
