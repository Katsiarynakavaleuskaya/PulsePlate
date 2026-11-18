# Inline nosec TTL reassessment — 2026-09-30


## Current individual reassessment — 2026-10-31, PR #2494

Owner: Security/SRE. The original October30 review deadline was missed; this is
an actual October31 reassessment, not retrospective completion or calendar-only
renewal. Of the original45 annotations, B323 was removed by the verified-TLS fix;
43 existing conservative warnings were individually reviewed, and the remaining
domain B603 was qualified only after correcting its hostname/option ambiguity.
The44 surviving comments retain their rule and original reference. No new
suppression, scanner/config weakening, alias relocation or allowlist entry is added.

Manual review checkpoints are November30, December31 and January31. Hard remove-by
is2027-01-31 under the unchanged guard. Necessary native CLI operations and the
public reason key justify this finite interval; it is not an unfixed-CVE waiver.
No automatic renewal follows. Reassess immediately when executable/argv/caller
input, environment/trust, timeout/error behavior or a relevant finding changes.
The table records each site's actual controls and no-safe-equivalent rationale;
trusted checkout/PATH/CLI/daemon assumptions are bounded, not hostile-host proof.

Consumed native evidence: candidate7 mypy0,319 TLS cases including54 real TLS cases,
250 deadline cases and945 workflow cases; ordinary18-file Bandit0 findings/0errors,
unsuppressed54 findings/0errors and B323zero. Candidate9 domain mypy0 and118cases
with0failures/0errors/0skips; its fresh unsuppressed Bandit reports exactly B404/B603
with0errors. The domain fix rejects invalid/option-like names and derived-www
overflow before effects, explicitly binds dig -q/-t, and preserves verified HTTPS.
It does not establish DNS ownership, safe resolved addresses or general TLS safety.
Source/test anchors: `scripts/check_domain_tls.py:60`,
`tests/test_check_domain_tls.py:331`,
`scripts/ci/install_locked_python_requirements.py:2640`,
`tests/test_install_locked_python_requirements.py:1`.
ROOT consumption hashes are0a6624caeb7614ce914ce269def398834b19e44f2bfccf8318014df59aaaa9c1,
da16bfac6fca978e48e10c783819b1b040b1f724d380b5c533565a5c628feb96 and
453a3942c731f2fb5bce2ba61c110f4c47265a6d0f3db5344f035af4a0396f46.
The independent candidate9 Mako ordering failure is retained and corrected in its
own slice; it is not waived by domain success. Full final-material NoSec and
configured scanner reruns remain pending after these comment edits.

Ten additional findings retain their existing annotation terms. AM05 nine, N7,
TrivyD and original39 remain separate. Historical September/October material
below remains unchanged and applies only to its original bytes.

