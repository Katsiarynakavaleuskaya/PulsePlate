# PulsePlate Composer Implementation Kit — PR-1 Bootstrap

## Goal

Enable Composer to start operating inside the PulsePlate workforce track safely and consistently.

This first PR is intentionally **narrow**:

- Cursor bootstrap rules
- slash-command task bootstrap
- action packet schema
- event log schema
- memory capsule schema
- local SQLite starter schema

## Branch

`docs/composer-bootstrap-kit`

## PR title

`docs(orchestration): add Composer bootstrap kit for local workforce track`

## In scope

- `.cursor/rules/*`
- `.cursor/commands/*`
- `docs/orchestration/schemas/*`
- `docs/orchestration/sql/local_agent_control_plane.sql`
- one short docs update linking to the kit

## Out of scope

- production runtime code
- deployment automation
- cloud agents
- secret handling
- autonomous execution beyond docs/tooling bootstrap

## Why first

Composer needs strict entry behavior before it can safely participate in a CAID-style local workforce system.

## DoD

- Composer has a repo-local bootstrap rule set
- Composer has a task bootstrap command
- action packet schema exists
- event log schema exists
- memory capsule schema exists
- local control-plane SQLite starter schema exists
- no product runtime behavior changes are introduced

## Review follow-up

This follow-up keeps the PR narrow and closes merge-readiness review items without widening scope:

- make SQLite child-table foreign-key behavior explicit
- add explicit human approval signaling to the action packet schema for high-risk work
- allow clean reflection packets without mandatory failure entries

## Next PRs

1. `chore(orchestration): add local workforce control-plane SQLite adapter`
2. `chore(cursor): add first 5 custom role modes`
3. `chore(mcp): add safe local adapters for repo/search/log triage`
4. `docs(orchestration): add director and memory librarian operating packets`

## Repo layout (this slice)

| Area | Paths |
|------|--------|
| Root bootstrap + role modes | `.cursor/rules/00_root_bootstrap.mdc` … `50_memory_librarian.mdc` |
| Commands | `.cursor/commands/create_action_packet.md`, `create_reflection_packet.md` |
| Control plane docs | `docs/orchestration/LOCAL_AGENT_*.md` |
| JSON Schema | `docs/orchestration/schemas/*.schema.json` |
| SQLite starter | `docs/orchestration/sql/local_agent_control_plane.sql` |

Install order matches [PulsePlate_Local_Agent_Workforce_System_Design_Packet_v1_2.md](./PulsePlate_Local_Agent_Workforce_System_Design_Packet_v1_2.md) §18 (Immediate implementation kit).
