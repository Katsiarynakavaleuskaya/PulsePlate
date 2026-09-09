# PR 2347 — Review Governance

Review-Seal-Version: v1

## Lane Start Provenance
Packet: `artifacts/orchestration/task_packets/a17be0c6d330.json`

## Experiment Runner Evidence
Artifact: `artifacts/orchestration/experiments/results/pr2347-closeout-8c7fa726-structural-reviewed.json`

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

Disposition: FIXED
Commit: d1f308ee8bfe5b2c4705ffdcd0b2ba9b4511dd19
Evidence: Production archive includes scripts/ops/postgres_backup.sh; deploy contracts validate, synchronize, mode-check, and bind its contents before use.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2347#discussion_r3875744714 -> d1f308ee8bfe5b2c4705ffdcd0b2ba9b4511dd19

Disposition: FIXED
Commit: 57f62dd0454db69f1fc4fd389ff7c0fd4f308c2a
Evidence: Both deploy scripts preserve ambiguous PostgreSQL stop status while keeping product writers quiesced; test_old_postgres_stop_failure_keeps_product_writers_quiesced proves no restart, candidate start, or migration.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2347#discussion_r3875806046 -> 57f62dd0454db69f1fc4fd389ff7c0fd4f308c2a

Disposition: FIXED
Commit: e1c79a6f74bcee69608d7f3d83ac4a1abf451ec2
Evidence: Non-evicting bounded read-only admission polling supersedes shared-concurrency pending-member eviction; tests/test_deploy_contract_scripts.py covers success and timeout.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2347#discussion_r3875806055 -> e1c79a6f74bcee69608d7f3d83ac4a1abf451ec2

Disposition: FIXED
Commit: e1c79a6f74bcee69608d7f3d83ac4a1abf451ec2
Evidence: CD package identity checks use the owner-scoped public package endpoint with the explicitly bound release context
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2347#discussion_r3875809967 -> e1c79a6f74bcee69608d7f3d83ac4a1abf451ec2

Disposition: FIXED
Commit: 57f62dd0454db69f1fc4fd389ff7c0fd4f308c2a
Evidence: Provenance reuse normalization removes commit-varying source_sha while preserving material conflict detection
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2347#discussion_r3875809978 -> 57f62dd0454db69f1fc4fd389ff7c0fd4f308c2a

Disposition: FIXED
Commit: 57f62dd0454db69f1fc4fd389ff7c0fd4f308c2a
Evidence: Deployment regression asserts the full inspected old PostgreSQL container identity is not stopped on pre-switch failure
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2347#discussion_r3875809990 -> 57f62dd0454db69f1fc4fd389ff7c0fd4f308c2a

Disposition: FIXED
Commit: e1c79a6f74bcee69608d7f3d83ac4a1abf451ec2
Evidence: CD package checks use the exact owner-scoped package endpoint; tests/test_deploy_contract_scripts.py enforces it.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2347#discussion_r3876521066 -> e1c79a6f74bcee69608d7f3d83ac4a1abf451ec2

Disposition: FIXED
Commit: e1c79a6f74bcee69608d7f3d83ac4a1abf451ec2
Evidence: Production backup helper is bound to the same Compose project directory and file as the deployment wrapper; deterministic deploy-contract tests prove identity and receipt.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2347#discussion_r3876521073 -> e1c79a6f74bcee69608d7f3d83ac4a1abf451ec2

Disposition: FIXED
Commit: e1c79a6f74bcee69608d7f3d83ac4a1abf451ec2
Evidence: Production deploy establishes umask 077 before tokenless or authenticated paths; deterministic tests prove backup receipt mode 0600.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2347#discussion_r3876521077 -> e1c79a6f74bcee69608d7f3d83ac4a1abf451ec2

Disposition: FIXED
Commit: e1c79a6f74bcee69608d7f3d83ac4a1abf451ec2
Evidence: Reuse stays outside publisher concurrency and performs bounded read-only admission polling; deterministic ready-after-two and timeout tests pass.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2347#discussion_r3877937244 -> e1c79a6f74bcee69608d7f3d83ac4a1abf451ec2

Disposition: FIXED
Commit: e1c79a6f74bcee69608d7f3d83ac4a1abf451ec2
Evidence: SPDX mode is passed explicitly and current source-digest filtering is limited to creation; historical-source reuse arguments are covered by deterministic tests.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2347#discussion_r3877937247 -> e1c79a6f74bcee69608d7f3d83ac4a1abf451ec2

