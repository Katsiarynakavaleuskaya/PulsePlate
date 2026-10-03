# Inline nosec TTL reassessment — 2026-09-30

<!-- markdownlint-disable MD013 -->

## Scope and current truth

One admitted security PR reconciles the September cohort and its existing executable boundaries. The cohort is frozen at `c32e61e85c9d02e7a22bd006462435eaf7bbfe7d`; all 23 source blobs were byte-identical at implementation base `b04d2eb1c9a0ea6a86dd2db18c2b5818432f97d9`. The direct accepted implementation request has SHA256 `befa0d1ac24761e124d4996c416765bd0e66933af13b75a3f51dd02244b243ce`; historical criteria-v1 preserved all 32 original criteria. Direct owner revision criteria-v3 authorized repairing/removing two avoidable B105 label-name exceptions while preserving every original record. Historical `NOSEC-TTL-20260930-criteria-v5` retains all original 32 criteria plus ten individually identified failed-main-test outcomes and the owner's approved exact 31-path scope. Criteria-v4 remains the historical preparation reference; no original requirement is removed.

The existing scanner's 53 records in 22 files omit two root conftest entries. Full finite reconciliation is **55 = 7 stale removals + 3 repairs/removals + 45 individually justified renewals**. Extra root B110 and nine future separator edits are separate. Renewing through **2026-10-30** is temporary exception handling, not vulnerability remediation or a no-findings claim.

The existing private proxy is retained without purchase, infrastructure or secrets changes. The accepted planning observation was an HTTPS project-page HTTP 200 with `tls_verify=0` (curl verification success), without credentials or a TLS bypass; this document does not refresh or extend that remote observation.

## Executable boundaries

- Settings and direct project-page reads share `_admit_private_proxy_netrc_auth`. The closed native Requests default candidate order is `.netrc`, then `_netrc`, selecting the first existing file even when it has no applicable host entry. Parsing and named/default-stanza selection remain delegated to stdlib `netrc.authenticators`, including effective login/account fallback. Primary `.netrc` retains filename-less stdlib owner/mode enforcement; explicit `_netrc` parsing follows native Requests semantics. A selected-file read/disappearance error never falls through to anonymous mode or another file. Root, password-only/indeterminate, read/parse/decode uncertainty fail closed. Applicable credentials require verified HTTPS before CLI branches, including upgrade-only, or connection/context creation. None denotes established source absence only. The claim does not cover NETRC overrides, keyring, other pip authentication/configuration or later external configuration mutation.
- Trusted authority is hostname plus optional explicit port, including bracketed IPv6; native pip mounts compare hostname case-insensitively but retain trailing-dot distinctions. Requests canonicalizes explicit URL port spelling before adapter selection, while trusted-host mounts retain literal port spelling: `:0443` trusted does not match prepared `:443`, while `:443` trusted matches URL `:0443`. A portless trusted host matches any URL port; an explicit trusted port matches only the canonical spelling of an explicitly present URL port. Missing port is not implicitly 443. Malformed authority, including delimiter-only query/fragment and control characters, is rejected.
- The existing Docker URL validator executes immediately before network access at `scripts/ci/fetch_docker_source_artifacts.py:239`; the real network opener is `scripts/ci/fetch_docker_source_artifacts.py:241`; explicit empty userinfo and port 0 are rejected by presence checks. The real opener installs the local reject-all redirect handler defined at `scripts/ci/fetch_docker_source_artifacts.py:48`; every 301/302/303/307/308 redirect fails before a second request, including otherwise allowed hosts, relative targets and scheme changes. SHA3, the 60-second timeout, cache reuse, output modes and existing filesystem restrictions remain intact. That original repair changed no source manifests, versions or review dates. The later direct-owner PCRE2 supplement below adds only the exact PCRE2/SLJIT records while preserving the existing SQLite/util-linux records and dates.
- Constructor/context/request/response/read/close failures share the existing finite probe retry budget. Raw exception details are replaced with class-only diagnostics; existing package/redacted URL context is retained and raw exception chaining is suppressed. Only successfully constructed owned connections are closed; cleanup failure cannot produce success or replace safe diagnostics with exception text.
- Root teardown uses logging with a constant message and exception class, retains best-effort cleanup and reaches gc.collect(); no exception repr/text/traceback or warnings.warn is introduced.

Evidence anchors: `scripts/ci/install_locked_python_requirements.py:1205`, `scripts/ci/fetch_docker_source_artifacts.py:63`, and `conftest.py:105`. Existing test-owner modules use real synthetic default-netrc parsing in temporary HOME directories and actual installed urllib handler dispatch with substituted transport. No permanent test module, new scanner or competing authority mechanism is introduced.

## Individual September decisions

Every original row has 2026-09-30 TTL. Each Renew row retains its original rule/reference and uses the accepted second-comment separator with 2026-10-30 TTL. The original coordinate and rationale, reviewed delta/outcome and current source anchor are individually recorded below. The generated local reconciliation is bounded advisory evidence, not a new permanent guard.

