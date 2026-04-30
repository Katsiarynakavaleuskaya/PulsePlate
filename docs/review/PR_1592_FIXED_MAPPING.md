# PR 1592 Fixed in Commit Mapping

**PR:** https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1592
**Branch:** `release/release-control-plane-pr1-reviewer-hash`
**Base:** `main`
**Release-control-plane slice:** PR-1 reviewer-packet hash contract

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

No human, CodeRabbit, Sourcery, or Cubic actionable review threads were present
when this canonical mapping artifact was created. This file must be updated
before any review thread is resolved.

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1592#pullrequestreview-4203576058 -> 0259cf5b4
Disposition: FIXED
Commit: 0259cf5b4
Evidence: `scripts/release/reviewer_packet_hashes.py` aggregates missing metadata files, reports UTF-8 decode context, and derives the digest from `HASH_ALGORITHM`; `tests/test_release_reviewer_packet_hashes.py` covers ordering and missing-file diagnostics.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1592#discussion_r3166579076 -> 0259cf5b4
Disposition: FIXED
Commit: 0259cf5b4
Evidence: `scripts/release/reviewer_packet_hashes.py` includes artifact path context in UTF-8 decode failures; `tests/test_release_reviewer_packet_hashes.py` covers the diagnostic.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1592#discussion_r3166579122 -> 0259cf5b4
Disposition: FIXED
Commit: 0259cf5b4
Evidence: `scripts/release/reviewer_packet_hashes.py` uses `hashlib.new(HASH_ALGORITHM, payload)` so the emitted algorithm and digest behavior stay aligned.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1592#discussion_r3166579154 -> 0259cf5b4
Disposition: FIXED
Commit: 0259cf5b4
Evidence: `tests/test_release_reviewer_packet_hashes.py` covers deterministic `metadata_artifact_paths` ordering.

## Implementation Evidence

Disposition: FIXED
Commit: 49eb4162e
Evidence:

- `docs/release/REVIEWER_PACKET_HASH_CONTRACT.md`
- `docs/release/REVIEWER_PACKET_HASH_CONTRACT.schema.json`
- `scripts/release/reviewer_packet_hashes.py`
- `tests/test_release_reviewer_packet_hashes.py`

## Local Gate Evidence

- `python3 scripts/orchestration/check_preflight.py` PASS
- `python3 scripts/orchestration/check_agent_consistency.py` PASS
- `pytest -q tests/test_release_reviewer_packet_hashes.py` PASS
- `pytest -q tests/test_ios_appstore_asset_validators.py tests/test_ios_appstore_assets_workflow_contract.py` PASS
- `pytest -q tests/test_repo_policy_guards.py` PASS
- `VENV_PYTHON=/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python make validate-changed` PASS
- `pre-commit run --all-files` PASS
- Pre-push hooks PASS: formatting, ruff, changed-file mypy, pip-audit,
  backend pre-push tests, full-repo Bandit, docker build test

## Merge Readiness

Full local `make verify` was intentionally not run under operator-approved
machine-heavy deferral to avoid CPU-heavy local execution. Before this PR can be
marked ready, current-head GitHub CI parity and the strict merge-readiness
wrapper must pass, and all review/bot actionables must have explicit
dispositions in this artifact and in the PR body mirror.

## Deferred / Follow-ups

None for PR-1. Later release-control-plane slices own RAG/ML gate export,
release manifest generation, build equivalence, and CI release decision
integration.
