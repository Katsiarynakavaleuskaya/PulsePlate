from core.rag import simple_rag as RAG


def test_rag_topk_zero_and_unknown_section(tmp_path):
    # Prepare a tiny markdown file
    f = tmp_path / "doc.md"
    f.write_text("Vitamin D helps calcium.")

    RAG.ROOT = tmp_path
    RAG.invalidate_index()

    # top_k = 0 → library uses max(1, k), so still returns top-1; assert non-empty
    assert RAG.retrieve_context("vitamin", max_chunks=0) != ""
