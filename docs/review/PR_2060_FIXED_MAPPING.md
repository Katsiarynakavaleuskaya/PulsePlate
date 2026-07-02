# PR #2060 Fixed in Commit Mapping SoT

PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2060

Branch: `codex/experiment-runner-github-app-capability-gate`

## Summary

This PR adds a local/orchestration-only GitHub App private-pilot capability gate.
The gate validates a strict read-only capability report, embeds normalized
capability state into the creative-code private-pilot operator state, and blocks
candidate-plan preparation when a supplied report lacks Pull requests read or
Checks read. It does not mutate GitHub App settings, mint tokens, write PRs or
review threads, change product runtime, change workflows, or claim readiness.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed
- [x] Post-open `qa-engineer-agent` pass completed.
- [x] Post-open `bug-hunter` pass completed.
- [x] Post-open `security-auditor` pass completed.
- [x] Codex Security diff scan / finding discovery completed or explicitly
  dispositioned.
- [x] `pulseplate-pr-review` completed.
- [x] CodeRabbit usage-limit comment checked and dispositioned.
- [x] Sourcery high-level review comment checked and dispositioned.
- [ ] Current-head CI complete before readiness language.
- [ ] Strict merge-readiness checks run after the final review/check cycle.

## Fixed in Commit Mapping

Disposition: NOT-A-BUG
Evidence: Codex connector comment reports code-review usage limits only and does not contain a code, docs, schema, security, or governance actionable.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2060#issuecomment-4861939066

Disposition: NOT-A-BUG
Evidence: CodeRabbit comment reports temporary review-limit state only and does not contain a code, docs, schema, security, or governance actionable.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2060#issuecomment-4861939191

Disposition: FIXED
Commit: c6d3e97a8d20077db5e84af636c6c26bc846ce29
Evidence: `scripts/orchestration/github_app_private_pilot_capability.py` centralizes missing-permission/status derivation and includes mismatched field names in capability/authority diagnostics; regression coverage is in `tests/test_creative_code_private_pilot_loop.py`.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2060#pullrequestreview-4614334490 -> c6d3e97a8d20077db5e84af636c6c26bc846ce29

Disposition: NOT-A-BUG
Evidence: Sourcery issue comment is a generated review guide/summary and not the review-level actionable; the actionable review is mapped separately.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2060#issuecomment-4861939596

## Role-Agent Finding Dispositions

Disposition: FIXED
Source: post-open `qa-engineer-agent`
Evidence: This artifact fixes the missing canonical mapping artifact that made
`PR Body Phase2 gates` and `Merge readiness gate` fail on run `28563481298`.

Disposition: FIXED
Source: post-open `qa-engineer-agent`
Evidence: `validate_private_pilot_state()` normalizes legacy v1.0 states
without `github_app_capability` to `manual_only` / `not_checked`, verifies their
legacy fingerprint, and returns current-shape/current-identity state with
regression coverage in `tests/test_creative_code_private_pilot_loop.py`.

Disposition: FIXED
Source: post-open `qa-engineer-agent`
Evidence: `creative_code_private_pilot_state.v1.schema.json` now mirrors runtime
coupling for report-present metadata read, PR/check read booleans,
`missing_permissions`, read authority, and derived status; schema parity tests
assert the coupling markers.

Disposition: FIXED
Source: post-open `bug-hunter`
Evidence: Commit `3304494dc76ca664bd3fb8b0c00ed756f4e4cef2` makes legacy
defaulting operational after first read: the legacy payload is verified against
its original fingerprint, then returned with current identity so second
validation and `build_candidate_plan()` succeed.

Disposition: FIXED
Source: post-open `bug-hunter`
Evidence: Commit `3304494dc76ca664bd3fb8b0c00ed756f4e4cef2` tightens
`creative_code_private_pilot_state.v1.schema.json` authority coupling for
manual/not-checked, metadata-read, and workflow-dispatch states; schema parity
tests assert the read-authority markers.

Disposition: FIXED
Source: post-open `bug-hunter`
Evidence: This mapping artifact now records Sourcery's actual review URL
`https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2060#pullrequestreview-4614334490`
as the FIXED actionable and classifies the generated guide issue comment as
NOT-A-BUG.

Disposition: FIXED
Source: post-open `security-auditor`
Evidence: This artifact now marks the completed post-open `bug-hunter` pass in
the checklist, matching the recorded bug-hunter dispositions.

Disposition: NOT-A-BUG
Source: post-open `security-auditor`
Evidence: Security-auditor found no P0/P1/P2 security issues in pushed HEAD
`c70063ad4`; the only finding was the checklist consistency item fixed above.

Disposition: NOT-A-BUG
Source: Codex Security diff scan / finding discovery
Evidence: Codex Security scan `c9c2f570-46e7-4790-8195-41244d5a02bf`
completed with 0 reportable findings and 4/4 diff worklist rows closed. The
scan focused on secret/path diagnostic leaks, unsafe GitHub authority
expansion, write-permission bypasses, token minting/app mutation, and
schema/runtime drift with security impact.

Disposition: NOT-A-BUG
Source: `pulseplate-pr-review`
Evidence: The dry-run report produced one advisory `large-diff-risk` note. The
diff is intentionally a single capability-gate slice spanning schema, runtime
contract, operator collect input, identity policy, docs, and focused tests; the
split rationale is documented in the PR body and follow-up auto-attach runner
work is deferred. Local proof already includes focused pytest,
`check_experiment_runner_identity.py`, `make validate-changed`, and
`pre-commit run --all-files`.

## Experiment Runner Evidence

- Artifact: `artifacts/orchestration/experiments/results/github_app_capability_gate_oracle_result_network1.json`
- Experiment ID: `exp-3afd8d437b8e`
- Mode: `oracle_only_governance_reviewer`
- Status: accepted
- Source diff applied: true
- Oracles: 4/4 passed

## Lane Start Provenance

- Packet: `artifacts/orchestration/task_packets/9369e1e12d9e.json`
- Starter: `scripts/orchestration/start_pr_lane.sh`

## Merge Readiness

Not claimed. This artifact records post-open dispositions and local evidence
only; current-head CI must be rechecked after this mapping-only update before
any readiness language.
