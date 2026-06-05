# PR 1889 Fixed in Commit Mapping

## Scope

This PR hardens the repo subprocess policy guard so direct Python
`subprocess.run` / `subprocess.Popen` argv literals cannot use bare `python` or
`python3`. It also fixes the one existing bare `git` subprocess call surfaced by
the stricter AST scan. The PR does not change product runtime behavior,
Makefile recipes, workflow YAML, shell snippets, docs command examples, or the
Experiment Runner runtime.

## Lane Start Provenance

- Branch: `codex/harden-python-subprocess-policy`
- Base: `origin/main` at `854562d203c300161360f2b2c453e3b5daf7dd78`
- Current-head `main` CI before implementation: run `27022824181` completed
  successfully.
- Packet: `artifacts/orchestration/task_packets/6d720c0d1e1c.json`
- Dispatch manifest:
  `.venv/bin/python scripts/orchestration/role_dispatch_bridge.py --packet artifacts/orchestration/task_packets/6d720c0d1e1c.json --mode runtime --implementation-owner security-auditor --pretty`
- Declared pre-open role order:
  `agent-coordinator -> security-auditor -> bug-hunter -> architecture-specialist`
- Native role-agent transport note: `agent-coordinator` native subagent was
  attempted and timed out before returning; packet and manifest evidence remain
  attached, and post-open role review gates are still pending.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed
- Review threads inspected after PR open:
  - `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1889#discussion_r3363900835`
  - `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1889#discussion_r3363940005`
  - `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1889#discussion_r3365117348`
  - `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1889#discussion_r3365117355`
  - `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1889#discussion_r3365117359`
  - `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1889#discussion_r3365117362`
  - `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1889#discussion_r3365134732`
  - `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1889#discussion_r3365147162`
  - `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1889#discussion_r3365207231`
  - `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1889#discussion_r3365207234`
  - `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1889#discussion_r3365207235`
  - `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1889#discussion_r3365207240`
  - `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1889#discussion_r3365240998`
  - `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1889#discussion_r3365241000`
  - `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1889#discussion_r3365241009`
  - `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1889#discussion_r3365249101`
  - `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1889#pullrequestreview-4439503013`
  - `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1889#discussion_r3365271688`
  - `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1889#discussion_r3365271691`
  - `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1889#discussion_r3365271696`
  - `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1889#discussion_r3365321503`
  - `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1889#discussion_r3365321512`
  - `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1889#discussion_r3365321518`

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1889#discussion_r3363900835 -> 009061a5210aaa6b1a4af5e33722d06feb464175
Disposition: FIXED
Commit: 009061a5210aaa6b1a4af5e33722d06feb464175
Evidence: `tests/guards/test_subprocess_uses_absolute_binaries.py` now reads subprocess argv from the first positional argument or keyword `args=`, and `.venv/bin/python -m pytest tests/guards/test_subprocess_uses_absolute_binaries.py tests/test_repo_hygiene_no_worktrees_tracked_guard.py -q` passed with `11 passed`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1889#discussion_r3363940005
Disposition: NOT-A-BUG
Evidence: `git show -s --format=full 85b9af6181ed90ff949a18103a4db86dc5f1360e` shows the governed trailer `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>` on the implementation commit referenced by this artifact; this PR has not been squash-merged yet, so the synthetic squash-preview commit mentioned in the review comment is not the branch commit used as Experiment Runner evidence.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1889#discussion_r3365117348 -> 8a7248590199893f7977754f3998d00a2368b679
Disposition: FIXED
Commit: 8a7248590199893f7977754f3998d00a2368b679
Evidence: `tests/guards/test_subprocess_uses_absolute_binaries.py` resolves simple argv-list and argv-binary variables before evaluating the first subprocess binary; `.venv/bin/python -m pytest tests/guards/test_subprocess_uses_absolute_binaries.py tests/test_repo_hygiene_no_worktrees_tracked_guard.py -q` passed with `17 passed`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1889#discussion_r3365117355 -> 8a7248590199893f7977754f3998d00a2368b679
Disposition: FIXED
Commit: 8a7248590199893f7977754f3998d00a2368b679
Evidence: `tests/guards/test_subprocess_uses_absolute_binaries.py` now rejects absolute Python interpreter literals outside repo `.venv/bin/python` while preserving repo-approved `.venv/bin/python`; focused pytest passed with `17 passed`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1889#discussion_r3365117359 -> 8a7248590199893f7977754f3998d00a2368b679
Disposition: FIXED
Commit: 8a7248590199893f7977754f3998d00a2368b679
Evidence: `tests/guards/test_subprocess_uses_absolute_binaries.py` tracks `import subprocess as <alias>` and `from subprocess import <helper>` aliases for guarded subprocess helpers; focused pytest passed with `17 passed`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1889#discussion_r3365117362 -> 8a7248590199893f7977754f3998d00a2368b679
Disposition: FIXED
Commit: 8a7248590199893f7977754f3998d00a2368b679
Evidence: `tests/guards/test_subprocess_uses_absolute_binaries.py` now covers standard subprocess helpers `call`, `check_call`, and `check_output` in addition to `run` and `Popen`; focused pytest passed with `17 passed`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1889#discussion_r3365134732 -> 6a4241d4d0ebcaa1aeca42b4b6f97cc3cc0fc1b0
Disposition: FIXED
Commit: 6a4241d4d0ebcaa1aeca42b4b6f97cc3cc0fc1b0
Evidence: `tests/guards/test_subprocess_uses_absolute_binaries.py` now scans `tools/graphmap`, and `tools/graphmap/build_graph.py` resolves `git` with `shutil.which("git")` before `subprocess.check_output`; focused pytest passed with `17 passed`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1889#discussion_r3365147162 -> 6a4241d4d0ebcaa1aeca42b4b6f97cc3cc0fc1b0
Disposition: FIXED
Commit: 6a4241d4d0ebcaa1aeca42b4b6f97cc3cc0fc1b0
Evidence: `docs/review/PR_1889_FIXED_MAPPING.md` now separates adjacent review-thread mapping blocks with blank lines while preserving the strict canonical mapping format; `.venv/bin/python scripts/ci/check_pr_body_phase2_gates.py --pr-number 1889` passed.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1889#discussion_r3365207231 -> a403b8e392cff88df8c0083364b82b94f447c2c9
Disposition: FIXED
Commit: a403b8e392cff88df8c0083364b82b94f447c2c9
Evidence: `tests/guards/test_subprocess_uses_absolute_binaries.py` now treats versioned short Python names such as `python3.12` as disallowed repo interpreter bypasses; focused pytest passed with `21 passed`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1889#discussion_r3365207234 -> a403b8e392cff88df8c0083364b82b94f447c2c9
Disposition: FIXED
Commit: a403b8e392cff88df8c0083364b82b94f447c2c9
Evidence: `tests/guards/test_subprocess_uses_absolute_binaries.py` resolves simple `Path(...)` and `str(...)` wrappers around subprocess argv binary literals; focused pytest passed with `21 passed`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1889#discussion_r3365207235 -> a403b8e392cff88df8c0083364b82b94f447c2c9
Disposition: FIXED
Commit: a403b8e392cff88df8c0083364b82b94f447c2c9
Evidence: `tests/guards/test_subprocess_uses_absolute_binaries.py` rejects parent traversal in absolute repo `.venv/bin` Python literals instead of accepting lexical `..` paths; focused pytest passed with `21 passed`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1889#discussion_r3365207240 -> a403b8e392cff88df8c0083364b82b94f447c2c9
Disposition: FIXED
Commit: a403b8e392cff88df8c0083364b82b94f447c2c9
Evidence: `tests/guards/test_subprocess_uses_absolute_binaries.py` now inspects `executable=` overrides on guarded subprocess calls and rejects bare Python overrides even when argv uses `sys.executable`; focused pytest passed with `21 passed`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1889#discussion_r3365240998 -> 1c37c8afb33d93861933690fa74c8da6274823ad
Disposition: FIXED
Commit: 1c37c8afb33d93861933690fa74c8da6274823ad
Evidence: `tests/guards/test_subprocess_uses_absolute_binaries.py` now resolves simple argv variable assignments only from the current lexical scope chain, preventing sibling function/class assignments from influencing subprocess guard decisions; focused pytest passed with `24 passed`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1889#discussion_r3365241000 -> 1c37c8afb33d93861933690fa74c8da6274823ad
Disposition: FIXED
Commit: 1c37c8afb33d93861933690fa74c8da6274823ad
Evidence: `tests/guards/test_subprocess_uses_absolute_binaries.py` now parses literal string-form subprocess commands with `shlex.split(...)` and rejects bare Python or short external binaries in that form; focused pytest passed with `24 passed`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1889#discussion_r3365241009
Disposition: NOT-A-BUG
Evidence: duplicate/stale versioned-Python feedback; `a403b8e392cff88df8c0083364b82b94f447c2c9` already changed the short-name predicate to use `_is_python_binary_name(...)`, and focused pytest now covers `python3.12` with `24 passed`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1889#discussion_r3365249101 -> 1c37c8afb33d93861933690fa74c8da6274823ad
Disposition: FIXED
Commit: 1c37c8afb33d93861933690fa74c8da6274823ad
Evidence: `tests/guards/test_subprocess_uses_absolute_binaries.py` now parses literal string-form subprocess commands with `shlex.split(...)`; focused pytest passed with `24 passed`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1889#pullrequestreview-4439503013
Disposition: NOT-A-BUG
Evidence: CodeRabbit review summary is covered by its individual mapped review comments in this section; no separate code change is required for the summary URL itself.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1889#discussion_r3365271688 -> 1c37c8afb33d93861933690fa74c8da6274823ad
Disposition: FIXED
Commit: 1c37c8afb33d93861933690fa74c8da6274823ad
Evidence: `tests/guards/test_subprocess_uses_absolute_binaries.py` now limits recent assignment lookup to the current lexical scope chain; focused pytest passed with `24 passed`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1889#discussion_r3365271691
Disposition: NOT-A-BUG
Evidence: duplicate/stale versioned-Python feedback; `a403b8e392cff88df8c0083364b82b94f447c2c9` already rejects versioned Python short names, and focused pytest now covers `python3.12` with `24 passed`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1889#discussion_r3365271696 -> 1c37c8afb33d93861933690fa74c8da6274823ad
Disposition: FIXED
Commit: 1c37c8afb33d93861933690fa74c8da6274823ad
Evidence: `tests/guards/test_subprocess_uses_absolute_binaries.py` now parses literal string-form subprocess commands with `shlex.split(...)`; focused pytest passed with `24 passed`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1889#discussion_r3365321503 -> b290796d0eccbc1cd4e09c693f1592013afb858d
Disposition: FIXED
Commit: b290796d0eccbc1cd4e09c693f1592013afb858d
Evidence: `tests/guards/test_subprocess_uses_absolute_binaries.py` treats non-approved Python environment keys such as `PYTHON` as disallowed interpreter sources while preserving approved `VENV_PYTHON`/`DEV_PYTHON`; focused pytest passed with `28 passed`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1889#discussion_r3365321512 -> b290796d0eccbc1cd4e09c693f1592013afb858d
Disposition: FIXED
Commit: b290796d0eccbc1cd4e09c693f1592013afb858d
Evidence: `tests/guards/test_subprocess_uses_absolute_binaries.py` checks all same-scope reaching assignments for disallowed subprocess binaries before accepting a later safe assignment; focused pytest passed with `28 passed`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1889#discussion_r3365321518 -> b290796d0eccbc1cd4e09c693f1592013afb858d
Disposition: FIXED
Commit: b290796d0eccbc1cd4e09c693f1592013afb858d
Evidence: `tests/guards/test_subprocess_uses_absolute_binaries.py` inspects `/usr/bin/env` launcher argv and rejects disallowed short Python targets after the absolute env binary; focused pytest passed with `28 passed`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1889#discussion_r3365407894 -> 930284e78a0ad1f73c77c302507ad3be6def3b68
Disposition: FIXED
Commit: 930284e78a0ad1f73c77c302507ad3be6def3b68
Evidence: `tests/guards/test_subprocess_uses_absolute_binaries.py` now resolves `/usr/bin/env` targets after `-S`, env options, and `KEY=value` assignment prefixes; focused pytest passed with `30 passed`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1889#pullrequestreview-4439751748
Disposition: NOT-A-BUG
Evidence: Cubic review summary is covered by its two individual mapped review comments in this section; no separate code change is required for the summary URL itself.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1889#discussion_r3365428490 -> 930284e78a0ad1f73c77c302507ad3be6def3b68
Disposition: FIXED
Commit: 930284e78a0ad1f73c77c302507ad3be6def3b68
Evidence: `tests/guards/test_subprocess_uses_absolute_binaries.py` now treats only branch-dependent assignments as multi-reach checks and allows a later linear safe overwrite; focused pytest passed with `30 passed`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1889#discussion_r3365428493 -> 930284e78a0ad1f73c77c302507ad3be6def3b68
Disposition: FIXED
Commit: 930284e78a0ad1f73c77c302507ad3be6def3b68
Evidence: `tests/guards/test_subprocess_uses_absolute_binaries.py` now skips `/usr/bin/env` options and env assignment prefixes before evaluating the actual launcher target; focused pytest passed with `30 passed`.

