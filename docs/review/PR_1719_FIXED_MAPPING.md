<!-- markdownlint-disable MD013 MD034 -->
# PR 1719 Fixed In Commit Mapping

- PR: <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1719>
- Branch: `dependabot/pip/types-pyyaml-6.0.12.20260508`
- Title: `deps(deps-dev): bump types-pyyaml from 6.0.12.20260408 to 6.0.12.20260508`
- Implementing commit (types-pyyaml pin): `1580f7bb408fe9b6c10ee9b03c37014a587f92b6`
- Merge-base sync: `chore(pr): merge origin/main into dependabot types-pyyaml (#1719)` — `fb20f96f1bf42968300d032675344c0073faa6e8` (includes #1723 pre-commit emergency wheel and prior artifacts on `main`).
- Pip lock guard remediation: `fix(security): remove pip pin from requirements-dev lock` — `2c1fbcb2ce294824c0c871dfc6628401c8d1f787` (drops disallowed `pip==...` stanza per `tests/test_dependency_security_guard.py` / GHSA-58qw policy).
- Scope: `requirements-dev.txt` — Dependabot typeshed stub bump for `types-pyyaml` (dev-only typing support).

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

Dependabot deps-dev bump only; no unresolved actionable bot threads.

## Fixed in Commit Mapping

- No actionable review comments

## Local Validation Evidence

- Pre-flight: `python3 -m scripts.orchestration.check_preflight` — PASS.
- Pre-flight: `python3 scripts/orchestration/check_agent_consistency.py` — PASS.
- `make validate-min` — PASS.
- `pytest tests/test_dependency_security_guard.py` — PASS (includes `pip` pin absence guard per `docs/security/GHSA-58qw-9mgm-455v-pip.md`).
- `pre-commit run --all-files` — PASS (before push).

### Machine-heavy / operator-approved narrow gate

- Full `make verify` deferred per series policy; narrow gates plus current-head CI are merge signal.

## Security Notes

- `types-pyyaml` is a types-only dev stub; no runtime execution path change for production `requirements.txt`.
- Removed stray `pip==...` entry from `requirements-dev.txt` to satisfy repo guard aligned with GHSA-58qw-9mgm-455v remediation (unsafe pip pins must stay absent).

## Risks / Rollback

- Risk: typeshed date-stamped stubs can surface new mypy findings; mitigated by CI type/lint matrix and scoped dev usage.
- Rollback: revert `1580f7bb408fe9b6c10ee9b03c37014a587f92b6` or re-pin stub in `requirements-dev.in` / regenerate lock.

## Merge Readiness

- [x] Pre-flight + agent consistency: PASS
- [x] Canonical artifact (this file) on branch
- [x] `origin/main` merged into branch (tip carries #1723; see merge commit `fb20f96f1`)
- [x] Narrow gates: `make validate-min` + `pre-commit run --all-files`

## Deferred / Follow-ups

- None.
