<!-- markdownlint-disable MD013 MD034 -->
# PR 1752 Fixed In Commit Mapping

- PR: <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1752>
- Branch: `codex/experiment-runner-gnhi-crypto-policy`
- Title: `feat(orchestration): govern experiment runner identity`
- Implementing commits:
  - `f53cb69db` - governed Experiment Runner identity boundary, offline guard, tests, and nested git environment hardening.
  - `e33e29c2d` - initial PR 1752 fixed-mapping artifact.
  - `229777a55` - CodeRabbit CLI governance fixes for backlog priority ordering and Phase 2 fixed-mapping formatting.
  - `916b51d57` - mapping entry for CodeRabbit CLI governance fixes.
  - `6f1e29fb8` - canonical no-actionable review-thread mapping format for Phase 2 parser compatibility.
  - `7b8c78a35` - mapping entry for canonical Phase 2 parser format fix.
  - `5790abc7f` - PR body Phase 2 mirror validation evidence.
  - `19d2c92ee` - fail-closed malformed policy validation and token-prefix guard hardening.
  - `2853fca3e` - repo-standard `make validate-changed` validation command wording.
  - `4f431c553` - additional fail-closed identity policy bypass hardening for repeated separators, token-shaped keys, Slack app/config tokens, and authority drift.
  - `0aec2bf28` - reclassified coordinator task-packet evidence and mapped identity guard bypass findings.
  - `cf1174f86` - sanitized token-shaped key diagnostics, canonical sensitive boolean scope, and separator-normalized authority drift checks.
  - `2e9a48c6b` - normalized sandbox oracle PATH handling so branch-diff validation with relative repo venv PATH stays deterministic.
  - `1dbb8b612` - closed final Cubic/Codex edge cases for unset PATH fallback, punctuation-normalized sensitive keys, duplicate Slack blocks, and duplicate commit-context authority drift.
  - `432f5e51b` - rejected duplicate boundary blocks across naming styles, redacted sensitive field diagnostics, and blocked separator-variant authority fields inside the canonical boundary.
  - `647f49e12` - redacted secret-shaped ancestor path components in authority and duplicate-boundary diagnostics.
  - `c2fb89aaf` - expanded secret guards for API-key fields, PGP private key blocks, prefix duplicate boundaries, and dotted sensitive ancestor redaction.
  - `eeabbca59` - detected camelCase authority drift fields.
  - `fb03b0caf` - rejected password fields, Slack webhook URLs, and duplicate JSON keys before identity policy validation.
  - `fbd542f77` - detected private signing-key aliases with descriptors between private and key tokens.
  - `c1826f6da` - normalized the fixed-mapping disposition block for strict parser compatibility.
- Scope: Experiment Runner cryptographic attribution boundary, policy validation, Slack identity deferral, and focused runner test hardening.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

### Fixed in Commit Mapping

Disposition: FIXED
Commit: see mapping entries below
Evidence: CodeRabbit/Cubic/Codex bot findings were fixed by checking the fixed-mapping artifact checkboxes, hardening malformed policy validation to fail closed without raw `TypeError`, expanding current token-prefix detection for `github_pat_`, `xapp-`, and `xoxc-`, detecting token-shaped JSON keys without leaking them in diagnostics, rejecting API-key fields, access-key fields, password fields, Slack webhook URLs, PGP private key blocks, repeated and punctuation separators in sensitive key names, redacting sensitive field names and secret-shaped ancestor paths in diagnostics, rejecting duplicate sensitive booleans outside canonical paths, rejecting duplicate JSON keys before policy validation, rejecting separator/camelCase authority drift and duplicate `allowed_commit_context` drift inside and outside `authority_boundary`, rejecting compact authority aliases inside `authority_boundary`, rejecting camelCase private-key and access-key aliases, rejecting private signing-key aliases with descriptor tokens, rejecting duplicate Git attribution, cryptographic, notification, and Slack identity boundary blocks across naming styles and prefix/suffix variants, adding safe unset-PATH fallback, and replacing the brittle validation command text with `make validate-changed`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1752#discussion_r3242806268 -> 0aec2bf28
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1752#discussion_r3242806276 -> 4f431c553
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1752#discussion_r3242806284 -> 4f431c553
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1752#discussion_r3242806290 -> 4f431c553
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1752#discussion_r3242806297 -> 4f431c553
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1752#discussion_r3242806302 -> 4f431c553
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1752#discussion_r3242812229 -> 229777a55
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1752#discussion_r3242812243 -> 19d2c92ee
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1752#pullrequestreview-4291639395 -> 19d2c92ee
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1752#discussion_r3242847407 -> 19d2c92ee
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1752#discussion_r3242847414 -> 19d2c92ee
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1752#discussion_r3242847423 -> 19d2c92ee
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1752#discussion_r3242847432 -> 19d2c92ee
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1752#pullrequestreview-4291682243 -> 19d2c92ee
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1752#discussion_r3242894051 -> 2853fca3e
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1752#pullrequestreview-4291735416 -> 2853fca3e
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1752#discussion_r3243532243 -> cf1174f86
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1752#discussion_r3243532245 -> cf1174f86
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1752#discussion_r3243532247 -> cf1174f86
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1752#discussion_r3243710822 -> 1dbb8b612
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1752#discussion_r3243715290 -> 1dbb8b612
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1752#discussion_r3243715295 -> 1dbb8b612
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1752#discussion_r3243715301 -> 1dbb8b612
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1752#pullrequestreview-4292742187 -> 1dbb8b612
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1752#discussion_r3243858037 -> 432f5e51b
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1752#discussion_r3243867159 -> 432f5e51b
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1752#discussion_r3243867161 -> 432f5e51b
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1752#discussion_r3243867166 -> 432f5e51b
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1752#pullrequestreview-4292917793 -> 432f5e51b
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1752#discussion_r3243929617 -> 647f49e12
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1752#discussion_r3243929637 -> 647f49e12
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1752#discussion_r3243988614 -> c2fb89aaf
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1752#discussion_r3243988617 -> c2fb89aaf
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1752#discussion_r3243988622 -> c2fb89aaf
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1752#discussion_r3243988629 -> c2fb89aaf
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1752#discussion_r3244113316 -> eeabbca59
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1752#discussion_r3247757095 -> fb03b0caf
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1752#discussion_r3247757106 -> fb03b0caf
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1752#discussion_r3247757115 -> fb03b0caf
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1752#discussion_r3247909972 -> c1826f6da
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1752#discussion_r3247909978 -> c1826f6da
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1752#discussion_r3247909983 -> fbd542f77
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1752#discussion_r3248180081 -> 764da91f3
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1752#pullrequestreview-4298103971 -> 764da91f3
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1752#discussion_r3248260314 -> 3e7c37439
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1752#discussion_r3248260321 -> 3e7c37439

