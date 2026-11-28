# PR 2503 — Review Governance

Review-Seal-Version: v1

## Lane Start Provenance
Packet: `artifacts/orchestration/task_packets/bb4fe5049590.json`

## Experiment Runner Evidence
Artifact: `artifacts/orchestration/experiments/results/oracle_attachments/ff236331376b2045e68a223f2cc5bb9f25989b226b5ea0afc90dd3caa3b694c9/result.json`

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

Disposition: DEFERRED
Backlog: docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-main-recovery-1-image-publication
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2503#discussion_r4662589508

Disposition: FIXED
Commit: 47dcc127c37e825fce3df5d188d684c560062324
Evidence: scripts/AGENTS.md:297 documents renewal using a genuine import on unchanged source. Native dispatch and expiry checks are exercised in tests/test_docker_runtime_dependency_surface.py:4537.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2503#discussion_r4653176548 -> 47dcc127c37e825fce3df5d188d684c560062324

Disposition: FIXED
Commit: 89c7e9247c484eb6121e975e02ce80aa583e97bc
Evidence: scripts/ci/check_docker_runtime_dependency_surface.py:2335 validates the optional attempt field with a controlled identity check; the missing-attempt negative reports its bounded diagnostic.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2503#discussion_r4653176551 -> 89c7e9247c484eb6121e975e02ce80aa583e97bc

Disposition: FIXED
Commit: 89c7e9247c484eb6121e975e02ce80aa583e97bc
Evidence: scripts/ci/fetch_docker_source_artifacts.py:11779 and the current BASE comparator at scripts/ci/fetch_docker_source_artifacts.py:4499 independently bind current checkout bytes after original publisher verification; stale-base and historical consumer regression cases pass.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2503#discussion_r4653176566 -> 89c7e9247c484eb6121e975e02ce80aa583e97bc

Disposition: FIXED
Commit: 89c7e9247c484eb6121e975e02ce80aa583e97bc
Evidence: tests/test_deploy_contract_scripts.py:19275 sets a completion after the merge and within the source window. That historical case is rejected.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2503#discussion_r4653176569 -> 89c7e9247c484eb6121e975e02ce80aa583e97bc

Disposition: FIXED
Commit: 89c7e9247c484eb6121e975e02ce80aa583e97bc
Evidence: scripts/ci/check_docker_runtime_dependency_surface.py:2168 replaces comment revision admission. tests/test_docker_runtime_dependency_surface.py:4537 checks the actual native inputs, artifact and specific failure causes instead of matching any comment error.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2503#discussion_r4653176576 -> 89c7e9247c484eb6121e975e02ce80aa583e97bc

Disposition: FIXED
Commit: 89c7e9247c484eb6121e975e02ce80aa583e97bc
Evidence: scripts/ci/check_docker_runtime_dependency_surface.py:1023 verifies the preimage and exact byte-for-byte pin replacement in both regular CI/CD callers; extra caller bytes reject.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2503#discussion_r4653179624 -> 89c7e9247c484eb6121e975e02ce80aa583e97bc

Disposition: FIXED
Commit: 89c7e9247c484eb6121e975e02ce80aa583e97bc
Evidence: scripts/ci/check_docker_runtime_dependency_surface.py:2168 admits the original checked operation with actual immutable source and output. A GitHub comment cannot supply or revoke its technical receipt.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2503#discussion_r4653179635 -> 89c7e9247c484eb6121e975e02ce80aa583e97bc

Disposition: FIXED
Commit: 89c7e9247c484eb6121e975e02ce80aa583e97bc
Evidence: scripts/ci/check_docker_runtime_dependency_surface.py:1864 checks competing original operations before narrowing the receipts to the exact image and archived technical input. Independent competing and wrong-subject negatives pass.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2503#discussion_r4653179642 -> 89c7e9247c484eb6121e975e02ce80aa583e97bc

