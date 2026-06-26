# PR #2027 Fixed in Commit Mapping SoT

PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2027

Branch: `codex/replace-torch-vector-backend`

## Summary

This PR replaces the optional PyTorch/SentenceTransformers vector backend with
lazy local FastEmbed/ONNX embeddings while preserving the existing 768-dimensional
pgvector schema, PostgreSQL retrieval architecture, SQLite/test fallback, and
Jaccard degradation path.

## Scope

- Add `FastEmbedTextEmbeddings` as the only optional vector embedding provider.
- Replace direct optional vector pins with `fastembed==0.8.0` and
  `pgvector==0.4.2`.
- Retire the `CVE-2025-3000` pip-audit waiver by removing PyTorch from tracked
  optional vector dependency manifests.
- Add supply-chain and security guards for torch-free vector locks and retired
  waiver state.
- Add `RAG_VECTOR_EMBEDDING_MODEL_ACK` as the model-family acknowledgement fence
  before pgvector retrieval uses stored rows with the new BGE embedding family.

## Out Of Scope

No TEI/Hugging Face service deployment, OpenAI embeddings, Qdrant server,
OpenAPI/frontend/iOS changes, semantic-cache expansion, hash-verified lockfile
work, PyTorch bump, PyTorch fallback, DB migration, or automatic re-embedding
flow.

## Implementation Commits

- `0d24661a7` - commit generated detect-secrets baseline update from the
  pre-commit hook.
- `ab70cdec3` - replace the optional vector backend with FastEmbed/ONNX, refresh
  vector locks, retire the PyTorch CVE waiver, add model acknowledgement guards,
  and update tests/docs/security evidence.

## Lane Start Provenance

- Base branch: `main`
- Branch: `codex/replace-torch-vector-backend`
- Packet: `artifacts/orchestration/task_packets/7ebc86dfa6be.json`
- Role order executed pre-open:
  `agent-coordinator -> security-auditor -> backend-engineer -> ml-engineer-agent -> qa-engineer-agent -> bug-hunter -> architecture-specialist`
- Packet creation was treated as provenance/routing only; role passes were
  executed explicitly before implementation.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed
- [x] Fixed mapping artifact created after GitHub assigned PR number `#2027`.
- [x] Initial PR open: no GitHub review threads existed at artifact creation.
- [x] Post-open `qa-engineer-agent` pass completed: no actionable findings.
- [x] Post-open `bug-hunter` pass completed: no actionable findings.
- [x] Post-open `security-auditor` pass completed: no actionable findings.
- [ ] Codex Security diff scan / finding discovery is pending.
- [ ] CodeRabbit review is pending.
- [ ] `pulseplate-pr-review` is pending.
- [ ] Current-head CI complete before readiness language.
- [ ] Strict merge-readiness checks run after the final review/check cycle.

## Fixed in Commit Mapping

- No actionable review comments

## Post-Open Role Findings

Role: `qa-engineer-agent`

Disposition: NOT-A-BUG

Evidence: Post-open QA pass found no actionable findings. The pass confirmed
focused pytest coverage for FastEmbed/vector fallback and torch-free dependency
guards, and confirmed the vector requirements sweep had no retired
PyTorch/SentenceTransformers/Transformers hits.

Role: `bug-hunter`

Disposition: NOT-A-BUG

Evidence: Post-open bug-hunter pass found no actionable findings. The pass
confirmed FastEmbed normalization fails closed, model acknowledgement gating
blocks stale vector retrieval before provider/DB work, fallback preserves
degraded reasons, and supply-chain guards cover retired
torch/SentenceTransformers/Transformers surfaces.

Role: `security-auditor`

Disposition: NOT-A-BUG

Evidence: Post-open security-auditor pass found no actionable findings. The
pass confirmed the PR removes the PyTorch waiver, keeps vector locks
torch/SentenceTransformers/Transformers-free, preserves lazy FastEmbed loading,
and adds fail-closed embedding/model-ack guards without weakening audit
coverage.

## Local Validation Evidence

- `python3 scripts/orchestration/check_preflight.py` PASS.
- `python3 scripts/orchestration/check_agent_consistency.py` PASS.
- `python -m pytest -q tests/test_embeddings_provider.py tests/test_vector_rag.py`
  PASS.
- `python -m pytest -q tests/test_python_supply_chain_controls.py tests/guards/test_security_devtooling_regression_guards.py tests/test_install_locked_python_requirements.py tests/test_ci_risk_profile.py tests/test_pgvector_embedding_migration.py`
  PASS.
- `python verify_requirements.py` PASS.
- `PATH=".venv/bin:$PATH" bash scripts/ci_pip_audit.sh` PASS.
- Locked-install preflight PASS for `requirements-rag-vector.txt`.
- Locked-install preflight PASS for `requirements-rag-vector-cpu.txt`.
- `make validate-changed` PASS but selected no Python/cross-surface files, so
  focused pytest is the actual changed-surface proof.
- `pre-commit run --all-files` PASS.
- Push hooks PASS: changed-file mypy, pip-audit, backend pre-push pytest,
  full-repo Bandit, and docker build test.

## Machine-Heavy Deferral

Full local `make verify` was not run per operator request. This PR uses the
machine-heavy exception path: local focused gates passed, and current-head CI
must provide the heavy parity signal before any merge-readiness claim.
