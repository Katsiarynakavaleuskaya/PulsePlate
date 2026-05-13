<!-- markdownlint-disable MD013 MD034 -->
# PR 1734 Fixed In Commit Mapping

- PR: <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1734>
- Branch: `codex/fix-replay-sort-clean`
- Title: `fix(evidence): replay supersession chains topologically`
- Implementing commits:
  - `02d968265` — fix replay supersession supersedes ordering and keep fail-closed behavior.
  - `7de92822f` — merge current `origin/main` after #1738/#1740/#1739 recovery without rewriting PR history.
  - `42cb54728` — fix full-ancestry supersession replay, dependency-order evidence, and indexed successor lookup.
  - `3dee930fc` — cover replay supersession fail-closed and non-promoting existing-entry branches for diff coverage.
  - `8db30a3cf` — fail closed on unknown supersession ancestor references.
  - `1c81daf00` — keep current-head merge-readiness checkbox open until final current-head pass.
  - `a0e81b4b4` — remove workstation-local absolute paths from review evidence.
  - `b495847c7` — disposition current-head reachability review thread after live branch proof.
  - `c27b00b9d` — cover disconnected known supersede cycles for diff coverage.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

Per root `AGENTS.md` review governance, each actionable bot/human comment must receive a disposition (`FIXED` / `NOT-A-BUG` / `DEFERRED`) with proof before thread resolution.

### Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1734#discussion_r3220385510 -> 42cb54728
Disposition: FIXED
Commit: 42cb54728
Evidence: `core/evidence/replay.py` resolves only supersede entries whose remaining same-scope dependencies are already applied, so a valid `A <- B <- C` chain with `C.supersedes=(A,B)` no longer raises a false conflict.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1734#discussion_r3220388285 -> 42cb54728
Disposition: FIXED
Commit: 42cb54728
Evidence: `core/evidence/replay.py` now builds `supersede_index` and `remaining_by_id` before walking the chain, avoiding repeated full-list successor scans.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1734#discussion_r3220388302 -> 42cb54728
Disposition: FIXED
Commit: 42cb54728
Evidence: `tests/core/evidence/test_replay.py` asserts the exact dependency order for `applied_entry_ids` instead of comparing with `sorted(...)`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1734#discussion_r3220411620 -> 42cb54728
Disposition: FIXED
Commit: 42cb54728
Evidence: `tests/core/evidence/test_replay.py` covers full-ancestry supersedes with out-of-order existing entries and expects no conflict.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1734#pullrequestreview-4265346907 -> 42cb54728
Disposition: FIXED
Commit: 42cb54728
Evidence: Sourcery review actionables are dispositioned by the inline thread entries above and fixed in `core/evidence/replay.py` plus `tests/core/evidence/test_replay.py`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1734#pullrequestreview-4265372330 -> 42cb54728
Disposition: FIXED
Commit: 42cb54728
Evidence: Cubic review actionables are dispositioned by the inline thread entry above and fixed in `core/evidence/replay.py` plus `tests/core/evidence/test_replay.py`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1734#issuecomment-4422368663
Disposition: NOT-A-BUG
Evidence: Repo Phase2 body gate is authoritative for PR template compliance; this PR body already passed `PR Body Phase2 gates`. Test functions are not required to carry docstrings by repo policy, and production helper docstrings are present in `core/evidence/replay.py`.
Reason: The CodeRabbit docstring/template warning is advisory under repo policy unless Phase2/body or required checks fail.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1734#discussion_r3233099749 -> 8db30a3cf
Disposition: FIXED
Commit: 8db30a3cf
Evidence: `core/evidence/replay.py` validates every existing supersede reference against known same-scope ledger entry ids before successor selection; `tests/core/evidence/test_replay.py` covers `test_existing_supersede_with_unknown_ancestor_fails_closed`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1734#discussion_r3233099766 -> 1c81daf00
Disposition: FIXED
Commit: 1c81daf00
Evidence: `docs/review/PR_1734_FIXED_MAPPING.md` keeps the current-head merge-readiness checkbox unchecked until the final current-head pass.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1734#pullrequestreview-4280292651 -> 8db30a3cf
Disposition: FIXED
Commit: 8db30a3cf
Evidence: The CodeRabbit review actionables are dispositioned by `discussion_r3233099749` and `discussion_r3233099766`; code hardening landed in `8db30a3cf`, and readiness-checkbox hygiene landed in `1c81daf00`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1734#discussion_r3233145808 -> a0e81b4b4
Disposition: FIXED
Commit: a0e81b4b4
Evidence: `docs/review/PR_1734_FIXED_MAPPING.md` validation evidence now uses portable `.venv/bin/python` paths instead of workstation-local absolute paths.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1734#discussion_r3233145816
Disposition: NOT-A-BUG
Evidence: `git merge-base --is-ancestor 42cb54728 HEAD` and `git merge-base --is-ancestor 8db30a3cf HEAD` both returned `0` locally on branch `codex/fix-replay-sort-clean`.
Reason: The referenced reviewed SHA is not the live PR branch head; the mapped FIXED commits are reachable ancestors of the current PR branch.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1734#discussion_r3233302285
Disposition: NOT-A-BUG
Evidence: `git merge-base --is-ancestor 42cb54728 HEAD`, `git merge-base --is-ancestor 8db30a3cf HEAD`, `git merge-base --is-ancestor a0e81b4b4 HEAD`, and `git merge-base --is-ancestor 48922b778 HEAD` returned `0` locally on branch `codex/fix-replay-sort-clean`; `git rev-parse HEAD` returned `48922b7786f8cfe9034b29db0ac3ca9322926094`.
Reason: The comment references a non-current reviewed SHA; the mapped FIXED commits are reachable from the live PR head used for current-head CI.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/actions/runs/25793116493/job/75765042475 -> c27b00b9d
Disposition: FIXED
Commit: c27b00b9d
Evidence: `tests/core/evidence/test_replay.py::test_existing_disconnected_known_supersede_cycle_fails_closed` covers the fail-closed orphan branch for a known-id supersede cycle; focused replay tests passed with `36 passed`.

