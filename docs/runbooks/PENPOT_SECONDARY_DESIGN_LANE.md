# Penpot Secondary Design Lane

<!-- markdownlint-disable MD013 -->

This runbook defines the Phase 1 role of `Penpot` in PulsePlate.

## Purpose

Use Penpot as a secondary design lane for:

- exploratory design work
- export/import backup flows
- open collaboration where Penpot is a better fit

## Status

- `Penpot` is not the primary design Source of Truth.
- `Figma Design + Code Connect` remain canonical for implementation traceability.
- Penpot work is advisory until reconciled back into repo/Figma artifacts.

## Allowed

- exploratory boards and drafts
- exportable design specs
- backup or alternative collaboration path

## Forbidden

- final component mapping authority
- canonical Code Connect ownership
- overriding Figma node mappings or repo design tokens

## Reconciliation Contract

1. Create or update the Penpot artifact.
2. Export or summarize the relevant design state.
3. Review against repo visual SoT and Figma mappings.
4. Promote the accepted outcome into canonical repo docs or Figma Design nodes.

## Access Model

- Phase 1: `HITL/browser-first`
- Future automation: only after a dedicated security and evidence contract

## Evidence

Record:

- Penpot project/workspace URL
- artifact reviewed
- export/spec generated
- canonical promotion target

Use the shared design-tooling evidence template.

## Security Notes

- Do not store tokens or sensitive URLs in repo docs.
- Penpot collaboration must not bypass repo review or design-token SoT.