Disposition: FIXED
Commit: 89c7e9247c484eb6121e975e02ce80aa583e97bc
Evidence: tests/test_deploy_contract_scripts.py:18193 explicitly uses stored test bytes and measures the actual directory/read boundary for the ZIP.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2503#discussion_r4653179691 -> 89c7e9247c484eb6121e975e02ce80aa583e97bc

Disposition: FIXED
Commit: 89c7e9247c484eb6121e975e02ce80aa583e97bc
Evidence: scripts/ci/check_docker_runtime_dependency_surface.py:752 splits the public pin construction into adjacent literals while preserving its exact bytes.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2503#discussion_r4653179701 -> 89c7e9247c484eb6121e975e02ce80aa583e97bc

Disposition: FIXED
Commit: dcf14758ee5bf182493750fc88e3d5ebc28e45cd
Evidence: scripts/AGENTS.md:281 documents the spent-build/no-retained-artifact boundary and separate recovery after prebuild refusal.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2503#discussion_r4654507408 -> dcf14758ee5bf182493750fc88e3d5ebc28e45cd

Disposition: FIXED
Commit: dcf14758ee5bf182493750fc88e3d5ebc28e45cd
Evidence: scripts/ci/check_docker_runtime_dependency_surface.py:1221 normalizes explicit-zone native timestamps to UTC. tests/test_docker_runtime_dependency_surface.py:4879 covers the documented fractional offset, exact ordering and rejected ambiguous values.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2503#discussion_r4654507421 -> dcf14758ee5bf182493750fc88e3d5ebc28e45cd

Disposition: FIXED
Commit: dcf14758ee5bf182493750fc88e3d5ebc28e45cd
Evidence: scripts/ci/check_docker_runtime_dependency_surface.py:4442 reserves the actual remaining work, including SOURCE16, FINAL_SUBJECT, upload and verification, before build. tests/test_docker_runtime_dependency_surface.py:5017 checks both time boundaries against the workflow budgets.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2503#discussion_r4654507427 -> dcf14758ee5bf182493750fc88e3d5ebc28e45cd

Disposition: FIXED
Commit: dcf14758ee5bf182493750fc88e3d5ebc28e45cd
Evidence: scripts/ci/check_docker_runtime_dependency_surface.py:1864 consults the original attempt-one outcome and its authenticated job and artifact when the mutable listing points to a rerun; later attempts cannot supply that receipt.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2503#discussion_r4654507433 -> dcf14758ee5bf182493750fc88e3d5ebc28e45cd

Disposition: FIXED
Commit: dcf14758ee5bf182493750fc88e3d5ebc28e45cd
Evidence: scripts/ci/check_docker_runtime_dependency_surface.py:1520 verifies availability through the earliest required original Q/S/C expiry. The repair uploader requests 90 days, and rejects a shorter authenticated server retention. Historical source availability and the 24-hour read window are separate.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2503#discussion_r4654507440 -> dcf14758ee5bf182493750fc88e3d5ebc28e45cd

Disposition: FIXED
Commit: 03d5125770d7c7f73f90b73c786c2c511447b976
Evidence: scripts/ci/check_docker_runtime_dependency_surface.py:1392 shares all eight existing maxima between packing and reading. The qualifying upload runs the same ZIP decoder as the authenticated download before transmission. tests/test_docker_runtime_dependency_surface.py:5233 verifies both normal modes and negative inputs. The original oversized strict fixture now rejects before creating a transport.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2503#discussion_r4654983300 -> 03d5125770d7c7f73f90b73c786c2c511447b976

Disposition: FIXED
Commit: 03d5125770d7c7f73f90b73c786c2c511447b976
Evidence: scripts/ci/check_docker_runtime_dependency_surface.py:4442 bounds projected useful completion by dispatch and source expiry as well as the independent job limit. tests/test_docker_runtime_dependency_surface.py:5017 exercises earlier source expiry and strict equality.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2503#discussion_r4654983305 -> 03d5125770d7c7f73f90b73c786c2c511447b976

