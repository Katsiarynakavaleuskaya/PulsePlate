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

## Authority Boundary

Allowed:

- read sanitized changed-path and repo-reference inputs;
- emit local artifacts under
  `artifacts/orchestration/experiments/creative_context/`;
- build `CreativeProtocolContextMap`;
- generate exactly 3-5 hypotheses for eligible orchestration/creative surfaces;
- attach cross-domain analogies as implementation hypotheses, not product
  claims;
- route hypotheses to registered agents or record missing specialist
  capabilities with approved fallbacks;
- prepare a `CreativeHypothesisApproval` reservation for human review.

Forbidden:

- candidate patch generation;
- shared worktree writes, branch writes, push, PR creation, PR body edits,
  review comments, thread resolution, fixed-mapping edits, merge, release, or
  readiness claims;
- workflow mutation or automatic workflow dispatch;
- provider calls, product runtime calls, semantic-cache use, secrets reads,
  GitHub App mutation, or Slack mutation;
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
- `creative_hypothesis_packet.v1.schema.json`
- `creative_hypothesis_agent_routing.v1.schema.json`
- `creative_hypothesis_agent_consumption_summary.v1.schema.json`
- `creative_hypothesis_approval.v1.schema.json`

Runtime contract:

- `scripts/orchestration/experiment_runner_pr_creative_context_contract.py`

CLI:

```bash
python -m scripts.orchestration.experiment_runner_pr_creative_context collect-context
python -m scripts.orchestration.experiment_runner_pr_creative_context generate-hypotheses
python -m scripts.orchestration.experiment_runner_pr_creative_context route-agents
python -m scripts.orchestration.experiment_runner_pr_creative_context summarize
python -m scripts.orchestration.experiment_runner_pr_creative_context prepare
python -m scripts.orchestration.experiment_runner_pr_creative_context validate
```

`prepare` writes only these filenames:

- `context_map.json`
- `hypothesis_packet.json`
- `agent_routing.json`
- `oracle_attachment.json`
- `agent_consumption_summary.json`

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
falls back to `agent-coordinator` when the primary is not registered.

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
