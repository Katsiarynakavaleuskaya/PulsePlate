# CreativeCodePrivatePilotLoopOperator Contract

Status: local private-pilot lifecycle operator. No product runtime impact.

The operator reads sanitized PR/check/review metadata and existing PR-4 / PR-5
/ PR-6 local creative-code artifacts, then emits local lifecycle artifacts:

```text
CreativeCodePrivatePilotState
-> CreativeCodePrivatePilotCandidatePlan
```

It is an operator decision layer only. It must not generate candidates, execute
PR-1 / PR-2 / PR-3 commands, write branches, push, open PRs, resolve review
threads, edit fixed mapping, call providers, call product runtime, change
Slack/GitHub App settings, modify workflows, or make readiness claims.

## Artifacts

Strict schemas:

- `creative_code_private_pilot_state.v1.schema.json`
- `creative_code_private_pilot_candidate_plan.v1.schema.json`

Validator and CLI:

```bash
python -m scripts.orchestration.creative_code_private_pilot_loop_contract
python -m scripts.orchestration.creative_code_private_pilot_loop_operator --help
python -m scripts.orchestration.creative_code_private_pilot_loop_operator collect --pr-number <N> --output-dir artifacts/orchestration/creative_code/private_pilot/<N>
python -m scripts.orchestration.creative_code_private_pilot_loop_operator status --pilot-state artifacts/orchestration/creative_code/private_pilot/<N>/pilot_state.json
python -m scripts.orchestration.creative_code_private_pilot_loop_operator decide-next --pilot-state artifacts/orchestration/creative_code/private_pilot/<N>/pilot_state.json
python -m scripts.orchestration.creative_code_private_pilot_loop_operator prepare-next-candidate --pilot-state artifacts/orchestration/creative_code/private_pilot/<N>/pilot_state.json
```

Local outputs stay under:

```text
artifacts/orchestration/creative_code/private_pilot/<pr-number>/
```

That directory is local-only and gitignored. It must never be committed.

## Inputs

Allowed inputs are normalized metadata and already-sanitized local artifacts:

- PR metadata needed to identify repository, PR number, base ref, and head SHA.
- Current-head check summaries where every check/run is compared to the PR head
  SHA. Superseded, cancelled, or wrong-head runs remain diagnostic only.
- Review-source status from `scripts/orchestration/pr_review_context.py`.
- Fixed-mapping presence and entry counts, not raw mapping prose.
- PR-4 telemetry refs under `artifacts/orchestration/creative_code/telemetry/`.
- PR-5 review-disposition refs under
  `artifacts/orchestration/creative_code/review_disposition/`.
- PR-6 run-plan refs under
  `artifacts/orchestration/creative_code/applied_candidates/`.

The operator must not store raw PR bodies, review bodies, patches, prompts,
provider payloads, oracle stdout/stderr, token values, local absolute paths, raw
images, or user/runtime data.

## State

`CreativeCodePrivatePilotState` records:

- source PR repository, number, URL, state, draft flag, base ref/SHA, and head SHA;
- current-head check status, current check summaries, stale diagnostic counts,
  and required-check availability;
- review capacity friction and sanitized review-source status;
- actionable, security, governance, and fixed-mapping blocker counts;
- governance refs for fixed mapping and PR-4 / PR-5 / PR-6 artifacts;
- optional external hotfix dependency status;
- computed decision:
  `wait_for_hotfix_main | wait_for_review | wait_for_ci | fix_current_pr |
  prepare_next_candidate_plan | hold_for_governance | hold_for_security`;
- explicit authority with only `read_github_metadata`,
  `read_sanitized_artifacts`, `emit_pilot_state`, and `emit_candidate_plan`
  set to true;
- `sanitized=true`.

## Candidate Plan

`CreativeCodePrivatePilotCandidatePlan` is checklist-only. It may be emitted
only when the state decision is `prepare_next_candidate_plan`.

The target surface is exactly:

```text
docs/prompts/cv/program.md
```

The plan may name human gates and future manual use of existing PR-1 / PR-2 /
PR-3 / PR-4 tools. It must keep every checklist item at
`checklist_only=true` and `executes_in_operator=false`.

## Boundary

The private-pilot operator is not a replacement for normal PulsePlate PR
governance, current-head CI, fixed-mapping disposition, role-agent passes,
Codex Security review, or human review. It emits local evidence and next-action
guidance only.

Rollback removes the operator CLI, contract module, schemas, tests, docs, and
ignored local private-pilot artifacts. Because it adds no runtime behavior,
provider integration, workflow mutation, DB migration, OpenAPI/client change, or
external app setting, rollback needs no release or data coordination.