Disposition: FIXED
Commit: 59640e69f54ad0f77377a6e306150863bbfb9d9a
Evidence: scripts/AGENTS.md:294 directs the operator to derive a contract-specific operand and create a new GitHub dispatch at or after the prior expiry.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2503#discussion_r4655267358 -> 59640e69f54ad0f77377a6e306150863bbfb9d9a

Disposition: FIXED
Commit: 59640e69f54ad0f77377a6e306150863bbfb9d9a
Evidence: tests/test_docker_runtime_dependency_surface.py:5017 executes the actual BUILD charge with insufficient global job time and checks the controlled refusal, zero build debit and absence of an action deadline.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2503#discussion_r4655267364 -> 59640e69f54ad0f77377a6e306150863bbfb9d9a

Disposition: FIXED
Commit: 42f9ee33d8cf6b9f9eb567a3afd4b529e13fd12d
Evidence: scripts/ci/check_docker_runtime_dependency_surface.py:4619 reserves a verification-length allowance on the job clock before charging the upload. Tests reject 600/659s and preserve the full readback after a 60s interstep gap with 660s left.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2503#discussion_r4655960821 -> 42f9ee33d8cf6b9f9eb567a3afd4b529e13fd12d

Disposition: FIXED
Commit: 06d3a58190a41d16e55e1cb8c9baa1b22aa815f8
Evidence: scripts/AGENTS.md:284 explicitly identifies exhausted readback after a successful ZIP transfer as a failed original attempt; later matching metadata is diagnostic and a new build requires reviewed material and a distinct input.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2503#discussion_r4655960823 -> 06d3a58190a41d16e55e1cb8c9baa1b22aa815f8

Disposition: FIXED
Commit: 42f9ee33d8cf6b9f9eb567a3afd4b529e13fd12d
Evidence: tests/test_caddy_deploy_provenance.py:8546 checks each native reader after success or failure, including absence of the credential directory and cleared in-memory credentials.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2503#discussion_r4655960824 -> 42f9ee33d8cf6b9f9eb567a3afd4b529e13fd12d

Disposition: FIXED
Commit: 218ec3f324c1e15110888e60b2ce3b2e17b400d2
Evidence: scripts/ci/check_docker_runtime_dependency_surface.py:883 validates the live main ref at the end of admission. The real published-code regression accepts a stale PR base when main advances; the corrected live path rejects it while the historical squash path remains usable.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2503#discussion_r4662589505 -> 218ec3f324c1e15110888e60b2ce3b2e17b400d2

Disposition: FIXED
Commit: 218ec3f324c1e15110888e60b2ce3b2e17b400d2
Evidence: tests/test_docker_runtime_dependency_surface.py:4658 executes the actual repair branch PR discovery using the real dispatcher against bound API responses and tests stale listing rejection.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2503#discussion_r4662589517 -> 218ec3f324c1e15110888e60b2ce3b2e17b400d2

Disposition: FIXED
Commit: 218ec3f324c1e15110888e60b2ce3b2e17b400d2
Evidence: tests/test_docker_workflow_build_path_contract.py:17946 checks the actual PR, the read function, all six independently computed Alertmanager subject coordinates and current/historical mode for CI and CD.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2503#discussion_r4662589519 -> 218ec3f324c1e15110888e60b2ce3b2e17b400d2

Disposition: FIXED
Commit: 218ec3f324c1e15110888e60b2ce3b2e17b400d2
Evidence: scripts/ci/check_docker_runtime_dependency_surface.py:1889 splits both long workflow-history queries into literals that preserve the request path and query bytes.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2503#discussion_r4662589525 -> 218ec3f324c1e15110888e60b2ce3b2e17b400d2

Disposition: FIXED
Commit: a968e0ca9c1c2d19d0b8d9b3bcd0f90a87594982
Evidence: docs/roadmap/BACKLOG_LEDGER.md:395 explicitly identifies the conditional follow-up PR for duplicated runner cost and retains the existing owner, due date and original W7 discussion.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2503#discussion_r4663421880 -> a968e0ca9c1c2d19d0b8d9b3bcd0f90a87594982

