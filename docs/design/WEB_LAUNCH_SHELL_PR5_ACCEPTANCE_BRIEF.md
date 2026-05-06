<!-- markdownlint-disable MD013 -->
# Web Launch Shell PR-5 Acceptance Brief

## Decision

The current PulsePlate web launch shell for `/` and `/marketing` is accepted with deferred minor follow-up. No PR-5 frontend implementation patch is required now.

This is a reviewed decision packet only. It is not runtime truth, visual proof, or a second source of truth. Repo code, tests, `/tokens`, generated mirrors, UI vocabulary, backend/OpenAPI contracts, and implemented runtime behavior remain canonical.

## Surfaces

- `/`
- `/marketing`

## Evidence Considered

- PR #1608, `feat(web): polish launch marketing shell`, merged 2026-04-30 at `25d5cb954b11278700bf399434b98338b6a501b6`.
- PR #1674, `feat(frontend): refine public web launch shell after governed polish`, merged 2026-05-06 at `b7fdd245591ad811170ec1d23002081b5978fbe2`.
- `docs/design/DESIGN.md`, generated semantic wrapper from repo token and component contracts.
- `docs/design/screen_evidence/examples/web_marketing.sample.json`, PR-3 sample metadata for the web marketing shell.
- `docs/design/design_scorecard/examples/web_marketing.scorecard.sample.json`, PR-4 deterministic scorecard sample for the web marketing shell.
- `docs/review/PR_1608_FIXED_MAPPING.md` and `docs/review/PR_1674_FIXED_MAPPING.md`, which record focused frontend validation and review dispositions for the launch-shell polish work.

## Acceptance Rationale

PR #1608 implemented the first bounded launch-shell polish pass using repo-owned web code, existing routes, wellness-safe copy, and reference-only design inputs. PR #1674 followed with a narrower visible frontend refinement and recorded route sanity for `/` and `/marketing`, including the public shell render path, hidden tabbar expectation, and no horizontal-overflow regression.

The Design Intelligence evidence chain now exists and can govern future work:

- PR-1 generated/drift-checked `DESIGN.md` as non-canonical agent-readable guidance.
- PR-2 added external reference manifest tooling without allowing copy or second-source-of-truth drift.
- PR-3 added metadata-only screen evidence pack tooling.
- PR-4 added deterministic scorecard tooling over screen evidence metadata.

The PR-4 web marketing sample scorecard returns `status=pass`, `normalized_score=1.0`, and `recommendation=usable_for_pr5_pr6_brief`. This supports a governance decision that another immediate web-polish PR is not warranted.

This scorecard is not live runtime screenshot proof. It is deterministic metadata evidence over committed sample evidence. The acceptance decision also depends on the already-merged frontend work and review mappings from PR #1608 and PR #1674.

## Deferred Minor Follow-Up

Future web implementation should be opened only if a reviewer identifies a concrete bounded gap. Acceptable future gaps include:

- a specific `/` or `/marketing` route regression,
- a token/component-vocabulary mismatch,
- an accessibility or keyboard evidence gap from a real capture lane,
- a wellness-copy safety issue,
- a documented overflow, focus, or reduced-motion regression.

Any follow-up must name exact files and tests before implementation. It must not become a broad redesign.

## Decision Outcome

- Current web shell: accepted with deferred minor follow-up.
- PR-5 frontend implementation: skipped/deferred unless a future bounded gap is found.
- Next Design Intelligence slice: PR-6 iOS visual parity audit and bounded sync.

## Out of Scope

- No frontend runtime changes.
- No iOS runtime changes.
- No backend, OpenAPI, billing, auth, compliance, App Store, or deploy changes.
- No `/tokens` changes.
- No generated token mirror edits.
- No Figma or Canva writes.
- No screenshots, videos, traces, Storybook output, or binary artifacts.
- No scorecard, screen-evidence, or reference-manifest tooling changes.