Disposition: NOT-A-BUG
Evidence: Current branch head contains the mapped fix commits. `git merge-base --is-ancestor` reports `reachable` for mapped SHAs including `0aec2bf28`, `4f431c553`, `229777a55`, `19d2c92ee`, `2853fca3e`, `cf1174f86`, `1dbb8b612`, `432f5e51b`, `647f49e12`, `c2fb89aaf`, `eeabbca59`, `fb03b0caf`, `c1826f6da`, `fbd542f77`, `764da91f3`, and `8e58d133`; the cited `943a4cdd` was not the current PR head after the later pushes.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1752#discussion_r3248260326

## Role-Agent Findings

Disposition: FIXED
Commit: `f53cb69db`
Evidence: `scripts/orchestration/check_experiment_runner_identity.py` rejects placeholder attribution, non-governed attribution, private-key/token-shaped values, sensitive key names with separators/spaces, merge/readiness/thread authority drift, notification delivery drift, and Slack crypto-identity drift. `tests/test_experiment_runner_identity_policy.py` covers the regressions raised by `qa-engineer-agent` and `bug-hunter`.

Disposition: FIXED
Commit: `f53cb69db`
Evidence: `scripts/orchestration/experiment_runner.py` strips inherited `GIT_*` environment variables from nested git subprocesses so isolated experiment checkouts are not affected by parent commit/pre-commit hook context. `tests/test_experiment_runner.py` covers hook-style `GIT_INDEX_FILE` leakage.

Disposition: FIXED
Commit: `2e9a48c6b`
Evidence: `scripts/orchestration/experiment_runner.py` normalizes relative PATH entries to absolute paths before sandboxed oracle execution, preventing branch-diff validation from resolving `../../.venv/bin/python3` relative to temporary checkouts. `tests/test_experiment_runner.py` covers relative PATH normalization.

Disposition: NOT-A-BUG
Evidence: Coordinator scope was refreshed after review to include actual touched files, including `scripts/orchestration/experiment_runner.py`, `scripts/AGENTS.md`, `tests/test_experiment_runner.py`, and `docs/orchestration/GOVERNED_NON_HUMAN_IDENTITY_POLICY.json`.

Disposition: DEFERRED
Backlog: `docs/roadmap/BACKLOG_LEDGER.md#ledger-p2-experiment-runner-slack-identity-boundary`
Evidence: Slack identity is explicitly deferred as notification/display identity only. It is not a cryptographic Git identity and requires a separate security-governed PR.

Disposition: FIXED
Commit: `229777a55`
Evidence: CodeRabbit CLI governance findings were addressed by moving the Slack follow-up from the Open Items insertion point into the `### P2` section, changing the fixed-mapping heading to `### Fixed in Commit Mapping`, completing the discussion-thread/fixed-mapping checklist for the local review pass, and removing the stale draft-only note.

## Local Validation

