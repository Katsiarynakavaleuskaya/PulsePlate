# Penpot CTA Review Packet Template

**Date:** March 7, 2026
**Purpose:** tool-neutral review packet for a single CTA without requiring Figma Code Connect

## Packet Fields

1. `CTA ID`
2. `Runtime component path`
3. `Runtime screen/page path`
4. `Storybook review path`
5. `Repo test evidence`
6. `Token/variant reference`
7. `Design review reference`
8. `Penpot workspace / page / frame`
9. `Known gaps`
10. `Release decision`

## Required Evidence Rules

- Runtime ownership must point to a repo file path.
- Storybook review must point to a real story/MDX path in `frontend/src/`.
- Test evidence must point to at least one deterministic repo test.
- Design review reference stays tool-neutral:
  - preferred: packet doc path + Storybook story
  - optional: Penpot page/frame
  - optional later: Figma node ID only when Code Connect is in scope

## Packet Skeleton

```md
# CTA Review Packet — <CTA ID>

- Status: Draft | Review-ready | Approved
- Date: YYYY-MM-DD
- Owner: @owner

## 1. CTA Summary
- CTA ID:
- UI label:
- Runtime intent:

## 2. Runtime Ownership
- Component:
- Screen/page:
- Route / downstream flow:

## 3. Storybook Review Surface
- Story:
- Notes:

## 4. Repo Evidence
- Tests:
- Build / runtime note:

## 5. Design Review Reference
- Packet:
- Penpot:
- Optional Figma:

## 6. Token + Variant Alignment
- Variant family:
- Token source:
- Visual notes:

## 7. Known Gaps
- Gap 1
- Gap 2

## 8. Release Decision
- Decision:
- Follow-up:
```

## Acceptance

- Packet works without Code Connect
- Packet can be linked directly from the CTA matrix
- Packet is sufficient for FE + Design review even if Penpot frame is still pending
