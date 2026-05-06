<!-- markdownlint-disable MD013 -->
# Design Intelligence PR-5 Web Brief Packet

## Goal

Decide whether the web launch shell needs a PR-5 frontend implementation patch after the landed Design Intelligence evidence and scorecard layers.

## Decision

The web launch shell for `/` and `/marketing` is accepted with deferred minor follow-up. No frontend implementation is required in PR-5.

## Coordinator Route

Requested route:

1. `agent-coordinator`
2. `creative-designer`
3. `frontend-engineer`
4. `architecture-specialist`
5. `security-auditor`
6. `qa-engineer-agent`
7. `bug-hunter`
8. `data-scientist-agent`

The route is advisory through `task_bootstrap.py` and does not replace repository merge-readiness gates.

## Source Precedence

Repo code, tests, `/tokens`, generated mirrors, UI vocabulary, backend/OpenAPI contracts, and runtime code remain canonical.

The following are evidence/reference layers only:

- `docs/design/DESIGN.md`
- reference manifests
- screen evidence packs
- design scorecards
- Figma
- Canva
- Storybook
- external references
- prompt outputs

## Evidence Inputs

- PR #1608 merged launch-shell polish for `/` and `/marketing`.
- PR #1674 merged a bounded visible frontend follow-up.
- PR #1683 added metadata-only screen evidence pack tooling.
- PR #1686 added deterministic scorecard checks.
- `docs/design/screen_evidence/examples/web_marketing.sample.json` validates as sample evidence metadata.
- `docs/design/design_scorecard/examples/web_marketing.scorecard.sample.json` validates as a deterministic sample scorecard.

Required evidence commands:

```bash
python3 scripts/design/screen_evidence_pack.py validate-dir docs/design/screen_evidence/examples
python3 scripts/design/design_scorecard.py score docs/design/screen_evidence/examples/web_marketing.sample.json
python3 scripts/design/design_scorecard.py validate-score docs/design/design_scorecard/examples/web_marketing.scorecard.sample.json
python3 scripts/design/design_scorecard.py summarize docs/design/design_scorecard/examples/web_marketing.scorecard.sample.json
```

These commands provide governance evidence only. They do not prove live runtime visual readiness.

## Scope

- Add the PR-5 web launch shell acceptance brief.
- Record the acceptance decision and deferred follow-up boundary.
- Update the Design Intelligence ledger status narrowly.

## Out of Scope

- No frontend implementation.
- No iOS implementation.
- No Figma or Canva writes.
- No screenshots or binary artifacts.
- No scorecard, screen-evidence, reference-manifest, token, backend, OpenAPI, billing, auth, compliance, App Store, or deploy changes.

## Risks

- False visual-ready claim: mitigated by saying sample evidence is metadata only, not screenshot proof.
- Second source of truth: mitigated by repeating that repo runtime truth wins.
- Silent skip of necessary web work: mitigated by accepting only with deferred minor follow-up criteria.
- Broad redesign drift: mitigated by requiring any future implementation to name exact gaps, files, and tests.

## Definition of Done

- Acceptance brief exists.
- Packet records route, source precedence, evidence commands, and boundaries.
- Ledger marks PR-5 acceptance brief active without closing PR-6/PR-7/PR-8.
- Diff remains docs-only.
- Bounded checks pass.
