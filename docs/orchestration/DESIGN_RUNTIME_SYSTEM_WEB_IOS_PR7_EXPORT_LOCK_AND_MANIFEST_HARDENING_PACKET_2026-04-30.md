# PR-7 Design Export Lock And Manifest Hardening Packet

Date: 2026-04-30
Branch: `codex/design-export-lock-and-manifest-hardening`
Worktree: `worktrees/design-runtime-system-pr7`
PR series: Design runtime system web+iOS

## Coordinator Scope

PR-7 hardens the existing Figma design manifest into a repo-governed export
lock without widening token-pipeline schema ownership or creating missing asset
masters.

Role order:

1. `agent-coordinator`
2. `creative-designer`
3. `frontend-engineer`
4. advisory `cursor-specialist-agent`
5. reviewer `architecture-specialist`
6. mandatory post-open `qa-engineer-agent -> bug-hunter`

## Skills And Plugins

Required PulsePlate skills:

- `pulseplate-workflow`
- `pulseplate-design-launch-system`
- `pulseplate-gates`
- `pulseplate-guards`
- `pulseplate-ledger`
- `pulseplate-pr-review`

Advisory only if discovery touches the area:

- `pulseplate-frontend-ui` for token/runtime UI context only
- `pulseplate-graphmap` for manifest dependency graph evidence only

Out of scope unless a coordinator handoff is recorded:

- `pulseplate-openapi-sync`
- `pulseplate-backend-endpoints`
- `pulseplate-app-store-release`
- `pulseplate-web-launch-site`
- `pulseplate-monetization-gtm`
- `pulseplate-ai-reports`

External capabilities:

- GitHub for draft PR, current-head checks, review state, merge readiness, and
  merge.
- CodeRabbit for review input and disposition lifecycle.
- Figma read-only provenance from file `2JDwOByQIbcPgp93FDzHii`.

## Implementation Contract

In scope:

- Update `docs/design/figma-manifest.json` from `bootstrap` to `locked`.
- Lock only existing repo-governed design audit/runtime-set artifacts.
- Add deterministic `sha256` values for locked repo artifact paths.
- Preserve canonical Figma provenance with concrete design URLs and node IDs.
- Narrowly update `scripts/design_guard.py` so locked manifests validate export
  integrity while allowing icon-core lock metadata to remain explicitly
  deferred.
- Add focused locked-state tests in `tests/test_design_invariant_guard.py`.
- Update `docs/roadmap/BACKLOG_LEDGER.md` to mark PR-6 / `#1581` merged and
  PR-7 active.

Out of scope:

- Figma writes or exports.
- Missing icon-core master creation.
- Token generation or token schema unification.
- Storybook parity widening.
- Product screen migration.
- Backend, OpenAPI, billing, deploy, iOS adoption, App Store, Canva,
  Cloudflare, Remotion, macOS, or Life Science work.

## Design Source Precedence

Repo files remain Source of Truth. Figma is a read-only design-intent and
provenance lane. `/tokens` remains the token authoring source; generated web
and iOS mirrors remain derived runtime outputs. `figma-manifest.json` becomes a
locked export manifest only for the governed export set in this PR; it does not
become the token-pipeline schema.

## Validation

Start gates:

- `python3 scripts/orchestration/check_preflight.py`
- `python3 scripts/orchestration/check_agent_consistency.py`

Required local gates before push:

- `pytest -q tests/test_design_invariant_guard.py`
- `python3 scripts/design_guard.py --manifest docs/design/figma-manifest.json`
- `pytest -q tests/test_repo_policy_guards.py`
- `pre-commit run --all-files`
- `make verify`

PR lifecycle:

- Open draft PR first.
- After PR number exists, create `docs/review/PR_<N>_FIXED_MAPPING.md`.
- Run CodeRabbit / review disposition workflow.
- Run mandatory `qa-engineer-agent -> bug-hunter`.
- Mark ready only after current-head CI is green, all actionables are
  dispositioned, strict merge wrapper passes, and the wait-window is observed.

## Deferred / Blocked

The icon-core L4 lock remains deferred because
`assets/brand/icon/core/v1.0/icon_core_v1.svg` is absent on `main` and
`assets/brand/icon/core/v1.0/meta.json` still contains
`TBD_AFTER_WINNER_LOCK`. PR-7 records this explicitly and does not fabricate
missing asset evidence.

## Next Slice

After PR-7 merges and `main` is stable, the next design epic slice is PR-8
Storybook parity on branch `codex/storybook-design-review-parity`.
