# PR #1917 Fixed in Commit Mapping

PR: <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1917>

## Summary

This closeout hardens advisory wiki metadata normalization so separator variants
inside authority keys and values are compared through the same canonical text
policy before any advisory evidence or admission mapping is created.

The implementation stays inside `core/evidence/wiki_bridge.py` and focused
tests. It does not add runtime writes, DB access, provider calls, cache
admission, wiki compiler behavior, semantic cache behavior, or product-truth
authority.

## Lane Start Provenance

- Branch: `codex/fix-metadata-validation-for-forbidden-keys`
- Worktree: `worktrees/pr-1917-closeout`
- Task packet: `artifacts/orchestration/task_packets/e951467444d0.json`
- Role dispatch command: `python3 scripts/orchestration/role_dispatch_bridge.py --packet artifacts/orchestration/task_packets/e951467444d0.json --pretty`
- Declared role order executed: `agent-coordinator -> qa-engineer-agent -> bug-hunter -> security-auditor -> architecture-specialist`
- Implementation commit: `b738d4f5ef57d6a8caca29bf7ac8f5f5f4601efa`

## Scope

- Normalize authority-bearing metadata values with the same separator policy as
  metadata keys before checking authority fragments.
- Normalize configured authority fragments before fragment comparison.
- Add public API and admission-adapter regressions for dotted, dashed, nested,
  and list-shaped authority metadata values.
- Add the canonical fixed-mapping artifact required by PR governance.

## Out of Scope

- No runtime authority promotion.
- No advisory wiki compiler, ingest, query, or promotion behavior changes.
- No DB, provider, cache, semantic-cache, FastAPI, OpenAPI, frontend, or iOS
  changes.
- No review-thread resolution before this artifact and strict disposition gates.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed
- Notes: Valid Codex/Cubic authority-value bypass findings are fixed and mapped
  below. Sourcery's high-level maintainability suggestion is fixed with a short
  canonicalization comment. CodeRabbit's latest review reported no actionable
  comments. Codecov patch coverage is addressed by focused regression tests.
  Final merge readiness remains pending current-head CI, external bot state,
  strict disposition verification, strict merge-readiness verification, and the
  mandatory wait window.

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1917#discussion_r3380144634 -> b738d4f5ef57d6a8caca29bf7ac8f5f5f4601efa
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1917#pullrequestreview-4458022943 -> b738d4f5ef57d6a8caca29bf7ac8f5f5f4601efa
Disposition: FIXED
Commit: b738d4f5ef57d6a8caca29bf7ac8f5f5f4601efa
Evidence: `core/evidence/wiki_bridge.py` normalizes metadata claim text before authority key/value fragment comparisons, and `tests/core/evidence/test_wiki_bridge.py` covers the Codex-reported public API/admission bypass with `create_advisory_wiki_artifact_ref(..., metadata={"source.of.truth": "source.of.truth"})`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1917#discussion_r3380157273 -> b738d4f5ef57d6a8caca29bf7ac8f5f5f4601efa
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1917#pullrequestreview-4458036564 -> b738d4f5ef57d6a8caca29bf7ac8f5f5f4601efa
Disposition: FIXED
Commit: b738d4f5ef57d6a8caca29bf7ac8f5f5f4601efa
Evidence: `core/evidence/wiki_bridge.py` now applies separator normalization to authority values and normalized configured fragments before comparison, closing the Cubic-identified `source.of.truth` bypass. Focused pytest for `tests/core/evidence/test_wiki_bridge.py` passed.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1917#pullrequestreview-4458013142 -> b738d4f5ef57d6a8caca29bf7ac8f5f5f4601efa
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1917#issuecomment-4659161223 -> b738d4f5ef57d6a8caca29bf7ac8f5f5f4601efa
Disposition: FIXED
Commit: b738d4f5ef57d6a8caca29bf7ac8f5f5f4601efa
Evidence: `core/evidence/wiki_bridge.py` adds a concise comment above the canonical metadata claim normalizer explaining separator canonicalization with examples such as `api key` and `source.of.truth`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1917#issuecomment-4659160307
Disposition: NOT-A-BUG
Evidence: CodeRabbit reported "No actionable comments were generated in the recent review." Current fixed mapping separately covers the later actionable Codex/Cubic authority-value findings.
Reason: The CodeRabbit comment is a no-actionable review summary, not a requested code change.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1917#issuecomment-4659248806 -> b738d4f5ef57d6a8caca29bf7ac8f5f5f4601efa
Disposition: FIXED
Commit: b738d4f5ef57d6a8caca29bf7ac8f5f5f4601efa
Evidence: `tests/core/evidence/test_wiki_bridge.py` adds regression coverage for previously missing wiki bridge authority branches, including dotted/dashed authority values and admission-adapter metadata. Focused pytest and Experiment Runner pytest oracle passed.

## Experiment Runner Evidence

- Packet: `artifacts/orchestration/experiments/exp-3cb504eeaa7b.json`
- Artifact: `artifacts/orchestration/experiments/results/exp-3cb504eeaa7b.json`
- Mode: `oracle_only_governance_reviewer`
- Result: `accepted`
- Contribution: `fixed_mapping_review`
- `mutated_paths=[]`
- `shared_tree_untouched=true`
- `promotion_ready=false`
- `coauthor_required=true`
- Co-author reason: `Oracle-only governance evidence shapes PR 1917 fixed-mapping and validation evidence.`
- Oracle commands:
  - `python -m pytest -q tests/core/evidence/test_wiki_bridge.py`
  - `git diff --check HEAD`

