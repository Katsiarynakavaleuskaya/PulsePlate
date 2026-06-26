# Premortem: Replace PyTorch Vector Backend With FastEmbed/ONNX

Mode: `pr-premortem`
Skill: `pulseplate-premortem-risk-review`
Packet: `artifacts/orchestration/task_packets/7ebc86dfa6be.json`

## Frame

It is one week after merge. The PyTorch alert is gone from repo-owned
manifests, but vector RAG either regressed quietly or the security remediation
was incomplete. This premortem records the failure modes checked before PR open.

## Scope Inspected

- `providers/embeddings.py`
- `core/rag/vector_rag.py`
- `core/rag/rag_constants.py`
- `requirements-rag-vector*.in`
- `requirements-rag-vector*.txt`
- `scripts/ci_pip_audit.sh`
- vector, embedding, install, and supply-chain tests
- security advisory, Dependabot inventory, dependency docs, and backlog item

## Failure Modes

### P1: Dimension compatibility is mistaken for semantic compatibility

**Failure story:** The PR keeps `VECTOR(768)` and swaps MPNet to BGE, but
existing `user_knowledge.embedding` rows are still served as if both model
families shared the same vector space.

**Containment:** Runtime vector retrieval now requires
`RAG_VECTOR_EMBEDDING_MODEL_ACK` to equal the active model,
`BAAI/bge-base-en-v1.5`. Without that acknowledgement, `FEATURE_RAG_VECTOR=true`
falls back to Jaccard without provider or DB vector work.

Disposition: FIXED by the model acknowledgement guard and vector tests.

### P1: PyTorch returns through the optional vector dependency closure

**Failure story:** Direct pins are removed, but lock regeneration keeps a
transitive PyTorch, CUDA, Triton, SentenceTransformers, Transformers, or PyTorch
index path.

**Containment:** Both vector locks were regenerated through the approved Python
proxy with `fastembed==0.8.0` and `pgvector==0.4.2`. Supply-chain guards assert
that the default, runtime, CI-lite, Docker, full, and optional vector profiles do
not reintroduce the retired backend packages.

Disposition: FIXED by lock regeneration and supply-chain tests.

### P1: Security waiver remains after backend removal

**Failure story:** The dependency is gone, but `scripts/ci_pip_audit.sh` still
ignores `CVE-2025-3000`, leaving future regressions invisible.

**Containment:** The helper now scans vector manifests without `--ignore-vuln`,
and regression guards fail if the waiver or CVE-specific constant returns.

Disposition: FIXED by audit helper and guard updates.

### P2: FastEmbed load behavior breaks OpenAPI/import-time safety

**Failure story:** The provider imports or initializes the model at import time,
causing network/cache side effects during app startup or OpenAPI generation.

**Containment:** `FastEmbedTextEmbeddings` imports `TextEmbedding` only inside
`_load_model()` and creates the model on first `encode()`. Unit tests cover lazy
construction, empty input, shape normalization, wrong dimensions, and non-finite
outputs.

Disposition: FIXED by provider tests.

### P2: PR widens into service extraction or migration work

**Failure story:** The torch remediation becomes a TEI/Qdrant/OpenAI embedding
service migration or a DB backfill PR, increasing cost and review risk.

**Containment:** This PR stays at the existing adapter and pgvector retrieval
seams. No DB migration, OpenAPI change, frontend/iOS change, semantic-cache
expansion, or service extraction is included.

Disposition: NOT-A-BUG for this PR scope; service boundary and backfill remain
deferred until usage/latency or product need justifies them.

## Required Validation

- `python3 scripts/orchestration/check_preflight.py`
- `python scripts/orchestration/check_agent_consistency.py`
- focused embedding/vector pytest
- focused supply-chain, install, risk-profile, and pgvector migration pytest
- `python verify_requirements.py`
- `bash scripts/ci_pip_audit.sh`
- locked-install preflight for both vector lockfiles
- literal dependency sweep over vector manifests and pip-audit helper
- `make validate-changed`
- `pre-commit run --all-files`
- Experiment Runner oracle-only governance review

## Decision

Proceed with the FastEmbed/ONNX local backend and model acknowledgement guard.
Do not claim merge-readiness until PR current-head CI, post-open role reviews,
Codex Security review, and review-thread governance are complete.
