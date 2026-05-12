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
  - `1d2b9d6693803fd328cd39bac896dc53d22fde86` - add the exact `bandit==1.9.4` emergency wheel for CI-lite setup while the approved proxy lags.
  - `c3995510b5297a1f8971ef8f3733d25c7e779b28` - add the exact `certifi==2026.1.4` emergency wheel for CI-lite setup while the approved proxy lags.
  - `776dbef49820e86b3ddb84cc5c336ae1ef912d6c` - make the approved-index health probe honor matching `--trusted-host` semantics without widening fallback eligibility.
  - `eb369e79e2d2b322352f8cf43266a170dfebc88f` - map the trusted-host review finding and replace fragile mapping self-line references with stable section evidence.
  - `e3f5766a074f15cef2ced165fc22a8e241778172` - keep the trusted-host health-probe connection construction explicit and typed for pre-push MyPy.
  - `b3b925aaee7c402f6008c152d3c8e38d2010751e` - harden approved-proxy health probes for HTTP mirrors, redirects, real simple-index body validation, and dependency-floor preflight fallback.
  - `ec408ae79c33cd27e5ccb5a23eb2fd76827ff6dc` - use a non-blocked pip emergency artifact, accept normalized wheel names, and gate runtime fallback on resolver-miss plus approved project health.
  - `72cc39bf7d265a3e5d34af259bf0a81bedc2efd8` - tighten Docker stage extraction and direct pip-upgrade negative assertions in the Dockerfile policy test.
  - `b3c7a2a2d276d5d8477f62d98e23a6b3c47e6c7a` - allow multi-artifact fallback when at least one requested emergency artifact is named by the resolver miss while non-resolver failures remain fail-closed.

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
Evidence: docs/review/PR_1738_FIXED_MAPPING.md (Discussion Thread Pass section)
Reason: Discussion-thread and fixed-mapping pass are now explicitly checked after the thread-specific dispositions were recorded.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1738#discussion_r3223617533 -> 10520d5f28b10070a3bcbd4563fc01b0a1ba8245
Disposition: FIXED
Commit: 10520d5f28b10070a3bcbd4563fc01b0a1ba8245
Evidence: docs/review/PR_1738_FIXED_MAPPING.md (Merge Readiness section)
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
Evidence: docs/review/PR_1738_FIXED_MAPPING.md (Fixed in Commit Mapping section), scripts/ci/emergency_python_wheels.json:162
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
Evidence: docs/review/PR_1738_FIXED_MAPPING.md (Local Validation Evidence section)
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
Evidence: docs/review/PR_1738_FIXED_MAPPING.md (Fixed in Commit Mapping section)
Reason: The canonical mapping section now records concrete thread/review URLs instead of relying on a PR-root mapping entry.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1738#discussion_r3224278206
Disposition: NOT-A-BUG
Evidence: docs/review/PR_1738_FIXED_MAPPING.md (Discussion Thread Pass and Fixed in Commit Mapping sections)
Reason: The checkboxes are intentionally checked only in the committed artifact that also includes concrete dispositions for all known actionable review threads.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1738#discussion_r3226048269 -> 776dbef49820e86b3ddb84cc5c336ae1ef912d6c
Disposition: FIXED
Commit: 776dbef49820e86b3ddb84cc5c336ae1ef912d6c
Evidence: scripts/ci/install_locked_python_requirements.py:860, scripts/ci/install_locked_python_requirements.py:899, tests/test_install_locked_python_requirements.py:138
Reason: The health probe now mirrors an explicit matching `--trusted-host` when opening the approved project URL while preserving fail-closed proxy-health behavior.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1738#pullrequestreview-4271870841 -> 776dbef49820e86b3ddb84cc5c336ae1ef912d6c
Disposition: FIXED
Commit: 776dbef49820e86b3ddb84cc5c336ae1ef912d6c
Evidence: scripts/ci/install_locked_python_requirements.py:860, scripts/ci/install_locked_python_requirements.py:899, tests/test_install_locked_python_requirements.py:138
Reason: Cubic's review-level trusted-host finding is covered by the matching-host helper, probe call path, and regression test.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1738#pullrequestreview-4271982023 -> eb369e79e2d2b322352f8cf43266a170dfebc88f
Disposition: FIXED
Commit: eb369e79e2d2b322352f8cf43266a170dfebc88f
Evidence: docs/review/PR_1738_FIXED_MAPPING.md (Discussion Thread Pass, Fixed in Commit Mapping, Merge Readiness, and Local Validation Evidence sections)
Reason: CodeRabbit's fragile self-reference nit is addressed by replacing mapping-file line references with stable section-level evidence.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1738#discussion_r3226160640 -> b3b925aaee7c402f6008c152d3c8e38d2010751e
Disposition: FIXED
Commit: b3b925aaee7c402f6008c152d3c8e38d2010751e
Evidence: scripts/ci/install_locked_python_requirements.py:889, scripts/ci/install_locked_python_requirements.py:902, tests/test_install_locked_python_requirements.py:189
Reason: Approved HTTP package proxies remain eligible through `HTTPConnection`; HTTPS proxies keep the trusted-host path separate.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1738#discussion_r3226160643 -> b3b925aaee7c402f6008c152d3c8e38d2010751e
Disposition: FIXED
Commit: b3b925aaee7c402f6008c152d3c8e38d2010751e
Evidence: scripts/ci/install_locked_python_requirements.py:867, scripts/ci/install_locked_python_requirements.py:908, tests/test_install_locked_python_requirements.py:143
Reason: The health probe honors an explicitly matching trusted host before staging exact emergency artifacts.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1738#discussion_r3226160645 -> b3b925aaee7c402f6008c152d3c8e38d2010751e
Disposition: FIXED
Commit: b3b925aaee7c402f6008c152d3c8e38d2010751e
Evidence: scripts/ci/install_locked_python_requirements.py:936, tests/test_install_locked_python_requirements.py:225
Reason: Proxy health now requires a 2xx response, so redirects to login, maintenance, or canonicalization targets remain fail-closed.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1738#discussion_r3226160653 -> b3b925aaee7c402f6008c152d3c8e38d2010751e
Disposition: FIXED
Commit: b3b925aaee7c402f6008c152d3c8e38d2010751e
Evidence: scripts/ci/install_locked_python_requirements.py:1123, tests/test_install_locked_python_requirements.py:2729
Reason: Dependency-floor preflight now requires approved project health before accepting emergency artifacts after a resolver miss.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1738#discussion_r3226160656 -> b3b925aaee7c402f6008c152d3c8e38d2010751e
Disposition: FIXED
Commit: b3b925aaee7c402f6008c152d3c8e38d2010751e
Evidence: scripts/ci/install_locked_python_requirements.py:849, scripts/ci/install_locked_python_requirements.py:941, tests/test_install_locked_python_requirements.py:225
Reason: A 200 response must look like a PEP 503 project page for the requested package before fallback is allowed.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1738#discussion_r3226468084 -> ec408ae79c33cd27e5ccb5a23eb2fd76827ff6dc
Disposition: FIXED
Commit: ec408ae79c33cd27e5ccb5a23eb2fd76827ff6dc
Evidence: scripts/ci/install_locked_python_requirements.py:866, tests/test_install_locked_python_requirements.py:261
Reason: The approved-index project-page validator now accepts both normalized project names and underscore wheel filename forms such as `python_multipart-...`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1738#discussion_r3226525879 -> ec408ae79c33cd27e5ccb5a23eb2fd76827ff6dc
Disposition: FIXED
Commit: ec408ae79c33cd27e5ccb5a23eb2fd76827ff6dc
Evidence: scripts/ci/install_locked_python_requirements.py:866, tests/test_install_locked_python_requirements.py:261
Reason: The CodeRabbit duplicate of the normalized-name finding is covered by the same validator change and regression test.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1738#discussion_r3226525883 -> ec408ae79c33cd27e5ccb5a23eb2fd76827ff6dc
Disposition: FIXED
Commit: ec408ae79c33cd27e5ccb5a23eb2fd76827ff6dc
Evidence: scripts/ci/emergency_python_wheels.json:71, scripts/ci/install_locked_python_requirements.py:986
Reason: The emergency pip artifact is now `pip==26.1.1`, which satisfies the Docker `pip>=26,<27` bootstrap range without matching the blocked `pip<=26.0.1` dependency-floor schema.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1738#discussion_r3226525889 -> ec408ae79c33cd27e5ccb5a23eb2fd76827ff6dc
Disposition: FIXED
Commit: ec408ae79c33cd27e5ccb5a23eb2fd76827ff6dc
Evidence: scripts/ci/install_locked_python_requirements.py:1465, scripts/ci/install_locked_python_requirements.py:1488, tests/test_install_locked_python_requirements.py:1666
Reason: Runtime install fallback now stages emergency wheels only for exact requested artifacts whose failure is a resolver miss and whose approved project page passes health validation; transport failures stay fail-closed.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1738#pullrequestreview-4272353628 -> ec408ae79c33cd27e5ccb5a23eb2fd76827ff6dc
Disposition: FIXED
Commit: ec408ae79c33cd27e5ccb5a23eb2fd76827ff6dc
Evidence: scripts/ci/install_locked_python_requirements.py:866, tests/test_install_locked_python_requirements.py:261
Reason: Cubic's review-level simple-index validation finding is mapped to the normalized project and underscore wheel filename fix.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1738#discussion_r3226556040 -> 72cc39bf7d265a3e5d34af259bf0a81bedc2efd8
Disposition: FIXED
Commit: 72cc39bf7d265a3e5d34af259bf0a81bedc2efd8
Evidence: tests/test_install_locked_python_requirements.py:378, tests/test_install_locked_python_requirements.py:383
Reason: The Dockerfile stage helper now requires the requested `AS <stage>` alias and fails instead of matching an unnamed `FROM` stage.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1738#pullrequestreview-4272455056 -> 72cc39bf7d265a3e5d34af259bf0a81bedc2efd8
Disposition: FIXED
Commit: 72cc39bf7d265a3e5d34af259bf0a81bedc2efd8
Evidence: tests/test_install_locked_python_requirements.py:359, tests/test_install_locked_python_requirements.py:375, tests/test_install_locked_python_requirements.py:378
Reason: CodeRabbit's actionable stage-helper finding and duplicate direct-upgrade matcher finding are fixed by stage-scoped extraction and a stronger per-stage negative assertion; the baseline allowlist note is advisory scanner-noise cleanup outside this main hotfix scope.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1738#discussion_r3226775004 -> b3c7a2a2d276d5d8477f62d98e23a6b3c47e6c7a
Disposition: FIXED
Commit: b3c7a2a2d276d5d8477f62d98e23a6b3c47e6c7a
Evidence: scripts/ci/install_locked_python_requirements.py:1407, scripts/ci/install_locked_python_requirements.py:1452, tests/test_install_locked_python_requirements.py:1667
Reason: The fallback no longer requires one pip error to mention every requested emergency artifact; it requires at least one requested resolver-miss artifact, health-checks the matched package, and keeps non-resolver errors fail-closed.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1738#pullrequestreview-4272704144 -> b3c7a2a2d276d5d8477f62d98e23a6b3c47e6c7a
Disposition: FIXED
Commit: b3c7a2a2d276d5d8477f62d98e23a6b3c47e6c7a
Evidence: scripts/ci/install_locked_python_requirements.py:1512, scripts/ci/install_locked_python_requirements.py:1524, tests/test_install_locked_python_requirements.py:1739
Reason: Cubic's review-level multi-artifact fallback finding is covered by the shared resolver-miss artifact helper and runtime regression test.

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
