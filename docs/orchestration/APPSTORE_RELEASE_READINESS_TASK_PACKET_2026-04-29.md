# App Store Release Readiness Task Packet

**Packet ID:** `appstore-release-readiness-2026-04-29`

**Epic:** `epic/appstore-release-readiness-full-feature`

**Created:** 2026-04-29

**Branch namespace:** `release/appstore-readiness-*`

## Task Summary

Coordinate the PR train that closes App Store readiness for full-feature
PulsePlate launch without deleting App Store assets or weakening release claims.

Canonical epic:

- `docs/release/APPSTORE_RELEASE_READINESS_EPIC.md`
- `docs/release/APPSTORE_FEATURE_ASSET_MATRIX.md`
- `docs/roadmap/BACKLOG_LEDGER.md#ledger-p0-appstore-release-readiness-full-feature`

Hard-gate source of truth:

- root `AGENTS.md` section `App Store release readiness gates`

This date-stamped packet is the PR-0 bootstrap packet for the lane. Future
slices add their own date-stamped packets; the stable entrypoints for the train
remain the epic, matrix, backlog anchor, and root `AGENTS.md` gate list.

## Scope

PR-0 is docs/governance only:

- add canonical epic and feature asset matrix
- add this task packet
- add backlog ledger anchor
- add root App Store release-readiness gates

PR-0 must not change:

- iOS runtime behavior
- Fastlane upload behavior
- App Privacy payload
- screenshot generation logic
- asset binaries
- backend endpoints
- web runtime

## Role Order

The coordinator-owned train uses this role order unless a later slice packet
narrows it with explicit rationale:

1. `agent-coordinator`
2. `ios-engineer-agent`
3. `appstore-release-agent`
4. `privacy-compliance-agent`
5. `security-auditor`
6. `backend-engineer-agent`
7. `frontend-engineer-agent`
8. `design-systems-agent`
9. `qa-engineer-agent`
10. `bug-hunter`

Mandatory post-open review lane:

```text
qa-engineer-agent -> bug-hunter
```

## Recommended Skills

- `pulseplate-workflow`
- `pulseplate-app-store-release`
- `pulseplate-agent-product`
- `pulseplate-design-launch-system`
- `pulseplate-monetization-gtm`
- `pulseplate-pr-review`
- `pulseplate-gates`
- `pulseplate-ledger`
- `pulseplate-guards`
- `pulseplate-backend-endpoints` when backend smoke/endpoint truth changes
- `pulseplate-openapi-sync` only when backend API contract changes
- `pulseplate-frontend-ui` only when web UI changes
- `pulseplate-web-launch-site` only when public launch-site copy changes

External plugins such as Browser Use, Computer Use, Figma, Canva, Netlify,
Cloudflare, Hugging Face, Jam, Remotion, Life Science Research, Expo, and
CodeRabbit are optional evidence helpers only. They do not replace repo source
of truth, coordinator routing, fixed-mapping governance, or local gates.

## PR Train

| PR | Branch | Primary outcome | Blocking proof |
| --- | --- | --- | --- |
| PR-0 | `release/appstore-readiness-pr0-bootstrap` | Epic, matrix, packet, ledger, root gates | docs/ledger validation and repo policy guards |
| PR-1 | `release/appstore-readiness-pr1-privacy-manifest` | Privacy manifest and App Privacy truth | privacy manifest and App Privacy contract tests |
| PR-2 | `release/appstore-readiness-pr2-permission-purpose-strings` | Sensitive permission string cleanup | permission purpose-string guard |
| PR-3 | `release/appstore-readiness-pr3-base-url` | Explicit HTTPS Release backend | Release plist/baseURL tests |
| PR-4 | `release/appstore-readiness-pr4-asset-gating` | Screenshot submission policy | Swift and Python asset policy tests |
| PR-5 | `release/appstore-readiness-pr5-appicon` | AppIcon marketing asset validation | `actool` plus asset catalog test |
| PR-6 | `release/appstore-readiness-pr6-healthkit-swift6` | Read-only HealthKit Swift 6 cleanup | HealthKit tests and reviewer-note parity |
| PR-7 | `release/appstore-readiness-pr7-ai-consent` | AI wellness consent before CBT insight | consent-gate tests and privacy copy contract |
| PR-8 | `release/appstore-readiness-pr8-reviewer-pack` | Reviewer notes and metadata sync | Fastlane metadata validators |
| PR-9 | `release/appstore-readiness-pr9-validation-gates` | CI release validators | `make ios-appstore-verify` |

## Bootstrap Commands

Run from synced root before each slice:

```bash
git fetch --prune origin
git checkout main
git merge --ff-only origin/main
git rev-list --left-right --count HEAD...origin/main
git worktree add worktrees/appstore-readiness-pr<N> -b release/appstore-readiness-pr<N>-<slug> origin/main
```

Run inside the slice worktree before edits:

```bash
python3 scripts/orchestration/check_preflight.py
python3 scripts/orchestration/check_agent_consistency.py
python3 scripts/orchestration/task_bootstrap.py \
  --goal "App Store release readiness slice <N>: <goal>" \
  --task-class Orchestration \
  --pr-phase pre_open \
  --requested-agent agent-coordinator \
  --requested-agent ios-engineer-agent \
  --requested-agent appstore-release-agent \
  --requested-agent privacy-compliance-agent \
  --requested-agent security-auditor \
  --requested-agent qa-engineer-agent \
  --requested-agent bug-hunter
```

## Gates

Minimum every slice:

```bash
python3 scripts/orchestration/check_preflight.py
python3 scripts/orchestration/check_agent_consistency.py
pytest -q tests/test_repo_policy_guards.py
pre-commit run --all-files
make verify
```

iOS/App Store slices add the focused gate that matches touched surface:

```bash
make ios-test
bundle exec fastlane verify_appstore_metadata
make ios-appstore-verify
```

Protected upload claims require post-merge operator evidence from
`docs/runbooks/IOS_APPSTORE_ASSETS_ROLLOUT.md`; implementation PRs do not close
the protected rollout by themselves.

## Decisions

1. Assets are preserved and classified; public submission is gated.
2. The first runtime blocker is privacy manifest plus App Privacy truth.
3. The Release backend host must be explicit HTTPS. The exact host is tracked in
   `docs/release/APPSTORE_RELEASE_READINESS_EPIC.md#backend-host-decision-register`
   and remains a PR-3 operator decision.
4. Social features are out of scope for this train.
5. Apple Server API migration and billing rewrite are out of scope.
6. AI/CBT release requires explicit consent and wellness-only copy.

## Stop Conditions

Stop and report before editing more files if:

- a worktree/branch does not match the PR slice
- unrelated user or colleague changes appear in the touched files
- a slice needs backend/API/runtime changes outside its declared PR scope
- `DATA_NOT_COLLECTED` remains while network data flows are being claimed as
  App Store-ready
- a screenshot scenario is marked `SUBMIT_READY` without release flag, smoke,
  privacy, and reviewer-note proof
- protected upload credentials or App Store secrets would need to be placed in
  repo files
