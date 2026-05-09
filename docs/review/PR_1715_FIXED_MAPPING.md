<!-- markdownlint-disable MD013 MD034 -->
# PR 1715 Fixed In Commit Mapping

- PR: <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1715>
- Branch: `feat/design-icon-asset-validator-v1`
- Title: `feat(design): add icon asset validator lock-mode and guard tests`
- Initial reviewed head: `9cd0bc9305f1432d94777b5ff18ceca239911728`
- Review-fix commit: `8f1eb0999`
- Status: addressed Sourcery/CodeRabbit/Cubic inline threads; canonical Phase2 artifact.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

Open review-bot actionables were triaged against current head. This artifact is the source of truth for Fixed in Commit Mapping; PR body mirrors the Phase2 checklists per repo policy.

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1715#discussion_r3212898584 -> 8f1eb0999
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1715#discussion_r3212898587 -> 8f1eb0999
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1715#discussion_r3212898589 -> 8f1eb0999
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1715#discussion_r3212899779 -> 8f1eb0999
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1715#discussion_r3212900480 -> 8f1eb0999
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1715#pullrequestreview-4257495522 -> 8f1eb0999
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1715#pullrequestreview-4257497445 -> 8f1eb0999

Disposition: FIXED

Commit: 8f1eb0999

Evidence: `scripts/validate_icon_core_v1.py` gates `assets`/`hashes` shape checks behind key presence to avoid duplicate errors with top-level required-field validation.

Evidence: `tests/test_icon_core_validator.py` adds strict-mode coverage for missing meta fields, missing asset keys, and non-object `assets`/`hashes`; aligns lock-placeholder fixture path typo to `icon_core_v1_60.png`.

Evidence: `docs/release/APPSTORE_SCREENSHOT_ASSET_GATE.md` uses “App Store assets” for consistency with App Store Connect naming.

Evidence: Aggregated Sourcery and CodeRabbit review threads (`#pullrequestreview-4257495522`, `#pullrequestreview-4257497445`) are dispositioned to the same implementation commit; inline discussion URLs above cover file-level feedback.

## Local Validation Evidence

- `python3 -m pytest tests/test_icon_core_validator.py` - PASS (venv)
- `python3 scripts/ci/check_pr_body_phase2_gates.py --pr-number 1715 --body "$(gh pr view 1715 --repo Katsiarynakavaleuskaya/PulsePlate --json body -q .body)"` - intended PASS after artifact commit and body checkbox update

## Security Notes

- Validator remains network-free and deterministic; changes are meta-shape and test coverage only.

## Risks / Rollback

- Risk: stricter strict-mode aggregation may omit shape errors when top-level keys are missing until keys are present. Mitigation: top-level required set still requires `assets`/`hashes` names.
- Rollback: revert commit `8f1eb0999` and remove this artifact if the gate contract must be relaxed.

## Deferred / Follow-ups

- None for this mapping cycle.
