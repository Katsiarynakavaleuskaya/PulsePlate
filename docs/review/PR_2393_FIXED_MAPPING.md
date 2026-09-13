# PR 2393 — Review Governance

Review-Seal-Version: v1

## Lane Start Provenance
Packet: `artifacts/orchestration/task_packets/fc03a9dc7747.json`

## Experiment Runner Evidence
Artifact: `artifacts/orchestration/experiments/results/secure-staging-oracle-result.json`

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

Disposition: FIXED
Commit: 6fb2314cfccaca890133053cd1a10f817e7858f6
Evidence: tests/test_staging_postgres_runtime.py:54-59; tests/test_staging_postgres_runtime.py:182-183; The native result contract now asserts exact selected references and the sole uploaded metadata artifact instead of arbitrary URL-substring membership.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2393#discussion_r3997246096 -> 6fb2314cfccaca890133053cd1a10f817e7858f6

Disposition: FIXED
Commit: 6fb2314cfccaca890133053cd1a10f817e7858f6
Evidence: scripts/deploy.sh:856; tests/test_deploy_contract_scripts.py:8599; Existing staging authenticates the application DSN with verify-full and bounded timeout before product stops.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2393#discussion_r3997272647 -> 6fb2314cfccaca890133053cd1a10f817e7858f6

Disposition: FIXED
Commit: 665030abb0f5fe2909cfc1f114e3d25c5f3ffda6
Evidence: scripts/ops/postgres_restore.sh:27; scripts/ops/postgres_restore.sh:70; scripts/ci/check_staging_postgres_runtime.py:795; The unsafe replacement capability is retired: only a fresh verification-prefixed target created from template0 is admitted; occupied targets are refused without mutation.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2393#discussion_r3997272648 -> 665030abb0f5fe2909cfc1f114e3d25c5f3ffda6

Disposition: FIXED
Commit: 6fb2314cfccaca890133053cd1a10f817e7858f6
Evidence: scripts/ci/check_pgvector_attestations.py:403; scripts/ci/check_pgvector_attestations.py:548; Attestation inventory uses the bounded complete limit and rejects malformed or truncation-boundary inventories.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2393#discussion_r3997272655 -> 6fb2314cfccaca890133053cd1a10f817e7858f6

Disposition: FIXED
Commit: 6fb2314cfccaca890133053cd1a10f817e7858f6
Evidence: scripts/ops/check_staging_security.py:220-234; tests/test_staging_security.py:661-684; Every admitted secret file is checked as a regular file on the validated encrypted device with exact owner/mode.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2393#discussion_r3997272660 -> 6fb2314cfccaca890133053cd1a10f817e7858f6

Disposition: FIXED
Commit: 6fb2314cfccaca890133053cd1a10f817e7858f6
Evidence: docs/deploy/POSTGRES_SELF_HOSTED_DROPLET.md:96; docs/deploy/STAGING.md:252-272; Production retains the generic backup unit; staging has a distinct unit with staging security and mount lifecycle.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2393#discussion_r3997272664 -> 6fb2314cfccaca890133053cd1a10f817e7858f6

Disposition: FIXED
Commit: 6fb2314cfccaca890133053cd1a10f817e7858f6
Evidence: scripts/ops/postgres_restore.sh:69-71; tests/test_deploy_contract_scripts.py:8689; Fresh verification creation explicitly uses POSTGRES_DB as maintenance database; it does not authorize replacement.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2393#discussion_r3997272665 -> 6fb2314cfccaca890133053cd1a10f817e7858f6

Disposition: FIXED
Commit: 6fb2314cfccaca890133053cd1a10f817e7858f6
Evidence: tests/test_cd_attestation_workflow_contract.py:971; tests/test_cd_attestation_workflow_contract.py:999-1026; SHA admission rejects malformed/all-zero identity and preserves exact same-repository source checks; the transient push carrier was later removed by R.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2393#discussion_r3997285508 -> 6fb2314cfccaca890133053cd1a10f817e7858f6

Disposition: FIXED
Commit: 6fb2314cfccaca890133053cd1a10f817e7858f6
Evidence: docs/deploy/STAGING.md:42-59; The operator procedure explicitly installs and cross-binds the finite staging helper/systemd bundle; no automatic host mutation is claimed.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2393#discussion_r3997285519 -> 6fb2314cfccaca890133053cd1a10f817e7858f6