| Original site | Rule | Current source anchor / result | Individual controls and no-safe-equivalent rationale |
| --- | --- | --- | --- |
| `app/security/goplus_agentguard_bridge.py:16` | B404 | `app/security/goplus_agentguard_bridge.py:16`; Individually qualified conservative warning (NOT-A-BUG) | Import-only conservative warning; necessary native subprocess ownership. Feature/test opt-in gates; resolved Node, fixed repo scanner; user text/filename are JSON stdin, not argv; cwd repo; timeout5; nonzero/empty/malformed output degrades to None. PATH, script and inherited env remain trusted. Import itself executes no child; its call sites retain separate individual dispositions. Keep required native CLI semantics and visible subprocess; API alias/wrapper relocation would only conceal warning. Original ref: PR-main-nightly-nosec-ttl. |
| `app/security/goplus_agentguard_bridge.py:85` | B603 | `app/security/goplus_agentguard_bridge.py:85`; Individually qualified conservative warning (NOT-A-BUG) | Feature/test opt-in gates; resolved Node, fixed repo scanner; user text/filename are JSON stdin, not argv; cwd repo; timeout5; nonzero/empty/malformed output degrades to None. PATH, script and inherited env remain trusted. Keep required native CLI semantics and visible subprocess; API alias/wrapper relocation would only conceal warning. Original ref: PR-main-nightly-nosec-ttl. |
| `scripts/check_domain_tls.py:14` | B404 | `scripts/check_domain_tls.py:14`; Individually qualified conservative warning (NOT-A-BUG) | Import-only conservative warning; necessary native subprocess ownership. Resolved dig/curl callers; fixed diagnostic flags; per-call HTTP_TIMEOUT_SEC; curl HEAD without redirect option; native DNS fallback. Hostname data and host CLI/env remain trust inputs. Import itself executes no child; its call sites retain separate individual dispositions. Keep required native CLI semantics and visible subprocess; API alias/wrapper relocation would only conceal warning. Original ref: PR-main-nightly-nosec-ttl. |
| `scripts/check_domain_tls.py:91` | B603 | `scripts/check_domain_tls.py:97`; Corrected domain option/name defect; remaining B603 is individually qualified conservative warning | ASCII LDH labels1..63/total253, both apex and www validated before effects; dig -q/-t; resolved binaries/no shell/15s; native118 cases and mypy0, scannerexactB404+B603. No general DNS/address/TLS safety claim. Keep required native CLI semantics and visible subprocess; API alias/wrapper relocation would only conceal warning. Original ref: PR-main-nightly-nosec-ttl. |
| `scripts/ci/check_docker_provenance_attestation.py:19` | B404 | `scripts/ci/check_docker_provenance_attestation.py:19`; Individually qualified conservative warning (NOT-A-BUG) | Import-only conservative warning; necessary native subprocess ownership. Resolved gh; check=True; configured bounded timeout; attestation verify exact artifact/repository/signer/source-ref, bundle-from-oci and deny-self-hosted-runners. Replacing gh with ordinary HTTP would discard native verification semantics. Import itself executes no child; its call sites retain separate individual dispositions. Keep required native CLI semantics and visible subprocess; API alias/wrapper relocation would only conceal warning. Original ref: PR-docker-signed-provenance. |
| `scripts/ci/check_docker_provenance_attestation.py:106` | B603 | `scripts/ci/check_docker_provenance_attestation.py:106`; Individually qualified conservative warning (NOT-A-BUG) | Resolved gh; check=True; configured bounded timeout; attestation verify exact artifact/repository/signer/source-ref, bundle-from-oci and deny-self-hosted-runners. Replacing gh with ordinary HTTP would discard native verification semantics. Keep required native CLI semantics and visible subprocess; API alias/wrapper relocation would only conceal warning. Original ref: PR-docker-signed-provenance. |
| `scripts/ci/check_docker_runtime_dependency_surface.py:22` | B404 | `scripts/ci/check_docker_runtime_dependency_surface.py:22`; Individually qualified conservative warning (NOT-A-BUG) | Import-only conservative warning; necessary native subprocess ownership. Resolved Docker; check=True; DOCKER_TIMEOUT_SECONDS; UTF-8 strict path and controlled run/inspect callers. Docker daemon and qualified image/native runtime remain trusted; no shell=True. Import itself executes no child; its call sites retain separate individual dispositions. Keep required native CLI semantics and visible subprocess; API alias/wrapper relocation would only conceal warning. Original ref: PR-docker-runtime-slimming. |
| `scripts/ci/check_docker_runtime_dependency_surface.py:151` | B603 | `scripts/ci/check_docker_runtime_dependency_surface.py:151`; Individually qualified conservative warning (NOT-A-BUG) | Resolved Docker; check=True; DOCKER_TIMEOUT_SECONDS; UTF-8 strict path and controlled run/inspect callers. Docker daemon and qualified image/native runtime remain trusted; no shell=True. Keep required native CLI semantics and visible subprocess; API alias/wrapper relocation would only conceal warning. Original ref: PR-docker-runtime-slimming. |
| `scripts/ci/check_pr_merge_readiness.py:17` | B404 | `scripts/ci/check_pr_merge_readiness.py:17`; Individually qualified conservative warning (NOT-A-BUG) | Import-only conservative warning; necessary native subprocess ownership. Resolved Git; fixed status/rev-parse queries; timeout30; owning checkout and isolated Git config/replacement environment; strict return/output interpretation. Import itself executes no child; its call sites retain separate individual dispositions. Keep required native CLI semantics and visible subprocess; API alias/wrapper relocation would only conceal warning. Original ref: PR-governance-material-seal. |
| `scripts/ci/check_pr_merge_readiness.py:384` | B603 | `scripts/ci/check_pr_merge_readiness.py:384`; Individually qualified conservative warning (NOT-A-BUG) | Resolved Git; fixed status/rev-parse queries; timeout30; owning checkout and isolated Git config/replacement environment; strict return/output interpretation. Keep required native CLI semantics and visible subprocess; API alias/wrapper relocation would only conceal warning. Original ref: PR-strict-closeout-precommit-guard. |
| `scripts/ci/check_pr_merge_readiness.py:864` | B603 | `scripts/ci/check_pr_merge_readiness.py:864`; Individually qualified conservative warning (NOT-A-BUG) | Resolved Git; fixed status/rev-parse queries; timeout30; owning checkout and isolated Git config/replacement environment; strict return/output interpretation. Keep required native CLI semantics and visible subprocess; API alias/wrapper relocation would only conceal warning. Original ref: PR-governance-material-seal. |
| `scripts/ci/check_pr_size_governance.py:12` | B404 | `scripts/ci/check_pr_size_governance.py:12`; Individually qualified conservative warning (NOT-A-BUG) | Import-only conservative warning; necessary native subprocess ownership. Resolved Git; actual workflow supplies GitHub base/head SHAs and fixed diff queries; no shell; check=True; all three calls now timeout30 with terminal sanitized errors. Local CLI/operator, checkout, executable/PATH and inherited Git configuration are trusted inputs, not arbitrary remote input admission. Import itself executes no child; its call sites retain separate individual dispositions. Keep required native CLI semantics and visible subprocess; API alias/wrapper relocation would only conceal warning. Original ref: PR3-risk-topology. |
| `scripts/ci/check_pr_size_governance.py:581` | B603 | `scripts/ci/check_pr_size_governance.py:583`; Individually qualified conservative warning (NOT-A-BUG) | Resolved Git; actual workflow supplies GitHub base/head SHAs and fixed diff queries; no shell; check=True; all three calls now timeout30 with terminal sanitized errors. Local CLI/operator, checkout, executable/PATH and inherited Git configuration are trusted inputs, not arbitrary remote input admission. Keep required native CLI semantics and visible subprocess; API alias/wrapper relocation would only conceal warning. Original ref: PR3-risk-topology. |
| `scripts/ci/check_pr_size_governance.py:600` | B603 | `scripts/ci/check_pr_size_governance.py:608`; Individually qualified conservative warning (NOT-A-BUG) | Resolved Git; actual workflow supplies GitHub base/head SHAs and fixed diff queries; no shell; check=True; all three calls now timeout30 with terminal sanitized errors. Local CLI/operator, checkout, executable/PATH and inherited Git configuration are trusted inputs, not arbitrary remote input admission. Keep required native CLI semantics and visible subprocess; API alias/wrapper relocation would only conceal warning. Original ref: PR3-risk-topology. |
| `scripts/ci/check_release_control_plane.py:33` | B105 | `scripts/ci/check_release_control_plane.py:33`; Individually qualified conservative warning (NOT-A-BUG) | REASON_ORDER public reason key rag_gate_result_not_pass maps to integer80 and is used in deterministic public failure ordering/emission. No authentication, secret comparison, secret read or credential storage. Renaming it would alter public reason semantics without fixing a vulnerability. Public reason is not a credential; retain stable reason vocabulary. Original ref: PR-main-nightly-nosec-ttl. |
| `scripts/ci/ci_risk_profile.py:15` | B404 | `scripts/ci/ci_risk_profile.py:15`; Individually qualified conservative warning (NOT-A-BUG) | Import-only conservative warning; necessary native subprocess ownership. Resolved Git; fixed --no-renames --name-only -z range, owning checkout, check=True, GIT_DIFF_TIMEOUT_SECONDS and TimeoutExpired handling; native output supplies both changed endpoints. Import itself executes no child; its call sites retain separate individual dispositions. Keep required native CLI semantics and visible subprocess; API alias/wrapper relocation would only conceal warning. Original ref: PR3-risk-topology. |
| `scripts/ci/ci_risk_profile.py:519` | B603 | `scripts/ci/ci_risk_profile.py:519`; Individually qualified conservative warning (NOT-A-BUG) | Resolved Git; fixed --no-renames --name-only -z range, owning checkout, check=True, GIT_DIFF_TIMEOUT_SECONDS and TimeoutExpired handling; native output supplies both changed endpoints. Keep required native CLI semantics and visible subprocess; API alias/wrapper relocation would only conceal warning. Original ref: PR3-risk-topology. |
| `scripts/ci/docker_image_telemetry.py:19` | B404 | `scripts/ci/docker_image_telemetry.py:19`; Individually qualified conservative warning (NOT-A-BUG) | Import-only conservative warning; necessary native subprocess ownership. Resolved Docker; only image inspect/history caller families; check=True and DOCKER_TIMEOUT_SECONDS; read-only telemetry parsing. Docker CLI/env/daemon remain trusted. Import itself executes no child; its call sites retain separate individual dispositions. Keep required native CLI semantics and visible subprocess; API alias/wrapper relocation would only conceal warning. Original ref: PR-docker-telemetry-baseline. |
| `scripts/ci/docker_image_telemetry.py:86` | B603 | `scripts/ci/docker_image_telemetry.py:86`; Individually qualified conservative warning (NOT-A-BUG) | Resolved Docker; only image inspect/history caller families; check=True and DOCKER_TIMEOUT_SECONDS; read-only telemetry parsing. Docker CLI/env/daemon remain trusted. Keep required native CLI semantics and visible subprocess; API alias/wrapper relocation would only conceal warning. Original ref: PR-docker-telemetry-baseline. |
| `scripts/ci/fetch_docker_image_baseline.py:16` | B404 | `scripts/ci/fetch_docker_image_baseline.py:16`; Individually qualified conservative warning (NOT-A-BUG) | Import-only conservative warning; necessary native subprocess ownership. Resolved gh; fixed API/auth calls, supplied env and GH_TIMEOUT_SECONDS; artifact call is read-only API zip, bounded subprocess plus temporary archive processing. Native auth/download behavior must be retained. Import itself executes no child; its call sites retain separate individual dispositions. Keep required native CLI semantics and visible subprocess; API alias/wrapper relocation would only conceal warning. Original ref: PR-docker-image-budget-telemetry. |
| `scripts/ci/fetch_docker_image_baseline.py:54` | B603 | `scripts/ci/fetch_docker_image_baseline.py:54`; Individually qualified conservative warning (NOT-A-BUG) | Resolved gh; fixed API/auth calls, supplied env and GH_TIMEOUT_SECONDS; artifact call is read-only API zip, bounded subprocess plus temporary archive processing. Native auth/download behavior must be retained. Keep required native CLI semantics and visible subprocess; API alias/wrapper relocation would only conceal warning. Original ref: PR-docker-image-budget-telemetry. |
| `scripts/ci/fetch_docker_image_baseline.py:183` | B603 | `scripts/ci/fetch_docker_image_baseline.py:183`; Individually qualified conservative warning (NOT-A-BUG) | Resolved gh; fixed API/auth calls, supplied env and GH_TIMEOUT_SECONDS; artifact call is read-only API zip, bounded subprocess plus temporary archive processing. Native auth/download behavior must be retained. Keep required native CLI semantics and visible subprocess; API alias/wrapper relocation would only conceal warning. Original ref: PR-docker-image-budget-telemetry. |
| `scripts/ci/install_locked_python_requirements.py:2725` | B323 | Removed; verified TLS and terminal error propagation; no replacement suppression | Actual safe code fix applied. Native TLS matrix and proxy evidence above; no blind warning renewal. |
| `scripts/metatron_lab/compose_guard.py:6` | B404 | `scripts/metatron_lab/compose_guard.py:6`; Individually qualified conservative warning (NOT-A-BUG) | Import-only conservative warning; necessary native subprocess ownership. validate_all_profiles resolves Docker, chooses repo compose file and exactly two LAB_PROFILES; argv list/no shell; config -q only,30s; timeout124/nonzero stop iteration. Direct helper is an internal seam, not remote arbitrary-command API; Docker/checkout/environment trusted. Import itself executes no child; its call sites retain separate individual dispositions. Keep required native CLI semantics and visible subprocess; API alias/wrapper relocation would only conceal warning. Original ref: PR-main-nightly-nosec-ttl. |
| `scripts/metatron_lab/compose_guard.py:46` | B603 | `scripts/metatron_lab/compose_guard.py:48`; Individually qualified conservative warning (NOT-A-BUG) | validate_all_profiles resolves Docker, chooses repo compose file and exactly two LAB_PROFILES; argv list/no shell; config -q only,30s; timeout124/nonzero stop iteration. Direct helper is an internal seam, not remote arbitrary-command API; Docker/checkout/environment trusted. Keep required native CLI semantics and visible subprocess; API alias/wrapper relocation would only conceal warning. Original ref: PR-main-nightly-nosec-ttl. |
| `scripts/orchestration/check_codex_ollama_operator.py:17` | B404 | `scripts/orchestration/check_codex_ollama_operator.py:17`; Individually qualified conservative warning (NOT-A-BUG) | Import-only conservative warning; necessary native subprocess ownership. Resolved CLI supplied by callers; fixed version requests; shell=False, timeout10; timeout reported124. This pass did not execute local/provider CLI. Import itself executes no child; its call sites retain separate individual dispositions. Keep required native CLI semantics and visible subprocess; API alias/wrapper relocation would only conceal warning. Original ref: PR-main-nightly-nosec-ttl. |
| `scripts/orchestration/check_codex_ollama_operator.py:71` | B603 | `scripts/orchestration/check_codex_ollama_operator.py:71`; Individually qualified conservative warning (NOT-A-BUG) | Resolved CLI supplied by callers; fixed version requests; shell=False, timeout10; timeout reported124. This pass did not execute local/provider CLI. Keep required native CLI semantics and visible subprocess; API alias/wrapper relocation would only conceal warning. Original ref: PR-main-nightly-nosec-ttl. |
| `scripts/orchestration/check_merge_ready.py:10` | B404 | `scripts/orchestration/check_merge_ready.py:10`; Individually qualified conservative warning (NOT-A-BUG) | Import-only conservative warning; necessary native subprocess ownership. sys.executable+fixed gate scripts with per-gate timeout; resolved gh auth/pr view; selected repo/PR args and cwd; native failure propagation; strict pre-closeout requires both opaque tokens before auth. No replacement HTTP implementation proposed. Import itself executes no child; its call sites retain separate individual dispositions. Keep required native CLI semantics and visible subprocess; API alias/wrapper relocation would only conceal warning. Original ref: PR-main-nightly-nosec-ttl. |
| `scripts/orchestration/check_merge_ready.py:118` | B603 | `scripts/orchestration/check_merge_ready.py:118`; Individually qualified conservative warning (NOT-A-BUG) | sys.executable+fixed gate scripts with per-gate timeout; resolved gh auth/pr view; selected repo/PR args and cwd; native failure propagation; strict pre-closeout requires both opaque tokens before auth. No replacement HTTP implementation proposed. Keep required native CLI semantics and visible subprocess; API alias/wrapper relocation would only conceal warning. Original ref: PR-main-nightly-nosec-ttl. |
| `scripts/orchestration/check_merge_ready.py:158` | B603 | `scripts/orchestration/check_merge_ready.py:158`; Individually qualified conservative warning (NOT-A-BUG) | sys.executable+fixed gate scripts with per-gate timeout; resolved gh auth/pr view; selected repo/PR args and cwd; native failure propagation; strict pre-closeout requires both opaque tokens before auth. No replacement HTTP implementation proposed. Keep required native CLI semantics and visible subprocess; API alias/wrapper relocation would only conceal warning. Original ref: PR-main-nightly-nosec-ttl. |
| `scripts/orchestration/check_merge_ready.py:187` | B603 | `scripts/orchestration/check_merge_ready.py:187`; Individually qualified conservative warning (NOT-A-BUG) | sys.executable+fixed gate scripts with per-gate timeout; resolved gh auth/pr view; selected repo/PR args and cwd; native failure propagation; strict pre-closeout requires both opaque tokens before auth. No replacement HTTP implementation proposed. Keep required native CLI semantics and visible subprocess; API alias/wrapper relocation would only conceal warning. Original ref: PR-main-nightly-nosec-ttl. |
| `scripts/orchestration/check_merge_ready.py:241` | B603 | `scripts/orchestration/check_merge_ready.py:241`; Individually qualified conservative warning (NOT-A-BUG) | sys.executable+fixed gate scripts with per-gate timeout; resolved gh auth/pr view; selected repo/PR args and cwd; native failure propagation; strict pre-closeout requires both opaque tokens before auth. No replacement HTTP implementation proposed. Keep required native CLI semantics and visible subprocess; API alias/wrapper relocation would only conceal warning. Original ref: PR-main-nightly-nosec-ttl. |
| `scripts/orchestration/check_preflight.py:13` | B404 | `scripts/orchestration/check_preflight.py:13`; Individually qualified conservative warning (NOT-A-BUG) | Import-only conservative warning; necessary native subprocess ownership. Literal Git or sys.executable with fixed repo consistency script; no shell; Git30s and consistency120s; timeout returns124 and cannot pass. Only fixed status/ls-files/consistency callers are reachable in this CLI. Import itself executes no child; its call sites retain separate individual dispositions. Keep required native CLI semantics and visible subprocess; API alias/wrapper relocation would only conceal warning. Original ref: PR-main-nightly-nosec-ttl. |
| `scripts/orchestration/check_preflight.py:78` | B603 | `scripts/orchestration/check_preflight.py:84`; Individually qualified conservative warning (NOT-A-BUG) | Literal Git or sys.executable with fixed repo consistency script; no shell; Git30s and consistency120s; timeout returns124 and cannot pass. Only fixed status/ls-files/consistency callers are reachable in this CLI. Keep required native CLI semantics and visible subprocess; API alias/wrapper relocation would only conceal warning. Original ref: PR-main-nightly-nosec-ttl. |
| `scripts/orchestration/creative_pilot_workspace_contract.py:16` | B404 | `scripts/orchestration/creative_pilot_workspace_contract.py:16`; Individually qualified conservative warning (NOT-A-BUG) | Import-only conservative warning; necessary native subprocess ownership. Resolved Git; cat-file/rev-parse/ls-tree/show caller families; repo cwd; timeout15, checked return and bytes/text distinction. Native Git object grammar retained; env is inherited at this seam. Import itself executes no child; its call sites retain separate individual dispositions. Keep required native CLI semantics and visible subprocess; API alias/wrapper relocation would only conceal warning. Original ref: ledger-p1-agent-experimentation-lane. |
| `scripts/orchestration/creative_pilot_workspace_contract.py:927` | B603 | `scripts/orchestration/creative_pilot_workspace_contract.py:927`; Individually qualified conservative warning (NOT-A-BUG) | Resolved Git; cat-file/rev-parse/ls-tree/show caller families; repo cwd; timeout15, checked return and bytes/text distinction. Native Git object grammar retained; env is inherited at this seam. Keep required native CLI semantics and visible subprocess; API alias/wrapper relocation would only conceal warning. Original ref: ledger-p1-agent-experimentation-lane. |
| `scripts/orchestration/pr_review_closeout.py:16` | B404 | `scripts/orchestration/pr_review_closeout.py:16`; Individually qualified conservative warning (NOT-A-BUG) | Import-only conservative warning; necessary native subprocess ownership. Resolved Git; isolated Git environment, active-graft rejection and timeout30 at both calls; exact native object/status/hash semantics and checked returns. Import itself executes no child; its call sites retain separate individual dispositions. Keep required native CLI semantics and visible subprocess; API alias/wrapper relocation would only conceal warning. Original ref: PR-governance-material-seal. |
| `scripts/orchestration/pr_review_closeout.py:209` | B603 | `scripts/orchestration/pr_review_closeout.py:209`; Individually qualified conservative warning (NOT-A-BUG) | Resolved Git; isolated Git environment, active-graft rejection and timeout30 at both calls; exact native object/status/hash semantics and checked returns. Keep required native CLI semantics and visible subprocess; API alias/wrapper relocation would only conceal warning. Original ref: PR-governance-material-seal. |
| `scripts/orchestration/pr_review_closeout.py:235` | B603 | `scripts/orchestration/pr_review_closeout.py:235`; Individually qualified conservative warning (NOT-A-BUG) | Resolved Git; isolated Git environment, active-graft rejection and timeout30 at both calls; exact native object/status/hash semantics and checked returns. Keep required native CLI semantics and visible subprocess; API alias/wrapper relocation would only conceal warning. Original ref: PR-governance-material-seal. |
| `scripts/orchestration/pr_review_evidence.py:17` | B404 | `scripts/orchestration/pr_review_evidence.py:17`; Individually qualified conservative warning (NOT-A-BUG) | Import-only conservative warning; necessary native subprocess ownership. Resolved Git; sanitized environment, timeout30/default override, active-graft and selected shallow-ancestry rejection. merge-base exits0/1 are distinct from tool errors. Exact real Git topology cannot be replaced by string tests. Import itself executes no child; its call sites retain separate individual dispositions. Keep required native CLI semantics and visible subprocess; API alias/wrapper relocation would only conceal warning. Original ref: PR-governance-seal. |
| `scripts/orchestration/pr_review_evidence.py:1958` | B603 | `scripts/orchestration/pr_review_evidence.py:1958`; Individually qualified conservative warning (NOT-A-BUG) | Resolved Git; sanitized environment, timeout30/default override, active-graft and selected shallow-ancestry rejection. merge-base exits0/1 are distinct from tool errors. Exact real Git topology cannot be replaced by string tests. Keep required native CLI semantics and visible subprocess; API alias/wrapper relocation would only conceal warning. Original ref: PR-governance-seal. |
| `scripts/orchestration/pr_review_evidence.py:1982` | B603 | `scripts/orchestration/pr_review_evidence.py:1982`; Individually qualified conservative warning (NOT-A-BUG) | Resolved Git; sanitized environment, timeout30/default override, active-graft and selected shallow-ancestry rejection. merge-base exits0/1 are distinct from tool errors. Exact real Git topology cannot be replaced by string tests. Keep required native CLI semantics and visible subprocess; API alias/wrapper relocation would only conceal warning. Original ref: PR-governance-seal. |
| `scripts/orchestration/pr_review_evidence.py:2002` | B603 | `scripts/orchestration/pr_review_evidence.py:2002`; Individually qualified conservative warning (NOT-A-BUG) | Resolved Git; sanitized environment, timeout30/default override, active-graft and selected shallow-ancestry rejection. merge-base exits0/1 are distinct from tool errors. Exact real Git topology cannot be replaced by string tests. Keep required native CLI semantics and visible subprocess; API alias/wrapper relocation would only conceal warning. Original ref: PR-governance-seal. |
| `scripts/orchestration/pr_review_evidence.py:2036` | B603 | `scripts/orchestration/pr_review_evidence.py:2036`; Individually qualified conservative warning (NOT-A-BUG) | Resolved Git; sanitized environment, timeout30/default override, active-graft and selected shallow-ancestry rejection. merge-base exits0/1 are distinct from tool errors. Exact real Git topology cannot be replaced by string tests. Keep required native CLI semantics and visible subprocess; API alias/wrapper relocation would only conceal warning. Original ref: PR-governance-seal. |
| `scripts/orchestration/pr_review_evidence.py:2103` | B603 | `scripts/orchestration/pr_review_evidence.py:2103`; Individually qualified conservative warning (NOT-A-BUG) | Resolved Git; sanitized environment, timeout30/default override, active-graft and selected shallow-ancestry rejection. merge-base exits0/1 are distinct from tool errors. Exact real Git topology cannot be replaced by string tests. Keep required native CLI semantics and visible subprocess; API alias/wrapper relocation would only conceal warning. Original ref: PR-governance-seal. |


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

## November 1 reassessment of the two iOS simulator selector sites

CI/iOS explicitly adopted the event-driven schedule for the two existing PR-2460
annotations. Security/SRE concurred separately on each warning. The October 31
removal deadline was missed. CI/iOS withdrew its proposed November 9 deadline.
The adopted schedule covers these two reviewed operations.

| Site | Qualified behavior | Reassessment and removal |
| --- | --- | --- |
| B404 at `scripts/ci/select_ios_simulator.py:11` | The standard-library import supplies the native inventory process and its typed failure handling. Moving the import would leave the execution boundary intact. | Reassess immediately if the subprocess consumers or inventory owner change. Remove the annotation when the import is retired or qualified scanning ceases to report it. |
| B603 at `scripts/ci/select_ios_simulator.py:137` | The managed runner resolves an absolute xcrun executable. Two fixed, shell-free argv lists read available devices and device types. Each has a 30-second timeout. Failure precedes destination publication. This depends on the runner’s PATH and developer-directory ownership. | Reassess immediately on changes to the runner/toolchain, PATH, DEVELOPER_DIR, arguments, shell, timeout, error handling or destination-write order. Remove upon retirement, qualification of a safer equivalent, or disappearance of the finding in a qualified scan. |

The material 27 Linux selector module passed all 35 cases with zero skips. Five
mocked subprocess cases checked both argv lists, bounded failures and output
preservation. The preceding whole-file ordinary scan reported zero selector
findings. Its unsuppressed counterpart reported exactly B404 and B603, both LOW
severity with HIGH confidence. These observations precede the comment changes.

