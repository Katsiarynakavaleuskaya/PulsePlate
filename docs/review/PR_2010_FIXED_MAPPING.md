# PR #2010 Fixed in Commit Mapping

## Summary

PR: `fix(deps): bump optional RAG vector packages`

Branch: `codex/rag-vector-st-transformers-refresh`

Implementation commit: `bd6d57036`

This PR refreshes only the optional RAG/vector dependency profiles by bumping
`sentence-transformers` to `5.6.0` and `transformers` to `5.12.1`, while
preserving the existing `torch` / `pgvector` closure and retiring the stale
`sentence-transformers==5.5.1` emergency fallback after approved proxy proof.

## Lane Start Provenance

- Base branch: `main`
- Start head: `58fe0a81199e5ab0b08ecd643adc1b139a2072b7`
- Packet: `artifacts/orchestration/task_packets/5f2e0dae1cd5.json`
- Dispatch manifest:
  `agent-coordinator -> security-auditor -> qa-engineer-agent -> bug-hunter -> architecture-specialist`
- Worktree: `worktrees/rag-vector-st-transformers-refresh`

## Scope

- Updated `requirements-rag-vector.in` and `requirements-rag-vector.txt`.
- Updated `requirements-rag-vector-cpu.in` and
  `requirements-rag-vector-cpu.txt`.
- Removed the stale `sentence-transformers==5.5.1` emergency wheel artifact.
- Updated fallback guard tests and backlog evidence.
- Recorded premortem findings and dispositions for this dependency lane.

## Out Of Scope

No `torch`, `pgvector`, runtime, Docker, CI-lite, dev/test, shared full-lock,
OpenAPI, frontend, iOS, runtime RAG behavior, semantic-cache behavior,
Dependabot #2001, Dependabot #2002, Torch alerts #160/#161/#162, or Faraday
alert #224 changes.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

Sourcery review-level feedback and advisory bot comments are mapped below.

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2010#pullrequestreview-4550923707 -> a8c2a994b
Disposition: FIXED
Commit: a8c2a994b
Evidence: `tests/test_install_locked_python_requirements.py` centralizes expected optional RAG/vector package versions; `docs/orchestration/RAG_VECTOR_ST_TRANSFORMERS_REFRESH_PREMORTEM_2026-06-23.md` names the exact fallback-retirement tests and locked-installer preflight command that enforce no fallback and exact-version constraints.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2010#issuecomment-4776733404
Disposition: NOT-A-BUG
Reason: CodeRabbit's advisory docstring coverage warning applies to generated review heuristics, not a repo merge gate for this dependency/test/docs lane.
Evidence: The PR adds no production Python API or runtime callable requiring docstring coverage; the only changed Python file is `tests/test_install_locked_python_requirements.py`, where the review-requested constants at module scope centralize expected dependency versions without introducing new functions.

## Implementation Commits

- `bd6d57036` - bump optional RAG/vector direct pins, retire the stale
  `sentence-transformers` fallback, update guard tests and ledger evidence, and
  record premortem evidence.
- `cd0c9d1da` - add the PR #2010 fixed-mapping artifact.
- `a8c2a994b` - address Sourcery review feedback by centralizing expected RAG
  package versions and tightening premortem enforcement references.

Implementation evidence:

- `requirements-rag-vector.txt` changes only `sentence-transformers==5.6.0` and
  `transformers==5.12.1` among optional RAG/vector pins.
- `requirements-rag-vector-cpu.txt` changes only `sentence-transformers==5.6.0`
  and `transformers==5.12.1`; `torch==2.11.0+cpu` remains unchanged.
- `scripts/ci/emergency_python_wheels.json` no longer contains a
  `sentence-transformers` artifact.
- `tests/test_install_locked_python_requirements.py` asserts
  `sentence-transformers` fallback retirement and validates RAG surfaces use
  `5.6.0`.

## Internal Finding Dispositions

Finding: Local `pip-compile` can drift platform-sensitive ML closure.

Disposition: FIXED

Commit: bd6d57036

Evidence: The final lockfile diff preserves prior CUDA/Triton closure in
`requirements-rag-vector.txt` and preserves `torch==2.11.0+cpu` in
`requirements-rag-vector-cpu.txt`; only the two direct RAG pins changed.

Finding: Stale `sentence-transformers==5.5.1` emergency fallback could remain
active after the direct pin bump.

Disposition: FIXED

Commit: bd6d57036

Evidence: Approved proxy probe served
`sentence_transformers-5.6.0-py3-none-any.whl` and
`transformers-5.12.1-py3-none-any.whl`; the stale manifest artifact was removed
and the guard test now requires no active `sentence-transformers` fallback.

Finding: `pip-audit` reports the existing out-of-scope Torch CVE in
`requirements-rag-vector.txt`.

Disposition: DEFERRED

Backlog:

- `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-pytorch-jit-cve-2025-3000-vector-profile`

Evidence:

- `docs/security/DEPENDABOT_ALERT_INVENTORY.md` lists alerts `#160`, `#161`,
  and `#162` as DEFERRED / monitored with no GHSA fixed version.
