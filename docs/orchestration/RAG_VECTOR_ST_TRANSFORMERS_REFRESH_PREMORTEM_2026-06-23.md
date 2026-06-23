# Optional RAG Vector Dependency Refresh Premortem

Mode: `pr-premortem`
Packet: `artifacts/orchestration/task_packets/5f2e0dae1cd5.json`
Branch: `codex/rag-vector-st-transformers-refresh`
Date: 2026-06-23

## Summary

This PR refreshes only the optional RAG/vector dependency profile by moving
`sentence-transformers` to `5.6.0` and `transformers` to `5.12.1`.

Failure frame: it is 48 hours from now, this dependency refresh made the
security/dependency lane worse, and we are looking backward to understand why.

## Findings

### 1. Platform resolver drift widens the lockfile diff

Failure story: local `pip-compile` resolves the optional ML stack differently
from the original platform-sensitive lock closure. The PR appears to update two
direct pins, but it silently removes CUDA/Triton packages or changes
`torch==2.11.0+cpu` to a non-CPU build.

Underlying assumption: local lock regeneration is platform-neutral for PyTorch
profiles.

Early warning signs:

- `requirements-rag-vector.txt` changes CUDA/NVIDIA/Triton package rows.
- `requirements-rag-vector-cpu.txt` changes `torch==2.11.0+cpu`.

Containment action: keep the compiled lockfile closure unchanged except for the
two direct RAG pins, and scan the final diff for `torch`, `pgvector`, CUDA,
Triton, private index URLs, local paths, and direct URLs.

Disposition: FIXED

Evidence:

- `requirements-rag-vector.txt` changes only `sentence-transformers==5.6.0` and
  `transformers==5.12.1`.
- `requirements-rag-vector-cpu.txt` changes only `sentence-transformers==5.6.0`
  and `transformers==5.12.1`; `torch==2.11.0+cpu` remains unchanged.
- Local scan: no private/local/direct URL leakage in RAG vector inputs/locks.

### 2. Retired fallback remains active after the direct pin bump

Failure story: the direct pins move to `sentence-transformers==5.6.0`, but the
emergency manifest still carries the stale `sentence-transformers==5.5.1` wheel.
That creates false confidence in fallback coverage and keeps a public exact-wheel
exception alive after the approved proxy serves the new version.

Underlying assumption: emergency fallback entries can lag direct pins without
affecting install governance.

Early warning signs:

- `scripts/ci/emergency_python_wheels.json` still contains package
  `sentence-transformers`.
- Fallback tests still read the active manifest for the expected
  `sentence-transformers` version.

Containment action: retire the stale emergency entry after approved proxy proof,
and convert the test to the existing "retired after proxy sync" pattern.

Disposition: FIXED

Evidence:

- Approved proxy probe served `sentence_transformers-5.6.0-py3-none-any.whl` and
  `transformers-5.12.1-py3-none-any.whl`.
- `scripts/ci/emergency_python_wheels.json` no longer contains
  `sentence-transformers`.
- `tests/test_install_locked_python_requirements.py` asserts no active
  `sentence-transformers` fallback and checks all RAG vector surfaces use
  `5.6.0`.

### 3. Torch audit finding is accidentally treated as part of this PR

Failure story: `pip-audit` reports `torch 2.11.0 CVE-2025-3000` in
`requirements-rag-vector.txt`, causing the RAG/vector refresh to expand into the
separate Torch advisory lane. The PR then either widens scope or claims a green
audit while a known out-of-scope alert remains.

Underlying assumption: every audit finding in the touched optional profile must
be fixed by this PR.

Early warning signs:

- `pip-audit --no-deps --disable-pip -r requirements-rag-vector.txt` reports
  `torch 2.11.0 CVE-2025-3000` with no fix version.
- Any diff changes `torch`, `requirements-ci-lite.txt`, runtime, Docker, or
  shared lockfiles.

Containment action: keep `torch` unchanged, document the raw audit finding, and
tie it to the existing deferred Torch advisory lane.

Disposition: DEFERRED

Backlog:

- `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-pytorch-jit-cve-2025-3000-vector-profile`

Evidence:

- `docs/security/DEPENDABOT_ALERT_INVENTORY.md` lists alerts `#160`, `#161`,
  and `#162` as DEFERRED / monitored with no GHSA fixed version.
- `docs/security/PYTORCH_JIT_CVE_2025_3000_ADVISORY.md` keeps Torch remediation
  in the future advisory lane.

## Revised Plan

- Keep this PR to optional RAG/vector direct pins and fallback retirement only.
- Do not update `torch`, `pgvector`, runtime, Docker, CI-lite, dev/test, or
  shared full-lock surfaces.
- Use focused local gates, `make validate-changed`, and `pre-commit run
  --all-files`; document the operator-approved full `make verify` deferral in
  the PR body and fixed mapping.
- Use current-head CI as the heavy parity signal after PR open.

## Pre-Merge Checklist

- Approved proxy proof for `sentence-transformers==5.6.0` and
  `transformers==5.12.1`.
- Final lockfile diff changes only those two direct pins.
- Emergency manifest has no active `sentence-transformers` fallback.
- Focused pytest bundle passes.
- `make validate-changed` and `pre-commit run --all-files` pass.
- PR body and `docs/review/PR_<N>_FIXED_MAPPING.md` document local
  `make verify` deferral and the out-of-scope Torch audit finding.

## Decision

Decision: `proceed with changes`

The plan is sound after preserving the platform-sensitive lock closure,
retiring the stale fallback, and documenting the existing Torch advisory as a
deferred separate lane.
