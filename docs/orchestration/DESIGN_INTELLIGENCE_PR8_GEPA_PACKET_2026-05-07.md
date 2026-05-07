<!-- markdownlint-disable MD013 -->
# Design Intelligence PR-8 GEPA Packet

## Branch And Title

- Branch: `docs/design-gepa-prompt-rubric-lane-v1`
- Title: `docs(research): add GEPA-compatible prompt/rubric evolution lane`

## Goal

Add the Design Intelligence PR-8 research/eval lane for GEPA-compatible prompt and rubric evolution after PR-7 workflow/template governance.

This packet is binding for PR-8 scope. It does not authorize runtime, token, Figma, Canva, Storybook, screenshot, asset, or infrastructure changes.

## Touched Paths

Expected paths:

- `docs/research/DESIGN_GEPA_PROMPT_RUBRIC_EVOLUTION_LANE.md`
- `docs/orchestration/DESIGN_INTELLIGENCE_PR8_GEPA_PACKET_2026-05-07.md`
- `tests/test_design_gepa_research_lane_docs.py`
- `docs/roadmap/BACKLOG_LEDGER.md`
- `docs/review/PR_<N>_FIXED_MAPPING.md` after the PR number exists

Forbidden paths:

- `frontend/**`
- `ios/**`
- `app/**`
- `core/**`
- `tokens/**`
- generated token mirrors
- Storybook configuration
- Figma or Canva remote assets
- screenshots, videos, runtime/product traces, binary assets, and external infrastructure

## Coordinator Bootstrap

Run before editing:

```bash
.venv/bin/python scripts/orchestration/check_preflight.py
.venv/bin/python scripts/orchestration/check_agent_consistency.py
.venv/bin/python scripts/orchestration/task_bootstrap.py \
  --goal "Design Intelligence PR-8: add GEPA-compatible prompt/rubric evolution lane" \
  --task-class "Research" \
  --pr-phase pre_open \
  --requested-agent agent-coordinator \
  --requested-agent creative-designer \
  --requested-agent architecture-specialist \
  --requested-agent security-auditor \
  --requested-agent qa-engineer-agent \
  --requested-agent bug-hunter \
  --requested-agent data-scientist-agent \
  --requested-agent ml-engineer-agent
```

Observed pre-open route for this branch:

- Task packet: `artifacts/orchestration/task_packets/a5391218cf3d.json` (local, gitignored)
- Primary: `agent-coordinator`
- Reviewer: `ai-innovation-specialist`
- Cluster/domain: `ml` / `research`
- Requested route: `agent-coordinator`, `creative-designer`, `architecture-specialist`, `security-auditor`, `qa-engineer-agent`, `bug-hunter`, `data-scientist-agent`, `ml-engineer-agent`
- Bootstrap disposition: `agent-coordinator` promoted; the other requested roles are advisory review lanes for this research packet and actual diff.

No system Python command examples are allowed in this packet or PR docs. Use repo `.venv/bin/python` only.

## Role Order

1. `agent-coordinator`: scope, route, risks, touched paths, validation, and DoD.
2. `creative-designer`: design evidence boundaries and no Figma/Canva authority drift.
3. `architecture-specialist`: no second source of truth and no runtime architecture mutation.
4. `security-auditor`: no prompt self-modification, secret, user-data, or live-flow loopholes.
5. `qa-engineer-agent`: docs guard coverage and bounded check plan.
6. `bug-hunter`: scope creep, generated mirror, runtime, and regression sweep.
7. `data-scientist-agent`: eval fixture and trace governance.
8. `ml-engineer-agent`: GEPA-compatible research boundary and no production optimization engine.

## Required Skills And Plugins

Use as advisory helpers only:

- `pulseplate-design-launch-system`
- `pulseplate-pr-review`
- `pulseplate-premortem-risk-review`
- Codex Security review for security wording and loopholes after the PR opens
- GitHub and CodeRabbit for PR truth and review comments when available

Do not vendor, install, or commit skill changes in PR-8. Existing root skill drift remains out of scope.

## Source Precedence

Canonical:

- Repo code/docs/tests and `AGENTS.md`.
- `/tokens` as token authoring truth.
- Generated mirrors as derived artifacts.
- UI vocabulary.
- Backend/OpenAPI contracts.
- Runtime web and iOS code.

Reference/evidence/process only:

- `DESIGN.md`.
- Reference manifests.
- Screen evidence packs.
- Design scorecards.
- Web acceptance briefs.
- iOS parity audits.
- Figma, Canva, Storybook, external references, prompt outputs, generated briefs, GEPA-inspired traces, and this packet.

## In Scope

- Add the PR-8 research lane doc.
- Add this orchestration packet.
- Add a deterministic docs guard test.
- Update the Design Intelligence ledger status.
- Add the fixed mapping artifact after the PR number exists.

## Out Of Scope

