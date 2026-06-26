# PyTorch `torch.jit.script` CVE-2025-3000 advisory

## Summary

`CVE-2025-3000` / `GHSA-rrmf-rvhw-rf47` previously applied to `torch` in the
optional RAG/vector manifests. This PR resolves the repo-owned exposure by
removing the PyTorch/SentenceTransformers backend from the tracked optional
vector profiles and replacing it with FastEmbed/ONNX.

This is resolved by removal. PulsePlate now has no pip-audit waiver for this
CVE.

## Governance

- **Owner:** @katsiaryna_kavaleuskaya
- **Backlog:** `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-pytorch-jit-cve-2025-3000-vector-profile`
- **pip-audit waiver:** removed from `scripts/ci_pip_audit.sh`
- **Last checked:** 2026-06-26

## Current Repo State

- `requirements.txt`: no direct `torch` pin.
- `requirements-ci-lite.txt`: no direct `torch` pin.
- `requirements-docker-runtime.txt`: no direct `torch` pin.
- `requirements-lock.txt`: no direct `torch` pin.
- `requirements-rag-vector.txt`: FastEmbed/ONNX + `pgvector`, no direct `torch`
  pin and no PyTorch index.
- `requirements-rag-vector-cpu.txt`: FastEmbed/ONNX + `pgvector`, no direct
  `torch` pin and no PyTorch index.
- `scripts/ci_pip_audit.sh`: scans optional vector manifests without any
  `CVE-2025-3000` ignore.

## Exposure Assessment

The vulnerable surface was tied to PyTorch TorchScript (`torch.jit.script`) in
the optional RAG/vector dependency profile. The active local embedding backend is
now FastEmbed/ONNX, and the tracked vector lockfiles do not contain `torch`,
`sentence-transformers`, `transformers`, CUDA/NVIDIA packages, Triton, or the
PyTorch wheel index.

The backend model changed from MPNet to `BAAI/bge-base-en-v1.5`. The schema
remains `VECTOR(768)`, but the vector spaces are not semantically compatible.
Vector retrieval therefore requires `RAG_VECTOR_EMBEDDING_MODEL_ACK` to match the
current model after stored `user_knowledge` embeddings have been rebuilt or
reset; otherwise runtime falls back to Jaccard retrieval.

## Remaining Follow-Up

GitHub Dependabot alerts may remain visible until the dependency graph refreshes
after this PR lands. Treat any remaining `torch` alert against the optional
RAG/vector manifests as dependency-graph lag unless a future diff reintroduces a
tracked PyTorch dependency.

## References

- CVE: `https://www.cve.org/CVERecord?id=CVE-2025-3000`
- NVD: `https://nvd.nist.gov/vuln/detail/CVE-2025-3000`
- GitHub Advisory Database: `https://github.com/advisories/GHSA-rrmf-rvhw-rf47`
- OSV: `https://osv.dev/vulnerability/GHSA-rrmf-rvhw-rf47`
