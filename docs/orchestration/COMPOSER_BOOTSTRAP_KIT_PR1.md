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

1. `PR-A` — extend the canonical coordinator bootstrap seam instead of adding a second packet system
2. `PR-B` — extend the canonical reflection protocol before deriving helper/schema material
3. `PR-C` — add experimental local control-plane storage as a non-canonical support plane

## Worktree promotion

Safe path remains standard git flow:

1. update the branch in the worktree
2. push the branch
3. merge only the docs-only RFC lane
4. fetch or pull `main`
5. rebase or restack follow-on PRs onto the updated `main`

Do not manually copy files from the worktree into `main`.