Disposition: FIXED
Commit: a968e0ca9c1c2d19d0b8d9b3bcd0f90a87594982
Evidence: scripts/ci/check_docker_runtime_dependency_surface.py:2639 filters positively identified foreign head repositories before dereferencing attempts, checks the listed inventory and independently verifies selected same-repository attempt identity. Foreign-only or malformed evidence does not qualify.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2503#discussion_r4663421883 -> a968e0ca9c1c2d19d0b8d9b3bcd0f90a87594982

Disposition: FIXED
Commit: 486d2f0aad8d2e255af458188710bf19dfb653f9
Evidence: .github/workflows/cd.yml:349 admits rate-limited reads within Retry-After and remaining time, and typed temporary timeout/reset. The fixed repository, exact uploaded ID, deadline, three requests and existing verification remain enforced.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2503#discussion_r4663645148 -> 486d2f0aad8d2e255af458188710bf19dfb653f9

Disposition: FIXED
Commit: 486d2f0aad8d2e255af458188710bf19dfb653f9
Evidence: scripts/ci/check_docker_runtime_dependency_surface.py:4355 types the isolated worker fetch signature. The same source commit declares typed arguments and return value for pages in the Frontend workflow.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2503#discussion_r4663645161 -> 486d2f0aad8d2e255af458188710bf19dfb653f9

Disposition: FIXED
Commit: a5e2c67dd8e79476845f5416a04f0079f7898b1d
Evidence: .github/workflows/cd.yml:2085 The CD classifier reads its own CD base blob. The native shell fixture covers both divergence directions and the equal-pin baseline.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2503#discussion_r4665836871 -> a5e2c67dd8e79476845f5416a04f0079f7898b1d

Disposition: FIXED
Commit: 89c7e9247c484eb6121e975e02ce80aa583e97bc
Evidence: scripts/ci/check_docker_runtime_dependency_surface.py:1023 binds the original source, Q/S/C descriptors, archive and all three actual BASE image operands. The outside-diff Caddy wrong-subject case is covered alongside the individual roots.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2503#pullrequestreview-6006038566 -> 89c7e9247c484eb6121e975e02ce80aa583e97bc

Disposition: FIXED
Commit: 89c7e9247c484eb6121e975e02ce80aa583e97bc
Evidence: scripts/ci/check_docker_runtime_dependency_surface.py:2168 and the independent caller-byte check address the original substantive findings. The ten individual roots have separate source- or artifact-backed dispositions.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2503#pullrequestreview-6006042589 -> 89c7e9247c484eb6121e975e02ce80aa583e97bc

Disposition: FIXED
Commit: dcf14758ee5bf182493750fc88e3d5ebc28e45cd
Evidence: scripts/ci/check_docker_runtime_dependency_surface.py:1410 bounds the exact transmitted ZIP before upload and verifies its actual size, digest and original source horizon. The historical 284-member positive retained all contents and modes. Negative AM routes now assert individual causes; the fixed public operand vector independently changes only the candidate ZIP digest.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2503#pullrequestreview-6007574535 -> dcf14758ee5bf182493750fc88e3d5ebc28e45cd

Disposition: FIXED
Commit: 03d5125770d7c7f73f90b73c786c2c511447b976
Evidence: scripts/ci/check_docker_runtime_dependency_surface.py:1698 supplies the same native content check to producer and reader. The final PR verification uses one independently initialized read context across requests; scripts/AGENTS.md:289 describes the original reopened event on the same PR and head.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2503#pullrequestreview-6008145741 -> 03d5125770d7c7f73f90b73c786c2c511447b976

Disposition: FIXED
Commit: 59640e69f54ad0f77377a6e306150863bbfb9d9a
Evidence: scripts/ci/check_docker_runtime_dependency_surface.py:4500 checks uploader ceiling plus the reserved readback while charging only the uploader share. tests/test_docker_runtime_dependency_surface.py:5104 verifies the pinned uploader’s run-native retention clamp before BUILD; the actual artifact expiry is still read back from GitHub.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2503#pullrequestreview-6008551334 -> 59640e69f54ad0f77377a6e306150863bbfb9d9a

