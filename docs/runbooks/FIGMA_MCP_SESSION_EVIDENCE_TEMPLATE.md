# Design Tooling Session Evidence Template

Use this template after each governed design-tooling session. Keep the title of
the copied session file specific to the tool used (`FIGMA`, `NOTION`,
`AIRWEAVE`, `PENPOT`), but preserve the common fields below for auditability.

## Session Metadata

- Date:
- Operator:
- Branch:
- Tool:
- Runtime:
- Local source route:
- Source URL:
- Target file/workspace URL:
- Target node/frame/page URL:

## Preconditions Check

- Secret/token present in runtime: yes/no
- Secret length check passed: yes/no
- Tool/server visible in runtime: yes/no
- Required tools callable: yes/no
- Canonical SoT preserved: yes/no

## Execution

### Request

- Prompt used:
- Task packet:
- Variant label:
- Target surface:

### Result

- Created/updated external artifact ID:
- Created/updated node/frame/page ID:
- Lifecycle status:
- Push/read status: success/failure

## Validation

- Visual parity status: pass/fail
- Naming convention status: pass/fail
- Layer hygiene status: pass/fail
- Canonical source precedence status: pass/fail

## Security Check

- Token value leaked: yes/no
- Sensitive data in logs/comments: yes/no
- External content promoted to git with evidence only: yes/no

## Raw Evidence

- Command 1:
- Output lines:
- Exit code:

- Command 2:
- Output lines:
- Exit code:

## Follow-ups

- Next iteration variant:
- Blockers:
- Owner:
