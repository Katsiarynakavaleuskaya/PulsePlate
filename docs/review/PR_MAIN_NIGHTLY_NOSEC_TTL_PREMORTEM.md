# Main/Nightly NOSEC TTL Stabilization Premortem

Mode: `pr-premortem`
Skill: `pulseplate-premortem-risk-review`
Task packets: `artifacts/orchestration/task_packets/07e158339c7d.json`, `artifacts/orchestration/task_packets/82da7727b5db.json`
Branch: `codex/stabilize-main-nightly-nosec-ttl`
Base head reviewed: `6571a4ba6181899330d0bec659328adfbb4bead0`

## Summary

This stabilization PR fixes the current `main` CI run `28497174542` and `Nightly Full Tests` run `28497874442` failure mode where `tests/guards/test_nosec_policy_guard.py::test_nosec_policy_guard` rejects expired or due `# nosec` `remove-by` dates. It is 48 hours from now, this hotfix made things worse, and we are looking backward to understand why.

## Failure Modes And Closure

| ID | Failure mode | Disposition | Closure evidence |
| --- | --- | --- | --- |
| PM-NOSEC-001 | The PR blindly extended every expired suppression and normalized technical debt instead of fixing safe code paths. | FIXED | `app/metrics.py`, `core/db_fallback.py`, and `core/insight/telemetry.py` remove B110 suppressions by preserving best-effort behavior with `logger.debug(..., exc_info=True)`. `app/routers/vip.py` removes the unnecessary B105 suppression while preserving the legacy `TEST_KEY` contract. |
| PM-NOSEC-002 | The trusted-host health probe could renew B323 without proof that unverified TLS is limited to matching trusted hosts. | FIXED | `tests/test_install_locked_python_requirements.py::test_private_index_project_health_uses_default_tls_for_mismatched_trusted_host` proves mismatched trusted hosts use the default verified TLS context. |
| PM-NOSEC-003 | The PR fixes the currently red `2026-06-30` TTLs but leaves due-today `2026-07-01` suppressions to fail the next nightly. | FIXED | `scripts/metatron_lab/compose_guard.py` is included in supplemental packet `82da7727b5db` and refreshes only the same bounded Docker compose fixed-argv suppressions. |
| PM-NOSEC-004 | Refreshed B105/B404/B603 suppressions could become permanent exceptions with no removal condition. | FIXED | All refreshed suppressions use `remove-by: 2026-09-30` and `ref: PR-main-nightly-nosec-ttl`; no `2026-06-30` or `2026-07-01` TTL remains under `app`, `core`, `scripts`, or `tests`. |
| PM-NOSEC-005 | Debug logging in metrics and telemetry could turn optional observability failures into request-path noise or user-visible errors. | NOT-A-BUG | The code still catches exceptions and returns normally; logging is debug-level and server-side only. Focused role reviews confirmed the non-raising behavior. |

## Most Likely Failure

The most likely failure was treating the guard output as a date-update chore. That would have passed the immediate failing test while leaving avoidable `B110` suppressions in place and preserving silent `pass` blocks where debug logging is safer and more auditable.

## Most Dangerous Failure

The most dangerous failure was renewing the B323 unverified TLS suppression without a negative test. If that branch widened, package-proxy health checks could silently use an unverified context for hosts outside the operator-approved trusted host.

## Hidden Assumption

The hidden assumption was that only the exact `2026-06-30` lines from the red run mattered. Because the current date is 2026-07-01, due-today TTLs in the same scan surface would become the next red nightly if left alone.

## Revised Plan

- Remove suppressions where a safe code fix exists.
- Keep suppressions only where Bandit still flags an intentional bounded surface.
- Add deterministic proof around the B323 trusted-host boundary.
- Include due-today nosec TTLs in the same stabilization lane only when they are the same guard surface.
- Keep validation focused on nosec policy, subprocess policy, trusted-host TLS behavior, changed-file selection, and pre-commit.

## Pre-Merge Checklist

- `python3 scripts/orchestration/check_preflight.py`
- `python3 scripts/orchestration/check_agent_consistency.py`
- Focused nosec/subprocess/private-index TLS tests.
- File-scoped Bandit over changed Python files.
- `make validate-changed`
- `pre-commit run --all-files`
- Current-head PR CI after opening the PR.

## Decision

`proceed with changes` - the plan is sound after replacing avoidable suppressions with code fixes, adding trusted-host TLS proof, and including due-today suppressions from the same guard surface.

Unresolved P0/P1: none.