Disposition: FIXED
Commit: d1f308ee8bfe5b2c4705ffdcd0b2ba9b4511dd19
Evidence: PostgreSQL reuse job timeout is 90 minutes and deterministically covers its 60-minute wait plus scan and verification tail
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2347#discussion_r3878161130 -> d1f308ee8bfe5b2c4705ffdcd0b2ba9b4511dd19

Disposition: FIXED
Commit: d1f308ee8bfe5b2c4705ffdcd0b2ba9b4511dd19
Evidence: Both deploy scripts leave captured writers quiesced on pre- or post-backup identity revalidation failure; deterministic tests execute all four branches.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2347#discussion_r3878171938 -> d1f308ee8bfe5b2c4705ffdcd0b2ba9b4511dd19

Disposition: FIXED
Commit: d1f308ee8bfe5b2c4705ffdcd0b2ba9b4511dd19
Evidence: Reuse admission parses the canonical tag manifest and requires its unique linux/amd64 digest to equal the frozen runtime digest; ready and timeout paths are tested.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2347#discussion_r3878171948 -> d1f308ee8bfe5b2c4705ffdcd0b2ba9b4511dd19

Disposition: FIXED
Commit: d1f308ee8bfe5b2c4705ffdcd0b2ba9b4511dd19
Evidence: Registry credentials are destroyed before repository-controlled tests and reauthenticated only in a later bounded publication step; credential-order tests pass.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2347#discussion_r3878200535 -> d1f308ee8bfe5b2c4705ffdcd0b2ba9b4511dd19

Disposition: FIXED
Commit: bd049bd1936a3425a52e9fba2df4f4a98559e632
Evidence: Verified reused SPDX predicate content is compared with the freshly generated exact Trivy SBOM; matching, mismatch, and duplicate cases are tested.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2347#discussion_r3879791265 -> bd049bd1936a3425a52e9fba2df4f4a98559e632

Disposition: FIXED
Commit: bd049bd1936a3425a52e9fba2df4f4a98559e632
Evidence: The verified upstream pgvector LICENSE is installed as a regular mode-0644 file; reproducible builds, runtime hash, and suppression-free Trivy evidence passed.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2347#discussion_r3879791270 -> bd049bd1936a3425a52e9fba2df4f4a98559e632

Disposition: FIXED
Commit: bd049bd1936a3425a52e9fba2df4f4a98559e632
Evidence: Promotion freshness binds the publication-authority workflow plus recipe and manifest; a policy-only main change revokes an in-flight publisher in tests.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2347#discussion_r3879791279 -> bd049bd1936a3425a52e9fba2df4f4a98559e632

Disposition: FIXED
Commit: bb028f523b4f9e0c5fe163fcf3e4645664e381a4
Evidence: Both deploy scripts keep writers quiesced when backup execution or receipt validation fails; staging and production failure branches are executed by tests.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2347#discussion_r3879979702 -> bb028f523b4f9e0c5fe163fcf3e4645664e381a4

Disposition: FIXED
Commit: bb028f523b4f9e0c5fe163fcf3e4645664e381a4
Evidence: The production archive admits and requires the self-hosted Compose member; managed and self-hosted archive preflight carriers are tested.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2347#discussion_r3879979706 -> bb028f523b4f9e0c5fe163fcf3e4645664e381a4

Disposition: FIXED
Commit: bb028f523b4f9e0c5fe163fcf3e4645664e381a4
Evidence: A separate fresh-runner admission waits for exact-main CI and pgvector compatibility before the credentialed publisher; success, failed-CI, and timeout states are tested.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2347#discussion_r3880003768 -> bb028f523b4f9e0c5fe163fcf3e4645664e381a4

Disposition: FIXED
Commit: 4646e7053a6b43355f37fe818d169ce91e939835
Evidence: The CD contract binds the exact current whole-manifest SHA-256 and deterministic tests recompute the same hash.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2347#discussion_r3880720295 -> 4646e7053a6b43355f37fe818d169ce91e939835

Disposition: FIXED
Commit: 4646e7053a6b43355f37fe818d169ce91e939835
Evidence: Both deploy scripts require the current manifest config digest; deterministic manifest and repeat-deploy census tests pass.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2347#discussion_r3880720299 -> 4646e7053a6b43355f37fe818d169ce91e939835

