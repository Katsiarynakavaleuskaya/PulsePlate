# Premortem: Mandatory-Orchestrated Slack Bridge Module Split

## Frame

It is 6 months from now. The Experiment Runner Slack bridge split landed, but a later operator event leaked raw Slack context or bypassed a dry-run/approval gate because the facade no longer exercised the same internals that the old tests patched. We are looking backward to understand why.

## Scope

- PR lane: `codex/slack-bridge-module-boundaries`
- Task packet: `artifacts/orchestration/task_packets/49d34bea88dc.json` (local-only, not committed)
- Entry point preserved: `python3 -m scripts.orchestration.experiment_slack_socket_bridge`
- In scope: module boundaries for config/runtime validation, parsing/rendering, audit/idempotency/rate limiting, dispatch/live approval, optional Slack transport, facade compatibility, backlog hygiene entries
- Out of scope: root-wide file moves, semantic-cache runtime enablement, new Slack commands, DB/OpenAPI changes, product-facing Slack UX

## Mandatory Role Execution Evidence

Bootstrap evidence:

- `python3 scripts/orchestration/check_preflight.py` - PASS
- `python3 scripts/orchestration/check_agent_consistency.py` - PASS
- `python3 scripts/orchestration/task_bootstrap.py ... --pr-phase pre_open` - PASS, packet `49d34bea88dc`
- `python3 scripts/orchestration/qoder_dispatch_bridge.py --packet artifacts/orchestration/task_packets/49d34bea88dc.json --pretty` - emitted `role_agent_dispatch_required=true` equivalent context and `packet_creation_executes_roles=false`

Pre-open role passes were launched as mandatory subagent work, not treated as advisory notes:

| Order | Role | Agent id | Result | Disposition |
|---:|---|---|---|---|
| 1 | `agent-coordinator` | `019e7ae6-733c-71e1-93d3-f25469e0ffdf` | PASS | Scope, route, risks, validation plan, and DoD confirmed. |
| 2 | `architecture-specialist` | `019e7ae8-ba25-77d2-aacd-4a73492bb787` | PASS | Module-boundary plan accepted with facade compatibility as P1 risk. |
| 3 | `cursor-specialist-agent` | `019e7aeb-d5c2-7c12-a5d8-690467bdda8a` | BLOCK -> FIXED | Found generated manifest order drift; resolved by executing stricter operator-required order and recording durable evidence here. |
| 4 | `security-auditor` | `019e7aed-cbb6-7022-80b5-ebfe61eb24ed` | PASS | Security boundaries accepted if hash-only audit, lazy Slack imports, and execute gates remain unchanged. |
| 5 | `qa-engineer-agent` | `019e7af3-71a7-72c0-8e5b-1262f75b7e68` | PASS | Acceptance and regression matrix approved. |
| 6 | `bug-hunter` | `019e7af7-6218-7791-a0ba-c1f648a47772` | PASS | False-green risks identified; implementation cleared to start. |

The generated dispatch manifest listed `qa-engineer-agent -> bug-hunter -> security-auditor` after `cursor-specialist-agent`, but the operator-required lane order for this PR is `security-auditor -> qa-engineer-agent -> bug-hunter`. This artifact records the explicit coordinator/operator disposition: follow the stricter operator-required order for this lane. No assigned/requested role was skipped.

## Failure Modes And Disposition

### 1. Facade monkeypatch compatibility silently breaks

- **Failure story:** Tests continue importing `experiment_slack_socket_bridge`, but extracted modules own the real behavior. Existing tests monkeypatch facade symbols such as `REPO_ROOT`, `AUDIT_ARTIFACT_DIR`, `_load_slack_bolt`, `_send_slack_api_request`, `_claim_rate_limit`, `_remove_stale_rate_limit_claim`, and `_read_latest_snapshot_line`; after the split, those monkeypatches no longer affect runtime paths. The tests pass for isolated helpers while live behavior uses unpatched module globals.
- **Underlying assumption:** Moving a function into a module is behavior-neutral even when tests patch facade-level private helpers.
- **Early warning signs:** `process_payload()` lives outside the facade without dependency injection; `render_mvp_evidence_summary()` calls the snapshot reader directly from the rendering module.
- **Containment:** Keep `experiment_slack_socket_bridge.py` as the compatibility facade and pass facade-level dependencies into modules through wrappers.
- **Disposition:** FIXED
- **Evidence:** `scripts/orchestration/experiment_slack_socket_bridge.py` keeps facade wrappers for root/audit paths, snapshot reader, Slack transport, GitHub dispatch, and rate-limit removal. Focused bridge tests passed locally.

### 2. Optional Slack runtime becomes an import-time dependency

- **Failure story:** A config/rendering module imports `slack_bolt` at top level. `--help`, `--validate-runtime`, and dry-run CI paths fail on machines without the optional Slack SDK, blocking ordinary PR validation.
- **Underlying assumption:** Optional transport code can be imported by shared modules without affecting dry-run entrypoints.
- **Early warning signs:** `slack_bolt` appears outside `_load_slack_bolt()` or the optional transport module.
- **Containment:** Keep Slack SDK loading behind `_load_slack_bolt()` and a transport-only module.
- **Disposition:** FIXED
- **Evidence:** `scripts/orchestration/experiment_slack_bridge_transport.py` keeps Slack Bolt import inside `_load_slack_bolt()`. `python3 -m scripts.orchestration.experiment_slack_socket_bridge --help` and `--validate-runtime` passed without Slack SDK loading.

### 3. Hash-only audit or execute gates drift during extraction

- **Failure story:** Audit payload construction moves away from dispatch orchestration and starts persisting raw branch refs, hypotheses, channel IDs, or provider errors. Execute mode then dispatches without the reviewed sentinel, team allowlist, GitHub auth, fixed workflow allowlist, or live approval digest match.
- **Underlying assumption:** Security behavior is incidental to the old monolith instead of being a stable contract.
- **Early warning signs:** New audit schema fields contain non-hashed Slack or GitHub values; `_github_dispatch_inputs()` becomes callable without `_require_execute_config()`.
- **Containment:** Keep audit/idempotency/rate-limit and dispatch/live-approval logic in separate bounded modules with facade wrappers and focused regression coverage.
- **Disposition:** FIXED
- **Evidence:** `scripts/orchestration/experiment_slack_bridge_audit.py` preserves hash-only payload construction; `scripts/orchestration/experiment_slack_bridge_dispatch.py` preserves execute-mode and approval gates. Focused Slack bridge tests passed locally.

### 4. Role-agent execution is mistaken for bootstrap metadata

- **Failure story:** The PR body says agents were assigned because the task packet includes role names, but no role pass actually ran. A later regression ships because security/QA/bug-hunter feedback was never executed.
- **Underlying assumption:** `task_bootstrap.py` packet creation is equivalent to role execution.
- **Early warning signs:** PR evidence cites only `task_bootstrap.py` and omits agent ids/results.
- **Containment:** Run every requested role in order, record subagent ids/results, and mirror evidence into committed review artifacts because local `artifacts/` packets are gitignored.
- **Disposition:** FIXED
- **Evidence:** Mandatory role execution table in this artifact records all pre-open role passes and the cursor order-drift resolution.

### 5. Root artifact hygiene contaminates the Slack bridge PR

- **Failure story:** The branch combines Slack bridge extraction with broad root file moves/deletions. Reviewers cannot tell whether failures come from the bridge split, root cleanup, or unrelated import-path churn.
- **Underlying assumption:** Since root clutter is real, it is safe to fix alongside the bridge split.
- **Early warning signs:** Diff includes root-wide moves such as requirements reshuffles, script relocations, or broad docs cleanup not needed by the bridge.
- **Containment:** Track root artifact hygiene as a separate backlog follow-up and keep this PR scoped to Slack bridge boundaries plus required governance artifacts.
- **Disposition:** FIXED
- **Evidence:** `docs/roadmap/BACKLOG_LEDGER.md#ledger-p2-root-artifact-hygiene-follow-up` tracks the separate hygiene lane.

