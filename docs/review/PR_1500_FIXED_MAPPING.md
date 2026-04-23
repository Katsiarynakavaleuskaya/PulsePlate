# PR 1500 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
Disposition: NOT-A-BUG
Evidence: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1500#issuecomment-4300578742
Reason: CodeRabbit only posted a draft-state status note (`Review skipped`) and did not request any code or documentation changes on the current head.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1500#issuecomment-4300578742

Disposition: NOT-A-BUG
Evidence: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1500#issuecomment-4300586504
Reason: Sourcery generated a reviewer guide and summary only; it contains no requested fixes or unresolved action items for this PR head.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1500#issuecomment-4300586504

Disposition: FIXED
Commit: fb2987564b3939edc26bd7f84dda1ce45717d953
Evidence: `setup_custom_mcp.py`; `tests/test_setup_custom_mcp_coverage.py`
Reason: The environment merge path now strips whitespace around managed keys before upserting, and the test suite covers whitespace around `.env` keys so reruns do not create duplicate managed entries.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1500#discussion_r3131152464 -> fb2987564b3939edc26bd7f84dda1ce45717d953
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1500#pullrequestreview-4162814275 -> fb2987564b3939edc26bd7f84dda1ce45717d953

Disposition: FIXED
Commit: fb2987564b3939edc26bd7f84dda1ce45717d953
Evidence: `docs/deploy/MANUAL_API.md`
Reason: The bare OpenAI API keys URL is now wrapped in angle brackets and the MCP troubleshooting heading no longer has trailing punctuation, satisfying the markdownlint failures reported by CodeRabbit.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1500#discussion_r3131179004 -> fb2987564b3939edc26bd7f84dda1ce45717d953
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1500#discussion_r3131179032 -> fb2987564b3939edc26bd7f84dda1ce45717d953

Disposition: FIXED
Commit: fb2987564b3939edc26bd7f84dda1ce45717d953
Evidence: `docs/dev/CODEX_SKILLS.md`
Reason: The useful installer examples now include the `--no-cybersec` path that the same document recommends for normal PulsePlate repo work.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1500#discussion_r3131179046 -> fb2987564b3939edc26bd7f84dda1ce45717d953
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1500#pullrequestreview-4162850417 -> fb2987564b3939edc26bd7f84dda1ce45717d953

Disposition: NOT-A-BUG
Evidence: https://github.com/Katsiarynakavaleuskaya/anthropic-cybersecurity-skills/pull/1
Reason: The submodule pointer already referenced commit `d04d818b41cc300f8110f17ea167fa494db7fb29`; the upstream PR containing that commit was promoted from draft and merged on 2026-04-23, so the pointer now references a stable merged upstream commit.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1500#discussion_r3131179069

Disposition: FIXED
Commit: e86f17d6799593982f413e3a74651fb6645f4fde
Evidence: `setup_custom_mcp.py`
Reason: Runtime setup output no longer prints key-oriented replacement instructions that CodeQL classified as clear-text sensitive logging; it now gives generic placeholder and git-exclusion guidance without echoing sensitive field details.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1500#discussion_r3131225599 -> e86f17d6799593982f413e3a74651fb6645f4fde

Disposition: FIXED
Commit: 6665329b5cd94e893496a78790f3f4564241e312
Evidence: `setup_custom_mcp.py`; `tests/test_setup_custom_mcp_coverage.py`
Reason: The `.env` setup path no longer upserts `OPENAI_API_KEY` into generated env content and does not rewrite an existing secret-bearing `.env`; it appends only a missing non-secret `MCP_ENABLED=true` flag when safe.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/runs/72709978017 -> 6665329b5cd94e893496a78790f3f4564241e312
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1500#pullrequestreview-4162941045 -> 6665329b5cd94e893496a78790f3f4564241e312

Disposition: FIXED
Commit: 9f27df0134704db9af3a946df32f0531f33688ea
Evidence: `tests/test_setup_custom_mcp_coverage.py`
Reason: The newly added setup coverage tests now include explicit `-> None` return annotations, matching the repo test typing convention requested by CodeRabbit.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1500#discussion_r3131298939 -> 9f27df0134704db9af3a946df32f0531f33688ea
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1500#pullrequestreview-4163014536 -> 9f27df0134704db9af3a946df32f0531f33688ea

## Merge Readiness

- [ ] All required checks pass
  Evidence target: `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:179-213`
- [x] No unresolved review threads (re-check on current head before merge)
- [x] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
  Evidence target: `docs/orchestration/COORDINATOR_MERGE_READINESS_RULES.md:11-17`
- [x] Pre-commit green
  Evidence target: `RUNBOOK_AGENT.md:166-174`
- [ ] `make verify` green
  Evidence target: `AGENTS.md:5-16`
- [ ] Mandatory post-open `qa-engineer-agent -> bug-hunter` pass completed
  Evidence target: `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:98-103`

Notes: Merge-readiness remains blocked until the current-head required checks,
the post-open QA lane, and the repo hard gates are all re-verified on the latest
head.