Disposition: FIXED
Commit: 4646e7053a6b43355f37fe818d169ce91e939835
Evidence: Containerfile sets and verifies the installed pgvector LICENSE mtime against SOURCE_DATE_EPOCH
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2347#discussion_r3880744505 -> 4646e7053a6b43355f37fe818d169ce91e939835

Disposition: FIXED
Commit: 4646e7053a6b43355f37fe818d169ce91e939835
Evidence: PGvector contract test scopes platform digest evidence to contract and publisher job boundaries instead of the whole workflow
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2347#discussion_r3880744522 -> 4646e7053a6b43355f37fe818d169ce91e939835

Disposition: FIXED
Commit: 28dbf1309398a45144efce59a1b677e4e9bca66c
Evidence: CD runs exact-head pgvector compatibility directly on its own fresh runner; job, service, checkout, and publisher dependency are tested.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2347#discussion_r3883973291 -> 28dbf1309398a45144efce59a1b677e4e9bca66c

Disposition: FIXED
Commit: 28dbf1309398a45144efce59a1b677e4e9bca66c
Evidence: CD no longer polls the separately cancelable CI workflow; exact-head compatibility is local to the non-canceling CD run and contract tests enforce it.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2347#discussion_r3883973294 -> 28dbf1309398a45144efce59a1b677e4e9bca66c

Disposition: FIXED
Commit: 28dbf1309398a45144efce59a1b677e4e9bca66c
Evidence: Standalone reuse generates an exact Trivy SPDX document and verifies predicate equality; match, mismatch, and duplicate-attestation cases are tested.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2347#discussion_r3883973296 -> 28dbf1309398a45144efce59a1b677e4e9bca66c

Disposition: FIXED
Commit: 28dbf1309398a45144efce59a1b677e4e9bca66c
Evidence: Publisher is bound to the protected pgvector-publish environment restricted to main; workflow contract tests enforce the environment binding.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2347#discussion_r3883991826 -> 28dbf1309398a45144efce59a1b677e4e9bca66c

Disposition: FIXED
Commit: 0d29de57df995524f3cce700d85f9c39ff64937a
Evidence: Standalone reuse normalizes only volatile SPDX metadata before equality while keeping package, relationship, and creator content exact; drift cases are tested.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2347#discussion_r3884235954 -> 0d29de57df995524f3cce700d85f9c39ff64937a

Disposition: FIXED
Commit: 0d29de57df995524f3cce700d85f9c39ff64937a
Evidence: The CD workflow is part of the closed publisher-trigger set, so publication-policy-only main changes run a replacement publisher; classifier tests enforce it.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2347#discussion_r3884235956 -> 0d29de57df995524f3cce700d85f9c39ff64937a

Disposition: FIXED
Commit: 532d9944b156f9faf1d44ee4b53650444f09ca24
Evidence: Standalone reuse normalizes the tag-derived SPDX document name plus volatile metadata while package and relationship content remain exact; drift cases are tested.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2347#discussion_r3885849283 -> 532d9944b156f9faf1d44ee4b53650444f09ca24

Disposition: FIXED
Commit: cf7ace9aa7636252a23fbe95eaeabe5d3ad61aeb
Evidence: Both deploy scripts admit a fresh PostgreSQL path only after a successful full volume census proves the exact name absent; absent, present, malformed, and daemon-failure cases are tested.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2347#discussion_r3885944435 -> cf7ace9aa7636252a23fbe95eaeabe5d3ad61aeb

Disposition: FIXED
Commit: c091ff3db3e064c736b0166e04ec5325f4d7b9d1
Evidence: .github/workflows/cd.yml post-promotion exact-main fence plus canonical-tag supersession regression
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2347#discussion_r3886123118 -> c091ff3db3e064c736b0166e04ec5325f4d7b9d1

Disposition: FIXED
Commit: f411493f0781d9a2cc8f880c89c6885243efbf94
Evidence: Staging and self-hosted deploy paths perform a second definitive volume census immediately before the single PostgreSQL start
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2347#discussion_r3887313894 -> f411493f0781d9a2cc8f880c89c6885243efbf94

Disposition: FIXED
Commit: 59bc354fb1050829a320fa0f96cccb099d7b691a
Evidence: Shallow fallback fetches execute only in an isolated temporary bare Git repository
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2347#discussion_r3887551520 -> 59bc354fb1050829a320fa0f96cccb099d7b691a