Disposition: FIXED
Commit: 42f9ee33d8cf6b9f9eb567a3afd4b529e13fd12d
Evidence: .github/workflows/cd.yml:348 restricts retries to the exact freshly uploaded ID and selected transient HTTP statuses under the existing one-minute job step. The native postcondition is also proven on the original retained upload 14698994798. The related inline fixes have their own source entries.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2503#pullrequestreview-6009398523 -> 42f9ee33d8cf6b9f9eb567a3afd4b529e13fd12d

Disposition: FIXED
Commit: 218ec3f324c1e15110888e60b2ce3b2e17b400d2
Evidence: scripts/ci/check_docker_runtime_dependency_surface.py:883 closes the stale live-base defect. The related route coverage and formatting have individual receipts. The two inapplicable claims have explicit source evidence and the residual duplicate-cost scenario is tracked in MAIN-RECOVERY-1.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2503#pullrequestreview-6017536874 -> 218ec3f324c1e15110888e60b2ce3b2e17b400d2

Disposition: FIXED
Commit: a968e0ca9c1c2d19d0b8d9b3bcd0f90a87594982
Evidence: scripts/ci/check_docker_runtime_dependency_surface.py:2761 selects unique open maintenance PRs for a live branch, so a prior closed PR cannot veto the current valid one. Historical main selection retains its all-state lookup. The two inline findings have separate evidence entries.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2503#pullrequestreview-6018579213 -> a968e0ca9c1c2d19d0b8d9b3bcd0f90a87594982

Disposition: FIXED
Commit: 486d2f0aad8d2e255af458188710bf19dfb653f9
Evidence: .github/workflows/cd.yml:349 and the related workflow type annotations correct the two actionable omissions. Separate entries cite raw S modes, visible spent builds and the isolated module clock fixture for the three other comments.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2503#pullrequestreview-6018864769 -> 486d2f0aad8d2e255af458188710bf19dfb653f9

Disposition: FIXED
Commit: a5e2c67dd8e79476845f5416a04f0079f7898b1d
Evidence: .github/workflows/cd.yml:2085 The demonstrated CD baseline-owner mismatch was fixed and tested. The separate visible failed build claim is addressed by the native spent gate and original failed W5 job.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2503#pullrequestreview-6021722121 -> a5e2c67dd8e79476845f5416a04f0079f7898b1d

Disposition: NOT-A-BUG
Evidence: scripts/ci/fetch_docker_source_artifacts.py:2774; the pinned upload action emitted the bare SHA-256 for original support run 44884735732, job 136787453655. Its REST artifact 14698994798 uses the corresponding sha256-prefixed value.
Reason: The checker compares the two actual output formats after applying the required prefix to the action digest.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2503#discussion_r4653179648

Disposition: NOT-A-BUG
Evidence: scripts/ci/fetch_docker_source_artifacts.py:8301; original authenticated support ZIPs 14200227448, 14673652074 and 14698994798 matched the native footer modes for all 91 files in each archive.
Reason: The preserved ZIP member modes agree with the producer evidence. The historical replay accepted all three archives using their actual mode, CRC and content.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2503#discussion_r4653179657

Disposition: NOT-A-BUG
Evidence: scripts/ci/fetch_docker_source_artifacts.py:12292 and scripts/ci/fetch_docker_source_artifacts.py:12334; the native mapping-successor and wrong-mapping cases in tests/test_deploy_contract_scripts.py:19596 verify both outcomes.
Reason: For the direct mapping-only successor the code selects its parent before comparing the caller SHA. The prior published source used the same ordering.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2503#discussion_r4653179662

Disposition: NOT-A-BUG
Evidence: docs/security/CVE-2026-84445-alertmanager.md:974 and scripts/ci/fetch_docker_source_artifacts.py:2805 document and enforce the 2,240 MiB current S cap with independent class, member and compressed-byte limits.
Reason: The 2 GiB module-qualification limit continues to govern Q. The support archive has its own explicitly bounded producer and consumer checks.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2503#discussion_r4653179672

