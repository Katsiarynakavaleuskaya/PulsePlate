# Experiment Runner Lane Start Provenance Packet

**Date:** 2026-05-21
**Status:** Coordinator-owned pre-open packet for the lane-start provenance PR
**Branch:** `codex/experiment-runner-lane-start-provenance`
**Worktree:** `worktrees/experiment-runner-lane-start-provenance`
**Bootstrap packet:** `artifacts/orchestration/task_packets/a733b2e09986.json`

## Goal

Make repo-owned lane startup provenance explicit, keep host/Codex preflight from
substituting for PulsePlate orchestration, and prepare Experiment Runner
Evidence for future hard gating while this PR remains diagnostic dry-run.

## Coordinator Start

Repo startup authority remains:

```text
check_preflight.py -> task_bootstrap.py -> agent-coordinator
```

Experiment Runner joins after coordinator bootstrap as oracle-only evidence. It
does not replace `agent-coordinator`, does not become lane-start authority, and
does not gain mutation authority over governance validators.

## Role Order

Coordinator-declared role order:

```text
agent-coordinator -> architecture-specialist -> security-auditor -> qa-engineer-agent -> bug-hunter -> dev-operator
```

Supporting bridge-dispatch reviewers from the bootstrap packet:

```text
agent-coordinator -> cursor-specialist-agent -> security-auditor -> architecture-specialist
```

Mandatory closure reviewers:

```text
qa-engineer-agent -> bug-hunter
```

## Scope

In scope:

- Phase2 PR body/fixed-mapping diagnostics for `Experiment Runner Evidence`
- Phase2 PR body/fixed-mapping diagnostics for `Lane Start Provenance`
- starter script and generated Codex prompt wording
- task-bootstrap JSON packet parsing by the Qoder dispatch bridge
- documentation for coordinator-first startup and Experiment Runner oracle-only
  participation
- focused regression tests for the governance surfaces above

Out of scope:

- active merge blocking for missing runner evidence or lane provenance
- Experiment Runner mutation of `scripts/ci/**` or other validator authority
- hidden replacement of `agent-coordinator` with Experiment Runner
- product/runtime behavior, OpenAPI, DB, frontend, iOS, provider, or medical
  claim changes

## Experiment Runner Evidence

Local oracle-only result artifact for this PR:

```text
artifacts/orchestration/experiments/results/lane-start-provenance-oracle.json
```

The artifact records `mutated_paths: []`, `promotion_ready: false`, and
`coauthor_required: true` because the runner evidence shaped the diagnostic
design and commit decision.
