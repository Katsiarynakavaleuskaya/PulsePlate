<!-- markdownlint-disable MD013 MD034 -->
# PR 1715 Fixed In Commit Mapping

- PR: <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1715>
- Branch: `feat/design-icon-asset-validator-v1`
- Title: `feat(design): add icon asset validator lock-mode and guard tests`
- Initial reviewed head: `9cd0bc9305f1432d94777b5ff18ceca239911728`
- Review-fix commit: `f16886190` (includes `474c8f0f5`, `183bc1b5d`, `3374e3a88`, `8f1eb0999`; review-bot / Cubic threads)
- Premortem / security-auditor hardening: see Evidence lines at end of **Fixed in Commit Mapping** (commit \`fix(validate): anchor repo root and harden meta.json handling\` on this branch)
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
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1715#pullrequestreview-4258427610 -> 3374e3a88
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1715#discussion_r3213807371 -> 3374e3a88

Disposition: FIXED

Commit: f16886190

Evidence: `scripts/validate_icon_core_v1.py` gates `assets`/`hashes` shape checks behind key presence to avoid duplicate errors with top-level required-field validation.

Evidence: `tests/test_icon_core_validator.py` adds strict-mode coverage for missing meta fields, missing asset keys, and non-object `assets`/`hashes`; aligns lock-placeholder fixture path typo to `icon_core_v1_60.png`.

Evidence: `docs/release/APPSTORE_SCREENSHOT_ASSET_GATE.md` uses “App Store assets” for consistency with App Store Connect naming.

Evidence: Aggregated Sourcery and CodeRabbit review threads (`#pullrequestreview-4257495522`, `#pullrequestreview-4257497445`) are dispositioned to the same implementation commit; inline discussion URLs above cover file-level feedback.

Evidence: Cubic aggregated review `#pullrequestreview-4258427610` (P2 canonical-masters vs derived files) dispositioned to `3374e3a88` (same fix as `discussion_r3213807371`).

Evidence: `183bc1b5d` removes duplicate “missing meta.json” line when `meta.json` is already listed in `missing required governance files`; covered by `test_missing_meta_json_is_single_governance_error`.

Evidence: Premortem / security-auditor closure — disposition FIXED. `scripts/validate_icon_core_v1.py` adds `_default_repo_root()` / `_resolve_repo_root()`, `ICON_CORE_SUBPATH`, and `validate(..., repo_root=)`. Resolved `core_dir` must satisfy `core_dir.relative_to(root.resolve())` or validation fails fast (path containment; blocks symlink / `--repo-root` escape).

Evidence: Premortem / security-auditor closure — CLI `--repo-root` for non-repo cwd; `META_JSON_MAX_BYTES` (256 KiB) enforced via `stat` before `json.load`; `JSONDecodeError` reported as `line` / `column` only (no full exception string).

Evidence: Premortem / security-auditor closure — `tests/test_icon_core_validator.py`: `test_meta_json_size_cap`, `test_symlinked_core_dir_outside_repo_rejected` (skip if symlinks unsupported), `test_cli_accepts_repo_root`; `test_malformed_meta_json_is_detected` asserts `JSON parse error at line` prefix; `_run_validator` uses `repo_root=tmp_root` instead of patching `CORE_DIR`.

## Local Validation Evidence

- `python3 -m pytest tests/test_icon_core_validator.py -q --noconftest` — PASS
- `python3 -m pytest tests/test_icon_core_validator.py` - PASS (venv / `--noconftest` when root conftest deps absent)
- `python3 scripts/ci/check_pr_body_phase2_gates.py --pr-number 1715 --body "$(gh pr view 1715 --repo Katsiarynakavaleuskaya/PulsePlate --json body -q .body)"` - intended PASS after artifact commit and body checkbox update

## Security Notes

- Validator remains network-free and deterministic.
- Repo-root anchoring and `meta.json` size cap reduce abuse of the gate script on shared runners or pathological inputs; no guard weakening.

## Risks / Rollback

- Risk: stricter strict-mode aggregation may omit shape errors when top-level keys are missing until keys are present. Mitigation: top-level required set still requires `assets`/`hashes` names.
- Risk: very large `meta.json` on disk could spike memory on `json.load` before strict contracts apply. Mitigation: 256 KiB cap rejects oversize files before parse.
- Rollback: revert premortem hardening commit for `validate_icon_core_v1` / tests / this artifact; revert earlier `183bc1b5d` / `3374e3a88` (and prior `8f1eb0999` if needed) only if the broader gate contract must be relaxed.

## Deferred / Follow-ups

- None for this mapping cycle.