- No runtime web, iOS, backend, OpenAPI, billing, auth, StoreKit, HealthKit, entitlement, nutrition, BMI, or coaching changes.
- No `/tokens` changes.
- No manual generated mirror edits.
- No Figma writes.
- No Canva writes.
- No Storybook config changes.
- No screenshots, videos, runtime/product traces, binary assets, or external infrastructure.
- No GEPA runtime engine, online optimization, self-modifying production agent, or prompt mutation against live product flows.

## Premortem Checklist

Premortem must inspect the actual docs/test diff and fix real defects before mapping.

Check:

- Does wording create a second source of truth?
- Does wording imply automatic adoption or self-promotion of evolved prompts/rubrics?
- Does any command use a system Python interpreter instead of `.venv/bin/python`?
- Does any loophole allow runtime web, iOS, backend, token, Figma, Canva, Storybook, screenshot, asset, or infrastructure mutation?
- Does the PR claim green main or full local `make verify`?
- Does mapping attempt to substitute for fixing docs/test defects?

## Bug-Hunter Checklist

Bug-hunter must inspect the actual diff.

Verify:

- Docs/test-only diff before mapping; docs/review only after PR number exists.
- No runtime files changed.
- No `/tokens` files changed.
- No generated mirror files changed.
- No Figma, Canva, or Storybook-config write path.
- All command examples use `.venv/bin/python` or `DEV_PYTHON=.venv/bin/python VENV_PYTHON=.venv/bin/python`.
- Prompt outputs are not source of truth.
- GEPA remains research/eval/process-only.
- Next PR is not auto-started by this packet.

## Bounded Checks

Run only bounded checks for this lane:

```bash
.venv/bin/python scripts/orchestration/check_preflight.py
.venv/bin/python scripts/orchestration/check_agent_consistency.py
.venv/bin/python scripts/design/generate_design_md.py --check
.venv/bin/python scripts/design/reference_manifest.py validate-dir docs/design/reference_manifest/examples
.venv/bin/python scripts/design/screen_evidence_pack.py validate-dir docs/design/screen_evidence/examples
.venv/bin/python scripts/design/design_scorecard.py validate-score docs/design/design_scorecard/examples/web_marketing.scorecard.sample.json
.venv/bin/python scripts/design/design_scorecard.py validate-score docs/design/design_scorecard/examples/ios_home.scorecard.sample.json
.venv/bin/python -m pytest -q tests/test_design_gepa_research_lane_docs.py
DEV_PYTHON=.venv/bin/python VENV_PYTHON=.venv/bin/python make validate-changed
DEV_PYTHON=.venv/bin/python VENV_PYTHON=.venv/bin/python make design-guard
DEV_PYTHON=.venv/bin/python VENV_PYTHON=.venv/bin/python make tokens-check
PATH=.venv/bin:$PATH pre-commit run --all-files
```

Do not run full local `make verify` for this operator-scoped docs/research lane unless a later coordinator decision changes the validation scope.

This bounded-check path must still satisfy the root `AGENTS.md` machine-heavy exception before any merge-readiness claim:

- operator approval for bounded local checks is documented in the PR body and fixed mapping;
- all PR-scoped local gates listed above pass or have a fixed root-cause failure;
- the PR body and `docs/review/PR_<N>_FIXED_MAPPING.md` document the local full-verify deferral;
- current-head CI parity is complete for required checks, diff coverage, security/governance checks, and touched-surface checks;
- strict merge-readiness wrapper passes with auth after review dispositions and wait-window.

## Merge-Readiness Rules

Do not claim merge readiness until:

- current-head PR checks are complete;
- no actionable bot comments remain;
- no unresolved review threads remain;
- `docs/review/PR_<N>_FIXED_MAPPING.md` exists and matches the PR body;
- the PR body includes discussion-thread pass, fixed mapping, merge readiness, and follow-up sections;
- the mandatory wait-window has completed;
- strict merge-readiness wrapper passes with auth.

Strict wrapper:

```bash
GH_TOKEN=$(gh auth token) GITHUB_TOKEN=$(gh auth token) \
.venv/bin/python scripts/orchestration/check_merge_ready.py \
  --pr-number <N> \
  --repo Katsiarynakavaleuskaya/PulsePlate \
  --require-auth
```

## Rollback

Revert this docs/test PR. No runtime rollback is required.

If a later PR promotes a prompt/rubric candidate, that later PR must provide its own rollback path for the exact promoted artifact.

## Post-Merge Cleanup Notes

- Sync local `main` with fetch and fast-forward merge.
- Confirm branch sync state with `git rev-list --left-right --count HEAD...origin/main`.
- Inspect current main health without assuming it is green.
- Remove only this worktree, this local branch, local temp artifacts, and any local-only `.venv` symlink used in the worktree.
- Do not remove unrelated root `.agents/skills/*` or `skills-lock.json` changes.
- Do not start the next PR automatically.

## Definition Of Done

- Research lane doc exists.
- PR-8 packet exists.
- Docs guard test exists and passes.
- Ledger records PR-8 as active after PR-7 merge.
- No runtime, token, generated mirror, Figma, Canva, Storybook config, screenshot, asset, or infrastructure diff exists.
- Premortem and bug-hunter findings are fixed before mapping.
- Bounded checks pass.