Disposition: FIXED
Commit: 6fb2314cfccaca890133053cd1a10f817e7858f6
Evidence: docs/deploy/POSTGRES_SELF_HOSTED_DROPLET.md:74-82; The self-hosted recovery example uses the absolute restore-helper path and current --verify-into interface.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2393#discussion_r3997285520 -> 6fb2314cfccaca890133053cd1a10f817e7858f6

Disposition: FIXED
Commit: 6fb2314cfccaca890133053cd1a10f817e7858f6
Evidence: docs/deploy/STAGING.md:83-89; Documentation states that Docker and backup consumers depend on the admitted mount units, matching the unit direction.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2393#discussion_r3997285522 -> 6fb2314cfccaca890133053cd1a10f817e7858f6

Disposition: FIXED
Commit: 6fb2314cfccaca890133053cd1a10f817e7858f6
Evidence: scripts/ci/check_pgvector_attestations.py:491; scripts/ci/check_pgvector_attestations.py:539; scripts/ops/postgres_restore.sh:27; CLI modes and required inputs are validated as a closed set before use; current restore accepts only --verify-into.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2393#discussion_r3997285528 -> 6fb2314cfccaca890133053cd1a10f817e7858f6

Disposition: FIXED
Commit: 6fb2314cfccaca890133053cd1a10f817e7858f6
Evidence: .github/workflows/cd.yml:107; tests/test_cd_attestation_workflow_contract.py:788; The native integration checks Docker Compose >=2.35.0 before runtime; focused tests reject 2.34.9 and malformed versions.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2393#discussion_r3997285530 -> 6fb2314cfccaca890133053cd1a10f817e7858f6

Disposition: FIXED
Commit: 665030abb0f5fe2909cfc1f114e3d25c5f3ffda6
Evidence: scripts/ops/postgres_restore.sh:27-34; scripts/ci/check_staging_postgres_runtime.py:795-894; tests/test_staging_postgres_runtime.py:947-1035; Replacement is retired; occupied targets, including ordinary/non-public/publication/global state, are refused and preserved, while full represented archive objects are exercised only in a fresh target.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2393#discussion_r3997285532 -> 665030abb0f5fe2909cfc1f114e3d25c5f3ffda6

Disposition: FIXED
Commit: 08c3f786df5d9180260ca3e29e30ec4ce4bfd8ac
Evidence: tests/test_cd_attestation_workflow_contract.py:119; tests/test_cd_attestation_workflow_contract.py:132; The current credential regression compares the complete unchanged private DHI file bytes and exact typed SDK configuration, replacing substring-only assertions.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2393#discussion_r3997915313 -> 08c3f786df5d9180260ca3e29e30ec4ce4bfd8ac

Disposition: FIXED
Commit: 08c3f786df5d9180260ca3e29e30ec4ce4bfd8ac
Evidence: .github/workflows/cd.yml:3091-3162; .github/workflows/cd.yml:3210-3257; The selected restore-helper bytes are independently hashed, required regular/non-symlink, and cross-bound in both staging remote passes.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2393#discussion_r3997929135 -> 08c3f786df5d9180260ca3e29e30ec4ce4bfd8ac

Disposition: FIXED
Commit: 08c3f786df5d9180260ca3e29e30ec4ce4bfd8ac
Evidence: docs/deploy/STAGING.md:284-295; docs/deploy/STAGING.md:465; Staging examples consistently use role pulseplate and retained database pulseplate_staging with the current fresh-only restore boundary.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2393#discussion_r3997929138 -> 08c3f786df5d9180260ca3e29e30ec4ce4bfd8ac

Disposition: FIXED
Commit: 08c3f786df5d9180260ca3e29e30ec4ce4bfd8ac
Evidence: docs/deploy/STAGING.md:42-59; deploy/systemd/pulseplate-staging-postgres-backup.service.example:1; Root-owned staging inputs and the reviewed privileged operator boundary remove execution/config ownership from the operator account; no sudo containment claim.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2393#discussion_r3997941098 -> 08c3f786df5d9180260ca3e29e30ec4ce4bfd8ac

