# PR #1861 - Fixed in Commit Mapping

**Title:** `test: stabilize KPP xdist collection`
**Branch:** `codex/nightly-xdist-security-outcomes-order`
**Scope:** Stabilize pytest-xdist collection order for the Experiment Runner KPP
security-sensitive header test.
**Primary commit:** `59f94a63e`

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1861#pullrequestreview-4401020366 -> a96b31e50
Disposition: FIXED
Commit: a96b31e50
Evidence: Cubic's review-level actionable surface is covered by the stale-evidence fix below; `docs/review/PR_1861_FIXED_MAPPING.md` no longer claims the removed no-actionable sentinel is present.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1861#discussion_r3333983785 -> a96b31e50
Disposition: FIXED
Commit: a96b31e50
Evidence: `docs/review/PR_1861_FIXED_MAPPING.md` now says the artifact uses explicit review-thread and review-level mappings, removing the stale `- No actionable review comments` evidence text Cubic identified.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1861#pullrequestreview-4401024810
Disposition: NOT-A-BUG
Evidence: `git merge-base --is-ancestor 99407267b HEAD` exits 0 on the current branch, `git show -s --format=%B HEAD` includes `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>`, and `dc10d2da688830ac169f7d509aa56d0644f413b6` is not present in local branch history.
Reason: The review references a synthetic/non-branch SHA; current branch history preserves the mapped proof commits and required Experiment Runner trailer.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1861#discussion_r3333988227
Disposition: NOT-A-BUG
Evidence: `git merge-base --is-ancestor 99407267b HEAD` exits 0 on the current branch, proving the referenced FIXED proof commit is an ancestor of the branch head that will be pushed.
Reason: The non-ancestor claim was based on `dc10d2da688830ac169f7d509aa56d0644f413b6`, which is not a current branch commit.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1861#discussion_r3333988232
Disposition: NOT-A-BUG
Evidence: `git show -s --format=%B HEAD` includes `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>`, and the PR artifact keeps the squash-merge note to preserve the same trailer in the final merge commit.
Reason: The reviewed `dc10d2da688830ac169f7d509aa56d0644f413b6` SHA is not present in current branch history; the branch head and merge instructions preserve attribution.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1861#pullrequestreview-4400847990 -> d4157039d
Disposition: FIXED
Commit: d4157039d
Evidence: CodeRabbit's review-level actionable surface is covered by the explicit thread dispositions below; mapping commit `d4157039d` records all six earlier resolved thread proofs and passes `check_review_threads_disposition.py --pr-number 1861 --require-auth`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1861#discussion_r3333825720 -> 99407267b
Disposition: FIXED
Commit: 99407267b
Evidence: `docs/review/PR_1861_FIXED_MAPPING.md` now uses explicit review-thread and review-level mappings for the actionable bot findings.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1861#discussion_r3333843581 -> 99407267b
Disposition: FIXED
Commit: 99407267b
Evidence: `docs/review/PR_1861_FIXED_MAPPING.md` now uses explicit review-thread and review-level mappings for the actionable bot findings.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1861#discussion_r3333825724
Disposition: NOT-A-BUG
Evidence: `git log --format=%B origin/main..HEAD` shows every current branch commit carries the required `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>` trailer; the reviewed `69e86dade6eb40450fba6b81a73794665c62c9bd` SHA is not present in the current branch history.
Reason: The branch history preserves the required Experiment Runner trailer; the referenced SHA was a stale or synthetic review surface, not the current PR head.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1861#discussion_r3333829067 -> 137cb8378
Disposition: FIXED
Commit: 137cb8378
Evidence: `docs/review/PR_1861_FIXED_MAPPING.md:36` now says `required hash-seed collection and validation checks`, removing the awkward phrase identified by CodeRabbit.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1861#discussion_r3333829084 -> 137cb8378
Disposition: FIXED
Commit: 137cb8378
Evidence: `docs/review/PR_1861_FIXED_MAPPING.md:61` now references `artifacts/orchestration/experiments/nightly-xdist-security-outcomes-oracle-packet.json` without the duplicated `artifacts/orchestration/experiments/` segment.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1861#discussion_r3333843593 -> 137cb8378
Disposition: FIXED
Commit: 137cb8378
Evidence: `docs/review/PR_1861_FIXED_MAPPING.md:61` now references `artifacts/orchestration/experiments/nightly-xdist-security-outcomes-oracle-packet.json` without the duplicated `artifacts/orchestration/experiments/` segment.

## Implementation Evidence

Disposition: FIXED
Commit: `59f94a63e`
Evidence: `tests/test_experiment_slack_kpp_renderer.py` now derives
`SECURITY_SENSITIVE_OUTCOME_CASES` with deterministic ordering before pytest
parametrization, while production `SECURITY_SENSITIVE_OUTCOMES` remains a
`frozenset`.

## Role-Agent / Premortem Pass