| Original coordinate | Rule | Original rationale | Outcome | Reviewed rationale and current anchor |
|---|---|---|---|---|
| `app/middleware/api_tiers.py:106` | B105 | deterministic non-production test key | Remove | Synthetic test value unchanged; ordinary Bandit needs no B105 suppression. `app/middleware/api_tiers.py:106` |
| `app/middleware/api_tiers.py:107` | B105 | deterministic non-production test key | Remove | Synthetic test value unchanged; ordinary Bandit needs no B105 suppression. `app/middleware/api_tiers.py:107` |
| `app/security/goplus_agentguard_bridge.py:16` | B404 | Required for local Node bridge to verified scanner | Renew | Required for local Node bridge to verified scanner `app/security/goplus_agentguard_bridge.py:16` |
| `app/security/goplus_agentguard_bridge.py:85` | B603 | Static argv with shutil.which('node') and fixed repo script path only | Renew | Static argv with shutil.which('node') and fixed repo script path only `app/security/goplus_agentguard_bridge.py:85` |
| `conftest.py:190` | B105 | deterministic non-production test key | Remove | Synthetic test value unchanged; ordinary Bandit needs no B105 suppression. `conftest.py:193` |
| `conftest.py:191` | B105 | deterministic non-production test key | Remove | Synthetic test value unchanged; ordinary Bandit needs no B105 suppression. `conftest.py:194` |
| `scripts/check_domain_tls.py:14` | B404 | read-only diagnostics require bounded subprocess calls | Renew | read-only diagnostics require bounded subprocess calls `scripts/check_domain_tls.py:14` |
| `scripts/check_domain_tls.py:90` | B603 | argv uses absolute binaries and fixed diagnostic flags | Renew | argv uses absolute binaries and fixed diagnostic flags `scripts/check_domain_tls.py:91` |
| `scripts/ci/check_docker_provenance_attestation.py:19` | B404 | bounded gh CLI verification is required for OCI attestation checks | Renew | bounded gh CLI verification is required for OCI attestation checks `scripts/ci/check_docker_provenance_attestation.py:19` |
| `scripts/ci/check_docker_provenance_attestation.py:106` | B603 | argv uses a resolved gh path with fixed attestation verify/download subcommands only | Renew | argv uses a resolved gh path with fixed attestation verify/download subcommands only `scripts/ci/check_docker_provenance_attestation.py:106` |
| `scripts/ci/check_docker_runtime_dependency_surface.py:18` | B404 | subprocess is required for bounded local Docker inspection | Renew | subprocess is required for bounded local Docker inspection `scripts/ci/check_docker_runtime_dependency_surface.py:18` |
| `scripts/ci/check_docker_runtime_dependency_surface.py:143` | B603 | argv uses resolved docker path with fixed run subcommand only | Renew | resolved Docker for fixed run inventory or image inspect calls; 60-second timeout and no shell `scripts/ci/check_docker_runtime_dependency_surface.py:143` |
| `scripts/ci/check_pr_merge_readiness.py:17` | B404 | bounded absolute git identity checks are required | Renew | bounded absolute git identity checks are required `scripts/ci/check_pr_merge_readiness.py:17` |
| `scripts/ci/check_pr_merge_readiness.py:380` | B603 | absolute git with fixed status argv only | Renew | absolute git with fixed status argv only `scripts/ci/check_pr_merge_readiness.py:380` |
| `scripts/ci/check_pr_merge_readiness.py:813` | B603 | absolute git with fixed rev-parse argv only | Renew | resolved Git with fixed rev-parse HEAD argv and ambient Git/replacement-object isolation `scripts/ci/check_pr_merge_readiness.py:813` |
| `scripts/ci/check_pr_size_governance.py:12` | B404 | subprocess is required for bounded local git diff execution | Renew | subprocess is required for bounded local git diff execution `scripts/ci/check_pr_size_governance.py:12` |
| `scripts/ci/check_pr_size_governance.py:550` | B603 | fixed git argv without shell for local CI routing only | Renew | resolved Git, fixed diff --numstat query and workflow revision arguments; no shell `scripts/ci/check_pr_size_governance.py:550` |
| `scripts/ci/check_pr_size_governance.py:569` | B603 | fixed git argv without shell for local CI routing only | Renew | resolved Git, fixed diff --name-status -z query and workflow revision arguments; no shell `scripts/ci/check_pr_size_governance.py:569` |
| `scripts/ci/check_release_control_plane.py:33` | B105 | release gate reason code, not credential | Renew | release gate reason code, not credential `scripts/ci/check_release_control_plane.py:33` |
| `scripts/ci/ci_risk_profile.py:15` | B404 | subprocess is required for bounded local git diff execution | Renew | subprocess is required for bounded local git diff execution `scripts/ci/ci_risk_profile.py:15` |
| `scripts/ci/ci_risk_profile.py:514` | B603 | fixed git argv without shell for local CI routing only | Renew | fixed git argv without shell for local CI routing only `scripts/ci/ci_risk_profile.py:514` |
| `scripts/ci/docker_image_telemetry.py:19` | B404 | bounded local Docker inspection is required for CI telemetry evidence | Renew | bounded local Docker inspection is required for CI telemetry evidence `scripts/ci/docker_image_telemetry.py:19` |
| `scripts/ci/docker_image_telemetry.py:86` | B603 | argv uses resolved docker path with fixed inspect/history subcommands only | Renew | argv uses resolved docker path with fixed inspect/history subcommands only `scripts/ci/docker_image_telemetry.py:86` |
| `scripts/ci/fetch_docker_image_baseline.py:16` | B404 | bounded gh CLI calls are required to fetch workflow artifacts for CI telemetry | Renew | bounded gh CLI calls are required to fetch workflow artifacts for CI telemetry `scripts/ci/fetch_docker_image_baseline.py:16` |
| `scripts/ci/fetch_docker_image_baseline.py:54` | B603 | argv uses a resolved gh path with fixed GitHub API/auth subcommands only | Renew | argv uses a resolved gh path with fixed GitHub API/auth subcommands only `scripts/ci/fetch_docker_image_baseline.py:54` |
| `scripts/ci/fetch_docker_image_baseline.py:183` | B603 | argv uses resolved gh path with fixed artifact-download subcommand only | Renew | resolved gh with fixed workflow-artifact API argv, temporary archive and bounded timeout; no shell `scripts/ci/fetch_docker_image_baseline.py:183` |
| `scripts/ci/fetch_docker_source_artifacts.py:175` | B310 | URL is manifest-pinned to approved HTTPS hosts and SHA3-verified | Repair/remove | Boundary URL revalidation and real no-redirect opener; SHA3, timeout and filesystem/cache controls retained. `scripts/ci/fetch_docker_source_artifacts.py:239`, `scripts/ci/fetch_docker_source_artifacts.py:241` |
| `scripts/ci/install_locked_python_requirements.py:1503` | B323 | mirrors explicit operator `--trusted-host` semantics for this health probe only | Renew | explicit anonymous trusted-host probe only; selected default .netrc/_netrc credentials require verified HTTPS before context creation `scripts/ci/install_locked_python_requirements.py:1577` |
| `scripts/metatron_lab/compose_guard.py:6` | B404 | operator-only docker compose config -q; argv from fixed tokens + docker via shutil.which | Renew | operator-only docker compose config -q; argv from fixed tokens + docker via shutil.which `scripts/metatron_lab/compose_guard.py:6` |
| `scripts/metatron_lab/compose_guard.py:46` | B603 | no shell; argv is docker + fixed compose flags + repo compose path | Renew | no shell; argv is docker + fixed compose flags + repo compose path `scripts/metatron_lab/compose_guard.py:46` |
| `scripts/orchestration/check_codex_ollama_operator.py:17` | B404 | required for bounded local CLI version checks | Renew | required for bounded local CLI version checks `scripts/orchestration/check_codex_ollama_operator.py:17` |
| `scripts/orchestration/check_codex_ollama_operator.py:71` | B603 | argv uses shutil.which-resolved absolute binaries | Renew | argv uses shutil.which-resolved absolute binaries `scripts/orchestration/check_codex_ollama_operator.py:71` |
| `scripts/orchestration/check_codex_ollama_operator.py:280` | B310 | URL is validated as localhost http(s) immediately before use | Remove | Existing validated localhost opener already rejects redirects; ordinary Bandit needs no B310 suppression. `scripts/orchestration/check_codex_ollama_operator.py:278` |
| `scripts/orchestration/check_merge_ready.py:10` | B404 | wrapper executes fixed repo scripts only | Renew | bounded repo gates and read-only gh metadata/auth require subprocess `scripts/orchestration/check_merge_ready.py:10` |
| `scripts/orchestration/check_merge_ready.py:118` | B603 | fixed interpreter/script paths; args validated by parser | Renew | fixed interpreter/script paths; args validated by parser `scripts/orchestration/check_merge_ready.py:118` |
| `scripts/orchestration/check_merge_ready.py:158` | B603 | absolute gh path with fixed auth-status argv | Renew | absolute gh path with fixed auth-status argv `scripts/orchestration/check_merge_ready.py:158` |
| `scripts/orchestration/check_merge_ready.py:187` | B603 | absolute gh path with fixed read-only argv | Renew | absolute gh path with fixed read-only argv `scripts/orchestration/check_merge_ready.py:187` |
| `scripts/orchestration/check_merge_ready.py:241` | B603 | absolute gh path with fixed auth-status argv | Renew | absolute gh path with fixed auth-status argv `scripts/orchestration/check_merge_ready.py:241` |
| `scripts/orchestration/check_preflight.py:13` | B404 | fixed git commands only, no user input | Renew | fixed Git checks and current-interpreter consistency gate require subprocess `scripts/orchestration/check_preflight.py:13` |
| `scripts/orchestration/check_preflight.py:78` | B603 | fixed git commands only | Renew | resolved Git or sys.executable with fixed repo consistency script and bounded argv; no shell `scripts/orchestration/check_preflight.py:78` |
| `scripts/orchestration/creative_pilot_workspace_contract.py:16` | B404 | bounded Git object reads require subprocess | Renew | bounded Git object reads require subprocess `scripts/orchestration/creative_pilot_workspace_contract.py:16` |
| `scripts/orchestration/creative_pilot_workspace_contract.py:927` | B603 | absolute Git binary with validated bounded argv | Renew | absolute Git binary with validated bounded argv `scripts/orchestration/creative_pilot_workspace_contract.py:927` |
| `scripts/orchestration/pr_review_closeout.py:16` | B404 | bounded absolute git commands are required | Renew | bounded absolute git commands are required `scripts/orchestration/pr_review_closeout.py:16` |
| `scripts/orchestration/pr_review_closeout.py:203` | B603 | argv starts with resolved git and fixed subcommands | Renew | resolved Git with fixed graft-path lookup, sanitized environment and 30-second timeout `scripts/orchestration/pr_review_closeout.py:203` |
| `scripts/orchestration/pr_review_closeout.py:229` | B603 | argv starts with resolved git and fixed subcommands | Renew | resolved Git, fixed local object/status/hash callers, sanitized environment and 30-second timeout `scripts/orchestration/pr_review_closeout.py:229` |
| `scripts/orchestration/pr_review_evidence.py:17` | B404 | fixed absolute git only | Renew | fixed absolute git only `scripts/orchestration/pr_review_evidence.py:17` |
| `scripts/orchestration/pr_review_evidence.py:1481` | B603 | absolute git plus validated fixed argv | Renew | resolved Git with bounded object/diff callers, sanitized environment, graft checks and timeout `scripts/orchestration/pr_review_evidence.py:1481` |
| `scripts/orchestration/pr_review_evidence.py:1505` | B603 | absolute git plus validated fixed argv | Renew | resolved Git with fixed ancestry query, checked identities, sanitized environment and shallow/graft rejection `scripts/orchestration/pr_review_evidence.py:1505` |
| `scripts/orchestration/pr_review_evidence.py:1525` | B603 | absolute git plus fixed argv | Renew | resolved Git with fixed graft-path lookup, sanitized environment and 30-second timeout `scripts/orchestration/pr_review_evidence.py:1525` |
| `scripts/orchestration/pr_review_evidence.py:1559` | B603 | absolute git plus fixed argv | Renew | resolved Git with fixed shallow-path lookup, sanitized environment and 30-second timeout `scripts/orchestration/pr_review_evidence.py:1559` |
| `scripts/orchestration/pr_review_evidence.py:1626` | B603 | absolute git plus validated fixed argv | Renew | resolved Git with fixed parent-object read, checked commit, sanitized environment and 30-second timeout `scripts/orchestration/pr_review_evidence.py:1626` |
| `scripts/orchestration/review_mapping_artifact.py:33` | B105 | doc heading | Repair/remove | Private name `DISCUSSION_THREAD_HEADING` avoids the B105 heuristic; exact label and inverse-rename AST preserved. `scripts/orchestration/review_mapping_artifact.py:33` |
| `scripts/orchestration/review_mapping_artifact.py:37` | B105 | checkbox label | Repair/remove | Private name `CHECKBOX_DISCUSSION_COMPLETED` avoids the B105 heuristic; exact label and inverse-rename AST preserved. `scripts/orchestration/review_mapping_artifact.py:37` |
| `tests/test_vip_coverage_additional.py:32` | B105 | deterministic non-production test key | Remove | Synthetic test value unchanged; ordinary Bandit needs no B105 suppression. `tests/test_vip_coverage_additional.py:32` |
| `tests/test_vip_coverage_additional.py:36` | B105 | deterministic non-production test key | Remove | Synthetic test value unchanged; ordinary Bandit needs no B105 suppression. `tests/test_vip_coverage_additional.py:36` |

