# PulsePlate Local Workforce RFC Packet — PR-1 Reclassification Note

## Goal

Reclassify PR `#1325` from a mistaken bootstrap implementation lane into a docs-only RFC/reference lane.

This PR should describe the proposed local workforce platform shape, evidence baseline, and rollout decomposition only. It should not introduce executable or policy-shaping surfaces into the repository.

## Branch

`docs/composer-bootstrap-kit`

## Recommended PR title

`docs(orchestration): add local workforce platform RFC packet`

## Keep in scope

- [PulsePlate_Local_Agent_Workforce_System_Design_Packet_v1_2.md](./PulsePlate_Local_Agent_Workforce_System_Design_Packet_v1_2.md)
- [CURSOR_COMPOSER_PLATFORM_FACTS_VERIFIED.md](./CURSOR_COMPOSER_PLATFORM_FACTS_VERIFIED.md)
- this decomposition note

## Remove from scope

- `.cursor/rules/*`
- `.cursor/commands/*`
- `docs/orchestration/LOCAL_AGENT_*`
- `docs/orchestration/schemas/*`
- `docs/orchestration/sql/local_agent_control_plane.sql`

## Why reclassification is necessary

The repo already contains canonical seams for the workflows that this PR originally tried to introduce again:

- task bootstrap/coordinator flow already exists and should be extended rather than paralleled
- reflection flow already has a canonical protocol and should be extended there first
- repo-global workflow and merge governance are owned by root policy, not by a docs-only bootstrap slice
- the platform facts note still contains `[VERIFY]` items and cannot safely sit behind always-on rules

## Required file posture

### Design packet

Treat the design packet as RFC/reference architecture only.

### Platform facts note

Treat the facts file as evidence/reference only, not canonical policy.

### This document

Treat this file as a rollout/decomposition note for future follow-on PRs, not as proof that a bootstrap kit is already implemented.

## Follow-on PRs

Status snapshot before starting any follow-on repo slice:

- coordinator automation PR2 bootstrap hardening is already landed on `main`
- coordinator automation PR3 skill routing is already landed on `main`
- coordinator automation PR4 PR lifecycle automation is already landed on `main`
- coordinator automation PR5 creative/design activation is already landed on `main`
- bootstrap sync-policy extraction is already landed on `main`

These bullets describe the landed **repo-engine baseline once invoked**. They do not imply raw-session auto-start, launcher enforcement, or host-runtime guarantees by docs alone.

That means the workforce follow-ons below must extend the **current canonical baseline**, not reopen those earlier automation slices under new names.

1. `PR-A` — extend the canonical coordinator bootstrap seam instead of adding a second packet system
   - primary surfaces: `scripts/orchestration/task_bootstrap.py`, `scripts/orchestration/skill_router.py`, `scripts/orchestration/bootstrap_sync_policy.py`
   - expected parity docs/tests: `docs/orchestration/AGENT_SKILL_ROUTING_POLICY.md`, `docs/orchestration/AGENT_MESSAGE_PROTOCOL.md`, `tests/test_task_bootstrap.py`, `tests/test_skill_router.py`, `tests/test_bootstrap_sync_policy.py`
   - planning packet: [`LOCAL_WORKFORCE_PR_A_TASK_PACKET_2026-04-05.md`](./LOCAL_WORKFORCE_PR_A_TASK_PACKET_2026-04-05.md)
   - hard constraint: additive packet/routing semantics only; no standalone `action_packet` tree, no parallel bootstrap schema system
2. `PR-B` — extend the canonical reflection protocol before deriving helper/schema material
   - primary surface: `docs/orchestration/AGENT_REFLECTION_PROTOCOL.md`
   - hard constraint: protocol first, helper/schema second; no parallel reflection contract
3. `PR-C` — add experimental local support-plane storage as a non-canonical support plane
   - primary surfaces must reuse existing security/control-plane runtime and runbook primitives unless coordinator review records an explicit exception
   - hard constraint: this remains support infrastructure, not the canonical orchestration source of truth

## Worktree promotion

Safe path remains standard git flow:

1. update the branch in the worktree
2. push the branch
3. merge only the docs-only RFC lane
4. fetch `origin/main` and sync the local baseline by the repo's canonical git flow
5. if a follow-on child lane needs restacking, use the canonical replacement-PR / cherry-pick flow from `AGENTS.md` and `RUNBOOK_AGENT.md` instead of ad-hoc `pull` / `rebase` guidance

Do not manually copy files from the worktree into `main`.