Disposition: FIXED
Commit: 5e6196fcae7a228d6ddfbb31555f111c8166a098
Evidence: .github/workflows/cd.yml:160-166; tests/test_cd_attestation_workflow_contract.py:999-1026; R removes the privileged wildcard push carrier and preserves only exact-SHA manual selected-branch dispatch; reuse remains main-only.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2393#discussion_r3997941103 -> 5e6196fcae7a228d6ddfbb31555f111c8166a098

Disposition: FIXED
Commit: e7bfbca10546c15d002d659132106748dbe57592
Evidence: scripts/ops/check_staging_security.py:555-575; tests/test_staging_security.py:818; tests/test_staging_security.py:1342; Fresh admission proves empty stable backing storage and rejects orphan retained PostgreSQL history before any fresh start.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2393#discussion_r3999015539 -> e7bfbca10546c15d002d659132106748dbe57592

Disposition: FIXED
Commit: e7bfbca10546c15d002d659132106748dbe57592
Evidence: tests/test_staging_security.py:926; docs/deploy/STAGING.md:175; Prometheus admits only an empty fresh state or a verified current v5 service/mount and retains legacy volume history after proved cutover.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2393#discussion_r3999015542 -> e7bfbca10546c15d002d659132106748dbe57592

Disposition: FIXED
Commit: e7bfbca10546c15d002d659132106748dbe57592
Evidence: scripts/ops/check_staging_security.py:401-503; tests/test_staging_security.py:1185-1274; The checker binds exact installed service/timer bytes and closed loaded systemd properties, mount lifecycle, environment, commands and daily schedule.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2393#discussion_r3999015558 -> e7bfbca10546c15d002d659132106748dbe57592

Disposition: FIXED
Commit: 665030abb0f5fe2909cfc1f114e3d25c5f3ffda6
Evidence: .github/workflows/cd.yml:1237-1244; .github/workflows/cd.yml:2715-2716; tests/test_cd_attestation_workflow_contract.py:830-853; Native staging integration success is a required dependency of PostgreSQL publication and staging deployment.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2393#discussion_r3999473936 -> 665030abb0f5fe2909cfc1f114e3d25c5f3ffda6

Disposition: FIXED
Commit: 665030abb0f5fe2909cfc1f114e3d25c5f3ffda6
Evidence: scripts/ops/check_staging_security.py:220-234; tests/test_staging_security.py:661-684; The metrics scrape key is now included in the same per-file encrypted-device check as the PostgreSQL credentials.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2393#discussion_r3999473942 -> 665030abb0f5fe2909cfc1f114e3d25c5f3ffda6

Disposition: FIXED
Commit: 665030abb0f5fe2909cfc1f114e3d25c5f3ffda6
Evidence: scripts/ops/postgres_restore.sh:27-34; scripts/ci/check_staging_postgres_runtime.py:795-894; tests/test_staging_postgres_runtime.py:947-1035; The database-level-object blacklist and in-place reset are removed; all occupied targets are refused and preserved before mutation.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2393#discussion_r3999473945 -> 665030abb0f5fe2909cfc1f114e3d25c5f3ffda6

Disposition: FIXED
Commit: 6938acb0c339377550c497d007a9ef45bb026658
Evidence: scripts/ci/check_pgvector_attestations.py:37; .github/workflows/ci.yml:77; tests/test_pgvector_attestations.py:548; tests/test_pgvector_attestations.py:552; artifacts/orchestration/secure-staging/euler-preparation/timer-class-review.md; The shared backup timer now belongs to the existing finite PostgreSQL material union, preserving both distinct service templates. A real Git timer-only schedule change proves classification; the existing parameterized membership test covers all four current systemd siblings. Euler bounded inventory found this sole omission among 28 inspected owners; no new recognizer or arbitrary-dependency completeness claim.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2393#discussion_r4000257753 -> 6938acb0c339377550c497d007a9ef45bb026658

Disposition: FIXED
Commit: 5e6196fcae7a228d6ddfbb31555f111c8166a098
Evidence: docs/deploy/STAGING.md:47; .github/workflows/cd.yml:160; tests/test_cd_attestation_workflow_contract.py:999; Bot-editable aggregate lists only root-input and wildcard findings; D fixes the former and descendant R removes the latter. Inline roots remain independently mapped.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2393#issuecomment-5648048041 -> 5e6196fcae7a228d6ddfbb31555f111c8166a098

