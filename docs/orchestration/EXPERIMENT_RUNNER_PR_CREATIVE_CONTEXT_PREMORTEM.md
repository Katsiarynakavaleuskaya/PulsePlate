# Experiment Runner PR Creative-Context Premortem

Status: pre-open premortem closure for the local Experiment Runner PR
creative-context attachment. This is governance evidence only; it is not
fixed-mapping evidence, review-thread disposition proof, merge readiness, or
release evidence.

## Frame

It is after this PR opened and the lane failed. The failure did not come from
product runtime behavior, because this PR intentionally adds no product runtime
surface and no workflow. The failure came from a local hypothesis artifact being
misread as write authority, unsafe PR/review payloads being persisted, role
routing being treated as complete when required specialists are unavailable, or
the post-open Codex Security chain rerunning after every comment instead of
once per material diff.

Success means eligible orchestration / Experiment Runner PR surfaces can emit a
sanitized context map, 3-5 bounded hypotheses, cross-domain analogies,
coordinator-owned routing proposals, oracle attachment summaries, and a human
approval reservation while keeping candidate patch generation, GitHub writes,
workflow mutation, provider calls, and product runtime calls closed.

## Closure Matrix

| ID | Scenario | Premortem decision | Closure |
|---|---|---|---|
| PM-ERCC-001 | A PR workflow auto-runs creative context with unsafe permissions or `pull_request_target`. | block until fixed | [x] FIXED |
| PM-ERCC-002 | Raw PR/review/prompt/provider/oracle output leaks into local artifacts. | block until fixed | [x] FIXED |
| PM-ERCC-003 | Hypothesis output is treated as patch, branch, PR, fixed-mapping, or merge authority. | block until fixed | [x] FIXED |
| PM-ERCC-004 | Eligible orchestration PRs produce decorative docs-only hypotheses with no concrete repo surface. | block until fixed | [x] FIXED |
| PM-ERCC-005 | Missing specialist agents disappear from routing and create a false sense of review coverage. | block until fixed | [x] FIXED |
| PM-ERCC-006 | Codex Security / review chain reruns after every comment and creates an unbounded review loop. | block until fixed | [x] FIXED |
| PM-ERCC-007 | CLI output escapes the gitignored creative-context artifact root. | block until fixed | [x] FIXED |
| PM-ERCC-008 | Product runtime, app, iOS, provider, or migration PRs get creative context by label/marker accident. | block until fixed | [x] FIXED |

## Scenarios

### PM-ERCC-001 Workflow Auto-Run Opens Privilege Risk

Failure story: this PR adds a GitHub Actions workflow that runs on
`pull_request_target`, checks out untrusted PR content, or grants write
permissions. A fork or compromised branch can then feed event text or repo
content into an agent-like artifact path and create a workflow-level injection
or write-authority risk.

Underlying assumption: creative-context generation is "read-only enough" to
ship directly as a workflow. That is false for v1 because workflow trigger,
permission, event-context, and artifact-retention controls need their own
review.

Containment action: keep v1 local-only and defer auto-workflow attachment to a
separate reviewed PR.

Closure:

- [x] FIXED. No `.github/workflows/**` files are changed in this diff.
- [x] FIXED. Workflow paths classify as `workflow_deferred_followup`:
  `scripts/orchestration/experiment_runner_pr_creative_context_contract.py`.
- [x] TESTED. Workflow surfaces emit `no_creative_action`:
  `tests/test_experiment_runner_pr_creative_context.py`.
- [x] DOCUMENTED. The follow-up automation is tracked in
  `docs/roadmap/BACKLOG_LEDGER.md`.

### PM-ERCC-002 Unsafe Payload Leakage

Failure story: a copied PR event, review comment, Codex transcript, provider
payload, or oracle stdout lands in `context_map.json` or
`hypothesis_packet.json`. Later role agents trust the artifact as sanitized and
replay private text, local paths, secrets, or prompt material.

Underlying assumption: local artifacts are harmless because they are gitignored.
That is false because local artifacts can be consumed by future agents and
mirrored into PR bodies or review summaries.

Containment action: reject unsafe keys and text before validation or write.

Closure:

- [x] FIXED. `reject_unsafe_creative_context_value(...)` rejects raw-body,
  prompt, patch, provider, oracle-output, local-path, secret, token, and
  readiness-claim patterns.
- [x] FIXED. The CLI writes only after running the sanitizer.
- [x] TESTED. Unsafe payload variants are rejected in
  `tests/test_experiment_runner_pr_creative_context.py`.

### PM-ERCC-003 Advisory Hypotheses Become Hidden Mutation Authority

Failure story: a future agent reads a hypothesis as permission to generate a
candidate patch, write a branch, open a PR, edit fixed mapping, resolve review
threads, or claim merge readiness. The creative layer silently bypasses PR-1 /
PR-2 / PR-3 approvals.

Underlying assumption: a typed hypothesis packet implies execution authority.
For this PR it does not; it is only context, hypotheses, routing, and human
approval reservation.

Containment action: pin the authority map and fail closed on escalation.

Closure:

- [x] FIXED. `default_creative_context_authority()` keeps patch, branch, push,
  PR, comment, thread, fixed-mapping, workflow, provider, runtime, merge, and
  readiness flags false.
- [x] FIXED. `CreativeHypothesisApproval` keeps `generate_patch=false` and may
  only reserve `create_pr1_specification`.
- [x] TESTED. Authority escalation is rejected in
  `tests/test_experiment_runner_pr_creative_context.py`.

### PM-ERCC-004 Decorative Docs-Only Hypotheses

Failure story: an orchestration PR receives three hypotheses that only say to
update documentation. The artifact looks complete but creates no concrete
test/code/contract guard and the next agent performs a docs closeout instead of
finding how the actual diff could break production governance.

Underlying assumption: any hypothesis packet is useful. That is false; eligible
orchestration/code surfaces need at least one concrete target.

Containment action: require target surfaces, tests/oracles, falsifiers, risk
notes, cross-domain analogies, and at least one concrete code, test, contract,
agent, or prompt/program target.

Closure:

- [x] FIXED. Generated hypotheses include target surfaces and executable guard
  refs.
- [x] FIXED. The validator rejects generated packets whose targets are only
  generic docs.
- [x] TESTED. Docs-only generated packets are rejected in
  `tests/test_experiment_runner_pr_creative_context.py`.

### PM-ERCC-005 Missing Specialist Agents Are Hidden

Failure story: a scientific/statistical or philosophical hypothesis needs a
specialist agent that is not registered, but the routing artifact silently
assigns a generic reviewer and omits the missing capability. The coordinator
later believes the hypothesis had complete specialist review.

Underlying assumption: registered fallback is equivalent to specialist
coverage. It is not; fallback is a routing safety net, not coverage.

Containment action: record `missing_agent_capabilities` and require coordinator
decision before handoff.

Closure:

- [x] FIXED. Routing records missing specialist agents and falls back to
  `agent-coordinator` only for unregistered primary agents.
- [x] TESTED. Missing `experiment-design-stats-agent` capability is recorded in
  `tests/test_experiment_runner_pr_creative_context.py`.

### PM-ERCC-006 Security Review Loop Reruns Without Material Diff

Failure story: after the PR opens, each comment or mapping tweak triggers the
entire `qa-engineer-agent -> bug-hunter -> security-auditor -> Codex Security
-> pulseplate-pr-review` chain again. The PR spends its review budget looping
over the same diff and may train agents to ignore the single authoritative
security pass.

Underlying assumption: more security scans always improve safety. That is false
when the diff is unchanged and the new activity should be handled through fixed
mapping and targeted gates.

Containment action: make `single_pass_per_material_diff` visible in both
artifacts and rendered start prompts.

Closure:

- [x] FIXED. Creative context embeds
  `policy=single_pass_per_material_diff` plus bounded rerun reasons.
- [x] FIXED. `task_bootstrap.py` emits single-pass post-open lifecycle metadata.
- [x] FIXED. `render_codex_start_prompt.py` tells agents to use fixed mapping
  and targeted gates after the single pass.
- [x] TESTED. Governance regressions are covered in
  `tests/test_task_bootstrap.py` and `tests/test_render_codex_start_prompt.py`.

### PM-ERCC-007 Artifact Output Escapes Local Root

Failure story: an operator passes an absolute output path or a symlinked output
directory. The CLI writes sanitized-looking JSON outside
`artifacts/orchestration/experiments/creative_context/`, possibly modifying a
tracked file or private local file.

Underlying assumption: JSON output is safe if the payload is safe. That misses
filesystem containment risk.

Containment action: constrain output directories and filenames under the
creative-context artifact root, reject symlink traversal, and use atomic writes.

Closure:

- [x] FIXED. CLI output is restricted to approved artifact filenames under the
  creative-context artifact root.
- [x] FIXED. Symlink traversal and outside paths fail closed.
- [x] TESTED. CLI output containment is covered in
  `tests/test_experiment_runner_pr_creative_context.py`.

### PM-ERCC-008 Product Runtime Surfaces Accidentally Activate

Failure story: a product-runtime PR gets a label or marker intended for
orchestration work. The creative-context layer emits hypotheses for `app/**`,
`core/**`, provider, iOS, migration, or frontend surfaces and appears to route
agents for product changes without the product/runtime governance required for
those surfaces.

Underlying assumption: labels and markers can override path risk. That is false
for product runtime and workflow surfaces in v1.

Containment action: classify product runtime and workflow paths before label,
marker, or manual activation.

Closure:

- [x] FIXED. Product runtime prefixes return `product_runtime_surface`.
- [x] FIXED. Workflow prefixes return `workflow_deferred_followup`.
- [x] TESTED. Product-runtime and workflow paths emit `no_creative_action` in
  `tests/test_experiment_runner_pr_creative_context.py`.

## Closeout

All blocking premortem scenarios are closed in this PR as code, contract,
schema, docs, or deterministic tests. This premortem does not make the PR
merge-ready; merge readiness still requires the repo narrow local bundle,
Experiment Runner oracle-only evidence, post-open role/security review, current
head CI truth, review-thread disposition, and strict merge-readiness checks.