## Implementation Evidence

- Implementation commit: `85b9af618`
- Keyword-args guard follow-up commit: `009061a52`
- Alias/helper/absolute-python guard follow-up commit: `8a724859`
- Graphmap scan and mapping-separation follow-up commit: `6a4241d`
- Python executable edge-case follow-up commit: `a403b8e`
- String-form and scope-aware assignment follow-up commit: `1c37c8a`
- Env-based Python and env-launcher follow-up commit: `b290796`
- Env launcher option and assignment-overwrite follow-up commit: `930284e`
- Mapping artifact commit: `aa478a2e0`
- Evidence: `tests/guards/test_subprocess_uses_absolute_binaries.py` now parses direct `subprocess.run` / `subprocess.Popen` calls with AST, rejects bare `python` / `python3` literals, preserves `sys.executable` and repo interpreter variable usage, and keeps existing `shutil.which` guidance for external tools; root policy and the orchestration contract matrix document the invariant.

## Premortem Findings

- Disposition: FIXED
  Evidence: most likely failure was the stricter AST guard surfacing a hidden
  existing violation; it found one bare `git` subprocess in
  `tests/test_repo_hygiene_no_worktrees_tracked_guard.py`, now fixed with
  `shutil.which("git")`.
- Disposition: FIXED
  Evidence: most dangerous failure was overbroad matching of docs, shell
  snippets, workflow YAML, or Experiment Runner oracle command strings; the
  guard inspects only Python AST call nodes for `subprocess.run` and
  `subprocess.Popen`.
