# PR #2058 Fixed in Commit Mapping SoT

PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2058

Branch: `codex/creative-code-private-pilot-loop-operator`

## Summary

This PR adds the local Creative-Code private-pilot lifecycle operator. The
operator collects sanitized PR/check/review metadata, emits a normalized pilot
state, decides the next bounded action, and can prepare a checklist-only
candidate plan. It does not generate candidate patches, push branches, open PRs,
edit fixed mapping, resolve review threads, call providers, touch product
runtime, or claim merge readiness.

## Scope

- Add private-pilot state and candidate-plan contracts plus JSON schemas.
- Add a local CLI with `status`, `collect`, `decide-next`, and
  `prepare-next-candidate`.
- Add focused tests for current-head filtering, stale run handling, authority
  boundaries, sanitized artifact refs, and unsafe payload rejection.
- Document the local artifact path and read/artifact-only authority boundary.

## Out Of Scope

No nosec TTL cleanup, candidate generation, GitHub write automation, provider
execution, product runtime calls, fixed-mapping mutation, or review-thread
resolution is included.

## Lane Start Provenance

Packet: `artifacts/orchestration/task_packets/c2c25a90a433.json`

Starter: `scripts/orchestration/start_pr_lane.sh`

## Experiment Runner Evidence

Artifact:
`artifacts/orchestration/experiments/results/exp-private-pilot-loop-operator-oracle-result.json`

- Mode: `oracle_only_governance_reviewer`
- Status: `accepted`
- Experiment ID: `exp-2f724f27fb17`
- Shared tree untouched: `true`
- Mutated paths: `[]`
- Contribution kind: `commit_decision`
- Co-author required: `true`
- Commit trailer present in `301b3b686`.

Zero-network local attempt:
`artifacts/orchestration/experiments/results/exp-ebb380800011.json` recorded
`status=rejected`, `failure_class=infra_flake`, because the macOS local
network-disabled sandbox lacked `unshare`.

## Discussion Thread Pass

- [x] Initial fixed-mapping artifact created after PR open.
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed
- [x] Post-open `qa-engineer-agent` pass completed.
- [x] Post-open `bug-hunter` pass completed.
- [x] Post-open `security-auditor` pass completed.
- [x] Codex Security diff scan / finding discovery completed or explicitly
  dispositioned.
- [x] `pulseplate-pr-review` completed.
- [x] CodeRabbit, Sourcery, and Cubic actionables checked and dispositioned.
- [ ] Review threads checked, dispositioned, and resolved if any appear.
- [ ] Current-head CI complete before readiness language.
- [ ] Strict merge-readiness checks run after the final review/check cycle.

## Fixed in Commit Mapping

Disposition: FIXED
Commit: 8e4489f4c73ddb9d509aece5dad6e4040de8b40e
Evidence: `scripts/orchestration/creative_code_private_pilot_loop_contract.py` now treats unavailable required-check metadata as `overall=unknown`, and `tests/test_creative_code_private_pilot_loop.py` covers visible green checks with missing required metadata returning `wait_for_ci`.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2058#discussion_r3506022279 -> 8e4489f4c73ddb9d509aece5dad6e4040de8b40e

Disposition: FIXED
Commit: 8e4489f4c73ddb9d509aece5dad6e4040de8b40e
Evidence: `scripts/orchestration/creative_code_private_pilot_loop_operator.py` now passes the base branch name to `collect_review_context`, with regression coverage in `tests/test_creative_code_private_pilot_loop.py`.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2058#discussion_r3505988511 -> 8e4489f4c73ddb9d509aece5dad6e4040de8b40e

Disposition: FIXED
Commit: 8e4489f4c73ddb9d509aece5dad6e4040de8b40e
Evidence: `_typed_artifact_refs` now scans all matching PR-5 disposition packet files before blocker counting; the regression places the actionable packet after 25 non-disposition sidecars.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2058#discussion_r3506022287 -> 8e4489f4c73ddb9d509aece5dad6e4040de8b40e

