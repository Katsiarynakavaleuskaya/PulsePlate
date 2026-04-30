# PR 1605 Fixed Mapping

**PR:** <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1605>
**Branch:** `release/release-control-plane-pr3-release-manifest`
**Release-control-plane slice:** PR-3 release manifest generator and validator
**Canonical commit:** `998664069`
**Latest review-fix commit:** `bae29dc40`

## Scope

PR-3 adds the internal release manifest generator and validator for the
release-control-plane line. It consumes PR-1 reviewer packet hashes and PR-2
RAG gate result exports, records build and supply-chain identity, and computes
a fail-closed `ALLOW` / `BLOCK` decision.

Out of scope: App Store upload behavior, RAG threshold/runtime changes, backend
APIs, OpenAPI, PR-4 build equivalence, and PR-5 CI release-decision enforcement.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

Codex and CodeRabbit review threads are dispositioned as `FIXED` below. New
actionable review comments must be dispositioned here first as `FIXED`,
`NOT-A-BUG`, or `DEFERRED` before any thread is resolved.

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1605#discussion_r3168909585
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1605#discussion_r3168909592
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1605#discussion_r3168929124
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1605#discussion_r3168929086
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1605#discussion_r3169033949
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1605#discussion_r3169033954
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1605#pullrequestreview-4206288583
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1605#pullrequestreview-4206404870
Disposition: FIXED
Commit: see mapping entries below
Evidence: `scripts/release/release_manifest.py` rejects missing `reviewer_identity.source_artifacts` / `ml_identity.source_artifacts`, validates source artifact `kind`, wraps unreadable JSON inputs in `ReleaseManifestError`, and validates upstream RAG export `hash_algorithm`, canonicalization, and non-empty `source_artifacts`; `docs/release/RELEASE_MANIFEST_CONTRACT.md` now carries file-line evidence anchors; `tests/test_release_manifest.py` covers missing source artifacts, invalid artifact kind, unreadable inputs, invalid provenance digest, and malformed RAG gate metadata.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1605#discussion_r3168909585 -> 1697feb5b
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1605#discussion_r3168909592 -> 1697feb5b
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1605#discussion_r3168929124 -> 1697feb5b
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1605#discussion_r3168929086 -> 3a647ee35
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1605#discussion_r3169033949 -> bae29dc40
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1605#discussion_r3169033954 -> bae29dc40
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1605#pullrequestreview-4206288583 -> bae29dc40
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1605#pullrequestreview-4206404870 -> bae29dc40

## Validation

- `python3 scripts/orchestration/check_preflight.py` PASS
- `python3 scripts/orchestration/check_agent_consistency.py` PASS
- `python3 scripts/orchestration/task_bootstrap.py --goal "Release control plane PR-3: release manifest generator and validator" --task-class Orchestration --pr-phase pre_open --requested-agent ...` PASS
- `python3 scripts/orchestration/task_bootstrap.py --goal "Release control plane PR-3 post-open review: release manifest generator and validator" --task-class Orchestration --pr-phase post_open_review --requested-agent ...` PASS
- `pytest -q tests/test_release_manifest.py tests/test_release_reviewer_packet_hashes.py tests/test_rag_release_gates_runner.py` PASS
- `pytest -q tests/test_repo_policy_guards.py` PASS
- `python3 scripts/ci/check_docs_phase1_gates.py --files docs/orchestration/RELEASE_CONTROL_PLANE_TASK_PACKET_2026-04-29.md docs/release/RELEASE_CONTROL_PLANE_EPIC.md docs/release/RELEASE_MANIFEST_CONTRACT.md docs/release/RELEASE_MANIFEST_CONTRACT.schema.json docs/roadmap/BACKLOG_LEDGER.md` PASS
- `VENV_PYTHON=/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python make validate-changed` PASS
- `pre-commit run --all-files` PASS
- `pytest -q tests/test_release_manifest.py` PASS after `1697feb5b`
- `python3 scripts/ci/check_docs_phase1_gates.py --files docs/release/RELEASE_MANIFEST_CONTRACT.md docs/release/RELEASE_MANIFEST_CONTRACT.schema.json` PASS after `1697feb5b`
- `pytest -q tests/test_release_manifest.py` PASS after `3a647ee35`
- `pytest -q tests/test_release_manifest.py` PASS after `bae29dc40`
- `python3 scripts/ci/check_docs_phase1_gates.py --files docs/release/RELEASE_MANIFEST_CONTRACT.md docs/review/PR_1605_FIXED_MAPPING.md` PASS after `bae29dc40`
- Push-time hooks PASS: mypy changed files, backend pre-push, full-repo Bandit, Docker build test

## Machine-Heavy Deferral

Full local `make verify` was intentionally not run per operator CPU constraint.
This PR follows the operator-approved machine-heavy exception path: narrow
local gates plus current-head GitHub CI before any merge-ready claim.

## Merge Readiness

- [ ] PR is ready for review and no longer draft.
- [ ] Current-head required CI is green with no pending required checks.
- [ ] CodeRabbit/Sourcery/Cubic actionable comments are dispositioned.
- [ ] Strict merge readiness gate passes with auth.
