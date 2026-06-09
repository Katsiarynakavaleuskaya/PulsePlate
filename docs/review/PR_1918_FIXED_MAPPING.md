# PR 1918 Fixed Mapping

PR: <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1918>

## Summary

This PR hardens devcontainer defaults by removing automatic workspace bootstrap,
default host Docker access, and wholesale `.env` import. It forwards only the
package-proxy variables needed for manual bootstrap after workspace trust and
adds deterministic guard coverage for the devcontainer security boundary.

## Lane Start Provenance

- Packet: `artifacts/orchestration/task_packets/3031655b8145.json`
- Branch: `codex/fix-devcontainer-auto-bootstrap-vulnerability`
- Head commit at bootstrap: `3e71d0276636003b2611e92b651c90ef9627c6a5`
- Role dispatch command executed: `python3 scripts/orchestration/role_dispatch_bridge.py --packet artifacts/orchestration/task_packets/3031655b8145.json --pretty`
- Role order executed: `agent-coordinator -> qa-engineer-agent -> bug-hunter -> security-auditor -> architecture-specialist`

## Scope

IN:

- `.devcontainer/devcontainer.json`
- `.devcontainer/docker-compose.devcontainer.yml`
- `tests/test_devcontainer_foundation.py`
- `CONTRIBUTING.md`
- `README.md`
- `docs/review/PR_1918_FIXED_MAPPING.md`

OUT:

- Runtime app/core behavior
- OpenAPI artifacts
- Docker production image behavior
- Host Docker access enablement
- Full `make verify` local execution

## Agent Execution Log

- `agent-coordinator`: FAIL until governance and stale-doc findings are fixed.
  Evidence: identified missing mapping artifact, missing PR-body mirror, and
  stale local gate text in `CONTRIBUTING.md`.
- `qa-engineer-agent`: FAIL until mapping/body and missing `containerEnv`
  negative coverage are fixed; post-fix QA also found stale PR-body wording and
  an actionable Sourcery lifecycle-hook guard suggestion.
- `bug-hunter`: FAIL until mapping/body, stale `CONTRIBUTING.md`, and
  `containerEnv` guard coverage are fixed.
- `security-auditor`: FAIL until `devcontainer.json` secret-forwarding guard
  coverage and Phase2 governance artifact are fixed.
- `architecture-specialist`: FAIL until duplicated stale thresholds in
  `CONTRIBUTING.md` are replaced with canonical gate references.

## Skill Execution Log

- `pulseplate-workflow`: coordinator-first workflow, PR-state inspection, and
  current-head CI failure triage.
- `pulseplate-orchestration-dispatch`: generated dispatch manifest from packet
  `3031655b8145`.
- `pulseplate-premortem-risk-review`: decision `block until fixed` until this
  artifact, PR-body mirror, stale-doc cleanup, and `containerEnv` guard coverage
  are complete.
- `pulseplate-pr-review`: pending after implementation fixes and local gates.

## Premortem Findings

- Missing review mapping artifact/body mirror can block Phase2 and merge
  readiness gates.
  - Disposition: FIXED
  - Evidence: this artifact and PR body mirror are added for PR #1918.
- Stale local gate documentation can steer contributors away from canonical
  `AGENTS.md` / `RUNBOOK_AGENT.md` requirements.
  - Disposition: FIXED
  - Evidence: `CONTRIBUTING.md` now points to canonical gate sources and avoids
    duplicating Python-version or coverage thresholds.
- `devcontainer.json` could later forward app or CI secrets via `containerEnv`
  without deterministic test failure.
  - Disposition: FIXED
  - Evidence: `tests/test_devcontainer_foundation.py` adds a focused
    `containerEnv` secret-exclusion and localEnv allowlist guard.
- Full local `make verify` is deferred by operator request.
  - Disposition: NOT-A-BUG
  - Evidence: user explicitly instructed not to run full `make verify`; this PR
    uses narrow local gates plus current-head CI parity before readiness claims.

## Experiment Runner Evidence

- Not applicable: this PR is a focused security/governance remediation driven by
  deterministic CI failures and role-agent review findings; no Experiment Runner
  artifact materially shaped code or commit decisions.

## Risk Fix Matrix

