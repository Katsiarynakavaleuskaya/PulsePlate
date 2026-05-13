<!-- markdownlint-disable MD013 MD034 -->
# PR 1734 Fixed In Commit Mapping

- PR: <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1734>
- Branch: `codex/fix-replay-sort-clean`
- Title: `fix(evidence): replay supersession chains topologically`
- Implementing commits:
  - `02d968265` — fix replay supersession supersedes ordering and keep fail-closed behavior.
  - `7de92822f` — merge current `origin/main` after #1738/#1740/#1739 recovery without rewriting PR history.
  - `42cb54728` — fix full-ancestry supersession replay, dependency-order evidence, and indexed successor lookup.

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

## Premortem Risk Review

- Decision: `proceed with changes`.
- Most likely failure: stale-main CI and old package-index fallout mask a replay-specific regression.
  - Disposition: FIXED via `7de92822f`, which merges recovered `origin/main` into the PR branch without force-pushing.
- Most dangerous failure: fail-closed replay rejects valid full-ancestry supersession chains.
  - Disposition: FIXED via `42cb54728`, with `test_existing_supersession_chain_allows_full_ancestry_supersedes`.
- Hidden assumption: `applied_entry_ids` could be sorted while still proving topological replay.
  - Disposition: FIXED via `42cb54728`, with exact dependency-order assertions.

## Merge Readiness

- [x] Pre-flight + agent consistency gates: PASS.
- [x] Canonical artifact: this file.
- [x] Required current-head checks checked on current head at review time.
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
- `/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python -m pytest -q tests/core/evidence/test_replay.py tests/test_repo_policy_guards.py` — PASS (`31 passed`)
- `/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python -m ruff check core/evidence/replay.py tests/core/evidence/test_replay.py` — PASS
- `./.venv/bin/python -m bandit -r core/evidence scripts/orchestration -ll` — PASS (no security issues)
- `./.venv/bin/pip-audit -r requirements.txt` — FAIL expected baseline: existing `urllib3==2.6.3` CVEs (`CVE-2026-44431`, `CVE-2026-44432`) outside PR scope.
- `python3 scripts/ci/run_safety_audit.py --root .` — FAIL: missing `safety` binary in environment.
