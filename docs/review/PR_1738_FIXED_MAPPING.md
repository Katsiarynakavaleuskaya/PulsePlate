<!-- markdownlint-disable MD013 MD034 -->
# PR 1738 Fixed In Commit Mapping

- PR: <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1738>
- Branch: `codex/main-docker-proxy-security-unblock`
- Title: `fix(docker): unblock pip bootstrap through governed fallback`
- Implementing commits:
  - `d1a242507dde7ecf8f05c51582f469e929c2efce` - update the generated detect-secrets baseline for the new pinned emergency wheel digest.
  - `75d780cc3ef2b2a9300b2c9f126298b5a527b176` - route Docker pip bootstrap through the governed installer emergency fallback path.
  - `83d5da71416134807e7bf54e4a4c43ec02e8e9bc` - extend the exact emergency manifest for `requests==2.33.0`.
  - `10520d5f28b10070a3bcbd4563fc01b0a1ba8245` - harden proxy-outage classification, Docker helper cleanup, anyio fallback, and review-requested tests.
  - `4826bf69b48cb7dc327aec8bdc3434e5b73b8916` - require approved index project health before pip emergency fallback and strengthen wheel filename coverage.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

Per root `AGENTS.md` review governance, each actionable bot/human comment receives a disposition (`FIXED` / `NOT-A-BUG` / `DEFERRED`) with proof before thread resolution.

### Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1738#discussion_r3223607486 -> 10520d5f28b10070a3bcbd4563fc01b0a1ba8245
Disposition: FIXED
Commit: 10520d5f28b10070a3bcbd4563fc01b0a1ba8245
Evidence: tests/test_install_locked_python_requirements.py:135, tests/test_install_locked_python_requirements.py:182
Reason: Dockerfile coverage now checks both pip-bootstrap stages and the runtime dependency stage for the governed installer fallback contract.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1738#discussion_r3223617091 -> 10520d5f28b10070a3bcbd4563fc01b0a1ba8245
Disposition: FIXED
Commit: 10520d5f28b10070a3bcbd4563fc01b0a1ba8245
Evidence: scripts/ci/install_locked_python_requirements.py:823, tests/test_install_locked_python_requirements.py:1599
Reason: Cloudflare/proxy 521 transport failures are classified as proxy outages and do not trigger emergency wheel fallback.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1738#discussion_r3223617517
Disposition: NOT-A-BUG
Evidence: Dockerfile:55, scripts/ci/install_locked_python_requirements.py:703
Reason: `--trusted-host` remains an explicit operator-supplied build argument path that already existed before this PR; the PR does not introduce unconditional TLS bypass or a new public-index trust path.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1738#discussion_r3223617522 -> 10520d5f28b10070a3bcbd4563fc01b0a1ba8245
Disposition: FIXED
Commit: 10520d5f28b10070a3bcbd4563fc01b0a1ba8245
Evidence: docs/review/PR_1738_FIXED_MAPPING.md:16
Reason: Discussion-thread and fixed-mapping pass are now explicitly checked after the thread-specific dispositions were recorded.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1738#discussion_r3223617533 -> 10520d5f28b10070a3bcbd4563fc01b0a1ba8245
Disposition: FIXED
Commit: 10520d5f28b10070a3bcbd4563fc01b0a1ba8245
Evidence: docs/review/PR_1738_FIXED_MAPPING.md:143
Reason: Merge-readiness checklist items are unchecked until current-head CI, security scan, review disposition, and wait-window evidence exist.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1738#discussion_r3223617541 -> 83d5da71416134807e7bf54e4a4c43ec02e8e9bc
Disposition: FIXED
Commit: 83d5da71416134807e7bf54e4a4c43ec02e8e9bc
Evidence: scripts/ci/emergency_python_wheels.json:162
Reason: `requests==2.33.0` is present as an exact, pinned emergency bridge entry.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1738#pullrequestreview-4269020449 -> 10520d5f28b10070a3bcbd4563fc01b0a1ba8245
Disposition: FIXED
Commit: 10520d5f28b10070a3bcbd4563fc01b0a1ba8245
Evidence: scripts/ci/install_locked_python_requirements.py:157, scripts/ci/install_locked_python_requirements.py:874, tests/test_install_locked_python_requirements.py:135
Reason: The review's pip-spec help, invalid-constraint diagnostics, and Docker fallback-test coverage are now addressed.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1738#pullrequestreview-4269034135 -> 10520d5f28b10070a3bcbd4563fc01b0a1ba8245
Disposition: FIXED
Commit: 10520d5f28b10070a3bcbd4563fc01b0a1ba8245
Evidence: docs/review/PR_1738_FIXED_MAPPING.md:21, scripts/ci/emergency_python_wheels.json:162
Reason: CodeRabbit actionable items are mapped individually; the requested `requests==2.33.0` entry is present and the readiness checkboxes no longer overclaim.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1738#pullrequestreview-4269046049 -> 10520d5f28b10070a3bcbd4563fc01b0a1ba8245
Disposition: FIXED
Commit: 10520d5f28b10070a3bcbd4563fc01b0a1ba8245
Evidence: scripts/ci/install_locked_python_requirements.py:823, tests/test_install_locked_python_requirements.py:1599
Reason: Cubic's proxy-outage classification concern is addressed by fail-closed 521/server-error handling and a deterministic regression test.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1738#discussion_r3223627241 -> 10520d5f28b10070a3bcbd4563fc01b0a1ba8245
Disposition: FIXED
Commit: 10520d5f28b10070a3bcbd4563fc01b0a1ba8245
Evidence: scripts/ci/install_locked_python_requirements.py:823, tests/test_install_locked_python_requirements.py:1599
Reason: A 521 response with final resolver text now stays fail-closed instead of being treated as package-missing fallback eligibility.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1738#pullrequestreview-4269709547 -> 10520d5f28b10070a3bcbd4563fc01b0a1ba8245
Disposition: FIXED
Commit: 10520d5f28b10070a3bcbd4563fc01b0a1ba8245
Evidence: scripts/ci/install_locked_python_requirements.py:157, scripts/ci/install_locked_python_requirements.py:874, Dockerfile:64
Reason: The second Sourcery review's actionable help text, invalid constraint diagnostic, and Docker cleanup findings are addressed.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1738#discussion_r3224214521 -> 10520d5f28b10070a3bcbd4563fc01b0a1ba8245
Disposition: FIXED
Commit: 10520d5f28b10070a3bcbd4563fc01b0a1ba8245
Evidence: scripts/ci/install_locked_python_requirements.py:157
Reason: `--upgrade-pip-spec` help now describes the restricted numeric pip requirement forms actually accepted by the parser.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1738#discussion_r3224214527 -> 10520d5f28b10070a3bcbd4563fc01b0a1ba8245
Disposition: FIXED
Commit: 10520d5f28b10070a3bcbd4563fc01b0a1ba8245
Evidence: scripts/ci/install_locked_python_requirements.py:874
Reason: Unsupported pip upgrade constraints now include the exact rejected constraint and the original spec in the error.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1738#discussion_r3224214530 -> 10520d5f28b10070a3bcbd4563fc01b0a1ba8245
Disposition: FIXED
Commit: 10520d5f28b10070a3bcbd4563fc01b0a1ba8245
Evidence: Dockerfile:64, Dockerfile:68
Reason: The first builder pip-upgrade helper copy is removed after use, and the runtime dependency stage recopies the needed helper files before install.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1738#discussion_r3224229039 -> 10520d5f28b10070a3bcbd4563fc01b0a1ba8245
Disposition: FIXED
Commit: 10520d5f28b10070a3bcbd4563fc01b0a1ba8245
Evidence: docs/review/PR_1738_FIXED_MAPPING.md:156, docs/review/PR_1738_FIXED_MAPPING.md:158
Reason: Local validation examples use portable commands instead of machine-specific absolute interpreter paths.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1738#discussion_r3224229050 -> 10520d5f28b10070a3bcbd4563fc01b0a1ba8245
Disposition: FIXED
Commit: 10520d5f28b10070a3bcbd4563fc01b0a1ba8245
Evidence: tests/test_install_locked_python_requirements.py:135, tests/test_install_locked_python_requirements.py:182
Reason: Dockerfile guard coverage now extracts the target stages and asserts installer fallback in each relevant stage.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1738#pullrequestreview-4269725401 -> 4826bf69b48cb7dc327aec8bdc3434e5b73b8916
Disposition: FIXED
Commit: 4826bf69b48cb7dc327aec8bdc3434e5b73b8916
Evidence: tests/test_install_locked_python_requirements.py:1516, tests/test_install_locked_python_requirements.py:1559
Reason: The review-level CodeRabbit findings are covered by portable validation evidence, stage-scoped Docker guards, and the manifest-filename assertion for staged pip wheels.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1738#discussion_r3224278195 -> 4826bf69b48cb7dc327aec8bdc3434e5b73b8916
Disposition: FIXED
Commit: 4826bf69b48cb7dc327aec8bdc3434e5b73b8916
Evidence: scripts/ci/install_locked_python_requirements.py:859, tests/test_install_locked_python_requirements.py:1710
Reason: Generic pip resolver miss output can use emergency fallback only after the approved `/simple/pip/` project page passes an HTTPS health probe; suppressed 521 responses stay fail-closed.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1738#discussion_r3224278200 -> 4826bf69b48cb7dc327aec8bdc3434e5b73b8916
Disposition: FIXED
Commit: 4826bf69b48cb7dc327aec8bdc3434e5b73b8916
Evidence: docs/review/PR_1738_FIXED_MAPPING.md:21
Reason: The canonical mapping section now records concrete thread/review URLs instead of relying on a PR-root mapping entry.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1738#discussion_r3224278206
Disposition: NOT-A-BUG
Evidence: docs/review/PR_1738_FIXED_MAPPING.md:16, docs/review/PR_1738_FIXED_MAPPING.md:21
Reason: The checkboxes are intentionally checked only in the committed artifact that also includes concrete dispositions for all known actionable review threads.