- Disposition: NOT-A-BUG
  Evidence: variable-based subprocess interpreters remain allowed because this
  PR intentionally targets first-argv string literals only; root policy now
  names approved interpreter sources (`sys.executable`, `VENV_PYTHON`,
  `DEV_PYTHON`, repo `.venv/bin/python`, and Experiment Runner resolver
  pattern).

## Experiment Runner Evidence

- Packet: `artifacts/orchestration/experiments/exp-616bdc7819d9.json`
- Artifact: `artifacts/orchestration/experiments/results/exp-616bdc7819d9.json`
- Mode: `oracle_only_governance_reviewer`
- Status: `accepted`
- Contribution kind: `commit_decision`
- `shared_tree_untouched`: `true`
- `source_diff_applied`: `true`
- `source_diff_paths`:
  - `AGENTS.md`
  - `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md`
  - `tests/guards/test_subprocess_uses_absolute_binaries.py`
  - `tests/test_repo_hygiene_no_worktrees_tracked_guard.py`
- `oracle_commands_executed`: `2`
- Co-author trailer is present on `85b9af618`.

## Validation

- PASS: current-head `main` CI run `27022824181` completed successfully before
  implementation.
- PASS: `.venv/bin/python scripts/orchestration/check_preflight.py --path AGENTS.md --path tests/guards/test_subprocess_uses_absolute_binaries.py --path tests/test_repo_hygiene_no_worktrees_tracked_guard.py --path docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md`
- PASS: `.venv/bin/python scripts/orchestration/check_agent_consistency.py`
- PASS: `.venv/bin/python -m pytest tests/guards/test_subprocess_uses_absolute_binaries.py tests/test_repo_hygiene_no_worktrees_tracked_guard.py -q`
  (`9 passed`)
