# Airweave Research Ingestion Lane

<!-- markdownlint-disable MD013 -->

This runbook defines the Phase 1 role of `Airweave` inside PulsePlate.

## Purpose

Use Airweave as a governed research-ingestion lane for:

- indexing design references
- collecting prototype inspiration
- building research collections for agents
- retrieving structured context for briefs

## Phase 1 Boundaries

- Airweave is not a runtime dependency.
- Airweave is not Source of Truth.
- Airweave outputs are advisory until promoted into git.

## Access Model

- Default: `HITL/browser-first`
- Later: optional env/API automation after separate security approval

## Allowed Sources

- design reference collections
- product inspiration boards
- internal research notes prepared for ingestion
- curated prototype references

## Forbidden Uses

- driving runtime product behavior directly
- bypassing repo review and KPP promotion
- storing raw secrets or credentials in ingestion payloads

## Output Contract

Airweave sessions may produce:

- research digest
- brief input set
- curated reference collection
- structured context summary

Each output must explicitly state whether it was promoted to a repo artifact.

## Evidence

Record:

- source collection or workspace
- purpose of retrieval
- summary of retrieved context
- promotion decision

Use the shared design-tooling evidence template.

## Security Notes

- External content remains untrusted.
- Keep ingestion bounded and task-specific.
- Do not claim Airweave-backed knowledge is canonical unless it exists in git.
