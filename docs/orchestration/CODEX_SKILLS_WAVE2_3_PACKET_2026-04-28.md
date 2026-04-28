# PulsePlate Codex Skills Wave 2/3 Packet

Date: 28 April 2026
Branch: `codex/pulseplate-skills-wave2-3`
Coordinator packet: `artifacts/orchestration/task_packets/acc91e19d4ef.json` (local, gitignored)

## Coordinator Start

Primary agent: `agent-coordinator`

Declared role order:

1. `agent-coordinator`
2. `architecture-specialist`
3. `qa-engineer-agent`
4. `bug-hunter`
5. `data-scientist-agent`

The coordinator scoped this lane to PulsePlate Codex skills points 1-3:

1. Close stale ledger state for merged `pulseplate-design-launch-system`.
2. Add `pulseplate-web-launch-site`.
3. Add `pulseplate-agent-product`.

## Required Skills

- `pulseplate-workflow`
- `pulseplate-gates`
- `pulseplate-ledger`
- `pulseplate-guards`
- `pulseplate-pr-review`
- `docs-sync`
- `agents-md`
- `bug-triage`
- `code-review-expert`

## Lane Contract

Allowed:

- add passive repo-tracked skills under `tools/codex_skills/`,
- expose those skills through `.agents/skills/`,
- update skill inventory, alignment, routing policy, ledger, and deterministic tests,
- wire deterministic `skill_router.py` recommendations.

Out of scope:

- replacing `agent-coordinator`,
- adding runtime agent autonomy,
- changing `native_subagent_bridge` semantics,
- adding deployment, billing, review posting, or auto-merge behavior,
- creating a parallel orchestration layer.

## Role Review

- `agent-coordinator`: Owns scope, worktree isolation, packet, and Definition of Done.
- `architecture-specialist`: Confirms skills stay passive and additive.
- `qa-engineer-agent`: Owns deterministic tests and focused gate plan.
- `bug-hunter`: Looks for stale-ledger, mirror, and router false-green risks.
- `data-scientist-agent`: Keeps scoring/eval language advisory and future-facing only.

## Gate Plan

Focused:

- `python3 -m pytest tests/test_install_codex_skills.py tests/test_skill_router.py -q`
- `python3 scripts/orchestration/check_preflight.py`
- `python3 scripts/orchestration/check_agent_consistency.py`
- `pre-commit run --all-files`
- `make validate-changed`

Machine-heavy full `make verify` remains deferred unless the operator requests it;
GitHub current-head CI is the heavy signal for this docs/skills/router lane.

## Decision Log

- Deliver both remaining custom skills in one small skills wave because they share
  the same installer, mirror, docs, ledger, and routing surfaces.
- Close the stale design-launch ledger item using live PR #1482 merge evidence.
- Keep both new skills passive/discovery-only; neither can execute deployment,
  merge, thread resolution, billing, or runtime autonomy.