Disposition: FIXED
Commit: 8e4489f4c73ddb9d509aece5dad6e4040de8b40e
Evidence: `_blocker_counts_from_pr5_refs` now counts `simple_fix` disposition records as actionable blockers, with focused regression coverage.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2058#discussion_r3506022292 -> 8e4489f4c73ddb9d509aece5dad6e4040de8b40e

Disposition: FIXED
Commit: 8e4489f4c73ddb9d509aece5dad6e4040de8b40e
Evidence: `_fixed_mapping_ref` now treats degraded fixed-mapping evidence as not present/usable, causing the existing governance hold path to apply.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2058#discussion_r3506022298 -> 8e4489f4c73ddb9d509aece5dad6e4040de8b40e

Disposition: FIXED
Commit: 8e4489f4c73ddb9d509aece5dad6e4040de8b40e
Evidence: current-head check normalization now deduplicates by check name and workflow, preserving failing required rows when an optional check shares a name.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2058#discussion_r3506022307 -> 8e4489f4c73ddb9d509aece5dad6e4040de8b40e

Disposition: FIXED
Commit: b4901f158704192f97a695fa443a3404e637647c
Evidence: required check metadata now preserves source identity using `status_context:<context>` and `app_id:<id>:<context>` descriptors; duplicate name-only required checks now add a blocking identity-conflict diagnostic, with focused regression coverage.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2058#discussion_r3506221759 -> b4901f158704192f97a695fa443a3404e637647c

Disposition: FIXED
Commit: b4901f158704192f97a695fa443a3404e637647c
Evidence: `collect_private_pilot_state()` now passes the PR base SHA into `collect_review_context()` for fixed-mapping diff checks while preserving the branch name for branch-protection metadata, with focused regression coverage.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2058#discussion_r3506221767 -> b4901f158704192f97a695fa443a3404e637647c

Disposition: FIXED
Commit: b4901f158704192f97a695fa443a3404e637647c
Evidence: `source_pr.base_ref` now uses a git-ref-safe validator and the state schema now points `base_ref` to `git_ref`, allowing safe refs such as `release/1.0` while still rejecting traversal, local paths, and unsafe ref syntax.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2058#discussion_r3506221771 -> b4901f158704192f97a695fa443a3404e637647c

Disposition: FIXED
Commit: b4901f158704192f97a695fa443a3404e637647c
Evidence: `_fixed_mapping_ref()` now marks fixed-mapping evidence present only when the artifact exists, is not degraded, and has either mapping entries or explicit no-actionable proof; focused tests cover stub mapping artifacts holding governance.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2058#discussion_r3506221781 -> b4901f158704192f97a695fa443a3404e637647c

## Post-Open Review Evidence

Codex Security diff scan `8269429e-360d-484e-bbfa-8c76fa73cd1f` completed
for the current diff scope with 2/2 discovery rows closed and 0 reportable
findings.

`pulseplate-pr-review` completed from the local gitignored review-context
artifact. It emitted one advisory large-diff note.

Disposition: NOT-A-BUG
Evidence: The 3,936 changed-line count is explained by one bounded operator
surface plus its contract, JSON schemas, documentation, and focused regression
tests. Focused tests, regression bundle, `make validate-changed`, and
`pre-commit run --all-files` are the validation path for this intentionally
coupled PR surface.
Reason: Splitting the schema/contract/operator/tests would weaken review of
the authority boundary that this PR is specifically adding.

CodeRabbit reported review-capacity friction before later status completion;
the current CodeRabbit status is pass/no code actionables. Sourcery's only
inline actionable was fixed and mapped above; its enum/schema dedupe and
artifact-fingerprint-cache notes are advisory tradeoffs for this first local
operator. Cubic was skipped/advisory and did not provide actionables.

## Merge Readiness

- [ ] Local narrow validation bundle completed on the final pushed head.
- [ ] Current-head CI complete with required checks passing.
- [ ] CodeRabbit, Sourcery, and Cubic have no unresolved actionables.
- [ ] Review threads checked and dispositioned.
- [ ] Merge-readiness gate rerun after the final review/check cycle.
