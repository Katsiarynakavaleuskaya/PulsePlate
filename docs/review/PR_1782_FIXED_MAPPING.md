# PR 1782 Fixed in Commit Mapping

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

Disposition: FIXED
Commit: 28ba03d8f
Evidence: scripts/orchestration/qoder_dispatch_bridge.py and tests/test_qoder_dispatch_bridge.py
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1782#discussion_r3279490497 -> 28ba03d8f

Disposition: FIXED
Commit: 90b43005c
Evidence: tests/test_pr_body_phase2_gates.py
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1782#discussion_r3279349553 -> 90b43005c

Disposition: FIXED
Commit: 90b43005c
Evidence: tests/test_pr_body_phase2_gates.py
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1782#pullrequestreview-4334787625 -> 90b43005c

Disposition: FIXED
Commit: 45fa74af9
Evidence: scripts/orchestration/qoder_dispatch_bridge.py and tests/test_qoder_dispatch_bridge.py
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1782#discussion_r3279280679 -> 45fa74af9

Disposition: FIXED
Commit: 45fa74af9
Evidence: scripts/ci/check_pr_body_phase2_gates.py and tests/test_pr_body_phase2_gates.py
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1782#discussion_r3279280688 -> 45fa74af9

Disposition: FIXED
Commit: 45fa74af9
Evidence: scripts/ci/check_pr_body_phase2_gates.py and tests/test_pr_body_phase2_gates.py
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1782#discussion_r3279280693 -> 45fa74af9

Disposition: FIXED
Commit: 45fa74af9
Evidence: scripts/ci/check_pr_body_phase2_gates.py and tests/test_pr_body_phase2_gates.py
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1782#discussion_r3279280698 -> 45fa74af9

Disposition: NOT-A-BUG
Evidence: Current HEAD places JSON reviewer roles after executable secondary roles in scripts/orchestration/qoder_dispatch_bridge.py and covers that behavior in tests/test_qoder_dispatch_bridge.py.
Reason: This Codex thread is outdated after commit 79ea81243; the current parser already preserves the reviewer tail semantics.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1782#discussion_r3279280691

Disposition: FIXED
Commit: 79ea81243
Evidence: scripts/orchestration/qoder_dispatch_bridge.py and tests/test_qoder_dispatch_bridge.py
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1782#discussion_r3279238724 -> 79ea81243

Disposition: FIXED
Commit: e49746305
Evidence: tests/test_qoder_dispatch_bridge.py
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1782#pullrequestreview-4334608995 -> e49746305

Disposition: NOT-A-BUG
Evidence: scripts/ci/check_pr_body_phase2_gates.py keeps lane-start provenance validation constants co-located with the Phase2 parser; prompt and docs wording is covered by tests/test_render_codex_start_prompt.py and tests/test_start_pr_lane.py.
Reason: Sourcery suggested a maintainability refactor/centralization. The current dry-run PR intentionally keeps the policy in the Phase2 gate and tests the generated user-facing wording for drift; extracting a shared config module is not required before this advisory signal stabilizes.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1782#pullrequestreview-4334601980

## Implementation Commits

- `90b43005c` — fixes the CodeRabbit mixed-case packet test by using an
  isolated temporary repo root.
- `28ba03d8f` — fixes the Codex review finding by making empty or fully
  no-spawn task-bootstrap JSON bridges return no roles, preserving the CLI
  fail-fast path instead of auto-injecting a coordinator-only lane.
- `45fa74af9` — fixes follow-up Codex parser findings for repeated JSON roles,
  mixed-case repo packet names, symlink-loop packet resolution, and negated
  host-preflight context.
- `79ea81243` — fixes the Codex review finding by placing task-bootstrap JSON
  reviewer roles in the tail reviewer slot so reviewer-capable slugs keep
  `CodeReview` semantics.
- `e49746305` — fixes the CodeRabbit test-fixture finding by creating the
  patched `REPO_ROOT` agent definition used by the fenced-code packet parser
  test.
- `5e17e4d372b57e1f53bbf6c011b2cbfc54e2013f` — adds lane-start provenance
  dry-run diagnostics, coordinator-first startup wording, task-bootstrap JSON
  packet dispatch parsing, and focused regression tests.

## Experiment Runner Evidence

Artifact: artifacts/orchestration/experiments/results/lane-start-provenance-oracle.json

Local artifact summary:

- `runner_mode`: `oracle_only_governance_reviewer`
- `mutated_paths`: `[]`
- `promotion_ready`: `false`
- `contribution_kind`: `experiment_design`
- `coauthor_required`: `true`
- `coauthor_reason`: Experiment Runner oracle evidence shaped the lane-start
  provenance diagnostic design, split-source correction, starter-supplement
  wording, durable packet reference, and commit decision.

## Lane Start Provenance

Packet: docs/orchestration/EXPERIMENT_RUNNER_LANE_START_PROVENANCE_PACKET_2026-05-21.md
Starter: scripts/orchestration/start_pr_lane.sh

Local bootstrap packet:

- `artifacts/orchestration/task_packets/a733b2e09986.json`

## Validation

- `python3 scripts/orchestration/check_preflight.py --path <changed paths>` — PASS
- `python3 scripts/orchestration/check_agent_consistency.py` — PASS
- `../../.venv/bin/python -m pytest tests/test_experiment_runner.py tests/test_experiment_runner_identity_policy.py tests/test_pr_body_phase2_gates.py tests/test_start_pr_lane.py tests/test_render_codex_start_prompt.py tests/test_qoder_dispatch_bridge.py -q` — PASS
- `python3 scripts/orchestration/check_experiment_runner_identity.py` — PASS
- `make validate-changed` — PASS
- `VENV_PYTHON=../../.venv/bin/python pre-commit run --all-files` — PASS
- `git diff --check` — PASS
- `python3 scripts/ci/check_pr_body_phase2_gates.py --body <fixture> --commit-range HEAD` — PASS

Full `make verify` is deferred under the operator-approved machine-heavy
exception; this lane uses PR-scoped local gates plus current-head CI parity.

## Deferred / Follow-ups

- Promote Experiment Runner Evidence and Lane Start Provenance from diagnostic
  dry-run to configurable fail-closed hard gate after this advisory signal
  stabilizes.
- Keep Experiment Runner mutation of `scripts/ci/**` for a separate
  threat-model PR with allowlist, forbidden-surface tests,
  identity/trailer checks, and rollback notes.