- PASS: `.venv/bin/python -m pytest tests/guards/test_subprocess_uses_absolute_binaries.py tests/test_repo_hygiene_no_worktrees_tracked_guard.py -q`
  after `args=` review fix (`11 passed`)
- PASS: `.venv/bin/python -m pytest tests/guards/test_subprocess_uses_absolute_binaries.py tests/test_repo_hygiene_no_worktrees_tracked_guard.py -q`
  after alias/helper/variable/absolute-python review fix (`17 passed`)
- PASS: `.venv/bin/python -m pytest tests/guards/test_subprocess_uses_absolute_binaries.py tests/test_repo_hygiene_no_worktrees_tracked_guard.py -q`
  after `tools/graphmap` scan follow-up (`17 passed`)
- PASS: `.venv/bin/python scripts/ci/check_pr_body_phase2_gates.py --pr-number 1889`
  after mapping block separation
- PASS: `.venv/bin/python -m pytest tests/guards/test_subprocess_uses_absolute_binaries.py tests/test_repo_hygiene_no_worktrees_tracked_guard.py -q`
  after versioned-python/path-wrapper/traversal/executable override follow-up
  (`21 passed`)
- PASS: `.venv/bin/python -m pytest tests/guards/test_subprocess_uses_absolute_binaries.py tests/test_repo_hygiene_no_worktrees_tracked_guard.py -q`
  after string-form subprocess and scope-aware assignment follow-up (`24 passed`)
- PASS: `.venv/bin/python -m pytest tests/guards/test_subprocess_uses_absolute_binaries.py tests/test_repo_hygiene_no_worktrees_tracked_guard.py -q`
  after env-based Python and `/usr/bin/env` launcher follow-up (`28 passed`)
- PASS: `.venv/bin/python -m pytest tests/guards/test_subprocess_uses_absolute_binaries.py tests/test_repo_hygiene_no_worktrees_tracked_guard.py -q`
  after env launcher option and assignment-overwrite follow-up (`30 passed`)
- PASS: `.venv/bin/python -m pytest tests/test_experiment_runner.py -k "python_oracle_path_prefix or temporary_sandbox_env" -q`
  (`10 passed`)
- PASS: `make validate-changed` after commit selected
  `tests/guards/test_subprocess_uses_absolute_binaries.py` and
  `tests/test_repo_hygiene_no_worktrees_tracked_guard.py` (`9 passed`)
- PASS: `pre-commit run --all-files`
- PASS: pre-push hooks, including backend pytest and full-repo Bandit

## Merge Readiness

Not merge-ready at PR open. Required post-open role review, Codex Security diff
scan / finding discovery, external bot review, current-head PR CI, and strict
merge-readiness gates remain pending.