## Merge Readiness

- [ ] Pre-flight + agent consistency: PASS locally on hotfix branch.
- [ ] Canonical artifact: this file.
- [ ] PR body Phase2 mirror synchronized after this artifact commit is pushed.
- [ ] Required current-head CI jobs green.
- [ ] Docker Build and Push reaches image security scan and uploads current-head evidence.
- [ ] Hidden Trivy/image findings triaged or split to a follow-up PR.
- [ ] Post-open reviewers completed (`qa-engineer-agent` -> `bug-hunter`) and actionables dispositioned.
- [ ] Mandatory wait-window after latest bot/review activity observed.

## Local Validation Evidence

- Startup gate: `python3 scripts/orchestration/check_preflight.py --path Dockerfile --path .github/workflows/build.yml --path .github/workflows/cd.yml --path .github/workflows/security.yml --path scripts/ci/install_locked_python_requirements.py --path scripts/ci/emergency_python_wheels.json --path tests/test_install_locked_python_requirements.py --path docs/roadmap/BACKLOG_LEDGER.md --path docs/review/PR_1738_FIXED_MAPPING.md` - PASS.
- Agent consistency: `python3 scripts/orchestration/check_agent_consistency.py` - PASS.
- Focused tests: `python -m pytest -q tests/test_install_locked_python_requirements.py tests/test_repo_policy_guards.py` - PASS.
- Phase2/focused security guards: `python -m pytest -q tests/test_install_locked_python_requirements.py tests/test_pr_body_phase2_gates.py tests/guards/test_nosec_policy_guard.py tests/guards/test_subprocess_uses_absolute_binaries.py` - PASS.
- Pre-commit: `pre-commit run --all-files` - PASS on the final pushed head.
- Pre-push hooks: PASS, including mypy, pip-audit, backend pre-push tests, full-repo Bandit, and docker build test.
