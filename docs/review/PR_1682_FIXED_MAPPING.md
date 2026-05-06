# PR 1682 Fixed Mapping

**PR:** <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1682>
**Branch:** `release/release-control-plane-pr5-ci-gates`
**Release-control-plane slice:** PR-5 CI release decision integration
**Canonical commit:** `eb798b4d9`
**Latest review-fix commit:** `eb798b4d9`

## Scope

PR-5 adds a deterministic release-control-plane CI checker for release manifest,
RAG gate result, build-equivalence result, and supply-chain evidence. It also
wires a non-secret fixture validation job into CD without changing production
deploy dependencies, App Store upload behavior, Fastlane, runtime/API/OpenAPI,
iOS runtime, RAG behavior, semantic cache, GraphRAG, or product-facing behavior.

## Discussion Thread Pass

- [ ] Discussion-thread pass completed
- [ ] Fixed in commit mapping completed

Post-open review is in progress. No human or bot review thread has been
resolved without disposition evidence.

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1682 -> eb798b4d9
Disposition: FIXED
Commit: eb798b4d9
Evidence: Pre-push MyPy found `_sha256_file(...)` returning an `Any`-typed value in `scripts/ci/check_release_control_plane.py`; commit `eb798b4d9` fixed the type boundary without suppression. Evidence commands after the fix: `. .venv/bin/activate && mypy --no-incremental --cache-dir=/dev/null scripts/ci/check_release_control_plane.py` PASS, `. .venv/bin/activate && pytest -q tests/test_release_control_plane_ci_gate.py` PASS (`19 passed`), `make validate-changed` PASS (`41 passed`), `pre-commit run --all-files` PASS, and pre-push hooks PASS.

## Premortem

- [x] Premortem pass completed against actual changed files
- [x] All P0/P1 premortem findings fixed or dispositioned as NOT-A-BUG with evidence
- [x] P2 findings, if any, are linked in BACKLOG_LEDGER.md

Artifact: [`docs/review/PR_1682_PREMORTEM.md`](PR_1682_PREMORTEM.md)

## Validation

- `python3 scripts/orchestration/check_preflight.py` PASS
- `python3 scripts/orchestration/check_agent_consistency.py` PASS
- `python3 scripts/orchestration/task_bootstrap.py --goal "Release control plane PR-5: CI release decision integration" --task-class Orchestration --pr-phase pre_open --path docs/roadmap/BACKLOG_LEDGER.md --path docs/release/RELEASE_CONTROL_PLANE_CI_GATE.md --path scripts/ci/check_release_control_plane.py --path tests/test_release_control_plane_ci_gate.py --path docs/release/RELEASE_CONTROL_PLANE_EPIC.md --path docs/orchestration/RELEASE_CONTROL_PLANE_TASK_PACKET_2026-04-29.md --path .github/workflows/cd.yml --requested-agent ...` PASS, packet `0ddd1b459d6d`
- `python3 scripts/orchestration/task_bootstrap.py --goal "Release control plane PR-5 post-open review: CI decision integration" --task-class Orchestration --pr-phase post_open_review --requested-agent qa-engineer-agent --requested-agent bug-hunter --requested-agent premortem-facilitator --requested-agent security-auditor` PASS, packet `f6116f0353a4`
- `. .venv/bin/activate && pytest -q tests/test_release_control_plane_ci_gate.py` PASS (`19 passed`)
- `. .venv/bin/activate && pytest -q tests/test_release_manifest.py` PASS (`20 passed`)
- `. .venv/bin/activate && pytest -q tests/test_build_equivalence.py` PASS (`22 passed`)
- `. .venv/bin/activate && pytest -q tests/test_rag_release_gates_runner.py` PASS (`48 passed`)
- `. .venv/bin/activate && pytest -q tests/test_check_docker_provenance_attestation.py` PASS (`12 passed`)
- `. .venv/bin/activate && pytest -q tests/test_repo_policy_guards.py` PASS (`14 passed`)
- `python3 scripts/ci/check_docs_phase1_gates.py --files docs/release/RELEASE_CONTROL_PLANE_CI_GATE.md docs/release/RELEASE_CONTROL_PLANE_CI_GATE.schema.json docs/release/RELEASE_CONTROL_PLANE_EPIC.md docs/orchestration/RELEASE_CONTROL_PLANE_TASK_PACKET_2026-04-29.md docs/roadmap/BACKLOG_LEDGER.md` PASS
- `make validate-changed` PASS (`41 passed`)
- `pre-commit run --all-files` PASS
- Pre-push hooks PASS, including changed-file MyPy, pip-audit, backend pre-push tests, full-repo Bandit, and docker build test

## Machine-Heavy Deferral

Full local `make verify` was intentionally not run per operator instruction.
This PR follows the bounded local gate path with focused tests,
`make validate-changed`, pre-commit, and current-head PR CI before any
merge-readiness claim.

## Merge Readiness

- [ ] PR is ready for review and no longer draft.
- [ ] Current-head required CI is green with no pending required checks.
- [ ] CodeRabbit/Sourcery/Cubic actionable comments are dispositioned.
- [ ] Discussion-thread pass is complete.
- [ ] Strict merge readiness gate passes with auth.