## Ancillary changes and parity

The undated root B110 at original `conftest.py:115` is separately removed by executable constant/class logging. Synthetic keys, public document labels and the numeric release reason remain unchanged; root key lines retain independent `pragma: allowlist secret` comments. Current AST evidence distinguishes 18 genuinely comment-only cohort files, one narrowly projected type-only domain-diagnostic repair, and one exact inverse-rename identity for the two local mapping-helper symbols. The three runtime behavior repairs remain installer, fetcher and root teardown; the additional diagnostic cast preserves values under its existing native internet-family contract.

The nine following annotations change only `# nosec Bxxx:` to `# nosec Bxxx # Bxxx:`. Rule, explanation, reference and TTL are otherwise exact; eight October 31 and one December 31 dates are retained.

| Original coordinate | Preserved TTL |
|---|---|
| `scripts/ci/check_pr_merge_readiness.py:845` | 2026-10-31 |
| `scripts/ci/check_pr_size_governance.py:124` | 2026-10-31 |
| `scripts/ci/install_locked_python_requirements.py:19` | 2026-10-31 |
| `scripts/ci/install_locked_python_requirements.py:73` | 2026-12-31 |
| `scripts/ci/install_locked_python_requirements.py:751` | 2026-10-31 |
| `scripts/ci/install_locked_python_requirements.py:893` | 2026-10-31 |
| `scripts/ci/install_locked_python_requirements.py:1782` | 2026-10-31 |
| `scripts/ci/install_locked_python_requirements.py:1810` | 2026-10-31 |
| `scripts/ci/install_locked_python_requirements.py:1903` | 2026-10-31 |

## Validation observations

Pre-implementation nosec/subprocess/repository-policy guards passed. The first complete focused run of both existing test-owner modules exited 0. Subsequent required validation caught a temporary syntax error from deleting the Ollama comment at the first parenthesis in `http(s)`; it was corrected before publication. Its raw failing Bandit JSON/stderr and focused log are preserved locally. Bandit exit 0 never substitutes for an empty JSON errors array and complete file inventory.

A later combined run retained both that syntax failure and an existing route-manifest child-process 30-second TimeoutExpired: 2 failed, 428 passed in 529.32s. The targeted rerun and final repaired-material observations follow below. No guard is skipped or weakened and no new readiness claim follows this failed run.

<!-- implementation-terminal-evidence -->
The repaired-material focused command was `../../.venv/bin/python -B -m pytest -o addopts='' -q -p no:cacheprovider tests/test_install_locked_python_requirements.py tests/test_docker_workflow_build_path_contract.py` (exit **0**). Raw terminal stdout:

```text
351 passed in 120.70s (0:02:00)
```

The failed-gate rerun was `../../.venv/bin/python -B -m pytest -o addopts='' -q -p no:cacheprovider 'tests/test_repo_policy_guards.py::test_registration_authority_live_manifest_rejects_drift[foreign_duplicate]' tests/guards/test_nosec_policy_guard.py tests/guards/test_subprocess_uses_absolute_binaries.py` (exit **0**). Raw terminal stdout:

```text
43 passed in 85.73s (0:01:25)
```

The preserved earlier combined required run exited **1**. Raw terminal summary, retained in the local implementation-focused-final log:

```text
FAILED tests/guards/test_subprocess_uses_absolute_binaries.py::test_subprocess_requires_absolute_or_which_resolved_binary
FAILED tests/test_repo_policy_guards.py::test_registration_authority_live_manifest_rejects_drift[foreign_duplicate]
2 failed, 428 passed in 529.32s (0:08:49)
```

The source defect pointer was `scripts/orchestration/check_codex_ollama_operator.py:280:SyntaxError`; removal truncated at `http(s)`, and the repaired source now parses with the other 22 files and preserves its base AST. The separate child-process `tests/test_repo_policy_guards.py:862:TimeoutExpired` received the exact targeted rerun above. Neither failure is ignored; historical pre-repair Bandit reports remain retained and are not current evidence.

The production/root Bandit command was `../../.venv/bin/python -B -m bandit -q -f json app/middleware/api_tiers.py app/security/goplus_agentguard_bridge.py conftest.py scripts/check_domain_tls.py scripts/ci/check_docker_provenance_attestation.py scripts/ci/check_docker_runtime_dependency_surface.py scripts/ci/check_pr_merge_readiness.py scripts/ci/check_pr_size_governance.py scripts/ci/check_release_control_plane.py scripts/ci/ci_risk_profile.py scripts/ci/docker_image_telemetry.py scripts/ci/fetch_docker_image_baseline.py scripts/ci/fetch_docker_source_artifacts.py scripts/ci/install_locked_python_requirements.py scripts/metatron_lab/compose_guard.py scripts/orchestration/check_codex_ollama_operator.py scripts/orchestration/check_merge_ready.py scripts/orchestration/check_preflight.py scripts/orchestration/creative_pilot_workspace_contract.py scripts/orchestration/pr_review_closeout.py scripts/orchestration/pr_review_evidence.py scripts/orchestration/review_mapping_artifact.py` (exit **0**). The already-governed test profile was `../../.venv/bin/python -B -m bandit -q -f json --skip B101,B112 tests/test_vip_coverage_additional.py` (exit **0**). Both JSON reports contain raw `"errors": []` and `"results": []`; neither has malformed annotation warnings. No extra production skip or exclusion is added.

The separate plain all-23 diagnostic exits **1** with exactly **25 B101** test assertions; unsuppressed all-23 exits **1** with **81** findings. Both have empty parse-error inventories. Production/plain stderr retains **19** existing node-level “nosec encountered (B105), but no failed test” warnings around the retained numeric reason-code dictionary. They are distinct from the eliminated prose-as-rule parser warnings, which are **0**. These diagnostics are retained separately from the required existing-profile success and do not establish provider review, scan approval or repository-wide safety.

Before the later required MyPy repair, the bounded reconciliation command was `../../.venv/bin/python -B artifacts/orchestration/nosec_ttl_20260930/reconcile_implementation.py` (exit **0**). This ignored one-time finite evidence helper compares the exact base ASTs and preserved source annotations; it is not a new permanent scanner or authority mechanism. The following original stdout is historical; the current 19-plus-one result appears in the MyPy correction below:

```text
PASS: cohort 55 = 7 removals + 1 repair/removal + 47 renewals
PASS: AST equality for 20 comment-only source files; syntax checked for all 23
PASS: nine future separators only; eight October 31 and one December 31 TTLs preserved
```

The bounded synthetic teardown probe exited **0**, observed exactly one garbage-collection call and captured:

```text
PASS: root cleanup is nonfatal, constant/class-only and reaches gc.collect()
Best-effort database cleanup failed (RuntimeError)
```

Black check and Ruff check passed for the executable/test surface; `../../.venv/bin/python -B scripts/ci/check_docs_phase1_gates.py --files docs/security/INLINE_NOSEC_TTL_20260930_REASSESSMENT.md` exited **0** with raw `phase1-docs-gates: passed.` Coordinator-final execute preflight and agent consistency also passed, with raw `PASS: task scope isolated`, `PASS: routing readiness`, and `OK: agent docs and files are consistent.` Their full scoped invocations and logs are retained in the existing lane evidence. Required make validate-changed, all-files hooks, current-head CI and subsequent lifecycle evidence remain coordinator-owned.

### Hook recovery and instruction attribution

The first material-commit attempt was blocked by stock detect-secrets on the synthetic Basic Auth URI at `tests/test_docker_workflow_build_path_contract.py:783`; its raw failure remains in `material-commit.log`. The same existing fixture now uses username-only userinfo, preserving rejection before transport without a password-like token. The affected matrix passed with raw `8 passed in 3.66s`; no new pragma, allowlist or secret fingerprint was added.

The cache interruption left only the owned unstaged `scripts/AGENTS.md` patch in pre-commit's stash. Its verified SHA256 was `24c44e0ab2434000ffd5925a4ba75230c795f2202dbdc09860d9bbfd0172d0e7`; `git apply --check` passed before restoration, and staged material remained unchanged. A later stock hook regenerated only four root-conftest line coordinates (188→191, 189→192, 213→216, 214→217) and `generated_at`. The local `baseline-hook-receipt.json` records unchanged fingerprints, secret dispositions and 117 result-file entries. This generated baseline update was committed separately as `8ea1c7b5413e05b72e8cd038ff8a19d34f575d3d` (`chore(pre-commit): apply hook fixes`).

The coordinator's learning-helper run records raw `24 passed in 8.99s`. Commit `052ca397ea20273093cd80e716371f147264ba67` (`docs(agents): document bounded transport and scan evidence`) includes the small scoped lesson to verify Bandit JSON errors/expected file inventory and AST equality for comment-only edits. At that recovery checkpoint, the source-material commit had not restarted. Source material is now committed as `d0f40df81576e0e9d23befb9628c013c9c7a6be0`; normal commit hooks passed, including backend-tests and detect-secrets. Required `make validate-changed`, all-files pre-commit and a refreshed oracle proceed on our current material now, with current-head GitHub checks and later lifecycle gates still required. Refresh affected evidence if a new base arrives; commit-hook success alone does not establish readiness.

### Required MyPy correction on the admitted diagnostic

The initial ordinary push failed its required MyPy gate before publication. Raw `initial-push.log` evidence includes:

```text
scripts/check_domain_tls.py:128: error: Argument 1 to "sorted" has incompatible
type "set[str | int]"; expected "Iterable[str]"  [arg-type]
Found 1 error in 1 file (checked 21 source files)
```

`_collect_dns_answers` invokes `_socket_answers` only for AF_INET/AF_INET6. Installed socket typeshed includes a generic `tuple[int, bytes]` alternative that explains the inferred union; these existing internet-family callers use native string-address tuples. The same admitted diagnostic now imports `typing.cast` and uses only `cast(str, item[4][0])` in its existing comprehension. Installed stdlib cast returns its input unchanged; there is no filtering, conversion, dropped uncertain value, type ignore or new permanent test module.

