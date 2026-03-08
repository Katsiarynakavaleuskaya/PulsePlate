# Notion Structured Memory Governance

<!-- markdownlint-disable MD013 -->

This runbook defines how PulsePlate agents may use `Notion` without turning it
into a second source of truth.

## Purpose

Use Notion as a structured workspace for:

- PRD and feature briefs
- design briefs
- research digests
- meeting summaries
- agent handoff pages

## Allowed

- Read and summarize existing Notion pages
- Create or update working pages for briefs and handoffs
- Link back to canonical repo docs and Figma nodes
- Capture decision context before promotion into git

## Forbidden As Source Of Truth

Do not treat Notion as canonical for:

- runtime contracts
- design-token SoT
- security policy
- review mapping
- merge readiness

## Agent Flow

1. Ingest or read Notion content.
2. Summarize or structure it for the current task.
3. Link it to canonical repo docs or Figma nodes.
4. Promote durable insights into git through KPP.

Hard rule: if a reusable rule matters for future work, it must move into a repo
artifact with evidence.

## Access Model

- Phase 1: `HITL/browser-first`
- Phase 2: optional env/API-based automation only after a separate security
  review and runbook extension

## Evidence

Use the common design-tooling evidence template and record:

- Notion page URL
- purpose of the page
- whether content stayed working-only or was promoted into git

## Security Notes

- Never paste secrets into Notion pages.
- Treat Notion content as editable working memory, not immutable truth.
- Avoid copying sensitive internal URLs into pages meant for broad sharing.