At the first eligible hosted execution on pinned Xcode 27.0, CI/iOS records the
material commit, native run/job IDs, verified runner, toolchain, iOS runtime and
selector outcome. Review an adverse signal immediately. Record the two iPhone
and two iPad outcomes across the unit and UI-smoke jobs as they become available.
The four current-head hosted outcomes remain pending.

At the **January 11, 2027** evidence checkpoint, CI/iOS records any missing jobs
or runtime evidence and arranges the next qualified verification. Security/SRE
reassesses each row. The hard removal date is **January 31, 2027 inclusive** on
the evaluating host’s local calendar. An unresolved row expires on February 1.
Rollback restores the prior comment and exposes the original expiry condition.
Repeat the owning selector tests, both Bandit modes and the actual-calendar guard
against final material.

## November 1 reassessment of the six PR-985 disposition-checker sites

CI/orchestration and Security/SRE individually adopted maintenance of the six
warnings below. Their original PR-985 removal date of October 31, 2026 was
missed. Record the first applicable observation for each row with the material,
operation and sanitized outcome. Reopen the affected row immediately if its
conditions change or a control fails.

| Site in `scripts/orchestration/check_review_threads_disposition.py` | Qualified operation | First observation and immediate review triggers |
| --- | --- | --- |
| B404 at line 26 | The standard-library import supplies Git and gh execution and typed failures. | At the next source inventory verify both tool families. Review any new or retired executable family or change of process owner. |
| B603 at line 133 | The closed gh dispatcher validates dynamic REST operands and bounds each invocation to 60 seconds. Successful auth-token output remains private. | At the next applicable dispatch inspect the operation category and sanitized outcome. Review changes to command or operand grammar, executable, host, credentials, timeout or output handling. |
| B603 at line 207 | The local native Git reader binds the CLI checkout, validates unambiguous commit identity, and reads time, subject and NUL-delimited paths with a 15-second per-process limit. | At the next local strict read verify the checkout and individual predicates. Review executable, config, ref/object grammar, graft/shallow handling, output parsing or time-source changes. |
| B603 at line 932 | The fixed gh GraphQL operation sends its request on stdin and rejects transport, decoding and response-envelope failures. | At the next applicable GraphQL operation inspect its sanitized outcome. Review transport, authentication, request channel, response shape and diagnostics changes. |
| B603 at line 1190 | Advisory gh auth status returns availability under a five-second bound. | Observe the next advisory routing opportunity and its success/unavailable controls. Review changes to callers, executable, timeout or advisory SKIP semantics. A strict-only run does not exercise this site. |
| B603 at line 1246 | Strict preflight requires the token before the ten-second gh auth-status check and blocks GraphQL on failure. | At the next applicable strict run inspect token-before-auth-before-GraphQL ordering and the rejection path. Review credential precedence, executable, timeout, ordering or diagnostic changes. |