- `python3 scripts/orchestration/check_preflight.py --path ...` PASS.
- `python3 scripts/orchestration/check_agent_consistency.py` PASS.
- `scripts/orchestration/check_experiment_runner_identity.py --json` PASS.
- `pytest -q tests/test_experiment_runner_identity_policy.py tests/test_experiment_runner.py tests/test_experiment_notify.py` PASS.
- `pytest -q tests/test_experiment_runner_identity_policy.py` PASS after `cf1174f86`.
- `make validate-changed` PASS after `2e9a48c6b`.
- `pytest -q tests/test_experiment_runner_identity_policy.py tests/test_experiment_runner.py tests/test_experiment_notify.py` PASS after `1dbb8b612`.
- `make validate-changed` PASS after `1dbb8b612`.
- `pytest -q tests/test_experiment_runner_identity_policy.py tests/test_experiment_runner.py tests/test_experiment_notify.py` PASS after `432f5e51b`.
- `make validate-changed` PASS after `432f5e51b`.
- `pytest -q tests/test_experiment_runner_identity_policy.py tests/test_experiment_runner.py tests/test_experiment_notify.py` PASS after `647f49e12`.
- `make validate-changed` PASS after `647f49e12`.
- `pytest -q tests/test_experiment_runner_identity_policy.py tests/test_experiment_runner.py tests/test_experiment_notify.py` PASS after `c2fb89aaf`.
- `make validate-changed` PASS after `c2fb89aaf`.
- `pytest -q tests/test_experiment_runner_identity_policy.py tests/test_experiment_runner.py tests/test_experiment_notify.py` PASS after `eeabbca59`.
- `make validate-changed` PASS after `eeabbca59`.
- `scripts/orchestration/check_experiment_runner_identity.py --json` PASS after `fb03b0caf`.
- `pytest -q tests/test_experiment_runner_identity_policy.py tests/test_experiment_runner.py tests/test_experiment_notify.py` PASS after `fb03b0caf`.
- `make validate-changed` PASS after `fb03b0caf`.
- `mypy --explicit-package-bases scripts/orchestration/check_experiment_runner_identity.py tests/test_experiment_runner_identity_policy.py` PASS after `fb03b0caf`.
- `bandit -q scripts/orchestration/check_experiment_runner_identity.py` PASS after `fb03b0caf`.
- `pytest -q tests/test_experiment_runner_identity_policy.py tests/test_experiment_runner.py tests/test_experiment_notify.py` PASS after `fbd542f77`.
- `make validate-changed` PASS after `fbd542f77`.
- `mypy --explicit-package-bases scripts/orchestration/check_experiment_runner_identity.py tests/test_experiment_runner_identity_policy.py` PASS after `fbd542f77`.
- `bandit -q scripts/orchestration/check_experiment_runner_identity.py` PASS after `fbd542f77`.
- `python3 scripts/orchestration/review_mapping_artifact.py docs/review/PR_1752_FIXED_MAPPING.md` PASS after `c1826f6da`.
- `pre-commit run --all-files` PASS after `c1826f6da`.
- `black --check` on changed Python files PASS.
- `flake8` on identity guard/tests PASS.
- `mypy --explicit-package-bases` on identity guard/tests PASS.
- `bandit -q scripts/orchestration/check_experiment_runner_identity.py` PASS.
- `pre-commit run --all-files` PASS.
- `make validate-changed` PASS.
- `pytest -q tests/test_experiment_runner_identity_policy.py` PASS after `764da91f3`.
- `scripts/orchestration/check_experiment_runner_identity.py --json` PASS after `764da91f3`.
- `black --check` on changed Python files PASS after `764da91f3`.
- `flake8` on identity guard/tests PASS after `764da91f3`.
- `mypy --explicit-package-bases` on identity guard/tests PASS after `764da91f3`.
- `bandit -q scripts/orchestration/check_experiment_runner_identity.py` PASS after `764da91f3`.
- `make validate-changed` PASS after `764da91f3`.
- `pre-commit run --all-files` PASS after `764da91f3`.
- `pytest -q tests/test_experiment_runner_identity_policy.py` PASS after `3e7c37439`.
- `scripts/orchestration/check_experiment_runner_identity.py --json` PASS after `3e7c37439`.
- `black --check` on changed Python files PASS after `3e7c37439`.
- `flake8` on identity guard/tests PASS after `3e7c37439`.
- `mypy --explicit-package-bases` on identity guard/tests PASS after `3e7c37439`.
- `bandit -q scripts/orchestration/check_experiment_runner_identity.py` PASS after `3e7c37439`.
- `make validate-changed` PASS after `3e7c37439`.
- `pre-commit run --all-files` PASS after `3e7c37439`.
- Pre-push hooks PASS: mypy, pip-audit, backend tests, full bandit, docker-build-test hook.
- `python3 scripts/ci/check_pr_body_phase2_gates.py --body "$(gh pr view 1752 --json body -q .body)" --pr-number 1752` PASS after live PR body mirror update.

## Merge Readiness

- [ ] Current-head CI terminal and required checks passing.
- [ ] CodeRabbit no actionables.
- [ ] Cubic no actionables.
- [ ] Sourcery no actionables.
- [ ] Discussion-thread pass complete.
- [ ] Fixed mapping artifact/body mirror updated after review activity.
- [ ] Required wait-window complete.