Disposition: FIXED
Commit: 1f0ad5df0373ba035b98280deef08fa50162fe9c
Evidence: Compatibility admission uses only credential-free repository variables and rejects secrets.* or DEVPI_CI_* reintroduction
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2347#discussion_r3887759530 -> 1f0ad5df0373ba035b98280deef08fa50162fe9c

Disposition: FIXED
Commit: 2961f18a05ed34e55bac73961344a6455a3bb2fc
Evidence: The main classifier now covers the complete finite pgvector compatibility surface aligned with canonical CI; executable classifier tests prove migration changes publish and unrelated docs reuse.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2347#discussion_r3893430516 -> 2961f18a05ed34e55bac73961344a6455a3bb2fc

Disposition: FIXED
Commit: 2961f18a05ed34e55bac73961344a6455a3bb2fc
Evidence: Read-only reuse now performs one terminal current-main compatibility diff and canonical-tag/digest recheck; deterministic tests prove unrelated advance PASS and relevant/tag drift HOLD.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2347#discussion_r3893430530 -> 2961f18a05ed34e55bac73961344a6455a3bb2fc

Disposition: FIXED
Commit: 2961f18a05ed34e55bac73961344a6455a3bb2fc
Evidence: Staging preflight now requires rendered app and worker DSNs to match the local PostgreSQL service credentials/database before pull or quiesce; missing, external, and divergent DSNs fail in deterministic tests.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2347#discussion_r3893430539 -> 2961f18a05ed34e55bac73961344a6455a3bb2fc

Disposition: FIXED
Commit: 3e02c17469f2e7fe076b70858b88b614b698390a
Evidence: scripts/deploy.sh:1054 and scripts/deploy_production.sh:2721 propagate the exact selected ENV_FILE; scripts/ops/postgres_backup.sh:35 passes it through docker compose --env-file; tests/test_deploy_contract_scripts.py:6809 and tests/test_deploy_contract_scripts.py:7045 prove staging override and helper-contract behavior; focused deploy tests, make validate-changed, and pre-commit run --all-files pass.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2347#discussion_r3897476612 -> 3e02c17469f2e7fe076b70858b88b614b698390a

Disposition: FIXED
Commit: 47ae368bcc11cea249b495878becf8bd52d2c19f
Evidence: scripts/deploy.sh:738 and scripts/deploy_production.sh:2221 now fail the product-service census on Docker inspect failure; scripts/deploy.sh:745 and scripts/deploy_production.sh:2228 reject every non-boolean running state; tests/test_deploy_contract_scripts.py:7055 executes both scripts against inspect failure, malformed output, and multi-line output; full deploy tests, make validate-changed, and pre-commit run --all-files pass.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2347#discussion_r3907640271 -> 47ae368bcc11cea249b495878becf8bd52d2c19f

Disposition: FIXED
Commit: 8c7fa72631b90e5a5a1708c5a9af2296e9244de5
Evidence: The owner-approved official-image transition removes scripts/ci/prometheus_derivative_candidate.py, including its first-use artifact-root path; immutable official selection is enforced by deploy/prometheus/image-manifest.json:1 and tests/test_deploy_contract_scripts.py:361.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2347#discussion_r3944486298 -> 8c7fa72631b90e5a5a1708c5a9af2296e9244de5

Disposition: FIXED
Commit: 8c7fa72631b90e5a5a1708c5a9af2296e9244de5
Evidence: The owner-approved official-image transition deletes scripts/ci/_prometheus_derivative_transport.py and its subprocess capture/build path; no unmerged derivative command remains. Current-head CD Prometheus security run 34272969121 validates the selected official digest.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2347#discussion_r3944486300 -> 8c7fa72631b90e5a5a1708c5a9af2296e9244de5

Disposition: FIXED
Commit: 8c7fa72631b90e5a5a1708c5a9af2296e9244de5
Evidence: The owner-approved official-image transition deletes prometheus_derivative_candidate.py and its candidate workflow-dispatch path; no candidate dispatch or derivative publication remains. The ordinary post-merge build/publish path is preserved.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2347#discussion_r3944486301 -> 8c7fa72631b90e5a5a1708c5a9af2296e9244de5

