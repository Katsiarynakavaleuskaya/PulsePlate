# PR #1487 — Fixed in Commit Mapping (canonical)

## Discussion Thread Pass

Canonical review-governance artifact and PR-body mirror requirements:
`AGENTS.md:42-52`; `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:41-90`;
`docs/orchestration/AGENTS.md:58-60`.

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

This artifact is created immediately after lane setup per repo governance.
Record every new review or bot disposition here before resolving threads on
GitHub.

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1487#pullrequestreview-4148025010
Disposition: FIXED
Commit: 661e88b2b
Evidence: `tests/test_install_locked_python_requirements.py:37`, `tests/test_install_locked_python_requirements.py:48`, `tests/test_install_locked_python_requirements.py:107`
Reason: Follow-up commit replaces the `StopIteration`-style manifest lookup with an explicit assertion helper and tightens the compatible-release parser so `ruff~=...` checks remain stable when requirement lines carry environment markers.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1487#pullrequestreview-4148047226
Disposition: NOT-A-BUG
Evidence: `docs/orchestration/MAINLINE_NIGHTLY_RUFF_BOOTSTRAP_REMEDIATION_PACKET_2026-04-21.md:33`, `docs/orchestration/MAINLINE_NIGHTLY_RUFF_BOOTSTRAP_REMEDIATION_PACKET_2026-04-21.md:47`, `docs/orchestration/MAINLINE_NIGHTLY_RUFF_BOOTSTRAP_REMEDIATION_PACKET_2026-04-21.md:51`
Reason: The packet intentionally follows the coordinator-approved role order for this nightly remediation lane: `architecture-specialist` stays escalation-only, while `dev-operator` may assist with evidence gathering but does not replace any reviewer in the mandatory order.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1487#discussion_r3117790513
Disposition: NOT-A-BUG
Evidence: `docs/orchestration/MAINLINE_NIGHTLY_RUFF_BOOTSTRAP_REMEDIATION_PACKET_2026-04-21.md:33`, `docs/orchestration/MAINLINE_NIGHTLY_RUFF_BOOTSTRAP_REMEDIATION_PACKET_2026-04-21.md:47`, `docs/orchestration/MAINLINE_NIGHTLY_RUFF_BOOTSTRAP_REMEDIATION_PACKET_2026-04-21.md:51`
Reason: The inline CodeRabbit packet comment asks to replace the lane-specific coordinator order with the generic Docker/CI sequence, but this remediation packet deliberately keeps `architecture-specialist` escalation-only and keeps `dev-operator` outside the mandatory reviewer order.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1487#pullrequestreview-4148140221
Disposition: FIXED
Commit: aaac4f037
Evidence: `tests/test_install_locked_python_requirements.py:26`, `tests/test_install_locked_python_requirements.py:109`, `tests/test_install_locked_python_requirements.py:119`
Reason: `_exact_requirement_pairs(...)` now strips environment markers from exact pins, and the new regression test proves `ruff==... ; marker` lines still satisfy the exact-version alignment guard.

## Merge Readiness

Merge-readiness contract:
`AGENTS.md:42-52`; `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:93-112`;
`docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:153-216`.

- [ ] Current-head CI is green for PR branch head
  Evidence: current-head `CI` run `24726549478` is still in progress on branch
  head `4897c1fe4`; `security` and `OpenAPI sync` are now green, while
  `lint` and `test-pr (3.13)` remain in flight.
- [ ] Required checks complete (no pending jobs)
  Evidence: required current-head jobs are still pending, so the final
  `check_merge_ready.py --require-auth` pass cannot be claimed yet.
- [ ] All review threads resolved on GitHub after disposition updates
  Evidence: the earlier packet thread `#discussion_r3117790513` has already
  been resolved, but the latest CodeRabbit artifact comment
  `#discussion_r3117975560` still needs final disposition handling on the next
  follow-up head.
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
  Evidence: `sourcery-ai` and the earlier CodeRabbit findings are mapped, but
  the newest CodeRabbit review `#pullrequestreview-4148257999` /
  `#discussion_r3117975560` is still actionable on this head, and `cubic`
  remains `action_required` until its status is classified.
- [ ] Pre-commit green on validated remediation head
  Evidence: local `pre-commit run --all-files` passed before pushing the
  code-bearing remediation head `2b6e65b77`; later heads are governance-only
  follow-through.
- [ ] `make verify` green on validated remediation head
  Evidence: local `make verify` passed end-to-end on code-bearing remediation
  head `2b6e65b77`; later heads are governance-only follow-through.

## Notes

- Live failure references for this lane:
  - `Nightly Full Tests` run `24704500078` (`tests` job `72254565349`)
  - `Nightly Tests` run `24704528938` (`test (1)` job `72254656999`)
- Narrow remediation scope:
  - align `requirements-dev.in`, `requirements-dev.txt`, and
    `requirements-lock.txt` to `ruff 0.15.11`
  - keep workflow YAML unchanged unless branch-head validation proves the pin
    alignment is insufficient
- Local latest-head evidence already collected:
  - `python3 scripts/orchestration/check_preflight.py` passed
  - `python3 scripts/orchestration/check_agent_consistency.py` passed
  - `pytest -q tests/test_install_locked_python_requirements.py` passed
  - `pytest -q tests/test_python_supply_chain_controls.py` passed
  - runtime-dev approved-proxy preflight passed via
    `scripts/ci/install_locked_python_requirements.py --preflight-only`
  - `pre-commit run --all-files` passed
  - `make verify` passed end-to-end
- Canonical lane packet:
  `docs/orchestration/MAINLINE_NIGHTLY_RUFF_BOOTSTRAP_REMEDIATION_PACKET_2026-04-21.md`