- `docs/security/PYTORCH_JIT_CVE_2025_3000_ADVISORY.md` keeps Torch remediation
  in the future advisory lane.

Finding: `pulseplate-pr-review` dry-run report flagged large-diff review risk
because this dependency/governance PR changes more than 300 lines.

Disposition: NOT-A-BUG

Evidence: The diff size is driven by lockfile/governance evidence rather than a
runtime/API expansion: the changed files are limited to RAG/vector requirements,
the emergency wheel manifest, dependency guard tests, `.secrets.baseline`, and
review/ledger/premortem docs. The PR body and this artifact document the split
rationale, out-of-scope lanes, local `make verify` deferral, and focused gates;
`make validate-changed`, `pre-commit run --all-files`, focused pytest, installer
preflight, and Codex Security diff scan all passed for the scoped surface.

## Premortem Evidence

- Artifact:
  `docs/orchestration/RAG_VECTOR_ST_TRANSFORMERS_REFRESH_PREMORTEM_2026-06-23.md`
- Decision: `proceed with changes`
- Findings closed before PR open:
  - Platform resolver drift: FIXED.
  - Stale `sentence-transformers` fallback: FIXED.
  - Existing Torch audit finding: DEFERRED to the Torch advisory lane.

## Experiment Runner Evidence

- Packet:
  `artifacts/orchestration/experiments/pr-rag-vector-st-transformers-refresh-oracle-v2.json`
- Artifact:
  `artifacts/orchestration/experiments/results/pr-rag-vector-st-transformers-refresh-oracle-result-v2.json`
- Status: `accepted`
- Runner mode: `oracle_only_governance_reviewer`
- Contribution kind: `oracle_review`
- Co-author required: yes
- Co-author trailer included in `bd6d57036` and `cd0c9d1da`:
  `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>`

The first runner attempt was rejected because installer preflight inside the
sandbox could not access `PULSEPLATE_PYTHON_INDEX_URL` without embedding the
private proxy URL in an artifact. External installer preflight was run
separately.

## Validation

Passed locally:

- `python scripts/orchestration/check_preflight.py --path requirements-rag-vector.in --path requirements-rag-vector.txt --path requirements-rag-vector-cpu.in --path requirements-rag-vector-cpu.txt --path scripts/ci/emergency_python_wheels.json --path docs/roadmap/BACKLOG_LEDGER.md --path tests/test_install_locked_python_requirements.py`
- `python scripts/orchestration/check_agent_consistency.py`
- Approved proxy probe for `sentence-transformers==5.6.0` and
  `transformers==5.12.1`
- `python -m pytest -q tests/test_install_locked_python_requirements.py tests/test_python_supply_chain_controls.py tests/guards/test_security_devtooling_regression_guards.py tests/test_vector_rag.py tests/test_embeddings_provider.py tests/test_rag_vector_feature_flag_guard.py`
- `python scripts/ci/install_locked_python_requirements.py --requirements-profile rag-vector --rag-vector-requirements-file requirements-rag-vector.txt --emergency-wheel-manifest scripts/ci/emergency_python_wheels.json --preflight-only`
- `python scripts/ci/install_locked_python_requirements.py --requirements-profile rag-vector --rag-vector-requirements-file requirements-rag-vector-cpu.txt --emergency-wheel-manifest scripts/ci/emergency_python_wheels.json --preflight-only`
- `make validate-changed` after commit; selected
  `tests/test_install_locked_python_requirements.py` and passed.
- `pre-commit run --all-files`
- Pre-push hooks: detect-secrets, backend tests, full-repo Bandit, Docker build
  test, repo pip-audit hook
- `git diff --check HEAD~1..HEAD`
- Codex Security diff scan `9f834b76-7359-432a-9f6e-98501f517637`: completed
  with 0 reportable findings.
- `pulseplate-pr-review`: completed; advisory large-diff risk dispositioned above.

Audit notes:

- Initial plain `pip-audit -r requirements-rag-vector.txt` failed during
  resolver collection because `cuda-bindings==13.3.1` is platform/index
  specific.
- Initial plain `pip-audit -r requirements-rag-vector-cpu.txt` failed during
  resolver collection because `torch==2.11.0+cpu` is not resolvable from the
  default PyPI index.
- `pip-audit --no-deps --disable-pip -r requirements-rag-vector.txt` reported
  `torch 2.11.0 CVE-2025-3000`, which is the deferred Torch advisory lane.
- `pip-audit --no-deps --disable-pip -r requirements-rag-vector-cpu.txt`
  returned no known vulnerabilities and skipped `torch==2.11.0+cpu` because the
  CPU wheel is not found on PyPI.

Full local `make verify` was not run for this dependency/governance lane under
the operator-approved machine-heavy exception. Current-head CI is the heavy
parity signal before any readiness claim.

## Merge Readiness

Not merge-ready yet.

Required before merge:

- [ ] Current-head CI passes.
- [x] Current known bot/human review comments dispositioned.
- [x] Post-open role passes completed:
  `qa-engineer-agent -> bug-hunter -> security-auditor`.
- [x] Codex Security diff scan / finding discovery run.
- [x] `pulseplate-pr-review` completed.
- [ ] Strict merge-readiness checks pass with auth.
