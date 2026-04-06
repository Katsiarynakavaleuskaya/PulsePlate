<!-- markdownlint-disable MD034 -->
# PR 1353 — Fixed in Commit Mapping

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

Disposition: FIXED
Commit: 68e4055d
Evidence: `scripts/ci/install_locked_python_requirements.py` inserts `--no-cache-dir` immediately after the `install` subcommand (robust to future flag ordering), `install_with_guard_from_proxy` fails closed when `PULSEPLATE_DOCKER_SINGLE_PASS_LOCKED_INSTALL` is set with more than one requirements surface, `.github/workflows/build.yml` uses `continue-on-error: true` on disk-cleanup steps with `set -euo pipefail` (no shell `|| true`), `build.yml` `security-scan` grants `packages: read` and logs into GHCR before Trivy FS scan, `.github/workflows/trivy.yml` grants `packages: read`, applies the same disk-cleanup pattern, and logs into GHCR before `trivy image`, `tests/test_install_locked_python_requirements.py` locks `--no-cache-dir` placement and the single-pass multi-file rejection.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1353#discussion_r3038884405 -> 68e4055d
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1353#discussion_r3038957084 -> 68e4055d
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1353#discussion_r3038957096 -> 68e4055d
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1353#discussion_r3038957106 -> 68e4055d

Disposition: FIXED
Commit: 3dd93269
Evidence: Phase 2 checklist and mapping in this artifact aligned with `scripts/ci/check_pr_body_phase2_gates.py` contract (checkboxes and bot-comment mapping).
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1353#discussion_r3038957099 -> 3dd93269

Disposition: NOT-A-BUG
Evidence: `AGENTS.md` (CI strictness / `continue-on-error` at YAML level), `68e4055d` (concrete workflow edits above).
Reason: Sourcery aggregate review; the actionable inline thread `3038884405` is mapped to `68e4055d`.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1353#pullrequestreview-4061358914

Disposition: NOT-A-BUG
Evidence: `68e4055d` (workflow + installer evidence above).
Reason: CodeRabbit summary review; actionable inline threads `3038957084`, `3038957096`, `3038957099`, `3038957106` are mapped individually above.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1353#pullrequestreview-4061433916

Disposition: FIXED
Commit: e93cee9a
Evidence: `.github/workflows/build.yml:120`, `.github/workflows/trivy.yml:71`: `Log in to GHCR (Trivy DB)` runs only when `secrets.GHCR_READ_TOKEN` is non-empty so workflows do not fail the login step when the org secret is unavailable (e.g. forked PRs).
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1353#discussion_r3039119684 -> e93cee9a

Disposition: NOT-A-BUG
Evidence: `docs/review/PR_1353_FIXED_MAPPING.md` lists aggregate review URLs on separate `- <url>` lines per `scripts/orchestration/review_mapping_artifact.py` and CodeRabbit review `4061610776` formatting guidance.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1353#pullrequestreview-4061610776

Disposition: NOT-A-BUG
Evidence: Cubic P1 inline thread `3039119684` is covered by the FIXED mapping entry immediately above; this URL is the aggregate Cubic review only.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1353#pullrequestreview-4061616480

## Merge Readiness

- [ ] All required checks pass (GitHub CI on current PR head after each push)
- [ ] No unresolved review threads
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
- [ ] Pre-commit green
- [ ] `make verify` green locally

Notes: Resolve GitHub review threads only after disposition evidence exists. Re-run `scripts/ci/check_pr_merge_readiness.py` after push.

<!-- markdownlint-enable MD034 -->
