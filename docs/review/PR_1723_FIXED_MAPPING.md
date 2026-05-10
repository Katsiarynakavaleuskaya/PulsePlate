<!-- markdownlint-disable MD013 MD034 -->
# PR 1723 Fixed In Commit Mapping

- PR: <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1723>
- Branch: `fix/ci-emergency-wheel-pre-commit-460`
- Title: `fix(ci): emergency wheel for pre-commit 4.6.0 (proxy lag)`
- Implementing commit (pre-commit emergency wheel): `d58ea8eac16e71e9c305b1fc65b373b7632999a3`
- Scope: `scripts/ci/emergency_python_wheels.json` (privileged CI surface), `.secrets.baseline` (detect-secrets refresh for manifest digest lines). No runtime application source changes.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

CI hotfix: registers the PyPI-hosted `pre-commit` 4.6.0 universal wheel for emergency install when the approved private proxy lags PyPI (same pattern as #1722 / hypothesis). CodeRabbit, Sourcery, and Cubic auto-summaries contained no actionable inline items requiring a disposition beyond this artifact.

## Fixed in Commit Mapping

- No actionable review comments

## Local Validation Evidence

- Pre-flight: `python3 scripts/orchestration/check_preflight.py` — PASS.
- Pre-flight: `python3 scripts/orchestration/check_agent_consistency.py` — PASS (runs as part of `check_preflight` bundle where configured).
- `make validate-min` — PASS.
- PyPI cross-check: URL `https://files.pythonhosted.org/packages/80/6e/4b28b62ecb6aae56769c34a8ff1d661473ec1e9519e2d5f8b2c150086b26/pre_commit-4.6.0-py2.py3-none-any.whl` and `sha256=e2cf246f7299edcabcf15f9b0571fdce06058527f0a06535068a86d38089f29b` confirmed against `https://pypi.org/pypi/pre-commit/4.6.0/json` (matches exactly).
- Targeted test: `pytest tests/test_install_locked_python_requirements.py::test_repo_emergency_manifest_tracks_current_active_fallback_set` — PASS.

### Machine-heavy / operator-approved narrow gate

- This PR scopes only `scripts/ci/**` (privileged surface) and `.secrets.baseline`. Per operator-approved narrow-gate policy and root `AGENTS.md` "Machine-heavy PR exception", full local `make verify` is deferred; PR-scoped gates above plus current-head GitHub CI are the merge truth signal.

## Security Notes

- Supply-chain: emergency wheel uses the canonical PyPI artifact (`files.pythonhosted.org`) with exact `sha256` digest matching PyPI metadata.
- `.secrets.baseline` refresh follows repo detect-secrets policy for rotated hex fingerprints on `scripts/ci/emergency_python_wheels.json`, not a credential leak.

## Risks / Rollback

- Risk: manifest `expires_at` remains `2026-05-27`; remove the `pre-commit` entry once the private proxy serves `4.6.0` without miss.
- Rollback: revert implementing commit `d58ea8eac16e71e9c305b1fc65b373b7632999a3` and regenerate `.secrets.baseline` for the prior manifest state.

## Merge Readiness

- [x] Pre-flight + agent consistency: PASS
- [x] Canonical artifact: this file (`docs/review/PR_1723_FIXED_MAPPING.md`)
- [x] PR body mirrors Discussion Thread Pass / Fixed in Commit Mapping / Merge Readiness sections
- [x] Narrow gate: `make validate-min` (operator-approved, scope = `scripts/ci/**` + secrets baseline)
- [x] CI parity (current-head): canonical Tier-1 `CI` workflow + merge governance gates once Phase2 body + artifact are on the branch tip
- [x] Bot summaries reviewed (CodeRabbit / Sourcery / Cubic): no actionable code changes required

## Deferred / Follow-ups

- Remove emergency `pre-commit` wheel entry after proxy parity or manifest rotation policy.