The focused command `../../.venv/bin/python -B -m mypy scripts/check_domain_tls.py` exited **0**, with raw `Success: no issues found in 1 source file`. The existing owner suite command `../../.venv/bin/python -B -m pytest -o addopts='' -q -p no:cacheprovider tests/test_check_domain_tls.py` exited **0**, with raw `9 passed in 10.20s`.

The ignored one-time command `../../.venv/bin/python -B -m artifacts.orchestration.nosec_ttl_20260930.socket_typing_probe` exited **0**. It compares original/current sorting, duplicates and gaierror output for both existing families, observes numeric-only native sockaddr values, and checks cast object identity. Raw stdout:

```text
PASS: AF_INET sorting, duplicate removal, gaierror and native numeric string sockaddr
PASS: AF_INET6 sorting, duplicate removal, gaierror and native numeric string sockaddr
PASS: typing.cast returns the original object; no filtering, coercion or dropped values
```

The updated ignored reconciliation command above exited **0**. It permits exactly one `from typing import cast` and one scoped `cast(str, item[4][0])` wrapper, removes only those in its finite AST projection, and requires the whole remaining file AST to equal exact base. All permanent guards remain unchanged. Current raw stdout includes:

```text
PASS: AST equality for 19 comment-only source files; syntax checked for all 23
PASS: domain resolver whole-file AST equals base after only one cast import and one exact cast projection
PASS: nine future separators only; eight October 31 and one December 31 TTLs preserved
```

At that historical MyPy checkpoint, the 55-record outcomes, nine future annotations, three behavior repairs and then-admitted 30-path cap remained unchanged. The subsequent main-test scope revision and projected 31-path publication boundary are recorded below; this focused repair was not current-head CI or publication proof.

## Current-head inline review repairs

Two actual inline findings on material head `08b9b1b0641ee9064c4132e9b7f2467b1475b7d2` invalidated the earlier bounded clean assessment. The owner explicitly authorized both safe fixes and revised numeric criteria to **55 = 7 stale removals + 3 repairs/removals + 45 retained exceptions**. Original criteria and historical raw observations remain retained; the current source outcome table above records every original coordinate under that revision. No review mapping or thread resolution preceded these fixes.