Disposition: FIXED
Commit: f8d7078d968739af0db81c31864e6d587251ac75
Evidence: .github/workflows/cd.yml:861 executes the complete canonical Alembic, binding, extension, vector-query and RLS suite before publication; tests/test_deploy_contract_scripts.py:7667 proves exact target parity and nonzero test failure propagation.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2347#discussion_r3944900727 -> f8d7078d968739af0db81c31864e6d587251ac75

Disposition: FIXED
Commit: f8d7078d968739af0db81c31864e6d587251ac75
Evidence: scripts/deploy_production.sh:266 normalizes a relative ENV_FILE against DEPLOY_DIR before sourcing/exporting it; deploy/AGENTS.md:214 records the parent-selected path contract and the full deploy contract suite passed.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2347#discussion_r3944900731 -> f8d7078d968739af0db81c31864e6d587251ac75

Disposition: FIXED
Commit: 8c7fa72631b90e5a5a1708c5a9af2296e9244de5
Evidence: The owner-approved official-image transition removes _prometheus_derivative_transport.py and its config-response MIME comparison; the replacement official-image v2 contract binds the recorded index, platform manifest, config and binary revision in the successful current-head CD run 34272969121.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2347#discussion_r3955352807 -> 8c7fa72631b90e5a5a1708c5a9af2296e9244de5

Disposition: FIXED
Commit: 8c7fa72631b90e5a5a1708c5a9af2296e9244de5
Evidence: The owner-approved official-image transition removes _prometheus_derivative_transport.py and the compressed candidate OCI archive parser/extractor; no unmerged derivative archive intake remains. The admitted official image is verified directly at its immutable registry digest.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2347#discussion_r3955352812 -> 8c7fa72631b90e5a5a1708c5a9af2296e9244de5

Disposition: FIXED
Commit: 7e74dd6fd8215a31ab48b775e9a5c7be031d3dbf
Evidence: Production bundle and deploy contract bind the reviewed scripts/ops/postgres_backup.sh helper before self-hosted cutover
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2347#pullrequestreview-5045531851 -> 7e74dd6fd8215a31ab48b775e9a5c7be031d3dbf

Disposition: FIXED
Commit: e1c79a6f74bcee69608d7f3d83ac4a1abf451ec2
Evidence: Consolidated CodeRabbit package, provenance, container-identity, and release-context review findings are covered by the reviewed workflow and tests
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2347#pullrequestreview-5045605961 -> e1c79a6f74bcee69608d7f3d83ac4a1abf451ec2

Disposition: FIXED
Commit: e1c79a6f74bcee69608d7f3d83ac4a1abf451ec2
Evidence: SPDX reuse omits current source-digest binding and read-only admission has bounded non-cancelling concurrency evidence
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2347#pullrequestreview-5047946377 -> e1c79a6f74bcee69608d7f3d83ac4a1abf451ec2

Disposition: FIXED
Commit: d1f308ee8bfe5b2c4705ffdcd0b2ba9b4511dd19
Evidence: The sole actionable timeout finding is fixed and guarded by the closed reuse-state-machine contract test
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2347#pullrequestreview-5048191394 -> d1f308ee8bfe5b2c4705ffdcd0b2ba9b4511dd19

Disposition: FIXED
Commit: 4646e7053a6b43355f37fe818d169ce91e939835
Evidence: Both actionable LICENSE reproducibility and publisher-scoped digest assertions are fixed with exact regression coverage
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2347#pullrequestreview-5051266573 -> 4646e7053a6b43355f37fe818d169ce91e939835

Disposition: FIXED
Commit: 829a5be64416191597ec7123c0eee34a4222e2f0
Evidence: Production archive regex now requires scripts/ops/postgres_backup.sh and deploy/postgres-pgvector/image-manifest.json in canonical order
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2347#pullrequestreview-5055358328 -> 829a5be64416191597ec7123c0eee34a4222e2f0

Disposition: NOT-A-BUG
Evidence: AGENTS.md:159 permits valid feedback with a correct current implementation; the Review Material Seal below binds exact material 8c7fa72631b90e5a5a1708c5a9af2296e9244de5, base 87feb5272ca81aa698416c5ed999d26e79f21b2a and digest sha256:3e2ac327c0542f211ce11d56accb416cbc08f017aaf683c4efa475086cb5dd3c. Fresh native self-review and Apple oracle exp-20260909c347 validate this material; current-head CI and strict seal validation remain required.
Reason: The operator explicitly approved ordinary NOT-A-BUG disposition of this historical-only stale-seal comment. Its observation described the intermediate receipt at cfe313c3a7413b201000d953a4dcd9716df5c4fd, not an independent runtime or security defect. Subsequent authorized material work invalidated that receipt; this closeout regenerates and validates the exact current binding. This does not claim the historical receipt was valid, waive any current material or security check, or grant merge authority.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2347#discussion_r3944680852

