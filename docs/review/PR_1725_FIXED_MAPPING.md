<!-- markdownlint-disable MD013 MD034 -->
# PR 1725 Fixed In Commit Mapping

- PR: <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1725>
- Branch: `fix/private-pypi-proxy-premortem-521`
- Title: `fix(ci): private PyPI proxy premortem — emergency wheels, runbook, baseline`
- Implementing commits:
  - `7225d2cd3` — initial premortem fix (emergency wheels expand, runbook 521 triage, baseline refresh, ledger entry)
  - `5218e0c42` — scope Cloudflare 521 triage to *packages hostname only*; marketing 521 stays intentional (operator decision)
  - `63d367bb0` — clarify `emergency_python_wheels.json` scope (mirror-lag fallback, not 521 fallback) and correct Wrangler auth wording (Codex P2 + Cubic P3)
  - `d2dbc9e39` — fix HTTP probe to PEP 503 `/simple/<package>/` path and bound `curl` with `--connect-timeout` / `--max-time` (Sourcery P2 + P3)
- Scope: `scripts/ci/emergency_python_wheels.json`, `RUNBOOK_AGENT.md`, `docs/roadmap/BACKLOG_LEDGER.md`, `.secrets.baseline` — repo-side bridge + triage doc; no application runtime surface, no security policy weakening.

## Discussion Thread Pass

- [x] Discussion-thread pass completed (Codex, Cubic, and Sourcery actionable findings reviewed and dispositioned)
- [x] Fixed in commit mapping completed

Per root `AGENTS.md` Review Governance, every actionable bot/human comment receives a disposition (`FIXED` / `NOT-A-BUG` / `DEFERRED`) with proof before the thread is resolved. New threads after this pass will be added below in the same format and the post-comment commit-time rule (`Commit-after-comment`) will be respected.

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1725#discussion_r3215286292 -> 63d367bb039d59e4661f4bf06cdf1afb108c6165

Disposition: FIXED
Commit: 63d367bb039d59e4661f4bf06cdf1afb108c6165
Evidence: RUNBOOK_AGENT.md Python private index proxy section + docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-private-pypi-proxy-mirror-parity — scripts/ci/emergency_python_wheels.json is now explicitly described as a mirror-lag fallback for exact, listed wheels only, not a generic 521 fallback. Reviewer: Codex (P2).

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1725#discussion_r3215289066 -> 63d367bb039d59e4661f4bf06cdf1afb108c6165

Disposition: FIXED
Commit: 63d367bb039d59e4661f4bf06cdf1afb108c6165
Evidence: RUNBOOK_AGENT.md SRE/infra section — Wrangler description now correctly states it supports wrangler login (browser-based OAuth) and API-token / API-key auth (the prior wording said "no interactive login flow"). Reviewer: Cubic (P3 inline).

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1725#pullrequestreview-4259728610 -> 63d367bb039d59e4661f4bf06cdf1afb108c6165

Disposition: FIXED
Commit: 63d367bb039d59e4661f4bf06cdf1afb108c6165
Evidence: same Wrangler-auth correction in RUNBOOK_AGENT.md; this is the top-level Cubic review summarising the P3 inline finding above. No additional code change required beyond the inline fix. Reviewer: Cubic (top-level).

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1725#pullrequestreview-4259724916 -> d2dbc9e39bc11a9d8cb64e3f0e5499e4953e48f4

Disposition: FIXED
Commit: d2dbc9e39bc11a9d8cb64e3f0e5499e4953e48f4
Evidence: RUNBOOK_AGENT.md HTTP-probe step — the probe URL is now PEP 503 compliant (${PULSEPLATE_PYTHON_INDEX_URL%/}/simple/aiosqlite/) so it actually exercises the simple-index surface pip consumes, and the curl invocation is bounded by --connect-timeout 5 --max-time 10 so a hung Cloudflare origin cannot stall triage. Both Sourcery findings (P2 simple-index path and P3 timeout bounds) are addressed in this single commit. Reviewer: Sourcery (top-level review).

## Local Validation Evidence

- Pre-flight: `python3 scripts/orchestration/check_preflight.py` — PASS.
- Agent consistency: `python3 scripts/orchestration/check_agent_consistency.py` — PASS.
- `pytest -q tests/test_python_supply_chain_controls.py` — PASS (covers `emergency_python_wheels.json` schema, sha256-only, `files.pythonhosted.org` URL constraint, expiry, and TTL).
- `pytest -q tests/test_install_locked_python_requirements.py::test_repo_mypy_emergency_fallback_matches_dev_requirement_surfaces` — PASS (mypy 2.0.0 surface parity with `requirements-dev.txt`).
- `pre-commit run --all-files` — PASS before each commit (`detect-secrets` baseline regenerated and committed; no new secrets introduced).
- Pre-push hooks (pip-audit, pytest, bandit) — PASS for `5218e0c42`.

