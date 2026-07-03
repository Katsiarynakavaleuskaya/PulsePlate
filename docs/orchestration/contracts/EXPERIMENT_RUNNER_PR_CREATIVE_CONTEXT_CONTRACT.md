# Experiment Runner PR Creative-Context Contract

<!-- markdownlint-disable MD013 -->

**Status:** v1 local artifact contract. No workflow, provider, product runtime,
branch, PR, comment, thread, fixed-mapping, or merge authority.

**Purpose:** Give eligible orchestration / Experiment Runner PR lanes active
creative-hypothesis authority without granting code mutation. The classic
Experiment Runner oracle remains the verifier. This layer builds sanitized
context, emits 3-5 bounded hypotheses, maps cross-domain analogies, proposes
coordinator-owned agent routing, and prepares a human approval packet for a
later PR-1 specification handoff.

PR-2 adds an active local intake lane: an operator-controlled local model/tool
may produce structured hypothesis JSON outside the repo, while the repo only
validates, normalizes, fingerprints, and routes that JSON. The repo does not
call a provider/model and does not retain raw prompts or raw model payloads.

The approved next handoff after a human `CreativeHypothesisApproval` is the
separate local bridge in
`scripts/orchestration/creative_hypothesis_spec_bridge.py`. That bridge may
build a validated `CreativeCodeCandidatePacket`, deterministic local metrics,
and existing PR-1 prepare artifacts only when the approval decision is
`approve_for_pr1_specification` with `next_step=create_pr1_specification`.
Approval remains specification handoff authority only; it is not patch,
repository-write, PR, agent-execution, provider, product-runtime, cache, graph,
or merge authority.

## Authority Boundary

Allowed:

- read sanitized changed-path and repo-reference inputs;
- emit local artifacts under
  `artifacts/orchestration/experiments/creative_context/`;
- build `CreativeProtocolContextMap`;
- generate exactly 3-5 hypotheses for eligible orchestration/creative surfaces;
- ingest operator-supplied local model JSON after strict schema validation;
- attach cross-domain analogies as implementation hypotheses, not product
  claims;
- route hypotheses to registered agents or record missing specialist
  capabilities with approved fallbacks;
- emit a coordinator dispatch handoff for critique/refine review only;
- prepare a `CreativeHypothesisApproval` reservation for human review.

Forbidden:

- candidate patch generation;
- shared worktree writes, branch writes, push, PR creation, PR body edits,
  review comments, thread resolution, fixed-mapping edits, merge, release, or
  readiness claims;
- workflow mutation or automatic workflow dispatch;
- provider calls, product runtime calls, semantic-cache use, secrets reads,
  GitHub App mutation, or Slack mutation;
- local HTTP model adapters, GitHub App `workflow_dispatch`, and Actions write
  permissions unless a later reviewed capability gate opens them;
- storing raw PR bodies, review bodies, patches, prompts, provider payloads,
  oracle stdout/stderr, Codex JSONL, secrets, tokens, or absolute local paths.

## Activation

Eligible by default:

- `scripts/orchestration/**`;
- `docs/orchestration/**`;
- `.agents/skills/**`;
- `tools/codex_skills/**`;
- `scripts/AGENTS.md`;
- `RUNBOOK_AGENT.md`;
- `docs/roadmap/BACKLOG_LEDGER.md`.

Label, marker, or manual activation may require hypotheses only when the
changed path is still a safe non-product, non-workflow, concrete surface.

Ineligible v1 surfaces:

- `.github/workflows/**` returns `workflow_deferred_followup`;
- `app/**`, `core/**`, `frontend/**`, `ios/**`, `providers/**`, and
  `alembic/**` return `product_runtime_surface`;
- generic docs-only changes return `docs_only_no_runtime_action`.

Workflow auto-run / PR attachment is intentionally deferred to a separate
reviewed PR.

## Artifacts

Schemas:

- `experiment_runner_pr_oracle_attachment.v1.schema.json`
- `creative_protocol_context_map.v1.schema.json`
- `creative_hypothesis_operator_model_intake.v1.schema.json`
- `creative_hypothesis_packet.v1.schema.json`
- `creative_hypothesis_agent_routing.v1.schema.json`
- `creative_hypothesis_coordinator_dispatch.v1.schema.json`
- `creative_hypothesis_agent_consumption_summary.v1.schema.json`
- `creative_hypothesis_approval.v1.schema.json`
- `creative_hypothesis_specification_bridge.v1.schema.json`
- `creative_hypothesis_spec_bridge_metrics.v1.schema.json`

Runtime contract:

- `scripts/orchestration/experiment_runner_pr_creative_context_contract.py`
- `scripts/orchestration/creative_hypothesis_spec_bridge_contract.py`

CLI:

```bash
python -m scripts.orchestration.experiment_runner_pr_creative_context collect-context
python -m scripts.orchestration.experiment_runner_pr_creative_context generate-hypotheses
python -m scripts.orchestration.experiment_runner_pr_creative_context ingest-model-hypotheses
python -m scripts.orchestration.experiment_runner_pr_creative_context route-agents
python -m scripts.orchestration.experiment_runner_pr_creative_context dispatch-coordinator
python -m scripts.orchestration.experiment_runner_pr_creative_context summarize
python -m scripts.orchestration.experiment_runner_pr_creative_context prepare
python -m scripts.orchestration.experiment_runner_pr_creative_context validate
python -m scripts.orchestration.creative_hypothesis_spec_bridge build-candidate
python -m scripts.orchestration.creative_hypothesis_spec_bridge prepare-specification
python -m scripts.orchestration.creative_hypothesis_spec_bridge build-and-prepare
python -m scripts.orchestration.creative_hypothesis_spec_bridge validate
```

`prepare` writes only these filenames:

- `context_map.json`
- `model_intake.json` when `--model-intake` is supplied;
- `hypothesis_packet.json`
- `agent_routing.json`
- `coordinator_dispatch.json`
- `oracle_attachment.json`
- `agent_consumption_summary.json`

`prepare --context-map <context_map.json> --model-intake <json>` uses the
supplied fingerprinted context map and intake instead of deterministic
templates, then writes the normalized intake as `model_intake.json` beside the
packet whose `source_model_intake_fingerprint` points at that normalized
artifact. Supplying the same `context_map.json` used by
`ingest-model-hypotheses` prevents timestamp or argument drift from
invalidating otherwise valid operator/model JSON.

`ingest-model-hypotheses --output <path>` writes the normalized packet to
`<path>` and, by default, writes the validated normalized intake as
`model_intake.json` beside it. Operators may override that sidecar path with
`--normalized-intake-output`; stdout-only mode does not create a sidecar unless
an explicit sidecar output is provided.

`creative_hypothesis_spec_bridge build-candidate` consumes an existing
`context_map.json`, `hypothesis_packet.json`, `coordinator_dispatch.json`, and
`approval.json`, then writes only:

- `creative_hypothesis_specification_bridge.json`;
- `creative_code_candidate_packet.json`;
- `bridge_metrics.json`.

`creative_hypothesis_spec_bridge build-and-prepare` additionally delegates to
the existing PR-1 `creative_code_spec_pipeline.prepare(...)` implementation and
writes only these prepare artifacts under `spec_prepare/`:

- `source_packet.json`;
- `variants.json`;
- `skeptic_reviews.json`;
- `context_pack.json`.

The bridge never calls `finalize`, patch builders, promotion tooling, role
dispatch, providers, product runtime, workflow dispatch, GitHub/Slack write
paths, or cache/graph truth systems.

## Operator Model Intake

`CreativeHypothesisOperatorModelIntake` is an advisory, unverified local input
artifact. It is not evidence-backed truth and not a patch request.

Required boundaries:

- `generation.mode=operator_supplied_model_json`;
- `repo_provider_calls=false`;
- `raw_model_payload_stored=false`;
- `semantic_cache_used=false`;
- `hypothesis_count` may be omitted and derived from `hypotheses`; if supplied,
  it must be 3, 4, or 5 and must match the array length;