## Review Material Seal
<!-- PULSEPLATE_PR_REVIEW_SEAL_V1_BEGIN -->
<!-- pragma: allowlist nextline secret -->
{"authority":"human_asserted_content_receipt","code_review":{"blocking":false,"material_digest":"sha256:3e2ac327c0542f211ce11d56accb416cbc08f017aaf683c4efa475086cb5dd3c","material_head_sha":"8c7fa72631b90e5a5a1708c5a9af2296e9244de5","output_required":false,"review_claim":"none"},"codex_security":{"base_revision":"87feb5272ca81aa698416c5ed999d26e79f21b2a","blocking":false,"head_revision":"8c7fa72631b90e5a5a1708c5a9af2296e9244de5","material_digest":"sha256:3e2ac327c0542f211ce11d56accb416cbc08f017aaf683c4efa475086cb5dd3c","no_findings_claim":false,"output_required":false,"scan_claim":"none"},"material":{"base_ref_oid":"87feb5272ca81aa698416c5ed999d26e79f21b2a","digest":"sha256:3e2ac327c0542f211ce11d56accb416cbc08f017aaf683c4efa475086cb5dd3c","material_head_sha":"8c7fa72631b90e5a5a1708c5a9af2296e9244de5","merge_base_sha":"87feb5272ca81aa698416c5ed999d26e79f21b2a","policy_version":"pulseplate.material-classification/v1"},"pr_number":2347,"repository":"Katsiarynakavaleuskaya/PulsePlate","schema_version":"pulseplate.pr-review-seal/v1","self_review":{"actionable_findings_count":0,"authority":"repo_native_pulseplate_pr_review_advisory","blocking":false,"findings_count":1,"material_digest":"sha256:3e2ac327c0542f211ce11d56accb416cbc08f017aaf683c4efa475086cb5dd3c","material_head_sha":"8c7fa72631b90e5a5a1708c5a9af2296e9244de5","report_payload":{"actionable_findings_count":0,"base_ref_oid":"87feb5272ca81aa698416c5ed999d26e79f21b2a","calibration":{"case_labels":["large-diff-risk"],"false_positive_controls":["clean context must produce zero findings","benign fixed-mapping presence must not become a governance finding","warnings and governance uncertainty remain actionable findings, not diagnostic notes","review-source degradation is status/warning only unless an explicit blocking source finding exists","large diff risk is review-planning evidence, not a merge-readiness claim"],"posting_eligible":false,"posting_gate":"GitHub posting remains out of scope until a dedicated calibrated posting PR.","rubric_version":"pr4-2026-04-28"},"coordinator_packet":{"path":"artifacts/orchestration/task_packets/a17be0c6d330.json","role_order":["agent-coordinator","architecture-specialist","security-auditor","qa-engineer-agent","bug-hunter","data-scientist-agent"],"task_packet_id":"a17be0c6d330"},"decision_log":["This report is advisory and side-effect free.","This report does not post GitHub comments, resolve review threads, merge PRs, or claim merge readiness.","External CodeRabbit, Sourcery, and Cubic statuses remain separate PR governance signals."],"deferred_followups":[],"findings":[{"category":"tests","diagnostic_code":"large_diff_review_risk","disposition_candidate":"NOT-A-BUG","evidence":"Diff contains 9836 changed lines, above review-risk threshold 800.","file":"docs/roadmap/BACKLOG_LEDGER.md","gate_to_run":"make validate-changed","line":null,"role_agent":"bug-hunter","severity":"note","suggested_fix":"Confirm PR split rationale and targeted deterministic gates before opening review."}],"findings_count":1,"gate_plan":["python3 scripts/orchestration/check_preflight.py","python3 scripts/orchestration/check_agent_consistency.py","python3 -m pytest tests/test_pr_review_report.py tests/test_pr_review_context.py -q","make test-fast","make validate-changed"],"generated_at_utc":"2026-09-08T22:03:26Z","material_digest":"sha256:3e2ac327c0542f211ce11d56accb416cbc08f017aaf683c4efa475086cb5dd3c","material_head_sha":"8c7fa72631b90e5a5a1708c5a9af2296e9244de5","merge_base_sha":"87feb5272ca81aa698416c5ed999d26e79f21b2a","mode":"dry-run-report","review_source_status":[{"blocking":false,"evidence":"gh api repos/<repo>/pulls/<pr>","fallback_required":false,"reason":"","source":"github_pr_metadata","source_degraded":false,"status":"available"},{"blocking":false,"evidence":"87feb5272ca81aa698416c5ed999d26e79f21b2a..8c7fa72631b90e5a5a1708c5a9af2296e9244de5","fallback_required":false,"reason":"","source":"git_diff","source_degraded":false,"status":"available"},{"blocking":false,"evidence":"docs/review/PR_2347_FIXED_MAPPING.md","fallback_required":false,"reason":"","source":"fixed_mapping_artifact","source_degraded":false,"status":"available"}],"role_review":[{"role_agent":"agent-coordinator","summary":"agent-coordinator has no deterministic findings from the supplied context."},{"role_agent":"architecture-specialist","summary":"architecture-specialist has no deterministic findings from the supplied context."},{"role_agent":"security-auditor","summary":"security-auditor has no deterministic findings from the supplied context."},{"role_agent":"qa-engineer-agent","summary":"qa-engineer-agent has no deterministic findings from the supplied context."},{"role_agent":"bug-hunter","summary":"bug-hunter flagged 1 advisory finding(s) for human review."},{"role_agent":"data-scientist-agent","summary":"data-scientist-agent has no scoring calibration changes in this dry-run report."}],"schema_version":"2.0.0","scope_reviewed":{"changed_files":[".github/workflows/build.yml",".github/workflows/cd.yml",".github/workflows/ci.yml",".github/workflows/ios-appstore-assets.yml",".github/workflows/trivy.yml",".secrets.baseline","deploy/AGENTS.md","deploy/docker-compose.production.selfhosted.yaml","deploy/docker-compose.production.yaml","deploy/docker-compose.staging.yaml","deploy/postgres-pgvector/Containerfile","deploy/postgres-pgvector/image-manifest.json","deploy/prometheus/image-manifest.json","docs/deploy/OPERATIONAL_SIGNALS.md","docs/roadmap/BACKLOG_LEDGER.md","docs/security/PR_2347_CVE_2026_84304_GRPC_GO_DERIVATIVE_REMEDIATION.md","docs/security/PR_2347_CVE_2026_85396_RUBYZIP_REMEDIATION.md","frontend/Dockerfile.caddy-spa","ios/AGENTS.md","ios/Gemfile","ios/Gemfile.lock","scripts/AGENTS.md","scripts/ci/check_rubyzip_fastlane.rb","scripts/deploy.sh","scripts/deploy_production.sh","scripts/ops/postgres_backup.sh","tests/AGENTS.md","tests/test_caddy_deploy_provenance.py","tests/test_canonical_application_lifespan.py","tests/test_cd_workflow_production_deploy_gate.py","tests/test_cfpropertylist_ruby_compatibility_guard.py","tests/test_ci_workflow_pr_size_governance_contract.py","tests/test_deploy_contract_scripts.py","tests/test_ios_appstore_assets_workflow_contract.py","tests/test_pgvector_compat.py","tests/test_rubyzip_fastlane.rb","tests/test_runtime_toolchain_alignment.py"],"diff_summary":{"additions":9469,"changed_lines":9836,"deletions":367,"files":37},"fixed_mapping_errors":[],"omitted_surfaces":["GitHub posting","PR thread resolution","merge readiness claims"],"pr_metadata_available":true,"scoped_agents_md":["AGENTS.md","deploy/AGENTS.md","frontend/AGENTS.md","ios/AGENTS.md","scripts/AGENTS.md","tests/AGENTS.md"]},"warnings":[]},"report_sha256":"sha256:1e3f50a86de34c05453dc26dde6cb52b55e3b7e0e4f826cf3a657cb63dfc5af8","review_claim":"none","review_tool":"pulseplate-pr-review","schema_version":"pulseplate.self-review-advisory/v1","status":"advisory_report_attached"}}
<!-- PULSEPLATE_PR_REVIEW_SEAL_V1_END -->