Disposition: FIXED
Commit: a6c6c424c028958dbb5a907d4642da5d7bec09be
Evidence: scripts/run-backend-tests-pre-commit.sh:157; tests/test_pre_commit_hook_python_resolver.py:2492; tests/test_pre_commit_hook_python_resolver.py:2621; AGENTS.md:2081; .github/workflows/cd.yml:1152; .github/workflows/cd.yml:2681; The current Git-discovery finding is fixed by K, including upstream/base/recent-history failures. The bot docstring percentage is advisory and is not a repository coverage requirement; no docstring or coverage rule is weakened. The aggregate also mentions force-pushing main: this is forbidden by AGENTS.md:2081, and non-ancestor publication HOLD is intentional fail-closed behavior, not a supported-operation defect. No force-push recovery capability is added.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2393#issuecomment-5648051192 -> a6c6c424c028958dbb5a907d4642da5d7bec09be

Disposition: FIXED
Commit: 665030abb0f5fe2909cfc1f114e3d25c5f3ffda6
Evidence: scripts/deploy.sh:856; scripts/ops/postgres_restore.sh:27; scripts/ci/check_staging_postgres_runtime.py:795; The earlier real fix added bounded connect_timeout and closed the publication/secret/unit/CLI findings; descendant F retires unsafe existing-database replacement. The aggregate and each actionable child retain separate records.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2393#pullrequestreview-5187717950 -> 665030abb0f5fe2909cfc1f114e3d25c5f3ffda6

Disposition: FIXED
Commit: a6c6c424c028958dbb5a907d4642da5d7bec09be
Evidence: scripts/run-backend-tests-pre-commit.sh:157; tests/test_pre_commit_hook_python_resolver.py:2492; tests/test_pre_commit_hook_python_resolver.py:2621; Actionable outside-diff merge-base failure is fixed by fail-closed Git discovery at scripts/run-backend-tests-pre-commit.sh:157-208 and tests/test_pre_commit_hook_python_resolver.py:2489ff.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2393#pullrequestreview-5191253719 -> a6c6c424c028958dbb5a907d4642da5d7bec09be

Disposition: NOT-A-BUG
Evidence: scripts/ci/check_staging_postgres_runtime.py:242-260; The flagged write contains CA configuration and a private-key pathname, not private-key bytes.
Reason: The flagged write contains CA configuration and a private-key pathname, not private-key bytes.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2393#discussion_r3997246068

Disposition: NOT-A-BUG
Evidence: scripts/ci/check_staging_postgres_runtime.py:279-281; scripts/ci/check_staging_postgres_runtime.py:1005; Plaintext synthetic password is required invocation-local probe input in restricted disposable storage; no secure-erasure or runner-owner protection claim.
Reason: Plaintext synthetic password is required invocation-local probe input in restricted disposable storage; no secure-erasure or runner-owner protection claim.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2393#discussion_r3997246082

Disposition: NOT-A-BUG
Evidence: scripts/ci/check_staging_postgres_runtime.py:279-281; scripts/ci/check_staging_postgres_runtime.py:1005; Plaintext synthetic libpq passfile is required invocation-local probe input in restricted disposable storage; no secure-erasure claim.
Reason: Plaintext synthetic libpq passfile is required invocation-local probe input in restricted disposable storage; no secure-erasure claim.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2393#discussion_r3997246088

Disposition: NOT-A-BUG
Evidence: scripts/ops/postgres_backup.sh:23; tests/test_deploy_contract_scripts.py:8838; tests/test_deploy_contract_scripts.py:8869; Reserved staging selection uses exact project or Compose basename equality after normalization; a production name merely containing staging does not select it.
Reason: Reserved staging selection uses exact project or Compose basename equality after normalization; a production name merely containing staging does not select it.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2393#discussion_r3997249072

Disposition: NOT-A-BUG
Evidence: scripts/ci/check_staging_postgres_runtime.py:483-529; scripts/ci/check_staging_postgres_runtime.py:943-946; The flagged compose.native.json sink serializes explicit Compose structure, secret filenames and bind paths, not password/passfile/key/archive contents.
Reason: The flagged compose.native.json sink serializes explicit Compose structure, secret filenames and bind paths, not password/passfile/key/archive contents.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2393#discussion_r3997915303