- operator-supplied `intake_id` and `idempotency_key` are non-authoritative and
  are overwritten by repo-derived identity during normalization;
- external `hypothesis_id` is rejected; the repo normalizer assigns stable
  `hyp-001`, `hyp-002`, ... IDs;
- each hypothesis must include concrete target surfaces, tests/oracles, risk
  notes, cross-domain analogies, falsifier, negative controls, human approval,
  `eligible_for_pr1_specification=true`, and `eligible_for_pr2_patch=false`;
- authority is limited to `operator_supplied_hypotheses=true`; GitHub,
  workflow, provider, runtime, patch, branch, PR, thread, fixed-mapping,
  semantic-cache, OpenAPI, and client-runtime powers are forced false.

The normalizer rejects raw prompt/response fields, provider payloads,
chain-of-thought, patch or diff text, token-like values, absolute local paths,
product-runtime targets, workflow mutation, GitHub write intent, and
semantic-cache claims.

Normalized `CreativeHypothesisPacket` records:

- `hypothesis_generation_mode=operator_validated_intake_v1`;
- `source_model_intake_fingerprint=sha256:...`;
- `repo_provider_calls=false`;
- `raw_model_payload_stored=false`;
- `semantic_cache_used=false`.

## Hypothesis Requirements

Generated packets must satisfy all of the following:

- `hypothesis_count` is 3, 4, or 5 for eligible surfaces;
- every hypothesis has target surfaces, expected behavior, tests/oracles, risk
  notes, a falsifier, negative controls, at least one cross-domain analogy, and
  `requires_human_approval=true`;
- `eligible_for_pr1_specification=true`;
- `eligible_for_pr2_patch=false`;
- generated packets include at least one concrete code, test, contract, agent,
  or prompt/program target.

## Agent Routing

The coordinator owns routing. Agents may critique and refine hypotheses only.
They do not mutate code from this artifact.

Baseline routing:

- architecture -> `architecture-specialist`, `security-auditor`,
  `qa-engineer-agent`;
- security authority -> `security-auditor`, `bug-hunter`,
  `architecture-specialist`;
- testing/oracle -> `qa-engineer-agent`, `bug-hunter`, `logic-agent`;
- creative protocol -> `philosophy-agent`,
  `epistemology-discovery-agent`, `logic-agent`;
- scientific/statistics -> `data-scientist-agent` plus
  `experiment-design-stats-agent` when registered.

Missing specialist agents are recorded as `missing_agent_capabilities`; routing
falls back to `agent-coordinator` when the primary is not registered. Missing
capability entries must still use PulsePlate agent-slug shape; they are not
free-form rationale text.

`CreativeHypothesisCoordinatorDispatch` converts routing rows into
`TASK_PACKET_V1`-style local handoff rows with `task_mode=critique_refine_only`,
`mutation_authority=false`, `execute_agent_tasks=false`, and
`dispatch_to_coordinator=true`. It is a coordinator input, not an agent executor.

## Codex Security Single-Pass Guard

Creative-context artifacts carry:

```text
policy=single_pass_per_material_diff
rerun_allowed_reasons=[
  security_relevant_diff_changed,
  coordinator_evidence_backed_reroute,
  operator_explicit_request,
  scan_artifact_failed_or_incomplete
]
```

The post-open chain is:

```text
qa-engineer-agent -> bug-hunter -> security-auditor
-> Codex Security diff scan / finding discovery
-> pulseplate-pr-review
```

That chain runs once per material diff. Later comments go through fixed mapping
and targeted gates unless one of the rerun reasons is present.

## Human Approval

`CreativeHypothesisApproval` is a reservation, not a mutation grant. An
approval may authorize only `create_pr1_specification`. It must keep
`generate_patch=false`; PR-2 patch generation requires a later explicit gate and
approved specification evidence.

## Rollback

Rollback is removal of this contract doc, schemas, CLI/contract modules, tests,
and local ignored creative-context artifacts. Because v1 adds no workflows,
providers, product runtime behavior, GitHub/Slack settings, DB state, OpenAPI
changes, or branch/PR writes, rollback does not require external service or
data migration.