Material 29 ran the complete strict module (121/121) and readiness module
(229/229), with zero failures, errors or skips. The ordinary and unsuppressed
Bandit reports covered all 1,354 lines of the same checker and recorded zero
scanner errors. Ordinary contributed zero checker findings. Unsuppressed
reported the six LOW-severity, HIGH-confidence sites above. Those observations
precede this comment-only change. The gh calls rely on the intended installed
CLI, host and authentication context. Local Git identity alone cannot establish
the independent server push-time and live review predicates.

By **January 18, 2027**, record any unobserved operation or missing negative
control and arrange its next qualified observation. The hard remove-by date for
each row is **February 1, 2027 inclusive**, on the evaluating host's local
calendar. February 2 rejects. A missed observation cannot extend the term.
Remove each annotation when the operation retires, a qualified safer equivalent
is available or the scanner ceases to report it. Rollback restores the prior
comments and the original expiry condition. Recheck both full-file Bandit modes,
the actual-calendar guard and applicable owning checks on final material. The
independent HTTP and pagination findings retain their separate remediation.

## November 1 maintenance of ten existing CI and Python reader annotations

CI/orchestration adopted the three shard and three Phase2 decisions. The Python
supply-chain implementation owner and CI adopted the two startup and two carrier
decisions. Security/SRE concurred individually on all ten. Their original
October 31, 2026 removal deadlines were missed. Each row retains its introduction
reference. Record the material, operation and outcome at its first applicable
event and reopen the affected row immediately when its stated conditions change.