- [P1 default `_netrc` fallback](https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2463#discussion_r4146294495): installed pip-vendored Requests searches `.netrc`, then `_netrc`, selecting the first existing candidate. The earlier filename-less stdlib call omitted `_netrc`, allowing its credentials through unsafe CLI admission. The existing shared helper now selects the same closed default candidates before settings/direct admission. First-file precedence is preserved even if that file has no applicable authenticator; indeterminate selection or selected-file read/disappearance errors fail closed with constant/class-only output. Stdlib owns parsing and machine/default/account selection; primary `.netrc` retains its existing filename-less permission checks, while explicit `_netrc` parsing follows native Requests semantics. Evidence: `scripts/ci/install_locked_python_requirements.py:1435`, `tests/test_install_locked_python_requirements.py:827`.
- [P2 avoidable B105 labels](https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2463#discussion_r4146294490): the two private symbols are renamed to `DISCUSSION_THREAD_HEADING` and `CHECKBOX_DISCUSSION_COMPLETED`, their suppressions are removed, and all local references follow the rename. Exact rendered values remain unchanged. Whole-file AST equality after only the two inverse local renames proves the bounded identity; this is not an authority or parser behavior change. Evidence: `scripts/orchestration/review_mapping_artifact.py:33`, `scripts/orchestration/review_mapping_artifact.py:37`.

The local native-source command `../../.venv/bin/python -B artifacts/orchestration/nosec_ttl_20260930/native-default-netrc-proof.py` exited **0**. Raw stdout includes:

```text
Native Requests NETRC_FILES: ('.netrc', '_netrc')
Native Requests: first existing default candidate; login-or-account authentication
Stdlib: filename-less .netrc preserves default owner/mode checks
```

The refreshed focused command `../../.venv/bin/python -B -m pytest -o addopts='' -q -p no:cacheprovider tests/test_install_locked_python_requirements.py tests/test_review_mapping_artifact.py tests/guards/test_nosec_policy_guard.py tests/guards/test_subprocess_uses_absolute_binaries.py` exited **0**. Raw stdout:

```text
429 passed in 119.38s (0:01:59)
```

The synthetic temporary-HOME tests exercise both candidate filenames, named/default login/account, root/indeterminate rejection, HTTP/matching trusted HTTPS refusal before every CLI branch and direct connection/context, verified HTTPS, absent/unrelated authenticators, first-existing precedence, primary permissions, selected-file parse/read/disappearance failures and selection uncertainty. No real operator credentials, skipped check or new permanent test module is used.

Refreshed Bandit repeats the exact production/root22, existing test1 profile, plain23 and unsuppressed23 commands recorded above against the repaired material. Commands and raw JSON/stderr remain in the owned local `bandit-review-fix-*` artifacts. Production/root22 and test1 each exit **0**, with exact expected file inventories and raw `"errors": []`, `"results": []`. Plain23 remains a distinct diagnostic **exit 1**, **25 B101** assertions; unsuppressed23 remains diagnostic **exit 1**, now **79** findings after two B105 removals. Every profile has zero parse omissions/errors and zero malformed-rule explanation warnings; the existing reason-code node-level warnings remain a separate observation.

The refreshed reconciliation command `../../.venv/bin/python -B artifacts/orchestration/nosec_ttl_20260930/reconcile_implementation.py` exited **0**. Raw stdout includes:

```text
PASS: cohort 55 = 7 removals + 3 repair/removals + 45 renewals
PASS: AST equality for 18 comment-only source files; syntax checked for all 23
PASS: mapping helper whole-file AST equals base after only the two inverse local renames
```

The same reconciliation independently retains the exact domain cast projection and all nine future separator-only annotations. Black/Ruff checks pass on the three changed Python files. These targeted observations cover the new material; prior broad local hooks, hosted CI, oracle, self-review and seal evidence do not automatically transfer to it. The fixes are not yet commit-bound review dispositions; coordinator-owned broader gates, publication and closeout remain separate.

## Premortem and Experiment Runner

The coordinator's actual-diff premortem reviewed all 28 admitted paths against the unchanged 32-criterion reference. Its local record is `artifacts/orchestration/nosec_ttl_20260930/premortem-actual-diff.md`. The proceed decision retains every later gate and grants no readiness or merge authority.

- **PM-NOSEC-01 — annotation-removal syntax defect:** repaired in working material at the existing Ollama opener statement. All 23 source files parse, and the affected nosec/subprocess plus exact timeout-case rerun passes with 43 tests. The original 20-comment-only AST observation is retained historically above; that checkpoint had 19 comment-only files plus the exact runtime-identity type projection described in the required MyPy correction; the later two safe mapping-helper renames reduce current comment-only parity to 18 plus the exact inverse-rename identity. Historical failed output is retained; process exit alone never proves complete scan coverage. Ordinary material commit identity will supply commit-bound FIXED proof.
- **PM-NOSEC-02 — delimiter-only trusted authority:** repaired in the existing matcher by requiring parsed netloc equality with the admitted authority. Five added malformed-authority cases are included in the 351-test passing owner run. Ordinary material commit identity will supply commit-bound FIXED proof.
- The real-opener redirect dispatch and bounded connection/cleanup diagnostics were assessed as NOT-A-BUG for the reviewed implementation, with the executable 351-test run, one-request assertions and observed root garbage collection as evidence. These are bounded findings/dispositions, not a general security or no-findings claim.

The strict oracle-only Experiment Runner result `artifacts/orchestration/experiments/results/nosec-ttl-20260930-complete-oracle.json` is **accepted**, experiment **exp-6ef749e4ec2a**. Execution used the existing Apple Container backend, image `sha256:5b3abbad998dc1b23f9d99e72a8fde931558401b81a2aec8c5eeeff90b128a70`, with passed preflight and `apple_internal_no_dns_plus_linux_unshare` network isolation. The recorded network budget is **0**; two configured commands executed in one attempt with zero retries. The result applies the complete 28-path source diff, records `mutated_paths: []` and `shared_tree_untouched: true`, and leaves `promotion_ready: false`.

Both exact guest commands ran in `/workspace`, returned **0**, had empty stderr and were neither timed out nor truncated. The counts below are taken from their actual passing-progress dots in the retained JSON stdout: **265 + 128 = 393** observed oracle cases.

| Exact guest command | Return code | Observed cases |
|---|---|---|
| `python -m pytest -q tests/test_install_locked_python_requirements.py` | 0 | 265 |
| `python -m pytest -q tests/test_docker_workflow_build_path_contract.py tests/guards/test_nosec_policy_guard.py tests/guards/test_subprocess_uses_absolute_binaries.py` | 0 | 128 |

The earlier result `nosec-ttl-20260930-oracle.json` was rejected as a capability mismatch (`host_listener_unavailable`) before any oracle command or test executed. The canonical host probe was restored. The subsequent six-path context result `nosec-ttl-20260930-oracle-restored.json` was rejected as a policy violation before any oracle command executed. Neither rejected attempt supplies test evidence. The accepted context uses the supported tracked `scripts/ci` directory plus the other exact paths and covers all 28 source-diff paths; `oracle-context-selection-v2.json` records this choice. Governing scope and validators remain unchanged, with no fabricated CV metadata or excluded material.

The accepted artifact records `coauthor_required: true`, contribution `oracle_review`: the oracle materially shaped the engineering decision. Material commits therefore require the canonical public attribution trailer:

```text
Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>
```

This oracle supplies its observed isolated test results and procedural evidence only. Required `make validate-changed`, all-files pre-commit, current-head GitHub checks, post-open role execution, final-material review/seal and separate human merge approval remain pending and distinct.

## Separately owned main image remediation and base watch

Coordinator-saved Docker run **36683691099**, job **109784592483**, and CD run **36683691096**, job **109785230250**, at main `b04d2eb1c9a0ea6a86dd2db18c2b5818432f97d9` report **CVE-2026-84782** for **libssl3/openssl 3.0.22-1~deb12u1**, with an empty scanner fixed-version value. These historical main/image/CD observations belong to the separately owned Security/SRE remediation rail; this inline-nosec PR does not fix them. No causality from PR #2462 or a scanner-database change is established.

The [Debian primary tracker](https://security-tracker.debian.org/tracker/CVE-2026-84782), [exact Docker job](https://github.com/Katsiarynakavaleuskaya/PulsePlate/actions/runs/36683691099/job/109784592483) and [exact CD job](https://github.com/Katsiarynakavaleuskaya/PulsePlate/actions/runs/36683691096/job/109785230250) are separate-lane source/evidence references. Saved observations are not fresh upstream-status verification. The [separate remediation ledger item](../roadmap/BACKLOG_LEDGER.md#ledger-p1-main-openssl-cve-2026-84782) retains its owner's terminal image proof. Historical red main/CD is not an independent merge blocker for our PR under the latest direct owner clarification. Our actual required current-head checks, security bundle, findings/dispositions and separate exact-head merge approval remain mandatory; no gate is waived and no foreign remediation ownership transfers here.

Docker/CVE remediation was assigned to [PR #2447](https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2447), owned by the Prometheus T0-1 closeout chat `01a0def6-7596-7a41-95e7-0ccf8ce90f58`. The earlier OPEN/base-watch observation is historical. The coordinator's authenticated 2026-10-01 snapshot records **MERGED** at `2026-10-01T17:14:09Z`, merge commit `5338465ad08d4a0c8da6ffa9d65dce9d8dbea985`. This lane adopted that fetched main through ancestry-preserving merge `16ddaf8eb26aae5ed39e18595e859076b9619d6a`, without waiting for green main CI; all 23 owned cohort source blobs remained unchanged from prior head `4acce289f04d7e12e74cf879535a488edd14ba5f`. At that historical checkpoint, the owner classified the separately owned Docker/CD failure as nonblocking for our work and merge. The later direct instruction admits the new PCRE2 finding and requires fully passing applicable Docker gates. Adoption proves neither Docker PASS nor current-main health. All original 32 criteria and the ten newly admitted main-test outcomes remain required. No scheduled heartbeat is restored.

## Separately owned urllib3 handoff

The direct owner instruction withdrew Python urllib3 from this PR before any dependency edits and assigned it to the Prometheus T0-1 closeout chat `01a0def6-7596-7a41-95e7-0ccf8ce90f58`. The coordinator sent the authorized evidence handoff. The earlier unconfirmed implementation identity is historical: the owning PR is now merged #2447, merge commit `5338465ad08d4a0c8da6ffa9d65dce9d8dbea985`, adopted by this lane at `16ddaf8eb26aae5ed39e18595e859076b9619d6a`. urllib3 **2.8.0** arrives solely from that upstream merge; this lane authored no dependency change. The original inline-nosec packet and owner-revised `55 = 7 + 3 + 45` scope continue; no withdrawn dependency admission was executed.

The saved [canonical security job](https://github.com/Katsiarynakavaleuskaya/PulsePlate/actions/runs/36734183242/job/109953943533) at historical head `08b9b1b0641ee9064c4132e9b7f2467b1475b7d2` reports urllib3 **2.7.0** with **CVE-2026-97687**, **CVE-2026-97688** and **CVE-2026-97689** in four audited lock profiles. This retained failure is distinct from Docker/OpenSSL. After upstream 2.8.0 adoption, the coordinator ran `pre-commit run pip-audit --hook-stage pre-push --all-files` after `. ../../.venv/bin/activate`; the installed required hook completed with exit **0** on the adopted lock material. Retained raw `main533-pip-audit-hook.log` contains `pip-audit (pip vulns)....................................................Passed`. This local hook observation does not establish unpublished hosted-CI or main-security terminal success. The [handoff ledger entry](../roadmap/BACKLOG_LEDGER.md#ledger-p1-urllib3-prometheus-handoff-20260930) preserves the concrete implementation identity and remaining owning-rail terminal validation requirement. No dependency material or suppression change was authored in this lane.

## Adopted-main registry guard correction

Canonical main run **36897887285** at `5338465ad08d4a0c8da6ffa9d65dce9d8dbea985` had ten distinct failed pytest nodes: the NOSEC guard and nine registry-policy nodes. The retained exact-ten-node local baseline at adopted head `16ddaf8eb26aae5ed39e18595e859076b9619d6a` exited **1**: NOSEC passed after adoption, while the nine registry nodes failed. Five positives reached the stale parent digest, two rawHTML negatives were masked by that earlier failure, and two suppression mutations had no current target. Raw baseline lines:

```text
.FFFFFFFFF                                                               [100%]
E     Expected regex: 'Non-canonical raw HTML'
E   AssertionError: assert 0 == 1
```

The source pointers were `tests/test_agent_docs_registry_guard.py:695` for the stale digest and `tests/test_agent_docs_registry_guard.py:1592` for the missing mutation targets at that baseline. The independent source comparison established that adopted AGENTS.md equals the exact merged-main blob; the reviewed Security-parent digest is `d1600d6987b05af35fdfd1585627dde68c6afd6f42f6dfa17db01dc48b0fd621`. Only four locations change in the existing registry test owner: that literal at `tests/test_agent_docs_registry_guard.py:437`, the two current scoped-default and omitted/added-cohort/no-blanket fixtures at `tests/test_agent_docs_registry_guard.py:1390` and `tests/test_agent_docs_registry_guard.py:1395`, and the explicit protected-parent rejection match at `tests/test_agent_docs_registry_guard.py:1981`. The other digests, all 38 exact admission field types/values, duplicate/extra/malformed JSON rejection, unique mutation checks, line-ending positives and Markdown/rawHTML/rendered-root negatives remain intact. The expected digest is never derived dynamically from candidate text.

The exact command was `../../.venv/bin/python -B -m pytest -o addopts='' -q -p no:cacheprovider --junitxml=artifacts/orchestration/nosec_ttl_20260930/main-guard-full-junit.xml tests/test_agent_docs_registry_guard.py tests/guards/test_nosec_policy_guard.py tests/guards/test_subprocess_uses_absolute_binaries.py` after `. ../../.venv/bin/activate` (exit **0**). Raw terminal stdout:

```text
199 passed in 24.24s
```

Retained JUnit reports **157 registry + 4 NOSEC + 38 subprocess = 199**, with **0 failures, 0 errors and 0 skips**. Each exact frozen M01–M10 node appears once and passes; the complete module run supplies all nine registry outcomes without a redundant ten-node rerun. Both rawHTML cases retain their `Non-canonical raw HTML` match, and every suppression mutation now requires `AGENTS Security parent region changed`, proving the intended rejection rather than an unrelated AssertionError. Black command `../../.venv/bin/python -m black --check tests/test_agent_docs_registry_guard.py` and Ruff command `../../.venv/bin/python -m ruff check tests/test_agent_docs_registry_guard.py` each exited **0**, with raw `1 file would be left unchanged.` and `All checks passed!` respectively. The log, status and XML are ignored local evidence; they are not current-head CI or merge-readiness proof.

The supplemental ordinary packet `e6f417903ae4` completed its five serial no-write preparation occurrences against criteria-v4 and passed execute preflight before the separate security-auditor occurrence-4 handoff. The original six preparation passes and single post-open QA/Bug/Security chain remain preserved. Current criteria-v5 retains **42 individually required outcomes: original 32 plus M01–M10** and versions the subsequent owner-approved exact 31-path scope; local test success alone does not mark lifecycle criteria achieved. All required final gates, actual-diff premortem, supplemental oracle execution, normal commits, current-head CI, review and closeout remain coordinator-owned.

## Follow-ups, rollback and authority

The [September ledger item](../roadmap/BACKLOG_LEDGER.md#ledger-p1-inline-nosec-ttl-20260930) remains open until merged implementation and required terminal proof. [October 30 reassessment](../roadmap/BACKLOG_LEDGER.md#ledger-p1-inline-nosec-reassessment-20261030) owns the remaining 45 exceptions. October 5 Docker/zlib/ncurses, October 7 Trivy/util-linux and October 28 native-Trivy obligations are distinct and unchanged.

Before the main-test correction, committed material had 29 pre-closeout paths, including the justified separate hook-generated secrets-baseline update. The admitted registry-test correction brings current material to 30 paths; the reserved canonical mapping projects 31. On 2026-10-01 the direct owner explicitly approved this exact 31-path scope and the emergency label; the coordinator authenticated application of `scope/emergency-approved` alongside the existing operator/privileged scope labels. Publication must retain the approved `Operator approval: approved`, `Privileged scope exception: approved` and `Emergency exception: approved` markers, split justification and all trusted scope labels. The approval is bounded to the shown material and canonical mapping, grants no unrelated expansion and is separate from exact-head merge approval. Foreign #2455/#2461 semantics/worktrees remain protected. That earlier admission included no Trivy/Rego/allowlist, authored dependency, source-manifest, infrastructure, secret, deployment or PT-VIP-1 context-map pointer change. The later explicit PCRE2 supplement below supersedes the source/Docker limitation only for its exact required correction.

If incompatibility appears, stop the affected operation and repair the admitted seam. Never restore unchecked credential transport, expired suppressions, redirect following or weakened gates. Required narrow-bundle completion, current-head CI, review and provider-neutral seal remain coordinator-owned. No local full make verify is run. Separate exact-PR/head/squash owner approval remains required for merge; provider absence creates no review/scan claim or bypass of findings, CI, mapping, unresolved threads or the review wait window.


## Native pip final-send correction

All installer-owned `python -m pip` commands now enter the existing installer's
reserved child before native CLI parsing (`scripts/ci/install_locked_python_requirements.py:1938`,
`scripts/ci/install_locked_python_requirements.py:2482`). Original pip argument
tails and diagnostic argv are preserved. The child lazily installs one guard
on native Requests `HTTPAdapter.send` and retains it through process termination,
including workers and atexit (`scripts/ci/install_locked_python_requirements.py:1880`,
`scripts/ci/install_locked_python_requirements.py:1923`).

Case-insensitive final Authorization key presence, including an empty value,
requires HTTPS, the current native verifying adapter and retained native
`cert_verify`, plus enabled verification or an existing native CA file/directory
path. Header values and credential sources are not inspected. This closes native
redirect reauthentication, direct 401 adapter retries and positional CacheControl
network sends. Initial default-file precedence, permissions and root admission
remain independent. The separate private-proxy health checker is outside this
installer contract. No version membership, release allowlist, fingerprint table,
general recognizer, dependency pin or upgrade is added.

Before the portability correction below, nine offline native groups passed in
both actual Python 3.13.14/pip 26.1.2 target and owned ensurepip staging. They retain real preparation/auth/redirect/cache/
certificate code and substitute only lower network: redirect statuses and both
default filenames, trusted ports with cache/no-cache, value-free key membership,
invalid/disabled verification and real CA paths, source removal after attachment,
real 401 retries, cache miss/hit/revalidation/cached redirects and secure/anonymous
controls (`tests/test_install_locked_python_requirements.py:6298`). The corrected
lower fixture uses genuine stdlib HTTP-response EOF closure for native cache
publication. Cache hits are reads, not network enforcement proof.

Four real subprocess controls each observed one blocked post-CLI worker send,
one blocked atexit send and zero lower calls, with controlled return/exception
exits 17/18; both guarded native `--version` controls exited 0. Eighteen captured
launches preserved tails and unrelated venv/metadata argv, and upgrade-only
dispatch was observed (`tests/test_install_locked_python_requirements.py:6587`,
`tests/test_install_locked_python_requirements.py:6674`). Synthetic credential,
encoded-header and exception markers were absent from final child diagnostics.
Native adapter transport controls separately observe retained `cert_verify`
setting `CERT_REQUIRED`. The common vendored urllib3 `match_hostname(cert, hostname)`
accepts the matching synthetic hostname and raises its native `CertificateError`
for a mismatch (`tests/test_install_locked_python_requirements.py:6577`). The
matcher is called directly with its two required arguments; no private socket
wrapper, completed TLS handshake or real-peer chain verification is claimed.

The correction trusts the current unmodified native client. Arbitrary plugins,
monkeypatched clients, future implementations, proxy authorization and other
credential channels are outside the proof. Import failure stops before native
CLI and detected unsafe authenticated sends stop before lower transport, without
an ordinary unguarded pip fallback. Future runtime changes require ordinary
current-material validation; no future-version rejection guarantee is claimed.
Focused tracked test output is retained below. Local narrow gates, current-head
CI, all 42 criteria, review closeout and exact-head human merge approval remain
independent requirements; these observations do not establish PR readiness.


Before the Oracle portability correction below, tracked focused validation used
the repo-approved shared interpreter. Its portable
command form is `$VENV_PYTHON -m pytest -q tests/test_install_locked_python_requirements.py
--junitxml=artifacts/orchestration/nosec_ttl_20260930/pip-phase0-proposal/tracked-installer-junit.xml`
(with `VENV_PYTHON` resolved by `scripts/hooks/repo_python.sh`). The retained raw
command includes the actual resolved interpreter; JUnit reports **348 tests,
0 failures, 0 errors, 0 skips** in 42.682 seconds. Raw terminal evidence:

```text
............................................................             [100%]
EXIT 0
```


The strict Apple/Linux oracle subsequently exposed only a test portability defect:
its vendored urllib3 lacks the private `_ssl_wrap_socket_and_match_hostname`
wrapper previously exercised by the local fixture. The native guard is unchanged.
The test now calls the common native hostname matcher directly, preserving a
positive match and a mismatch rejection; certificate-setting evidence remains in
the separate real native adapter controls. The rejected Oracle result and raw
failure remain retained; they are not converted into a passing Oracle claim.


The replacement matcher node passed locally with the resolved repo interpreter:
`tests/test_install_locked_python_requirements.py::TestLockedPipNativeTransport::test_native_pip_hostname_matcher_accepts_and_rejects`
(`pytest -o addopts='' -q`, targeted JUnit retained), exit **0**. Raw stdout:

```text
1 passed in 1.24s
```

The strict Oracle rerun and affected mandatory gates remain coordinator-owned;
this local targeted result does not establish a passing Oracle or PR readiness.


## Direct-owner PCRE2 supplement on 2026-10-02

The owner explicitly admitted the new HIGH `CVE-2026-103111` finding from
Docker run 36943207660/job 110639261837 into this same PR and requested fully
passing applicable current-head CI/security/Docker/review/readiness checks.
Current `NOSEC-TTL-20260930-criteria-v7` preserves all original 42 requirements
and adds D01–D06, for 48 individually required outcomes. B03 preserves the
existing SQLite/util-linux records and review dates while admitting exactly
PCRE2 10.49 and its upstream SLJIT gitlink closure. The earlier 31-path bound
and no-Docker restriction are historical for this necessary admitted change;
quality gates, trusted scope provenance and existing NoSec/pip/main corrections
remain intact. `55 = 7 obsolete + 3 fix/removals + 45 retained` is unchanged.

The [per-CVE owner document](CVE-2026-103111-pcre2.md) binds the immutable
scanner subject, exact source pair and retained native feasibility observations.
`scripts/ci/fetch_docker_source_artifacts.py:125` cross-binds the two exact
name/version/filename/URL/digest records. Calls at
`scripts/ci/fetch_docker_source_artifacts.py:214` and
`scripts/ci/fetch_docker_source_artifacts.py:238` enforce that identity before
cache reuse and before transport. URL validation at
`scripts/ci/fetch_docker_source_artifacts.py:239` and the installed reject-all
opener at `scripts/ci/fetch_docker_source_artifacts.py:241`, with its handler
defined at `scripts/ci/fetch_docker_source_artifacts.py:48`, retain old identity
behavior, verified TLS, no redirects and safe-cache/SHA3 checks. `Dockerfile:234` uses
the existing toolchain and manifest with network-disabled native source build;
`Dockerfile:557` exercises patched PCRE2/JIT and native libselinux under the
final nonroot user after pruning. The existing image inventory checker receives
one additional blocked package in its three workflow consumers.

Root subsequently built the actual final local linux/amd64 production image
`sha256:f6845ea1e1b680d41070328b2b60d882eeae043a9c11a14b44761ca02a25941a`
with exit **0**. Both interpreters under `pulseplate` passed PCRE2 10.49
UTF/UCP/JIT and native libselinux regex/loaded-path checks after pruning; retained
grep/dpkg/ls/mkdir/rmdir operations passed. Local Trivy 0.74.0 using the fresh
October 2 database and unchanged existing policy returned exit **0**, two result
subjects, zero HIGH/CRITICAL findings and zero secrets. Its final report SHA256
is `80e8b35cf88d271fbea3031a5f5cb63c25a051a715241595e27560c6341c9db4`.
The existing same-image inventory/report consumer also exited **0**. The per-CVE
owner document retains raw native stdout and this bounded local proof.

The first focused run found one stale expected complete package-list literal at
`tests/test_docker_workflow_build_path_contract.py:240`; its expectation now
includes `libpcre2-8-0` and preserves every existing member. Focused rerun,
remaining required local gates and current-material hosted CI/closeout proof
remain pending. Final local image observations do not prove hosted readiness.
No new ignore,
residual-risk waiver, provider call, schedule or production deployment is
admitted. Root retains the direct owner advance conditional squash instruction
and must bind it to fully passing live-head strict readiness, dispositions,
wait cycle and match-head guard at execution. Earlier passes and this supplement
are not completion or merge-readiness proof. The [new PCRE2 ledger item](../roadmap/BACKLOG_LEDGER.md#ledger-p1-pcre2-cve-2026-103111)
remains in progress until merged implementation and terminal evidence.


## Late native-pip command diagnostic correction

The current review exposed that native pip's normal `Command._run_wrapper`
caught the RuntimeError transport rejection through its broad exception path,
returning exit 2 with a traceback. Root's retained offline normal-wrapper
reproduction confirms that the minimal lazy exception interoperability subclass,
which remains `_PipTransportRejected` and is also native `InstallationError`,
uses the ordinary controlled exit-1 path with the constant transport message.
This correction changes only native exception categorization; transport
predicates, guard boundary/lifetime, CLI argument tails and normal mode stay
intact. No debug workaround or provider request is used.

Child pip import failure now has a distinct constant diagnostic rather than
being described as transport rejection. Raw import exception text, synthetic
credentials and traceback are not emitted. The actual native normal-wrapper
regression and import-failure privacy regressions are authored in the existing
test owner; their execution and fresh material gates remain Root-owned and
pending. Retained native PCRE2/local scanner evidence above remains local proof;
it does not establish hosted current-head or closeout readiness for this fix.