## Premortem Risk Review

- Decision: `proceed with changes`.
- Most likely failure: stale-main CI and old package-index fallout mask a replay-specific regression.
  - Disposition: FIXED via `7de92822f`, which merges recovered `origin/main` into the PR branch without force-pushing.
- Most dangerous failure: fail-closed replay rejects valid full-ancestry supersession chains.
  - Disposition: FIXED via `42cb54728`, with `test_existing_supersession_chain_allows_full_ancestry_supersedes`.
- Hidden assumption: `applied_entry_ids` could be sorted while still proving topological replay.
  - Disposition: FIXED via `42cb54728`, with exact dependency-order assertions.
- Diff-coverage blind spot: newly added fail-closed branches stay unexecuted in CI even though focused happy-path tests pass.
  - Disposition: FIXED via `3dee930fc`, with disconnected successor, parallel successor, and existing non-promoting entry tests.
- Unknown supersede references: malformed ancestry can appear satisfied when it includes the active id plus a missing id.
  - Disposition: FIXED via `8db30a3cf`, with explicit known-id validation before successor selection.
- Diff coverage regression: current-head CI reported `core/evidence/replay.py` lines 243-244 uncovered.
  - Disposition: FIXED via `c27b00b9d`, with `test_existing_disconnected_known_supersede_cycle_fails_closed`.

## Merge Readiness

- [x] Pre-flight + agent consistency gates: PASS.
- [x] Canonical artifact: this file.
- [ ] Required current-head checks checked on current head at review time.
- [ ] PR body Phase2 mirror synchronized after this mapping update.
- [x] Post-open reviewers completed (`qa-engineer-agent` -> `bug-hunter`) and actionables dispositioned.
- [ ] Mandatory wait-window after latest review activity observed.

## Local Validation Evidence

- `python3 scripts/orchestration/check_preflight.py` — PASS
- `python3 scripts/orchestration/check_agent_consistency.py` — PASS
- `python3 scripts/orchestration/task_bootstrap.py --goal "PR 1734: rebase replay supersession deterministic ordering after main recovery, close review governance, premortem risks, and current-head CI" --task-class trust --pr-phase post_open_review --path core/evidence/replay.py --path tests/core/evidence/test_replay.py --path docs/review/PR_1734_FIXED_MAPPING.md --requested-agent agent-coordinator --requested-agent architecture-specialist --requested-agent security-auditor --requested-agent qa-engineer-agent --requested-agent bug-hunter` — PASS (`de8451495345`)
- `python3 scripts/orchestration/task_bootstrap.py --goal "fix replay supersession chains topologically" --task-class "Orchestration" --pr-phase post_open_review --path core/evidence/replay.py --path tests/core/evidence/test_replay.py --requested-agent agent-coordinator --requested-agent security-auditor --requested-agent qa-engineer-agent --requested-agent bug-hunter` — PASS
- `python3 scripts/orchestration/pr_review_context.py --pr 1734 --repo Katsiarynakavaleuskaya/PulsePlate` — PASS
- `python3 scripts/orchestration/pr_review_report.py --pr 1734 --repo Katsiarynakavaleuskaya/PulsePlate` — PASS
- `make validate-changed` — PASS
- `./.venv/bin/python -m pytest tests/core/evidence/test_replay.py -q` — PASS
- `.venv/bin/python -m pytest -q tests/core/evidence/test_replay.py tests/test_repo_policy_guards.py` — PASS (`35 passed`)
- `.venv/bin/python -m pytest -q tests/core/evidence/test_replay.py tests/test_repo_policy_guards.py` — PASS (`36 passed`)
- `.venv/bin/python -m ruff check core/evidence/replay.py tests/core/evidence/test_replay.py` — PASS
- `./.venv/bin/python -m bandit -r core/evidence scripts/orchestration -ll` — PASS (no security issues)
- `./.venv/bin/pip-audit -r requirements.txt` — FAIL expected baseline: existing `urllib3==2.6.3` CVEs (`CVE-2026-44431`, `CVE-2026-44432`) outside PR scope.
- `python3 scripts/ci/run_safety_audit.py --root .` — FAIL: missing `safety` binary in environment.
