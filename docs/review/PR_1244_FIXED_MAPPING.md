# PR 1244 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
Disposition: FIXED
Commit: 5fce2bb4514e67a8f5d6c7da600107f37ea51172
Evidence: `.github/workflows/ci.yml:321` adds an explicit Bandit HIGH-severity enforcement step, and `.github/workflows/ci.yml:344` through `.github/workflows/ci.yml:347` now hard-fail the canonical PR security lane when `bandit-report.json` contains HIGH findings.
Reason: PR-time backend/shared merge truth stays in `ci.yml`, but that lane now enforces the same HIGH-severity Bandit failure semantics the review requested without reintroducing `pull_request` triggers on the scheduled/manual audit workflow.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1244#discussion_r2994114804 -> 5fce2bb4514e67a8f5d6c7da600107f37ea51172

Disposition: NOT-A-BUG
Evidence: `.github/scripts/parse-safety-report.py:18` through `.github/scripts/parse-safety-report.py:19` define `safety-report.txt` as a generated summary artifact, `.github/scripts/parse-safety-report.py:74` writes that file, and `docs/orchestration/TIER1_CI_CD_PR_SERIES_RUNBOOK.md:68` through `docs/orchestration/TIER1_CI_CD_PR_SERIES_RUNBOOK.md:72` document that PR2 intentionally keeps `ci.yml` as the canonical PR lane while `security.yml` remains a scheduled/manual audit lane.
Reason: The inline artifact warning is a false positive because the parser step does generate `safety-report.txt`; the review-level duplication suggestion is acknowledged but does not describe a correctness bug in PR2 because the temporary `ci.yml`/`security.yml` overlap is the documented consolidation shape for this wave.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1244#discussion_r2994105623
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1244#pullrequestreview-4013216084

Disposition: FIXED
Commit: 8586f7b91c7ba4bdd07cad0b51cb7f08749de49d
Evidence: `.github/workflows/ci.yml:891` through `.github/workflows/ci.yml:903` remove repo-source carve-outs from the canonical `diff-cover` invocation, `docs/roadmap/BACKLOG_LEDGER.md:2045` through `docs/roadmap/BACKLOG_LEDGER.md:2055` keep the PR2 ledger item open until merge and replace deleted workflow links with a historical note, and `docs/review/PR_1244_FIXED_MAPPING.md:23` no longer marks bot-comment mapping complete before the final merge cycle.
Reason: CodeRabbit's current-head follow-up was addressed by restoring coverage enforcement for real source files, reverting premature backlog closure, replacing stale links to deleted workflows, and unchecking the artifact gate until the remaining current-head dispositions are recorded.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1244#discussion_r2994177517 -> 8586f7b91c7ba4bdd07cad0b51cb7f08749de49d
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1244#discussion_r2994177544 -> 8586f7b91c7ba4bdd07cad0b51cb7f08749de49d
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1244#discussion_r2994177547 -> 8586f7b91c7ba4bdd07cad0b51cb7f08749de49d
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1244#discussion_r2994177563 -> 8586f7b91c7ba4bdd07cad0b51cb7f08749de49d
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1244#pullrequestreview-4013295600 -> 8586f7b91c7ba4bdd07cad0b51cb7f08749de49d

## Merge Readiness
- [ ] All required checks pass
- [ ] No unresolved review threads (re-check on current head before merge)
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
- [ ] Pre-commit green
