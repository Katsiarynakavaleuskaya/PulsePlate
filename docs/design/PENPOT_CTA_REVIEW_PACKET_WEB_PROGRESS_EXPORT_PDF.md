# CTA Review Packet — `web.progress.export_pdf`

- Status: Pilot exception - Storybook-backed, pending Penpot frame capture
- Date: 2026-03-07
- Owner: @katsiaryna_kavaleuskaya

## 1. CTA Summary

- CTA ID: `web.progress.export_pdf`
- UI label: `Export PDF`
- Runtime intent: export the rendered progress dashboard as a local PDF file

## 2. Runtime Ownership

- Component: `frontend/src/components/cta/ProgressExportPdfButton.tsx:6`
- Screen/page: `frontend/src/features/progress/ProgressCharts.tsx:145`
- Route / downstream flow: local client-side export, no backend dependency on click

## 3. Storybook Review Surface

- Story: `frontend/src/components/cta/ProgressExportPdfButton.stories.tsx:6`
- Storybook title: `PulsePlate/Patterns/ProgressExportPdfButton`
- Notes: isolates the utility CTA from chart layout so design review can focus on label, icon, and utility-button emphasis

## 4. Repo Evidence

- Tests:
  - `frontend/src/features/progress/__tests__/ProgressCharts.test.tsx:153`
- Runtime evidence:
  - success path saves `progress-report.pdf`
    (`frontend/src/features/progress/__tests__/ProgressCharts.test.tsx:153`)
  - failure path emits deterministic `showError(...)`
    (`frontend/src/features/progress/__tests__/ProgressCharts.test.tsx:173`)

## 5. Design Review Reference

- Packet: this document
- Penpot workspace: `https://design.penpot.app/#/dashboard/recent?team-id=ff0898e1-835b-80ff-8007-ac98b669a273`
- Penpot page/frame: pilot exception pending first explicit Progress export CTA board capture in the registered team workspace
- Optional Figma: node ID remains intentionally non-blocking on the bridge path

## 6. Token + Variant Alignment

- Variant family: `V3`
- Token source:
  - `frontend/src/styles/tokens.css:8`
  - `frontend/src/styles/tokens.ts:12`
- Visual notes:
  - utility-primary emphasis
  - icon + label pair
  - must remain readable inside a chart-heavy header context

## 7. Known Gaps

- Review packet does not yet include a Penpot frame URL and therefore remains a documented pilot exception
- Export CTA still lives inside a larger chart container for runtime behavior, so story coverage is intentionally style-first

## 8. Release Decision

- Decision: acceptable as pilot review packet for utility CTA review under the Penpot bridge
- Follow-up: add a Penpot frame reference once the Progress header board exists in the registered workspace