### Bootstrap / coordinator lane

- Coordinator-first start gate observed; role order applied for this scoped infra-doc PR:
  `agent-coordinator` → `security-auditor` → `dev-operator` → `qa-engineer-agent` → `bug-hunter`.
- Backend execution lane intentionally not used: no application runtime / FastAPI / `core/` change.
- Coordinator packet kept local under `artifacts/orchestration/` per repo policy (gitignored, not committed).

### Machine-heavy / operator-approved narrow gate

- Full `make verify` deferred under the documented machine-heavy exception for this docs+config-only PR; the merge signal is canonical current-head CI on `main`-targeted lanes (CI, Frontend CI, CodeQL, Docker Build and Push, RAG Release Gates) plus the local narrow gates listed above.
- This deferral is recorded here per root `AGENTS.md` (machine-heavy PR exception requires explicit doc + PR-scoped narrow gates).

## Security Notes

- `scripts/ci/emergency_python_wheels.json` updates are time-boxed (`expires_at` set, `sha256` enforced, `files.pythonhosted.org` only) and exist solely to bridge transient unhealthy private proxy windows. Schema and integrity are enforced by `tests/test_python_supply_chain_controls.py`.
- `mypy 2.0.0` emergency entry mirrors `requirements-dev.txt` to keep `make typecheck` reachable while the proxy is unhealthy; no version drift vs locked dev surface.
- `aiosqlite 0.22.1` added to bridge the same window for runtime test installers; SHA pinned.
- `.secrets.baseline` regenerated only because `detect-secrets` re-fingerprinted the updated JSON; no new live secret added (artifact contains hashed fingerprints, ignored by Sourcery per repo policy).
- `RUNBOOK_AGENT.md` makes explicit that this assistant has **no** Cloudflare account access; all real fixes happen on the operator side. Wrangler is called out as not a substitute for zone SSL/DNS work.

## Risks / Rollback

- **Risk:** Low. Changes are doc + time-boxed wheel manifest; runtime/feature surface unaffected. The biggest risk is forgetting to retire emergency entries after the proxy mirror parity work in `ledger-p1-private-pypi-proxy-mirror-parity` lands — that retirement is explicitly tracked in the ledger DoD.
- **Rollback:** `git revert 5218e0c42 7225d2cd3` (in that order). Emergency entries are TTL-bounded (`expires_at`); the supply-chain guard enforces expiry, so a stale manifest fails CI rather than silently shipping.

## Cloudflare 521 — explicit scope

- The HTTP 521 currently observed on the public marketing apex `pulseplate.app` is an **intentional operator-side release gate** (the unfinished public site is held down on purpose) and **must not** be reverted as part of this PR or as part of the SRE/infra triage in `RUNBOOK_AGENT.md`.
- The CI-blocking surface is strictly the *packages hostname* behind `PULSEPLATE_PYTHON_INDEX_URL` (e.g. `packages.pulseplate.app`), which must serve PEP 503 `+simple/` for the locked pins. The runbook section now reflects that distinction; the ledger item enforces it as P1 mirror-parity work.
- This PR does **not** change the marketing-apex state, Cloudflare zone configuration, DNS records, or SSL/TLS modes. It only documents the scope and provides the time-boxed repo-side bridge.

## Merge Readiness

- [x] Pre-flight + agent consistency: PASS (local gates in evidence section)
- [x] Canonical artifact: this file
- [ ] PR body Phase2 mirror synchronized (checked boxes + `### Fixed in Commit Mapping` → canonical artifact pointer)
- [ ] Required current-head CI jobs green (`CI` canonical lane + governance checks; Frontend CI, CodeQL, Docker Build and Push, RAG Release Gates)
- [ ] Post-open reviewers: `qa-engineer-agent` → `bug-hunter` mandatory pass completed per root `AGENTS.md`
- [ ] Mandatory wait-window after latest bot/review activity observed before claiming merge-ready

## Deferred / Follow-ups

- `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-private-pypi-proxy-mirror-parity` — Origin/Cloudflare healthy independently of marketing apex; `curl` 200 on `+simple/` for representative pins; preflight installer green with prod URL; emergency manifest entries retired after security sign-off.
- Hostname split (packages vs marketing) is part of the same ledger item if origins are currently shared.
- If the operator decides to lift the marketing apex 521 gate, that decision is logged separately (out of scope here).