| Site and original ref | First event and reassessment triggers | 2027 evidence checkpoint / inclusive hard removal |
| --- | --- | --- |
| `scripts/ci/run_main_test_shards.py:15`, B404, PR-1748 | At the next CI runner inventory, review the import's launch, observation, signalling and coverage consumers. Reopen for a new process family or wait owner. | January 4 / January 25 |
| Shard runner line 525, B603, PR-1748 | Record the next test-main material and ordinary exit. At the first cancellation, verify original-group custody, the TERM-resistant child and the unaffected peer. Reopen on interpreter, argv, job environment, signal, platform, census or timeout changes. | January 4 / January 25 |
| Shard runner line 799, B603, PR-2020 | Observe the next combine, XML and applicable HTML/report sequence. Reopen on interpreter, coverage plugin/configuration, inherited environment, command or timeout changes. The bound applies to each direct process. | January 4 / January 25 |
| `scripts/ci/check_python_startup_hooks.py:11`, B404, PR-litellm-private-proxy | At the next guarded installation, review the selected-interpreter inspection and exception consumers. Reopen for a different process family, interpreter or owner. | January 11 / February 1 |
| Startup guard line 218, B603, PR-litellm-private-proxy | At the next stage/target inspection verify the selected venv invocation, prefixes, real home, user-site paths, closed environment, diagnostics and 30-second bound. Reopen on changes to those inputs or the target platform. The outer installer has separate findings. | January 11 / February 1 |
| `scripts/ci/dependabot_requirement_carriers.py:24`, B404, PR-2181 | At the next dependency or policy discovery, confirm the import still serves the two index queries. Reopen on an additional native operation, new process owner or broader filesystem discovery. | January 11 / February 1 |
| Carrier reader line 473, B603, PR-2181 | At the next requirements/policy change, exercise populated and empty indexes and hostile Git configuration. Reopen on executable, checkout, environment, NUL parsing or the ten-second per-query bound. The child retains non-Git environment variables. | January 11 / February 1 |
| `scripts/ci/check_pr_body_phase2_gates.py:8`, B404, experiment-runner-oracle-attribution-semantics | At the next Phase2 source inventory, verify log and trailer consumers. Reopen on any added Git operation or process-owner change. | January 18 / February 8 |
| Phase2 checker line 637, B603, same attribution ref | Observe the next branch log read and its distinct optional fallback where applicable. Reopen on executable, checkout/config isolation, selected range, diagnostics, or 15-second per-attempt bound. An empty successful log stops the lookup. | January 18 / February 8 |
| Phase2 checker line 671, B603, same attribution ref | At the next attributed commit, verify native trailer parsing, exact match and negative control. Reopen on Git/config, grammar, stdin/output handling, advisory semantics or five-second per-message bound. | January 18 / February 8 |

Material 30's owning module results were 87/87 shard, 40/40 startup, 212/212
carrier and 119/119 Phase2 tests. Each row appeared once in the unsuppressed
production scan and had no ordinary match. The ordinary scan separately reported
the visible B603 at shard runner line 565. The ten decisions grant no term for
that call. The material 30 calendar snapshot recorded 47 expired rows. Final
scanner counts and calendar results require observation on the changed bytes.

The Linux shard evidence covers the controlled resistant child and original-group
cleanup. Darwin evidence covers native nonreaping readiness, BSD group census,
direct reap and socket EOF. Darwin fallback point-query behavior remains
unqualified. Each checkpoint leaves 21 days for follow-up. If a first event has
not occurred, record the missing evidence and arrange qualification. Each hard
removal is inclusive on the actual evaluating host's calendar. Remove the row
upon retirement, qualification of a safer equivalent, or verified disappearance
of the raw warning. Rollback restores the prior comments and corresponding expiry
failure. Recheck ordinary and unsuppressed scans, the actual-calendar guard and
the affected owning behaviors against final material.

## November 1 reassessment of 15 transferred inline Bandit sites

The original October 31, 2026 removal obligations were missed. On source tree 00e13260f97d7fd9240fc94bcd90dbfbe1dd1287 the four scoped native checks passed: corpus/promotion 228/228, creative builder 22/22, local verifier 40/40 and Playwright 49/49. No real browser installation or creative model/promotion was performed for these tests. The original material31 date guard failed with 28 rows, including the 15 below. The remaining 13 are outside this decision.

