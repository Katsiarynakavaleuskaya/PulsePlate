# PR 1207 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1207#discussion_r2969286594 -> 415c3562
Disposition: FIXED
Commit: 415c3562
Evidence: `ios/PulsePlate/Services/SubscriptionManager.swift:252`, `ios/PulsePlate/Services/SubscriptionManager.swift:260`, `ios/PulsePlate/Services/SubscriptionManager.swift:276`, `ios/PulsePlateTests/Services/SubscriptionManagerTests.swift:390`
Reason: sanitized persisted activation pointers before refresh fetch and added regression coverage proving blank stored IDs are cleared without backend fetch.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1207#pullrequestreview-3985774046 -> 415c3562
Disposition: FIXED
Commit: 415c3562
Evidence: `ios/PulsePlate/Services/SubscriptionManager.swift:252`, `ios/PulsePlate/Services/SubscriptionManager.swift:260`, `ios/PulsePlate/Services/SubscriptionManager.swift:276`, `ios/PulsePlateTests/Services/SubscriptionManagerTests.swift:236`, `ios/PulsePlateTests/Services/SubscriptionManagerTests.swift:390`
Reason: normalized stored activation pointers before refresh fetch, short-circuited blank stored IDs locally, and added restore/refresh regression coverage for blank activation identifiers.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1207#pullrequestreview-3985772768
Disposition: NOT-A-BUG
Evidence: `ios/PulsePlate/Services/SubscriptionManager.swift:93`, `ios/PulsePlate/Services/SubscriptionManager.swift:360`, `ios/AGENTS.md:86`, `ios/AGENTS.md:88`, `ios/AGENTS.md:92`
Reason: the review bundles two high-level suggestions into one review URL; for governance this review is classified as NOT-A-BUG because runtime logging for invalid activation identifiers is already present and DTO-level normalization remains intentionally out of scope for the thin-client boundary.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1207#issuecomment-4102765863
Disposition: NOT-A-BUG
Evidence: `AGENTS.md:3`, `AGENTS.md:8`, `RUNBOOK_AGENT.md:113`
Reason: CodeRabbit's docstring coverage warning is advisory and not part of this repo's blocking merge gates; the required local bundle is `pre-commit run --all-files` plus `make verify`, both green on this lane.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1207#issuecomment-4102765990
Disposition: NOT-A-BUG
Evidence: `ios/PulsePlate/Services/SubscriptionManager.swift:93`, `ios/AGENTS.md:88`
Reason: the Sourcery review-guide comment duplicates the actionable review above and adds no independent unresolved item after the FIXED and NOT-A-BUG dispositions recorded here.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1207#pullrequestreview-3985798146 -> 9938ce65
Disposition: FIXED
Commit: 9938ce65
Evidence: `docs/review/PR_1207_FIXED_MAPPING.md:20`, `docs/review/PR_1207_FIXED_MAPPING.md:31`
Reason: cubic identified an ambiguous double-disposition on the same review URL; this artifact now assigns a single disposition to the Sourcery review and keeps each review URL unique.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1207#discussion_r2969317746 -> 9938ce65
Disposition: FIXED
Commit: 9938ce65
Evidence: `docs/review/PR_1207_FIXED_MAPPING.md:20`, `docs/review/PR_1207_FIXED_MAPPING.md:31`
Reason: fixed the exact mapping ambiguity called out by cubic on the review thread by removing the duplicate disposition for the same review URL.

## Merge Readiness
- Status: in progress; draft removed, local gates green, waiting for pushed head + current-head CI/governance re-check.
- Current fix commits:
  - `2f98dea7` — `docs(roadmap): close B3 in local tracker`
  - `d4c9a38f` — `feat(ios): harden thin subscription activation flow`
  - `415c3562` — `fix(ios): harden activation id refresh flow`
- Current scope discipline:
  - repo-local SoT alignment after B3 closure in PR #1189
  - iOS thin `SubscriptionManager` activation hardening
  - fail-closed regression tests and scoped `ios/AGENTS.md` policy sync
- Local validation executed on this lane:
  - `python3 scripts/orchestration/check_preflight.py`
  - targeted `make ios-test` for `SubscriptionManager` / billing runtime tests
  - `pytest -q tests/test_repo_policy_guards.py`
  - `bug-hunter` review pass (no findings in current diff; residual risk limited to missing higher-level relaunch integration coverage)
  - `pre-commit run --all-files`
  - `make verify`
- Bot status snapshot before push:
  - CodeRabbit: actionable review addressed in `415c3562`; summary docstring warning classified as advisory / NOT-A-BUG.
  - Sourcery: logging feedback addressed in `415c3562`; DTO-centralization suggestion classified as NOT-A-BUG for current thin-client boundary.
  - cubic identified no issues in `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1207#pullrequestreview-3985774235`.
- Required before merge:
  - push `415c3562` plus this artifact update and refresh PR body mirror
  - resolve threads only after disposition evidence exists on pushed commits
  - confirm current-head required checks are green with no pending required jobs
  - confirm no actionable bot comments remain