Disposition: NOT-A-BUG
Evidence: tests/test_deploy_contract_scripts.py:17760 and the generated base-to-head baseline comparison show only the two obsolete public deploy-helper fingerprints removed, 1,360 to 1,358.
Reason: The published base-to-head change already removes both old public pins. Later native hook updates preserved the full remaining fingerprint multiset.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2503#discussion_r4653179684

Disposition: NOT-A-BUG
Evidence: .github/workflows/frontend-ci.yml:728 records an observed build start before checking success and rejects prior starts at .github/workflows/frontend-ci.yml:824. Original W5 run 44962160496 includes a successful build step and failed overall job.
Reason: The successful-receipt filter controls reuse. The separate admission check also counts active and failed native starts for the same source.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2503#discussion_r4662589502

Disposition: NOT-A-BUG
Evidence: scripts/ci/fetch_docker_source_artifacts.py:81 defines 2240 MiB for the expanded current S payload and its own 384 MiB transport cap. Original support archive 14698994798 exercises the larger expanded envelope.
Reason: Q has a separate 2 GiB limit. S has its own documented expanded and uploaded size envelopes, including the footer.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2503#discussion_r4662589513

Disposition: NOT-A-BUG
Evidence: .github/workflows/frontend-ci.yml:728 records actual native starts before filtering successful artifacts. The original W5 native job 137023212928 failed after its build; a new build for that W is still rejected.
Reason: The reuse inventory requires success. Its separate spent-build gate includes prior failed native builds.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2503#discussion_r4663645128

Disposition: NOT-A-BUG
Evidence: scripts/ci/fetch_docker_source_artifacts.py:8476 compares the retained raw ZIP entry mode with its bound footer. Three genuine support ZIPs, including artifact 14698994798, retain native-support/trivy as 0555 in both; scanner payload is 168456354 bytes in each.
Reason: The checked raw ZIP metadata retains the source modes. The consumer reads this archive directly and restores the verified modes independently of a generic artifact download extractor.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2503#discussion_r4663645140

Disposition: NOT-A-BUG
Evidence: tests/test_docker_runtime_dependency_surface.py:5225 defines a clock fixture subclass. Three fixture identity checks confirm that standard-library datetime.datetime and its method owner remain intact and teardown restores the original module binding.
Reason: The scoped monkeypatch replaces the consumer module name, preserving the immutable built-in type.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2503#discussion_r4663645180

Disposition: NOT-A-BUG
Evidence: .github/workflows/frontend-ci.yml:729 records observed native build starts without testing whether the producer succeeded. The original W5 Caddy run 44962160496 failed after its native build and its same-source build allowance was spent.
Reason: Receipt selection admits only a successful producer for reuse. Independently, the workflow checks every observed started build for the same branch and source before it can start another.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2503#discussion_r4665836889

Disposition: NOT-A-BUG
Evidence: scripts/ci/check_docker_runtime_dependency_surface.py:2872 derives the two flags from mutually exclusive push and workflow_dispatch events. scripts/ci/fetch_docker_source_artifacts.py:11959 supplies only historical=True; its historical path enforces completed CI/CD at scripts/ci/check_docker_runtime_dependency_surface.py:2259.
Reason: An unsupported direct Python call can supply contradictory booleans and return via the live branch. No supported CLI, native workflow input or production caller can supply that pair or use its result to authorize historical reads.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2503#discussion_r4671331350

Disposition: NOT-A-BUG
Evidence: tests/test_docker_runtime_dependency_surface.py:4658 and the equivalent clock fixtures at lines 5256 and 5315 replace the consumer module attribute only. The recorded clock identity/teardown check verifies that the standard-library datetime class and now method retain identity.
Reason: The fixture installs a scoped module-local clock and restores it after the test. It does not mutate the built-in class or its methods.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2503#discussion_r4671331366