| Individual site and historical ref | Evidence, limits and first event triggering re-review | Review checkpoint / inclusive hard removal |
|---|---|---|
| Local verify B404 :21 PR-1243 | Required fixed stock guard and native failure handling; review at next verify-env use or change of subprocess family. | Dec 1, 2026 / Jan 1, 2027 |
| Local verify B603 :101 PR-1243 | Qualified repo interpreter and guard, controlled real site inputs, bounded deadline and complete stock response; recheck failure/nonempty/mixed report and identity on next guard change. | Dec 1, 2026 / Jan 1, 2027 |
| Corpus B404 :14 PR-2446 | Required native Git object reads; review new reader/client or replacement of its owner. | Jan 1 / Feb 1, 2027 |
| Corpus B603 :1252 PR-2446 | Fixed read-only Git operations, replacement isolation, 30s and categorical failure; recheck changes in tree/blob/diff or errors. No total stdout bound implied. | Jan 1 / Feb 1, 2027 |
| Corpus fixture B603 :45 PR-2446 | Remove the expired test annotation, expose the ordinary warning; retain test-owned fixed Git operation/30s and replacement negative. | Remove; no new term |
| Creative executor B404 :8 PR-2 | Required stdin execution and typed failure handling; review on executor/tooling contract change. | Dec 1, 2026 / Jan 1, 2027 |
| Creative executor B603 :126 PR-2 | Explicit model executable and bounded process with stdout/stderr counts only; synthetic failure controls. No real model execution or byte cap implied. Review on prompt/argv/env/error projection changes. | Dec 1, 2026 / Jan 1, 2027 |
| Creative workspace B404 :13 PR-2 | Required Git for private generation checkout; review change of command set or workspace ownership. | Dec 1, 2026 / Jan 1, 2027 |
| Creative workspace B603 :392 PR-2 | Generation reserves and verifies its own directory, retains uncertain mutation and verifies base; actual size-dependent clone/status not subject to a universal cap. Reassess on tool, mutation, parent/child identity, retry or cleanup change. Separate validation-checkout caller remains a separate boundary. | HOLD; no change |
| Creative promotion B404 :18 PR-3 | Required actual Git/gh and validation families; review next caller/authorization or tool change. | Dec 1, 2026 / Jan 1, 2027 |
| Creative promotion B603 :347 PR-3 | Selected fixed command transports with existing bounded calls, sanitized failures and native rc2/porcelain ambiguity semantics; isolated tests only, no real push/PR. Reassess before changing command/credentials/rollback. | Dec 1, 2026 / Jan 1, 2027 |
| Promotion fixture B603 :961 PR-2455 | Remove expired test annotation so ordinary test scan displays warning. Keep actual temporary-ref suffix case and 30s cap. | Remove; no new term |
| Browser B404 :11 PR-playwright-mcp-node22 | Required read-only Node lookup and explicit Chromium command as separate operations. Review on adding subprocess families. | Jan 1 / Feb 1, 2027 |
| Browser doctor B603 :99 PR-playwright-mcp-node22 | Fixed version query/qualified absolute Node, controlled startup and 10s; unavailable does not install. Recheck optional/required selection and failure routing. | Dec 1, 2026 / Jan 1, 2027 |
| Browser install B603 :450 PR-playwright-mcp-node22 | Qualified Node plus installed lock-matched local CLI, literal install chromium; actual cache/mirror/proxy operands preserved and no npx package acquisition. Mock selection/rejection/return evidence only. No live installation, universal deadline, exclusive shared-cache ownership or verified browser launchability. Reassess on CLI/toolchain/cache/child handling change. | Nov 15 / Dec 1, 2026 |

Source-bound four-profile Bandit recorded zero scan errors and one matching unsuppressed finding for each of the 15 sites, six B404 imports and nine B603 calls. On stage31 the production ordinary/unsuppressed counts were 1/62 and test ordinary/unsuppressed 176/182. The production ordinary finding is a different site, the shard ps invocation. CI/tooling, backend component and Security/SRE decisions support exactly twelve existing production terms and two test retirements. Tooling explicitly adopted the shorter browser install checkpoint and hard term. Workspace :392 retains its expired historical annotation until the checked shared Git error stops disclosing argv and raw stderr/stdout through its callers and the separate validation-checkout cleanup defect is resolved on qualified material. The interrupted validation writer and partial/shared cache states are not accepted residual risks.

Earlier relevant events or changed/failed controls require immediate review. If no event occurred by a named checkpoint, record the missing observation and run the scoped owner control. Hard removal uses the evaluating host’s local date. Retire earlier if a safe equivalent exists, the operation retires or the raw scanner finding disappears on positively scanned source. Rollback restores only the corresponding original comments and expired state. The two removed test annotations should increase ordinary B603 visibility by exactly two while the underlying raw findings remain. Evidence anchors: scripts/ci/check_local_verify_environment.py:101, scripts/ci/check_philosophy_source_corpus_index.py:1252, scripts/orchestration/creative_code_patch_executor.py:126, scripts/orchestration/creative_code_patch_workspace.py:392, scripts/orchestration/creative_code_pr_promotion.py:347 and scripts/playwright_mcp.py:450.

## November 1 single-site B603 disposition for the shard process census

| Site | Operation and evidence | Review and removal |
|---|---|---|
| `scripts/ci/run_main_test_shards.py:565`, B603, PR-2494 | The two callers query the reserved direct-child PID with system `ps -p` or its group with `ps -g`. The command reads fixed PID, PPID, PGID and state fields with closed stdin, an explicit system PATH and C locale, and the remaining phase deadline. The reader requires the owned leader as a witness. | CI/test-main and Security/SRE review the first affected cancellation or runner/toolchain change. Evidence checkpoint **January 4, 2027**. Hard removal **January 25, 2027 inclusive** on the evaluator’s local calendar. |

The operator explicitly authorized this one census annotation on November 1,
2026 after CI/test-main and Security/SRE reviewed this exact call. The direct
reply was “Разрешаю этот один B603” (“I authorize this one B603”). On material 30 the configured pre-commit
hook reported this single LOW-severity, HIGH-confidence B603 and exited 1
(receipt `ea268a14d709863323d3d055909241dad77c7918957b62142f955696907b31e6`).
The ordinary and unsuppressed production reports both contained the finding.

The Linux control observed the previously TERM-resistant child become terminal,
the owned group become inactive and the leader be reaped. The owning module
passed 87/87 cases. On Darwin the native WNOWAIT and BSD group census were
observed. The non-WNOWAIT BSD point-query fallback remains unqualified.
The claim covers the original owned group on a trusted system-tool installation.
It does not establish an output-byte limit or custody of escaped descendants.
The broader Prometheus census reads different fields across the host and does
not replace the required held-leader observation.