Disposition: NOT-A-BUG
Evidence: scripts/deploy.sh:907; scripts/deploy.sh:943; scripts/deploy.sh:958; scripts/ci/check_docker_provenance_attestation.py:101; Staging deployment uses the Go gh verifier with authenticated DOCKER_CONFIG; the JavaScript OCI writer default-directory bridge is not this path.
Reason: Staging deployment uses the Go gh verifier with authenticated DOCKER_CONFIG; the JavaScript OCI writer default-directory bridge is not this path.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2393#discussion_r3997929124

Disposition: NOT-A-BUG
Evidence: .github/workflows/cd.yml:1299; .github/workflows/cd.yml:1320; .github/workflows/cd.yml:2118; scripts/ci/check_pgvector_attestations.py:378; Publication authenticates before OCI inventory reads; only the pinned JavaScript write action needed the separate default-directory bridge.
Reason: Publication authenticates before OCI inventory reads; only the pinned JavaScript write action needed the separate default-directory bridge.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2393#discussion_r3997929128

Disposition: NOT-A-BUG
Evidence: .github/workflows/cd.yml:2545; .github/workflows/cd.yml:2613; scripts/ci/check_pgvector_attestations.py:378; Reuse verification uses the Go verifier with DOCKER_CONFIG and remains outside the JavaScript writer credential behavior.
Reason: Reuse verification uses the Go verifier with DOCKER_CONFIG and remains outside the JavaScript writer credential behavior.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2393#discussion_r3997929132

Disposition: NOT-A-BUG
Evidence: .github/workflows/cd.yml:61-122; artifacts/orchestration/secure-staging/roles/new-D-review-routing.md; Observed public-repository job receives only built-in read-only contents/packages token, no PAT/DHI/staging/production secret; PR workflow writers already own permissions. A trusted-base executor would be a new authority architecture.
Reason: Observed public-repository job receives only built-in read-only contents/packages token, no PAT/DHI/staging/production secret; PR workflow writers already own permissions. A trusted-base executor would be a new authority architecture.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2393#discussion_r3999015552

Disposition: NOT-A-BUG
Evidence: .github/workflows/cd.yml:144-185; tests/test_cd_attestation_workflow_contract.py:938-1038; artifacts/orchestration/secure-staging/roles/K-late-review-triage.md; Accepted A8 requires an explicit SHA-bound synthetic premerge build by a same-repository writer. This job requires repository/ref/SHA/Commit API/checkout agreement and has no DHI/SSH/runtime promotion/deployment. Repository writers already control workflow permissions; a main-only restriction would remove the accepted premerge capability and would not contain an already-trusted malicious writer.
Reason: Accepted A8 requires an explicit SHA-bound synthetic premerge build by a same-repository writer. This job requires repository/ref/SHA/Commit API/checkout agreement and has no DHI/SSH/runtime promotion/deployment. Repository writers already control workflow permissions; a main-only restriction would remove the accepted premerge capability and would not contain an already-trusted malicious writer.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2393#discussion_r4000257748

Disposition: NOT-A-BUG
Evidence: .github/workflows/ci.yml:2470-2477; artifacts/orchestration/secure-staging/K-hosted-ios-receipt.json; https://github.com/Katsiarynakavaleuskaya/PulsePlate/actions/runs/34770173576; Exact K hosted run uploaded artifact 10322385750 (758520 bytes, 699 members), independently downloaded with matching SHA-256 and parsed by native xcresulttool: 328 passed, zero failed/skipped. The explicit glob does retain this bundle; broadening hidden-file inclusion is not required.
Reason: Exact K hosted run uploaded artifact 10322385750 (758520 bytes, 699 members), independently downloaded with matching SHA-256 and parsed by native xcresulttool: 328 passed, zero failed/skipped. The explicit glob does retain this bundle; broadening hidden-file inclusion is not required.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2393#discussion_r4000257751

Disposition: NOT-A-BUG
Evidence: scripts/ops/postgres_backup.sh:23; tests/test_deploy_contract_scripts.py:8838; tests/test_deploy_contract_scripts.py:8869; Actionable Sourcery body duplicates r3997249072; use the exact reserved-staging identity evidence.
Reason: Actionable Sourcery body duplicates r3997249072; use the exact reserved-staging identity evidence.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2393#pullrequestreview-5187684276