Disposition: NOT-A-BUG
Evidence: scripts/ci/check_docker_runtime_dependency_surface.py:2259 retains mandatory historical CI/CD evidence; tests/test_docker_runtime_dependency_surface.py:4658 uses an isolated consumer clock, with the earlier identity and teardown checks unchanged on W10.
Reason: The complete review contains the unsupported internal mode pair and a repeated fixture claim. The three native callers cannot request the pair; immutable datetime is preserved. Both inline findings are recorded separately.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2503#pullrequestreview-6028652177

## Review Material Seal
<!-- PULSEPLATE_PR_REVIEW_SEAL_V1_BEGIN -->
<!-- pragma: allowlist nextline secret -->
{"authority":"human_asserted_content_receipt","code_review":{"blocking":false,"material_digest":"sha256:7783b784e36f3e430b022d98ce24f10e9776ae293b8d3c926fd7605721451905","material_head_sha":"2985c4d4434233f5bc6e830c7c7a0ad6f0512b67","output_required":false,"review_claim":"none"},"codex_security":{"base_revision":"b96c7f66767d314e2952ea8180a7a3b499c16fce","blocking":false,"head_revision":"2985c4d4434233f5bc6e830c7c7a0ad6f0512b67","material_digest":"sha256:7783b784e36f3e430b022d98ce24f10e9776ae293b8d3c926fd7605721451905","no_findings_claim":false,"output_required":false,"scan_claim":"none"},"material":{"base_ref_oid":"b96c7f66767d314e2952ea8180a7a3b499c16fce","digest":"sha256:7783b784e36f3e430b022d98ce24f10e9776ae293b8d3c926fd7605721451905","material_head_sha":"2985c4d4434233f5bc6e830c7c7a0ad6f0512b67","merge_base_sha":"b96c7f66767d314e2952ea8180a7a3b499c16fce","policy_version":"pulseplate.material-classification/v1"},"pr_number":2503,"repository":"Katsiarynakavaleuskaya/PulsePlate","schema_version":"pulseplate.pr-review-seal/v1","self_review":{"actionable_findings_count":0,"authority":"repo_native_pulseplate_pr_review_advisory","blocking":false,"findings_count":1,"material_digest":"sha256:7783b784e36f3e430b022d98ce24f10e9776ae293b8d3c926fd7605721451905","material_head_sha":"2985c4d4434233f5bc6e830c7c7a0ad6f0512b67","report_payload":{"actionable_findings_count":0,"base_ref_oid":"b96c7f66767d314e2952ea8180a7a3b499c16fce","calibration":{"case_labels":["review-source-degraded","large-diff-risk"],"false_positive_controls":["clean context must produce zero findings","benign fixed-mapping presence must not become a governance finding","warnings and governance uncertainty remain actionable findings, not diagnostic notes","review-source degradation is status/warning only unless an explicit blocking source finding exists","large diff risk is review-planning evidence, not a merge-readiness claim"],"posting_eligible":false,"posting_gate":"GitHub posting remains out of scope until a dedicated calibrated posting PR.","rubric_version":"pr4-2026-04-28"},"coordinator_packet":{"path":"artifacts/orchestration/task_packets/bb4fe5049590.json","role_order":["agent-coordinator","architecture-specialist","security-auditor","qa-engineer-agent","bug-hunter","data-scientist-agent"],"task_packet_id":"bb4fe5049590"},"decision_log":["This report is advisory and side-effect free.","This report does not post GitHub comments, resolve review threads, merge PRs, or claim merge readiness.","External CodeRabbit, Sourcery, and Cubic statuses remain separate PR governance signals."],"deferred_followups":[],"findings":[{"category":"tests","diagnostic_code":"large_diff_review_risk","disposition_candidate":"NOT-A-BUG","evidence":"Diff contains 7293 changed lines, above review-risk threshold 800.","file":"docs/roadmap/BACKLOG_LEDGER.md","gate_to_run":"make validate-changed","line":null,"role_agent":"bug-hunter","severity":"note","suggested_fix":"Confirm PR split rationale and targeted deterministic gates before opening review."}],"findings_count":1,"gate_plan":["python3 scripts/orchestration/check_preflight.py","python3 scripts/orchestration/check_agent_consistency.py","python3 -m pytest tests/test_pr_review_report.py tests/test_pr_review_context.py -q","Add and fill docs/review/PR_<N>_FIXED_MAPPING.md before merge-ready loop","make test-fast","make validate-changed"],"generated_at_utc":"2026-11-23T22:00:12Z","material_digest":"sha256:7783b784e36f3e430b022d98ce24f10e9776ae293b8d3c926fd7605721451905","material_head_sha":"2985c4d4434233f5bc6e830c7c7a0ad6f0512b67","merge_base_sha":"b96c7f66767d314e2952ea8180a7a3b499c16fce","mode":"dry-run-report","review_source_status":[{"blocking":false,"evidence":"gh api repos/<repo>/pulls/<pr>","fallback_required":false,"reason":"","source":"github_pr_metadata","source_degraded":false,"status":"available"},{"blocking":false,"evidence":"b96c7f66767d314e2952ea8180a7a3b499c16fce..2985c4d4434233f5bc6e830c7c7a0ad6f0512b67","fallback_required":false,"reason":"","source":"git_diff","source_degraded":false,"status":"available"},{"blocking":false,"evidence":"docs/review/PR_2503_FIXED_MAPPING.md","fallback_required":true,"reason":"Fixed-mapping artifact unavailable","source":"fixed_mapping_artifact","source_degraded":true,"status":"unavailable"}],"role_review":[{"role_agent":"agent-coordinator","summary":"agent-coordinator has no deterministic findings from the supplied context."},{"role_agent":"architecture-specialist","summary":"architecture-specialist has no deterministic findings from the supplied context."},{"role_agent":"security-auditor","summary":"security-auditor has no deterministic findings from the supplied context."},{"role_agent":"qa-engineer-agent","summary":"qa-engineer-agent has no deterministic findings from the supplied context."},{"role_agent":"bug-hunter","summary":"bug-hunter flagged 1 advisory finding(s) for human review."},{"role_agent":"data-scientist-agent","summary":"data-scientist-agent has no scoring calibration changes in this dry-run report."}],"schema_version":"2.0.0","scope_reviewed":{"changed_files":[".github/workflows/cd.yml",".github/workflows/ci.yml",".github/workflows/frontend-ci.yml",".secrets.baseline","AGENTS.md","docs/roadmap/BACKLOG_LEDGER.md","docs/security/CVE-2026-84445-alertmanager.md","scripts/AGENTS.md","scripts/ci/check_docker_runtime_dependency_surface.py","scripts/ci/fetch_docker_source_artifacts.py","scripts/deploy.sh","scripts/deploy_production.sh","tests/test_caddy_deploy_provenance.py","tests/test_cd_workflow_production_deploy_gate.py","tests/test_ci_workflow_pr_size_governance_contract.py","tests/test_deploy_contract_scripts.py","tests/test_docker_runtime_dependency_surface.py","tests/test_docker_workflow_build_path_contract.py"],"diff_summary":{"additions":6811,"changed_lines":7293,"deletions":482,"files":18},"fixed_mapping_errors":[],"omitted_surfaces":["GitHub posting","PR thread resolution","merge readiness claims"],"pr_metadata_available":true,"scoped_agents_md":["AGENTS.md","scripts/AGENTS.md","tests/AGENTS.md"]},"warnings":[]},"report_sha256":"sha256:ccbd44c0d8f2a379f57793f1ba9ad37e8acfdedf2de6b1ad2ba02eb49ba9a3d5","review_claim":"none","review_tool":"pulseplate-pr-review","schema_version":"pulseplate.self-review-advisory/v1","status":"advisory_report_attached"}}
<!-- PULSEPLATE_PR_REVIEW_SEAL_V1_END -->