### 6. New hard-gate wording drifts from executable bootstrap behavior

- **Failure story:** The PR says role-agent launch is mandatory, but
  `task_bootstrap.py` still synthesizes only `qa-engineer-agent -> bug-hunter`
  for post-open review. Later lanes follow the packet, skip the security-auditor
  pass, and treat Codex Security as a replacement for repo role review.
- **Underlying assumption:** Updating AGENTS/RUNBOOK wording is enough when the
  packet schema still emits the older review lane.
- **Early warning signs:** `pr_lifecycle_contract.review_lane` lacks
  `security-auditor`; `role_agent_dispatch_contract` says required but does not
  say missing execution blocks readiness.
- **Containment:** Update the packet contract and tests so post-open review
  includes `qa-engineer-agent -> bug-hunter -> security-auditor`, records the
  Codex Security scan expectation, and marks role dispatch as a hard gate.
- **Disposition:** FIXED
- **Evidence:** `scripts/orchestration/task_bootstrap.py` now emits the expanded
  post-open lane plus hard-gate metadata; `tests/test_task_bootstrap.py` covers
  the contract.

### 7. Experiment Runner hard gate is misread as a CI-local artifact upload rule

- **Failure story:** A future PR flips CI to required mode while only recording
  gitignored `artifacts/orchestration/experiments/results/*.json` paths. CI then
  fails every valid PR because local runner artifacts are intentionally not
  committed, so maintainers roll back the whole Experiment Runner evidence
  requirement.
- **Underlying assumption:** Process hard gate and CI artifact availability are
  the same problem.
- **Early warning signs:** Docs say "hard gate" without explaining local-only
  runner artifacts; `check_merge_ready.py` advisory-mode output suggests missing
  evidence is harmless.
- **Containment:** Make the PR process gate mandatory now, but keep machine
  default activation tracked until a CI-safe evidence mirror exists. Clarify the
  distinction in the experimentation protocol, rollout packet, ledger, and merge
  wrapper output.
- **Disposition:** FIXED
- **Evidence:** `docs/orchestration/AGENT_EXPERIMENTATION_PROTOCOL.md`,
  `docs/orchestration/EXPERIMENT_RUNNER_EVIDENCE_REQUIRED_MODE_ROLLOUT_PACKET_2026-05-24.md`,
  `docs/roadmap/BACKLOG_LEDGER.md`, and
  `scripts/orchestration/check_merge_ready.py` now preserve the process hard
  gate without requiring committed local runner artifacts.

## Pre-Open Checklist

- [x] Preflight and agent consistency checks passed before implementation
- [x] Task packet generated with `--pr-phase pre_open`
- [x] Every pre-open role agent launched in required order
- [x] Premortem findings dispositioned
- [x] Focused Slack bridge test file passed after first coherent diff
- [x] Experiment Runner oracle/advisory mode run after coherent diff
- [x] Focused test bundle passed
- [ ] `make validate-changed` passed
- [ ] `pre-commit run --all-files` passed

Experiment Runner oracle evidence:

- Packet: `artifacts/orchestration/experiments/exp-5e8c86e3b72e.json` (local-only)
- Result: `artifacts/orchestration/experiments/results/exp-5e8c86e3b72e.json` (local-only)
- Status: accepted
- Mutated paths: `[]`
- Shared tree untouched: `true`
- Oracle commands: focused pytest bundle, bridge `--help`, bridge `--validate-runtime`
- Attribution: material `oracle_review`; commit that uses this evidence requires `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>`

## Decision

`proceed with changes` - implementation may proceed because the high-risk failure modes have specific containment actions and the first coherent diff preserves facade compatibility, lazy optional Slack transport, hash-only audit, and execute-mode gates. This is not merge readiness.