| Risk ID | Failure mode | Fix | Regression test | Evidence command | Fix commit SHA | Evidence | Disposition |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `DEVCONTAINER-001` | Opening a devcontainer auto-runs repository-controlled bootstrap before workspace trust. | Removed automatic `postCreateCommand` and added a guard against auto-execution hooks. | `test_devcontainer_json_does_not_auto_execute_workspace_bootstrap` | `.venv/bin/python -m pytest -q tests/test_devcontainer_foundation.py` | `5d854a074` | `.devcontainer/devcontainer.json`; `tests/test_devcontainer_foundation.py` | FIXED |
| `DEVCONTAINER-002` | Default devcontainer exposes host Docker daemon access. | Removed Docker-outside-of-Docker feature and guards against Docker socket features. | `test_devcontainer_json_does_not_enable_host_docker_socket` | `.venv/bin/python -m pytest -q tests/test_devcontainer_foundation.py` | `5d854a074` | `.devcontainer/devcontainer.json`; `tests/test_devcontainer_foundation.py` | FIXED |
| `DEVCONTAINER-003` | Devcontainer imports full app `.env` or forwards app/CI secrets. | Removed Compose `env_file`, forwards only package-proxy vars, and added Compose plus `devcontainer.json` secret-exclusion tests. | `test_devcontainer_compose_does_not_import_full_env_file`; `test_devcontainer_compose_forwards_only_bootstrap_proxy_env`; `test_devcontainer_json_container_env_forwards_only_safe_bootstrap_env` | `.venv/bin/python -m pytest -q tests/test_devcontainer_foundation.py` | `5d854a074` | `.devcontainer/docker-compose.devcontainer.yml`; `.devcontainer/devcontainer.json`; `tests/test_devcontainer_foundation.py` | FIXED |
| `GOVERNANCE-001` | Phase2 and merge-readiness gates fail because the canonical mapping artifact and PR-body mirror are missing. | Added this canonical artifact and will refresh the PR-body mirror after commit/push. | `python3 scripts/ci/check_pr_body_phase2_gates.py --pr-number 1918 --body "$PR_BODY"` | `python3 scripts/ci/check_pr_body_phase2_gates.py --pr-number 1918 --body "$PR_BODY"` | `5d854a074` | `docs/review/PR_1918_FIXED_MAPPING.md` | FIXED |
| `GOVERNANCE-002` | Stale contribution instructions duplicate wrong Python/coverage thresholds. | Replaced threshold duplication with canonical `AGENTS.md` / `RUNBOOK_AGENT.md` gate references. | Docs review and Phase2 gate. | `python3 scripts/ci/check_pr_body_phase2_gates.py --pr-number 1918 --body "$PR_BODY"` | `5d854a074` | `CONTRIBUTING.md` | FIXED |

## Tests / Bounded Checks

- PASS: `python3 scripts/orchestration/check_preflight.py`
- PASS: `python3 scripts/orchestration/check_agent_consistency.py`
- PASS: `python3 scripts/orchestration/task_bootstrap.py --goal "Harden devcontainer bootstrap defaults and complete PR 1918 governance" --task-class security --pr-phase post_open_review`
- PASS: `python3 scripts/orchestration/role_dispatch_bridge.py --packet artifacts/orchestration/task_packets/3031655b8145.json --pretty`
- PASS: `.venv/bin/python -m pytest -q tests/test_devcontainer_foundation.py`
- PASS: `make validate-changed`
- PASS: `pre-commit run --all-files`

## Machine-Heavy Verify Exception

Full local `make verify` is operator-deferred for this PR by explicit user
instruction. This PR must rely on narrow local gates plus current-head GitHub CI
parity before any merge-readiness claim.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

Disposition: FIXED
Commit: see mapping entries below
Evidence: Sourcery and Cubic actionable review findings were fixed in the mapped commits and summarized in Bot Review Summary.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1918#pullrequestreview-4458019788 -> f53d23f56
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1918#discussion_r3380651249 -> 824683f0
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1918#discussion_r3380702499 -> 824683f0

## Bot Review Summary

- CodeRabbit: NOT-A-BUG. Evidence: status reports `Review skipped`; no
  actionable review thread found during current pass.
- Sourcery: FIXED. Evidence: actionable security suggestion to extend
  devcontainer lifecycle-hook guard coverage is addressed in
  commit `f53d23f56`; `tests/test_devcontainer_foundation.py` now blocks
  `postAttachCommand` and `overrideCommand`, while explicitly allowing only the
  safe-directory `postStartCommand`. General feedback to tighten Compose env
  forwarding is also fixed by exact allowed-key assertions.
- Cubic: NOT-A-BUG. Evidence: status check passes and no actionable blocking
  finding was visible during initial pass.
- Cubic post-fix review: FIXED. Evidence: Cubic P2 finding about
  `CONTRIBUTING.md` implying `pre-commit run --all-files` was only for the
  machine-heavy exception path is fixed; the command is now listed as required
  before every push.
- CodeQL/security CI: NOT-A-BUG. Evidence: current-head security checks passed
  before this artifact commit; final current-head CI remains required.

## Deferred / Follow-ups

None.

## Merge Readiness

Not merge-ready yet. Pending after this artifact/fix commit:

- PR-body mirror refresh from this canonical artifact.
- Current-head CI rerun with `PR Body Phase2 gates` PASS.
- Current-head CI rerun with `Merge readiness gate` PASS.
- Final strict review-thread disposition and merge-readiness checks with auth.