## Review Material Seal
<!-- PULSEPLATE_PR_REVIEW_SEAL_V1_BEGIN -->
<!-- pragma: allowlist nextline secret -->
{"authority":"human_asserted_content_receipt","code_review":{"blocking":false,"material_digest":"sha256:0d5875ba2ebb83faaf09fd148dec369d30abeb02aad8f3079dd7d657b2a1acd6","material_head_sha":"94771cda10e229d02a7dd4aa8700cc00bce4a28f","output_required":false,"review_claim":"none"},"codex_security":{"base_revision":"d8358f87425756df77e5c014682c8c48a62d6eaa","blocking":false,"head_revision":"94771cda10e229d02a7dd4aa8700cc00bce4a28f","material_digest":"sha256:0d5875ba2ebb83faaf09fd148dec369d30abeb02aad8f3079dd7d657b2a1acd6","no_findings_claim":false,"output_required":false,"scan_claim":"none"},"material":{"base_ref_oid":"d8358f87425756df77e5c014682c8c48a62d6eaa","digest":"sha256:0d5875ba2ebb83faaf09fd148dec369d30abeb02aad8f3079dd7d657b2a1acd6","material_head_sha":"94771cda10e229d02a7dd4aa8700cc00bce4a28f","merge_base_sha":"d8358f87425756df77e5c014682c8c48a62d6eaa","policy_version":"pulseplate.material-classification/v1"},"pr_number":2393,"repository":"Katsiarynakavaleuskaya/PulsePlate","schema_version":"pulseplate.pr-review-seal/v1","self_review":{"actionable_findings_count":0,"authority":"repo_native_pulseplate_pr_review_advisory","blocking":false,"findings_count":1,"material_digest":"sha256:0d5875ba2ebb83faaf09fd148dec369d30abeb02aad8f3079dd7d657b2a1acd6","material_head_sha":"94771cda10e229d02a7dd4aa8700cc00bce4a28f","report_payload":{"actionable_findings_count":0,"base_ref_oid":"d8358f87425756df77e5c014682c8c48a62d6eaa","calibration":{"case_labels":["review-source-degraded","large-diff-risk"],"false_positive_controls":["clean context must produce zero findings","benign fixed-mapping presence must not become a governance finding","warnings and governance uncertainty remain actionable findings, not diagnostic notes","review-source degradation is status/warning only unless an explicit blocking source finding exists","large diff risk is review-planning evidence, not a merge-readiness claim"],"posting_eligible":false,"posting_gate":"GitHub posting remains out of scope until a dedicated calibrated posting PR.","rubric_version":"pr4-2026-04-28"},"coordinator_packet":{"path":"artifacts/orchestration/task_packets/fc03a9dc7747.json","role_order":["agent-coordinator","architecture-specialist","security-auditor","qa-engineer-agent","bug-hunter","data-scientist-agent"],"task_packet_id":"fc03a9dc7747"},"decision_log":["This report is advisory and side-effect free.","This report does not post GitHub comments, resolve review threads, merge PRs, or claim merge readiness.","External CodeRabbit, Sourcery, and Cubic statuses remain separate PR governance signals."],"deferred_followups":[],"findings":[{"category":"tests","diagnostic_code":"large_diff_review_risk","disposition_candidate":"NOT-A-BUG","evidence":"Diff contains 12547 changed lines, above review-risk threshold 800.","file":"docs/roadmap/BACKLOG_LEDGER.md","gate_to_run":"make validate-changed","line":null,"role_agent":"bug-hunter","severity":"note","suggested_fix":"Confirm PR split rationale and targeted deterministic gates before opening review."}],"findings_count":1,"gate_plan":["python3 scripts/orchestration/check_preflight.py","python3 scripts/orchestration/check_agent_consistency.py","python3 -m pytest tests/test_pr_review_report.py tests/test_pr_review_context.py -q","Add and fill docs/review/PR_<N>_FIXED_MAPPING.md before merge-ready loop","make test-fast","make validate-changed"],"generated_at_utc":"2026-09-13T19:37:05Z","material_digest":"sha256:0d5875ba2ebb83faaf09fd148dec369d30abeb02aad8f3079dd7d657b2a1acd6","material_head_sha":"94771cda10e229d02a7dd4aa8700cc00bce4a28f","merge_base_sha":"d8358f87425756df77e5c014682c8c48a62d6eaa","mode":"dry-run-report","review_source_status":[{"blocking":false,"evidence":"gh api repos/<repo>/pulls/<pr>","fallback_required":false,"reason":"","source":"github_pr_metadata","source_degraded":false,"status":"available"},{"blocking":false,"evidence":"d8358f87425756df77e5c014682c8c48a62d6eaa..94771cda10e229d02a7dd4aa8700cc00bce4a28f","fallback_required":false,"reason":"","source":"git_diff","source_degraded":false,"status":"available"},{"blocking":false,"evidence":"docs/review/PR_2393_FIXED_MAPPING.md","fallback_required":true,"reason":"Fixed-mapping artifact unavailable","source":"fixed_mapping_artifact","source_degraded":true,"status":"unavailable"}],"role_review":[{"role_agent":"agent-coordinator","summary":"agent-coordinator has no deterministic findings from the supplied context."},{"role_agent":"architecture-specialist","summary":"architecture-specialist has no deterministic findings from the supplied context."},{"role_agent":"security-auditor","summary":"security-auditor has no deterministic findings from the supplied context."},{"role_agent":"qa-engineer-agent","summary":"qa-engineer-agent has no deterministic findings from the supplied context."},{"role_agent":"bug-hunter","summary":"bug-hunter flagged 1 advisory finding(s) for human review."},{"role_agent":"data-scientist-agent","summary":"data-scientist-agent has no scoring calibration changes in this dry-run report."}],"schema_version":"2.0.0","scope_reviewed":{"changed_files":[".env.example",".github/workflows/cd.yml",".github/workflows/ci.yml",".secrets.baseline","AGENTS.md","deploy/AGENTS.md","deploy/docker-compose.staging.yaml","deploy/postgres-pgvector/pg_hba.conf","deploy/systemd/pulseplate-staging-postgres-backup.service.example","deploy/systemd/pulseplate-staging-storage.conf","docs/deploy/POSTGRES_SELF_HOSTED_DROPLET.md","docs/deploy/STAGING.md","docs/roadmap/BACKLOG_LEDGER.md","docs/security/MAIN_RECOVERY_1_CONTAINER_PUBLICATION.md","ios/PulsePlateTests/AppNavigationShellTests.swift","scripts/AGENTS.md","scripts/ci/check_pgvector_attestations.py","scripts/ci/check_staging_postgres_runtime.py","scripts/ci/ghcr_attestation_credentials.py","scripts/deploy.sh","scripts/ops/check_staging_security.py","scripts/ops/postgres_backup.sh","scripts/ops/postgres_restore.sh","scripts/run-backend-tests-pre-commit.sh","tests/guards/test_review_source_quota_policy_guard.py","tests/test_caddy_deploy_provenance.py","tests/test_cd_attestation_workflow_contract.py","tests/test_cd_workflow_production_deploy_gate.py","tests/test_ci_workflow_pr_size_governance_contract.py","tests/test_deploy_contract_scripts.py","tests/test_pgvector_attestations.py","tests/test_pre_commit_hook_python_resolver.py","tests/test_production_release_evidence_wiring.py","tests/test_staging_postgres_runtime.py","tests/test_staging_security.py"],"diff_summary":{"additions":11154,"changed_lines":12547,"deletions":1393,"files":35},"fixed_mapping_errors":[],"omitted_surfaces":["GitHub posting","PR thread resolution","merge readiness claims"],"pr_metadata_available":true,"scoped_agents_md":["AGENTS.md","deploy/AGENTS.md","ios/AGENTS.md","scripts/AGENTS.md","tests/AGENTS.md"]},"warnings":[]},"report_sha256":"sha256:76270932a39761c4e2dc53b604edfc494b2c7ad699f286d843930ee49eba4e84","review_claim":"none","review_tool":"pulseplate-pr-review","schema_version":"pulseplate.self-review-advisory/v1","status":"advisory_report_attached"}}
<!-- PULSEPLATE_PR_REVIEW_SEAL_V1_END -->