At the first review, retain material identity, scanner profile, group/leader
provenance, a positive resistant-child witness and the independent peer result.
If no qualifying event occurs by January 4, record that gap and exercise the
owned fixture. Reopen immediately on changes to callers, selectors, executable
trust, environment, fields, parser, OS, deadline or wait ownership, or on a
failed custody observation or new finding. Remove on retirement, a demonstrated
safer equivalent, or verified disappearance from a qualified unsuppressed scan.
An unresolved annotation expires January 26. Rollback removes this one comment
and its record and restores ordinary visibility. Recheck the configured hook,
both scanner modes, owning controls and actual-calendar guard on final material.

## November 1 maintenance of thirteen remaining process warnings

The October 31, 2026 deadlines below were missed. Component and Security/SRE
reviews compared each warning with the frozen material32 source and its raw
Bandit span. The eight focused groups passed all 138 native cases. The ordinary
production scan found zero warnings and the unsuppressed scan retained 62.
These decisions cover the listed imports and calls. The sandbox Popen warning
still requires the separate executable-resolution correction and native proof.

| Source and original reference | Necessary operation and retained boundary | First review / checkpoint / inclusive removal |
|---|---|---|
| app/security/execution_sandbox.py:14, B404, PR-1010 | Sandbox process launch and typed failure handling | First applicable use or relevant change / 2027-01-04 / 2027-02-01 |
| scripts/ci/install_locked_python_requirements.py:31, B404, PR-litellm-hardening | Selected Python/pip process and error handling | First applicable use or relevant change / 2027-01-04 / 2027-02-01 |
| scripts/ci/install_locked_python_requirements.py:1948, B603, PR-2017 | Isolated selected-target metadata, fixed flags, 30-second bound, unqualified provider rejected | First applicable use or relevant change / 2026-12-01 / 2027-01-01 |
| scripts/ci/install_locked_python_requirements.py:3348, B603, PR-litellm-hardening | Selected CPython prefix discovery without site execution, identity checks and 30-second bound | First applicable use or relevant change / 2026-12-01 / 2027-01-01 |
| scripts/ci/install_locked_python_requirements.py:3519, B603, PR-litellm-hardening | Owned Python/pip argv, private completed-result evidence and fixed public errors; caller may select timeout=None | First applicable use or relevant change / 2026-12-01 / 2027-01-01 |
| scripts/ci/install_locked_python_requirements.py:3662, B603, PR-litellm-hardening | Stock or explicit custom guard with controlled startup/env and 60-second bound; findings fail closed | First applicable use or relevant change / 2026-12-01 / 2027-01-01 |
| scripts/orchestration/creative_code_patch_workspace.py:393, B603, PR-2 | Generation/validation ownership and categorical checked errors; only metadata callers have the recorded short deadline | First applicable use or relevant change / 2026-12-01 / 2027-01-01 |
| scripts/orchestration/experiment_contract.py:15, B404, ledger-p1-experiment-runner-oracle-only-governance-reviewer | Git tracked-context lookup and typed failures | First applicable use or relevant change / 2027-01-04 / 2027-02-01 |
| scripts/orchestration/experiment_contract.py:346, B603, ledger-p1-experiment-runner-oracle-only-governance-reviewer | Fixed read-only tracked-context Git query with 30-second bound | First applicable use or relevant change / 2026-12-01 / 2027-01-01 |
| scripts/orchestration/experiment_runner.py:20, B404, PR-1082 | Git operations used by candidate and Oracle paths | First applicable use or relevant change / 2027-01-04 / 2027-02-01 |
| scripts/orchestration/experiment_runner.py:303, B603, PR-1082 | Owned Git operands and private nonzero evidence; ambiguous mutation is retained, general mutation has no fixed deadline | First applicable use or relevant change / 2026-12-01 / 2027-01-01 |
| scripts/orchestration/experiment_runner_dispatch.py:25, B404, ledger-p1-experiment-runner-macos-strict-backend | Selected backend probe and runtime process support | First applicable use or relevant change / 2027-01-04 / 2027-02-01 |
| scripts/orchestration/experiment_runner_dispatch.py:352, B603, ledger-p1-experiment-runner-macos-strict-backend | Absolute selected executable, per-caller timeout and fixed exception; explicit env/secret inputs are intentional | First applicable use or relevant change / 2026-12-01 / 2027-01-01 |

The original owning component and Security/SRE review the first applicable
operation and any change to executable, argv, environment, metadata grammar,
caller, cleanup, trust or native toolchain before the stated checkpoint.
Missing observations are recorded at that checkpoint. No automatic renewal
follows. Remove an annotation when the operation retires, a safe replacement
is verified or the raw warning disappears on a positively scanned source.
Rollback restores its original comment and expired state.

Captured subprocess output has no general byte-size bound. The optional
Git/pip deadlines and intentional runtime inputs remain caller-specific.
The current external-target rejection and the separately approved shard-ps
annotation retain their own decisions. Final local, hosted, image, coverage
and review gates require their actual results.


## November 1 sandbox launch warning after executable and CLI repair

The sandbox/Experiment Runner component and Security/SRE adopted the remaining
B603 at app/security/execution_sandbox.py:466 after the complete material34
module passed all 76 cases. The material33 result of 73 passed and 3 failed
remains recorded. The corrected direct CLI supplies its own repository import
path, and its original three tests pass with PYTHONPATH removed.

The selected executable is anchored before the child cwd change. Its final
venv invocation symlink is preserved, and the resolved target must be a regular
executable. Controlled native tests exercise competing parent/child PATH
locations, the actual venv prefix, rejected targets, terminal process handling
and completed output readers. Both current file scans contain complete
positive file metrics. Ordinary Bandit exits 0 with no finding, while the
unsuppressed scan exits 1 with the B404 import and the B603 launch at lines
14 and 466. The retained scan aggregator exits 2 because it incorrectly expects
four reports for this deliberately two-profile operation. ROOT independently
checked both actual reports and preserved that accounting failure.

Review the first actual enabled sandbox call and any change to executable
selection, venv, PATH/cwd, process family, platform, configured limits, inputs,
caller or cleanup. The calendar evidence checkpoint is **December 1, 2026**.
The inclusive hard removal date is **January 1, 2027**, evaluated on the host's
local calendar. Preserve original ref PR-1010 and its missed October 31, 2026
deadline. Record missing evidence at the checkpoint and reassess immediately on
an uncertain cleanup or new finding. Remove sooner on retirement, a verified
safe replacement or qualified disappearance of the warning. No automatic
renewal follows.

The executable check is an observation before launch. Concurrent replacement
by the same user remains outside that check. Initial execution and subsequent
cleanup have separate time intervals, and escaped descendants have no global
absence claim. Rollback removes this term or restores the original annotation,
making the warning or historical expiry visible again. The final local and
current-head checks still require their own complete evidence.