## Post-Open Review Gates

- [x] `agent-coordinator`
  - Disposition: NOT-A-BUG
  - Evidence: coordinator scoped the closeout to the wiki bridge, focused tests,
    canonical mapping artifact, and PR body mirror, with no product-runtime,
    cache, provider, DB, frontend, or iOS expansion.
- [x] `qa-engineer-agent`
  - Disposition: NOT-A-BUG
  - Evidence: QA identified the public API/admission regression cases for
    dotted and list-shaped authority values. Those tests are now present in
    `tests/core/evidence/test_wiki_bridge.py`.
- [x] `bug-hunter`
  - Disposition: FIXED
  - Evidence: bug-hunter confirmed the raw lowercase authority-value bypass in
    `core/evidence/wiki_bridge.py`; commit
    `b738d4f5ef57d6a8caca29bf7ac8f5f5f4601efa` fixes the root cause.
- [x] `security-auditor`
  - Disposition: FIXED
  - Evidence: security-auditor confirmed separator variants such as
    `source.of.truth`, `source-of-truth`, `user.facing`, nested mappings, and
    list values. Commit `b738d4f5ef57d6a8caca29bf7ac8f5f5f4601efa` covers those
    cases while preserving advisory-only evidence boundaries.
- [x] `architecture-specialist`
  - Disposition: NOT-A-BUG
  - Evidence: architecture review accepted the narrow boundary in
    `core/evidence/wiki_bridge.py` and `tests/core/evidence/test_wiki_bridge.py`
    and found no runtime/compiler/cache/wiki-ingest/DB/provider expansion.
- [x] Codex Security diff scan / finding discovery
  - Disposition: NOT-A-BUG
  - Evidence: Codex Security diff scan completed under
    `/tmp/codex-security-scans/BMI-App_2025_clean/b738d4f5e_20260611T055446Z`.
    Completion receipts cover both PR-scoped files in
    `artifacts/02_discovery/work_ledger.jsonl`; final reports are `report.md`
    and `report.html`; no diff-scoped findings were identified.
- [x] `pulseplate-pr-review`
  - Disposition: NOT-A-BUG
  - Evidence: incremental dry-run from reviewed PR head
    `7f229f5ca90bf968eff9d4256ed3525c25e3ac58` to
    `b738d4f5ef57d6a8caca29bf7ac8f5f5f4601efa` reported 2 files, 53 additions,
    7 deletions, and no deterministic findings. Report:
    `/tmp/pr1917_pr_review_report_incremental.md`.
  - Reason: the earlier raw-ancestry dry-run surfaced unrelated local base-drift
    noise; the incremental closeout diff matches the post-open review delta.

## Local Validation

- PASS: `python3 scripts/orchestration/check_preflight.py`
- PASS: `python3 scripts/orchestration/check_agent_consistency.py`
- PASS: `python3 scripts/orchestration/task_bootstrap.py --goal "Close PR 1917 wiki metadata normalization hardening through merge-ready" --task-class security --path core/evidence/wiki_bridge.py --path tests/core/evidence/test_wiki_bridge.py --path docs/review/PR_1917_FIXED_MAPPING.md --requested-agent agent-coordinator --requested-agent security-auditor --requested-agent qa-engineer-agent --requested-agent bug-hunter --pr-phase post_open_review`
- PASS: `python3 scripts/orchestration/role_dispatch_bridge.py --packet artifacts/orchestration/task_packets/e951467444d0.json --pretty`
- PASS: `VENV_PYTHON="$(. scripts/hooks/repo_python.sh; resolve_repo_python "$PWD")"; "$VENV_PYTHON" -m pytest -q tests/core/evidence/test_wiki_bridge.py`
- PASS: `git diff --check`
- PASS: `DEV_PYTHON=/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python VENV_PYTHON=/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python make validate-changed`
- PASS: code commit hooks for `b738d4f5ef57d6a8caca29bf7ac8f5f5f4601efa`, including Black, Ruff, Bandit, backend changed tests, and policy hooks.
- PASS: Experiment Runner oracle-only governance review accepted with pytest and `git diff --check` oracle commands returning 0.
- PASS: Codex Security diff scan / finding discovery with no diff-scoped findings.
- PASS: `pre-commit run --all-files`
- STOPPED: full local `make verify` was started, passed `verify-env`, and entered
  `mypy`; the operator then explicitly narrowed this PR lane to
  `make validate-changed` because full verify runs the repository-scale test
  budget. No full-verify green claim is made.

## Merge Readiness

Not claimed.

Required before merge readiness:

- Run `pre-commit run --all-files`.
- Push current head and wait for current-head GitHub checks.
- Confirm CodeRabbit, Sourcery, Cubic, Codex, and Codecov have no remaining
  actionable blockers at current head.
- Run strict review-thread disposition with auth.
- Run strict merge-readiness with auth.
- Observe the mandatory wait window after latest review or bot activity.

## Deferred / Follow-ups

None.
