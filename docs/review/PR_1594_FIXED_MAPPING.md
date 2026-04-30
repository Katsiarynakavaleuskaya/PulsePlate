# PR #1594 - Fixed in Commit Mapping (canonical)

## Discussion Thread Pass

Canonical review-governance artifact and PR-body mirror requirements:
`AGENTS.md`; `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md`;
`docs/orchestration/AGENTS.md`.

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1594#pullrequestreview-4203461409 -> 694c6eb25
Disposition: FIXED
Commit: 694c6eb25
Evidence: `tests/core/evidence/test_fingerprints.py` asserts the full lowercase `sha256:[0-9a-f]{64}` format, and `tests/core/evidence/test_assets.py` varies `policy_version` in the identity-scope uniqueness test.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1594#pullrequestreview-4203441788
Disposition: NOT-A-BUG
Evidence: Sourcery reported a service-side weekly diff-character rate limit. No repo code or PR scope change is requested.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1594#pullrequestreview-4203472985
Disposition: NOT-A-BUG
Evidence: Codex connector posted informational review metadata without actionable suggestions.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1594#issuecomment-4350691456
Disposition: NOT-A-BUG
Evidence: CodeRabbit docstring coverage is not a required repository merge gate; public `core/evidence` helpers introduced by E1 have docstrings, and required local gates are listed below.

## Post-open Agent Review

`qa-engineer-agent` found that raw `upstream_ids` could bypass rail separation by
passing an advisory `evidence:...` id into a runtime asset.

Disposition: FIXED
Commit: 3f26a6409
Evidence: `core/evidence/policies.py` validates raw canonical evidence upstream ids against the target rail, `core/evidence/assets.py` applies that validation after upstream-id normalization, and `tests/core/evidence/test_assets.py` covers the bypass case.

`bug-hunter` found that colon-delimited `version` values could create asset IDs
that later failed canonical parsing, and that raw `evidence:` upstream IDs did
not validate the 24-character lowercase hex digest shape.

Disposition: FIXED
Commit: 75dd48bb2
Evidence: `core/evidence/policies.py` rejects colon-delimited tokens and validates raw canonical evidence upstream-id digests as 24 lowercase hex characters; `tests/core/evidence/test_assets.py` covers same-rail upstream refs, colon-token rejection, and malformed raw evidence IDs.

Current-head `diff-coverage` failed because the CI coverage artifact did not
run the new focused `tests/core/evidence` suite, so the new `core/evidence`
modules appeared as uncovered despite local targeted tests passing.

Disposition: FIXED
Commit: f52c5a06e
Evidence: `.github/workflows/ci.yml` includes `tests/core/evidence` in both PR and feature critical smoke coverage runs; local `tests/core/evidence` and workflow governance tests pass.

## Initial Implementation Commits

- `64ba7a6fc` - `feat(metadata): add evidence asset registry`
- `bc0991aa0` - `docs(review): add PR 1594 mapping`
- `694c6eb25` - `test(evidence): harden asset registry contracts`
- `3f26a6409` - `fix(evidence): reject cross-rail raw upstream ids`
- `75dd48bb2` - `fix(evidence): harden evidence asset id parsing`
- `f52c5a06e` - `ci(evidence): include asset registry in coverage smoke`

## Coordinator Packet

- Pre-open packet: `artifacts/orchestration/task_packets/95e7f0962991.json`
  (local/gitignored, intentionally not committed).
- Post-open packet: `artifacts/orchestration/task_packets/d62dc7d03c3f.json`
  (local/gitignored, intentionally not committed).

## Role Order

Coordinator-owned role order:

1. `agent-coordinator`
2. `cursor-specialist-agent`
3. `architecture-specialist`
4. `rag-systems-agent`
5. `data-scientist-agent`
6. `security-auditor`
7. `qa-engineer-agent`
8. `bug-hunter`

Mandatory post-open review lane:

1. `qa-engineer-agent`
2. `bug-hunter`

## Local Validation

- `python3 scripts/orchestration/check_preflight.py` PASS.
- `python3 scripts/orchestration/check_agent_consistency.py` PASS.
- `. .venv/bin/activate && pytest -q tests/core/evidence` PASS
  (`21 passed`) after CodeRabbit test-hardening fixes and the post-open
  `qa-engineer-agent` / `bug-hunter` fixes.
- `. .venv/bin/activate && pytest -q tests/core/evidence tests/test_ci_workflow_pr_size_governance_contract.py`
  PASS (`30 passed`) after the CI coverage-routing fix.
- `. .venv/bin/activate && python -m mypy --no-incremental --cache-dir=/dev/null core/evidence tests/core/evidence`
  PASS (`Success: no issues found in 6 source files`) after CodeRabbit
  test-hardening fixes.
- `pre-commit run --all-files` PASS after the CI coverage-routing fix.
- Commit hook PASS.
- Pre-push changed-file mypy PASS.
- Pre-push pip-audit PASS.
- Pre-push backend pytest PASS.
- Pre-push full Bandit PASS.
- Pre-push docker build test PASS.

## Machine-Heavy Gate Note

Operator explicitly stopped local `make verify` for this lane because it was
causing CPU pressure. This PR must remain draft / not merge-ready until
current-head GitHub CI and strict merge-readiness checks provide the heavy
signal, or the operator later approves the full local run.

## Deferred / Follow-ups

- E2 unified eval event schema.
- E3 knowledge promotion ledger + replay.
- E4 active metadata admission.
- E5 advisory wiki evidence bridge.
- Semantic cache remains blocked until asset lineage, replay-safe promotion,
  metadata admission gates, and the dedicated semantic-cache gate exist.

## Review Notes

No actionable human or bot review comments are present at artifact creation.
Record every later actionable comment in `Fixed in Commit Mapping` before
resolving threads on GitHub.
