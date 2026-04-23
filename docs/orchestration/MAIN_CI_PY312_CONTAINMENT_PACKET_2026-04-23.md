# Main CI Py312 Xdist Containment Packet

Date: 2026-04-23
Branch: `codex/main-py312-containment`
Worktree: isolated local worktree, not committed as a repo-specific path.
Base: `origin/main`

## Coordinator Start

`agent-coordinator` owns this lane. The lane starts from the user's explicit
role order and stays bounded to main-branch CI containment for Python 3.12
worker-node instability.

## Assigned Role Agents

- `agent-coordinator`: task analysis, role routing, packet, scope lock, final synthesis, DoD.
- `dev-operator`: GitHub Actions evidence, live run triage, current-head CI truth, rerun/watch flow.
- `architecture-specialist`: confirms containment does not change required-check topology or CI contract shape.
- `backend-engineer`: edits `.github/workflows/ci.yml` and workflow contract test.
- `security-auditor`: verifies no unsafe CI shortcuts, no ignored failures, no secret/permission broadening.
- `qa-engineer-agent`: validates local gates and PR evidence quality.
- `bug-hunter`: post-open regression review, searches for missed xdist-risk signals and confirms fix targets symptom.
- `agent-coordinator`: synthesizes role outputs, updates PR body/mapping/ledger, confirms merge-readiness path.

## Live Evidence

- Gate run: `24811914187`.
- `test-main (3.12, 60)` job `72651217023` was cancelled after the coverage test step reached the 60-minute containment window.
- `test-main (3.11, 60)` job `72651217642` passed.
- `test-main (3.13, 90)` job `72651217219` passed.
- Historical failure signature: `pytest-xdist` worker node down with `Not properly terminated` in Python 3.12 main CI.

## Scope Lock

In scope:

- Preserve required job identity `test-main (3.12, 60)`.
- Preserve the existing `test-main` matrix topology.
- Run Python 3.12 `-m "not slow"` sequentially with `-p no:xdist`.
- Keep Python 3.11 parallel and Python 3.13 sequential.
- Freeze the contract in the workflow governance test.
- Record the deferred root-cause hardening follow-up in the backlog ledger.

Out of scope:

- Product/runtime behavior changes.
- Required-check topology changes.
- Broad test-suite cleanup unrelated to xdist containment.
- Frontend, Expo, Hugging Face, Life Science Research, or wellness/product work.

## Coordinator Decision

The previous mitigations kept Python 3.12 partially under xdist and did not
produce a live green main signal. This lane contains the symptom by disabling
xdist for Python 3.12 only, while preserving the same required job name and
leaving Python 3.11 parallelism intact. Root-cause xdist hardening is deferred
to a follow-up ledger item so this PR stays narrow and reversible.

## Validation Plan

- Pre-edit: `python3 scripts/orchestration/check_preflight.py`.
- Pre-edit: `python3 scripts/orchestration/check_agent_consistency.py`.
- Local: workflow contract test for main CI xdist policy.
- Local: `pre-commit run --all-files`.
- Local: `make validate-changed`.
- Local: `make verify`.
- PR: current-head GitHub CI green, with no Python 3.12 xdist worker-node failure or timeout.
- Merge readiness: review threads resolved, bot actionables mapped, and wait-window observed.
