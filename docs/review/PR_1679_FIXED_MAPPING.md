# PR 1679 Fixed Mapping

**PR:** <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1679>
**Branch:** `release/release-control-plane-pr4-build-equivalence`
**Release-control-plane slice:** PR-4 build equivalence check
**Canonical commit:** `56c94adda`
**Latest review-fix commit:** `1a1878444`

## Scope

PR-4 adds an internal deterministic build-equivalence checker for App Review
build identity versus production-candidate build identity. It consumes the PR-3
`release-manifest.v1` contract and compares build identity, artifact digest,
release manifest hash, reviewer identity, ML identity, and supply-chain
identity.

Out of scope: PR-5 CI fail-closed enforcement, workflow mutation, App Store
Connect execution, Fastlane upload mutation, backend routes, OpenAPI changes,
iOS runtime changes, RAG behavior changes, semantic cache, GraphRAG, and
product-facing behavior.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

Post-open QA, CodeRabbit, and Cubic review found actionable PR-4 contract gaps.
All are dispositioned as `FIXED` below before resolving any review thread.

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1679 -> 789d03ceb
Disposition: FIXED
Commit: 789d03ceb
Evidence: `scripts/release/build_equivalence.py` now turns missing review or production build identity files into deterministic `BLOCK` decisions with stable missing-identity reason codes, and now compares manifest-present `reviewer_identity`, `ml_identity`, and `supply_chain_identity` even when both build identity artifacts omit those snapshots; `tests/test_build_equivalence.py` covers missing review/prod identity files writing `BLOCK` output and omitted manifest identity snapshots returning deterministic identity mismatch reasons.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1679#discussion_r3194675016 -> 1a1878444
Disposition: FIXED
Commit: 1a1878444
Evidence: `docs/release/BUILD_EQUIVALENCE_CONTRACT.schema.json` constrains `reason_codes` and `compared_fields` with `$defs` enums and `uniqueItems`, preserving deterministic schema validation for known PR-4 output values.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1679#discussion_r3194675029 -> 1a1878444
Disposition: FIXED
Commit: 1a1878444
Evidence: `docs/roadmap/BACKLOG_LEDGER.md` now names PR #1679 in both the release-control-plane Target PR chain and PR-4 active status while preserving PR-5 as deferred.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1679#pullrequestreview-4235223961 -> 1a1878444
Disposition: FIXED
Commit: 1a1878444
Evidence: CodeRabbit review summary actionables are covered by the two inline dispositions above: schema enum hardening and ledger PR #1679 traceability.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1679#discussion_r3194676918 -> 1a1878444
Disposition: FIXED
Commit: 1a1878444
Evidence: `scripts/release/build_equivalence.py` now attributes malformed production-candidate validation values to `production_candidate` in `mismatch_details`; `tests/test_build_equivalence.py` covers the production-candidate schema-version malformed case.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1679#pullrequestreview-4235226467 -> 1a1878444
Disposition: FIXED
Commit: 1a1878444
Evidence: Cubic review summary actionable is covered by the inline disposition above: malformed production-candidate validation errors are no longer emitted under `review_build`.

## Validation

- `python3 scripts/orchestration/check_preflight.py` PASS
- `python3 scripts/orchestration/check_agent_consistency.py` PASS
- `python3 scripts/orchestration/task_bootstrap.py --goal "Release control plane PR-4: build equivalence check" --task-class Orchestration --pr-phase pre_open --path docs/roadmap/BACKLOG_LEDGER.md --path docs/release/BUILD_EQUIVALENCE_CONTRACT.md --path docs/release/BUILD_EQUIVALENCE_CONTRACT.schema.json --path scripts/release/build_equivalence.py --path tests/test_build_equivalence.py --path docs/release/RELEASE_CONTROL_PLANE_EPIC.md --path docs/orchestration/RELEASE_CONTROL_PLANE_TASK_PACKET_2026-04-29.md --requested-agent ...` PASS, packet `4dcaa5e6be7d`
- `python3 scripts/orchestration/task_bootstrap.py --goal "Release control plane PR-4 post-open review: build equivalence check" --task-class Orchestration --pr-phase post_open_review --path docs/roadmap/BACKLOG_LEDGER.md --path docs/release/BUILD_EQUIVALENCE_CONTRACT.md --path docs/release/BUILD_EQUIVALENCE_CONTRACT.schema.json --path scripts/release/build_equivalence.py --path tests/test_build_equivalence.py --path docs/release/RELEASE_CONTROL_PLANE_EPIC.md --path docs/orchestration/RELEASE_CONTROL_PLANE_TASK_PACKET_2026-04-29.md --path docs/review/PR_1679_FIXED_MAPPING.md --requested-agent ...` PASS, packet `81b582fc6671`
- `/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python -m pytest -q tests/test_build_equivalence.py` PASS (`22 passed`) after `1a1878444`
- `/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python -m pytest -q tests/test_release_manifest.py` PASS (`20 passed`)
- `/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python -m pytest -q tests/test_repo_policy_guards.py` PASS (`14 passed`)
- `python3 scripts/ci/check_docs_phase1_gates.py --files docs/release/BUILD_EQUIVALENCE_CONTRACT.md docs/release/BUILD_EQUIVALENCE_CONTRACT.schema.json docs/release/RELEASE_CONTROL_PLANE_EPIC.md docs/orchestration/RELEASE_CONTROL_PLANE_TASK_PACKET_2026-04-29.md docs/roadmap/BACKLOG_LEDGER.md` PASS
- `VENV_PYTHON=/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python make validate-changed` PASS (`tests/test_build_equivalence.py`, `18 passed`) before `789d03ceb`
- `VENV_PYTHON=/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python /Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/pre-commit run --all-files` PASS before `789d03ceb`
- Push-time hooks PASS before PR open: changed-file mypy, pip-audit, backend pre-push tests, full-repo Bandit, Docker build test

## Machine-Heavy Deferral

Full local `make verify` was intentionally not run per operator CPU constraint.
This PR follows the operator-approved machine-heavy exception path: narrow local
gates plus current-head GitHub CI before any merge-ready claim.

## Merge Readiness

- [ ] PR is ready for review and no longer draft.
- [ ] Current-head required CI is green with no pending required checks.
- [ ] CodeRabbit/Sourcery/Cubic actionable comments are dispositioned.
- [ ] Strict merge readiness gate passes with auth.
