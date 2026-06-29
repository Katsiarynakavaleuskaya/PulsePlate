# PR #2050 Fixed in Commit Mapping SoT

PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2050

Branch: `codex/deps-ruff-0-15-20-refresh`

## Summary

This PR supersedes closed Dependabot PR #2019 with a human-owned Ruff
quality-tooling dependency refresh from `0.15.19` to `0.15.20`.

## Scope

- `constraints.txt`: raise Ruff floor to `>=0.15.20`.
- `requirements-all.txt`: raise Ruff quality-tooling floor to `>=0.15.20`.
- `requirements-dev.in`: raise direct Ruff dev constraint to `~=0.15.20`.
- `requirements-dev.txt`: lock Ruff to `0.15.20`.
- `requirements-lock.txt`: lock Ruff to `0.15.20`.

## Out Of Scope

No `requirements.txt`, runtime dependency, OpenAPI, backend route, web, iOS,
macOS, private-proxy, emergency-wheel, workflow, installer, or pre-commit hook
configuration change is included. `.pre-commit-config.yaml` remains pinned to
`astral-sh/ruff-pre-commit` `v0.14.10` by design for this lane.

## Implementation Commits

- `f31e5e642` - bump Ruff quality-tooling dependency surfaces to `0.15.20`.

## Lane Start Provenance

- Base branch: `main`
- Branch: `codex/deps-ruff-0-15-20-refresh`
- Packet: `artifacts/orchestration/task_packets/505b1519b2ff.json`
- Current `main` CI run `28386708528` completed successfully before edits.
- Pre-implementation role order executed:
  `agent-coordinator -> architecture-specialist -> security-auditor -> qa-engineer-agent -> bug-hunter -> cursor-specialist-agent`
- Packet creation was routing/provenance only; role passes were executed
  explicitly before implementation.

## Premortem Evidence

Artifact: `artifacts/orchestration/premortem/pr-ruff-0-15-20-replacement-premortem.md`

Decision: `proceed with changes`. The accepted changes are the five-line
Ruff-only diff plus explicit private-proxy/index and local Ruff-version
validation notes.

## Experiment Runner Evidence

Packet: `artifacts/orchestration/experiments/artifacts/orchestration/experiments/ruff-0-15-20-replacement-oracle-packet.json`

Result: `artifacts/orchestration/experiments/results/ruff-0-15-20-replacement-oracle-result.json`

Status: accepted.

Contribution: `oracle_review`; commit `f31e5e642` includes
`Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>`.

## Discussion Thread Pass

- [x] Discussion-thread pass initialized.
- [x] Fixed in commit mapping artifact created after PR number allocation.
- [ ] CodeRabbit actionable review comments dispositioned.
- [ ] Codex Security diff scan / finding discovery completed or explicitly
  dispositioned.
- [ ] Post-open `qa-engineer-agent` pass completed.
- [ ] Post-open `bug-hunter` pass completed.
- [ ] Post-open `security-auditor` pass completed.
- [ ] `pulseplate-pr-review` completed.
- [ ] Current-head CI complete before readiness language.
- [ ] Strict merge-readiness checks run after the final review/check cycle.

## Fixed in Commit Mapping

No review-thread mappings yet. Initial artifact created after GitHub assigned PR
number `#2050`.

## Validation Evidence

- PASS: `python3 scripts/orchestration/check_preflight.py --path constraints.txt --path requirements-all.txt --path requirements-dev.in --path requirements-dev.txt --path requirements-lock.txt`
- PASS: `python3 scripts/orchestration/check_agent_consistency.py`
- PASS: `python verify_requirements.py`
- PASS: `python scripts/ci/check_python_dependency_surfaces.py`
- PASS: canonical-index private proxy health for `ruff==0.15.20` in
  `requirements-dev.txt`
- PASS: canonical-index private proxy health for `ruff==0.15.20` in
  `requirements-lock.txt`
- PASS: `python scripts/ci/install_locked_python_requirements.py --requirements-file requirements-dev.txt --constraints-file constraints.txt --install-dev --preflight-only`
- PASS: `python -m pytest -q tests/test_install_locked_python_requirements.py tests/test_python_supply_chain_controls.py tests/test_dependency_security_guard.py tests/guards/test_security_devtooling_regression_guards.py`
- PASS: `python -m pytest -q tests/test_python_dependency_surfaces.py tests/test_verify_requirements.py`
- PASS: `python -m ruff --version` reported `ruff 0.15.20`
- PASS: `python -m ruff check .`
- PASS: `make validate-changed`
- PASS: `pre-commit run --all-files`
- PASS: `git diff --check`
- PASS: no `pip==` unsafe pins in `requirements-dev.txt` or
  `requirements-lock.txt`

## Initial Review-State Notes

This PR is not merge-ready. GitHub current-head PR checks, review-tool
comments, the post-open role chain, and strict merge-readiness gates remain
pending.
