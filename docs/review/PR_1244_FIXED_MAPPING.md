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
Evidence: `.github/workflows/ci.yml:396` invokes `.github/scripts/parse-safety-report.py` before artifact upload, `.github/scripts/parse-safety-report.py:19` defines `safety-report.txt` as the summary artifact path, and `.github/scripts/parse-safety-report.py:74` writes that file before the upload step at `.github/workflows/ci.yml:413` through `.github/workflows/ci.yml:418`.
Reason: The inline artifact warning is a false positive because the canonical PR lane still generates `safety-report.txt` via the parser step before upload; the review-level duplication suggestion is acknowledged but does not describe a correctness bug in PR2 because the temporary `ci.yml`/`security.yml` overlap is the documented consolidation shape for this wave.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1244#discussion_r2994105623
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1244#pullrequestreview-4013216084

Disposition: FIXED
Commit: 8586f7b91c7ba4bdd07cad0b51cb7f08749de49d
Evidence: `.github/workflows/ci.yml:891` through `.github/workflows/ci.yml:903` remove repo-source carve-outs from the canonical `diff-cover` invocation, `docs/roadmap/BACKLOG_LEDGER.md:2045` through `docs/roadmap/BACKLOG_LEDGER.md:2055` keep the PR2 ledger item open until merge and replace deleted workflow links with a historical note, and `docs/review/PR_1244_FIXED_MAPPING.md:47` keeps the merge-readiness bot-mapping gate unchecked until the final cycle.
Reason: CodeRabbit's current-head follow-up was addressed by restoring coverage enforcement for real source files, reverting premature backlog closure, replacing stale links to deleted workflows, and keeping the artifact gate unchecked until the remaining current-head dispositions are recorded.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1244#discussion_r2994177517 -> 8586f7b91c7ba4bdd07cad0b51cb7f08749de49d
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1244#discussion_r2994177544 -> 8586f7b91c7ba4bdd07cad0b51cb7f08749de49d
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1244#discussion_r2994177547 -> 8586f7b91c7ba4bdd07cad0b51cb7f08749de49d
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1244#discussion_r2994177563 -> 8586f7b91c7ba4bdd07cad0b51cb7f08749de49d
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1244#pullrequestreview-4013295600 -> 8586f7b91c7ba4bdd07cad0b51cb7f08749de49d

Disposition: FIXED
Commit: 146722b8f86ecc503bed0971c7864a37448d2717
Evidence: `docs/review/PR_1244_FIXED_MAPPING.md:48` now keeps `Pre-commit green` unchecked so the merge-readiness checklist stays in final-cycle-only mode until the actual merge pass.
Reason: The final current-head CodeRabbit follow-up correctly noted that even a locally green pre-commit run should not flip a merge-readiness checkbox before the final merge cycle.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1244#discussion_r2994323898 -> 146722b8f86ecc503bed0971c7864a37448d2717
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1244#pullrequestreview-4013464994 -> 146722b8f86ecc503bed0971c7864a37448d2717

Disposition: FIXED
Commit: ab8ed030f48b7f6c6ea53d9ba0c491f81908e51a
Evidence: `docs/review/PR_1244_FIXED_MAPPING.md:15` now points the Sourcery evidence to the actual parser invocation and write path, `docs/review/PR_1244_FIXED_MAPPING.md:22` now cites the unchecked bot-mapping gate at `docs/review/PR_1244_FIXED_MAPPING.md:47`, and `docs/review/PR_1244_FIXED_MAPPING.md:32` now cites the unchecked pre-commit gate at `docs/review/PR_1244_FIXED_MAPPING.md:48`.
Reason: The latest CodeRabbit note correctly flagged that the artifact still had stale `file:line` proof anchors, so the evidence pointers were updated to the actual unchecked merge-readiness gates while also tightening the Sourcery false-positive evidence to the live workflow path.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1244#discussion_r2995074782 -> ab8ed030f48b7f6c6ea53d9ba0c491f81908e51a
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1244#pullrequestreview-4014369145 -> ab8ed030f48b7f6c6ea53d9ba0c491f81908e51a

## Merge Readiness
- [ ] All required checks pass
- [ ] No unresolved review threads (re-check on current head before merge)
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
- [ ] Pre-commit green