- `agent-coordinator` - completed; decision: complete mandatory role passes
  before implementation, keep scope test-only, and leave Trivy #602 out of
  scope.
- `dev-operator` - completed; validation plan required hash-seed collection,
  xdist execution, `make validate-changed`, and `pre-commit run --all-files`.
- `architecture-specialist` - completed; required test-only deterministic
  parametrization and preserving the production renderer contract.
- `qa-engineer-agent` - completed; required hash-seed collection and validation
  checks, xdist checks, full renderer module validation, and no skips or xfails.
- `bug-hunter` - completed; confirmed the root cause as direct parametrization
  from a `frozenset` and classified the low coverage result as downstream
  collection-abort fallout.
- `security-auditor` - completed; approved only a test-only stable
  parametrization with unchanged security-sensitive membership and no Trivy
  scope expansion.
- `cursor-specialist-agent` - completed; confirmed no `.cursor/agents`, memory,
  or workflow instruction update is needed for this narrow fix.
- `pulseplate-premortem-risk-review` - completed; decision: proceed. The xdist
  collection risk is FIXED by focused validation, and the production membership
  and Trivy scope risks are NOT-A-BUG for this PR.

## Lane Start Provenance

- Packet: `artifacts/orchestration/task_packets/b2abaffcd011.json`
- Branch start: synced `main` at `4d47c3b97`, then created
  `codex/nightly-xdist-security-outcomes-order`.
- Colleague-owned `.cursor/agents/*.md` edits were stashed before branch work
  and are not part of this PR.

## Experiment Runner Evidence

- Packet: `artifacts/orchestration/experiments/nightly-xdist-security-outcomes-oracle-packet.json`.
- Artifact: `artifacts/orchestration/experiments/results/nightly-xdist-security-outcomes-oracle-result.json`
- Mode: `oracle_only_governance_reviewer`.
- Result: accepted; 2/2 oracle commands passed; shared tree untouched;
  `mutated_paths=[]`; `source_diff_paths=["tests/test_experiment_slack_kpp_renderer.py"]`;
  `coauthor_required=true`.
- Commit trailer used:
  `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>` on
  `59f94a63e`.
- Squash-merge note: preserve
  `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>` in the final
  merge commit message.

## Local Validation

- `python3 scripts/orchestration/check_preflight.py --path tests/test_experiment_slack_kpp_renderer.py --path scripts/orchestration/experiment_slack_kpp_renderer.py` - PASS.
- `python3 scripts/orchestration/check_agent_consistency.py` - PASS.
- `PYTHONHASHSEED=0 .venv/bin/python -m pytest --collect-only -vv tests/test_experiment_slack_kpp_renderer.py::test_security_sensitive_headers` - PASS.
- `PYTHONHASHSEED=1 .venv/bin/python -m pytest --collect-only -vv tests/test_experiment_slack_kpp_renderer.py::test_security_sensitive_headers` - PASS.
- `PYTHONHASHSEED=3 .venv/bin/python -m pytest --collect-only -vv tests/test_experiment_slack_kpp_renderer.py::test_security_sensitive_headers` - PASS.
- `.venv/bin/python -m pytest -q tests/test_experiment_slack_kpp_renderer.py::test_security_sensitive_headers tests/test_experiment_slack_kpp_renderer.py::test_security_sensitive_outcomes_frozen` - PASS.
- `PYTHONHASHSEED=0 .venv/bin/python -m pytest -q -n 2 --dist=loadscope tests/test_experiment_slack_kpp_renderer.py::test_security_sensitive_headers tests/test_experiment_slack_kpp_renderer.py::test_security_sensitive_outcomes_frozen` - PASS.
- `PYTHONHASHSEED=1 .venv/bin/python -m pytest -q -n 2 --dist=loadscope tests/test_experiment_slack_kpp_renderer.py::test_security_sensitive_headers tests/test_experiment_slack_kpp_renderer.py::test_security_sensitive_outcomes_frozen` - PASS.
- `.venv/bin/python -m pytest -q -n 4 --dist=loadscope tests/test_experiment_slack_kpp_renderer.py::test_security_sensitive_headers` - PASS.
- `.venv/bin/python -m pytest -q tests/test_experiment_slack_kpp_renderer.py` - PASS.
- `make validate-changed` - PASS after commit.
- `pre-commit run --all-files` - PASS.
- Pre-push hooks - PASS, including pip-audit, backend tests, full-repo bandit,
  and Docker build skip for no Docker changes.

## Machine-Heavy Gate Deferral

Full local `make verify` was started and passed `verify-env`, lint, mypy, and
`test-fast`, then entered the full coverage suite via
`coverage run -m pytest -q`. It was stopped at roughly 3% suite progress under
the operator-approved machine-heavy exception. This artifact does not claim
local full-verify readiness.

Merge readiness still requires current-head CI parity, post-open role passes,
Codex Security diff scan, no unresolved review threads, no actionable bot
findings, strict merge-readiness checks, and the mandatory wait-window.
