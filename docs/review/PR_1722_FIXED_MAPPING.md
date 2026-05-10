<!-- markdownlint-disable MD013 MD034 -->
# PR 1722 Fixed In Commit Mapping

- PR: <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1722>
- Branch: `fix/ci-hypothesis-61524-emergency-wheel`
- Title: `fix(ci): emergency wheel for hypothesis 6.152.4 (proxy lag)`
- Implementing commit (hypothesis emergency wheel): `51109399fb09ef4a26de9bec7763eeab37811ced`
- Scope: `scripts/ci/emergency_python_wheels.json` (privileged CI surface), `.secrets.baseline` (detect-secrets refresh for the rotated wheel digest). No runtime application source changes.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

CI hotfix only: bumps the emergency-fallback `hypothesis` wheel from `6.152.1` to `6.152.4` to match the lockfile from #1717 while the approved private proxy lags PyPI. CodeRabbit, Sourcery, and Cubic auto-summaries reported no actionable items requiring code disposition; no unresolved inline review threads.

## Fixed in Commit Mapping

- No actionable review comments

## Local Validation Evidence

- Pre-flight: `python3 -m scripts.orchestration.check_preflight` — PASS.
- Pre-flight: `python3 scripts/orchestration/check_agent_consistency.py` — PASS.
- `make validate-changed` — PASS (no Python sources changed on branch tip vs merge-base; diff runner exits 0 per operator narrow-gate policy).
- PyPI cross-check: URL `https://files.pythonhosted.org/packages/19/89/0f50dd0d92e8a7dffc24f69ab910ff81db89b2f082ba42682bd57695e4d2/hypothesis-6.152.4-py3-none-any.whl` and `sha256=e730fd93c7578182efadc7f90b3c5437ee4d55edf738930eb5043c81ac1d97e8` confirmed against `https://pypi.org/pypi/hypothesis/6.152.4/json` (matches exactly).

### Machine-heavy / operator-approved narrow gate

- This PR scopes only `scripts/ci/**` (privileged surface) and `.secrets.baseline`. Per operator-approved narrow-gate policy and root `AGENTS.md` "Machine-heavy PR exception", full local `make verify` is deferred; PR-scoped gates above plus current-head GitHub CI are the merge truth signal.

## Security Notes

- Supply-chain: emergency wheel pin uses the canonical PyPI artifact (`files.pythonhosted.org`) with exact `sha256` digest matching PyPI metadata; no weakened policy, no new transitive surface.
- `.secrets.baseline` refresh is the legitimate detect-secrets baseline rotation for the new hashed wheel digest on `scripts/ci/emergency_python_wheels.json:82` (per repo pre-commit policy), not a secret leak.

## Risks / Rollback

- Risk: emergency-wheel manifest expires_at remains `2026-05-27`; follow-up to drop the entry once the private proxy serves `hypothesis>=6.152.4` cleanly. Mitigation: tracked window sufficient for the upstream proxy catch-up.
- Risk: hash mismatch would hard-fail CI install fast; verified against PyPI before merge.
- Rollback: revert commit `51109399fb09ef4a26de9bec7763eeab37811ced` and regenerate `.secrets.baseline` (detect-secrets will reproduce the prior digest).

## Merge Readiness

- [x] Pre-flight + agent consistency: PASS
- [x] Coordinator-first task packet: `artifacts/orchestration/task_packets/2c40f0922483.json`
- [x] PR body mirrors Discussion Thread Pass / Fixed in Commit Mapping / Merge Readiness sections
- [x] Narrow gate: `make validate-changed` (operator-approved, scope = `scripts/ci/**` + secrets baseline)
- [x] CI parity (current-head): non-required `test-pr` / `coverage-pr` / `diff-coverage` are non-blocking signal only; canonical merge signal is the `Merge readiness gate` and `PR Body Phase2 gates` once this artifact ships
- [x] No actionable bot comments (CodeRabbit / Sourcery / Cubic auto-summaries reviewed)

## Deferred / Follow-ups

- None.
