<!-- markdownlint-disable MD013 -->
# Backlog Ledger (Canonical)

**Purpose:** single source of truth for postponed / follow-up work.
If it is not recorded here — it does not exist.

**Language policy:** Primary language: English. Russian details allowed in linked design/analysis docs for clarity, but backlog entries must include English summary/translation for maintainability and tooling compatibility.

## Rules (non-negotiable)

1) Any postponed work MUST be recorded here immediately.
2) Each item MUST include:
   - Owner
   - Priority (P0/P1/P2)
   - Target PR (number or placeholder)
   - Reason for deferral
   - Links to relevant audit/docs
   - DoD (acceptance criteria)
3) Every PR description MUST include a "Deferred / Follow-ups" section with links to items here.
4) Closing an item requires:
   - PR merged OR explicit "won't do" decision recorded (with reason).

## Open Items

<!-- EXPERIMENT_BACKLOG_ENTRIES:INSERT BELOW -->

<a id="ledger-p1-canonical-coaching-goal-source"></a>
- [ ] P1: Implement the canonical backend source for coaching goal authority
  - Owner: Human Product Owner to assign a dedicated backend plus web/iOS lane
  - Priority: P1 (goal authority / consent / coaching trust)
  - Target PR: Unassigned; set only when the Human Product Owner opens the live-integration lane
  - Status: Deferred live-integration follow-up; non-blocking for the narrow E1-02 internal contract
  - Area: backend goal ownership / authorization / web / iOS / shadow coaching
  - Reason (EN): E1-02 defines only the internal lifecycle and deterministic
    `no_intervention` boundary. A separate canonical producer must establish
    who owns goal truth and how an active goal version becomes demonstrably
    user-confirmed, current, correctable, and revocable before shadow coaching
    can consume live authority. Neither request-scoped goal prose,
    `WeeklyPlan.plan_data`, `safe_goal`, behavioral inference, model output, nor
    engagement policy may be promoted into that source implicitly.
  - Links:
    - `app/schemas/user_coaching_state.py`
    - `app/services/coaching_state_builder.py`
    - `docs/orchestration/FITCHEF_SAFE_PERSONALIZATION_PROTOCOL.md`
  - DoD:
    - backend ownership and the canonical read contract are explicit, with
      object-level authorization (BOLA) tests and no cross-user disclosure
    - consent provenance, persistence and request binding, currentness, and
      correction semantics are explicit and tested
    - versioning covers predecessor/successor integrity plus deterministic
      pause, withdrawal, and supersession behavior
    - web and iOS distinguish unset, unconfirmed, active, paused, withdrawn,
      and superseded states and require explicit confirmation where applicable
    - privacy, auditability, rollback, and stale-version rejection are covered
      without moving authority truth into either client
    - this item blocks claims of live active-goal integration, but does not
      block the narrow source-free E1-02 internal lifecycle contract

<a id="ledger-p1-weekly-profile-client-confirmation"></a>
- [ ] P1: Require explicit web and iOS confirmation for profile-driven weekly plans
  - Owner: Human Product Owner to assign a separate web/iOS client lane
  - Priority: P1 (client truth / weekly-plan trust)
  - Target PR: Unassigned; set only when the Human Product Owner opens the client lane
  - Status: Deferred client follow-up; non-blocking for the narrow E1-01 backend truth boundary
  - Area: web / iOS / weekly planning / backend-contract parity
  - Reason (EN): Web and iOS must distinguish unset or unconfirmed profile
    selections from explicit `moderate` activity and `maintain` goal choices,
    then require user confirmation before a profile-driven weekly-plan
    submission. The backend remains the source of admission truth; clients must
    not infer or synthesize the six core profile values.
  - Links:
    - `app/schemas/vip.py`
    - `app/services/fitchef_runtime.py`
    - `docs/orchestration/FITCHEF_SAFE_PERSONALIZATION_PROTOCOL.md`
  - DoD:
    - web and iOS represent unset and unconfirmed values separately from
      explicit `moderate` and `maintain` selections
    - both clients require confirmation before profile-driven weekly submission
      without moving profile admission or normalization truth out of the backend
    - deterministic web/iOS parity tests cover unset, unconfirmed, explicit,
      confirmed, and backend-rejected submissions
    - the Human Product Owner assigns the separate client lane and target PR
      only when that lane opens
    - this item remains non-blocking for narrow E1-01, but blocks any broader
      claim that a weekly profile is human-confirmed across clients

<a id="ledger-p1-task-normative-envelope-v1-shadow"></a>
- [ ] P1: Task normative envelope v1 shadow contract umbrella
  - Owner: orchestration / security-auditor
  - Priority: P1 (delegated-authority and normative-boundary trust)
  - Target PR: TBD (`codex/task-normative-envelope-v1-shadow`)
  - Status: Bounded shadow contract implementation; no integration authority
  - Area: orchestration / task contracts / fail-closed validation
  - Reason (EN): Task packets need one deterministic, non-authoritative envelope
    for declared purpose, normative boundaries, delegated authority, capability
    evidence, evaluation, and change controls before any later integration is
    considered. The first slice must stay pure and offline so a structurally
    valid or consistent shadow cannot silently become routing, execution,
    approval, promotion, blocking, or merge authority.
  - Links:
    - `docs/orchestration/contracts/TASK_NORMATIVE_ENVELOPE_V1.md`
    - `scripts/orchestration/task_normative_envelope_contract.py`
    - `tests/test_task_normative_envelope_contract.py`
  - DoD:
    - exactly five frozen slot dataclasses and four public functions define the
      explicit v1 surface
    - builder normalization and direct canonical validation enforce the frozen
      ASCII token grammars without echoing rejected raw values
    - the stable mapping and envelope identity reuse the shared evidence
      fingerprint helpers and keep every authority flag literal `False`
    - assessment is limited to local and exact immediate-parent checks, exactly
      16 reasons, and exactly five bounded witnesses
    - authority-basis requirements, norm-conflict classification, parent
      reversibility comparison, recursive ancestry, CLI/I/O, dispatch/runtime
      wiring, and additional authority are excluded
    - focused deterministic tests and type/syntax checks pass before any later
      integration lane is proposed
  - Empirical sequence (exact): N1 internal shadow contract -> 3-5 sanitized
    completed trajectories -> GO/DEFER/STOP -> N2 consumer inventory only after
    GO -> N3 read-only lineage projection only after sufficient outcomes.
  - GO criteria (all required):
    - at least one previously implicit authority or corrigibility mismatch is found
    - no more than one false positive is observed
    - no semantic prose interpretation is required
    - the reviewer judges the assessment more useful than a simple task-packet check
  - DEFER / STOP criteria (any is sufficient):
    - five cases yield zero novel mismatch
    - more than one false positive is observed
    - utility requires free-text interpretation
  - Rollback (EN): Before any consumer exists, remove the pure module, focused
    tests, contract document, and this umbrella entry. N1 has no consumer or
    persisted artifact, so no runtime-state or data migration is required.
  - Deferred / follow-ups (EN): Any bootstrap/dispatcher integration, persisted
    artifact or schema, recursive ancestry, reason/witness expansion, or policy
    enforcement requires its own reviewed follow-up PR and an update to this
    umbrella. This shadow contract alone opens none of those gates.

<a id="ledger-p1-rag-pilot-3b-exact-context-compaction"></a>
- [ ] P1: Pilot 3B default-off exact-carrier RAG context compaction
  - Owner: backend-engineer
  - Priority: P1 (bounded LLM context cost / latency experiment)
  - Branch: `codex/rag-context-compaction-pilot-b3-r2`
  - Target PR: [PR #2257](https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2257)
    (replacement PR; supersedes
    [PR #2249](https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2249))
  - Status: In review in PR #2257; exact current-main provenance is bound by
    the live PR commit graph and final review seal, not duplicated here.
  - Area: backend / RAG / Insight runtime
  - Business reason (EN): Avoid sending byte-for-byte duplicate final evidence
    carriers to the provider when explicitly enabled, while preserving every
    distinct evidence reference and the existing user response fallback.
  - Exact invariant (EN): After mandatory Stage 1 and final metadata/content
    hygiene, collapse only later `RAGChunk` carriers that match an earlier
    carrier in runtime type and value for all five primitive fields
    (`chunk_id`, `file`, `content`, `score`, `hop`). Preserve the first
    occurrence and order. Prompt, sources, confidence, evidence, provenance,
    bundle, and candidates use that one compacted snapshot. Failure returns an
    untouched validated snapshot for the response and closes bundle admission
    and candidates through an existing internal degraded state.
  - Links:
    - `docs/contracts/RAG_CONTRACT.md#34-pilot-3b-exact-carrier-context-compaction`
    - `core/rag/context_compaction.py`
    - [Final roadmap PDF (product intent only; not runtime authority)](https://drive.google.com/file/d/1e7Ij5pV897BTUImocsES26fP0gE0IcxK/view?usp=drivesdk)
  - DoD:
    - optional request-time flag defaults off and is forwarded explicitly from app to core
    - vector and final merged recursive results cross the same outer seam
    - exact duplicates collapse without mutable aliasing; every field difference,
      distinct evidence reference, non-equal score, and original order survive
    - success reports only the bounded internal `chunks_compacted` count
    - mutation or exception returns the pristine final snapshot, one stable
      non-sensitive warning/log record, and closed knowledge admission
    - both Insight aliases retain DTO/OpenAPI, provider-call count,
      guard/quota/rate-limit ordering, and non-RAG fallback behavior
    - focused tests, typecheck, targeted Bandit, branch-diff backend hook,
      `make validate-changed`, full pre-commit, and current-head CI/governance pass
  - Rollback (EN): Set `FEATURE_RAG_CONTEXT_COMPACTION=false` (default) or revert
    the PR. Mandatory Stage 1 and the non-RAG fallback remain unchanged.
  - Out of scope (EN): Stage 0, content-only/normalized/fuzzy/semantic or
    boilerplate deduplication, semantic cache, Evidence Graph serving,
    persistent memory, `TaskNormativeEnvelopeV1`, public routes/DTO/OpenAPI,
    provider/model, quota/rate-limit, and broad RAG cleanup. Semantic-cache
    widening remains prohibited until its dedicated gate opens.

<a id="ledger-p1-rag-main-ci-ownership-carryover"></a>
- [ ] P1: Carry over the RAG main fixture and CI ownership repair into replacement PR #2247
  - Owner: backend-engineer / qa-engineer-agent
  - Priority: P1 (current-main recovery / CI trust)
  - Target PR: [PR #2247](https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2247)
  - Source PR: [PR #2245](https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2245), superseded after its two material commits are verified on replacement PR #2247
  - Status: Integrated into the single operator-authorized remediation lane; exact-head CI and closeout pending
  - Reason (EN): PR #2245 repairs the Stage-1-invalid positive Jaccard fixture
    and the finite `insight_ai` owning-suite gap, but its Trivy check is blocked
    by the dependency identities first assembled in superseded PR #2246 and now
    carried by replacement PR #2247. PR #2246 was in turn blocked in every
    canonical Python matrix by that same fixture. Carrying the two
    already-reviewed commits into the replacement PR breaks the circular dependency
    without changing RAG runtime behavior or weakening Stage 1.
  - Links:
    - `tests/test_rag_vector_feature_flag_guard.py`
    - `.github/workflows/ci.yml`
    - `scripts/ci/ci_risk_profile.py`
    - `tests/test_ci_risk_profile.py`
    - `tests/test_ci_workflow_pr_size_governance_contract.py`
  - DoD:
    - the positive Jaccard mock satisfies the existing Stage-1 minimum while
      `tests/test_rag_validation.py::test_short_content_removed` remains the
      negative control
    - the four finite RAG owner suites occur exactly once in `insight_ai` for
      both `test-pr` and `test-feature`, and each self-routes through the risk
      profile
    - no `core/rag/**`, route, DTO, OpenAPI, provider, quota, or rate-limit
      behavior changes
    - exact PR #2247 current-head Python 3.11, 3.12, and 3.13 matrices pass
      before any main/nightly recovery claim

<a id="ledger-p1-rag-s2-baseline-validation-boundary"></a>
- [ ] P1: RAG-S2 baseline validation boundary
  - Owner: backend-engineer
  - Priority: P1 (AI runtime trust / response continuity)
  - Target PR: [PR #2232](https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2232)
  - Status: In review on `codex/rag-baseline-validation-boundary`
  - Area: backend / RAG / Insight runtime / knowledge admission
  - Business reason (EN): Keep the available non-medical wellness response when
    advisory enrichment fails while preventing any unvalidated retrieval chunk
    from reaching prompts, sources, confidence, provenance, verification
    evidence, or durable knowledge admission.
  - Exact invariant (EN): Every final request-local vector or merged recursive
    chunk set crosses mandatory Stage 1. Response fields derive from one fresh,
    order-preserving Stage-1 survivor snapshot. Knowledge admission additionally
    requires observed successful completion of configured Stages 2-4, no
    existing degraded reason, the existing non-recursive policy, usable final
    formatting/redaction, and an admission-allowing canonical verification
    bundle. Requested feature state alone grants no authority.
  - Links:
    - `docs/contracts/RAG_CONTRACT.md#33-mandatory-stage-1-validation-boundary`
    - `core/rag/philosophy_pipeline.py`
    - `core/rag/orchestration.py`
    - [Final roadmap PDF (product intent only; not runtime authority)](https://drive.google.com/file/d/1e7Ij5pV897BTUImocsES26fP0gE0IcxK/view?usp=drivesdk)
  - DoD:
    - Stage 1 runs for flag-on and flag-off vector and final merged recursive paths
    - Stage-1 exception or zero survivors returns no RAG context and never restores raw chunks
    - Optional-stage mutation or exception returns an untouched Stage-1 snapshot,
      one stable enrichment warning, and closed knowledge admission
    - Prompt, response evidence, provenance, final bundle, and candidates derive
      from the same survivor snapshot after usable formatting and redaction
    - A final post-Stage-1 boundary rejects non-built-in, blank, overlong,
      control/noncharacter-bearing, or mark-only `chunk_id` and `file` values
      before every content carrier while preserving visible decomposed Unicode
      and assigned private-use metadata; this does not add Stage 0
    - Runtime warnings are fixed codes and internal diagnostics contain bounded
      aggregate counts only, with no raw query/content/identifier/path/score or
      exception detail
    - Both Insight aliases preserve response schema, status/error behavior,
      provider-call count, guard/quota/rate-limit ordering, and non-RAG fallback
    - Focused tests, typecheck, targeted Bandit, branch-diff backend hook,
      `make validate-changed`, full pre-commit, and current-head CI/governance
      checks pass without OpenAPI or generated-client changes
  - Rollback (EN): Revert the PR. During an incident, disable all RAG with the
    existing `FEATURE_RAG=false`; `FEATURE_PHILOSOPHY_VALIDATION=false` disables
    only post-Stage-1 enrichment and is not a validation-safety rollback.
  - Out of scope (EN): Semantic cache, GraphRAG, Evidence Graph serving,
    persistent memory, advisory-wiki promotion, new authority engines, Stage-1
    keywords or thresholds, provider/model selection, quota/rate-limit changes,
    telemetry expansion, public routes/DTO/OpenAPI, frontend, and iOS. Semantic
    cache widening is explicitly prohibited while its dedicated gate remains closed.

<a id="ledger-p2-rag-chunk-copy-helper-consolidation"></a>
- [ ] P2: Consolidate RAG chunk-copy helpers and profile boundary copies
  - Owner: backend-engineer
  - Priority: P2
  - Priority note (EN): maintainability cleanup; non-blocking.
  - Target PR: TBD (follow-up cleanup after PR #2232 merges)
  - Status: Deferred from PR #2232 Sourcery review (2026-08-07)
  - Area: backend / RAG
  - Reason (EN): `_copy_rag_chunks` (`core/rag/orchestration.py`)
    and `_copy_chunks` (`core/rag/philosophy_pipeline.py`) are near-identical
    primitive-equivalent copy carriers. Consolidating them and profiling the
    intentional per-boundary copies (pipeline survivors -> snapshot preparation
    -> formatting -> candidate builder) is valid maintainability work but is
    outside the PR #2232 Stage-1 safety boundary; per-boundary independent
    copies are an intentional isolation design, not accidental redundancy.
  - DoD: one shared chunk-copy helper is used by both modules (or intentional
    divergence is documented in `docs/contracts/RAG_CONTRACT.md`), a boundary
    copy profiling note is recorded, and deterministic RAG suites stay green.
  - Links:
    - `core/rag/orchestration.py` (`_copy_rag_chunks`)
    - `core/rag/philosophy_pipeline.py` (`_copy_chunks`)
    - PR #2232 Sourcery top-level review (2026-08-07)

<a id="ledger-p1-cryptography-50-security-floor"></a>
- [ ] P1: Raise the canonical `cryptography` security floor to 50.0.0
  - Owner: backend-engineer
  - Priority: P1 (dependency security / shared-runtime blocker)
  - Branch: `codex/cryptography-50-security-floor-replacement`
  - Target PR: PR #2237
  - Status: PR #2237 open; PR #2236 superseded; post-open review and current-head CI pending
  - Area: Python dependency security / shared runtime locks / approved proxy
  - Business reason (EN): The normal pre-push audit surfaced a bounded
    three-ID `cryptography` advisory cluster. `GHSA-g6cj-pr64-35w5` directly
    covers the repo's 48.0.1 pin and requires 50.0.0; the common 50.0.0 floor
    clears the full bounded cluster through the approved supply path without
    weakening audit policy or changing unrelated product lanes.
  - Exact invariant (EN): Every canonical shared Python source manifest carries
    `cryptography>=50.0.0,<51.0.0`, `constraints.txt` carries
    `cryptography>=50.0.0`, and every corresponding lock pins exactly
    `cryptography==50.0.0`. The dependency-security schema and current-floor map
    enforce the same minimum. Resolution uses only the approved PulsePlate
    proxy, and no other package version or dependency graph node changes.
  - Links:
    - `docs/security/CRYPTOGRAPHY_50_0_0_ADVISORY_CLUSTER.md`
    - `tests/test_dependency_security_guard.py`
    - [GHSA-m2h6-j472-rp4c](https://github.com/advisories/GHSA-m2h6-j472-rp4c)
    - [GHSA-g6cj-pr64-35w5](https://github.com/advisories/GHSA-g6cj-pr64-35w5)
    - [GHSA-jwv3-5hgf-82ww](https://github.com/advisories/GHSA-jwv3-5hgf-82ww)
  - DoD:
    - All four owning `.in` manifests use `>=50.0.0,<51.0.0`, constraints use
      `>=50.0.0`, and all five governed locks pin exactly `50.0.0`
    - A deterministic regression proves the actual all-min-versions guard
      rejects a complete former-48.0.1 surface
    - Approved-proxy preflight, dependency guard, real Fernet/AESGCM consumer
      tests, canonical manifest audit, and lock-delta checks pass
    - The dated 2026-08-04 platform snapshot records the approved proxy's
      macOS-arm64-only exact-50 wheel boundary, Intel macOS devcontainer path,
      conditional host `.venv` support, and host-native iOS/Xcode boundary
    - An isolated approved-proxy Apple Silicon environment imports exact
      `cryptography==50.0.0`, passes Fernet/AESGCM smoke checks, and passes all
      133 selected consumer tests without source-build or public-index fallback
    - Advisory documentation records finite reachability, approved-index
      evidence, rollback, and prohibited shortcuts without treating 50.0.0 as a
      permanent safety guarantee
    - No public-index fallback, emergency-wheel activation, waiver, ignore,
      suppression, unrelated package upgrade, or dependency graph migration
  - Rollback (EN): Revert the repository change and block release until another
    reviewed patched floor is available. Revert does not authorize shipping
    48.0.1 or bypassing the audit; there is no data migration.

<a id="ledger-p0-experiment-runner-container-cve-remediation"></a>
- [ ] P0: Remediate Experiment Runner container HIGH/CRITICAL vulnerabilities
  - Owner: @katsiaryna_kavaleuskaya (Security / Orchestration)
  - Priority: P0 prerequisite for mandatory Experiment Runner oracle evidence
  - Target PR: `codex/fix-experiment-runner-container-cves`
  - Status: Implementation and exact-image admission complete locally; final
    oracle, current-head PR, and merge evidence pending
  - Area: Experiment Runner / container security / supply chain
  - Reason (EN): The immutable bookworm runner baseline reports 61
    HIGH/CRITICAL occurrences across 27 unique vulnerability IDs. Mandatory
    Apple Container oracle evidence must not execute on that image. An exact
    slim-trixie candidate remained blocked with 60 occurrences across 25 unique
    IDs, and Alpine 3.24 could not satisfy the existing exact binary-wheel lock
    for `matplotlib==3.10.8`. The admitted candidate instead uses the exact UBI
    10 minimal digest, verifies exact EPEL sources and RPM signatures, pins the
    complete transitive RPM inventories, and overlays the checksum-pinned
    official CPython 3.13 backport for `CVE-2026-15308`. It preserves the
    private-index locked install and non-root boundary without a vulnerability
    suppression.
  - Links: `deploy/experiment-runner/Containerfile`,
    `tests/test_experiment_runner_dispatch.py`,
    `docs/security/EXPERIMENT_RUNNER_CONTAINER_CVE_REMEDIATION.md`,
    `docs/orchestration/EXPERIMENT_RUNNER_MACOS_RUNBOOK.md`
  - DoD: Build the exact candidate with Apple Container; preserve its immutable
    name-and-digest reference; verify the exported top index, exactly one
    `linux/arm64` manifest, every referenced layer blob, and the manifest-bound
    config by descriptor digest and size; require each layer to be a regular
    file with exact descriptor size and SHA-256; reject proxy-secret names and
    values in config/history; verify the official Trivy 0.72.0 asset against
    its release checksum, refresh its database, and scan the exact OCI layout
    without package-type filtering, with ambient Trivy configuration disabled,
    external ignore-policy, ignore-status, and VEX inputs explicitly empty,
    `/dev/null` ignore file, unfixed findings included, and zero HIGH/CRITICAL
    OS or language-package findings; fail closed unless the report proves Trivy
    schema v2, the exact container/Red Hat 10.2 identity, one 129-package OS
    result, and one 136-package Python result; verify exact RPM versions and the
    CPython patch inside the same digest; verify the complete 107/108/129
    package inventories over NEVRA, header SHA-256, payload digest, and payload
    digest algorithm; preserve sanitized runtime, probe, scanner, and
    success-only exit-status receipts; pass the strict Apple Container probe;
    and accept an oracle-only result with
    `network_budget=0`,
    `shared_tree_untouched: true`, expected backend provenance, and no host path
    or secret. Any retained vulnerable package blocks admission and requires a
    separately authorized remediation decision before oracle execution.

<a id="ledger-p1-pr2133-docker-manifest-prerequisite-consolidation"></a>
- [ ] P1: Consolidate the Docker source-manifest prerequisite into PR #2133
  - Owner: @katsiaryna_kavaleuskaya (Security / CI)
  - Priority: P1
  - Target PR: #2133
  - Status: In progress; carries over and supersedes PR #2120
  - Area: supply-chain / dependency security / CI
  - Reason (EN): PR #2133 remediates the setuptools exclusion-bypass
    vulnerability, but its current-head Docker lane fails before the dependency
    build because `main` still carries an expired SQLite source-artifact review
    date. PR #2120 contains the already reviewed two-file freshness refresh, but
    its governance-only follow-up cannot pass the mandatory pre-push audit while
    that branch still consumes the vulnerable setuptools lock. To avoid bypassing
    either fail-closed gate, PR #2133 carries the unchanged PR #2120 material
    commit and becomes the single merge vehicle for both prerequisites.
  - Links: `scripts/ci/docker_source_artifacts.json`,
    `tests/test_docker_workflow_build_path_contract.py`,
    `docs/review/PR_2133_FIXED_MAPPING.md`,
    `docs/security/CVE-2026-59890-setuptools.md`,
    `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2120`,
    `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2133`
  - DoD: PR #2133 preserves the exact reviewed manifest artifact identity and
    digest, enforces setuptools 83.0.0 across every governed dependency surface,
    records composition evidence for both sealed security scans, passes the
    combined focused/local/current-head Docker and dependency gates, merges to
    `main`, and PR #2120 is closed as superseded only after `main` is verified to
    contain the two-file manifest content.

<a id="ledger-p1-bodyfat-bmi-engine-delegation"></a>
- [ ] P1: Delegate bodyfat missing-BMI derivation to canonical BMI engine
  - Owner: @katsiaryna_kavaleuskaya (Backend / Nutrition)
  - Priority: P1
  - Target PR: TBD after bodyfat route ownership cleanup
  - Status: Open
  - Area: backend routing / nutrition calculation semantics
  - Reason (EN): `app/routers/bodyfat.py` currently derives BMI locally when
    the request omits `bmi`, while canonical BMI calculation and rounding
    semantics live in the BMI engine. This PR keeps bodyfat math unchanged while
    moving route ownership; the derivation seam needs a separate parity-reviewed
    PR so formula and rounding behavior do not drift accidentally.
  - Links: `app/routers/bodyfat.py`, `core/bmi/engine.py`,
    `tests/test_api.py::test_v1_bodyfat`,
    `tests/edges/test_bodyfat_edges.py`
  - DoD: Missing-BMI bodyfat requests delegate through the canonical BMI
    calculation seam or record an explicit semantics decision; supplied-BMI
    requests remain unchanged; deterministic parity tests cover supplied BMI,
    derived BMI, Deurenberg output, and rounding behavior; generated
    OpenAPI/client artifacts remain unchanged unless a separately reviewed
    contract change requires it.

<a id="ledger-p1-first-class-auth-principal-mapping"></a>
- [ ] P1: First-class authenticated principal mapping for API-key-derived subjects
  - Owner: @katsiaryna_kavaleuskaya (Backend / Security)
  - Priority: P1
  - Target PR: Follow-up after PR-3 auth/tier/BOLA contract pack
  - Status: Open
  - Area: security / auth / subject isolation
  - Reason (EN): Current backend contract derives subject principals from authenticated API keys for adherence, nutrition, feedback, RAG, and paid-tier route isolation. PR-3 records and tests that contract, but the long-term auth model still needs first-class user-authentication mapping and operational alerting for suspicious cross-subject attempts without moving product truth into clients.
  - Links: `docs/security/SEC-001-bayes-adherence-horizontal-privilege-escalation.md`, `docs/security/API_AUTH_TIER_BOLA_CONTRACT_PACK.md`, `tests/security/_api_authz_contracts.py`, `docs/contracts/RAG_CONTRACT.md`
  - DoD: Define the canonical authenticated principal model; migrate API-key-derived subject mapping without breaking existing paid-tier/API-key contracts; add deterministic migration and cross-principal negative tests; document rollback and alerting behavior; preserve wellness-only boundaries and keep OpenAPI/client changes in a separately reviewed contract if required.

<a id="ledger-p1-semantic-cache-cost-provenance-train"></a>
- [ ] P1: Semantic cache cost provenance and context-economy PR train
  - Owner: @katsiaryna_kavaleuskaya (AI runtime / orchestration governance)
  - Priority: P1
  - Target PR: PR-O1 merged baseline; PR-O2 merged baseline; PR-O3 merged baseline; current slice PR-O4 `codex/embedding-retrieval-admission-o4`; PR-O5+ deferred behind separate reviewed gates
  - Status: PR-O1 merged as metadata-only cost provenance baseline; PR-O2 merged as deterministic orchestration context compression baseline; PR-O3 merged as provider/model-tier routing policy telemetry; PR-O4 active for gate-closed embedding/retrieval admission telemetry; later runtime-serving work deferred behind separate gate-open PRs
  - Area: AI runtime governance / orchestration cost / semantic-cache scaffold
  - Reason (EN): Expensive GPT-5.5/Codex orchestration currently repeats prompt modules, context, and merge-readiness documentation work without a deterministic way to attribute safe reusable context, estimate saved tokens, label future provider/model-tier policy choices, or pre-classify future embedding/retrieval admission evidence without weakening review quality. PR-O1 created metadata-only provenance, prompt-module fingerprints, and token/cost estimate scaffolding; PR-O2 added deterministic graph/context-pack compression metadata so repeated orchestration context can be measured and de-duplicated without opening semantic-cache serving or provider integration; PR-O3 added metadata-only provider/model-tier routing telemetry with final review and synthesis still `frontier_required`; PR-O4 adds gate-closed embedding/retrieval admission telemetry with all runtime/provider/cache/serving authority flags false.
  - Links: `docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md`, `docs/orchestration/contracts/SEMANTIC_CACHE_COST_PROVENANCE_TELEMETRY.md`, `docs/orchestration/contracts/SEMANTIC_CACHE_CONTEXT_COMPRESSION_TELEMETRY.md`, `docs/orchestration/contracts/SEMANTIC_CACHE_PROVIDER_MODEL_TIER_ROUTING_TELEMETRY.md`, `docs/orchestration/contracts/SEMANTIC_CACHE_EMBEDDING_RETRIEVAL_ADMISSION_TELEMETRY.md`, `core/evidence/fingerprints.py`, `core/ai/prompt_modules.py`, `core/ai/cache_observability.py`, `scripts/orchestration/context_pack_compression.py`, `scripts/orchestration/provider_model_tier_policy.py`, `scripts/orchestration/embedding_retrieval_admission_telemetry.py`
  - PR train:
    - PR-O1: deterministic provenance envelope, prompt-module fingerprint registry, and token/cost telemetry scaffold; metadata-only and non-serving.
    - PR-O2: graph/context-pack compression for repeated orchestration and merge-readiness context; metadata-only, advisory, and non-serving.
    - PR-O3: provider/model-tier routing policy telemetry for orchestration cost decisions; metadata-only, label-only, selected route fixed to `no_runtime_selection`, and final review/synthesis preserved as `frontier_required`.
    - PR-O4: gate-closed embedding/retrieval admission telemetry scaffold; metadata-only, selected embedding backend fixed to `none`, selected retrieval runtime fixed to `none`, and all admission/runtime/provider/cache/serving authority flags false.
    - PR-O5+: replay, observability, runtime admission, and serving candidates remain deferred and require dedicated reviewed gates.
  - Deferred review follow-up: after PR-O3 stabilizes, evaluate whether safe-label,
    metadata-safety, and fingerprint validation helpers should be centralized in a
    shared orchestration utility; do not widen PR-O2 into unrelated shared helper
    extraction.
  - Out of scope: semantic-cache reads/writes, Redis, GPTCache, GraphRAG runtime, embeddings/vector search, Ollama or Perplexity/Sonar API wiring, provider clients/calls, runtime model/provider selection, OpenAPI, DB, frontend, iOS, entitlement/billing truth, provider-specific pricing truth, raw prompts, raw responses, raw queries, raw context snippets, provider payloads, and live cost-savings claims.
  - DoD: PR-O4 keeps markers `closed / false / false / true`; stores only safe fingerprints, IDs, counts, estimates, labels, graph nodes/edges, selected refs, omitted duplicate refs, provider/model-tier labels, embedding/retrieval admission labels, reason codes, and token-economy estimate references; fixes selected route to `no_runtime_selection`, selected embedding backend to `none`, and selected retrieval runtime to `none`; preserves final reasoning/review/synthesis as `frontier_required`; separates token estimates from runtime cost claims and provider pricing; rejects raw and provider payloads, embedding vectors, retrieval queries, similarity scores, secrets, and local paths; passes focused contract tests plus semantic-cache gate checks; documents that runtime serving and provider wiring remain no earlier than separately gated PR-O5+ work.

<a id="ledger-p1-pr-size-governance-trusted-base-execution"></a>
- [ ] P1: PR size governance trusted-base execution switch
  - Owner: @katsiaryna_kavaleuskaya (CI governance)
  - Priority: P1
  - Target PR: Follow-up after PR #1909 merge
  - Status: Open
  - Area: CI / merge governance / PR scope guard
  - Reason (EN): PR #1909 hardens trusted label-backed scope approvals, but premortem found that switching the workflow to execute `check_pr_size_governance.py` from the protected base checkout inside the same PR would ask base code to support behavior introduced only by PR #1909. That sequencing can make current-head CI fail or provide misleading assurance. The switch must land only after base contains the repo-root override and trusted-label contract.
  - Links: `.github/workflows/ci.yml`, `scripts/ci/check_pr_size_governance.py`, `tests/test_ci_workflow_pr_size_governance_contract.py`, `docs/review/PR_1909_FIXED_MAPPING.md`
  - DoD: Update `pr_scope_guard` to checkout PR code and trusted base guard code separately; execute PR size governance from the trusted base copy while setting `PULSEPLATE_SIZE_GOVERNANCE_REPO_ROOT` to the PR checkout; preserve `--base-sha`, `--head-sha`, and `--event-path`; add workflow contract coverage; verify current-head CI and merge-readiness gates.

<a id="ledger-p1-scientific-writing-agent"></a>
- [ ] P1: Scientific Writing Agent registration
  - Owner: @katsiaryna_kavaleuskaya (Agent governance)
  - Priority: P1
  - Target PR: TBD (Phase 2 scientific workforce PR train)
  - Status: Open
  - Area: agents / scientific workforce / publications
  - Reason (EN): Deferred from Phase 1 to keep the initial workforce PR focused on SC-G3 prompt/eval and gate planning blockers. PulsePlate still needs a readonly scientific writing specialist for Abstract, Related Work, Methods, Results, Discussion, citation-format guidance, reproducibility checks, and claim-quality review without creating medical authority.
  - Links: `.cursor/agents/prompt-engineering-eval-agent.md`, `.cursor/agents/project-planning-agent.md`, `docs/orchestration/AGENT_CAPABILITY_MATRIX.md`, `docs/orchestration/AGENT_CONTEXT_MAP.md`
  - DoD: Register `scientific-writing-agent` across canonical agent specs, index, inventory, capability matrix, context map, non-routable allowlist, coordinator summary, native bridge profile, and skill routing policy if needed; define wellness-only scientific-writing boundaries; run `python3 scripts/orchestration/check_agent_consistency.py` and focused registry/bridge gates.

<a id="ledger-p1-experiment-design-stats-agent"></a>
- [ ] P1: Experiment Design & Statistics Agent registration
  - Owner: @katsiaryna_kavaleuskaya (Agent governance)
  - Priority: P1
  - Target PR: TBD (Phase 2 scientific workforce PR train)
  - Status: Open
  - Area: agents / scientific workforce / statistics
  - Reason (EN): Deferred from Phase 1 because `prompt-engineering-eval-agent` and `project-planning-agent` unblock SC-G3 and release sequencing first. PulsePlate still needs a readonly specialist for RCT/A-B/observational design, power and sample-size planning, effect-size interpretation, confidence intervals, p-values, and Bayesian/frequentist validation boundaries for wellness-app studies.
  - Links: `.cursor/agents/data-scientist-agent.md`, `.cursor/agents/bayesian-uq-agent.md`, `docs/evals/PULSEPLATE_EVAL_VALIDITY_CONTRACT.md`, `docs/orchestration/AGENT_EXPERIMENTATION_PROTOCOL.md`
  - DoD: Register `experiment-design-stats-agent` across canonical agent surfaces; explicitly distinguish it from `data-scientist-agent` and `bayesian-uq-agent`; document wellness-only interpretation boundaries; run agent consistency plus focused registry/bridge gates.

<a id="ledger-p2-evidence-synthesis-agent"></a>
- [ ] P2: Evidence Synthesis Agent registration
  - Owner: @katsiaryna_kavaleuskaya (Agent governance)
  - Priority: P2
  - Target PR: TBD (Phase 2 or Phase 3 scientific workforce PR train)
  - Status: Open
  - Area: agents / scientific workforce / evidence synthesis
  - Reason (EN): Deferred from Phase 1 to avoid mixing SC-G3 prompt/eval ownership with literature-review methodology. PulsePlate still needs a readonly evidence synthesis specialist for systematic/scoping reviews, GRADE/Oxford LoE-style evidence grading, contradiction mapping, and product-safe narrative synthesis.
  - Links: `.cursor/agents/web-research-agent.md`, `.cursor/agents/epistemology-discovery-agent.md`, `docs/orchestration/RESEARCH_TRACK_PROTOCOL.md`, `docs/orchestration/AGENT_CONTEXT_MAP.md`
  - DoD: Register `evidence-synthesis-agent` across canonical agent surfaces; require External Claims Register and evidence logs for external claims; document no-medical-authority boundaries; run agent consistency plus focused registry/bridge gates.

<a id="ledger-p2-health-regulatory-agent"></a>
- [ ] P2: Health Regulatory Agent registration
  - Owner: @katsiaryna_kavaleuskaya (Agent governance)
  - Priority: P2
  - Target PR: TBD (Phase 2 or Phase 3 scientific workforce PR train)
  - Status: Open
  - Area: agents / scientific workforce / health data governance
  - Reason (EN): Deferred from Phase 1 because the current PR is scoped to internal agent registration for prompt/eval and planning blockers. PulsePlate still needs a readonly specialist for HIPAA/GDPR health-data analysis, Apple HealthKit / Google Fit governance, FDA wellness vs SaMD classification boundaries, and IRB/ethics-review planning.
  - Links: `AGENTS.md`, `ios/AGENTS.md`, `.cursor/agents/app-store-release-agent.md`, `.cursor/agents/security-auditor.md`, `docs/orchestration/AGENT_CONTEXT_MAP.md`
  - DoD: Register `health-regulatory-agent` across canonical agent surfaces; define advisory-only regulatory boundaries and escalation criteria; preserve wellness-only product positioning; run agent consistency plus focused registry/bridge gates.

<a id="ledger-p1-experiment-runner-operator-plane-slack-closeout"></a>
- [ ] P1: Experiment Runner Operator Plane & Slack Closeout
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR #1880 merged baseline; current slice `codex/private-pilot-manual-smoke-operations-v1`
  - Status: PR #1880 merged on 2026-06-04 as the deterministic no-secret Slack operator-plane CI gate, manual live-smoke activation wording, and semantic-cache gate recheck baseline. PR #1888 added GitHub App/private-pilot readiness. PR #1895 added Private Pilot Activation Evidence v1: typed redacted manual-smoke evidence contract, workflow artifact loop, local operator ledger/report ingestion, and existing `/pulseplate-runner status` projection only. Current slice is Private Pilot Manual Smoke Operations v1: validation-only downloaded evidence handling, local import/dedupe reporting, stale/blocker/manual-smoke history projection, additive Slack status labels, and operator runbook/policy guards, with no HTTPS ingress, no semantic cache, no GraphRAG, no product runtime, no token minting, no PR/review/merge authority, no arbitrary workflow dispatch, and no new Slack command authority.
  - Area: orchestration / Experiment Runner / Slack operator plane / local observability
  - Reason (EN): Finish the Experiment Runner as a Slack-first operator plane without widening product AI runtime, food data, semantic cache, CBT/coaching runtime, frontend MVP, or merge/review authority. Operators need bounded dry-run/approved dispatch visibility, redacted failure/status summaries, and local evidence reports that stay advisory until promoted through repo-reviewed governance.
  - Links:
    - `docs/orchestration/AGENT_EXPERIMENTATION_PROTOCOL.md`
    - `docs/orchestration/EXPERIMENT_RUNNER_SLACK_SOCKET_OPERATOR_RUNBOOK.md`
    - `docs/orchestration/EXPERIMENT_RUNNER_SLACK_APP_MANIFEST.yml`
    - `scripts/orchestration/experiment_slack_socket_bridge.py`
    - `scripts/orchestration/experiment_operator_ledger.py`
    - `.github/workflows/experiment-runner-dispatch.yml`
    - `.github/workflows/experiment-runner-slack-socket-smoke.yml`
  - PR train:
    - PR-1: local operator ledger/report contract, existing Slack status summary hook, runbook/backlog/tests, no command-surface widening
    - PR-2: optional bounded live-smoke evidence exercise if operator secrets and allowlists are available
    - PR-3: optional dashboard/report polish only if it remains local/dev-only under `artifacts/` with committed scripts/tests/docs only
    - PR-4: deterministic `operator_plane_slack` CI risk group and contract suite, manual live-smoke operator evidence wording, current activation diagnostics, semantic-cache gate recheck remains closed (merged as PR #1880)
    - PR-5: Socket Mode activation-readiness CLI/status/report/workflow diagnostics; live smoke remains manual operator evidence only, no HTTPS ingress, no semantic cache, no GraphRAG, no product runtime changes, and no new Slack authority
    - PR-6: Private Pilot Activation Evidence v1; redacted manual-smoke evidence contract, workflow artifact upload, local evidence import/report, status projection, policy guards, no token minting, no PR/review/merge mutation, no arbitrary workflow/ref, no semantic-cache runtime, and no public Slack expansion
    - PR-7: Private Pilot Manual Smoke Operations v1; validation-only downloaded evidence workflow, local import/dedupe labels, stale evidence class, blocker trend, latest smoke class, additive `/pulseplate-runner status` labels, runbook/policy guards, no artifact fetching, no new Slack commands, no token minting, no PR/review/merge mutation, no arbitrary workflow/ref, and no semantic-cache runtime
  - Out of scope: product AI runtime, backend API, OpenAPI, DB migrations, food data, semantic cache, GraphRAG, CBT/coaching runtime, frontend MVP, iOS, PR creation, review-thread resolution, fixed-mapping authority, merge-readiness authority, arbitrary workflow dispatch, HTTPS Slack ingress, and Slack/Git identity expansion.
  - DoD:
    - Slack remains operator-only, dry-run-first, allowlisted, secret-backed, and redacted.
    - Deterministic CI routes Slack/Experiment Runner operator-plane changes through `operator_plane_slack` without live Slack secrets, raw Slack IDs/text, workflow logs, local paths, or token values.
    - Manual live smoke remains `workflow_dispatch` operator evidence only; it is not a required CI gate, not merge-readiness proof, and requires runtime `SLACK_APP_TOKEN` app-level Socket Mode token, `SLACK_BOT_TOKEN` bot token, and channel/user/team allowlists.
    - Socket Mode activation readiness reports only `ready_for_manual_live_smoke`, `blocked_by_missing_secret`, `blocked_by_allowlist`, `blocked_by_smoke_input`, `blocked_by_invalid_config`, or `manual_only` plus value-free `present` / `missing` / `valid` / `invalid` / `not_checked` labels for token class shape, allowlists, smoke input shape, audit retention, and authority boundaries.
    - `/pulseplate-runner status` can include the latest local operator ledger summary when present; no new Slack command is added in PR-1.
    - Local operator ledger records only schema/policy version, task packet id, dispatch mode, fixed workflow file/ref, hashes, safe artifact refs, failure class, co-author decision, and human review outcome.
    - Ledger/report artifacts are local-only under `artifacts/orchestration/experiments/` and must not include raw Slack text, Slack IDs, local absolute paths, health data, provider logs, approval digests, token prefixes, oracle stdout/stderr, raw branch refs, raw hypotheses, or patch text.
    - Observability report is local/dev-only and aggregates ledger/result artifact status without becoming product analytics, runtime truth, or merge evidence by itself.
    - Manual smoke operations validate downloaded redacted activation evidence before import, dedupe identical local evidence, classify stale evidence and blocker trends locally, and surface only label-only status/report projections.
    - Semantic-cache markers remain `closed / false / false / true`; this lane adds no semantic cache, GraphRAG, cache read/write, provider activation, OpenAPI, DB, frontend, iOS, or product-serving behavior.
    - Einstein Arena or other HTTPS Slack ingress requires a separate reviewed PR with Slack signature verification, timestamp freshness, replay protection, rate limiting, runtime allowlists, and a redacted audit contract.
    - Focused tests cover schema strictness, malformed/extra fields, path traversal/symlink rejection, idempotency, redaction, command-surface stability, and runbook authority boundaries.
    - Each implementation PR runs coordinator-first startup, explicit role
      passes, premortem closure, Experiment Runner oracle-only evidence,
      post-open QA/bug/security-auditor passes, exact-material
      `pulseplate-pr-review`, applicable current-head security/governance
      checks, finding dispositions, and the static provider-neutral no-claim
      seal without invoking or waiting for Connector/Codex Security.

<a id="ledger-p1-container-perl-cve-remediation"></a>
- [ ] P1: Container image Perl / IO::Compress / Archive::Tar CVE remediation (CVE-2026-9538, CVE-2026-42497, CVE-2026-8376, CVE-2026-42496, CVE-2026-48959, CVE-2026-48962)
  - Owner: @katsiaryna_kavaleuskaya (Security/SRE)
  - Priority: P1
  - Target PR: codex/fix-main-trivy-container-cves
  - Status: In progress
  - Area: security / container / supply-chain
  - Reason (EN): Main/nightly Docker Trivy failures now report Perl-family findings against `perl-base` / `perl-modules-5.36`. Debian bookworm does not yet provide a clean package-update path for those Perl findings, so this emergency lane remediates by package removal from the production target instead of extending `.trivyignore` or `trivy/ignore-policy.rego`.
  - Links: `Dockerfile`, `.github/workflows/build.yml`, `.github/workflows/trivy.yml`, `scripts/ci/check_docker_runtime_dependency_surface.py`, `.trivyignore`, `trivy/ignore-policy.rego`, `docs/security/CVE-2026-48959-perl-base.md`, `docs/security/CVE-2026-48962-perl-base.md`, `docs/security/CVE-2026-archive-tar-perl-runtime-removal.md`
  - DoD: Production image removes `perl-base` and installed `perl-modules-*`; Docker runtime dependency-surface guard fails if they return; broad `.trivyignore` Perl CVE entries and exact Perl Rego suppressions are removed; current-head Docker build, runtime-surface guard, and Trivy image scan pass before any readiness claim.

<a id="ledger-p1-container-sqlite-cve-remediation"></a>
- [ ] P1: Container image SQLite CVE remediation (CVE-2026-11822, CVE-2026-11824)
  - Owner: @katsiaryna_kavaleuskaya (Security/SRE)
  - Priority: P1
  - Target PR: codex/fix-main-trivy-container-cves
  - Status: In progress
  - Area: security / container / supply-chain
  - Reason (EN): Main Docker publish Trivy now reports `libsqlite3-0 3.40.1-2+deb12u2` for SQLite CVEs with blank fixed-version metadata. SQLite support is still required by PulsePlate fallback, catalog, and Docker smoke paths, so this emergency lane remediates by explicitly pre-fetching and verifying SQLite 3.53.2 source before Docker build, loading that runtime library, and removing Debian `libsqlite3-0` from the production target instead of adding Trivy suppressions or hidden Dockerfile downloads.
  - Links: `Dockerfile`, `.dockerignore`, `.github/workflows/build.yml`, `.github/workflows/trivy.yml`, `scripts/ci/docker_source_artifacts.json`, `scripts/ci/fetch_docker_source_artifacts.py`, `scripts/ci/check_docker_runtime_dependency_surface.py`, `.trivyignore`, `trivy/ignore-policy.rego`, `docs/security/CVE-2026-sqlite-runtime-removal.md`
  - DoD: CI/local Docker lanes run explicit source-artifact preparation before Docker build; Dockerfile performs no live upstream download; production image loads SQLite >=3.53.2 through Python `sqlite3`; production image removes Debian `libsqlite3-0`; Docker runtime dependency-surface guard fails if `libsqlite3-0` returns; broad `.trivyignore` SQLite CVE entries are removed; current-head Docker build/runtime-surface/Trivy image scan pass before any readiness claim.

<a id="ledger-p1-container-gzip-cve-remediation"></a>
- [ ] P1: Container image gzip CVE remediation (CVE-2026-41992)
  - Owner: @katsiaryna_kavaleuskaya (Security/SRE)
  - Priority: P1
  - Target PR: PR #2062 — https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2062
  - Branch: codex/fix-main-docker-publish-gzip-cve-2026-41992
  - Status: In progress
  - Area: security / container / supply-chain
  - Reason (EN): Main Docker publish Trivy reports `gzip 1.12-1` for `CVE-2026-41992` with blank fixed-version metadata. Debian bookworm, trixie, and sid still mark their current `gzip` lines vulnerable, so this emergency lane remediates by production package removal instead of adding `.trivyignore` or `trivy/ignore-policy.rego` suppression.
  - Links: `Dockerfile`, `.github/workflows/build.yml`, `.github/workflows/trivy.yml`, `scripts/ci/check_docker_runtime_dependency_surface.py`, `.trivyignore`, `trivy/ignore-policy.rego`, `docs/security/CVE-2026-41992-gzip.md`
  - DoD: Production image removes `gzip`; Dockerfile fails closed if `gzip`, `gunzip`, or `zcat` binaries remain; Python stdlib `gzip` smoke still passes; Docker build and publish runtime dependency-surface guards fail if `gzip` returns; do not suppress CVE-2026-41992; current-head Docker build/runtime-surface/Trivy image scan pass before any readiness claim.

<a id="ledger-p1-private-pypi-proxy-mirror-parity"></a>
- [ ] P1: Private PyPI proxy mirror parity and origin stability (packages host only — marketing 521 stays intentional)
  - Owner: @katsiaryna_kavaleuskaya (SRE/DevOps)
  - Priority: P1
  - Target PR: infra (out of band) + repo gate `codex/private-python-proxy-health-gate`; close only when `curl` simple pages, CI preflight, and emergency-retirement evidence are green
  - Status: Phase A operator recovery completed for `packages.pulseplate.app`; Phase B repo health/parity gate in progress
  - Area: supply-chain / infra / CI
  - Reason (EN): Approved proxy `PULSEPLATE_PYTHON_INDEX_URL` must return HTTP 200 for project pages under the devpi simple-index root (`https://packages.pulseplate.app/root/pulseplate/+simple/`) used by lockfiles; intermittent **521** / empty index blocks `make venv-sync` and locked CI installs. **Scope clarification:** the public marketing apex `pulseplate.app` may legitimately remain at HTTP 521 because the operator is intentionally gating user access to the unfinished public site — that gate is **not** an outage and must not be reverted as part of this work. The fix is scoped to the *packages* hostname (e.g. `packages.pulseplate.app`) behind `PULSEPLATE_PYTHON_INDEX_URL`. If both hostnames currently share one origin, splitting them so the packages mirror can be healthy while the marketing origin stays gated is part of this item. Repository may use time-boxed `scripts/ci/emergency_python_wheels.json` only as a bridge; parity and removal of emergencies remain infra-owned. Authenticated CI use requires rotated non-root read credentials in `DEVPI_CI_USER` / `DEVPI_CI_PASSWORD` GitHub Secrets with a credential-free index URL; repository Vars must stay credential-free.
  - Links: `docs/DEPENDENCY_MANAGEMENT.md`, `RUNBOOK_AGENT.md` (Python private index triage; hostname split note), `docs/security/PRIVATE_PYTHON_PROXY_HEALTH_GATE.md`, `scripts/ci/check_private_python_proxy_health.py`, `scripts/ci/install_locked_python_requirements.py`
  - Evidence (2026-06-28): DigitalOcean restart restored the `packages.pulseplate.app` origin; repeated project-page probes to `https://packages.pulseplate.app/root/pulseplate/+simple/aiosqlite/` returned HTTP 200; `scripts/ci/install_locked_python_requirements.py --preflight-only` exited 0; representative exact pins were present on project pages for `aiosqlite==0.22.1`, `pydantic-core==2.41.5`, `cryptography==48.0.1`, and `requests==2.33.0`.
  - DoD: Packages hostname origin + Cloudflare path healthy independently of the marketing apex; sync job current; `curl` 200 for representative pins (e.g. `aiosqlite`) on the packages hostname; early CI health/parity job fails fast before dependency-heavy Python setup; exposed root credential rotated out of band; CI uses non-root read credentials from GitHub Secrets via `.netrc`, not URL userinfo or repository Vars; `install_locked_python_requirements.py --preflight-only` succeeds in CI with the prod URL; emergency manifest entries for mirror-lag can be retired after security sign-off; marketing apex gate state is untouched (or explicitly re-decided in a separate operator-approved entry).

<a id="ledger-p1-devcontainer-foundation"></a>
- [x] P1: Docker devcontainer foundation for local development
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: #1646 (merged)
  - Status: Complete
  - Area: developer-experience / docker / onboarding / worktree stability
  - Reason: local development and cloud agent worktrees are fragile under `.venv`-first bootstrap; add Docker devcontainer as recommended backend/web/devops/docs environment while keeping `make venv` as fallback
  - Evidence: `.devcontainer/devcontainer.json`, `.devcontainer/Dockerfile`, `.devcontainer/docker-compose.devcontainer.yml`, `Makefile`, `README.md`, `CONTRIBUTING.md`, `tests/test_devcontainer_foundation.py`
  - DoD: devcontainer files exist, no proxy secrets baked into image, `make devcontainer-bootstrap` exists, `make dc-up/dc-shell/dc-down/dc-smoke` exist, `make venv` remains, docs describe devcontainer as recommended path, iOS/Xcode stays host-native, guard tests pass

Entries are sorted by priority, then theme, then title. Theme uses `Area:` when present and a deterministic title/domain fallback otherwise.
<a id="ledger-p2-devcontainer-ci-smoke"></a>
- [ ] P2: Add CI devcontainer smoke job
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Status: In progress
  - Branch: devx/devcontainer-ci-smoke
  - Target PR: #1653
  - Reason: deferred from devcontainer foundation PR to keep blast radius low; path-scoped `.github/workflows/devcontainer-smoke.yml` job that builds devcontainer image and runs `scripts/devcontainer/smoke.sh` on `.devcontainer/**` changes
  - DoD: CI job exists, path-scoped, builds devcontainer image, runs smoke script, no secrets required, no dependency bootstrap, workflow contract tests pass, does not block unrelated PRs
  - Evidence: `.github/workflows/devcontainer-smoke.yml`, `scripts/devcontainer/smoke.sh`, `tests/test_devcontainer_smoke_workflow.py`

<a id="ledger-p2-makefile-dev-python-migration"></a>
- [x] P2: Migrate Makefile generic targets from VENV_PYTHON to DEV_PYTHON
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: devx/makefile-dev-python-migration
  - Status: Complete
  - Reason: deferred from devcontainer foundation PR; gradually replace hardcoded `.venv/bin/python` in generic Makefile targets (test-fast, lint, typecheck, cov, diff-cov) with DEV_PYTHON; add guard test against new hardcoded `.venv/bin/python` in generic targets
  - DoD: generic targets use DEV_PYTHON, `make venv` unchanged, guard test prevents regression
  - Evidence: `Makefile`, `tests/test_makefile_dev_python_migration.py`, `tests/test_check_local_verify_environment.py`

<a id="ledger-p2-opencode-mcp-devcontainer-compat"></a>
- [ ] P2: OpenCode local MCP command devcontainer compatibility
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: devx/opencode-mcp-devcontainer-compat
  - Status: In progress
  - Reason: opencode.json currently uses `.venv/bin/python` for `pulseplate-chatgpt` MCP server; works on host with .venv but not in devcontainer where .venv is absent or a symlink shim
  - Links: `opencode.json`, `scripts/opencode/run_pulseplate_mcp.sh`, `tests/test_opencode_mcp_devcontainer_compat.py`, PR #1651, PR #1652
  - Evidence: `opencode.json`, `scripts/opencode/run_pulseplate_mcp.sh`, `tests/test_opencode_mcp_devcontainer_compat.py`
  - DoD: opencode.json MCP command no longer hardcodes `.venv/bin/python`; wrapper preserves host `.venv` behavior; wrapper falls back to python3 in devcontainer; no secrets committed; Figma/Cloudflare posture unchanged; guard test exists

<a id="ledger-p1-web-launch-design-polish-v1"></a>
- [x] P1: Web launch shell design polish v1
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR #1608 / `codex/web-launch-design-polish-v1` (merged); PR #1674 / `feat/web-launch-shell-polish-v2` (merged)
  - Status: Complete / Closed
  - Area: web / launch / design system
  - Finding Type: design handoff implementation
  - Reason (EN): PR #1593 accepted the Figma Make `PulsePlate_Web` packet as reference-only design direction. The public launch shell now needs a bounded repo-first polish pass for `/` and `/marketing` using existing tokens/components, wellness-safe copy, and no Figma/Canva runtime authority.
  - Links:
    - `docs/figma/PULSEPLATE_WEB_MAKE_PROTOTYPE_DESIGN_PACKET_2026-04-30.md`
    - `docs/figma/orchestration/sessions/2026-04-30_web_launch_design_polish_v1/01_TASK_ANALYSIS.md`
    - `docs/figma/orchestration/sessions/2026-04-30_web_launch_design_polish_v1/02_DESIGN_IMPLEMENTATION_NOTES.md`
    - `frontend/src/pages/Marketing/PulsePlateMarketingPage.tsx`
    - `frontend/src/components/marketing/`
  - Evidence: PR #1608 merged on 2026-04-30 (`25d5cb954b11278700bf399434b98338b6a501b6`); PR #1608 fixed mapping recorded the focused frontend tests, build evidence, and the reference-only Figma/Canva boundary. PR #1674 merged on 2026-05-06 (`b7fdd245591ad811170ec1d23002081b5978fbe2`) and revalidated `/` and `/marketing` render behavior with no tabbar or horizontal-overflow regression. This docs-only closeout records the completed web launch polish lane only; Figma/Canva remain reference-only, no runtime work is included here, and Design Intelligence PR-1, reference manifest tooling, screen evidence pack, deterministic scorecard, and iOS visual parity remain separate follow-ups.
  - DoD:
    - `/` and `/marketing` still render the public launch shell and keep the tabbar hidden
    - launch page polish uses repo tokens/components and existing routes only
    - hero/product preview hierarchy, section rhythm, responsive layout, focus states, reduced-motion behavior, and CTA clarity are improved
    - wellness copy avoids unsupported proof, diagnosis, medical, guaranteed-outcome, pricing, billing, and store claims
    - focused frontend tests and `npm run build` pass
    - CI parity is confirmed with no local-green / CI-red delta
    - current-head CI is green and `check_merge_ready.py --require-auth` passes
    - merge does not proceed while current `main` stability signals are red
    - Figma/Canva remain reference-only with no writes or generated runtime assets

### P0

<a id="ledger-p0-appstore-release-readiness-full-feature"></a>
- [ ] P0: App Store release readiness closure for full-feature launch
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P0 (App Store submission blocker)
  - Target PR: PR #1582 -> PR-0 merged; PR #1591 -> PR-1 merged; PR #1600 / `release/appstore-readiness-pr2-permission-purpose-strings` -> PR-2 active; PR #1618 -> PR-3 merged; PR #1619 -> PR-4 merged; PR #1620 -> PR-5 merged; PR #1621 -> PR-6 merged; PR #1622 -> PR-7 merged (release base URL fail-fast); PR #1625 -> PR-8 merged (AppIcon marketing asset guard); PR #1627 -> PR-9 merged (HealthKit Swift 6 readiness); PR #1628 -> PR-10 merged (AI wellness consent); PR #1629 -> PR-10b merged (AI consent required state fix); PR #1630 -> PR-11 merged (reviewer notes and metadata sync); PR #1631 -> PR-12 merged (repo-local validation gates); PR #1708 -> PR-13 merged (docs reconciliation); remaining protected release-ops evidence and App Store Connect execution stay operator-owned
  - Status: 🛠️ PR-0 merged in PR #1582; PR-1 merged in PR #1591; PR-2 active in draft PR #1600; PR-3 merged in PR #1618 (reviewer submission matrix); PR-4 merged in PR #1619 (screenshot asset gate); PR-5 merged in PR #1620 (fastlane metadata audit); PR-6 merged in PR #1621 (release notes template and claim policy); PR-7 merged in PR #1622 (release base URL fail-fast); PR-8 merged in PR #1625 (AppIcon marketing asset guard); PR-9 merged in PR #1627 (HealthKit Swift 6 readiness); PR-10 merged in PR #1628 (AI wellness consent); PR-10b merged in PR #1629 (AI consent required state fix); PR-11 merged in PR #1630 (reviewer notes and metadata sync); PR-12 merged in PR #1631 (repo-local validation gates: `make ios-appstore-verify`, `scripts/release/check_ios_appstore_verify.py`, `tests/ios/test_ios_appstore_verify.py`); PR-13 merged in PR #1708. Repo-local App Store readiness train is reconciled through PR-13; final App Store submission still requires protected App Store Connect execution, credentials, upload evidence, Fastlane protected upload mutation, protected upload automation, and operator-owned release-ops outside repo branches.
  - Area: iOS / App Store / privacy / release governance
  - Finding Type: release-truth drift blocker
  - Reason (EN): The release shell must align iOS runtime, backend reachability, App Privacy, privacy manifest, permission strings, App Store assets, reviewer notes, and CI validators before public App Store submission. The fix is not to delete assets or reduce product scope; the train must preserve assets and classify each public submission surface as `SUBMIT_READY`, `IMPLEMENTATION_REQUIRED`, or `INTERNAL_REVIEW_ONLY`.
  - Links:
    - `docs/release/APPSTORE_RELEASE_READINESS_EPIC.md`
    - `docs/release/APPSTORE_FEATURE_ASSET_MATRIX.md`
    - `docs/release/APPSTORE_REVIEWER_SUBMISSION_MATRIX.md`
    - `docs/release/APPSTORE_SCREENSHOT_ASSET_GATE.md`
    - `docs/release/APPSTORE_FASTLANE_METADATA_AUDIT.md`
    - `docs/release/APPSTORE_RELEASE_NOTES_TEMPLATE.md`
    - `docs/orchestration/APPSTORE_RELEASE_READINESS_TASK_PACKET_2026-04-29.md`
    - `docs/orchestration/APPSTORE_RELEASE_READINESS_PR1_PRIVACY_PACKET_2026-04-30.md`
    - `docs/orchestration/APPSTORE_RELEASE_READINESS_PR2_PERMISSION_PACKET_2026-04-30.md`
    - `docs/review/PR_1600_FIXED_MAPPING.md`
    - `docs/runbooks/IOS_APPSTORE_ASSETS_ROLLOUT.md`
    - `ios/fastlane/app_privacy_details.json`
    - `ios/PulsePlate/Services/AppConfig.swift`
    - `ios/PulsePlate/AppStore/AppStoreScreenshotContext.swift`
    - `ios/PulsePlate/Models/HealthKitManager.swift`
    - `ios/PulsePlate/Assets.xcassets/AppIcon.appiconset/Contents.json`
  - DoD:
    - `ios/PulsePlate/PrivacyInfo.xcprivacy` exists and covers required-reason API use
    - App Privacy no longer declares `DATA_NOT_COLLECTED` while profile, AI, billing, receipt, activation, or diagnostics data leaves the device
    - Release `BASE_URL` is explicit HTTPS and fails before submission if missing or invalid
    - Unused sensitive permission strings are removed from release localization files
    - App Store screenshot scenarios are classified and blocked from submission unless release-enabled, smoke-tested, privacy-disclosed, and reviewer-note-covered
    - AppIcon marketing asset validates through the release asset gate
    - HealthKit remains read-only and Swift 6 clean
    - AI/CBT free-text flow is gated by explicit wellness-only consent
    - Reviewer notes, metadata, privacy map, and release validators enforce no drift

<a id="ledger-p0-self-hosted-postgres-droplet-foundation"></a>
- [x] P0: Self-hosted Postgres Droplet Foundation
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P0 (deployment-safety blocker)
  - Target PR: PR `#1417` (`docs/close-postgres-droplet-foundation-ledger`)
  - Area: infra / database / deploy
  - Status: Closed by repo/runtime evidence reconciliation. Managed PostgreSQL is the canonical default production lane; self-hosted PostgreSQL on the Droplet remains the supported lane B. No new infra implementation PR is required before Foods B2.
  - Reason: The repo already carries both production lanes, the required environment contract, and backup/restore operational assets. This item stayed open only because the backlog wording drifted behind the shipped deploy/runtime truth. SQLite remains dev/test fallback only.
  - Links:
    - docs/deploy/POSTGRES_SELF_HOSTED_DROPLET.md
    - deploy/docker-compose.production.yaml
    - deploy/docker-compose.production.selfhosted.yaml
    - deploy/systemd/pulseplate-postgres-backup.service.example
    - deploy/systemd/pulseplate-postgres-backup.timer.example
    - scripts/ops/postgres_backup.sh
    - scripts/ops/postgres_restore.sh
    - .env.example
  - DoD:
    - Backlog wording no longer claims an open infra implementation wave that is already present in repo
    - Closure evidence points to the canonical two-lane runbook, both production compose files, backup/restore assets, and `.env.example`
    - Deploy/docs canon is explicit that managed PostgreSQL is the default production lane and self-hosted PostgreSQL is the supported lane B
    - Foods sequencing no longer treats this item as the mandatory implementation blocker ahead of B2

<a id="ledger-p0-payments-ruby-ios"></a>
- [ ] P0: Payment rails for RU/BY + iOS-first monetization baseline
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P0 (revenue continuity)
  - Target PR: PR #1182 (B1 baseline) -> PR #1295 (main bootstrap blocker) -> PR #1296 (activation/persistence closeout) -> PR-TBD-BILLING-ENTITLEMENT-ROUTING
  - Status: B1 baseline closed (PR #1182); bootstrap blocker landed via PR #1295; activation + subscription persistence truth merged in PR #1296; current `main` carries the backend entitlement-routing runtime contract shipped in PR #1192, with the closeout packet in PR #1298 documenting that landed backend authz truth. Next active P0 release-truth lane: `ledger-p0-web-entitlement-truth`. Evidence: `docs/contracts/PAYMENTS_RU_BY_IOS_BASELINE.md`, `app/services/payments_activation.py:1`, `app/middleware/api_tiers.py:225`, `app/bootstrap/startup_guards.py:25`, `tests/test_paid_route_guards.py:289`, `tests/test_paid_route_guards.py:311`.
  - Carryover: PR #1005 keeps only the `RUBY` -> `RU_BY` identifier cleanup so the ledger stays aligned with the existing payments contract naming.
  - Reason (EN): Current business reality requires region-adapted payment rails: iOS as primary automated channel, RU/BY payments via eRIP (QR to account) and SWIFT card transfer fallback. Canonical billing flow must support these rails before global providers expansion. (RU: Текущий источник оплат: iOS + RU/BY локальные каналы (ЕРИП/QR и SWIFT). Нужен канонический billing baseline под эту реальность до расширения на глобальные провайдеры.)
  - Links:
    - docs/contracts/PAYMENTS_RU_BY_IOS_BASELINE.md
    - docs/contracts/API_CANONICAL_MAP.md
    - docs/IOS_API_INTEGRATION.md
    - docs/audit/PR_PAYMENTS_RUBY_IOS_CONTRACT_AUDIT.md
    - docs/contracts/PRODUCT_TIER_MAP.md
    - docs/review/PR_1182_FIXED_MAPPING.md
    - ios/PulsePlate/Services/ProKeyProvider.swift:1
    - app/routers/pro_registration.py:1
    - app/routers/pro_payments.py:1
    - app/schemas/payments.py:1
    - app/services/payments_activation.py:1
  - Prerequisites:
    - ✅ Tier activation contract exists (FREE/PRO/VIP)
    - ✅ Unified billing activation service is finalized for source-specific receipts
  - DoD:
    - Canonical source model documented: `ios_app_store`, `erip_qr`, `swift_manual`
    - `activate_subscription()` contract supports all three sources with deterministic audit trail
    - iOS receipt verification remains automated path; RU/BY flows have explicit reconciliation status lifecycle
    - API/webhook/error contracts are tested and non-breaking for existing clients
    - Runtime test plan is locked before implementation (`test_payment_source_contract_api`, `test_subscription_activation_api`, `test_ios_receipt_verification_api`, `test_payment_webhook_signature_api`, `test_payment_reconciliation_api`)

<a id="ledger-p0-billing-activation-service"></a>
- [x] P0: Billing activation service follow-through after Apple verify
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P0
  - Target PR: PR #1296
  - Status: ✅ Merged (PR #1296, 2026-04-02)
  - Area: backend / payments / activation
  - Finding Type: monetization chain gap
  - Reason: The verify-only PR intentionally stops before activation side effects, so the next runtime segment must consume the normalized Apple verification payload and activate paid access deterministically.
  - Links:
    - `docs/contracts/PAYMENTS_RU_BY_IOS_BASELINE.md`
    - `app/routers/billing.py`
    - `app/services/payments_activation.py`
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p0-billing-apple-verify`
  - DoD:
    - Activation service consumes the Apple verification contract without reintroducing client tier truth
    - Verify and activate remain separate runtime stages with deterministic handoff semantics
    - Activation-path tests cover success, replay, and failure transitions
    - No active runtime truth or readback path depends on `_ACTIVATIONS`
    - Activation readback is derived from persisted `subscriptions` plus `subscription_activation_audit`

<a id="ledger-p0-billing-subscription-persistence"></a>
- [x] P0: Subscription persistence for billing activation outcomes
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P0
  - Target PR: PR #1296
  - Status: ✅ Merged (PR #1296, 2026-04-02)
  - Area: backend / payments / persistence
  - Finding Type: subscription state gap
  - Reason: Verification responses are activation-ready, but canonical subscription state still lacks durable persistence for user, tier, platform, expiry, and receipt-linked audit fields.
  - Links:
    - `docs/contracts/PAYMENTS_RU_BY_IOS_BASELINE.md`
    - `app/services/payments_activation.py`
    - `app/services/subscriptions.py`
    - `app/schemas/payments.py`
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p0-billing-apple-verify`
  - DoD:
    - Subscription state is persisted with deterministic idempotency semantics
    - Persisted truth is stored in `subscriptions` plus `subscription_activation_audit`
    - Persistence schema stores canonical tier/platform/expires_at/receipt audit fields
    - Activation readback and reconcile status resolve from persisted subscription lineage
    - Tests prove repeated activation cannot create duplicate subscription state

<a id="ledger-p0-billing-entitlement-routing"></a>
- [x] P0: Entitlement-backed routing after billing activation
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P0
  - Target PR: PR #1192 (runtime entitlement routing baseline) -> PR #1298 (docs/authz closeout packet) -> PR #1380 (docs-only ledger closeout)
  - Status: ✅ Closed. Current `main` already carries the backend entitlement-routing runtime contract shipped in PR #1192; PR #1298 provides the closeout packet and governance evidence for that landed backend authz behavior. This docs-only lane reconciles the canonical ledger to shipped behavior and promotes `ledger-p0-web-entitlement-truth` as the next active P0 release-truth lane.
  - Area: backend / authz / routing
  - Finding Type: access-control gap
  - Reason: Closed by shipped backend entitlement-routing plus fail-closed startup/runtime guards; remaining web/frontend entitlement truth stays tracked under `ledger-p0-web-entitlement-truth`.
  - Evidence:
    - `docs/audit/PR4_ENTITLEMENT_ROUTING_CLOSEOUT_AUDIT_2026-04-02.md:22`
    - `docs/audit/PR4_ENTITLEMENT_ROUTING_CLOSEOUT_AUDIT_2026-04-02.md:40`
    - `docs/review/PR_1298_FIXED_MAPPING.md:43`
    - `app/middleware/api_tiers.py:225`
    - `app/middleware/api_tiers.py:364`
    - `app/routers/billing.py:242`
    - `app/bootstrap/startup_guards.py:25`
    - `tests/test_paid_route_guards.py:289`
    - `tests/test_paid_route_guards.py:311`
    - `tests/test_pro_vip_route_dependency_guard.py:86`
  - Links:
    - `docs/contracts/PAYMENTS_RU_BY_IOS_BASELINE.md`
    - `app/routers/billing.py`
    - `app/middleware/api_tiers.py`
    - `app/bootstrap/startup_guards.py`
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p0-billing-apple-verify`
  - DoD:
    - Entitlement truth is derived from backend activation/subscription state
    - Route guards consume entitlement state instead of client-declared tier
    - Production/staging fail closed when DB-backed entitlement mode is required but disabled/misconfigured
    - Manual RU/BY rails have an explicit pre-entitlement contract (transport-auth carveout or documented back-office-only posture)
    - Regression tests cover paid, expired, and missing-entitlement paths

<a id="ledger-p0-requested-agent-bootstrap"></a>
- [x] P0: Requested-agent bootstrap override and advisory specialist contract
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P0
  - Target PR: PR #1354 (https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1354)
  - Status: ✅ Merged (PR #1354, 2026-04-06; merge commit `ba9ea2f8`). Ledger checkbox closed in PR #1356 (mandatory docs-only follow-up the same working day; backlog ledger policy).
  - Area: orchestration / task bootstrap / routing
  - Finding Type: coordinator bootstrap gap
  - Reason: The canonical coordinator workflow must preserve explicit user-requested agent slugs instead of dropping them during bootstrap. This is especially critical for `agent-coordinator`, `backend-engineer`, `bug-hunter`, `ml-engineer-agent`, and `data-scientist-agent`, where current routing semantics otherwise under-express user intent or hide non-routable specialists.
  - Links:
    - `scripts/orchestration/task_bootstrap.py`
    - `docs/orchestration/AGENT_ROUTING_GRAPH.md`
    - `docs/orchestration/AGENT_NON_ROUTABLE_SPECIALISTS.md`
    - `docs/orchestration/workflow.md`
    - `tests/test_task_bootstrap.py` (integration tests: `test_build_task_packet_*requested*`)
  - DoD:
    - Task packet schema records `requested_agents`
    - Bootstrap either honors, preserves as advisory, or rejects each requested slug with explicit rationale
    - Non-routable specialists are documented as user-requestable/advisory rather than silently unreachable
    - Deterministic tests cover routable promotion and non-routable advisory behavior
  - Evidence (implementation):
    - Graph slot set is evaluated before the non-routable specialist list so in-graph secondaries (e.g. `data-scientist-agent` on `cv`) promote correctly: `scripts/orchestration/task_bootstrap.py:568` (`allowed_promotions`), `:575` (graph precedence comment)
    - Doc precedence: `docs/orchestration/AGENT_NON_ROUTABLE_SPECIALISTS.md:10`, rule 14 `docs/orchestration/AGENT_ROUTING_GRAPH.md:116`

<a id="ledger-p0-verify-env-wrapper-parity"></a>
- [ ] P0: Verify-env executable wrapper parity for local merge gate
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P0
  - Target PR: #1357
  - Area: tooling / local verify / developer workflow
  - Finding Type: false-green preflight gap
  - Reason: Local `make verify` can fail after `verify-env` already passed when stale `.venv` console entrypoints still point to deleted interpreters/worktrees. The preflight must detect broken wrappers or switch the gate to interpreter-module mode so local merge evidence is trustworthy.
  - Links:
    - `Makefile`
    - `scripts/ci/check_local_verify_environment.py`
    - `tests/test_check_local_verify_environment.py`
    - `RUNBOOK_AGENT.md` (section “Clean-Clone Verify Parity” / verify-env)
    - `AGENTS.md` (Hard Gates / verify-env console-script note)
  - DoD:
    - `verify-env` detects stale or non-executable repo tool wrappers before `lint`
    - Local verify path fails with explicit remediation instead of bad-interpreter shell errors
    - Deterministic tests cover stale shebang or broken-wrapper detection
    - Local merge-gate docs reference the stronger parity check
  - Status: implementation may land in a runtime PR; close this checkbox via a same-day docs-only PR after merge (ledger policy).

<a id="ledger-p0-web-entitlement-truth"></a>
- [x] P0: Web entitlement truth must come from canonical backend/store state
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P0
  - Target PR: PR `#1381`
  - Status: ✅ Closed. PR `#1381` (`feat(frontend): move web premium truth to canonical backend/store state`) merged on `2026-04-09` (`America/New_York`). Exception approved by KK on `2026-04-13`: the docs-only closeout was intentionally batched into the monetization planning-wave bootstrap after merged-state verification across the monetization backbone. Current `main` keeps canonical web entitlement truth on `/api/v1/pro/session`, release-path mocks no longer institutionalize `/api/purchase` or `/api/restore`, and web checkout remains thin-client-safe / fail-closed instead of pretending browser-side purchase success.
  - Area: frontend / monetization / thin-client
  - Finding Type: thin-client and release-truth gap
  - Reason: This release-truth lane is no longer an active runtime gap. `origin/main` already consumes canonical backend/store session truth on the web surface, so remaining monetization work must move to planning-flow value capture instead of reopening entitlement plumbing.
  - Links:
    - `frontend/src/lib/usePremium.ts`
    - `frontend/src/lib/paywallPurchase.ts`
    - `frontend/src/mocks/handlers.ts`
    - `frontend/src/mocks/__tests__/purchase.test.ts`
    - `frontend/src/pages/Pro/__tests__/ProPaywallPage.test.tsx`
    - `frontend/src/api/openapi.json`
    - `frontend/AGENTS.md`
  - DoD:
    - Web premium/paywall state derives from canonical backend or StoreKit-backed truth, not `localStorage`
    - Mock-only `/api/purchase` / `/api/restore` flows are removed from release path or explicitly gated to dev-only
    - Thin-client guards and targeted frontend tests cover the new source-of-truth path
    - Funnel/recovery UX stays additive and contract-safe

<a id="ledger-p0-web-progress-contract"></a>
- [x] P0: Web progress route must not ship demo-grade health data
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P0
  - Target PR: PR #1299 (runtime truth hardening) -> PR #1301 (docs closeout)
  - Area: frontend / progress UX / trust
  - Finding Type: user-facing data integrity gap
  - Status: ✅ Runtime closeout already landed on `main`; this docs-only lane reconciles roadmap/design/audit truth to the shipped release-safe behavior.
  - Reason: The release path no longer renders fabricated progress charts. Current web behavior is an explicit trusted empty state with export disabled until real data exists, so the remaining gap is documentation drift rather than a new frontend/backend feature lane.
  - Links:
    - `frontend/src/features/progress/ProgressCharts.tsx`
    - `frontend/src/pages/Progress.tsx`
    - `frontend/src/features/progress/__tests__/ProgressCharts.test.tsx`
    - `docs/audit/PR_WEB_PROGRESS_CLOSEOUT_AUDIT_2026-04-02.md`
    - `docs/analysis/FRONTEND_IOS_VISUAL_ANALYSIS.md`
  - DoD:
    - Progress route renders explicit empty/loading states instead of fabricated chart fixtures in the release path
    - Tests lock the trusted empty-state behavior rather than demo-only chart values
    - UX remains clear when historical data is absent
    - Release screenshots/copy cannot imply fabricated trend data
    - Future backend-fed history/chart work remains a separate optional lane and is not claimed as implemented here

<a id="ledger-p0-eu-compliance-control-plane-follow-through"></a>
- [ ] P0: EU-first compliance control plane follow-through
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P0
  - Target PR: PR #1046 -> PR #1307 -> PR-TBD-EU-COMPLIANCE-FOLLOW-THROUGH
  - Status: 🟡 In progress (baseline control-plane foundation merged in PR #1046; runtime/doc sync follow-through, legacy `/privacy` disclosure alignment, and deterministic drift-hardening merged in PR #1307 on 2026-04-03; program-level DSAR/public-surface and regulated-lane follow-through remain open)
  - Area: backend / privacy / legal docs / AI governance
  - Finding Type: compliance program hardening
  - Reason: Foundation runtime/docs work now establishes a canonical compliance control plane (`docs/compliance/*`, `core/compliance/*`, additive `/privacy` sync), but rollout still needs one program-level epic so future privacy, transparency, DSAR, and regulated-lane work does not drift into isolated follow-ups. This epic supersedes fragmented treatment of the same theme.
  - Links:
    - `docs/compliance/README.md`
    - `docs/compliance/DATA_CLASSIFICATION_AND_PROCESSING_MATRIX.md`
    - `docs/compliance/AI_TRANSPARENCY_AND_PROFILING_NOTICE.md`
    - `docs/compliance/DSAR_AND_DELETION_MAP.md`
    - `docs/compliance/US_REGULATED_LANE_RFC_42_CFR_PART_2.md`
    - `docs/legal/Privacy.md`
    - `docs/review/PR_1307_FIXED_MAPPING.md`
    - `core/compliance/privacy.py`
    - `core/compliance/transparency.py`
    - `legacy_app.py`
    - `tests/test_compliance_control_plane.py`
  - DoD:
    - `/privacy`, `docs/legal/Privacy.md`, and `core/compliance/*` remain synchronized for every new health-ish or AI surface
    - New AI or health-adjacent surfaces add transparency + minimization entries before release
    - Support-led DSAR workflow for direct-user artifacts is documented and used until a public auth-bound DSAR API is explicitly designed
    - The US regulated lane remains blocked from the wellness runtime until separate legal/compliance approval
    - Future public DSAR/export/delete endpoints are blocked until auth/ownership contract is explicit

<a id="ledger-p0-legal-policy-publish"></a>
- [x] P0: Legal policy publish and client-link alignment
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P0
  - Target PR: PR-1304
  - Status: ✅ Merged (PR #1304, 2026-04-02)
  - Area: docs / legal / release readiness
  - Finding Type: policy publication gap
  - Reason (EN): Privacy and Terms posture has been materially clarified in runtime and compliance docs, but canonical published policy paths and client references still need one explicit release-blocker item.
  - Links:
    - `docs/legal/Privacy.md`
    - `legacy_app.py`
    - `docs/roadmap/P0_MASTER_CHECKLIST_PHASE_FIT_TRIAGE_2026-03-05.md`
  - DoD:
    - Canonical privacy and terms publication paths exist in-repo
    - Web and iOS clients link to the published policy paths consistently
    - Published text stays aligned with runtime wellness/compliance posture
<a id="ledger-p0-insight-fallback-chain"></a>
- [x] P0: Insight fallback chain + echo-mode readiness visibility
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P0 (VIP reliability)
  - Target PR: PR `#1379`
  - Status: ✅ Merged (PR #1379, 2026-04-10; merge commit `1ddf8c6778ca1f13c2bfce2e052db5409e8d06ba`)
  - Reason (EN): Master checklist items #2 and #4 require deterministic behavior when primary LLM/provider path is unavailable and explicit operator visibility for fallback/echo mode.
  - Links:
    - docs/roadmap/P0_MASTER_CHECKLIST_PHASE_FIT_TRIAGE_2026-03-05.md
    - docs/roadmap/PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md
    - docs/review/PR_1379_FIXED_MAPPING.md
    - llm.py
    - app/routers/vip.py
    - app/main.py
  - DoD:
    - Provider fallback order is deterministic and test-covered
    - `/ready` exposes fallback/echo-mode state without leaking secrets
    - Insight response contract remains backward-compatible under fallback


<a id="ledger-p0-master-checklist-triage"></a>
- [ ] P0: Master checklist phase-fit triage (PulsePlate_Master_Checklist v1.0)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P0 (program alignment / scope control)
  - Target PR: PR-TBD-MASTER-CHECKLIST-TRIAGE
  - Status: 🟡 In progress (phase-fit matrix published; execution mapping in progress)
  - Reason (EN): External checklist contains valid launch concerns, but several items are release-phase only and can overload current execution wave. We need a canonical Now/Next/Later decision matrix tied to active implementation reality (food/restaurant hardening + quality-first AI track). (RU: Внешний чеклист полезен, но часть пунктов относится к релизной фазе и не должна ломать текущий execution flow. Нужна каноническая матрица Now/Next/Later по фактической стадии проекта.)
  - Links:
    - docs/roadmap/BACKLOG_LEDGER.md
    - docs/roadmap/PulsePlate_Master_Checklist_v1.0.md:1
    - docs/roadmap/P0_MASTER_CHECKLIST_PHASE_FIT_TRIAGE_2026-03-05.md
    - [PulsePlate_Master_Checklist v1.0 source](https://docs.google.com/document/d/1FkHyYUwb8W8Rb-pTQE9OvqHUT5hZyaE2/edit)
    - docs/analysis/LLM_RAG_AI_ASSISTANT_ANALYSIS.md
    - docs/design/RESTAURANT_INTEGRATION_SPEC.md
  - DoD:
    - Every checklist item is mapped to one of: `Now`, `Next`, `Later`, `Deferred`
    - Canonical triage matrix artifact exists in-repo and is versioned
    - `Now` items are represented by explicit backlog entries with owner + DoD + target PR
    - `Later/Deferred` items include re-activation trigger (release readiness / market / platform milestone)
    - No duplicate or conflicting ownership across active worktrees

### P1

<a id="ledger-p1-release-control-plane"></a>
- [ ] P1: Release automation control plane for C4, App Store Review, ML gates, and supply chain
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-0 -> PR-1 -> PR-2 -> PR-3 (PR #1605) -> PR-4 (PR #1679) -> PR-5 (PR #1682) -> PR-6 (PR #1688) -> PR #1692 -> PR #1699 -> PR #1703
  - Area: release / App Store / AI evals / supply-chain / orchestration
  - Finding Type: release evidence unification gap
  - Status: PR-0, PR-1, and PR-2 merged; PR-3 merged in PR #1605 on 2026-04-30; PR-4 merged in PR #1679 on 2026-05-06; PR-5 merged in PR #1682 on 2026-05-06; PR-6 merged in PR #1688 on 2026-05-06; PR #1692 enforces the production tag path fail-closed against PR-6 real evidence wiring and intentionally blocks production tags until protected release evidence is supplied. PR #1699 merged the governed manual evidence-publication workflow on 2026-05-07 (`ci/release-control-plane-evidence-publication`). The former active `ci/release-control-plane-source-producers` follow-up merged as PR #1703 with governed `workflow_dispatch` source producers for `Release Manifest Evidence` and `Build Equivalence Evidence`, so the PR #1699 publisher no longer depends on ad hoc source runs. The release-control-plane evidence plumbing is complete through governed source producers -> governed publisher -> production CD gate. Future protected artifact publication/upload automation and App Store Connect execution for App Store release remains out of scope; App Store Connect execution, Fastlane protected upload mutation, and final App Store readiness remain deferred. The full App Store readiness is not complete, and the broader release/App Store train is not production-ready.
  - Deferred follow-ups:
    - App Store Connect execution
      - Target PR: TBD App Store release execution/readiness lane
      - Reason for deferral: Release-control-plane evidence plumbing validates release evidence; it does not upload binaries or mutate App Store Connect state.
      - Links: PR #1699, PR #1703, `docs/release/RELEASE_CONTROL_PLANE_EPIC.md`
      - DoD: Protected App Store Connect execution is explicitly scoped, credential-gated, reviewed, and separated from evidence validation.
    - Fastlane protected upload mutation
      - Target PR: TBD Fastlane protected upload lane
      - Reason for deferral: Fastlane upload behavior is a protected release execution surface and remains outside this docs-only reconciliation.
      - Links: PR #1699, PR #1703, `docs/runbooks/IOS_APPSTORE_ASSETS_ROLLOUT.md`
      - DoD: Fastlane upload mutation is reviewed with protected environment controls, rollback notes, and App Store readiness evidence.
    - Protected artifact publication/upload automation
      - Target PR: TBD protected release automation lane
      - Reason for deferral: The evidence chain is complete through governed producer and publisher workflows, but protected upload automation is a separate credentialed execution concern.
      - Links: PR #1699, PR #1703, `.github/workflows/release-control-plane-evidence.yml`
      - DoD: Protected upload automation is explicitly scoped, cannot bypass the release-control-plane gate, and preserves fail-closed evidence checks.
    - Final App Store readiness and broader release/App Store train
      - Target PR: TBD App Store readiness closeout lane
      - Reason for deferral: Evidence plumbing completion is not the same as App Store submission readiness.
      - Links: PR #1699, PR #1703, `docs/release/RELEASE_CONTROL_PLANE_EPIC.md`
      - DoD: App Store readiness is separately reconciled against metadata, privacy, screenshots, credentials, and submission gates.
  - Reason (EN): The App Store readiness PR train is owned separately, while the attached release-automation document also identifies a cross-cutting control-plane gap: build identity, reviewer packet identity, RAG/ML gate identity, supply-chain provenance, and the final release decision are not yet represented by one machine-readable release packet. This line complements PR `#1582` without editing its branch or worktree.
  - Links:
    - `docs/orchestration/RELEASE_CONTROL_PLANE_TASK_PACKET_2026-04-29.md`
    - `docs/release/RELEASE_CONTROL_PLANE_EPIC.md`
    - `docs/release/REVIEWER_PACKET_HASH_CONTRACT.md`
    - `docs/release/REVIEWER_PACKET_HASH_CONTRACT.schema.json`
    - `docs/release/RAG_GATE_RESULT_EXPORT_CONTRACT.md`
    - `docs/release/RAG_GATE_RESULT_EXPORT_CONTRACT.schema.json`
    - `docs/release/RELEASE_MANIFEST_CONTRACT.md`
    - `docs/release/RELEASE_MANIFEST_CONTRACT.schema.json`
    - `docs/release/BUILD_EQUIVALENCE_CONTRACT.md`
    - `docs/release/BUILD_EQUIVALENCE_CONTRACT.schema.json`
    - `docs/release/RELEASE_CONTROL_PLANE_CI_GATE.md`
    - `docs/release/RELEASE_CONTROL_PLANE_CI_GATE.schema.json`
    - `docs/release/PRODUCTION_RELEASE_EVIDENCE_PUBLICATION.md`
    - `.github/workflows/release-control-plane-evidence.yml`
    - `.github/workflows/release-manifest-evidence.yml`
    - `.github/workflows/build-equivalence-evidence.yml`
    - `scripts/release/release_manifest.py`
    - `scripts/release/build_identity.py`
    - `scripts/release/build_equivalence.py`
    - `scripts/ci/check_release_control_plane.py`
    - `docs/architecture/C4_RELEASE_CONTROL_PLANE_CONTEXT.md`
    - `docs/evals/PULSEPLATE_RAG_RELEASE_GATES.md`
    - `scripts/evals/run_rag_release_gates.py`
    - `scripts/ci/check_docker_provenance_attestation.py`
    - `docs/runbooks/IOS_APPSTORE_ASSETS_ROLLOUT.md`
  - DoD:
    - PR-0 lands governance docs, C4 release-risk context, packet, and this ledger anchor without runtime/workflow changes.
    - PR-1 defines reviewer-packet hash contract after App Store readiness artifacts land on `main`, including `reviewer_notes_hash`, `appstore_metadata_hash`, canonical UTF-8 SHA-256 rules, and schema tests.
    - PR-2 exports a stable RAG/ML gate-result schema from the existing release-gate runner without creating a second eval source of truth, including `rag_gate_result_hash`, `eval_artifact_hash`, existing `PASS` / `NO-GO` eval decision fields, and safe artifact references.
    - PR-3 adds a release manifest generator and fail-closed validator. Completed by PR #1605.
    - PR-4 proves review-build and production-candidate equivalence by digest/hash checks. Completed by PR #1679.
    - PR-5 integrates focused CI gates for manifest, ML gate result, build-equivalence result, SBOM/provenance references, and `ALLOW` / `BLOCK` decision. Completed by PR #1682.
    - PR-6 wires real production release evidence artifacts into the production tag workflow path, requiring release manifest, RAG gate result, build-equivalence result, and supply-chain identity evidence before production deploy can treat the release-control-plane gate as `ALLOW`. Completed by PR #1688.
    - PR #1692 closes the production gate bypass by preserving the PR-6 real-evidence wiring as the deploy dependency and documenting that missing protected evidence is a release stop, while protected artifact publication/upload automation and App Store Connect execution remain deferred follow-ups.
    - The evidence-publication follow-up added a manual governed workflow that downloads successful `workflow_dispatch` source artifacts for the same git SHA, normalizes them to the canonical `release-control-plane/` layout, validates them with `scripts/ci/check_release_control_plane.py`, and uploads the artifact operators point production CD at. Completed by PR #1699.
    - The source-producer follow-up added governed `workflow_dispatch` producers for `Release Manifest Evidence` and `Build Equivalence Evidence`. Completed by PR #1703.
    - Release-control-plane evidence plumbing is now complete through governed RAG release gates, governed source producers, the governed publisher, and the production CD gate. Broader App Store Connect execution, Fastlane protected upload mutation, final App Store readiness, and protected upload automation remain separate deferred release/App Store work with auditable follow-up criteria recorded above.

<a id="ledger-p1-planning-flow-monetization-wave"></a>
- [ ] P1: Planning-flow monetization wave over the canonical FREE -> PRO -> VIP ladder
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR `#1416` -> PR `#1434` -> PR `#1464` -> PR-TBD-planning-next-best-action-consumers
  - Lane note: current branch `feat/planning-paywall-exposure-ledger`; planned follow-up branch `feat/planning-next-best-action-consumers`
  - Status: 🟡 Active epic. Bootstrap governance opened the wave on `2026-04-13` (`America/New_York`); PR `#1416` merged the general paywall exposure ledger foundation on `2026-04-15`, PR `#1434` merged intervention trigger engine v1 on `2026-04-17`, and PR-2 is now the narrow planning-specific ledger wiring/taxonomy delta.
  - Area: product / growth / monetization / planning flow
  - Finding Type: monetization value-capture orchestration
  - Reason (EN): `origin/main` already closed the backend monetization spine through merged PRs `#1296` (`2026-04-02`), `#1312` (`2026-04-03`), and `#1381` (`2026-04-09`). The next profitable lane is not another receipt/entitlement rewrite; it is deterministic monetization over the planning-first journey `BMI -> targets -> daily plate -> weekly plan -> export/recipe follow-through`. The epic must stay thin-client-safe, additive, and worktree-isolated so billing/provider modernization does not get reopened by accident. (RU: Биллинг-спайн уже закрыт на `main`; следующий шаг — monetization поверх planning flow, а не новый receipt/entitlement PR.)
  - Links:
    - `README.md`
    - `docs/contracts/PRODUCT_TIER_MAP.md`
    - `docs/contracts/PAYMENTS_RU_BY_IOS_BASELINE.md`
    - `docs/orchestration/MONETIZATION_PLANNING_WAVE_PR_SERIES_RUNBOOK.md`
    - `docs/orchestration/MONETIZATION_PLANNING_WAVE_TASK_PACKET_2026-04-13.md`
    - `app/routers/bmi.py`
    - `app/routers/pro.py`
    - `frontend/src/lib/usePremium.ts`
    - `frontend/src/lib/paywallPurchase.ts`
  - DoD:
    - Bootstrap docs PR reconciles stale ledger wording and records the monetization PR train under explicit coordinator-owned governance
    - PR-1 adds backend-owned `next_best_action` hints on canonical BMI / PRO planning surfaces without touching billing, provider verification, or client-side pricing truth
    - PR-2 adds deterministic planning-surface paywall exposure wiring/taxonomy on top of merged ledger foundation PR `#1416`, aligned to `docs/analytics/*` canon
    - PR-3 consumes backend `next_best_action` hints on web/iOS while preserving fail-closed web checkout semantics
    - Every PR in the wave runs from a fresh `worktree`, merges only after current-head merge-readiness passes, then fast-forward syncs local `main` before the next PR starts
    - Follow-up surfaces (`paywall-copy-alignment`, CBT premium packaging, business-wave follow-through) remain explicitly deferred until after PR-3

<a id="ledger-p1-fonttools-private-index-bump"></a>
- [ ] P1: Recheck fonttools >=4.62.0 after private Python index mirrors fixed wheels
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (supply-chain / CVE debt; mirrors `docs/security/` waiver discipline)
  - Target PR: TBD (land when `PULSEPLATE_PYTHON_INDEX_URL` resolves `fonttools>=4.62.0` with locked install + Docker)
  - Area: security / CI / dependencies
  - Reason (EN): Public PyPI ships patched `fonttools`; the approved private index currently exposes only `4.61.1`, so pins stay unchanged until the mirror syncs. The former Safety policy ignore was removed when Safety was retired from CI dependency auditing; keep this item as the mirror-sync recheck record. (RU: зеркало пакетов отстаёт от PyPI — после появления колеса >=4.62.0 поднять пин; Safety policy больше не активная поверхность.)
  - Links:
    - `docs/security/FONTTOOLS_TTX_EVAL_ADVISORY.md:1`
    - `requirements.txt:57`
    - `scripts/ci/install_locked_python_requirements.py:277`
  - DoD:
    - `requirements.txt`, `requirements-ci-lite.txt`, `requirements-lock.txt` pin `fonttools>=4.62.0` (or exact fixed version available on the private index)
    - `pip-audit` and Dependabot alert state do not report an active fonttools finding
    - Locked install + Docker production target succeed against the private index; `make verify` green
    - Advisory updated (remove-by closed or docs-only follow-up per backlog policy)

<a id="ledger-p1-pytorch-jit-cve-2025-3000-vector-profile"></a>
- [x] P1: Retire PyTorch TorchScript CVE-2025-3000 pip-audit waiver for optional vector profile
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (supply-chain / optional RAG-vector profile)
  - Target PR: this PR (`codex/replace-torch-vector-backend`)
  - Area: security / CI / dependencies / RAG-vector
  - Reason (EN): Recheck on 2026-06-24 found GitHub Advisory
    `GHSA-rrmf-rvhw-rf47` and `pip-audit` / OSV still marking
    `torch <=2.12.0` as affected by `CVE-2025-3000`, with no patched torch
    release listed in advisory metadata. This PR resolves the repo-owned
    optional RAG/vector surface by replacing the PyTorch/SentenceTransformers
    backend with FastEmbed/ONNX and removing the `CVE-2025-3000` pip-audit
    waiver. This is resolved by removal. `requirements.txt`,
    `requirements-ci-lite.txt`, `requirements-docker-runtime.txt`,
    `requirements-lock.txt`, `requirements-rag-vector.txt`, and
    `requirements-rag-vector-cpu.txt` now have no direct `torch` pin. Remaining
    GitHub Dependabot alert closure waits for dependency graph refresh after
    merge.
  - Links:
    - `docs/security/PYTORCH_JIT_CVE_2025_3000_ADVISORY.md:1`
    - `scripts/ci_pip_audit.sh`
    - `requirements-rag-vector.txt`
    - `requirements-rag-vector-cpu.txt`
    - `requirements-ci-lite.txt`: no direct `torch` pin
  - DoD:
    - [x] Replace the optional vector backend with FastEmbed/ONNX.
    - [x] Remove `torch`, `sentence-transformers`, `transformers`, the PyTorch
      index, and the `CVE-2025-3000` waiver from tracked optional vector
      manifests/audit helpers.
    - [x] Keep vector retrieval fail-closed until stored embeddings are rebuilt
      or reset for `BAAI/bge-base-en-v1.5`.
    - [x] Update advisory and Dependabot inventory; GitHub alert state refresh
      remains post-merge external evidence.

<a id="ledger-p1-msgpack-ci-lite-alert-recheck"></a>
- [ ] P1: Recheck msgpack Dependabot alert #225 after dev/full-lock remediation
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (supply-chain / dependency-graph reconciliation)
  - Target PR: PR-TBD after PR #2008 current-head dependency graph refresh
  - Area: security / CI / dependencies
  - Reason (EN): Live Dependabot alert `#225` reports `msgpack`
    `GHSA-6v7p-g79w-8964` against `requirements-ci-lite.txt` as a transitive
    runtime dependency, but current repo manifests show no direct
    `cachecontrol` or `msgpack` entry in `requirements-ci-lite.in` or
    `requirements-ci-lite.txt`. PR #2008 remediates the repo-owned vulnerable
    pins in `requirements-dev.txt` and `requirements-lock.txt` and deliberately
    avoids adding unused packages to `ci-lite` without a reproducible dependency
    path.
  - Links:
    - `docs/security/GHSA-6v7p-g79w-8964-msgpack.md`
    - `requirements-ci-lite.in`
    - `requirements-ci-lite.txt`
    - `requirements-dev.txt`
    - `requirements-lock.txt`
  - DoD:
    - Recheck Dependabot alert `#225` after PR #2008 merges and GitHub refreshes
      dependency graph state.
    - If the alert closes, record the closure evidence and mark this item
      complete.
    - If the alert remains open, prove the actual repo-owned `ci-lite`
      dependency path before editing `requirements-ci-lite.in` or
      `requirements-ci-lite.txt`.

<a id="ledger-p1-python-dependency-surface-contract"></a>
- [ ] P1: Add Python dependency surface contract and retire stale requirements guidance
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (supply-chain / dependency architecture)
  - Target PR: PR #2023
  - Status: In progress in PR #2023 as the Python dependency surface contract
    and security-floor preservation lane.
  - Area: security / CI / dependencies / docs
  - Reason (EN): The operator-linked requirements cleanup epic identifies a
    broader architecture debt train: every dependency profile needs an explicit
    owner, runtime authority, import surface, security scan coverage, optional
    profile boundary, Docker inclusion rule, and validation gate. PR #2008 only
    remediates `msgpack` and records the current alert boundary; it does not
    retire `requirements-all.txt`, replace `verify_requirements.py`, create new
    eval/data profiles, or migrate to pyproject/uv metadata.
  - Links:
    - `docs/DEPENDENCY_MANAGEMENT.md`
    - `requirements-all.txt`
    - `requirements-lock.txt`
    - `requirements-evals.in`
    - `requirements-data.in`
    - `verify_requirements.py`
    - `docs/contracts/PYTHON_DEPENDENCY_SURFACES.md`
    - `scripts/ci/check_python_dependency_surfaces.py`
  - DoD:
    - Document each Python dependency profile owner, purpose, install authority,
      and scan coverage in a canonical dependency-surface contract.
    - Reconcile `REQUIREMENTS.md` / `docs/DEPENDENCY_MANAGEMENT.md` drift and
      live `.github/dependabot.yml` cadence.
    - Decide and document whether `requirements-all.txt` and
      `requirements-lock.txt` are canonical, deprecated, or renamed.
    - Replace or wrap `verify_requirements.py` with a validator that understands
      all active profiles.
    - Keep eval/data profile locking, pyproject/uv migration, and broad package
      cleanup as separately scoped follow-up work unless the contract PR
      explicitly owns them.

<a id="ledger-p1-restore-ragas-companion-safe-deps"></a>
- [ ] P1: Restore native RAGAS companion after safe dependency path exists
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (eval tooling / dependency security)
  - Target PR: TBD after RAGAS / DiskCache advisories expose a patched path or
    after the companion runner migrates to a replacement eval stack
  - Area: evals / RAG release gates companion / dependency security
  - Reason (EN): The consolidated dependency-security lane disables tracked
    `ragas`, `datasets`, and transitive `diskcache` eval dependencies because
    `GHSA-95ww-475f-pr4f` and `GHSA-w8v5-vhqr-4h9v` have no patched dependency
    path. The local RAGAS runner remains importable and report-only, but native
    RAGAS execution must stay disabled until the dependency path is safe.
  - Links:
    - `requirements-evals.in`
    - `requirements-evals.txt`
    - `docs/evals/RAGAS_SETUP.md`
    - `evals/AGENTS.md`
  - DoD:
    - Re-check RAGAS, DiskCache, GitHub Advisory Database, OSV, and the approved
      private Python index for patched-version truth before reintroducing pins.
    - Either restore native RAGAS with safe locked dependencies and focused
      runner tests, or migrate the companion runner to a replacement eval stack
      without changing production runtime behavior.
    - Keep `evals/` offline-only and subordinate to
      `docs/evals/PULSEPLATE_RAG_RELEASE_GATES.md`.

<a id="ledger-p1-cryptography-private-index-sync"></a>
- [x] P1: Retire runtime-effective emergency wheel manifest entries after approved mirror sync
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (security / supply-chain / CI blocker)
  - Target PR: PR #2046 (`codex/retire-emergency-wheel-fallbacks`)
  - Status: Runtime-effective fallback retired in this PR; `scripts/ci/emergency_python_wheels.json` remains as an empty compatibility marker instead of deleting CI/Docker references in the same lane.
  - Area: security / CI / dependencies
  - Reason (EN): The repo carried a time-boxed exact-wheel emergency bridge while the approved private Python proxy caught up to patched locked releases. After PR #2036 and the 2026-06-29 mirror-parity proof, representative proxy health was `ok=true` and all 34 previously active emergency wheel filenames were present on the approved private proxy (`missing=0`). The broad cleanup path remains intentionally out of scope: the manifest file stays as an empty retired marker so rollback-compatible installer, CI, and Docker references do not churn in this infra PR. (RU: репозиторий временно держал exact-wheel emergency bridge, пока одобренный приватный Python proxy догонял исправленные lockfile-релизы. После PR #2036 и mirror-parity proof от 2026-06-29 representative health был `ok=true`, и все 34 ранее активных emergency wheel filename присутствовали в одобренном приватном proxy (`missing=0`). Широкое удаление compatibility path оставлено вне scope: manifest остаётся пустым retired marker, чтобы не смешивать rollback-compatible installer/CI/Docker references с этим infra PR.)
  - Links:
    - `docs/security/SFTY-20260615-python-runtime-floors.md:1`
    - `docs/security/CRYPTOGRAPHY_46_0_7_PRIVATE_INDEX_ADVISORY.md:1`
    - `docs/security/GHSA-whj4-6x5x-4v2j-pillow.md:1`
    - `scripts/ci/emergency_python_wheels.json`
    - `scripts/ci/install_locked_python_requirements.py`
    - `.github/actions/python-setup/action.yml`
    - `Dockerfile`
  - Evidence:
    - `scripts/ci/check_emergency_wheel_mirror_parity.py` validates every active manifest entry by exact wheel filename against the approved private proxy project pages, and treats the retired empty marker as `retired=true`.
    - `scripts/ci/emergency_python_wheels.json` now has `schema_version: 1`, `generated_at: 2026-06-29`, a retired reason, and `artifacts: []`.
    - `scripts/ci/install_locked_python_requirements.py` still preserves the compatibility path, but `load_emergency_wheel_manifest` returns `[]` for the retired marker so no emergency wheel is runtime-effective.
  - DoD:
    - [x] Approved private proxy served every previously active `scripts/ci/emergency_python_wheels.json` entry during the 2026-06-29 all-entry parity proof
    - [x] Runtime-effective emergency fallback is retired by replacing the manifest with an empty compatibility marker
    - [x] CI has a fail-closed all-entry parity step next to the representative private-proxy health gate
    - [ ] Full removal of the manifest compatibility path and any advisory cleanups are separate follow-up scope

<a id="ledger-p1-pillow-private-index-sync"></a>
- [x] P1: Remove temporary `pillow 12.2.0` emergency wheel fallback after approved mirror sync
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (security / supply-chain / CI blocker)
  - Target PR: PR #2046 (`codex/retire-emergency-wheel-fallbacks`)
  - Status: Runtime-effective fallback retired by the empty emergency manifest marker on `2026-06-29`; advisory cleanup remains separate follow-up scope if needed.
  - Area: security / CI / dependencies
  - Reason (EN): `feat/rag-hardening-followthrough` must stay on the patched exact release `pillow 12.2.0`, but current-head CI and Docker installs showed the approved private index lagged that upstream release and exposed only `12.1.1`. `PR #1415` therefore adds a time-boxed exact-wheel fallback with pinned `sha256` digests instead of a vulnerable repin or a broad public-index bypass. Remove this fallback as soon as the approved mirror serves `12.2.0` natively. (RU: ветка должна остаться на исправленном точном релизе `pillow 12.2.0`, но CI/Docker показали отставание приватного зеркала и наличие только `12.1.1`. Поэтому `PR #1415` добавляет временный exact-wheel fallback с pinned `sha256`, а не уязвимый репин и не широкий bypass на публичный индекс. Удалить fallback сразу после того, как одобренное зеркало начнёт отдавать `12.2.0` нативно.)
  - Links:
    - `docs/security/PILLOW_12_2_0_PRIVATE_INDEX_ADVISORY.md:1`
    - `scripts/ci/emergency_python_wheels.json`
    - `scripts/ci/install_locked_python_requirements.py`
    - `.github/actions/python-setup/action.yml`
    - `Dockerfile`
  - DoD:
    - [x] Approved private proxy serves `pillow 12.2.0` without a runtime-effective emergency fallback
    - [x] `scripts/ci/emergency_python_wheels.json` no longer carries `pillow 12.2.0` emergency entries
    - [ ] Full compatibility-path removal and advisory cleanup are separate follow-up scope

<a id="ledger-p1-mako-private-index-sync"></a>
- [x] P1: Remove temporary `mako 1.3.12` emergency wheel fallback after approved mirror sync
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (security / supply-chain / CI blocker)
  - Target PR: PR #2046 (`codex/retire-emergency-wheel-fallbacks`)
  - Status: Runtime-effective fallback retired by the empty emergency manifest marker on `2026-06-29`; advisory cleanup remains separate follow-up scope if needed.
  - Area: security / CI / dependencies
  - Reason (EN): `fix/mako-security-floor` started on the patched exact release `mako 1.3.11`, but current-head CI showed the approved private index still exposed only `1.3.10` during locked binary installs. `PR #1440` therefore added a time-boxed exact-wheel fallback with pinned `sha256` digests instead of a vulnerable repin or a broad public-index bypass. `PR #1697` refreshes the active floor to `mako 1.3.12` after a newer `pip-audit` advisory. Remove this fallback as soon as the approved mirror serves `1.3.12` natively. (RU: ветка `fix/mako-security-floor` стартовала с исправленного релиза `mako 1.3.11`, но current-head CI показал, что приватное зеркало всё ещё отдаёт только `1.3.10` при locked binary install. Поэтому `PR #1440` добавил временный exact-wheel fallback с pinned `sha256`, а не уязвимый репин и не широкий bypass на публичный индекс. `PR #1697` обновляет активный floor до `mako 1.3.12` после нового `pip-audit` advisory. Удалить fallback сразу после того, как одобренное зеркало начнёт отдавать `1.3.12` нативно.)
  - Links:
    - `docs/security/MAKO_1_3_11_PRIVATE_INDEX_ADVISORY.md:1`
    - `docs/security/GHSA-v92g-xgxw-vvmm-mako.md:1`
    - `scripts/ci/emergency_python_wheels.json`
    - `scripts/ci/install_locked_python_requirements.py`
    - `.github/actions/python-setup/action.yml:70`
    - `Dockerfile:74`
  - Evidence:
    - `docs/security/GHSA-v92g-xgxw-vvmm-mako.md:5-27` maps `GHSA-v92g-xgxw-vvmm`
      to `Mako` and records `1.3.11` as the first patched version across the
      repo-managed dependency surfaces.
    - `docs/security/MAKO_1_3_11_PRIVATE_INDEX_ADVISORY.md:44-48` records the
      current-head CI/private-proxy lag that still exposed only `1.3.10` during
      locked installs on `17 April 2026`.
    - `scripts/ci/emergency_python_wheels.json` is now an empty retired marker,
      so no `mako 1.3.12` emergency entry remains runtime-effective.
  - DoD:
    - [x] Approved private proxy serves `mako 1.3.12` without a runtime-effective emergency fallback
    - [x] `scripts/ci/emergency_python_wheels.json` no longer carries a `mako 1.3.12` emergency entry
    - [ ] Full compatibility-path removal and advisory cleanup are separate follow-up scope

<a id="ledger-p1-metatron-offensive-lab-out-of-band"></a>
- [ ] P1: METATRON-class offensive lab — out-of-band governance and operator runbook
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (security engineering / abuse prevention)
  - Target PR: Epic 1 merged [#1355](https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1355); Epic 2 — [#1366](https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1366) (isolated runner; branch `feat/metatron-track-a-epic2-runner`); Epic 3 — PR-TBD (runbook). Epic 2 packet: `docs/orchestration/METATRON_TRACK_A_EPIC2_TASK_PACKET_2026-04-06.md:1`.
  - Status: **Track A Epic 1 — CLOSED.** Landed via PR [#1355](https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1355); canonical squash merge commit [`5a39c2ec3`](https://github.com/Katsiarynakavaleuskaya/PulsePlate/commit/5a39c2ec3) on `main`. Remaining: Epic 2 (infra/scripts isolated runner), Epic 3 (runbook) per coordinator sequencing after this ledger closeout.
  - Area: security / deploy / orchestration / governance
  - Reason (EN): METATRON-like stacks (local LLM + offensive recon) must not enter the PulsePlate product runtime or OpenAPI; operators still need canonical RoE, ADR, isolated deploy boundary, and coordinator-led assessment workflow. (RU: оффенсив-лаборатория остаётся вне продукта, но процесс и документы должны быть в репозитории.)
  - Links:
    - `docs/orchestration/METATRON_TRACK_A_EPIC1_TASK_PACKET_2026-04-06.md:1`
    - `docs/orchestration/METATRON_TRACK_A_EPIC2_TASK_PACKET_2026-04-06.md:1`
    - `docs/architecture/ADR_METATRON_OFFENSIVE_LAB_OUT_OF_BAND_2026-04-06.md:1`
    - `docs/security/METATRON_LAB_RULES_OF_ENGAGEMENT.md:1`
    - `docs/orchestration/METATRON_SECURITY_ASSESSMENT_WAVE_RUNBOOK.md:1`
    - `deploy/metatron-lab/README.md:1`
    - Epic 1 merge evidence: [`5a39c2ec3`](https://github.com/Katsiarynakavaleuskaya/PulsePlate/commit/5a39c2ec3) (PR [#1355](https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1355))
  - DoD:
    - [x] Epic 1: ADR + RoE + task packet + lab stub merged with evidence anchors (#1355 / `5a39c2ec3`)
    - [x] Ledger links this packet; Epic 1 merge recorded
    - [x] No offensive tooling in `app.main` / product requirements; lab remains optional compose profile
    - [ ] Epic 2: isolated runner (infra/scripts only); merge-ready with `make verify` on touched surfaces per `AGENTS.md`
    - [ ] Epic 3: operator assessment runbook / wave workflow hardening as needed

<a id="ledger-p1-execution-doc-sot-reconciliation"></a>
- [ ] P1: Execution-doc source-of-truth reconciliation after PR-1
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-TBD (fix/deploy-spa-routing-web-shell)
  - Area: docs / deploy / roadmap
  - Reason: PR-1 intentionally kept the PR-2 deploy diagnosis packet out of scope, but `docs/roadmap/PulsePlate_P0_P1_Execution_Document_2026-03-30.md` still references source-of-truth documents that are missing or in transition. Reconcile the source-of-truth order in the PR-2 deploy shell lane instead of widening the Postgres foundation PR.
  - Links:
    - `docs/roadmap/PulsePlate_P0_P1_Execution_Document_2026-03-30.md`
    - `docs/roadmap/DEPLOY_WEB_DIAGNOSIS_AND_FIX.md`
    - `docs/roadmap/BACKLOG_LEDGER.md`
  - DoD:
    - The execution document source-of-truth list references only in-repo canonical artifacts
    - `DEPLOY_WEB_DIAGNOSIS_AND_FIX.md` has a settled canonical location and is tracked in git
    - Any remaining missing source-of-truth docs are either created or removed from the ordered list with rationale

<a id="ledger-p1-ci-install-profile-split-after-disk-unblock"></a>
- [x] P1: CI install profile split after disk-regression unblock
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR #1599 (`codex/ci-install-profile-split-after-fast-feedback`)
  - Area: CI / Python dependencies / supply-chain
  - Status note: Closed by governance closeout after `fix/ci-feature-fast-feedback`
    landed as PR #1573. The representative feature/fix push evidence recorded in
    `docs/review/PR_1599_FIXED_MAPPING.md` stayed inside the current feedback
    budget, so the post-#1573 re-evaluation did not justify a new heavy
    install-profile implementation slice. Generic CI lanes already use
    `ci-lite` / `ci-test`, optional vector/ML runtime dependencies remain
    isolated in `requirements-rag-vector.txt`, and production Docker targets use
    `requirements-docker-runtime.txt`.
  - Reason: The emergency unblock and follow-up CI stabilization work removed
    duplicate Python installs, forced `direct-proxy` in canonical CI lanes, and
    promoted explicit install profiles. This closeout records the live baseline:
    generic CI feedback no longer installs the heavy vector/ML stack, while
    optional RAG/vector runtime dependencies stay behind the explicit
    `rag-vector` profile instead of the default CI surface.
  - Links:
    - `.github/actions/python-setup/action.yml`
    - `.github/workflows/ci.yml`
    - `requirements.txt`
    - `requirements-ci-lite.txt`
    - `requirements-dev.txt`
    - `requirements-test.txt`
    - `requirements-rag-vector.txt`
    - `requirements-docker-runtime.txt`
    - `scripts/ci/install_locked_python_requirements.py`
    - `docs/DEPENDENCY_MANAGEMENT.md`
    - `docs/roadmap/BACKLOG_LEDGER.md`
  - Evidence:
    - PR #1573 (`fix/ci-feature-fast-feedback`) merged at `c44e2d0b`.
    - `docs/review/PR_1599_FIXED_MAPPING.md` records the representative
      feature/fix push run, head SHA, timing, and current warning budget used
      for this closeout decision.
    - `.github/workflows/ci.yml` uses `requirements-profile: ci-lite` for
      lint/security/OpenAPI/diff-coverage control-plane jobs and
      `requirements-profile: ci-test` for `test-pr`, `test-feature`, and
      `test-main`.
    - `tests/test_python_supply_chain_controls.py` covers the split CI,
      runtime, Docker runtime, and optional RAG/vector dependency surfaces.
    - `tests/test_install_locked_python_requirements.py` covers explicit
      `ci-lite`, `ci-test`, and `rag-vector` profile resolution and fail-closed
      missing-file behavior.
    - `tests/test_ci_workflow_pr_size_governance_contract.py` covers the
      feature/fix fast-feedback evidence artifact and warning-only budget
      contract.
  - DoD:
    - Canonical CI install profiles distinguish runtime, test/dev tooling, and OpenAPI-only tooling
    - Heavy ML/GPU dependencies are optionalized away from generic CI lanes unless a job explicitly needs them
    - Supply-chain guardrails remain fail-closed with the approved private proxy contract intact
    - Deterministic tests cover the promoted install-profile contract

<a id="ledger-p1-safety-audit-shared-script-after-pr1479"></a>
- [x] P1: Shared dependency audit script after install-profile split
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR #1515 (`codex/shared-safety-audit-script`)
  - Area: CI / security workflow / supply-chain
  - Status note: Merged via `PR #1515`; superseded on 2026-06-24 by the
    no-legacy Safety retirement lane, which moves blocking dependency audit to
    `scripts/ci_pip_audit.sh` and removes the Safety helper/policy/artifacts.
  - Depends on:
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-ci-install-profile-split-after-disk-unblock`
  - Reason: PR #1479 intentionally kept the install-profile split narrow. The
    follow-up first extracted a shared Safety audit helper; the 2026-06-24
    no-legacy remediation superseded that implementation with the shared
    `pip-audit` helper after Safety reintroduced vulnerable transitive `nltk`.
  - Links:
    - `.github/workflows/ci.yml`
    - `.github/workflows/security.yml`
    - `scripts/ci/`
    - `docs/review/PR_1479_FIXED_MAPPING.md`
  - Evidence:
    - `.github/workflows/ci.yml:440-485`
    - `.github/workflows/security.yml:120-167`
    - `scripts/ci_pip_audit.sh`
  - DoD:
    - Canonical multi-manifest dependency audit invocation and report generation
      live in one shared script.
    - `ci.yml`, `security.yml`, and nightly security checks delegate to the shared
      helper instead of duplicating audit loops.
    - Deterministic tests cover per-manifest artifact naming, fail-closed
      execution, and the scoped optional-RAG torch waiver.

<a id="ledger-p1-docker-deploy-contract-reconciliation"></a>
- [x] P1: Docker deploy contract reconciliation after install-profile split
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR #1571 (`codex/docker-deploy-contract-reconciliation-pr2`)
  - Area: deploy / docker / operator workflow
  - Status: Implemented in this PR
  - Depends on:
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-ci-install-profile-split-after-disk-unblock`
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-compose-v2-migration`
  - Reason: The canonical production shape is already split, but deploy/operator docs and some workflow assumptions still carried older shared-artifact language and insufficiently constrained manual shell-sync wording. This PR reconciles the live split contract without widening topology scope or reintroducing monolithic image assumptions: backend image updates remain `IMAGE_REF`-driven, the frontend/Caddy shell stays a separate `frontend/Dockerfile.caddy-spa` build, and manual `frontend/` sync is explicitly limited to production CD, CI-produced release bundles, or merged canonical checkout recovery. The install-profile dependency is satisfied here only for the deploy/operator contract surface; any remaining CI install-profile migration steps stay owned by their original ledger item.
  - Links:
    - `docs/orchestration/DOCKER_CI_DISCIPLINE_PR_SERIES_PACKET_2026-04-16.md`
    - `docs/roadmap/DEPLOY_WEB_DIAGNOSIS_AND_FIX.md`
    - `deploy/docker-compose.production.yaml`
    - `deploy/docker-compose.production.selfhosted.yaml`
    - `deploy/docker-compose.staging.yaml`
    - `deploy/WORKFLOW.md`
    - `docs/deploy/PRODUCTION.md`
  - DoD:
    - Deploy docs and compose files agree on split backend image + separate frontend/Caddy topology
    - Stale shared-volume or copy-into-backend assumptions are removed from touched docs and workflow notes
    - Operator rebuild / diagnose-web / `IMAGE_REF` flows match the live contract
    - `docker compose` v2 wording is canonical on touched surfaces

<a id="ledger-p1-pr-scoped-validation-contract-and-hook-fix"></a>
- [ ] P1: PR-scoped validation contract and pre-push hook fix
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR #1516 (`codex/main-ci-py313-timeout-prevention`)
  - Area: CI / tooling / governance
  - Status note: Active follow-up in `codex/main-ci-py313-timeout-prevention` narrows this item to the machine-heavy agent-local execution contract. Full local `make verify` stays canonical for normal PRs, while operator-approved CI/tooling lanes may document deferral and use narrow local gates plus canonical current-head CI parity as the heavy signal. The pre-push hook bug remains tracked here for a separate follow-up and is not closed by the Python 3.13 timeout-prevention lane.
  - Reason: The current repo-wide `make verify` loop is too broad for day-to-day PR iteration, while `scripts/run-backend-tests-pre-commit.sh` has surfaced a `FOUND_FOR_FILE[@]: unbound variable` failure on merge-commit paths. The follow-up must tighten the local PR-scoped validation contract around `make validate-changed` or an equivalent touched-scope path without weakening the canonical merge-readiness requirement.
  - Evidence:
    - `AGENTS.md:5-8`
    - `AGENTS.md:27-30`
    - `RUNBOOK_AGENT.md:377-383`
    - `RUNBOOK_AGENT.md:600-603`
    - `Makefile:130-134`
    - `Makefile:175-175`
    - `scripts/run-backend-tests-pre-commit.sh:174-204`
  - Links:
    - `AGENTS.md`
    - `RUNBOOK_AGENT.md`
    - `Makefile`
    - `.pre-commit-config.yaml`
    - `scripts/run-backend-tests-pre-commit.sh`
  - DoD:
    - Repo docs distinguish normal full local `make verify` from the operator-approved machine-heavy deferral path
    - Agent/runbook guidance points at the correct narrow validation path for machine-heavy PR iteration
    - Deterministic tests cover the promoted validation contract
    - Follow-up PR fixes the pre-push backend test hook failure shape (`FOUND_FOR_FILE[@]: unbound variable`)

<a id="ledger-p1-docker-runtime-slimming-after-profile-split"></a>
- [x] P1: Docker runtime slimming after CI install-profile split
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR #1490 (`fix(docker): slim runtime after profile split`)
  - Area: docker / runtime / supply-chain
  - Status note: Merged on April 22, 2026 via `PR #1490`. Production-target Docker builds now use `requirements-docker-runtime.txt`; telemetry baseline ([Docker image budget and telemetry baseline](#ledger-p1-docker-image-budget-telemetry); DoD: measured baseline artifact and docs), hard-budget follow-up ([Docker image hard budget gate after telemetry baseline](#ledger-p1-docker-image-hard-budget-gate); DoD: fail-closed budget gate), signed provenance restoration, and [Shared Safety audit extraction](#ledger-p1-safety-audit-shared-script-after-pr1479) have since landed. The next active Docker/CI slice is [Docker workflow build-path consolidation and loaded-image smoke reuse](#ledger-p1-docker-workflow-build-path-consolidation).
  - Depends on:
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-ci-install-profile-split-after-disk-unblock`
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-docker-deploy-contract-reconciliation`
  - Reason: Runtime slimming should happen only after the install-profile contract is stable and deploy topology drift is reconciled. The follow-up must remove residual builder/runtime waste without touching provenance policy or the split backend/frontend shell.
  - Links:
    - `docs/orchestration/DOCKER_CI_DISCIPLINE_PR_SERIES_PACKET_2026-04-16.md`
    - `Dockerfile`
    - `requirements-docker-runtime.in`
    - `requirements-docker-runtime.txt`
    - `frontend/Dockerfile.caddy-spa`
    - `.dockerignore`
    - `frontend/.dockerignore`
  - DoD:
    - No builder-only tooling leaks into runtime images
    - Production-target Docker workflows use `requirements-docker-runtime.txt` instead of `requirements-ci-lite.txt`
    - Docker `COPY` scope stays narrow and does not widen build context
    - Production backend build still serves `app.main:app`
    - Supply-chain guardrails and proxy install contract remain intact

<a id="ledger-p1-docker-image-budget-telemetry"></a>
- [x] P1: Docker image budget and telemetry baseline
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR #1492
  - Area: CI / docker / telemetry
  - Status note: Merged on April 22, 2026 via `PR #1492`. The lane established one canonical backend-image baseline, prefers the latest successful `main` artifact, falls back to a checked-in seed baseline, and kept delta reporting warning-only.
  - Depends on:
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-ci-install-profile-split-after-disk-unblock`
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-docker-deploy-contract-reconciliation`
  - Reason: The project needs deterministic PR-facing evidence for image size regressions, largest layers, build-context drift, and baseline provenance before discussing provenance recovery sequencing or any Dagger pilot. Start with warning/regression-only reporting, not an absolute hard stop.
  - Links:
    - `docs/orchestration/DOCKER_CI_DISCIPLINE_PR_SERIES_PACKET_2026-04-16.md`
    - `docs/orchestration/DOCKER_IMAGE_BUDGET_TELEMETRY_TASK_PACKET_2026-04-22.md`
    - `.github/workflows/build.yml`
    - `.github/workflows/docker-image.yml`
    - `.github/workflows/trivy.yml`
    - `docs/telemetry/docker_image_baseline.production.json`
    - `docs/architecture/ADR_DOCKER_BUILD_PROVENANCE_WORKAROUND_2026-03-01.md`
  - DoD:
    - CI emits deterministic image-size evidence for touched Docker lanes
    - Largest-layer and build-context summaries are visible to PR authors before merge
    - Baseline source is explicit (`main-artifact` or `repo-seed-fallback`)
    - The first gate is warning/regression-only, not an absolute size cap
    - Follow-up provenance or Dagger decisions can cite this baseline explicitly

<a id="ledger-p1-docker-image-hard-budget-gate"></a>
- [x] P1: Docker image hard budget gate after telemetry baseline
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR #1498
  - Area: CI / docker / telemetry
  - Status note: Merged on April 22, 2026 via `PR #1498`. The lane promotes the production backend image from warning-only telemetry to a deterministic hybrid hard gate with an absolute cap and a maximum positive delta vs baseline.
  - Depends on:
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-docker-image-budget-telemetry`
  - Reason: The repo should not enforce a hard image-size failure threshold until the warning-only baseline has stabilized on `main` and the canonical telemetry evidence is trustworthy enough to gate merges deterministically.
  - Links:
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-docker-image-budget-telemetry`
    - `docs/orchestration/DOCKER_IMAGE_HARD_BUDGET_GATE_TASK_PACKET_2026-04-22.md`
    - `.github/workflows/build.yml`
    - `.github/workflows/docker-image.yml`
    - `.github/workflows/trivy.yml`
    - `docs/telemetry/docker_image_budget.production.json`
  - DoD:
    - A canonical hard-fail threshold exists for the production backend image
    - Docker lanes fail deterministically when the threshold regresses beyond policy
    - The gate uses the same canonical telemetry artifact contract introduced by PR `#1492`

<a id="ledger-p1-business-wave-runtime-follow-through"></a>
- [ ] P1: Business wave runtime follow-through after governance/docs foundation
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-TBD-BUSINESS-WAVE-RUNTIME-FOLLOW-THROUGH
  - Area: business / runtime / governance carryover
  - Reason: The governance-first business wave intentionally avoids mutating `app/routers/business.py` and `core/business_bayesian_analyzer.py` in the first pass. A dedicated follow-up PR must audit runtime completeness, contract posture, any promotion from internal analyzer surfaces to broader business workflows, and any executive document layer that duplicates facts already owned by `docs/audience_pack/*`.
  - Links:
    - `docs/orchestration/BUSINESS_WAVE_PR_SERIES_RUNBOOK.md`
    - `docs/orchestration/BUSINESS_WAVE_TASK_PACKET_2026-03-21.md`
    - `docs/library/brainstorm/2026-03-21_business-wave-b2b-collateral.md`
    - `docs/audience_pack/README.md`
    - `docs/executive/PR_PORTFOLIO_BRIEF_DIRECTORS_2026-03.md`
    - `app/routers/business.py`
    - `core/business_bayesian_analyzer.py`
  - DoD:
    - Runtime business analyzer completeness is audited against the governance/business-line SoT
    - Any missing runtime/business contracts are either implemented or explicitly deferred with ledger proof
    - No client-side or external-facing business automation path is introduced without reviewed runtime contract evidence
    - Any executive document layer that rephrases `docs/audience_pack/*` is either eliminated, linked back to canon, or explicitly deferred with ledger proof

<a id="ledger-p1-pr1185-cubic-activation-contract"></a>
- [ ] P1: PR #1185 Cubic activation contract refinements (deferred)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-TBD (follow-up after PR #1185)
  - Area: payments / activation / contract
  - Reason: Cubic review comments (6 threads + review) posted after commit 26ec3bd0. Deferred to follow-up PR for activation contract refinements.
  - Links:
    - docs/review/PR_1185_FIXED_MAPPING.md
    - docs/contracts/PAYMENTS_RU_BY_IOS_BASELINE.md
  - DoD: Address Cubic findings in dedicated PR; update mapping artifact.

<a id="ledger-p1-postgres-backup-restore-hardening"></a>
- [ ] P1: Postgres backup/restore operational hardening
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-TBD (infra/p1-postgres-backup-restore-hardening)
  - Area: infra / database / ops
  - Reason: Deferred from PR #1184. Atomic backup write, tmp cleanup on pg_dump failure, restore preflight validation, psql ON_ERROR_STOP, explicit operator confirmation for destructive restore.
  - Links: scripts/ops/postgres_backup.sh, scripts/ops/postgres_restore.sh
  - DoD: Atomic backup; safer restore flow with validation and confirmation.

<a id="ledger-p1-pr1-50-remediation-wave1"></a>
- [ ] P1: PR 1-50 remediation follow-through after Wave 1
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (audit debt / type-safety / test hygiene)
  - Target PR: PR-TBD-PR1-50-REMEDIATION
  - Status: 🟡 In progress
  - Area: frontend / tests / dev-scripts / audit debt
  - Finding Type: audit remediation carryover
  - Reason (EN): PR 1-50 remediation Wave 1 is intentionally scoped to unresolved P0/P1 findings in production code, tests, and dev scripts. Lower-priority cleanup stays deferred so the fix PR remains narrow enough to reach green CI without mixing audit documentation work into the implementation branch.
  - Links:
    - `frontend/src/features/plan/WeeklyPlanViewer.tsx`
    - `frontend/src/features/shoplist/ShoplistPreview.tsx`
    - `tests/test_llm_extras.py`
    - `tests/test_repo_policy_sys_modules.py`
    - `tests/core/catalog/test_sqlite_fk_integrity.py`
    - `tests/test_api.py`
    - `run_coverage_tests.py`
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p2-pr1-50-sharefile-hardening`
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p2-pr1-50-glasscard-cleanup`
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p2-pr1-50-ollama-diagnostic-deps`
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p2-pr1-50-ollama-monitor-deps`
  - Deferred / P2 carryover:
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p2-pr1-50-sharefile-hardening`
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p2-pr1-50-glasscard-cleanup`
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p2-pr1-50-ollama-diagnostic-deps`
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p2-pr1-50-ollama-monitor-deps`
  - DoD:
    - Wave 1 fixes all unresolved P0/P1 findings from the PR 1-50 audit
    - Deferred P2 items remain tracked here with explicit file targets
    - `pre-commit run --all-files` and `make verify` pass in PR scope
    - PR body includes a `Deferred / Follow-ups` section with ledger links to this ledger item

<a id="backlog-restore-signed-build-provenance"></a>
- [x] P1: Restore signed build provenance after cache/buildx workaround is removed
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (supply-chain maturity after tooling-surface guard baseline)
  - Target PR: PR #1503
  - Status: Landed via `PR #1503`; provenance/SBOM attestations are restored for pushed-image lanes and verified before deploy. PR #1946 narrowed BuildKit in-action provenance to `mode=min` for private package-index secret-env lanes while preserving GitHub-signed provenance/SBOM verification.
  - Reason (EN): Docker baseline and hard-budget gates are now stable enough to restore signed provenance on pushed-image lanes without widening scope into `load: true` jobs or alternate control planes. This slice must re-enable provenance/SBOM attestations on registry pushes and fail closed before staging or production deploy if digest verification breaks.
  - Links:
    - `docs/orchestration/DOCKER_SIGNED_BUILD_PROVENANCE_TASK_PACKET_2026-04-23.md`
    - `.github/workflows/build.yml`
    - `.github/workflows/cd.yml`
    - `scripts/ci/check_docker_provenance_attestation.py`
    - `docs/architecture/ADR_DOCKER_BUILD_PROVENANCE_WORKAROUND_2026-03-01.md`
    - `docs/security/TOOLING_SURFACE_POLICY.md`
  - DoD:
    - `build.yml` publish uses a scan-before-push lane: private package-index inputs stay in BuildKit secret envs, the loaded scan build keeps `provenance: false`, then the scanned tags are pushed and attested by exact digest
    - `cd.yml` pushed-image BuildKit lanes use `provenance: mode=min` when private package-index inputs flow through BuildKit secret envs
    - pushed-image lanes emit SBOM attestations alongside provenance
    - publish/CD verifies provenance and SPDX SBOM attestations by exact pushed digest before release-control-plane publication or deploy
    - `load: true` jobs remain on `provenance: false`
    - Follow-up docs and CI checks explicitly cover the restored path

<a id="ledger-p1-docker-workflow-build-path-consolidation"></a>
- [x] P1: Docker workflow build-path consolidation and loaded-image smoke reuse
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR #1526 (`codex/docker-build-path-consolidation`)
  - Area: CI / docker / security scan / operator workflow
  - Status: Landed
  - Depends on:
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-docker-image-hard-budget-gate`
    - `docs/roadmap/BACKLOG_LEDGER.md#backlog-restore-signed-build-provenance`
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-safety-audit-shared-script-after-pr1479`
  - Reason: Landed via `PR #1526` on 2026-04-25. Docker production image work is now functionally correct, and `PR #1526` removed the duplicate `target: production` PR rebuild pattern across `build.yml`, `docker-image.yml`, `trivy.yml`, and `docker-openapi-smoke.yml`. The landed baseline consolidates PR-time runtime/telemetry/budget/OpenAPI smoke validation into `build.yml` and keeps `trivy.yml` outside ordinary PR merge truth as an image-security lane; PR #1935 later promoted that lane to `main`/schedule/manual fail-closed scanning. Baseline/governance closeout is the only remaining action in this PR.
  - Links:
    - `docs/orchestration/DOCKER_WORKFLOW_BUILD_PATH_CONSOLIDATION_TASK_PACKET_2026-04-25.md`
    - `.github/workflows/build.yml`
    - `.github/workflows/trivy.yml`
    - `scripts/ci/docker_image_telemetry.py`
    - `scripts/ci/check_docker_image_budget.py`
  - DoD:
    - One canonical production-image build path owns telemetry, budget evidence, test/local validation, and GHCR publish semantics.
    - Follow-on Docker smoke checks are folded into the produced local image validation path, while the image-security lane stays outside PR-time merge truth as `main`/schedule/manual instead of silently rebuilding divergent PR images.
    - Existing artifact names and hard-budget/provenance evidence stay stable for reviewers and operators.
    - `slim-bookworm`, `.dockerignore`, non-root runtime, healthcheck, and current runtime requirements profile remain unchanged.
    - Dagger, Docker base-image changes, requirements-profile split, and SBOM/VEX maturity work remain out of scope.

<a id="ledger-p1-docker-runtime-slimming-after-build-path-consolidation"></a>
- [x] P1: Docker runtime base-image and API dependency-profile slimming
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR #1530
  - Area: CI / docker / dependency profile / runtime cost
  - Status: Landed
  - Transition note: 2026-04-25 — Opened as immediate follow-up after PR #1526 and build-path consolidation telemetry stabilisation.
  - Depends on:
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-docker-workflow-build-path-consolidation`
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-docker-image-hard-budget-gate`
  - Reason: Landed via `PR #1530` on 2026-04-25. Base-image changes and API-core dependency-profile slimming were intentionally split from `PR #1526` and landed in `PR #1530` after build-path consolidation telemetry stabilized. This closeout PR only updates docs/governance truth. The active Docker/CI next state is baseline/governance closure, not a repeat runtime-slimming implementation slice.
  - Links:
    - `docs/deploy/DOCKER.md`
    - `Dockerfile`
    - `.github/workflows/build.yml`
    - `requirements-docker-runtime.txt`
    - `docs/telemetry/docker_image_budget.production.json`
  - DoD:
    - Consolidated PR #1526 Docker telemetry baseline is available for comparison.
    - Candidate base-image or dependency-profile changes have explicit rollback instructions.
    - Runtime route smoke, OpenAPI contract checks, image budget, and security scan evidence pass on the proposed image.
    - Dependency-profile changes are split from workflow consolidation and do not weaken the pinned install or startup-hook contracts.

<a id="ledger-p1-sbom-vex-signed-security-artifacts"></a>
- [ ] P1: SBOM/VEX signed security artifacts lane after P0 release-truth closure
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (security maturity after release-truth closure)
  - Target PR: PR #1332
  - Status: Blocked
  - Blocked by:
    - release-truth closure criteria listed below
  - Reason (EN): Blocked until P0 release-truth closure. SBOM/VEX/cosign/OPA is a separate security-maturity lane. Provenance is now restored, but the current canonical release risk remains concentrated in release-truth closure. Until entitlement truth, backend/runtime closure, infra hardening, canonical OpenAPI sync, and web/iOS runtime parity are stable, this lane stays docs/governance-only and must not add new blocking CI or merge-path complexity. This closeout PR does not enable CI/control-plane changes for SBOM/VEX.
  - Current action:
    - docs/governance only
    - no CI enablement
    - no blocking workflow or merge-gate changes
  - Entry criteria:
    - Entitlement truth is closed
    - Backend/runtime closure is closed
    - Infra hardening is stable
    - OpenAPI is restored as canonical truth
    - Web/iOS runtime parity is no longer a P0 release blocker
  - Links:
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p0-billing-entitlement-routing`
    - `docs/roadmap/BACKLOG_LEDGER.md#backlog-restore-signed-build-provenance`
    - `docs/security/TOOLING_SURFACE_POLICY.md`
    - `docs/architecture/ADR_DOCKER_BUILD_PROVENANCE_WORKAROUND_2026-03-01.md`
  - DoD:
    - SBOM is generated on every canonical build
    - Vulnerability scan results are stored as canonical artifacts
    - VEX is stored at a fixed canonical path
    - cosign attestations are verified automatically
    - OPA gate evaluates signed VEX exceptions deterministically
    - Rollout is staged `warn-only -> enforced`
    - Nightly reconciliation detects stale VEX entries

<a id="ledger-p1-canonical-bootstrap-late-rehydration"></a>
- [ ] P1: Canonical app bootstrap late-rehydration hardening
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (runtime reliability follow-up after `/metrics` hotfix)
  - Target PR: PR #1101 (`fix(metrics): restore late bootstrap route on main`) -> PR-TBD-CANONICAL-BOOTSTRAP-LATE-REHYDRATION
  - Area: backend / bootstrap / observability
  - Finding Type: import-order follow-up
  - Reason: The `/metrics` hotfix restores late route registration on already-built apps, but it intentionally does not attempt full middleware rehydration after `middleware_stack` exists. A follow-up is needed to define and harden the canonical behavior for late bootstrap/import-order paths without reintroducing unsafe post-start middleware mutation.
  - Links:
    - `docs/review/PR_1101_FIXED_MAPPING.md`
    - `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1101`
    - `app/main.py`
    - `app/bootstrap/metrics.py`
    - `tests/test_metrics.py`
    - `tests/test_no_direct_testclient.py`
  - DoD:
    - Canonical late-bootstrap contract is documented for route vs middleware behavior
    - Tests cover legacy/app-first import order for additive observability surfaces
    - Direct TestClient bypass debt is reduced or explicitly re-audited against the canonical bootstrap contract

<a id="ledger-p1-billing-activation-openapi-refinements"></a>
- [ ] P1: Billing activation OpenAPI refinements after PR #1095
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (contract-first clarity)
  - Target PR: PR-TBD-BILLING-ACTIVATION-OPENAPI-REFINEMENTS
  - Area: backend / frontend / payments / OpenAPI
  - Finding Type: contract refinement follow-up
  - Reason: PR #1095 intentionally keeps the runtime scope narrow around activation + persistence. The follow-up OpenAPI work should explicitly model source-specific activation variants, reuse canonical enums in Apple verify hints, and mark compatibility aliases as deprecated without expanding the current backend runtime PR.
  - Links:
    - `app/schemas/payments.py`
    - `frontend/src/api/openapi.json`
    - `frontend/src/api/schema.ts`
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p0-payments-ruby-ios`
  - DoD:
    - `ActivateSubscriptionRequest` is expressed as a discriminated `oneOf` keyed by `source`
    - Apple verify activation hints reuse canonical `PaymentPlatform`
    - Compatibility aliases in `SubscriptionActivationResponse` are explicitly deprecated in OpenAPI
    - `make openapi-check` passes with regenerated frontend artifacts

<a id="ledger-p1-dsar-direct-user-helper-contract"></a>
- [ ] P1: Internal DSAR direct-user helper contract
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR #1049
  - Area: backend / privacy
  - Finding Type: compliance runtime hardening
  - Reason: The compliance control plane now documents support-led DSAR handling, but the runtime still needs deterministic helper functions that export direct-user SQL artifacts and execute bounded deletion without exposing a public endpoint. This slice keeps DSAR execution consistent for `users`, `rag_feedback`, and `user_knowledge` while keeping account-row deletion on the dedicated existing path.
  - Links:
    - `core/compliance/dsar.py`
    - `core/compliance/dsar_service.py`
    - `docs/compliance/DSAR_AND_DELETION_MAP.md`
    - `docs/legal/Privacy.md`
  - DoD:
    - Internal helper functions export direct-user SQL artifacts in a deterministic, serializable format
    - Internal helper functions delete `rag_feedback` and `user_knowledge` idempotently and report per-artifact counts
    - Internal helper functions expose an explicit deletion plan for the `users` row instead of silently widening into full account deletion
    - No public DSAR endpoint is introduced before an explicit auth/ownership contract exists
    - Deterministic tests cover export + delete paths for `users`, `rag_feedback`, and `user_knowledge`

<a id="ledger-p1-telemetry-maturity-follow-through"></a>
- [ ] P1: Telemetry maturity follow-through for audited vault retrieval and budget dashboards
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (post-foundation observability maturity)
  - Target PR: TBD
  - Status: 📋 Planned
  - Reason (EN): The telemetry foundation PR intentionally stops at lightweight spans plus encrypted pointer storage. Audited decrypt workflow, detector budget dashboards, and retention/DSR operating hooks remain deferred so the first runtime slice stays additive and low-risk.
  - Links:
    - `docs/telemetry/TELEMETRY_POLICY.md`
    - `docs/telemetry/LLM_DETECTORS.md`
    - `docs/telemetry/TELEMETRY_FIELD_CLASSIFICATION.md`
    - `docs/compliance/DSAR_AND_DELETION_MAP.md`
    - `docs/legal/Privacy.md`
    - `deploy/otelcol/collector.yaml`
  - DoD:
    - Audited decrypt workflow exists for approved vault retrieval
    - Dashboards cover span volume, full-capture rate, and detector distribution
    - Retention and deletion hooks for telemetry vault references are documented and test-covered

<a id="ledger-p1-external-food-source-policy-enforcement"></a>
- [ ] P1: External food-source operating policy enforcement follow-through
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (data governance / legal-operating discipline)
  - Target PR: PR-TBD-FOOD-SOURCE-POLICY-ENFORCEMENT
  - Status: Not started
  - Area: backend / legal-compliance / data platform
  - Finding Type: provider operating-policy follow-up
  - Reason: ODbL attribution is canonical for Open Food Facts and the food
    platform strategy already names broader source tiers, but future ingestion
    work still needs one explicit enforcement lane across USDA, Open Food Facts,
    MenuStat-style datasets, and Nutritionix-style commercial providers so
    technically reachable data is not treated as automatically safe to cache or
    redistribute.
  - Links:
    - `docs/legal/EXTERNAL_FOOD_SOURCE_OPERATING_POLICY.md`
    - `docs/legal/ODbL_COMPLIANCE.md`
    - `docs/architecture/FOOD_DATABASE_PLATFORM_STRATEGY_v1.md`
    - `app/routers/pro_food_attribution.py`
  - DoD:
    - New provider onboarding checklist references the operating matrix before
      runtime rollout
    - Provider-specific docs exist whenever stricter rules are needed
    - Attribution registry and docs stay aligned when new public-facing sources
      are added
    - No new external food/menu source ships without explicit cache and
      redistribution decisions

<a id="ledger-p1-token-expansion-activation"></a>
- [ ] P1: Semantic/product token expansion + Tokens Studio activation + optional figma-manifest schema unification
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (design-system governance)
  - Target PR: PR #1047 (`feat(design): add token pipeline foundation`) -> PR-TBD-TOKEN-EXPANSION-ACTIVATION
  - Status: 📋 Deferred after token-pipeline foundation
  - Foundation PR: PR #1047 (2026-03-08, `f272503c`)
  - Area: frontend / ios / design-system
  - Finding Type: governance follow-up
  - Reason: The repo now has a governed `/tokens -> generated runtime mirrors` pipeline for foundation and current semantic tokens. Deferred work remains for broader semantic/product layers (`tier`, `paywall`, `plate`, `bmi`, `coach`), controlled Tokens Studio activation beyond documentation-only support, and an explicit decision on whether `docs/design/figma-manifest.json` should stay informational or be unified with token-pipeline schema validation.
  - Links:
    - [PR #1047](https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1047)
    - `docs/design/TOKENS_SOT.md`
    - `docs/design/TOKEN_PIPELINE_GOVERNANCE.md`
    - `docs/design/figma-manifest.json`
    - `frontend/src/styles/tokens.css`
    - `frontend/src/styles/tokens.ts`
    - `ios/PulsePlate/DesignSystem/DesignTokens.generated.swift`
    - `ios/PulsePlate/DesignSystem/DesignTokens.swift`
    - `docs/runbooks/FIGMA_MCP_DESIGN_SYSTEM_RULES.md`
  - DoD:
    - Semantic and product-token layers are explicitly named and promoted into web/iOS runtime mirrors where needed
    - Tokens Studio activation scope, export format, review gate, and ownership are documented before any runtime automation or commit contract is added
    - If figma-manifest unification is chosen, the schema/version/validation owner is documented; if not chosen, docs explicitly keep it informational
    - Active design-system docs continue to reference one governance path only

<a id="ledger-p1-design-intelligence-wave"></a>
- [ ] P1: Reference-driven design intelligence wave for web and iOS
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (design / web / iOS / agentic workflow / reference corpus)
  - Target PR: PR #1671 (`docs(design): open reference-driven design intelligence wave for web and iOS`, branch `docs/design-intelligence-wave-v1`) -> PR #1677 / PR-1 `feat(design): generate PulsePlate DESIGN.md from token and component contracts` -> PR #1680 / PR-2 `feat(design): add external reference manifest and normalization tooling` -> PR #1683 / PR-3 `feat(design): add screen evidence pack for web and iOS review surfaces` -> PR #1686 / PR-4 `feat(design): add deterministic design scorecard checks` -> PR #1689 / PR-5 acceptance brief `docs/design-web-launch-brief-pr5` -> PR #1694 / PR-6 `feat(ios): add iOS design parity audit and bounded visual sync` -> PR #1695 hotfix interruption -> PR #1698 / PR-7 `feat(orchestration): add design-agent workflow and PR template` -> PR #1704 / PR-8 `docs(research): add GEPA-compatible prompt/rubric evolution lane` -> next-lane decision `docs/design-automation-next-lane-decision-v1`
  - Status: PR-0 merged in PR #1671; PR-1 merged in PR #1677 with generated/drift-checked `docs/design/DESIGN.md`; PR-2 merged in PR #1680 with reference manifest validation and normalization tooling; PR-3 merged in PR #1683 with metadata-only screen evidence pack validation for web and iOS review surfaces; PR-4 merged in PR #1686 with deterministic evidence-quality scorecard checks; PR-5 acceptance brief merged in PR #1689 with the web shell accepted with deferred minor follow-up; PR-6 merged in PR #1694 with iOS visual parity audit and bounded sync decision; PR #1695 landed the BMI guard false-positive hotfix interruption; PR-7 merged in PR #1698 with workflow/template/test governance; PR-8 merged in PR #1704 with GEPA-compatible prompt/rubric evolution kept research/eval/process-only. The active follow-up is the docs-only decision lane `docs/design-automation-next-lane-decision-v1`, which selects the next design automation module without starting implementation.
  - Area: design / web / iOS / agentic workflow / reference corpus
  - Finding Type: reference-driven design intelligence bootstrap and governance
  - Anchor: `ledger-p1-design-intelligence-wave`
  - Reason: Web and iOS design automation needs a governed layer for external
    reference intake, DESIGN.md bootstrap, scoring, Figma/Storybook evidence,
    and controlled future implementation PRs without creating a second design
    source of truth.
  - Links:
    - `docs/orchestration/DESIGN_INTELLIGENCE_WEB_IOS_RUNBOOK.md`
    - `docs/orchestration/DESIGN_INTELLIGENCE_PR0_PACKET_2026-05-05.md`
    - `docs/design/REFERENCE_MANIFEST_SCHEMA.md`
    - `docs/design/REFERENCE_SCORECARD.md`
    - `docs/design/PULSEPLATE_DESIGN_MD_BOOTSTRAP.md`
    - `docs/design/DESIGN.md` (PR-1 generated semantic wrapper; non-canonical)
    - `docs/design/SCREEN_EVIDENCE_PACK_SCHEMA.md` (PR-3 screen evidence metadata schema; non-canonical)
    - `docs/design/DESIGN_SCORECARD_CHECKS.md` (PR-4 deterministic scorecard checks; non-canonical)
  - DoD:
    - PR-0 runbook and packet exist
    - External reference policy exists
    - Reference manifest schema exists
    - Reference scorecard exists
    - DESIGN.md bootstrap exists
    - External references are read-only
    - Future implementation PRs require screenshot / Storybook / a11y evidence
    - AGENTS.md update proposal included
    - No runtime UI mutation in PR-0
    - Premortem risks are converted into binding controls across the runbook,
      packet, schema, scorecard, and DESIGN.md bootstrap
    - PR-7 workflow/template governance is merged and future design-impacting PRs have a repeatable start, evidence, premortem, review-mapping, and merge-readiness path
  - Post-PR-8 next-lane decision tracking:
    - Owner: @katsiaryna_kavaleuskaya
    - Priority: P1
    - Target PR: `docs(design): select next design automation module after PR-8`, branch `docs/design-automation-next-lane-decision-v1`
    - Selected future lane: Icon Asset Validator / App Store asset guard lane
    - Deferred lane entries:
      - `design-automation-deferred-launch-copy-linter`
      - `design-automation-deferred-marketing-asset-pack`
      - `design-automation-deferred-component-drift-expansion`
      - `design-automation-deferred-design-agent-research`
    - Reason: PR-8 intentionally stopped before any automatic implementation lane. The next safe step is a coordinator-owned decision packet that selects the next module while preserving repo truth and requiring a separate future implementation packet.
    - Links: `docs/orchestration/DESIGN_INTELLIGENCE_WEB_IOS_RUNBOOK.md`, `docs/orchestration/DESIGN_AGENT_WORKFLOW.md`, `docs/design/NEXT_DESIGN_AUTOMATION_MODULE_DECISION.md`, `docs/orchestration/DESIGN_AUTOMATION_NEXT_LANE_PACKET_2026-05-08.md`
    - DoD: Decision packet selects the next design automation module, records deferred lanes, defines future implementation boundaries, and keeps runtime, token, generated mirror, Figma, Canva, Storybook, screenshots, and asset implementation out of scope.
  - Design-epic PR-prompt protocol tracking:
    - Owner: @katsiaryna_kavaleuskaya
    - Priority: P1
    - Target PR: `#1710`
    - Reason: Future design-epic PR prompts need a guarded protocol for clean worktree startup, worktree-local Python setup, coordinator-expanded mandatory agents, premortem execution on the actual diff, post-open and post-bot review passes, fixed mapping after fix/decision, and operator-owned post-merge local main synchronization.
    - Links: `docs/orchestration/DESIGN_EPIC_PR_PROMPT_PROTOCOL_2026_05_08.md`, `docs/orchestration/DESIGN_AGENT_WORKFLOW.md`, `docs/orchestration/DESIGN_AGENT_PR_TEMPLATE.md`
    - DoD: Protocol doc exists, workflow/template point future design-epic prompts at it, deterministic docs guards reject stale prompt patterns, and the lane remains docs/tests/governance only without rewriting the merged post-PR-8 next-lane decision.
  - PR-9 design-system automation docs lane tracking:
    - Owner: @katsiaryna_kavaleuskaya
    - Priority: P1
    - Target PR: `docs(design): open PR-9 design system automation lane for web+iOS runtime parity`, branch `codex/design-runtime-pr9-design-system-automation-docs`
    - Reason: The completed PR-0 through PR-8 design runtime train has strong governance, Storybook parity, token discipline, and evidence automation, but future web+iOS implementation needs machine-readable design infrastructure before runtime slices can safely start.
    - Required sequence: component contract registry -> bridge coverage inventory -> visual regression decision gate -> accessibility regression decision gate -> token/runtime parity boundary -> first bounded frontend MVP product slice.
    - Links: `docs/orchestration/DESIGN_RUNTIME_SYSTEM_WEB_IOS_PR9_DESIGN_SYSTEM_AUTOMATION_PACKET_2026-05-08.md`, `docs/design/DESIGN_SYSTEM_AUTOMATION_SPEC.md`, `docs/orchestration/contracts/DESIGN_COMPONENT_CONTRACT_REGISTRY.md`, `docs/orchestration/DESIGN_AGENT_WORKFLOW.md`, `docs/orchestration/DESIGN_AGENT_PR_TEMPLATE.md`
    - DoD: PR-9 packet, design-system automation spec, component contract registry contract, workflow/template pointers, deterministic docs guards, fixed-mapping governance, and any narrow orchestration preflight bugfix discovered by required agents exist; the lane remains governance/tests only and does not implement web runtime, iOS runtime, Storybook config, token mirrors, Figma/Canva/Penpot writes, screenshots, Code Connect activation, backend, OpenAPI, auth, billing, StoreKit, or HealthKit behavior.
  - [ ] P1: Design token/runtime parity boundary:
    - Owner: @katsiaryna_kavaleuskaya
    - Priority: P1
    - Status: active
    - Target PR: `feat/design-token-runtime-parity-boundary` (`feat(design): add token/runtime parity boundary`)
    - Reason: The accessibility regression decision gate must be followed by one final fail-closed token/runtime parity contract before PulsePlate stops accumulating design governance and moves into the first bounded frontend MVP product slice.
    - Links: `docs/orchestration/contracts/design_token_runtime_parity_boundary.v1.json`, `scripts/design/design_token_runtime_parity_boundary.py`, `docs/orchestration/contracts/design_accessibility_regression_decisions.v1.json`, `docs/design/DESIGN_SYSTEM_AUTOMATION_SPEC.md`, `docs/orchestration/contracts/DESIGN_COMPONENT_CONTRACT_REGISTRY.md`
    - Required sequence: registry -> bridge coverage -> visual regression decision -> accessibility regression decision -> token/runtime parity boundary -> first bounded frontend MVP product slice
    - DoD: Machine-readable token/runtime parity boundary exists; validator exists; tests exist; every registry/bridge component is represented exactly once; generated mirrors remain derived runtime evidence and are not token authoring truth; missing visual or accessibility decision evidence keeps implementation readiness `blocked`; frontend implementation is still blocked until this boundary lands; next PR is the first bounded frontend MVP product slice; Slack/Experiment Runner operator bridge remains after MVP observability, not before; no runtime, token value, generated mirror, Storybook, Figma/Canva/Penpot/Kimi, backend, OpenAPI, billing, auth, deploy, screenshot, binary, or iOS implementation change is included.
  - Kimi prototype intake modernization bridge tracking:
    - Owner: @katsiaryna_kavaleuskaya
    - Priority: P1
    - Target PR: `docs(design): add Kimi prototype intake and modernization bridge protocol`, branch `codex/kimi-prototype-intake-modernization-bridge`
    - Reason: The current Kimi prototype provides useful modern product and visual direction, but it must be captured as read-only evidence and normalized through repo-governed tokens, component contracts, visual regression, accessibility regression, and web+iOS parity gates before any implementation slice.
    - Links: `docs/orchestration/KIMI_PROTOTYPE_INTAKE_MODERNIZATION_BRIDGE_PROTOCOL.md`, `docs/orchestration/DESIGN_AGENT_WORKFLOW.md`, `docs/orchestration/DESIGN_AGENT_PR_TEMPLATE.md`, `docs/design/REFERENCE_MANIFEST_SCHEMA.md`, `docs/design/REFERENCE_SCORECARD.md`
    - DoD: Kimi page, Drive folder, and desktop code bundle evidence boundaries are recorded; Kimi is not source of truth; deterministic docs guards reject Kimi/Figma/Canva source-of-truth promotion, runtime/token/generated-mirror drift, external writes, binary artifacts, and direct-copy claims; future web/iOS implementation remains blocked behind component contract registry, bridge coverage, visual regression, accessibility regression, and token/runtime parity decisions.
  - [ ] Design component contract registry seed tracking:
    - Owner: @katsiaryna_kavaleuskaya
    - Priority: P1
    - Status: open
    - Target PR: #1745 `feat(design): add design component contract registry seed`, branch `codex/design-component-contract-registry-seed-v1`
    - Reason: The Kimi modernization bridge and PR-9 design-system automation sequence require a repo-owned machine-readable component registry before bridge coverage inventory or any web/iOS implementation slice can safely start.
    - Next lane: `feat(design): add design bridge coverage inventory`
    - Links: `docs/orchestration/contracts/design_component_registry.v1.json`, `scripts/design/design_component_registry.py`, `docs/orchestration/contracts/DESIGN_COMPONENT_CONTRACT_REGISTRY.md`, `docs/orchestration/KIMI_PROTOTYPE_INTAKE_MODERNIZATION_BRIDGE_PROTOCOL.md`, `docs/design/ui_component_vocabulary.json`
    - DoD: Registry seed includes only repo-confirmed component ids from `docs/design/ui_component_vocabulary.json`; unconfirmed anchors remain `unspecified`; validator fails closed on malformed JSON, missing fields, unknown or duplicate ids, invalid status, empty strings, and external evidence-tool authority promotion; docs keep Kimi/Figma/Canva/Penpot/Storybook/Code Connect evidence-only; next lane is bridge coverage inventory with no runtime, token, generated mirror, Storybook config, screenshot, binary asset, or external write changes.
  - [ ] Design bridge coverage inventory:
    - Owner: @katsiaryna_kavaleuskaya
    - Priority: P1
    - Status: complete in PR #1797; follow-up lane active for visual regression decision gate
    - Target PR: #1797 `codex/design-bridge-coverage-inventory-v1` (`feat(design): add design bridge coverage inventory`)
    - Reason: The seeded component registry must be followed by a repo-owned coverage inventory before modern Kimi-derived direction can be scheduled into bounded web/iOS implementation slices.
    - Links: `docs/orchestration/contracts/design_component_registry.v1.json`, `docs/orchestration/contracts/design_bridge_coverage_inventory.v1.json`, `scripts/design/design_component_registry.py`, `scripts/design/design_bridge_coverage_inventory.py`, `docs/orchestration/contracts/DESIGN_COMPONENT_CONTRACT_REGISTRY.md`, `docs/design/ui_component_vocabulary.json`
    - DoD: Inventory maps registry component ids across repo vocabulary, web runtime, iOS runtime, Storybook review, Figma reference, Penpot reference, and Code Connect anchors; validator exists and fails closed; tests exist; unconfirmed values remain `unspecified`; missing coverage blocks runtime implementation; external evidence remains non-authoritative; no runtime, token, generated mirror, Storybook config, screenshot, binary asset, or external write changes are made.
  - [ ] P1: Design visual regression decision gate:
    - Owner: @katsiaryna_kavaleuskaya
    - Priority: P1
    - Status: active
    - Target PR: `codex/design-visual-regression-decision-gate-v1` (`feat(design): add visual regression decision gate`)
    - Reason: The bridge coverage inventory must be followed by a repo-owned fail-closed visual QA decision contract before any web/iOS implementation planning can treat visual evidence as implementation-eligible.
    - Links: `docs/orchestration/contracts/design_bridge_coverage_inventory.v1.json`, `docs/orchestration/contracts/design_visual_regression_decisions.v1.json`, `scripts/design/design_bridge_coverage_inventory.py`, `scripts/design/design_visual_regression_decisions.py`, `docs/orchestration/contracts/DESIGN_COMPONENT_CONTRACT_REGISTRY.md`, `docs/design/DESIGN_SYSTEM_AUTOMATION_SPEC.md`
    - DoD: Machine-readable visual decision artifact exists; validator exists; tests exist; every bridge inventory component has exactly one visual decision record; no screenshots or binaries are committed; missing visual baseline, tool, or threshold blocks runtime implementation; Kimi/Figma/Canva/Penpot/Storybook/Code Connect remain reference-only; next gate is accessibility regression decision gate.
  - Deferred design automation lane: `design-automation-deferred-launch-copy-linter`
    - Owner: @katsiaryna_kavaleuskaya
    - Priority: P1
    - Target PR: TBD, separate coordinator packet required before implementation
    - Reason for deferral: Launch copy compliance is valuable but should follow the asset guard selection so release-facing visual asset validation has deterministic ownership first.
    - Links to relevant audit/docs: `docs/orchestration/DESIGN_AGENT_WORKFLOW.md`, `docs/design/NEXT_DESIGN_AUTOMATION_MODULE_DECISION.md`, `docs/orchestration/DESIGN_AUTOMATION_NEXT_LANE_PACKET_2026-05-08.md`
    - DoD: A future PR defines wellness/compliance copy sources, blocked-claim policy, bounded checks, and review mapping before any linter implementation.
  - Deferred design automation lane: `design-automation-deferred-marketing-asset-pack`
    - Owner: @katsiaryna_kavaleuskaya
    - Priority: P2
    - Target PR: TBD, separate coordinator packet required before implementation
    - Reason for deferral: Marketing asset compilation depends on approved asset and copy truth and must not precede the asset guard and copy-compliance lanes.
    - Links to relevant audit/docs: `docs/orchestration/DESIGN_AGENT_WORKFLOW.md`, `docs/design/NEXT_DESIGN_AUTOMATION_MODULE_DECISION.md`, `docs/orchestration/DESIGN_AUTOMATION_NEXT_LANE_PACKET_2026-05-08.md`
    - DoD: A future PR identifies approved input artifacts, packaging boundaries, no external write authority, rollback, and release review gates before any compiler implementation.
  - Deferred design automation lane: `design-automation-deferred-component-drift-expansion`
    - Owner: @katsiaryna_kavaleuskaya
    - Priority: P2
    - Target PR: TBD, separate coordinator packet required before implementation
    - Reason for deferral: Component drift expansion can become runtime redesign unless it is tied to a concrete repo-owned evidence gap and deterministic comparison scope.
    - Links to relevant audit/docs: `docs/design/DESIGN_SCORECARD_CHECKS.md`, `docs/design/UI_COMPONENT_VOCABULARY.md`, `docs/orchestration/DESIGN_AGENT_WORKFLOW.md`, `docs/design/NEXT_DESIGN_AUTOMATION_MODULE_DECISION.md`
    - DoD: A future PR names the exact component/evidence gap, permitted docs/tooling/test surfaces, forbidden runtime redesign surfaces, and bounded validation plan.
  - Deferred design automation lane: `design-automation-deferred-design-agent-research`
    - Owner: @katsiaryna_kavaleuskaya
    - Priority: P2
    - Target PR: TBD, separate coordinator packet required before implementation
    - Reason for deferral: Design-agent adjacent research remains process/eval-only and should not compete with the selected deterministic release asset guard lane.
    - Links to relevant audit/docs: `docs/orchestration/DESIGN_AGENT_WORKFLOW.md`, `docs/orchestration/DESIGN_AGENT_PR_TEMPLATE.md`, `docs/research/DESIGN_GEPA_PROMPT_RUBRIC_EVOLUTION_LANE.md`, `docs/design/NEXT_DESIGN_AUTOMATION_MODULE_DECISION.md`
    - DoD: A future PR preserves repo truth, marks research outputs non-canonical, avoids runtime/prompt self-modification, and defines deterministic review gates before any research expansion.

<a id="ledger-p1-design-runtime-system-web-ios-epic"></a>
- [x] P1: Coordinator-first design runtime system web+iOS epic bootstrap and PR train
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (design-system productization and governance)
  - Target PR: PR #1497 (`docs(design): add coordinator-first design runtime system web-ios runbook`) -> PR #1504 (`feat(frontend): add missing governed UI primitives v1`) -> PR #1510 (`feat(frontend): normalize specialized design families into shared governed patterns`) -> PR #1519 (`feat(tokens): add product-level token layer for planning and premium surfaces`, PR-3) -> PR #1527 (`feat(frontend): converge web shell onto governed tokens`, PR-4) -> PR #1569 (`feat(ios): adopt governed design-system primitives`, PR-5, branch `codex/ios-design-system-adoption-v1`) -> PR-5B (`feat(ios): adopt design tokens on Home Plate Progress`, branch `codex/ios-design-system-adoption-v1-clean`) -> PR #1581 (`feat(design): add accessibility motion state contract`, PR-6) -> PR #1595 (`feat(design): lock figma manifest exports`, PR-7) -> PR #1606 (`feat(storybook): expand design parity review surfaces`, PR-8) -> PR-9 docs-only design-system automation packet
  - Status: ✅ PR-0 merged; PR-1 merged in PR #1504; PR-2 merged in PR #1510; PR-3 product token expansion merged in PR #1519; PR-4 web shell convergence merged in PR #1527; PR-5 merged in PR #1569; PR-5B Home / Plate / Progress adoption is no longer an active next slice for this train; PR-6 accessibility / motion / state contract merged in PR #1581; PR-7 export lock and manifest hardening merged in PR #1595; PR-8 Storybook parity merged in PR #1606. The PR-0 through PR-8 design runtime web+iOS train is complete; PR-9 is reopened only as a docs/test governance packet for machine-readable design-system automation infrastructure before any future implementation slice.
  - Area: docs / orchestration / design-system / frontend / ios / storybook
  - Finding Type: coordinator-owned epic bootstrap and sequencing contract
  - Reason: PulsePlate already has governed design-runtime, token-pipeline,
    and bridge baselines on `main`, but it still lacks one coordinator-owned
    productization train that locks source precedence, role order, PR order,
    review surfaces, merge/cleanup governance, and the bounded handoff from
    docs bootstrap into implementation slices. This series must stay repo-first,
    keep clients thin, and avoid reopening merged design/runtime/bridge lanes.
  - Links:
    - `docs/orchestration/DESIGN_RUNTIME_SYSTEM_WEB_IOS_PR_SERIES_RUNBOOK.md`
    - `docs/orchestration/DESIGN_RUNTIME_SYSTEM_WEB_IOS_PR0_BOOTSTRAP_PACKET_2026-04-22.md`
    - `docs/orchestration/DESIGN_RUNTIME_SYSTEM_WEB_IOS_PR1_MISSING_GOVERNED_PRIMITIVES_PACKET_2026-04-23.md`
    - `docs/orchestration/DESIGN_RUNTIME_SYSTEM_WEB_IOS_PR2_SPECIALIZED_FAMILIES_NORMALIZATION_PACKET_2026-04-23.md`
    - `docs/orchestration/DESIGN_RUNTIME_SYSTEM_WEB_IOS_PR3_PRODUCT_TOKEN_EXPANSION_PACKET_2026-04-24.md`
    - `docs/orchestration/DESIGN_RUNTIME_SYSTEM_WEB_IOS_PR4_WEB_SHELL_CONVERGENCE_PACKET_2026-04-25.md`
    - `docs/orchestration/DESIGN_RUNTIME_SYSTEM_WEB_IOS_PR5_IOS_DESIGN_SYSTEM_ADOPTION_PACKET_2026-04-28.md`
    - `docs/orchestration/DESIGN_RUNTIME_SYSTEM_WEB_IOS_PR5B_HOME_PLATE_PROGRESS_ADOPTION_PACKET_2026-04-29.md`
    - `docs/orchestration/DESIGN_RUNTIME_SYSTEM_WEB_IOS_PR6_ACCESSIBILITY_MOTION_STATE_CONTRACT_PACKET_2026-04-29.md`
    - `docs/orchestration/DESIGN_RUNTIME_SYSTEM_WEB_IOS_PR7_EXPORT_LOCK_AND_MANIFEST_HARDENING_PACKET_2026-04-30.md`
    - `docs/orchestration/DESIGN_RUNTIME_SYSTEM_WEB_IOS_PR8_STORYBOOK_PARITY_PACKET_2026-04-30.md`
    - `docs/orchestration/DESIGN_RUNTIME_SYSTEM_WEB_IOS_CLOSEOUT_NEXT_WAVE_PACKET_2026-04-30.md`
    - [PR #1606](https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1606)
    - `docs/design/TOKENS_SOT.md`
    - `docs/design/TOKEN_PIPELINE_GOVERNANCE.md`
    - `docs/design/UI_COMPONENT_VOCABULARY.md`
    - `docs/runbooks/DESIGN_TOOLING_OPERATING_MODEL.md`
    - `docs/design/DESIGN_AGENT_RUNTIME_PR_CHAIN.md`
    - `docs/orchestration/DESIGN_BRIDGE_OPERATIONALIZATION_PACKET_2026-04-11.md`
    - `docs/orchestration/UI_EPIC_PR_SERIES_RUNBOOK.md`
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-token-expansion-activation`
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-design-token-lock-ci`
  - DoD:
    - One coordinator-owned runbook exists for the full `PR-0` through `PR-8`
      train with fixed source precedence, role order, validation matrix, merge
      path, and cleanup path
    - `PR-0` remains docs-only and introduces no runtime, client, or CI
      behavior changes; `PR-1` is the first executable slice and stays bounded
      to missing governed primitives only
    - The line explicitly stays downstream of merged design-runtime and
      design-bridge baselines and does not consume reserved design-agent PR
      slots
    - Web is locked as renderer-only and Storybook-first review only; iOS
      remains simulator-first for implementation slices
    - `/tokens` stays the authoring source and generated web+iOS mirrors remain
      derived runtime outputs
    - `figma-manifest` is hardened by the dedicated export lock slice without
      becoming the token-pipeline schema
    - PR-8 Storybook review parity is merged and the runbook does not imply an
      undocumented PR-9 or active follow-on implementation slice
    - PR-9 docs-only packet exists before any future implementation slice and
      records component contract registry, bridge coverage, visual regression,
      accessibility regression, and token/runtime parity boundaries

<a id="ledger-p1-design-agent-runtime-pr-chain"></a>
- [ ] P1: Coordinator-led design-agent runtime PR chain (PR1-PR4)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (design-runtime productization and orchestration)
  - Target PR: PR `#1219` (merged realignment bridge) -> `PR-TBD-DESIGN-AGENT-PR4` (reserved `worktree/design-agent-pr4-creative-research`, with a bounded packet still required before any future opening)
  - Status: ✅ Baseline PR1-PR3 and the realignment bridge are merged in `main`; design-agent PR4 remains optional, unopened, and explicitly reserved
  - Area: scripts / orchestration / design-runtime / docs
  - Finding Type: initiative umbrella and sequencing contract
  - Reason: PulsePlate already has a governed code-native design runtime, but the
    next wave needs a coordinated PR chain so adaptive presentation semantics,
    deterministic browser preview, and bounded creative research ship through
    one repo-first contract instead of becoming ad hoc design-agent behavior.
    This initiative explicitly keeps `/tokens -> vocabulary -> instruction
    contract -> pulseplate_canvas_v1` as the canonical source path and requires
    `bug-hunter` as a mandatory post-open fix lane before each PR is considered
    review-ready.
  - Links:
    - `docs/design/DESIGN_AGENT_RUNTIME_PR_CHAIN.md`
    - `docs/orchestration/DESIGN_AGENT_RUNTIME_REALIGNMENT_PACKET.md`
    - `docs/library/brainstorm/2026-03-21_design-agent-runtime-pr-chain.md`
    - `docs/library/research/2026-03-21_design-agent-runtime-pr-chain_evidence.md`
    - `docs/library/decisions/ADR_DESIGN_AGENT_RUNTIME_PR_CHAIN_2026-03-21.md`
    - `docs/library/promotion/2026-03-21_design-agent-runtime-pr-chain_promotion-log.md`
    - `docs/orchestration/DESIGN_AGENT_RUNTIME_REALIGNMENT_PACKET.md`
    - `docs/design/CODE_NATIVE_DESIGN_RUNTIME.md`
    - `docs/runbooks/DESIGN_TOOLING_OPERATING_MODEL.md`
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-design-execution-adapter-seam`
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-design-layout-archetype-templates`
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-screen-content-template-convergence`
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-design-html-preview`
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-design-prompt-canvas-compiler`
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-design-tooling-phase2-env-api`
  - DoD:
    - Baseline realized: PR1 artifact pack, PR2 additive `interaction_contract`,
      and PR3 deterministic HTML preview lane are explicitly acknowledged as
      already merged baseline state in `main`, primarily via `PR #1210`
    - Realignment bridge merged: the chain SoT and umbrella ledger item are
      state-aware and no longer describe the initiative as `PR1 scaffold active`
    - Realignment bridge merged: `docs/orchestration/DESIGN_AGENT_RUNTIME_REALIGNMENT_PACKET.md`
      canonically defines the docs-only coordinator cycle, routing, sync points,
      acceptance packet, and bug packet for the bridge PR
    - Design-agent PR4 remains optional, unopened, and explicitly reserved for
      bounded creative-research work; the bridge PR does not consume that
      reserved design-agent PR4 slot
    - Every PR in the chain documents and runs the mandatory
      `qa-engineer-agent -> bug-hunter` post-open review loop
    - No PR in the chain introduces public API changes or live self-modifying
      UI without a separate approved follow-up

<a id="ledger-p1-design-bridge-operationalization-pr21"></a>
- [ ] P1: PR21 design-bridge operationalization lane (preflight + capture + first parity pack)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (design-ops evidence pipeline)
  - Target PR: PR #1391 (`feat/design-bridge-ops-parity-pack`)
  - Status: 📋 Planned from merged bridge baseline on `main`
  - Area: docs / orchestration / design / runbooks / frontend / ios
  - Finding Type: operational follow-on after merged bridge baseline
  - Reason: Wave 7 defines a follow-on lane after the merged realignment bridge
    so the design bridge becomes an executable evidence pipeline instead of
    remaining principle-only documentation. This lane is separate from the
    colleague-owned bridge-closeout PR `#1386`, keeps Cloudflare preview
    advisory-only, and does not consume the reserved `design-agent PR4` slot.
  - Links:
    - `docs/roadmap/PulsePlate_P0_P1_Execution_Document_2026-03-30.md`
    - `docs/orchestration/DESIGN_BRIDGE_OPERATIONALIZATION_PACKET_2026-04-11.md`
    - `docs/design/PENPOT_STORYBOOK_BRIDGE.md`
    - `docs/runbooks/DESIGN_TOOLING_OPERATING_MODEL.md`
    - `frontend/src/stories/PulsePlateDesignSystemGuidelines.mdx`
    - `docs/design/DESIGN_BRIDGE_FIRST_PARITY_PACK_2026-04-11.md`
    - `docs/runbooks/sessions/DESIGN_TOOLING_SESSION_2026-04-11_design-bridge-ops-parity-pack.md`
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-design-agent-runtime-pr-chain`
  - DoD:
    - One canonical packet defines the design-bridge operationalization lane,
      role order, sync points, and merge path
    - Web review evidence is explicitly Storybook-first and points to real
      Storybook/MDX surfaces in repo
    - iOS evidence is explicitly simulator-based for workspace
      `ios/PulsePlate.xcworkspace` and scheme `PulsePlate`
    - The first parity pack is limited to representative baseline surfaces:
      `ios.home`, `web.plate`, `web.progress`
    - Cloudflare preview/deploy remains non-blocking and outside merge truth
    - The lane does not edit or reinterpret the colleague-owned closeout work
      around PR `#1386`
    - Draft PR may open with web evidence complete and an explicit iOS verifier
      blocker recorded in the packet/session artifact, but review-ready and
      merge-ready status still require the iOS blocker to be resolved or
      dispositioned

<a id="ledger-p1-ui-epic-post-bridge-series"></a>
- [ ] P1: Post-bridge UI epic series bootstrap and execution lane
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (UI/UX execution governance)
  - Target PR: PR #1463 (`docs(ui-ux): add post-bridge UI epic runbook and lane packet`)
  - Status: 🛠️ In progress in PR #1463
  - Area: docs / orchestration / ios / frontend / storybook
  - Finding Type: post-bridge execution follow-on
  - Reason: The design-bridge baseline is already merged on `main` through
    PR `#1386` and PR `#1391`, so the next UI lane must start as a fresh
    product-facing series instead of reopening bridge operationalization. The
    first executable gap is iOS visible coherence, followed by one semantic
    iOS surface seam, then bounded Storybook parity expansion, and only later
    thin-client consumption of the already existing backend
    `next_best_action` contract.
  - Evidence:
    - `docs/orchestration/DESIGN_BRIDGE_OPERATIONALIZATION_PACKET_2026-04-11.md:44-72`
    - `docs/roadmap/BACKLOG_LEDGER.md:860-876`
    - `app/schemas/weekly_plan.py:201-206`
    - `app/routers/pro.py:360-368`
    - `docs/orchestration/MONETIZATION_PLANNING_WAVE_PR_SERIES_RUNBOOK.md:74-103`
    - `frontend/src/api/__tests__/thin-client-guards.test.ts:7-19`
    - `frontend/AGENTS.md:27-38`
    - `ios/AGENTS.md:86-92`
  - Links:
    - `docs/orchestration/UI_EPIC_PR_SERIES_RUNBOOK.md`
    - `docs/orchestration/UI_EPIC_PR1_BOOTSTRAP_PACKET_2026-04-18.md`
    - `docs/architecture/ADR_UI_SEMANTIC_SURFACE_SEAM_2026-04-19.md`
    - `docs/orchestration/DESIGN_BRIDGE_OPERATIONALIZATION_PACKET_2026-04-11.md`
    - `docs/design/DESIGN_BRIDGE_FIRST_PARITY_PACK_2026-04-11.md`
    - `docs/runbooks/DESIGN_TOOLING_OPERATING_MODEL.md`
    - `frontend/src/stories/PulsePlateDesignSystemGuidelines.mdx`
    - `ios/PulsePlate.xcworkspace`
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-design-bridge-operationalization-pr21`
  - Blockers:
    - PR-3 must keep the semantic surface seam presentation-only and ADR-backed
      (`docs/architecture/ADR_UI_SEMANTIC_SURFACE_SEAM_2026-04-19.md:1-45`)
    - PR-3 must ship simulator evidence and targeted tests before the seam is
      considered stable
    - PR-5 may consume `next_best_action`, but clients must remain thin and
      renderer-only (`frontend/src/api/__tests__/thin-client-guards.test.ts:7-19`;
      `frontend/AGENTS.md:27-38`; `ios/AGENTS.md:86-92`)
  - DoD:
    - A dedicated post-bridge UI epic runbook exists and locks PR order,
      role order, sync points, validation, and merge-path rules
    - The runbook explicitly states that merged bridge work is baseline state
      and must not be reopened as a new bridge PR
    - The lane enforces one PR per dedicated worktree from synced
      `origin/main`
    - Web review is locked as Storybook-first and iOS evidence as
      simulator-first
    - Billing, entitlement, provider modernization, deploy/runtime infra,
      Cloudflare merge truth, and any new `/api/v1/ui/state` rail are
      explicitly out of scope for this series
    - The first executable slice is fixed as iOS visible coherence before
      surface-seam or web parity expansion work begins
    - Late-phase client hint work is explicitly limited to consuming the
      already existing backend `next_best_action` contract

<a id="ledger-p1-design-execution-adapter-seam"></a>
- [ ] P1: Design execution adapter seam promotion beyond local artifact lane
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (design runtime governance)
  - Target PR: PR #1117 (`feat(design): add code-first UI vocabulary and strengthen instruction generation`) -> PR-TBD-DESIGN-RUNTIME-ADAPTER
  - Status: 📋 Deferred after PR #1134 artifact-contract convergence
  - Area: scripts / integrations / design-runtime / docs
  - Finding Type: temporary seam follow-up
  - Reason: PR #1134 promotes `code_native_canvas` into the canonical local
    artifact emitter, but live external execution still remains intentionally
    deferred. Any bridge beyond the local artifact lane must consume
    `pulseplate_canvas_v1`, preserve manifest and verification semantics, and
    avoid becoming a hidden topology source of truth.
  - Links:
    - `docs/architecture/ADR_DESIGN_EXECUTION_ADAPTER_SEAM_2026-03-11.md`
    - `scripts/design/execution_adapters.py`
    - `scripts/design/execute_design.py`
    - `scripts/design/verify_design.py`
    - `scripts/design/canvas_artifact.py`
    - `docs/design/CODE_NATIVE_DESIGN_RUNTIME.md`
  - DoD:
    - A reviewed adapter exists for the chosen post-local design runtime target
    - External execution consumes `pulseplate_canvas_v1` or governed
      instruction payloads without bypassing contract validation
    - Manifest and verification flows distinguish local artifact emit from live
      bridge execution
    - Tests prove fail-closed behavior for missing auth, unsupported adapters,
      and contract drift
    - `docs/runbooks/DESIGN_TOOLING_OPERATING_MODEL.md` is updated so
      the adapter seam is described as a governed bridge rather than a local
      stub-only placeholder

<a id="ledger-p1-design-runtime-screen-coverage"></a>
- [ ] P1: Design runtime screen coverage beyond initial six parity screens
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (design runtime expansion)
  - Target PR: PR #1117 (`feat(design): add code-first UI vocabulary and strengthen instruction generation`) -> PR-TBD-DESIGN-RUNTIME-SCREEN-COVERAGE
  - Status: 📋 Deferred after PR #1117 contract hardening
  - Area: scripts / design-runtime / design-docs
  - Finding Type: deferred scope follow-up
  - Reason: PR #1117 intentionally hardens the code-first vocabulary and
    instruction contract around the first six parity screens only
    (`ios.home`, `ios.plate`, `ios.progress`, `web.home`, `web.plate`,
    `web.progress`). Additional governed screens must be promoted under the same
    contract instead of being inferred ad hoc.
  - Links:
    - `scripts/design/generate_figma_instructions.py`
    - `scripts/design/instructions/`
    - `docs/design/UI_SCREEN_BRIEF_TEMPLATES.md`
    - `docs/runbooks/DESIGN_TOOLING_OPERATING_MODEL.md`
  - DoD:
    - New screens are added through the same code-first brief and vocabulary
      contract
    - Instruction generation, execution, and verification remain deterministic
      for each added screen
    - Manifest/verification docs explicitly list the expanded supported-screen
      surface

<a id="ledger-p1-design-layout-archetype-templates"></a>
- [ ] P1: Reusable layout archetype templates beyond current shell families
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (design runtime semantics)
  - Target PR: PR #1117 (`feat(design): add code-first UI vocabulary and strengthen instruction generation`) -> PR-TBD-DESIGN-LAYOUT-ARCHETYPE-TEMPLATES
  - Status: 📋 Deferred after PR #1117 contract hardening
  - Area: scripts / design-runtime / docs
  - Finding Type: deferred semantics follow-up
  - Reason: PR #1117 formalizes `layout_archetype`, `layout_pattern`, and
    section/component hierarchy semantics, but it intentionally keeps the first
    archetype set small (`hero_shell`, `content_shell`, `dashboard_shell`).
    Richer reusable archetype families and template semantics should be promoted
    in a dedicated follow-up instead of expanding the contract implicitly.
  - Links:
    - `scripts/design/contracts.py`
    - `scripts/design/generate_figma_instructions.py`
    - `docs/design/CODE_FIRST_UI_PROMPT_COOKBOOK.md`
    - `docs/runbooks/DESIGN_TOOLING_OPERATING_MODEL.md`
  - DoD:
    - Additional archetype families are named and documented in the cookbook and
      runtime contract
    - Validation enforces the promoted archetype set deterministically
    - Screen-generation templates reuse the promoted archetypes without hidden
      per-screen exceptions

<a id="ledger-p1-screen-content-template-convergence"></a>
- [ ] P1: Screen content model, reusable template registry, and `pulseplate_canvas_v1` convergence after PR #1121
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (design runtime semantics)
  - Target PR: PR #1134
  - Status: 🚧 In progress in PR3 design canvas artifact contract
  - Area: scripts / design-runtime / docs
  - Finding Type: deferred model-governance cleanup
  - Reason: PR3 promotes reusable layout templates to the canonical topology
    source, removes duplicated inline `SCREEN_CONTENT_MODEL` structure, and
    introduces the governed `pulseplate_canvas_v1` artifact contract so screen
    topology and code-native runtime output are emitted from the same source.
  - Links:
    - `scripts/design/generate_figma_instructions.py`
    - `scripts/design/canvas_artifact.py`
    - `scripts/design/layout_templates.py`
    - `docs/design/CODE_NATIVE_DESIGN_RUNTIME.md`
  - DoD:
    - Reusable layout templates are the canonical authoring path for screen
      topology
    - `SCREEN_CONTENT_MODEL` stays metadata-only
    - `pulseplate_canvas_v1` has an explicit schema or artifact contract tied to
      that same source of truth
    - Tests prove instruction topology and emitted `pulseplate_canvas_v1`
      stay structurally aligned
    - Design-runtime docs describe the chosen source-of-truth contract

<a id="ledger-p1-design-html-preview"></a>
- [ ] P1: HTML preview and browser renderer on top of `pulseplate_canvas_v1`
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (design runtime productization)
  - Target PR: PR #1134 -> PR-TBD-DESIGN-HTML-PREVIEW
  - Status: 📋 Deferred after PR #1134 artifact-contract convergence
  - Area: scripts / frontend / design-runtime / docs
  - Finding Type: deferred renderer follow-up
  - Reason: PR #1134 intentionally stops at the governed artifact boundary so
    reusable layout templates, metadata-only `SCREEN_CONTENT_MODEL`, and
    `pulseplate_canvas_v1` can stabilize before any browser rendering surface is
    added.
  - Links:
    - `scripts/design/generate_figma_instructions.py`
    - `scripts/design/canvas_artifact.py`
    - `scripts/design/layout_templates.py`
    - `docs/design/CODE_NATIVE_DESIGN_RUNTIME.md`
  - DoD:
    - A deterministic HTML preview consumes `pulseplate_canvas_v1` without
      introducing a second topology source
    - Renderer output is validated against canvas sections and nodes
    - Tests cover representative screens such as `ios.home`, `web.plate`, and
      `web.progress`

<a id="ledger-p1-design-prompt-canvas-compiler"></a>
- [ ] P1: Prompt-to-canvas compiler expansion beyond artifact-contract PR3
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (design runtime semantics)
  - Target PR: PR #1134 -> PR-TBD-DESIGN-PROMPT-CANVAS-COMPILER
  - Status: 📋 Deferred after PR #1134 artifact-contract convergence
  - Area: scripts / orchestration / design-runtime / docs
  - Finding Type: deferred compiler follow-up
  - Reason: PR #1134 establishes the first canonical artifact, but it does not
    yet expand prompt-to-canvas compilation beyond the current topology and
    instruction contract boundary.
  - Links:
    - `scripts/design/generate_figma_instructions.py`
    - `scripts/design/canvas_artifact.py`
    - `scripts/design/contracts.py`
    - `docs/design/CODE_NATIVE_DESIGN_RUNTIME.md`
  - DoD:
    - Prompt packets compile deterministically into governed screen instructions
      and `pulseplate_canvas_v1`
    - Compiler stages expose explicit topology, token, and state decisions for
      review
    - Tests prove topology alignment and stable output for representative screen
      prompts

<a id="ledger-p1-design-token-lock-ci"></a>
- [ ] P1: Design-token lockfile and deterministic CI/build contract
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-TBD-DESIGN-TOKEN-LOCK-CI
  - Status: 📋 Planned
  - Area: design-system / frontend / iOS / CI
  - Finding Type: deterministic build-governance gap
  - Reason (EN): The repo now has token-pipeline governance and generated runtime mirrors, but it still does not have a canonical build-from-lock contract. There is no enforced `tokens.lock.json`, no explicit artifact-from-lock-only rule, and no release/rollback playbook for token changes across web and iOS.
  - Links:
    - `docs/design/TOKENS_SOT.md`
    - `docs/design/TOKEN_PIPELINE_GOVERNANCE.md`
    - `frontend/src/styles/tokens.css`
    - `ios/PulsePlate/DesignSystem/DesignTokens.generated.swift`
  - DoD:
    - Canonical token pipeline defines lockfile ownership, artifact generation from lock only, and CI drift policy
    - Release/rollback runbook exists for token builds across web/iOS surfaces
    - Existing semantic/token-governance docs link to the same deterministic build contract

<a id="ledger-p1-design-button-runtime-code-parity"></a>
- [ ] P1: Button RuntimeSet code parity (Figma vs `Button.tsx`)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR #1552
  - Status: OPEN — implementation on branch `feat/button-runtime-set-code-parity`; checkbox flips at merge close-out or docs-only ledger PR if preferred
  - Area: design-system / frontend / governance
  - Finding Type: Figma runtime audit follow-up (2026-04-27)
  - Reason (EN): The Figma Button RuntimeSet includes success, warning, danger, and loading states. `Button.tsx` now supports `primary`, `secondary`, `ghost`, `destructive`, `success`, and `warning` with sizes `sm` / `md` / `lg`, plus optional `loading` / `loadingLabel` (`frontend/src/components/ui/Button.tsx:3-4`, `frontend/src/components/ui/Button.tsx:10-11`).
  - Links:
    - `docs/design/FIGMA_RUNTIME_SET_AUDIT_2026-04-27.md`
    - `frontend/src/components/ui/Button.tsx`
    - `frontend/src/components/ui/__tests__/Button.test.tsx`
    - `frontend/src/components/ui/Button.stories.tsx`
    - `docs/review/PR_1552_FIXED_MAPPING.md`
  - DoD:
    - `success` and `warning` are first-class `ButtonVariant` values backed by existing `--color-success` / `--color-warning` tokens (no `tokens.css` edits in PR #1552).
    - Figma `tone=danger` maps only to `variant="destructive"` (documented in audit; no `danger` alias).
    - `loading` + `loadingLabel` with `aria-busy`, disabled while loading, and spread order preventing override of disabled/busy when loading.
    - Vitest coverage in `frontend/src/components/ui/__tests__/Button.test.tsx` and Storybook `frontend/src/components/ui/Button.stories.tsx`.

<a id="ledger-p1-design-input-runtime-code-parity"></a>
- [x] P1: Input RuntimeSet code parity (Figma vs `Input.tsx`)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR #1553
  - Status: CLOSED — merged in PR #1553 (`4206d81a5`); accessory-shell follow-up remains open
  - Area: design-system / frontend / governance
  - Finding Type: Figma runtime audit follow-up (2026-04-27)
  - Reason (EN): Core Input RuntimeSet parity for size/invalid/loading/type shipped in PR #1553; accessory-shell capabilities (unit/prefix/suffix/clear-action) remain intentionally deferred to the dedicated follow-up item.
  - Links:
    - `docs/design/FIGMA_RUNTIME_SET_AUDIT_2026-04-27.md`
    - `frontend/src/components/ui/Input.tsx`
    - `frontend/src/components/ui/__tests__/Input.test.tsx`
    - `frontend/src/components/ui/Input.stories.tsx`
    - `docs/review/PR_1553_FIXED_MAPPING.md`
  - DoD:
    - `size` supports `sm|md|lg` and maps to expected runtime classes in `frontend/src/components/ui/Input.tsx`.
    - `invalid` enforces error styling and `aria-invalid` semantics (including explicit token preservation for `grammar|spelling`).
    - `loading` sets `aria-busy` and deterministically enforces disabled-while-loading behavior.
    - Native `type` passthrough remains supported for `text`, `number`, `search`, `password` (runtime "secret" maps to native `password`).
    - Focused Vitest coverage for these behaviors exists in `frontend/src/components/ui/__tests__/Input.test.tsx` and passes in CI.
    - Storybook coverage for these behaviors exists in `frontend/src/components/ui/Input.stories.tsx` and passes `build-storybook`.
    - Accessory shell API (`unit`, `prefix`, `suffix`, `clear-action`) stays deferred to a dedicated PR

<a id="ledger-p1-design-input-accessory-shell-parity"></a>
- [ ] P1: Input accessory shell parity
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-TBD-DESIGN-INPUT-ACCESSORY-SHELL
  - Status: OPEN
  - Area: design-system / frontend / governance
  - Finding Type: Figma runtime audit follow-up
  - Reason (EN): Unit, prefix, suffix, and clear-action require a compound input shell rather than the core `Input` primitive.
  - Links:
    - `docs/design/FIGMA_RUNTIME_SET_AUDIT_2026-04-27.md`
    - `frontend/src/components/ui/Input.tsx`
  - DoD:
    - Decide whether accessory behavior belongs in `Input`, `InputGroup`, or FormField composition.
    - Define prefix/suffix/unit/clear-action API.
    - Add tests/stories/docs in a dedicated PR.

<a id="ledger-p1-rebuild-runtime-vocabulary-promotion-decision"></a>
- [ ] P1: Rebuild runtime family vocabulary promotion decision
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-TBD-REBUILD-RUNTIME-VOCABULARY-PROMOTION
  - Area: design-system / governance / vocabulary
  - Reason: Current Figma rebuild families have been audited, but most do not
    have exact canonical vocabulary support. A dedicated repo-side decision is
    required before any helper family is promoted into canonical primitive
    status.
  - Links:
    - `docs/design/FIGMA_REBUILD_RUNTIME_VOCABULARY_DECISION.md`
    - `docs/design/UI_COMPONENT_VOCABULARY.md`
    - `docs/runbooks/DESIGN_TOOLING_OPERATING_MODEL.md`
  - DoD:
    - each helper family is either explicitly promoted, explicitly kept as
      helper-only, or explicitly rejected
    - no off-canon-risk family is promoted without repo-side decision
    - UI vocabulary docs remain aligned with the final decision
    - Figma no longer leads primitive semantics for these families

<a id="ledger-p1-specialized-family-promotion-review"></a>
- [ ] P1: Specialized rebuild family promotion review
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-TBD-SPECIALIZED-FAMILY-PROMOTION-REVIEW
  - Area: design-system / governance / vocabulary
  - Reason: Specialized rebuild families are adjacent to canonical concepts but
    are not exact primitives. A narrow review is required before any future
    primitive promotion or vocabulary expansion.
  - Links:
    - `docs/design/FIGMA_REBUILD_RUNTIME_VOCABULARY_DECISION.md`
    - `docs/design/FIGMA_REBUILD_SPECIALIZED_FAMILY_REVIEW.md`
    - `docs/design/UI_COMPONENT_VOCABULARY.md`
  - DoD:
    - each specialized family has a repo-side decision
    - no specialized family is silently promoted through Figma usage
    - future RFC candidates are explicitly identified
    - helper-only families remain helper-only until a later reviewed decision

<a id="ledger-p1-color-profile-automation-parity"></a>
- [ ] P1: Color-profile automation and parity evidence follow-through
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (design-system governance)
  - Target PR: PR-TBD-COLOR-PROFILE-AUTOMATION
  - Status: Not started
  - Area: frontend / ios / design-system / governance
  - Finding Type: color-space policy follow-up
  - Reason: Token governance and generated runtime mirrors are canonical, but
    the repo still lacks deterministic automation for asset-profile checks and
    screenshot parity evidence. This follow-through keeps the `sRGB` baseline
    and optional `Display P3` asset lane from drifting into ad-hoc review
    memory.
  - Links:
    - `docs/design/COLOR_PROFILE_GOVERNANCE.md`
    - `docs/design/TOKEN_PIPELINE_GOVERNANCE.md`
    - `docs/design/TOKENS_SOT.md`
    - `ios/PulsePlate/Extensions/Color+Assets.swift`
  - DoD:
    - Deterministic asset/profile audit lane exists
    - Screenshot parity evidence contract is documented in an active design
      review runbook
    - `Display P3` exceptions require explicit fallback evidence
    - No new runtime component-level color-space logic appears outside the
      governed path

<a id="ledger-p1-ios-subscription-manager"></a>
- [x] P1: iOS SubscriptionManager backend-driven integration
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR #1207
  - Status: ✅ Merged in PR #1207; thin SubscriptionManager receipt-send flow now forwards backend activation truth and refreshes entitlement fail-closed
  - Area: iOS / payments / thin-client policy
  - Finding Type: monetization runtime follow-through
  - Reason (EN): The monetization baseline is iOS-first, but thin-client-safe subscription orchestration still needs an explicit app-side integration item rather than staying implicit inside the broader payments wave.
  - Links:
    - `docs/contracts/PAYMENTS_RU_BY_IOS_BASELINE.md`
    - `docs/roadmap/P0_MASTER_CHECKLIST_PHASE_FIT_TRIAGE_2026-03-05.md`
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p0-billing-activation-service`
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p0-billing-subscription-persistence`
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p0-billing-entitlement-routing`
    - `ios/PulsePlate/Services/SubscriptionManager.swift`
    - `ios/PulsePlateTests/Services/SubscriptionManagerTests.swift`
  - DoD:
    - iOS subscription orchestration remains thin and backend-driven
    - Product/state transitions are deterministic and test-covered
    - No client-side billing logic duplicates backend activation policy

<a id="ledger-p1-app-store-subscription-offers-governance"></a>
- [x] P1: App Store subscription offers governance and StoreKit-truth pricing contract
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR #1312
  - Status: ✅ Merged via `#1312`; release-governance gap closed (reason below
    retained as historical context)
  - Area: iOS / billing / App Store / growth
  - Finding Type: release-governance gap
  - Reason (EN): App Store Connect introductory offers, offer codes, promotional offers, and win-back pricing are operationally separate from in-app UI, but the repo does not yet have a canonical contract that says pricing, trial duration, and eligibility copy must be StoreKit-truth rather than manually inferred in product copy.
  - Links:
    - `docs/contracts/IOS_STOREKIT_PRODUCTS_CONTRACT.md`
    - `docs/contracts/PAYMENTS_RU_BY_IOS_BASELINE.md`
    - `docs/roadmap/IOS_BACKEND_REALIZATION_ROADMAP.md`
    - `docs/MOBILE_API_MIGRATION_GUIDE.md`
    - `docs/review/PR_1312_FIXED_MAPPING.md`
  - DoD:
    - Canonical billing/release doc defines how introductory offers, offer codes, and promotional offers are configured and reviewed
    - UI copy contract says prices, trial duration, and eligibility messaging must come from StoreKit/App Store truth rather than manual hardcoding
    - App Store release-ops and compliance docs link back to the same monetization governance source
  - Follow-up lanes kept separate:
    - `ledger-p1-ios-appstore-assets-rollout`
    - `ledger-p1-ios-appstore-semantic-validators`
    - `ledger-p1-apple-server-api-migration`

<a id="ledger-p1-ios-appstore-assets-rollout"></a>
- [ ] P1: iOS App Store assets rollout and protected ASC environment activation
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR #1323
  - Status: 🚧 In progress (protected `main` evidence attempted on 2026-04-03; rollout remains blocked by missing protected environment secrets in `appstore-assets` and `appstore-privacy`)
  - Area: iOS / release-ops / App Store Connect / compliance
  - Finding Type: release-ops activation follow-up
  - Reason (EN): Fastlane lanes, localized metadata, screenshot validators, and manual GitHub Actions workflows can now be versioned and validated in-repo, but the protected App Store Connect rollout remains incomplete until protected GitHub environments contain the required secrets and the draft upload/review cycle succeeds on `main`. Two protected `workflow_dispatch` runs were executed on 2026-04-03 and both failed closed at secret preflight, which confirms the remaining gap is environment activation rather than repo workflow correctness.
  - Links:
    - `ios/fastlane/Fastfile`
    - `ios/fastlane/app_privacy_details.json`
    - `ios/fastlane/metadata/review_information/notes.txt`
    - `.github/workflows/ios-appstore-assets.yml`
    - `https://github.com/Katsiarynakavaleuskaya/PulsePlate/actions/runs/23961157581`
    - `https://github.com/Katsiarynakavaleuskaya/PulsePlate/actions/runs/23963491232`
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-app-store-subscription-offers-governance`
  - Evidence:
    - `workflow_dispatch` run `23961157581` on `main` SHA `f7419179b305b4c997644ebd4b1cc030a2b6e0ab` completed `validate-assets` successfully, uploaded the `ios-appstore-screenshots` artifact, then failed in `upload-assets` at `Preflight protected App Store upload secrets` because `ASC_KEY_ID`, `ASC_ISSUER_ID`, `ASC_KEY_P8_BASE64`, and `APP_STORE_BUNDLE_IDENTIFIER` were empty in the protected environment.
    - `workflow_dispatch` run `23963491232` on `main` SHA `75830c29614fb6b0e9bc762742a91ac7c172b10d` completed `Validate metadata and privacy package` and `Guard privileged upload ref`, then failed in `upload-app-privacy` at `Preflight protected App Privacy secrets` because `FASTLANE_USER`, `FASTLANE_SESSION`, `FASTLANE_TEAM_ID`, `FASTLANE_TEAM_NAME`, and `APP_STORE_BUNDLE_IDENTIFIER` were empty in the protected environment.
  - Blockers:
    - Populate protected environment secrets for `appstore-assets`
    - Populate protected environment secrets for `appstore-privacy`
    - Re-run both protected `workflow_dispatch` lanes on `main` after environment activation
  - DoD:
    - Protected GitHub environments contain the required ASC API key, bundle identifier, and Apple session secrets
    - `workflow_dispatch` upload of localized metadata and screenshots completes against App Store Connect draft state
    - App Privacy upload succeeds through the protected Apple session lane
    - Privileged upload jobs are constrained to the intended default/release ref and have explicit concurrency/provenance protection
    - First release-ops runbook captures the reviewer-notes and rollback procedure for future asset refreshes

<a id="ledger-p1-ios-appstore-semantic-validators"></a>
- [ ] P1: Semantic App Store metadata and privacy validator expansion
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR #1324
  - Status: 🚧 In progress via `feat/ios-appstore-semantic-validators`
  - Area: iOS / release-ops / compliance
  - Finding Type: semantic compliance coverage gap
  - Reason: Current App Store validators are strong on file presence, dimensions, and basic wording rules, but they do not yet scan metadata/promotional copy for wellness-safe semantic drift or future privacy-package mismatches.
  - Links:
    - `ios/fastlane/verify/validate_metadata.rb`
    - `ios/fastlane/verify/validate_healthkit_copy.rb`
    - `ios/fastlane/app_privacy_details.json`
    - `.github/workflows/ios-appstore-assets.yml`
  - DoD:
    - Metadata validators detect blocked medical/promissory claims on App Store-facing copy
    - Privacy validator has a documented drift check against declared app capabilities and release package inputs
    - New checks stay deterministic and repo-local
    - Release-ops docs explain when semantic validator failures are blockers vs advisory cleanup

<a id="ledger-p1-pr1147-ios-appstore-asset-followups"></a>
<a id="ledger-p2-pr1147-ios-appstore-asset-followups"></a>
- [ ] P1: PR 1147 follow-up for iOS App Store asset workflow alignment
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-TBD-IOS-APPSTORE-ASSET-FOLLOWUPS
  - Area: ios / ci / release assets
  - Finding Type: deferred release-readiness alignment
  - Reason: PR #1147 fixed the immediate correctness, compliance, and governance blockers for Fastlane-driven App Store assets, but audit follow-up shows the remaining screenshot-manifest / UITest / validator contract still matters for deterministic release readiness and should no longer be treated as low-priority cosmetic cleanup.
  - Links:
    - `.github/workflows/ios-appstore-assets.yml`
    - `ios/fastlane/Fastfile`
    - `ios/PulsePlateUITests/AppStoreScreenshotTests.swift`
    - `tests/test_ios_appstore_asset_validators.py`
    - `docs/review/PR_1147_FIXED_MAPPING.md`
  - DoD:
    - `ios-appstore-assets.yml` uses one shared Xcode-selection helper across `validate-assets` and `upload-assets`
    - `ios/fastlane/Fastfile` documents or pins the `snapshot` `ios_version` strategy instead of relying on latest-runtime fallback
    - App/runtime screenshot scenario identifiers and UITest screenshot names move to one shared contract without introducing UI-test linker coupling
    - Cleanup preserves the current deterministic simulator matrix and does not reintroduce `OS=latest` drift

<a id="ledger-p1-release-env-security-contract"></a>
- [ ] P1: Release environment security contract for `API_KEY_REQUIRED` and tier-gating env truth
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: `codex/add-production-runtime-invariant-guards`
  - Status: 🚧 In progress via production runtime invariant guard PR
  - Area: deploy / security / release operations
  - Finding Type: runtime env contract gap
  - Reason (EN): Repo docs describe `API_KEY_REQUIRED` and related auth/tier env flags, but there is no canonical release contract that makes staging/production values explicit and auditable. Without that contract, a release can drift into a weaker env posture than local docs imply.
  - Links:
    - `.env.example`
    - `docker-compose.yaml`
    - `README.md`
    - `docs/deploy/OVERVIEW.md`
    - `docs/security/PRODUCTION_RUNTIME_INVARIANTS.md`
    - `app/security/production_invariants.py`
    - `scripts/ci/check_production_runtime_invariants.py`
  - DoD:
    - Canonical release-env doc defines expected values for `API_KEY_REQUIRED` and other auth/tier-critical env flags across local, staging, and production
    - Verification path for staging/prod env truth is documented and linked from release runbooks
    - Security posture docs no longer rely on implied env defaults where release enforcement is required

<a id="ledger-p1-fastapi-compatibility-gates"></a>
- [ ] P1: FastAPI / Pydantic / Starlette compatibility gates for schema and TestClient drift
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-TBD-FASTAPI-COMPAT-GATES
  - Status: 📋 Planned
  - Area: backend / CI / contracts
  - Finding Type: dependency-compatibility gap
  - Reason (EN): The repo already depends on FastAPI, Pydantic v2, and Starlette/httpx behavior, but it has no canonical CI bundle that explicitly guards strict JSON content-type handling, OpenAPI/root_path drift, nullable-required schema semantics, and TestClient behavior changes during dependency bumps. PR2 dependency refresh surfaced `StarletteDeprecationWarning: Using httpx with starlette.testclient is deprecated; install httpx2 instead`, so the follow-up must decide and test the repo's TestClient/httpx2 migration path instead of suppressing the warning broadly.
  - Links:
    - `README.md`
    - `docs/contracts/API_CANONICAL_MAP.md`
    - `tests/test_openapi_determinism.py`
    - `docs/audience_pack/FACTS_CANONICAL.md`
  - DoD:
    - Deterministic CI smoke/tests exist for strict content-type behavior, OpenAPI snapshot stability, and representative TestClient/runtime request paths
    - Schema checks explicitly cover Pydantic v2 nullable-required semantics where they affect API contracts
    - Test runtime explicitly validates the Starlette TestClient backend policy, including either an `httpx2` migration or documented compatibility decision with no blanket warning suppression
    - Dependency upgrade/runbook docs link to the same compatibility gate source

<a id="ledger-p1-starlette-fastapi-compatibility-pr"></a>
- [ ] P1: Starlette/FastAPI dependency compatibility lane after A8 closeout rescope
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-TBD-DEPENDENCY-STARLETTE-FASTAPI-COMPATIBILITY
  - Status: 📋 Planned
  - Area: dependencies / backend runtime compatibility / CI governance
  - Finding Type: PR scope drift follow-up
  - Reason (EN): PR #1792 must remain an A8 recursive-speed closeout-only lane. Starlette/FastAPI dependency upgrades and the related `app/bootstrap/food_search.py` lifecycle compatibility patch were removed from #1792 and need a separate dependency/runtime compatibility PR with focused tests and review.
  - Links:
    - `docs/review/PR_1792_FIXED_MAPPING.md`
    - `app/bootstrap/food_search.py`
    - `requirements.txt`
    - `requirements-lock.txt`
    - `requirements-ci-lite.txt`
    - `requirements-docker-runtime.txt`
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-fastapi-compatibility-gates`
  - DoD:
    - Dedicated PR updates all relevant dependency surfaces coherently or documents why no bump is needed
    - Runtime compatibility patch, if still required, is implemented outside #1792 with focused lifecycle tests
    - CI evidence includes current-head lint, tests, diff coverage, dependency/security checks, and fixed-mapping dispositions
    - PR body explicitly scopes the dependency/security compatibility lane and does not mix A8 closeout governance changes

<a id="ledger-p1-dependency-governance-pr-series"></a>
- [ ] P1: Dependency governance PR series (cluster policy + coordinator-led lane)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: D0 — governed Python Dependabot intake (PR #2181)
  - Status: 🟡 In progress
  - Area: dependencies / CI governance / orchestration
  - Finding Type: operating model consolidation gap
  - Reason (EN): The repo has floors, locks, and CI installers, but dependency work still risks
    being executed as mixed bump lanes. The series must codify policy classes (`security-floor`,
    `compatibility-cluster`, `override-seam`) and enforce coordinator-led PR lifecycle with
    mandatory post-open `qa-engineer-agent -> bug-hunter` on every slice.
  - Links:
    - `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2181`
    - `.github/dependabot.yml`
    - `scripts/ci/check_dependabot_python_policy.py`
    - `docs/security/DEPENDENCY_SECURITY_GUARD_WORKFLOW.md:5`
    - `docs/security/DEPENDENCY_SECURITY_GUARD_WORKFLOW.md:64`
    - `docs/DEPENDENCY_MANAGEMENT.md:62`
    - `docs/orchestration/PR_MERGE_WORKFLOW_MATRIX.md:37`
    - `requirements.txt:1`
    - `requirements-dev.txt:1`
    - `requirements-ci-lite.txt:1`
  - DoD:
    - Series packet defines role order, PR slices, and mandatory post-open lane; evidence anchor remains `docs/orchestration/PR_MERGE_WORKFLOW_MATRIX.md:37`
    - Python dependency cluster policy is documented with five-surface coherence rules; evidence anchors remain `docs/security/DEPENDENCY_SECURITY_GUARD_WORKFLOW.md:5`, `docs/security/DEPENDENCY_SECURITY_GUARD_WORKFLOW.md:64`, and `docs/DEPENDENCY_MANAGEMENT.md:62`
    - PR loop for each slice is explicitly artifact-first (`docs/review/PR_<N>_FIXED_MAPPING.md`); evidence anchor remains `docs/orchestration/PR_MERGE_WORKFLOW_MATRIX.md:39`
    - Deferred/security-maturity lanes (SBOM/VEX) remain blocked until existing ledger criteria are met

<a id="ledger-p1-test-hygiene-wave"></a>
- [ ] P1: Test hygiene remediation wave for the main test suite
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (test determinism / CI stability)
  - Target PR: PR-TBD-TEST-HYGIENE-WAVE
  - Status: 🟡 In progress
  - Area: tests / policy guards / CI reliability
  - Finding Type: test isolation and determinism debt
  - Reason (EN): The 13 March 2026 suite review found broad hygiene debt across import determinism, client lifecycle cleanup, env isolation, and timing controls. The work is too large for one fix PR and needs a canonical umbrella item so execution slices stay ordered and guard scope only expands after each cleaned slice is stable.
  - Links:
    - `docs/audit/TEST_SUITE_REVIEW_2026-03-13.md`
    - `tests/AGENTS.md`
    - `docs/ENGINEERING_LESSONS.md`
    - `tests/test_repo_policy_sys_modules.py`
    - `docs/tracking/ISSUE-TESTCLIENT-FACTORY-MIGRATION.md`
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-fastapi-compatibility-gates`
  - Child Items:
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-test-hygiene-risk-first`
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-test-hygiene-client-lifecycle`
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-test-hygiene-env-isolation`
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p2-test-hygiene-finalization`
  - Related History:
    - [FastAPI / Pydantic / Starlette compatibility gates](BACKLOG_LEDGER.md#ledger-p1-fastapi-compatibility-gates)
    - [Repository `sys.modules` mutation guard re-enable](BACKLOG_LEDGER.md#ledger-p1-reenable-sys-modules-guard)
    - [CI nightly test DB schema bootstrap broken](BACKLOG_LEDGER.md#ledger-p0-ci-nightly-test-db-schema-bootstrap)
    - [WebSocket idle-timeout follow-up](BACKLOG_LEDGER.md#ledger-p1-websocket-idle-timeout-follow-up)
  - DoD:
    - Each execution slice lands in its own focused PR with deterministic verification
    - Guard scope expands only after the targeted offender class is clean in that scope
    - Final wave closes only after `make verify` passes on the last cleanup PR

<a id="ledger-p1-test-hygiene-risk-first"></a>
- [ ] P1: Risk-first determinism cleanup for `sys.modules`, builtins import patching, and real sleeps
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR `#1157` (risk-first hygiene slice) -> PR-TBD-TEST-HYGIENE-RISK-FIRST
  - Status: 🟡 In progress
  - Area: tests / import determinism / timing
  - Finding Type: policy and flake remediation
  - Reason (EN): `sys.modules` mutation, `builtins.__import__` patching, and real sleeps create the highest-leverage determinism failures and can be remediated in bounded slices before the larger client/env waves.
  - Links:
    - `docs/audit/TEST_SUITE_REVIEW_2026-03-13.md`
    - `tests/test_repo_policy_sys_modules.py`
    - `tests/test_llm_import_coverage.py`
    - `tests/edges/test_unified_db_small_edges.py`
    - `tests/test_unified_db_coverage.py`
    - `tests/test_business_bayesian_analyzer.py`
  - DoD:
    - Cleaned files no longer use direct `builtins.__import__` patching
    - Cleaned files no longer rely on real `sleep()` to prove behavior
    - Incremental guard scope covers the cleaned non-VIP files
    - Targeted guard/tests for the slice pass locally

<a id="ledger-p1-test-hygiene-client-lifecycle"></a>
- [ ] P1: TestClient lifecycle and session-fixture isolation cleanup
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-TBD-TEST-HYGIENE-CLIENT-LIFECYCLE
  - Status: 📋 Planned
  - Area: tests / FastAPI lifecycle / session cleanup
  - Finding Type: resource lifecycle debt
  - Reason (EN): open-ended `TestClient(...)` usage and stale closeable resources are still present across the suite and need a dedicated wave so the canonical pattern becomes `env first, client second` without mixing in broad env cleanup.
  - Links:
    - `docs/audit/TEST_SUITE_REVIEW_2026-03-13.md`
    - `docs/tracking/ISSUE-TESTCLIENT-FACTORY-MIGRATION.md`
    - `tests/test_no_direct_testclient.py`
    - `tests/conftest.py`
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-test-hygiene-wave`
  - DoD:
    - High-risk `TestClient` offenders migrate to fixture-based or context-managed usage
    - Closeable test resources have deterministic teardown
    - Targeted xdist smoke for touched files passes without stale client/session state

<a id="ledger-p1-test-hygiene-env-isolation"></a>
- [ ] P1: `os.environ` isolation and `setup_method` teardown migration
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-TBD-TEST-HYGIENE-ENV-ISOLATION
  - Status: 📋 Planned
  - Area: tests / env isolation / setup teardown
  - Finding Type: worker pollution debt
  - Reason (EN): direct env mutation is still widespread and must move to `monkeypatch.setenv()` or autouse env fixtures in grouped mechanical passes after the first determinism slice lands.
  - Links:
    - `docs/audit/TEST_SUITE_REVIEW_2026-03-13.md`
    - `tests/AGENTS.md`
    - `docs/ENGINEERING_LESSONS.md`
  - DoD:
    - Touched files no longer write directly to `os.environ[...]` in `setup_method()`
    - Empty or partial env-only teardowns are removed or reduced to real resource cleanup
    - Targeted env-heavy suites pass under deterministic local runs

<a id="ledger-p1-search-observability-foundation"></a>
- [ ] P1: Search observability foundation with trace correlation, synthetic probes, and per-class SLOs
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-TBD-SEARCH-OBSERVABILITY-FOUNDATION
  - Status: 📋 Planned
  - Area: backend / observability / search
  - Finding Type: observability foundation gap
  - Reason (EN): Search and retrieval performance are still hard to diagnose end-to-end. The repo has tracing policy/docs, but it does not yet define a canonical package for correlated HTTP/DB/search traces, daily synthetic probes, and SLOs split by query class.
  - Links:
    - `docs/analytics/README.md`
    - `docs/analytics/METRICS_CATALOG.md`
    - `docs/plan/PR_WS_OBSERVABILITY_TASK_ANALYSIS.md`
  - DoD:
    - Canonical observability doc defines trace correlation, search/query-class tagging, and `X-Trace-Id` response contract if adopted
    - Synthetic probe workflow and per-class latency/error objectives are documented before rollout
    - Search performance debugging path is linked from ops/runbook docs

<a id="ledger-p1-food-data-source-update-preflight"></a>
- [ ] P1: Food data source-update preflight and diff-based ingest guard
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR `#1613` (PR13: `docs(food-data): add per-chain legal review gate`) -> PR #1743 (PR14: `feat(food-data): add recipe dish corpus governance gate`) -> PR #1747 (PR15: `feat(food-data): add preference recipe mapping contract`) -> PR #1768 (PR16: `feat(food-data): close preference recipe mapping review`) -> PR #1771 (PR17: `feat(food-data): add regional catalog identity license gate`) -> PR #1783 (PR18: `feat(food-data): add regional provider terms matrix gate`) -> PR #1793 (PR19: `feat(food-data): add regional source-specific terms gate`) -> PR #1815 (PR20: regional catalog source-specific terms closeout) -> PR #1829 (PR21: regional catalog dedicated legal contract review) -> PR22 (regional catalog dedicated legal contract review closeout)
  - Status: 🚧 USDA/FDC 2026 compatibility preflight lane after PR22 regional catalog dedicated legal contract review closeout
    - Merged: PR1 planning baseline (`#1513`), PR2 tooling baseline (`#1517`), PR3 lineage hardening (`#1532`), PR4 collision policy (`#1531`), PR5 source-onboarding gate (`#1559`), PR6 USDA manifest preflight (`#1563`), PR7 Open Food Facts manifest preflight (`#1572`), PR8 JPTN identity/license gate (`#1577`), PR9 MenuStat replacement gate (`#1590`), PR10 MenuStat source decision (`#1597`), PR11 coverage/source-gap audit (`#1601`), PR12 chain public nutrition governance (`#1609`), PR13 per-chain legal / anti-scraping review (`#1613`), PR14 recipe/dish corpus governance (`#1743`), PR15 preference recipe mapping contract (`#1747`), PR16 preference mapping closeout (`#1768`), PR17 regional catalog identity/license review (`#1771`), PR18 regional provider terms matrix (`#1783`), PR19 regional source-specific terms gate (`#1793`), PR20 regional catalog source-specific terms closeout (`#1815`), and PR21 regional catalog dedicated legal contract review (`#1829`)
  - Area: data ingestion / food catalog / quality
  - Finding Type: upstream data-change readiness gap
  - Reason (EN): USDA Foundation Foods, USDA Branded, USDA FNDDS, Open Food Facts, JPTN Food Facts, restaurant-menu data, and external recipe corpora can change the shape, volume, licensing, and dedupe behavior of ingestible records. The repo does not yet have a canonical preflight contract for source-version discovery, schema diffing, dedupe/mapping collisions, source replacement decisions, storage choice, and rollback before updating the unified food catalog.
  - Links:
    - `docs/orchestration/FOOD_DATA_SOURCE_UPDATE_PREFLIGHT_PR1_PACKET_2026-04-24.md`
    - `docs/orchestration/FOOD_DATA_SOURCE_PREFLIGHT_TOOLING_PR2_PACKET_2026-04-24.md`
    - `docs/orchestration/FOOD_DATA_SOURCE_DEDUPE_COLLISION_PR4_PACKET_2026-04-25.md`
    - `docs/orchestration/FOOD_DATA_SOURCE_ONBOARDING_GATE_PR5_PACKET_2026-04-28.md`
    - `docs/orchestration/FOOD_DATA_USDA_MANIFEST_PREFLIGHT_PR6_PACKET_2026-04-28.md`
    - `docs/orchestration/FOOD_DATA_USDA_FDC_2026_COMPAT_PREFLIGHT_PACKET_2026-06-08.md`
    - `docs/orchestration/FOOD_DATA_OFF_MANIFEST_PREFLIGHT_PR7_PACKET_2026-04-29.md`
    - `docs/orchestration/FOOD_DATA_JPTN_IDENTITY_LICENSE_PR8_PACKET_2026-04-29.md`
    - `docs/orchestration/FOOD_DATA_MENUSTAT_REPLACEMENT_PR9_PACKET_2026-04-30.md`
    - `docs/orchestration/FOOD_DATA_MENUSTAT_SOURCE_DECISION_PR10_PACKET_2026-04-30.md`
    - `docs/orchestration/FOOD_DATA_COVERAGE_SOURCE_GAP_PR11_PACKET_2026-04-30.md`
    - `docs/orchestration/FOOD_DATA_CHAIN_PUBLIC_NUTRITION_PR12_PACKET_2026-04-30.md`
    - `docs/orchestration/FOOD_DATA_PER_CHAIN_LEGAL_ANTI_SCRAPING_PR13_PACKET_2026-04-30.md`
    - `docs/orchestration/FOOD_DATA_RECIPE_DISH_CORPUS_PR14_PACKET_2026-05-13.md`
    - `docs/orchestration/FOOD_DATA_PREFERENCE_RECIPE_MAPPING_PR15_PACKET_2026-05-13.md`
    - `docs/orchestration/FOOD_DATA_PREFERENCE_RECIPE_MAPPING_CLOSEOUT_PR16_PACKET_2026-05-19.md`
    - `docs/orchestration/FOOD_DATA_REGIONAL_CATALOG_IDENTITY_LICENSE_PR17_PACKET_2026-05-19.md`
    - `docs/orchestration/FOOD_DATA_REGIONAL_CATALOG_PROVIDER_TERMS_MATRIX_PR18_PACKET_2026-05-21.md`
    - `docs/orchestration/FOOD_DATA_REGIONAL_CATALOG_SOURCE_SPECIFIC_TERMS_REVIEW_PR19_PACKET_2026-05-21.md`
    - `docs/orchestration/FOOD_DATA_REGIONAL_CATALOG_SOURCE_SPECIFIC_TERMS_CLOSEOUT_PR20_PACKET_2026-05-24.md`
    - `docs/orchestration/FOOD_DATA_REGIONAL_CATALOG_DEDICATED_LEGAL_CONTRACT_REVIEW_PR21_PACKET_2026-05-25.md`
    - `docs/orchestration/FOOD_DATA_REGIONAL_CATALOG_DEDICATED_LEGAL_CONTRACT_REVIEW_CLOSEOUT_PR22_PACKET_2026-05-25.md`
    - `docs/orchestration/FOOD_DATA_SOURCE_CATALOG_PR3_PACKET_2026-04-24.md`
    - `docs/architecture/FOOD_DATA_SOURCE_CATALOG_PR3_2026-04-24.json`
    - `docs/architecture/FOOD_DATA_SOURCE_ONBOARDING_PR5_2026-04-28.json`
    - `docs/architecture/FOOD_DATA_JPTN_IDENTITY_LICENSE_PR8_2026-04-29.json`
    - `docs/architecture/FOOD_DATA_MENUSTAT_REPLACEMENT_PR9_2026-04-30.json`
    - `docs/architecture/FOOD_DATA_MENUSTAT_SOURCE_DECISION_PR10_2026-04-30.json`
    - `docs/architecture/FOOD_DATA_COVERAGE_SOURCE_GAP_PR11_2026-04-30.json`
    - `docs/architecture/FOOD_DATA_CHAIN_PUBLIC_NUTRITION_PR12_2026-04-30.json`
    - `docs/architecture/FOOD_DATA_PER_CHAIN_LEGAL_ANTI_SCRAPING_PR13_2026-04-30.json`
    - `docs/architecture/FOOD_DATA_RECIPE_DISH_CORPUS_PR14_2026-05-13.json`
    - `docs/architecture/FOOD_DATA_PREFERENCE_RECIPE_MAPPING_PR15_2026-05-13.json`
    - `docs/architecture/FOOD_DATA_PREFERENCE_RECIPE_MAPPING_CLOSEOUT_PR16_2026-05-19.json`
    - `docs/architecture/FOOD_DATA_REGIONAL_CATALOG_IDENTITY_LICENSE_PR17_2026-05-19.json`
    - `docs/architecture/FOOD_DATA_REGIONAL_CATALOG_PROVIDER_TERMS_MATRIX_PR18_2026-05-21.json`
    - `docs/architecture/FOOD_DATA_REGIONAL_CATALOG_SOURCE_SPECIFIC_TERMS_REVIEW_PR19_2026-05-21.json`
    - `docs/architecture/FOOD_DATA_REGIONAL_CATALOG_SOURCE_SPECIFIC_TERMS_CLOSEOUT_PR20_2026-05-24.json`
    - `docs/architecture/FOOD_DATA_REGIONAL_CATALOG_DEDICATED_LEGAL_CONTRACT_REVIEW_PR21_2026-05-25.json`
    - `docs/architecture/FOOD_DATA_REGIONAL_CATALOG_DEDICATED_LEGAL_CONTRACT_REVIEW_CLOSEOUT_PR22_2026-05-25.json`
    - `docs/architecture/ADR_FOOD_DATA_SOURCE_UPDATE_PREFLIGHT_2026-04-24.md`
    - `docs/architecture/FOOD_DATABASE_PLATFORM_STRATEGY_v1.md`
    - `docs/legal/EXTERNAL_FOOD_SOURCE_OPERATING_POLICY.md`
    - `core/food_sources/source_preflight.py`
    - `scripts/food_source_preflight.py`
    - `scripts/build_food_db.py`
    - `docs/roadmap/GLOBAL_ROADMAP.md`
    - `app/services/food_store.py`
    - `docs/orchestration/FOOD_DATA_SOURCE_UPDATE_PREFLIGHT_CURRENT.md`
  - DoD:
    - Source-version manifest and source catalog cover USDA Foundation/Branded/FNDDS, Open Food Facts, MenuStat legacy/static, restaurant-menu replacement candidates, recipe/corpus sources, regional catalogs, and unresolved JPTN Food Facts
    - Preflight workflow exists for diffing incoming source changes against the current catalog snapshot; PR2 defines the file-only manifest/diff skeleton before ingest
    - PR3 catalog validation proves MenuStat is non-updating, replacement candidates are explicit, commercial sources require contract review, and unresolved sources remain blocked
    - `source_classification` is validated with allowed values `current`, `legacy_static`, `commercial_contract`, and `unresolved`
    - Dedupe/mapping collision checks are defined before snapshot promotion or PostgreSQL staging
    - Source-onboarding gate defines cache, display, attribution, redistribution, and contract-review decisions before any source-specific ingest
    - USDA Foundation, Branded, and FNDDS have deterministic manifest fixtures that pass source-specific dry-run preflight against PR2, PR3, and PR5 contracts before any USDA ingest lane opens
    - USDA/FDC 2026 compatibility locks Foundation `04/2026`, Branded `04/2026`, Full Download `04/2026`, FNDDS `10/2024` / `2021-2023`, and SR Legacy `04/2018` assumptions into file-only manifests and parser regressions without live API calls, downloads, `DEMO_KEY`, DB writes, DigitalOcean Postgres, SQLite/runtime authority changes, or OpenAPI/client scope
    - Open Food Facts has deterministic full-dump and delta/export-style manifest fixtures that pass source-specific dry-run preflight against PR2, PR3, and PR5 contracts while preserving ODbL attribution and redistribution policy before any OFF ingest lane opens
    - JPTN Food Facts has a deterministic identity/license gate that records missing provider identity, source URL, license, retrieval contract, schema/unit-normalization, attribution, and redistribution evidence while keeping JPTN blocked until verified
    - MenuStat is not treated as an actively updating source; PR9 defines a deterministic replacement-source decision gate that keeps Nutritionix, FatSecret Platform, Spoonacular, and chain public nutrition pages blocked until source-specific legal, contract, cache, attribution, redistribution, freshness, schema, and rollback terms are approved
    - PR10 narrows the PR9 interpretation: FatSecret Platform is explicitly not a PulsePlate project source; MenuStat is archival/reference-only and requires validation before use; chain public nutrition pages are the preferred budget-first research lane but remain manual-evidence-only until legal, anti-scraping, cache, attribution, freshness, schema, screenshot/evidence, and rollback governance is approved
    - Commercial food/recipe API candidates such as Edamam Food Database may be recorded only as adjacent review candidates and must not become source authority, API-call lanes, cache authority, or runtime/ingest surfaces without a dedicated source-specific packet
    - Core product food database authority stays USDA-first; Open Food Facts remains auxiliary and may require a later schema/PostgreSQL review lane because upstream fields/source structure changed, while restaurant menus, dish/recipe databases, and preference-menu planning remain the active unresolved source area
    - PR11 coverage/source-gap audit proves USDA + Open Food Facts cover the product food baseline only at the governance level, records restaurant menus, recipe/dish corpora, regional/local foods, manual evidence, and preference-menu planning as unresolved/deferred gaps, and prevents any gap decision from approving ingest, scraping, paid API use, DB writes, DigitalOcean Postgres, or runtime authority
    - PR12 governs official public chain nutrition pages as manual evidence only: McDonald's, Chipotle, Starbucks, and similar chain pages may be recorded as URL/screenshot evidence for internal legal review, while scraping, automated collection, API calls, downloads, cache authority, redistribution, public dataset claims, ingest, DB writes, DigitalOcean Postgres, and runtime authority remain blocked
    - PR13 records per-chain legal / anti-scraping review requirements for McDonald's, Chipotle, and Starbucks while keeping legal review, anti-scraping, cache, display, attribution, redistribution, freshness, schema, screenshot, and rollback decisions unapproved; recipe/dish corpus governance remains the next separate lane
    - PR14 records recipe/dish corpus governance for Edamam Food Database and Spoonacular while keeping legal review, contract review, paid/API use, cache, display, attribution, redistribution, freshness, schema, rollback, ingest, DB writes, DigitalOcean Postgres, and runtime authority unapproved; preference-to-recipe mapping remains the next separate lane
    - PR15 records preference-to-recipe mapping contract governance while keeping preference labels, recipe text, user preference text, LLM output, public chain evidence, Edamam, Spoonacular, and public menu pages non-authoritative; source use, API calls, paid plans, downloads, scraping, caching, redistribution, ingest, DB writes, DigitalOcean Postgres, runtime authority, product display, and nutrition authority remain unapproved
    - PR16 closes out the PR15 preference-to-recipe mapping contract lane, records operator-provided food-source research artifacts as review context only, preserves USDA + Open Food Facts as the budget-first canonical nutrition baseline, keeps paid/API/scraper/provider work deferred, and selects `regional_catalog_identity_license_review` as the next substantive food-data source governance lane
    - PR17 records regional catalog identity/license review candidates for data.europa.eu / national open-data portals, Kroger, Walmart, Pepesto Grocery, PricesAPI, Yandex EDA, Wildberries, Ozon, and scraping-style providers as evidence-only; source use, API calls, seller or partner API use, paid plans, downloads, scraping, caching, redistribution, ingest, DB writes, DigitalOcean Postgres, runtime authority, product display, and nutrition authority remain unapproved, with next lane set by the PR17 artifact
    - PR18 records the PR17 regional catalog candidate set as a provider terms matrix while keeping every candidate review-only; provider use, API calls, seller or partner API access, paid plans, downloads, scraping, cache authority, redistribution, ingest, DB writes, DigitalOcean Postgres, runtime authority, product display, and nutrition authority remain unapproved, with the next lane set to source-specific regional catalog terms review
    - PR19 records source-specific terms review requirements for the PR18 regional catalog candidate set while keeping every candidate review-only; public terms references are evidence pointers only, and network/API/scraping/download, account access, paid plans, seller or partner API access, provider use, DB writes, cache authority, redistribution, runtime/source authority, product display, and nutrition authority remain unapproved
    - PR20 closes out PR19 source-specific terms review while preserving the exact regional catalog candidate set/order, PR19 merged marker, review-only/no-provider-use posture, low/unverified evidence confidence, and dedicated legal-contract review requirement; network/API/scraping/download, account access, paid plans, seller or partner API access, provider use, DB writes, cache authority, redistribution, runtime/source authority, product display, and nutrition authority remain unapproved, with the next lane set to `regional_catalog_dedicated_legal_contract_review`
    - PR21 records dedicated legal/contract review requirements for the PR20 regional catalog candidate set while keeping every candidate review-only with no legal approval, source use, provider use, API calls, scraping, downloads, account access, paid use, DB writes, cache authority, redistribution, runtime/source authority, product display, or nutrition authority, with the next lane set by the PR21 artifact
    - PR22 closes out PR21 dedicated legal/contract review while preserving PR21/#1829 merge evidence, exact regional catalog candidate set/order, review-only/no-source-or-provider-use posture, low/unverified evidence confidence, and false unsafe flags; no legal approval, source use, provider use, API calls, scraping, downloads, account access, paid use, DB writes, cache authority, redistribution, runtime/source authority, product display, nutrition authority, connector writes, or source authority are approved, with the next lane set by the PR22 artifact
    - DigitalOcean production PostgreSQL load and runtime cutover stay blocked until source preflight, staging proof, rollback, and cutover packet are complete
    - Data-ingest docs and runbooks point to the same preflight source of truth
    - Deferred follow-ups remain separate: minimal `FoodRecord` metadata propagation for `fdc_id` / `brand` / `gtin`, staging/Postgres dry-run loader, governed cutover packet, and Open Food Facts refresh

<a id="ledger-p1-llm-reliability-security-gates"></a>
- [x] P1: LLM reliability and security CI gates for retrieval, faithfulness, prompt-injection, and privacy
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-A5 / PR #1395
  - Status: ✅ Closed. PR #1395 `feat(ai): add PR-A5 runtime gates` merged on `2026-04-12T11:45:35Z` with merge commit `2f8a9af461cec483aa81a774cce7496c6bf65a8a` from branch `feat/pr-a5-runtime-gates`.
  - Area: AI runtime / security / evaluation
  - Finding Type: model-evaluation gate gap
  - Reason (EN): Live GitHub/repo truth proves the dedicated A5 runtime-gate slice already landed in PR #1395. The landed evidence includes the canonical AI runtime gate contract, deterministic gate-bundle launcher, safety hardening, RAG/recursive tests, and review mapping without opening semantic cache or widening public contracts.
  - Links:
    - `docs/security/SECURITY_POSTURE.md`
    - `docs/analytics/README.md`
    - `docs/innovation/INNOVATION_EVALUATION_FRAMEWORK.md`
    - `docs/orchestration/contracts/AI_RUNTIME_GATE_CONTRACT.md`
    - `scripts/orchestration/ai_runtime_gate_bundle.py`
    - `core/insight/philosophy_validator.py`
    - `tests/test_ai_runtime_gate_bundle.py`
    - `tests/test_rag_orchestration.py`
    - `tests/test_recursive_rag.py`
    - `AGENTS.md`
  - DoD:
    - PR #1395 merge evidence is machine-checkable in active roadmap docs
    - Canonical evaluation package defines required retrieval/faithfulness/security/privacy checks and where they run
    - Prompt-injection and untrusted-context posture is covered by deterministic gate-bundle tests
    - LLM outputs used for product copy/coaching pass `philosophy_validator` (BLOCKER = rewrite)
    - AI runtime/runbook docs link to the same gate source instead of ad-hoc evaluation notes
    - Semantic-cache markers remain `closed / false / false / true`; no semantic cache, Redis/GPTCache, GraphRAG, ContextManifest, DB persistence, public route, OpenAPI, DTO, provider, or default activation scope is implied by this closeout

<a id="ledger-p1-rag-release-gates-lane"></a>
- [ ] P1: PulsePlate RAG release-gates lane and artifact contract
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR #1484
  - Status: In progress on the isolated release-gates lane (`PR #1484`)
  - Canonical contract note: Until a dedicated seam ADR exists, the authoritative contract for artifact-pack scope, CI behavior, and persistence boundaries lives in `docs/orchestration/PULSEPLATE_RAG_RELEASE_GATES_TASK_PACKET_2026-04-20.md` and `docs/evals/PULSEPLATE_RAG_RELEASE_GATES.md`; follow-on work must cite those files instead of inventing a parallel storage or dashboard truth.
  - Area: AI / RAG / Insight / evaluation
  - Finding Type: internal release-gate lane
  - Reason (EN): PulsePlate now has real RAG orchestration, runtime tracing, input safety, and philosophy validation hooks, but it still lacked one canonical internal lane that evaluates retrieval quality, grounding, calibration, and fail-closed safety before merge/release. This item tracks the repo-owned notebook + deterministic runner baseline and freezes the artifact/schema contract before any persistent dashboard work starts.
  - Links:
    - `notebooks/pulseplate_rag_release_gates.ipynb`
    - `scripts/evals/run_rag_release_gates.py`
    - `docs/evals/PULSEPLATE_RAG_RELEASE_GATES.md`
    - `docs/orchestration/PULSEPLATE_RAG_RELEASE_GATES_TASK_PACKET_2026-04-20.md`
    - `core/rag/orchestration.py`
    - `core/ai/insight_runtime.py`
    - `app/services/insight_runtime.py`
    - `app/security/agent_input_guard.py`
    - `core/insight/philosophy_validator.py`
  - DoD:
    - Notebook, sample fixture, deterministic runner, and canonical docs are committed
    - v1 source of truth is the gitignored artifact pack under `artifacts/rag_eval/<experiment_id>/`
    - CI exposes `gate_report.md` and a compact markdown summary without introducing a new database
    - Trace/run schema is explicit enough to mirror later into PostgreSQL without reworking evaluation logic
    - Persistence guidance is explicit: PostgreSQL is the future canonical store, Cloudflare may be access-only, and D1 is not introduced for this lane
    - Strict weekly/manual execution can inject a curated dataset via workflow input or repo variable without relying on an untracked file in the checkout
  - Blockers / Exit criteria:
    - Any PostgreSQL-backed history or dashboard promotion requires a separate ADR-backed follow-up lane; this PR intentionally keeps history artifact-only
    - Weekly curated datasets remain operational inputs and must stay outside git until a governed dataset-management contract is approved
<a id="ledger-p1-evaluation-validity-substrate"></a>
- [ ] P1: Evaluation validity substrate for invariance, mutation, and worst-case reporting
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-TBD (`evals/evaluation-validity-substrate`)
  - Status: In progress
  - Area: evals / RAG / judgment / measurement science
  - Finding Type: measurement-validity gap
  - Reason (EN): PulsePlate already has deterministic eval governance, RAG release gates, offline RAGAS, and judgment replay/adjudication, but lacks a measurement-science substrate for item-level validity, invariance, benchmark mutation, and worst-case reporting. This PR adds the foundation layer without changing production runtime.
  - Links:
    - `docs/evals/PULSEPLATE_EVAL_VALIDITY_CONTRACT.md`
    - `scripts/evals/eval_validity_contract.py`
    - `scripts/evals/run_eval_validity.py`
    - `data/evals/pulseplate_rag_eval_validity_sample.jsonl`
    - `data/evals/pulseplate_judgment_eval_validity_sample.jsonl`
    - `tests/evals/test_eval_validity_contract.py`
    - `tests/evals/test_run_eval_validity.py`
  - DoD:
    - Canonical item/variant schema exists
    - Deterministic validity runner exists
    - Curated RAG and judgment sample fixtures exist
    - Validity report includes invariance_score, mutation_drop, worst_case_error_rate, item_instability_index, slice_support, and unstable_items
    - Tests cover parser, metrics, runner, malformed input, and deterministic output
    - Existing release-gate PASS/NO-GO vocabulary is preserved
    - No Opus/Claude runtime integration, `.claude/`, MCP, production API, frontend, iOS, billing, OpenAPI, or App Store changes
<a id="ledger-p1-rag-release-gate-validity-sidecar"></a>
- [ ] P1: RAG release-gate validity sidecar integration
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-TBD (`evals/rag-release-gate-validity-sidecar`)
  - Status: In progress
  - Area: evals / RAG / release gates / measurement science
  - Finding Type: validity-artifact integration gap
  - Reason (EN): PR #1632 added the evaluation-validity substrate but intentionally deferred full integration with RAG release-gate artifacts. This PR adds optional validity sidecar emission to the RAG release-gate runner while preserving existing threshold results and PASS/NO-GO decisions.
  - Links:
    - `docs/evals/PULSEPLATE_RAG_RELEASE_GATES.md`
    - `docs/evals/PULSEPLATE_EVAL_VALIDITY_CONTRACT.md`
    - `scripts/evals/rag_release_gate_validity.py`
    - `scripts/evals/run_rag_release_gates.py`
    - `tests/evals/test_rag_release_gate_validity_sidecar.py`
  - DoD:
    - RAG release-gate runner emits validity-compatible item-level sidecar JSONL
    - RAG release-gate runner emits validity report sidecar JSON
    - Existing threshold_results remain canonical
    - Existing PASS/NO-GO decision logic is unchanged
    - Tests prove sidecar generation and no threshold/decision drift
    - Docs explain sidecar semantics and limitations
    - No runtime/API/frontend/iOS/billing/OpenAPI/App Store/Claude/Opus/MCP changes
<a id="ledger-p2-mlflow-required-check-integration"></a>
- [ ] P2: MLflow-backed eval identity integration without required-check drift
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR-TBD (`evals/mlflow-identity-integration`)
  - Status: Deferred
  - Area: evals / RAG / release gates / ML identity
  - Finding Type: external eval-source integration risk
  - Reason (EN): The RAG release-gates runner already emits canonical
    `metrics_summary.json`, `threshold_results`, `release_decision`, and
    `rag_gate_result.json`. Promoting an external MLflow tracking run directly
    into a required PR check would introduce secret, network, run-selection, and
    source-of-truth risk before the repo has an approved tracking URI, retention
    policy, and deterministic local fallback.
  - Links:
    - `docs/evals/PULSEPLATE_RAG_RELEASE_GATES.md`
    - `docs/release/RAG_GATE_RESULT_EXPORT_CONTRACT.md`
    - `scripts/evals/run_rag_release_gates.py`
    - `tests/test_rag_release_gates_runner.py`
    - `docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md`
  - DoD:
    - MLflow integration is optional identity metadata over repo-native
      `rag_gate_result.json`, not a replacement for `threshold_results` or
      `release_decision`
    - An approved tracking URI, secret policy, network/SLA posture, and artifact
      retention policy are documented before any CI integration
    - Deterministic local fallback exists and tests prove missing/unreachable
      MLflow does not block ordinary repo-native eval validation
    - Required-check status is not enabled until reliability is proven in a
      non-required lane and branch-protection impact is reviewed
    - The integration does not open the semantic-cache gate, add runtime
      `/insight` wiring, require provider calls, or persist raw prompts,
      responses, user context, secrets, or local paths
<a id="ledger-p1-judgment-validity-sidecar"></a>
- [ ] P1: Judgment replay validity sidecar integration
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-TBD (`evals/judgment-validity-sidecar`)
  - Status: In progress
  - Area: evals / judgment / adjudication / measurement science
  - Finding Type: validity-artifact integration gap
  - Reason (EN): PR #1632 added the evaluation-validity substrate and PR #1648 integrated RAG release-gate sidecars. The next rollout step in `PULSEPLATE_EVAL_VALIDITY_CONTRACT.md` is judgment eval outcome export, so judgment replay/adjudication should emit item-level validity-compatible sidecars while preserving existing promote/defer/discard semantics.
  - Links:
    - `docs/evals/PULSEPLATE_EVAL_VALIDITY_CONTRACT.md`
    - `docs/orchestration/JUDGMENT_ADJUDICATION_SUBLANE_PROTOCOL.md`
    - `core/judgment_eval.py`
    - `scripts/evals/judgment_validity.py`
    - `scripts/evals/eval_validity_contract.py`
    - `scripts/orchestration/judgment_eval.py`
    - `tests/evals/test_judgment_validity_sidecar.py`
    - `tests/test_judgment_eval.py`
  - DoD:
    - Judgment replay/eval can emit validity-compatible item-level sidecar JSONL
    - Judgment replay/eval can emit validity report sidecar JSON
    - Existing claim taxonomy remains canonical
    - Existing claim-to-evidence semantics remain canonical
    - Existing promote/defer/discard decision logic is unchanged
    - Tests prove sidecar generation and no decision drift
    - Docs explain sidecar semantics and limitations
    - No runtime/API/frontend/iOS/billing/OpenAPI/App Store/Claude/Opus/MCP changes
<a id="ledger-p1-judgment-invariance-mutation-fixtures"></a>
- [ ] P1: Judgment invariance and mutation fixture families
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-TBD (`evals/judgment-invariance-mutation-fixtures`)
  - Status: In progress
  - Area: evals / judgment / invariance / mutation / measurement science
  - Finding Type: robustness-coverage gap
  - Reason (EN): PR #1656 added judgment validity sidecar artifacts, but judgment datasets still need deterministic invariance and mutation variant families so the validity report measures robustness instead of canonical-only coverage.
  - Links:
    - `docs/evals/PULSEPLATE_EVAL_VALIDITY_CONTRACT.md`
    - `docs/orchestration/JUDGMENT_ADJUDICATION_SUBLANE_PROTOCOL.md`
    - `data/evals/pulseplate_judgment_eval_validity_variants.jsonl`
    - `scripts/evals/judgment_validity.py`
    - `tests/evals/test_judgment_validity_variant_families.py`
  - DoD:
    - Judgment fixture set includes canonical, invariance, and mutation rows
    - Fixture rows are deterministic and curated
    - No LLM-generated fixtures are introduced
    - Validity report shows non-trivial invariance/mutation coverage
    - Tests prove deterministic report output and stable unstable_items
    - Existing claim taxonomy and promote/defer/discard logic remain unchanged
    - No runtime/API/frontend/iOS/billing/OpenAPI/App Store/Claude/Opus/MCP changes
<a id="ledger-p1-rag-invariance-mutation-fixtures"></a>
- [ ] P1: RAG invariance and mutation fixture families
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-TBD (`evals/rag-invariance-mutation-fixtures`)
  - Status: In progress
  - Area: evals / RAG / release gates / invariance / mutation / measurement science
  - Finding Type: robustness-coverage gap
  - Reason (EN): The RAG validity sidecar currently emits canonical-only rows, which means invariance_score and mutation_drop cannot measure robustness. This slice adds deterministic RAG invariance and mutation fixtures so the validity report measures robustness while preserving RAG release-gate PASS/NO-GO decisions.
  - Links:
    - `docs/evals/PULSEPLATE_EVAL_VALIDITY_CONTRACT.md`
    - `docs/evals/PULSEPLATE_RAG_RELEASE_GATES.md`
    - `data/evals/pulseplate_rag_release_gate_validity_variants.jsonl`
    - `scripts/evals/rag_release_gate_validity.py`
    - `scripts/evals/run_rag_release_gates.py`
    - `tests/evals/test_rag_release_gate_validity_variant_families.py`
    - `tests/evals/test_rag_release_gate_validity_sidecar.py`
  - DoD:
    - RAG fixture set includes canonical, invariance, and mutation rows
    - Fixture rows are deterministic and curated
    - No LLM-generated fixtures are introduced
    - Validity report shows non-trivial invariance/mutation coverage
    - Tests prove deterministic report output and stable unstable_items
    - Existing RAG release-gate thresholds remain unchanged
    - Existing PASS/NO-GO logic remains unchanged
    - No runtime/API/frontend/iOS/billing/OpenAPI/App Store/Claude/Opus/MCP changes
<a id="ledger-p1-knowledge-promotion-from-validated-rag"></a>
- [x] P1: Knowledge contracts and promotion from validated RAG evidence
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-K1
  - Status: Closed by PR-K1 docs/review closeout after runtime seam merge via PR `#1483` on `2026-04-20`.
    Delayed-closeout exception: the docs-only follow-up PR `#1776` was opened on `2026-05-20`, one month after the merge, because the same-day/next-working-day handoff required by `AGENTS.md` was missed during the adjacent AI-runtime, semantic-cache, and philosophy-governance cutover; this closeout records the exception with both dates for auditability.
  - Area: AI runtime / knowledge / retrieval orchestration
  - Finding Type: bounded knowledge-promotion contract gap
  - Reason (EN): Before PR `#1483`, the AI runtime had deterministic retrieval diagnostics, bounded `core/ai/*` ownership, and request-local recursive optimization caches, but did not expose a first-class internal fact-promotion contract separated from retrieval artifacts. PR `#1483` closed that gap as a bounded post-A5 follow-up without widening into semantic cache or DB/storage rollout.
  - Closeout evidence:
    - Runtime seam merged: PR `#1483`, `2026-04-20`
    - Deferred PR `#1483` test-helper return annotations resolved in `tests/test_remaining_modules.py`
    - Review-governance reconciliation remains recorded in `docs/review/PR_1483_FIXED_MAPPING.md`
    - Role-agent and engineering lessons were updated for AI/RAG/cache governance closeout failures
    - Semantic-cache gate markers remain `closed / false / false / true`
  - Links:
    - `docs/orchestration/WAVE6_K1_KNOWLEDGE_PROMOTION_PACKET_2026-04-19.md`
    - `docs/orchestration/contracts/AI_RUNTIME_GATE_CONTRACT.md`
    - `docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md`
    - `docs/roadmap/PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md`
    - `core/ai/insight_runtime.py`
    - `core/rag/orchestration.py`
    - `core/insight/philosophical_runtime.py`
    - `app/services/insight_application_service.py`
    - `docs/memory/kpp_knowledge_promotion_pipeline.md`
    - `AGENTS.md`
  - DoD:
    - A bounded `core/knowledge/*` internal subdomain exists for knowledge contracts, policy, promotion, and store protocol only
    - `prepare_insight_runtime(...)` owns the canonical knowledge-policy seam for runtime execution
    - Promotion candidates are derived only from validated RAG evidence that survives orchestration and fail closed on degraded paths or insufficient confidence
    - `legacy_app.py`, `app/routers/*`, OpenAPI, and public response DTOs remain unchanged
    - No DB migration, Redis/GPTCache, or semantic-cache rollout is introduced in this slice
    - Deterministic tests cover promotion allow/deny behavior, supersession rules, and the invariant that request-local recursive caches never become persistent knowledge

<a id="ledger-p1-verification-registry-admission"></a>
- [x] P1: Verification registry and verify-before-write admission invariant
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-V1
  - Status: Closed via PR #1491 on 2026-04-22; merged commit `ce024e7cdca3ec94bbffb095e050010a8198e792` from `codex/ai-verification-registry-v1`. Closeout reconciliation is tracked in `codex/ai-verification-registry-v1-closeout`.
  - Area: AI runtime / verification / knowledge admission
  - Finding Type: verification-bundle admission closeout
  - Reason (EN): `main` now has the bounded K1 knowledge seam, deterministic recursive verification diagnostics, philosophical runtime verification/falsification logic, and a canonical `core/verification/` registry/bundle path. PR-V1 landed verify-before-write admission for knowledge promotion without widening into semantic cache, DB persistence, or public contract changes. Later cache/action gates must reuse this admission truth only after their dedicated gates open.
  - Delayed closeout: PR #1491 merged on 2026-04-22 before this ledger item was reconciled. This closeout records repo/GitHub truth, updates stale review/roadmap state, and does not duplicate the already-landed `core/verification/*` implementation.
  - Links:
    - `docs/orchestration/WAVE6_V1_VERIFICATION_REGISTRY_PACKET_2026-04-21.md`
    - `docs/orchestration/WAVE6_K1_KNOWLEDGE_PROMOTION_PACKET_2026-04-19.md`
    - `docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md`
    - `docs/roadmap/PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md`
    - `core/verification/`
    - `core/knowledge/promotion.py`
    - `core/rag/orchestration.py`
    - `core/insight/philosophical_runtime.py`
    - `app/services/insight_application_service.py`
    - `AGENTS.md`
  - DoD:
    - `core/verification/*` exists as the canonical internal artifact/bundle registry
    - Existing recursive and philosophical verification signals are reused, not reimplemented as a parallel validation system
    - Knowledge writes require an admissible verification bundle
    - Public routes, OpenAPI, response DTOs, and storage rollout remain unchanged
    - Semantic cache, Redis/GPTCache, GraphRAG, and ContextManifest remain out of scope
    - Deterministic tests cover bundle materialization and denied/allowed write admission paths

<a id="ledger-p1-evidence-graph-runtime"></a>
- [ ] P1: Evidence Graph Runtime umbrella
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (AI runtime governance / evidence lineage)
  - Target PR: PR-E0 (`codex/evidence-graph-runtime-umbrella`) -> PR-E1/E2/E3/E4/E5; PR #1884 baseline: Verification Bundle Provenance Attestation v1; PR #1887 baseline: Verification Provenance Admission Report v1; PR #1892 baseline: Semantic Cache Offline Admission Runner v1; current follow-up: Semantic Cache Shadow Admission Harness v1
  - Area: AI runtime / RAG / evals / knowledge promotion / advisory memory
  - Finding Type: asset-lineage and replay-governance gap
  - Status: PR-E5 advisory wiki evidence bridge merged; E0/E1/E2/E3/E4/E5 are baseline, #1666/#1667 eval-sidecar hardening is baseline, #1676 source-artifact path hardening is baseline, SC-G5 closed via PR #1742 `feat(ai-runtime): add semantic-cache backend selection contract` merged on `2026-05-16T21:03:48Z` with merge commit `cb1db8b40141817b3ca856de570b8fc02e2ae9fa`; PR #1884 adds internal-only `VerificationBundle` provenance digests/counts; PR #1887 adds a deterministic internal Verification Provenance Admission Report v1 guard; PR #1892 adds a deterministic Semantic Cache Offline Admission Runner v1 report over SC-G2/SC-G3/SC-G4/SC-G5; current follow-up adds a deterministic Semantic Cache Shadow Admission Harness v1 report that projects those decisions onto synthetic `/insight`, RAG, and philosophical runtime verification path labels while semantic cache remains blocked behind a dedicated gate with machine-checkable closed markers
  - Remove-by: 2026-06-30
  - Reason (EN): PulsePlate already has strong RAG runtime, verification, knowledge-promotion, eval-gate, advisory-wiki, and plugin/control-plane foundations, but evidence-bearing artifacts are still governed mostly through task packets, gate outputs, and lane-specific docs rather than one asset/evidence graph. This umbrella freezes the rail boundaries and PR train needed to make eval runs, context bundles, verification bundles, knowledge candidates, knowledge records, and gate reports first-class assets with lineage, idempotency, replay, fingerprints, policy versions, and admission decisions.
  - Links:
    - `docs/roadmap/EVIDENCE_GRAPH_RUNTIME_EPIC.md`
    - `docs/roadmap/PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md`
    - `docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md`
    - `docs/orchestration/PULSEPLATE_RAG_RELEASE_GATES_TASK_PACKET_2026-04-20.md`
    - `docs/orchestration/WAVE6_K1_KNOWLEDGE_PROMOTION_PACKET_2026-04-19.md`
    - `docs/orchestration/WAVE6_V1_VERIFICATION_REGISTRY_PACKET_2026-04-21.md`
    - `docs/orchestration/KARPATHY_ADVISORY_WIKI_UMBRELLA_S0_PACKET_2026-04-24.md`
    - `AGENTS.md`
  - DoD:
    - One canonical Evidence Graph Runtime epic doc exists and defines the PR-E0 -> PR-E5 train
    - Rail A product runtime, Rail B1 advisory wiki / compiled memory, and Rail B2 plugin/control-plane boundaries are explicit
    - Semantic cache remains blocked until evidence asset lineage, replay-safe promotion, metadata admission gates, observability, false-hit guardrails, rollout contract, current-head CI governance, and a dedicated gate-open PR exist
    - Downstream PR acceptance criteria cover asset registry, eval event schema, promotion ledger/replay, active metadata admission, and advisory wiki evidence bridge
    - PR-E0 remains docs/governance only with no public API, DB migration, endpoint, OpenAPI, billing, provider, semantic-cache, GraphRAG, or user-facing runtime behavior change
    - PR-E2 adds a deterministic schema-only eval event contract and documentation without adding runtime behavior, OpenAPI changes, DB migration, semantic cache, GraphRAG, advisory wiki authority, or promotion/replay logic
    - PR-E3 adds deterministic promotion ledger and dry-run replay contracts without adding runtime behavior, OpenAPI changes, DB migration, semantic cache, GraphRAG, advisory wiki authority, eval runners, or persistent writers
    - PR-E4 adds deterministic `allow_execute`, `allow_promote`, and `allow_serve` metadata admission contracts without adding runtime behavior, OpenAPI changes, DB migration, semantic cache, GraphRAG, advisory wiki authority, eval runners, or side effects
    - PR-E5 links existing advisory wiki artifacts to advisory evidence assets and advisory admission metadata without adding runtime behavior, OpenAPI changes, DB migration, semantic cache, GraphRAG, wiki compiler rewrites, runtime rail mapping, eval runners, or product-serving authority
    - Verification Bundle Provenance Attestation v1 adds internal-only redacted digest/count metadata to existing `VerificationBundle` decisions without changing admission authority, public DTOs, OpenAPI, DB persistence, providers, frontend, iOS, semantic cache, GraphRAG, Slack/operator authority, or runtime-serving behavior
    - Verification Provenance Admission Report v1 adds a deterministic internal report/schema/validator for redacted `VerificationBundle` provenance path coverage without changing admission authority, public DTOs, OpenAPI, DB persistence, providers, frontend, iOS, semantic cache, GraphRAG, Slack/operator authority, or runtime-serving behavior
    - Semantic-cache gate reconciliation keeps the gate closed with deterministic markers and a CI checker so E1-E5 cannot be misread as cache approval
    - SC-G1 semantic-cache rollout gate contract defines the future gate-open criteria, rollout sequence, false-hit risk model, observability, kill switch, and blocked surfaces while keeping semantic-cache markers closed
    - SC-G2 exact/fuzzy cache scaffold adds deterministic lexical matching contracts and guards while preserving closed semantic-cache markers, with no runtime serving, embeddings, Redis/GPTCache, vector search, provider changes, `/insight` wiring, DB, FastAPI, or OpenAPI changes
    - SC-G3 cache observability and false-hit harness adds offline audit events, negative controls, metric contracts, stop rules, rollback thresholds, and kill-switch modeling while preserving closed semantic-cache markers, with no runtime serving, embeddings, Redis/GPTCache, vector search, provider changes, `/insight` wiring, DB, FastAPI, or OpenAPI changes
    - SC-G4 bounded `/insight` semantic-cache experiment adds a deterministic, metadata-only, off-by-default, request-disableable, kill-switchable decision layer while preserving closed semantic-cache markers, with no runtime serving, Redis/GPTCache, embeddings, vector search, provider calls, DB, FastAPI, OpenAPI, or `/insight` route wiring changes
    - SC-G5 semantic-cache backend selection contract adds a deterministic, offline, label-only backend evaluation matrix while preserving closed semantic-cache markers, with Redis/GPTCache represented only as candidate labels and no runtime serving, backend clients, connection strings, provider calls, DB, FastAPI, OpenAPI, embeddings, vector search, or `/insight` route wiring changes
    - Semantic Cache Offline Admission Runner v1 composes SC-G2 exact/fuzzy, SC-G3 observability/false-hit, SC-G4 bounded insight eligibility, and SC-G5 label-only backend context into a deterministic offline report/schema/validator with safe IDs, fingerprints, labels, reason codes, score bps, stop-rule decisions, and `no_selection` backend context only, while preserving closed semantic-cache markers and adding no cache read/write/serving, DB, Redis/GPTCache clients, embeddings, vector search, provider calls, OpenAPI, frontend, iOS, Slack, GraphRAG, or `/insight` route wiring changes
    - Semantic Cache Shadow Admission Harness v1 projects the offline runner decisions onto synthetic `/insight`, RAG, degraded-retrieval, verification-disabled, missing/blocked bundle, philosophical runtime, and mismatch path labels with safe fingerprints, provenance coverage labels, freshness labels, reason codes, and `shadow_report_only` final status, while preserving closed semantic-cache markers and adding no runtime/cache authority, public API, OpenAPI, DB, Redis/GPTCache clients, embeddings, vector search, provider calls, frontend, iOS, Slack, GraphRAG, or `/insight` route wiring changes

<a id="ledger-p1-apple-server-api-migration"></a>
- [ ] P1: Apple receipt verification migration to App Store Server API
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-TBD-APPLE-SERVER-API-MIGRATION
  - Status: Prepared follow-on only; must not overtake still-open P0 release-truth items
  - Canonical contract note: This ledger entry owns the full precondition, wire-compatibility, and temporary-fallback contract for the lane. Sequencing packets and execution docs should point here rather than redefine the complete contract list.
  - Area: backend / payments / provider integration
  - Finding Type: provider modernization
  - Reason: The current PR uses classic `verifyReceipt` only as a transitional compatibility path; Apple-recommended signed transaction / App Store Server API validation remains mandatory follow-up work. This lane is P1 provider modernization and must not overtake still-open P0 release-truth work.
  - Links:
    - `docs/contracts/PAYMENTS_RU_BY_IOS_BASELINE.md`
    - `app/services/payments_activation.py`
    - `docs/roadmap/PulsePlate_P0_P1_Execution_Document_2026-03-30.md#12-featbilling-migrate-apple-verification-to-app-store-server-api`
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p0-billing-apple-verify`
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p0-billing-entitlement-routing`
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p0-web-entitlement-truth`
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p0-eu-compliance-control-plane-follow-through`
  - DoD:
    - Apple verification moves off classic `verifyReceipt` onto the approved server-side successor flow
    - Existing verification contract remains backward-compatible for downstream activation
    - Provider migration paths are covered with deterministic tests and rollout notes
    - Public endpoint `/api/v1/billing/apple/verify-receipt`, existing DTOs, and iOS transport contract remain unchanged unless a separate versioned migration explicitly says otherwise
    - Server-side identifier derivation from the current receipt path is proven, or the legacy path remains available as an explicit temporary fallback without forcing client payload changes in the same PR
    - Any temporary legacy fallback includes rollback notes, exit criteria, backlog link, and a remove-by date

<a id="ledger-p1-ios-subscription-orchestration"></a>
- [ ] P1: iOS SubscriptionManager orchestration follow-through
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-TBD-IOS-SUBSCRIPTION-MANAGER
  - Status: 💤 Superseded by `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-ios-subscription-manager`
  - Area: ios / payments / orchestration
  - Finding Type: client orchestration gap
  - Reason: Backend verify is now separated cleanly, but the iOS thin client still needs explicit orchestration for purchase -> verify -> activation handoff without embedding billing truth on-device. The canonical surviving tracker is `ledger-p1-ios-subscription-manager`; this entry remains as an audit bridge from the billing wave only.
  - Links:
    - `docs/contracts/PAYMENTS_RU_BY_IOS_BASELINE.md`
    - `app/routers/billing.py`
    - `app/services/payments_activation.py`
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p0-billing-apple-verify`
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-ios-subscription-manager`
  - DoD:
    - Follow the canonical DoD recorded under `ledger-p1-ios-subscription-manager`

<a id="ledger-p1-ios-storekit-products"></a>
- [x] P1: iOS StoreKit products contract and setup baseline
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR #1172 (contract baseline landed) -> PR #1189 (operational/setup close-out)
  - Status: ✅ Contract baseline merged in PR #1172; operational/setup close-out merged in PR #1189 and future setup work must use the canonical checklist
  - Area: ios / release / billing operations
  - Finding Type: store configuration readiness
  - Reason (EN): PR #1172 already versioned the canonical StoreKit product IDs and setup baseline in-repo. The remaining B3 work was to consolidate the surviving operational release/setup residue into one canonical checklist and make all Batch B follow-through docs point back to that contract instead of drifting into parallel setup notes after PR #1185 / PR #1187.
  - Links:
    - `docs/orchestration/TOP20_PR_RECOVERY_TASK_PACKETS_2026-03-08.md`
    - `docs/roadmap/P0_MASTER_CHECKLIST_PHASE_FIT_TRIAGE_2026-03-05.md`
    - `docs/contracts/PAYMENTS_RU_BY_IOS_BASELINE.md`
    - `docs/contracts/IOS_STOREKIT_PRODUCTS_CONTRACT.md`
    - `docs/IOS_API_INTEGRATION.md`
    - `docs/roadmap/PulsePlate_Master_Index_A-E.md`
  - DoD:
    - Canonical StoreKit product identifiers and one operational release checklist are versioned in-repo
    - Billing/runtime follow-through references the same product contract without client-side drift
    - Future TestFlight / App Store setup work has one explicit canonical checklist instead of fragmented docs

<a id="ledger-p1-mobile-secret-conformance"></a>
- [x] P1: Mobile secret storage conformance (iOS Keychain now, Android Keystore deferred)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (mobile security correctness)
  - Target PR: PR #1179 (`feat/pr-6-ios-keychain-conformance`)
  - Status: ✅ Merged (PR #1179, 2026-03-16)
  - Reason (EN): Master checklist item #5. PR #1179 completed: Keychain-only runtime, test-surface coverage, setup docs cleanup, guard tests.
  - Links:
    - docs/review/PR_1179_FIXED_MAPPING.md
    - docs/pr/PR-6_HANDOFF.md
    - docs/roadmap/P0_MASTER_CHECKLIST_PHASE_FIT_TRIAGE_2026-03-05.md
    - ios/PulsePlate/Services/KeychainStore.swift
    - ios/PulsePlate/Services/ProKeyProvider.swift
    - ios/PulsePlateTests/Guards/ThinClientGuardsTests.swift
    - ios/PulsePlateTests/Services/ProKeyProviderTests.swift
    - ios/PulsePlateTests/Services/KeychainStoreTests.swift
    - ios/SHOPPING_LIST_SETUP.md
  - DoD:
    - iOS runtime secret paths are verified to use Keychain storage only
    - Default local and CI iOS test surfaces include Keychain provider roundtrip/ignore-env coverage
    - Current-state iOS setup docs no longer advertise `PRO_API_KEY` or placeholder fallback as runtime auth truth
    - Guard tests prevent regression to insecure storage

<a id="ledger-p1-diet-flags-contract-sync"></a>
- [ ] P1: Diet flags contract sync across schemas and clients
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-TBD-DIET-FLAGS-CONTRACT-SYNC
  - Status: 📋 Planned
  - Area: frontend / backend / iOS contracts
  - Finding Type: contract consistency
  - Reason (EN): Diet-flag semantics are product-facing and cross-client. A dedicated sync item keeps the enum/normalization surface canonical instead of letting drift hide inside frontend or generated-type follow-ups.
  - Links:
    - `docs/roadmap/P0_MASTER_CHECKLIST_PHASE_FIT_TRIAGE_2026-03-05.md`
    - `docs/contracts/API_CANONICAL_MAP.md`
    - `frontend`
    - `ios/PulsePlate`
  - DoD:
    - One canonical diet-flags normalization table is used across backend schemas and clients
    - Generated or mirrored client types remain aligned with backend truth
    - Deterministic regression tests cover the shared contract

- [ ] P1: `vector_rag` SQL assembly refactor (remove raw SQL formatting debt)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (security + maintainability)
  - Target PR: PR-TBD-VECTOR-RAG-SQL-REFACTOR
  - Status: 📋 Planned
  - Reason: Raw SQL string assembly in vector retrieval path increases maintenance and security review overhead; contract should move to parameterized/ORM-safe composition.
  - Links:
    - `docs/contracts/RAG_CONTRACT.md`
    - `docs/audit/RAG_IMPLEMENTATION_AND_AGENT_KNOWLEDGE_AUDIT.md`
    - `core/rag/vector_rag.py`
    - `tests/test_vector_rag.py`
  - DoD:
    - Query assembly uses parameterized/ORM-safe path (no ad-hoc SQL string formatting)
    - Existing vector retrieval behavior remains contract-compatible
    - Security/static analysis checks pass without local suppressions for this path


<a id="ledger-p1-wave6-ai-runtime-umbrella"></a>
- [ ] P1: Wave 6 AI runtime umbrella
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (AI differentiation sequencing)
  - Target PR: PR-S0
  - Area: AI / roadmap / execution spine
  - Finding Type: epic normalization
  - Status: 📋 Planned
  - Reason (EN): Wave 6 already exists in the execution document, but the backlog still lacks one umbrella entry that binds runtime AI sequencing into a single governed PR spine. Without an umbrella, later agents keep reconstructing the order from scattered items and risk mixing runtime AI work with the advisory workforce/wiki lane.
  - Links:
    - `docs/roadmap/PulsePlate_P0_P1_Execution_Document_2026-03-30.md`
    - `docs/roadmap/PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md`
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p0-insight-fallback-chain`
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-pro-monthly-quota-ledger-reconciliation`
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-rag-hardening-followthrough`
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-ai-bounded-context-packet`
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-ai-bounded-context-extraction`
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-llm-reliability-security-gates`
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-philosophical-logic`
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-recursive-methods`
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-scientific-reliability-pipeline`
  - DoD:
    - One umbrella item exists for the product AI runtime rail
    - Wave 6 order is explicit and pointer-based through `A1b -> A5` for the current closure cycle
    - Runtime AI rail is kept separate from the Karpathy workforce/wiki rail
    - Existing child items remain authoritative and are not duplicated as competing SoT

<a id="ledger-p1-security-floor-unblock-seam"></a>
- [ ] P1: Temporary `security-floor` unblock seam
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (security governance / docs-lane unblock)
  - Target PR: PR `#1433`
  - Area: docs / dependency security / merge governance
  - Finding Type: temporary seam governance
  - Status: 🟡 In progress (`PR #1433` adds the canonical packet/ADR/backlog anchors for the seam)
  - Reason (EN): When a dependency advisory blocks a docs/governance lane, the repo may use one narrow `security-floor` unblock only for governed dependency manifests, lock regeneration, schema/guard synchronization, and CVE evidence. Without one canonical backlog item, that temporary exception drifts between packets and roadmap docs. (RU: Если dependency advisory блокирует docs/governance lane, репозиторий может использовать только один узкий `security-floor` unblock для governed dependency manifests, lock regeneration, schema/guard synchronization и CVE evidence. Без единого backlog-item это временное исключение начинает расходиться между packet и roadmap docs.)
  - Links:
    - `docs/orchestration/DEPENDABOT_ALERTS_110_113_REMEDIATION_TASK_PACKET_2026-04-16.md:16-21,64-70`
    - `docs/security/CVE-2026-40347-python-multipart.md:17-25`
    - `docs/security/GHSA-39q2-94rc-95cp-dompurify.md:17-24`
    - `docs/architecture/ADR_WAVE6_SECURITY_FLOOR_UNBLOCK_SEAM_2026-04-17.md:13-18,27-39,55-69`
  - DoD:
    - Canonical `security-floor` wording is shared by the Wave 6 packet (`docs/orchestration/WAVE6_AI_RUNTIME_AND_ADVISORY_SERIES_PACKET_2026-04-13.md:30-59`) and the Karpathy epic (`docs/roadmap/PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md:20-39`)
    - Allowed surfaces are explicitly limited to governed dependency manifests, lockfiles, schema/guard sync, and CVE evidence (`docs/architecture/ADR_WAVE6_SECURITY_FLOOR_UNBLOCK_SEAM_2026-04-17.md:27-39`)
    - Exit criteria and blockers are documented in the ADR and referenced from the packet (`docs/orchestration/WAVE6_AI_RUNTIME_AND_ADVISORY_SERIES_PACKET_2026-04-13.md:119-120,177-180`) and epic (`docs/roadmap/PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md:150-155,587-593`)
  - Blockers:
    - The advisory must remain dependency-only and must not widen into runtime/API/product scope
    - Every affected surface must have `file:line` evidence plus matching guard/schema proof
    - The seam closes once the dependency remediation lane is merged on `main` and the docs revert to normal lane wording

<a id="ledger-p1-mako-security-floor-alerts-114-116"></a>
- [ ] P1: Remediate `Mako` Dependabot alerts 114-116 with an explicit security floor
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (dependency security / current-head regression)
  - Target PR: PR `#1440`
  - Area: security / Python dependencies / merge governance
  - Finding Type: live dependency-security regression
  - Status: In progress as of 17 April 2026 in clean worktree `worktrees/mako-security-floor`
  - Reason (EN): `main` picked up three new Dependabot alerts on `Mako` after the
    latest merge. All three alerts (`#114`, `#115`, `#116`) map to
    `GHSA-v92g-xgxw-vvmm` with first patched version `1.3.11`. This remediation
    must land as a dedicated narrow PR before the paused security-epic/docs lane
    resumes, otherwise the repo continues to carry a current-head dependency
    security regression. (RU: На `main` после последнего merge появились три
    новых Dependabot alerts по `Mako`; их нужно закрыть отдельным узким PR до
    возврата к paused security-epic/docs lane.)
  - Links:
    - `docs/orchestration/DEPENDABOT_ALERTS_114_116_REMEDIATION_TASK_PACKET_2026-04-17.md:26-48`
    - `docs/security/GHSA-v92g-xgxw-vvmm-mako.md:5-27`
    - `tests/fixtures/dependency_security_schema.json:4`
    - `tests/test_dependency_security_guard.py:56-110`
    - GitHub alerts: `security/dependabot/114`, `security/dependabot/115`, `security/dependabot/116`
  - Evidence:
    - `docs/security/GHSA-v92g-xgxw-vvmm-mako.md:5-27` anchors the advisory
      identity, affected package, historical first patched version `1.3.11`,
      current enforced floor `1.3.12`, and the repo-managed requirement/lock
      surfaces that must stay aligned.
    - `docs/orchestration/DEPENDABOT_ALERTS_114_116_REMEDIATION_TASK_PACKET_2026-04-17.md:28-44`
      records the pre-remediation repo truth for alerts `#114-#116`, including
      the `mako==1.3.10` pins that triggered this dedicated narrow lane.
    - `tests/fixtures/dependency_security_schema.json:4` plus
      `tests/test_dependency_security_guard.py:56-110` provide the local
      fail-closed policy evidence that `Mako 1.3.12` is the current enforced
      minimum safe version for this remediation.
  - DoD:
    - Governed source surfaces explicitly enforce `Mako >= 1.3.12`
    - Pinned runtime/full/CI-lite lock surfaces resolve `mako==1.3.12`
    - Dependency security schema records `Mako 1.3.12` as the minimum safe version
    - Dedicated security note includes `file:line` evidence and validation commands
    - Draft PR is opened with canonical `docs/review/PR_<N>_FIXED_MAPPING.md`
    - Root-cause remediation plus verification land before any `docs/review/PR_<N>_FIXED_MAPPING.md` updates or review-thread resolution; fix-before-mapping remains mandatory
    - Mandatory post-open review pass `qa-engineer-agent -> bug-hunter` is completed before final mapping / resolution updates
    - Only after merge and local ref sync does the team return to the paused security-epic/docs lane

<a id="ledger-p1-pip-unsafe-pin-alerts-118-119"></a>
- [ ] P1: Remediate `pip` Dependabot alerts 118-119 by removing unsafe pins
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (dependency security / current-head regression)
  - Target PR: PR `#1529`
  - Area: security / Python dependencies / merge governance
  - Finding Type: live dependency-security regression
  - Status: In progress as of 25 April 2026 in clean worktree `worktrees/pip-unsafe-pin-remediation`
  - Reason (EN): `main` has two open Dependabot alerts on unsafe `pip` lock
    entries. Both alerts (`#118`, `#119`) map to `GHSA-58qw-9mgm-455v` /
    `CVE-2026-3219` with vulnerable range `<=26.0.1` and no patched version
    reported by GitHub on 2026-04-25. The correct narrow remediation is to
    remove the vulnerable unsafe `pip` pins from committed lock surfaces and
    block reintroduction through the dependency security schema, without broad
    lock regeneration or unrelated dependency churn.
  - Links:
    - `docs/orchestration/DEPENDABOT_ALERTS_118_119_PIP_REMEDIATION_TASK_PACKET_2026-04-25.md`
    - `docs/security/GHSA-58qw-9mgm-455v-pip.md`
    - `docs/review/PR_1529_FIXED_MAPPING.md`
    - `tests/fixtures/dependency_security_schema.json`
    - GitHub alerts: `security/dependabot/118`, `security/dependabot/119`
  - Evidence:
    - `requirements-dev.txt` no longer pins `pip==26.0`
    - `requirements-lock.txt` no longer pins `pip==26.0.1`
    - `tests/fixtures/dependency_security_schema.json` blocks `pip<=26.0.1`
  - DoD:
    - Vulnerable unsafe `pip` pins are absent from `requirements-dev.txt` and
      `requirements-lock.txt`
    - Dependency security schema blocks `pip<=26.0.1`
    - Dedicated security note includes alert identity, no-patched-version
      rationale, evidence, and validation commands
    - Draft PR is opened with canonical `docs/review/PR_<N>_FIXED_MAPPING.md`
    - Mandatory post-open review pass `qa-engineer-agent -> bug-hunter` is
      completed before final mapping / resolution updates
    - Only after merge and local ref sync does the team clean up this lane's
      worktree, branch, caches, and temporary artifacts

<a id="ledger-p1-rag-hardening-followthrough"></a>
- [x] P1: RAG hardening follow-through
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (runtime reliability)
  - Target PR: PR-A2 / PR #1415
  - Area: AI / RAG / runtime hardening
  - Finding Type: follow-through runtime slice
  - Status: ✅ Closed. PR #1415 merged on `2026-04-14T20:59:47Z`
    with merge commit `146da0e0d269acea5ba946d239997705ebaf62c3`
    from branch `feat/rag-hardening-followthrough`; title
    `feat(rag): harden degraded retrieval paths and keep contracts additive`.
  - Reason (EN): Live GitHub/repo truth proves the dedicated A2 runtime RAG
    hardening slice already landed in PR #1415. This closeout records the
    landed degraded-retrieval, malformed-vector, subject-isolation, fail-safe
    collapse, and final-confidence recomputation evidence without duplicating
    runtime implementation or making new benchmark/scientific performance
    claims.
  - Links:
    - `docs/roadmap/PulsePlate_P0_P1_Execution_Document_2026-03-30.md`
    - `docs/roadmap/PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md`
    - `docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md`
    - `docs/contracts/RAG_CONTRACT.md`
    - `core/rag/contracts.py`
    - `core/rag/orchestration.py`
    - `core/rag/vector_rag.py`
    - `tests/test_rag_orchestration.py`
    - `tests/test_vector_rag.py`
    - `tests/test_insight_rag_response_fields.py`
  - DoD:
    - PR #1415 merge evidence is machine-checkable in active roadmap/review docs
    - Landed degraded retrieval paths and fail-safe prompt preservation remain
      covered by deterministic RAG tests
    - Semantic-cache markers remain `closed / false / false / true`
    - No semantic cache, Redis/GPTCache, GraphRAG, ContextManifest, DB
      persistence, public route, OpenAPI, DTO, provider, or default activation
      scope is implied by this closeout

<a id="ledger-p1-ai-bounded-context-packet"></a>
- [x] P1: AI bounded-context packet
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (architecture sequencing)
  - Target PR: PR-A3 / PR #1469
  - Area: AI / architecture / docs
  - Finding Type: packet-first architecture freeze
  - Status: Closed. PR #1469 `docs(architecture): define AI bounded-context packet and ownership map` merged on `2026-04-19T11:35:29Z` with merge commit `f8454715f88e44657cfad1c4675f93ea669dc490` from branch `codex/ai-bounded-context-packet`.
  - Reason (EN): Live GitHub/repo truth proves the dedicated A3 docs-only packet already landed in PR #1469. This closeout reconciles active roadmap/review truth and prevents duplicate packet work before the separate A4 extraction lane.
  - Links:
    - `docs/roadmap/PulsePlate_P0_P1_Execution_Document_2026-03-30.md`
    - `docs/roadmap/PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md`
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-ai-bounded-context-extraction`
    - `docs/architecture/ADR_AI_RUNTIME_BOUNDED_CONTEXT_SEAM_2026-03-09.md`
    - `docs/architecture/C4_AI_BOUNDED_CONTEXT_PACKET_2026-03-20.md`
    - `docs/orchestration/WAVE6_A3_AI_BOUNDED_CONTEXT_PACKET_2026-04-18.md`
  - DoD:
    - PR #1469 merge evidence is machine-checkable in active roadmap/review docs
    - A docs-only packet exists before extraction
    - Ownership boundaries for AI runtime seams are explicit
    - Packet and extraction items are separate and non-duplicative
    - PR-A4 / `ledger-p1-ai-bounded-context-extraction` remains separate and open until its own extraction DoD is proven
    - Semantic-cache markers remain `closed / false / false / true`; no semantic cache, Redis/GPTCache, GraphRAG, ContextManifest, DB persistence, public route, OpenAPI, DTO, provider, or default activation scope is implied by this closeout

<a id="ledger-p1-governance-doc-sot-consolidation"></a>
- [ ] P1: Consolidate coordinator-first docs SoT and rail summary table
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-S0
  - Area: docs / orchestration / roadmap
  - Finding Type: review follow-up
  - Status: 📋 Planned
  - Reason (EN): PR #1377 review feedback identified two useful but broader follow-ups: reducing wording drift by pointing repeated coordinator-first and role-order guidance at one explicit source-of-truth subsection, and adding a compact rail/umbrella/scope summary table near the top of the RAG/LLM/Karpathy epic spine. This work should stay separate from the narrow docs/governance merge-fix slice so the current PR can close its governance lane without silently widening scope.
  - Links:
    - `AGENTS.md`
    - `RUNBOOK_AGENT.md`
    - `docs/orchestration/workflow.md`
    - `docs/dev/LOCAL_COORDINATOR_LAUNCHER_ROLLOUT.md`
    - `docs/roadmap/PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md`
    - `docs/review/PR_1377_FIXED_MAPPING.md`
  - DoD:
    - One explicit source-of-truth subsection is identified for coordinator-first and role-order invariants
    - Repeated operator-facing docs link to that source without losing lane-local execution context
    - `PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md` includes a compact rail/umbrella/scope summary table
    - No runtime, OpenAPI, or product-surface changes are introduced

<a id="ledger-p1-philosophical-logic"></a>
- [ ] P1: Philosophical logic principles for LLM reliability (Aristotelian, Analytical, Post-Analytical, Linguistic)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (high impact on reliability)
  - Target PR: PR #1024 (`feat: add philosophical runtime foundation for insight`) -> PR-A6 (`feat(ai-quality): rollout philosophical validation phases on bounded surfaces`)
  - Status: 🟡 In progress (foundation merged in PR #1024; bounded W1 rollout lane active on `codex/ai-philosophical-rollout-w1`)
  - Dependencies:
    - [P0 Master checklist phase-fit triage](#ledger-p0-master-checklist-triage)
    - [P0 Payment rails RU/BY + iOS baseline](#ledger-p0-payments-ruby-ios)
  - Reason (EN): Apply classical logic and philosophical principles to improve LLM response reliability and argumentative rigor. Hypothesized impact (requires benchmark validation): reduce contradictions from ~15% to <2%, unverifiable claims from ~30% to <5%, contextually irrelevant responses from ~25% to <10%. Four frameworks: Aristotelian logic (syllogisms, non-contradiction), Analytical philosophy (verification, falsification), Post-analytical philosophy (pragmatic validation, hermeneutics), Linguistic philosophy (speech acts, language games, meaning-as-use). **Speed optimization hypothesis target (requires benchmark validation):** philosophical principles may optimize speed (50-60% latency reduction) through adaptive depth, early stopping, and query classification. (RU: Применение классической логики и философских принципов для улучшения достоверности ответов LLM и доказательности аргументации. Гипотеза (с обязательной валидацией бенчмарками): снижение противоречий с ~15% до <2%, непроверяемых утверждений с ~30% до <5%, контекстуально нерелевантных ответов с ~25% до <10%. **Гипотеза оптимизации скорости (требует benchmark validation):** философские принципы могут снижать latency на 50-60% через адаптивную глубину, раннее прекращение и классификацию запросов.)
  - Links:
    - docs/insights/COMPREHENSIVE_PHILOSOPHY_LOGIC_MATH_CBT_ANALYSIS.md (unified analysis: philosophy + math + CBT integration)
    - docs/insights/PHILOSOPHICAL_LOGIC_LLM_RELIABILITY.md (comprehensive design, code examples, implementation roadmap)
    - docs/insights/PHILOSOPHICAL_SPEED_OPTIMIZATION.md (speed optimization using philosophical principles: speech acts, language games, early stopping, adaptive depth)
    - docs/analysis/LLM_RAG_AI_ASSISTANT_ANALYSIS.md (current LLM/RAG implementation)
    - core/insight/creative_scientific_innovations.md (AI assistant design)
    - `docs/review/PR_1024_FIXED_MAPPING.md`
    - `docs/orchestration/contracts/LOGIC_PHILOSOPHY_REPLAY_EVAL_CONTRACT.md`
    - `scripts/orchestration/logic_philosophy_replay_contract.py`
    - `scripts/orchestration/logic_philosophy_replay_eval.py`
    - `tests/test_logic_philosophy_replay_eval.py`
  - Prerequisites:
    - ✅ Current LLM/RAG infrastructure stable (`llm.py`, `core/rag/simple_rag.py`)
    - ✅ Insight endpoints stable (`legacy_app.py`, `app/routers/vip.py`)
    - ⏳ Master checklist phase-fit triage approved
    - ⏳ Fact-checking system implemented (P0 from LLM_RAG_AI_ASSISTANT_ANALYSIS.md)
  - DoD:
    - Phase 1: Aristotelian logic implemented (syllogistic prompts, contradiction detection)
    - Phase 2: Analytical philosophy implemented (verification, falsification)
    - Phase 3: Post-analytical philosophy implemented (pragmatic validation, hermeneutics)
    - Phase 4: Linguistic philosophy implemented (speech acts, language games)
    - Phase 5: Integrated framework complete (unified prompt builder + validator)
    - Hypothesis target (requires benchmark validation): Speech act classification (50-70% reduction for commands), language game detection (50-60% reduction for medical), early stopping (30-50% reduction), adaptive depth (50-60% average reduction)
    - Hypothesis target (requires benchmark validation): contradiction rate <2%, verification rate >95%, pragmatic utility >90%
    - Hypothesis target (requires benchmark validation): latency reduction 50-60% average, quality maintained ≥95%
    - Validation evidence owner: [P1 Scientific reliability publication pipeline](#ledger-p1-scientific-reliability-pipeline)
    - Integration tests pass (end-to-end philosophical validation + speed optimization pipeline)

<a id="ledger-p1-pro-monthly-quota-ledger-reconciliation"></a>
- [x] P1: Reconcile PRO monthly quota ledger with live runtime truth
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (AGENTS.md requires monthly quota before any LLM provider call)
  - Target PR: PR-A1b (`docs(ai-runtime): reconcile A1b PRO quota closeout`)
  - Status: Closed. PR #1461 merged on 2026-04-19T11:34:45Z with merge commit `cd01d9c6db89813202f85b8b9f4c8378e72380ea` from branch `codex/wave6-a1b-pro-quota-reconciliation`; follow-up PR #1466 merged on 2026-04-19T11:34:46Z with merge commit `fa0979e734b88575e01e3eca9ddd4d57ade86c05` from branch `codex/pr1461-mapping-fix`.
  - Reason (EN): PR-A1b is docs/governance closeout only. Runtime truth remains the already-merged A1 runtime spine from PR #1379, merged on 2026-04-10T12:08:46Z with merge commit `1ddf8c6778ca1f13c2bfce2e052db5409e8d06ba` from branch `feat/insight-fallback-chain`. Live `main` contains tier-aware LLM monthly quota machinery for both `PRO` and `VIP` (`app/security/llm_monthly_quota.py:26-45`, `app/security/llm_monthly_quota.py:56-93`, `app/security/llm_monthly_quota.py:200-244`), startup validation for both envs (`app/bootstrap/startup_guards.py:44-56`), PRO route tier gating (`app/routers/cbt_insight.py:144-150`), and quota-before-provider enforcement on the PRO CBT path (`app/services/fitchef_runtime.py:854-866`). PR-A1b does not reopen runtime quota logic.
  - Gate boundary: semantic-cache markers remain `closed / false / false / true`; Redis/GPTCache, GraphRAG, ContextManifest, DB persistence, public routes, OpenAPI, DTOs, provider/auth/billing changes, and default activation remain out of scope.
  - Links:
    - `docs/orchestration/WAVE6_A1B_PRO_QUOTA_RECONCILIATION_TASK_PACKET_2026-04-17.md`
    - `docs/review/PR_1379_FIXED_MAPPING.md:12-18`
    - `docs/review/PR_1461_FIXED_MAPPING.md`
    - `app/security/llm_monthly_quota.py:26-45`
    - `app/security/llm_monthly_quota.py:56-93`
    - `app/security/llm_monthly_quota.py:200-244`
    - `app/bootstrap/startup_guards.py:44-56`
    - `app/routers/cbt_insight.py:144-150`
    - `app/services/fitchef_runtime.py:854-866`
    - `tests/test_cbt_insight_api.py:109-115`
    - `tests/test_cbt_insight_api.py:356-370`
    - `tests/test_cbt_insight_api.py:1049-1072`
    - `tests/test_cbt_insight_api.py:1074-1108`
    - `tests/test_cbt_insight_api.py:1110-1134`
    - `docs/roadmap/PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md`
    - `docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md`
  - DoD:
    - Ledger and epic wording no longer describe PRO quota as VIP-only, missing, or active implementation work
    - This backlog item points to closed PR-A1b governance truth via PR #1461 and PR #1466, not a fresh runtime-from-scratch quota PR
    - Live code/test evidence for already-landed PRO quota parity is linked from the backlog item and anchored to merged PR #1379
    - Evidence bundle format is explicit: PR #1379 + PR #1461 + PR #1466, merge SHAs, and file:line pointers to runtime/test truth
    - Any true residual quota debt remains a separate narrow follow-up instead of reopening A1b

<a id="ledger-p1-philosophy-epic-v2-pr0-packet"></a>
- [x] P1: Philosophy Epic V2 PR-0 governance packet
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR #1744 (`codex/philosophy-epic-v2-pr0-packet`)
  - Status: ✅ Closed (merged PR #1744; PR-1 admission contract follow-up is tracked below)
  - Area: AI / RAG / philosophy / orchestration governance
  - Finding Type: epic-sequencing and premortem-closure gate
  - Reason (EN): Two operator-provided Philosophy Epic V2 PDFs define valuable analytical, linguistic, semantic-cache, FitChef, CBT, and rollout ideas, but current repo truth already has bounded philosophical runtime, offline logic+philosophy replay, and a closed semantic-cache gate. PR-0 creates the governed packet that reconciles those inputs before any runtime activation, prevents PDF/design input from becoming runtime authority by accident, and makes `pulseplate-premortem-risk-review` findings blocking unless they are fixed or formally dispositioned.
  - Links:
    - `docs/orchestration/PHILOSOPHY_EPIC_V2_PR0_PACKET_2026-05-13.md`
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-philosophical-logic`
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-ai-reliability-experiment-sublane`
    - `docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md`
    - `docs/orchestration/WAVE6_A6_PHILOSOPHICAL_ROLLOUT_W1_PACKET_2026-04-22.md`
    - `docs/orchestration/AI_RELIABILITY_EXPERIMENT_SUBLANE_W1_PACKET_2026-05-01.md`
    - `tools/codex_skills/pulseplate-premortem-risk-review/SKILL.md`
  - DoD:
    - PR-0 remains docs/governance only: no runtime flags, OpenAPI, DB, frontend, iOS, provider, FitChef/CBT runtime, or semantic-cache implementation changes
    - Packet records the PDF intake, repo-truth precedence, role order, plugin/skill boundaries, validation plan, PR body seed, and next-PR handoff
    - Premortem findings are closed in the packet as `FIXED`, `NOT-A-BUG`, or `DEFERRED`; follow-up PRs inherit the same closure rule before readiness claims
    - PR-1 is constrained by current semantic-cache gate markers and may not implement or enable semantic cache while the gate remains closed
    - Canonical post-open `qa-engineer-agent -> bug-hunter` plus security review are run and mapped before readiness
    - `docs/review/PR_<N>_FIXED_MAPPING.md` is added after the PR number exists and mirrored into the PR body

<a id="ledger-p1-philosophy-epic-v2-pr1-admission"></a>
- [x] P1: Philosophy Epic V2 PR-1 semantic-cache admission contract
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: #1761 (`codex/philosophy-epic-v2-pr1-admission-contract`)
  - Status: ✅ Merged PR #1761 on 2026-05-20 (`b837a683914e3439de8a61a3102e1e1b3c9ad006`)
  - Area: AI / RAG / philosophy / semantic-cache governance
  - Finding Type: admission-contract and gate-closed governance
  - Reason (EN): PR #1742 merged the SC-G5 backend-selection contract as an offline, label-only, non-serving semantic-cache governance layer. Philosophy Epic V2 PR-1 must add the higher-level philosophical admission contract that defines runtime-only, blocked, verification-bundle-required, and future-deferred request classes without opening the semantic-cache gate, duplicating SC-G5 backend-selection ranking, or adding Redis/GPTCache, embeddings, storage, serving, providers, OpenAPI, DB, frontend, or iOS changes.
  - Links:
    - `docs/orchestration/PHILOSOPHY_EPIC_V2_PR0_PACKET_2026-05-13.md`
    - `docs/orchestration/PHILOSOPHY_EPIC_V2_PR1_PACKET_2026-05-17.md`
    - `docs/orchestration/contracts/PHILOSOPHY_SEMANTIC_CACHE_ADMISSION_CONTRACT.md`
    - `docs/orchestration/contracts/SEMANTIC_CACHE_BACKEND_SELECTION_CONTRACT.md`
    - `docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md`
  - DoD:
    - Admission contract keeps semantic-cache gate markers closed and runtime/implementation false
    - Contract classifies philosophical request surfaces into `runtime_only`, `blocked_from_cache`, `verification_bundle_required`, and `future_cache_candidate_deferred`
    - Contract references SC-G5 / PR #1742 by SoT and merge evidence without duplicating backend-selection candidate/ranking matrix
    - Focused validators and tests remain static/read-only and add no runtime cache dependencies
    - All premortem, architecture, philosophy, security, QA, and bug-hunter findings are dispositioned before readiness claims
    - PR body mirrors review-thread disposition, deferred/follow-up, and merge-readiness sections after PR open

<a id="ledger-p1-philosophy-epic-v2-pr2-policy-oracle"></a>
- [x] P1: Philosophy Epic V2 PR-2 admission policy spec generator / claim-family oracle
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: #1777 (`codex/philosophy-epic-v2-pr2-policy-oracle`)
  - Status: ✅ Merged PR #1777 on 2026-05-21 (`101a6d2e6461cb86f23ff79458b9f0b36c4032ff`)
  - Area: AI / RAG / philosophy / semantic-cache governance / test infrastructure
  - Finding Type: false-green prevention, policy-as-data oracle, temporal/modal claim drift guard
  - Reason (EN): PR #1761 closed the Philosophy PR-1 admission contract but review loops exposed a systemic failure mode: hand-expanded regexes and test grammars made the same semantic claim family reappear as fresh comments. PR-2 makes the admission claim policy canonical JSON data, generates deterministic oracle fixtures, and checks policy/schema/fixture drift before runtime semantic-cache work resumes.
  - Links:
    - `docs/orchestration/contracts/PHILOSOPHY_SEMANTIC_CACHE_ADMISSION_CONTRACT.md`
    - `docs/orchestration/contracts/PHILOSOPHY_SEMANTIC_CACHE_ADMISSION_POLICY.json`
    - `docs/orchestration/contracts/PHILOSOPHY_SEMANTIC_CACHE_ADMISSION_POLICY.schema.json`
    - `tests/fixtures/orchestration/philosophy_admission_claim_oracle.json`
    - `scripts/ci/check_semantic_cache_gate.py`
    - `tests/test_philosophy_admission_policy_oracle.py`
  - DoD:
    - Canonical JSON policy defines every Philosophy admission forbidden-claim family with detector labels, modal/temporal drift examples, seed regressions, and allowed negative controls
    - Generated oracle fixture is byte-stable and fails drift checks when policy/spec/test cases diverge
    - Policy-driven checker preserves gate-closed behavior and does not add Redis, GPTCache, embeddings, vector search, provider/client, DB, OpenAPI, frontend, iOS, or runtime cache wiring
    - Phase 1 docs gates validate the policy, schema, and oracle fixture, and downstream Philosophy docs still reject forbidden admission claims while allowing explicitly negative examples
    - PR-2 documents the deterministic oracle boundary: semantic/research input may generate hypotheses, but admission truth is decided by policy/spec/oracle checks and does not mutate Experiment Runner or runtime oracle surfaces
    - Premortem, architecture, philosophy, QA, security, and bug-hunter findings are fixed or formally dispositioned before readiness claims

<a id="ledger-p1-philosophy-epic-v2-pr3-admission-dry-run"></a>
- [x] P1: Philosophy Epic V2 PR-3 admission oracle dry-run / verification-bundle adapter
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR #1784 (`codex/philosophy-epic-v2-pr3-admission-dry-run`)
  - Status: ✅ Merged PR #1784 on 2026-05-21 (`18be0c53c51e2d7d6a085d204c3a0a8f71689980`)
  - Area: AI / RAG / philosophy / semantic-cache governance / verification-bundle adapter
  - Finding Type: false-green prevention, provenance/report drift, gate-closed verification-bundle dry-run
  - Reason (EN): PR #1777 made philosophical admission claims deterministic through policy JSON and a generated oracle fixture. PR-3 adds the next governance guard: a deterministic dry-run report that connects the PR-2 oracle to synthetic verification-bundle states and proves that missing, failed, warning, and passed bundles still do not permit cache read, cache write, or serving while the semantic-cache gate remains closed.
  - Links:
    - `docs/orchestration/PHILOSOPHY_EPIC_V2_PR3_ADMISSION_DRY_RUN_PACKET_2026-05-21.md`
    - `docs/orchestration/contracts/PHILOSOPHY_ADMISSION_DRY_RUN_REPORT.json`
    - `docs/orchestration/contracts/PHILOSOPHY_ADMISSION_DRY_RUN_REPORT.schema.json`
    - `docs/orchestration/contracts/PHILOSOPHY_SEMANTIC_CACHE_ADMISSION_POLICY.json`
    - `tests/fixtures/orchestration/philosophy_admission_claim_oracle.json`
    - `scripts/ci/check_philosophy_admission_dry_run.py`
    - `tests/test_philosophy_admission_dry_run_report.py`
    - `docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md`
  - DoD:
    - Canonical dry-run report is generated from PR-2 policy/oracle truth and guarded by a closed JSON schema
    - Checker validates policy, policy schema, oracle fixture, dry-run report schema, and generated report together
    - Report records missing, failed, warning, and passed verification-bundle states with deterministic decisions
    - Passed verification bundle stays `gate_closed_deferred`; every decision keeps `cache_read_allowed=false`, `cache_write_allowed=false`, and `serving_allowed=false`
    - Phase 1 docs gates and CI workflow tests cover report/schema drift
    - No Redis, GPTCache, embeddings, vector search, provider/client, DB, OpenAPI, frontend, iOS, `/insight`, connection-string, cache-adapter, or runtime activation changes are made
    - Premortem, architecture, philosophy, QA, security, and bug-hunter findings are fixed or formally dispositioned before readiness claims

<a id="ledger-p1-philosophy-epic-v2-alignment-rule-trust-schema"></a>
- [x] P1: Philosophy Epic V2 alignment-rule trust schema
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR #1789 (`codex/philosophy-alignment-rule-trust-schema`)
  - Status: Completed. PR #1789 merged on 2026-05-21T22:14:53Z with merge commit `651c56bb510125b4df011a6d48de6f82a8f6e0b7`. PR #1811 / PR-4.1 reconciled the PR-4 ledger closeout on 2026-05-24T09:39:30Z with merge commit `0b324f516b5ba33dfc5e65d068cd5aaca742b5f8`; PR-4.2 closes this separate alignment-rule ledger row only. Semantic-cache runtime handoff remains blocked: all gate markers stay closed/false, PR-A1b through PR-A5 plus a later reviewed gate-open PR remain required, and no runtime semantic-cache work may begin.
  - Area: AI / RAG / philosophy / semantic-cache governance / trust schema
  - Finding Type: provenance, schema-hash, and future admission-rule auditability
  - Reason (EN): PR #1784 connected the admission oracle to verification-bundle dry-run truth while keeping cache read, cache write, and serving disabled. The next safe slice defines a machine-readable alignment-rule record shape and deterministic validator so future admission-rule artifacts can carry stable provenance, executable assertion hints, schema version, and schema hash before any later release-manifest or runtime semantic-cache linkage is considered.
  - Links:
    - `docs/orchestration/contracts/PHILOSOPHY_ALIGNMENT_RULE.schema.json`
    - `scripts/ci/check_philosophy_alignment_rules.py`
    - `tests/test_philosophy_alignment_rules.py`
    - `scripts/ci/check_docs_phase1_gates.py`
    - `docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md`
    - `docs/orchestration/contracts/PHILOSOPHY_ADMISSION_DRY_RUN_REPORT.json`
  - Deferred / Follow-ups:
    - Future release-manifest slice: add `alignment_schema_hash` only after the release evidence contract explicitly accepts the field and current-head CI proves deterministic manifest hashing.
    - Future runtime semantic-cache slice: add cache-row `rule_id` linkage only after the global semantic-cache gate opens and a reviewed runtime packet covers DB/cache migration, replay safety, rollback, and verification-bundle admission.
  - DoD:
    - Alignment-rule JSON schema is repo-native, closed to unknown fields, and requires rule identity, provenance, assertion hints, schema version, and schema hash
    - Validator computes the schema hash deterministically from canonical sorted JSON bytes and fails closed on mismatched rule records
    - Validator rejects duplicate `rule_id` values, malformed provenance, unknown keys, and invalid regex hints
    - Phase 1 docs gates validate the alignment-rule schema when the schema changes
    - PR stays governance/test-only with no Redis, GPTCache, embeddings, vector search, provider/client, DB, OpenAPI, frontend, iOS, `/insight`, connection-string, cache-adapter, release-manifest mutation, or runtime activation changes
    - Premortem, architecture, philosophy, QA, security, and bug-hunter findings are fixed or formally dispositioned before readiness claims

<a id="ledger-p1-philosophy-epic-v2-pr4-gate-open-preconditions"></a>
- [x] P1: Philosophy Epic V2 PR-4 semantic-cache gate-open preconditions / runtime admission handoff
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR #1791 (`codex/philosophy-epic-v2-pr4-gate-open-preconditions`)
  - Status: Completed. PR #1789 merged on 2026-05-21 with merge commit `651c56bb510125b4df011a6d48de6f82a8f6e0b7`; PR #1791 merged on 2026-05-22 with merge commit `b16175721933012ae53162b8268888c960458d46`. PR-4.1 reconciles ledger/roadmap status only: semantic-cache runtime handoff remains blocked and all gate markers stay closed/false. PR-SC0 records the A1b-A5 runtime prerequisite train as closed by merge evidence; a later reviewed gate-open PR remains required before runtime semantic-cache work can begin. Future status-only reconciliations must use the PR-4.1 packet source-truth section as the update checklist.
  - Area: AI / RAG / philosophy / semantic-cache governance / runtime handoff readiness
  - Finding Type: gate-open false-positive prevention, prerequisite drift guard, blocked runtime handoff inventory
  - Reason (EN): PR #1777 made Philosophy admission claim families deterministic, and PR #1784 connected them to a verification-bundle dry-run while preserving the closed gate. PR-4 adds the next guard: a compact machine-checkable precondition report that proves PR-2/PR-3 sources are current and, after PR-SC0 reconciliation, records PR-A1b through PR-A5 as merge-verified closed while runtime handoff remains blocked until a later reviewed gate-open PR changes the machine markers.
  - Links:
    - `docs/orchestration/PHILOSOPHY_EPIC_V2_PR4_GATE_OPEN_PRECONDITIONS_PACKET_2026-05-21.md`
    - `docs/orchestration/PHILOSOPHY_EPIC_V2_PR4_1_LEDGER_CLOSEOUT_PACKET_2026-05-24.md`
    - `docs/orchestration/contracts/PHILOSOPHY_GATE_OPEN_PRECONDITIONS_REPORT.json`
    - `docs/orchestration/contracts/PHILOSOPHY_GATE_OPEN_PRECONDITIONS_REPORT.schema.json`
    - `scripts/ci/check_philosophy_gate_open_preconditions.py`
    - `tests/test_philosophy_gate_open_preconditions.py`
    - `docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md`
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-philosophy-epic-v2-alignment-rule-trust-schema`
  - DoD:
    - PR-4 report validates PR-2 policy/oracle truth, PR-3 dry-run truth, semantic-cache roadmap markers, and runtime prerequisite merge evidence without opening the gate
    - Report distinguishes `source_current` governance sources from `merge_verified_closed` runtime prerequisites and records that ledger anchor presence alone does not verify closure
    - `gate_open_allowed=false`, `runtime_handoff_allowed=false`, `cache_read_allowed=false`, `cache_write_allowed=false`, and `serving_allowed=false` are enforced by report, schema, checker, and tests
    - PR #1789 alignment-rule schema remains a blocking external predecessor unless its artifact is present and minimally valid on the current base; file presence alone is not accepted
    - PR-4.1 closeout records PR #1789 and PR #1791 merge evidence without changing semantic-cache gate markers, runtime handoff flags, or runtime/cache implementation scope
    - Phase 1 docs gates validate PR-4 report/schema drift when the report, schema, roadmap, ledger, PR-2 policy/oracle, or PR-3 dry-run inputs change
    - No Redis, GPTCache, embeddings, vector search, provider/client, DB, OpenAPI, frontend, iOS, `/insight`, connection-string, cache-adapter, or runtime activation changes are made
    - Premortem, architecture, philosophy, QA, security, and bug-hunter findings are fixed or formally dispositioned before readiness claims

<a id="ledger-p1-philosophy-epic-v2-pr5-source-corpus-index"></a>
- [x] P1: Philosophy Epic V2 PR-5 philosophical source corpus / interdisciplinary synthesis index
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR #1822 (`docs(philosophy): add source corpus oracle`)
  - Status: Landed via PR #1822 on 2026-05-26 with merge commit `740a64fb7d87d404076117698bee5d4bee71f390`. PR-5 preserves the six operator-provided philosophy PDFs as a governed source-corpus index before any later philosophy module or semantic-cache follow-up. PR-A2 remains a separate AI/runtime prerequisite line. Semantic-cache runtime handoff remains blocked: all machine markers stay closed/false, and PR-A1b through PR-A5 plus a later reviewed gate-open PR remain required before any runtime semantic-cache work can begin.
  - Reconciliation note: PR #1865 is the retroactive docs-only ledger closeout
    for this already-landed source-corpus lane. Future PRs that close ledger
    items should still update this ledger in the same PR or same/next-day
    follow-up.
  - Area: AI / RAG / philosophy / source corpus / interdisciplinary governance / test infrastructure
  - Finding Type: corpus-preservation, source-boundary policy, interdisciplinary synthesis index
  - Reason (EN): PR-0 through PR-4.2 made the philosophy semantic-cache admission line deterministic and gate-closed, but the expanded operator PDF corpus now spans Socratic method, Leibniz and information theory, analytical/linguistic philosophy, CBT-coaching correlations, and plan-adaptation concepts. PR-5 prevents those documents from being lost or accidentally treated as runtime truth by adding a canonical source index, schema, guard, tests, and packet that preserve source identity while keeping semantic-cache and runtime activation blocked.
  - Links:
    - `docs/orchestration/PHILOSOPHY_EPIC_V2_PR5_SOURCE_CORPUS_INDEX_PACKET_2026-05-24.md`
    - `docs/orchestration/contracts/PHILOSOPHY_SOURCE_CORPUS_INDEX.json`
    - `docs/orchestration/contracts/PHILOSOPHY_SOURCE_CORPUS_INDEX.schema.json`
    - `scripts/ci/check_philosophy_source_corpus_index.py`
    - `tests/test_philosophy_source_corpus_index.py`
    - `docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md`
  - Deferred / Follow-ups:
    - Future analytical module packet: consume `analytic_linguistic_audit` only through a reviewed docs/governance packet with deterministic tests.
    - Future CBT/wellness-coaching packet: consume CBT correlation and plan-adaptation sources only with wellness-only copy and safety tests.
    - Future runtime semantic-cache slice: still requires the global semantic-cache gate to open through a reviewed gate-open PR after runtime prerequisites close.
  - DoD:
    - Canonical JSON index represents all six PDFs with stable IDs, page counts, SHA-256 fingerprints, paraphrased summaries, discipline rails, repo anchors, and false runtime flags
    - Closed JSON schema and deterministic checker validate source completeness, sorted IDs, page-count drift, local-path/credential-like URL leakage, roadmap marker drift, PR-4 blocked handoff state, and forbidden runtime touched paths
    - Phase 1 docs gates validate the source index and schema when either changes
    - PR-5 packet records coordinator-first startup, role order, research basis, oracle pass, premortem closure, Experiment Runner evidence rules, and post-open QA/bug/security pass
    - No Redis, GPTCache, embeddings, vector search, provider/client, DB, OpenAPI, frontend, iOS, `/insight`, connection-string, cache-adapter, or runtime activation changes are made
    - Premortem, architecture, philosophy, web-research, QA, security, cursor-specialist, and bug-hunter findings are fixed or formally dispositioned before readiness claims

<a id="ledger-p1-recursive-methods"></a>
- [ ] P1: Recursive methods for LLM/RAG/AI assistant (multi-hop retrieval, recursive reasoning, self-refinement, self-verification, learning)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (high impact on quality and accuracy)
  - Target PR: PR-A7 / PR #1499 (`feat(ai-runtime): rollout recursive RAG and bounded recursive verification`)
  - Status: ✅ W1 landed via PR #1499 on 2026-04-23 with merge commit `1e7166e55c54448c0d6475338e1b9984efd0caf1` from branch `codex/ai-recursive-methods-w1`; this closeout reconciles stale ledger/roadmap/review truth and does not duplicate implementation. Parent P1 checkbox stays open until the full recursive-framework DoD is separately proven.
  - Dependencies:
    - [P1 Philosophical logic principles](#ledger-p1-philosophical-logic)
  - Reason (EN): Explore recursive methods as hypothesis-driven ways to improve LLM/RAG reliability and AI assistant capabilities. Five recursive technique families remain under evaluation: recursive retrieval, recursive reasoning, recursive refinement, recursive verification, and recursive learning. Previously cited percentage ranges for retrieval quality, answer accuracy, answer quality, factual-error reduction, latency, and user satisfaction are benchmark hypotheses only, not shipped performance claims; validation evidence is owned by the scientific reliability publication pipeline before any production-quality assertion is made. (RU: Рекурсивные методы рассматриваются как гипотезы для улучшения надежности LLM/RAG и возможностей AI ассистента. Любые процентные диапазоны по качеству retrieval, точности ответов, качеству ответов, снижению фактических ошибок, latency и удовлетворенности пользователей являются только гипотезами до benchmark validation, а не shipped performance claims.)
  - Links:
    - docs/insights/COMPREHENSIVE_PHILOSOPHY_LOGIC_MATH_CBT_ANALYSIS.md (unified analysis: philosophy + math + CBT integration, recursive methods with philosophical validation)
    - docs/insights/RECURSIVE_METHODS_LLM_RAG.md (comprehensive design, code examples, implementation roadmap, expected impact)
    - docs/insights/RECURSIVE_OPTIMIZATION_STRATEGY.md (optimization strategies: parallelization, caching, batching, open-source libraries)
    - docs/analysis/LLM_RAG_AI_ASSISTANT_ANALYSIS.md (current RAG implementation: `core/rag/simple_rag.py`)
    - docs/insights/PHILOSOPHICAL_LOGIC_LLM_RELIABILITY.md (complements recursive verification)
    - core/rag/simple_rag.py (current single-pass keyword-based RAG)
  - Prerequisites:
    - ✅ Current RAG infrastructure stable (`core/rag/simple_rag.py`)
    - ✅ LLM provider stable (`llm.py`)
    - ✅ Redis available in docker-compose (for caching optimization)
    - ⏳ Fact-checking system implemented (for recursive verification)
    - ⏳ User feedback storage remains a future prerequisite for any separately reviewed recursive-learning lane
  - DoD:
    - Phase 1: Recursive RAG implemented (multi-hop retrieval, query refinement)
    - Phase 2: Recursive reasoning remains a future target; provider chain-of-thought/tree-of-thought claims stay out of scope until a separate reviewed runtime PR
    - Phase 3: Recursive refinement implemented (self-critique, iterative improvement)
    - Phase 4: Recursive verification implemented (self-validation, claim checking)
    - Phase 5: Recursive learning remains out of scope until a separate reviewed runtime PR defines storage, consent, privacy, and verification boundaries
    - Phase 6: Integrated recursive framework complete (`RecursiveAIAssistant`)
    - Hypothesis target (requires benchmark validation): Parallelization (asyncio.gather), GPTCache integration, Redis caching, batch verification (reduce latency from 2-3x to 1.2-1.5x)
    - Hypothesis target (requires benchmark validation): retrieval quality ≥85%, answer accuracy ≥85%, factual errors ≤5%, latency ≤1.5x baseline
    - Hypothesis target (requires benchmark validation): caching, parallelization, early stopping (3-5x LLM calls acceptable, reduced to 1.5-2x with caching)
    - Validation evidence owner: [P1 Scientific reliability publication pipeline](#ledger-p1-scientific-reliability-pipeline)
    - Integration tests pass (end-to-end recursive pipeline)
  - Merged increments (tracking only; parent P1 checkbox stays open until full DoD):
    - PR: [#1233](https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1233) — squash on `main`: `82f6aec24524306948ba67e774211c7cae8b494d` (2026-03-24).
    - Scope (EN): Request-scoped FIFO hop-vector memoization for bounded recursive RAG when optimization is enabled; lazy-import hardening for `vector_rag`; benchmark script `scripts/benchmark_recursive_rag_hop_cache.py` (`stop_reason` as enum values); tests in `tests/test_recursive_rag.py`; merge-mapping artifact `docs/review/PR_1233_FIXED_MAPPING.md`.
    - (RU: Инкремент: мемоизация hop-вектора в рамках запроса + бенч/тесты; родительский P1 по полному recursive-framework DoD не закрыт.)
    - PR: [#1499](https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1499) — merge commit `1e7166e55c54448c0d6475338e1b9984efd0caf1` (2026-04-23).
    - Scope (EN): Bounded W1 recursive RAG and bounded recursive verification rollout on existing product-AI insight seams, preserving recursive budgets, thin app/service handoff, and `VerificationBundle` truth without route/OpenAPI/DTO changes.
    - Closeout note (EN): This reconciliation records live GitHub/repo truth after the implementation PR had already merged. It keeps semantic cache, Redis/GPTCache, GraphRAG, ContextManifest, DB persistence, public routes, public DTOs, provider-side tree-of-thought, and recursive learning out of scope.
    - (RU: Инкремент: bounded W1 рекурсивный RAG + bounded verification уже приземлен в PR #1499; родительский P1 по полному recursive-framework DoD не закрыт.)
    - PR: [#1506](https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1506) — merge commit `19fdbd3098a6aef780a71e94e94980cb3d0f61ee` (2026-04-23T20:41:25Z) from branch `codex/ai-recursive-speed-optimization-w1`; title `feat(ai-runtime): add philosophical speed optimization to recursive stack`.
    - Scope (EN): PR-A8 landed deterministic recursive optimization hints and bounded early-stopping seams on existing recursive/RAG runtime surfaces without public route, OpenAPI, DTO, DB, provider-side reasoning, recursive-learning, or semantic-cache changes.
    - Evidence boundary (EN): This increment records landed code/review truth only. It does not claim fresh benchmark results; latency and quality numbers remain hypothesis targets that require benchmark validation.
    - PR: [#1578](https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1578) — merge commit `37995a6e8d4e9451b85e7e6284e9bd0cd5afff45` (2026-04-29T20:32:42Z) from branch `codex/wave6-a8-recursive-speed-optimization`; title `feat(ai-runtime): add philosophical speed optimization to recursive stack`.
    - Scope (EN): Follow-up hardening for PR-A8 review findings, including null route-hint fallback and refined-query short-circuit behavior, while preserving the same no-public-contract and gate-closed boundaries.
    - Closeout note (EN): Parent P1 checkbox stays open until the full recursive-methods DoD is separately proven. Semantic cache remains closed; Redis/GPTCache, GraphRAG, ContextManifest, DB persistence, public routes, OpenAPI, DTOs, recursive learning, provider chain-of-thought, provider tree-of-thought, and default activation remain out of scope.


- [ ] Orchestration: implement AI multi-agent contracts (RAG/UQ/CV + safety) — runtime follow-up
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (AI / safety / reliability)
  - Target PR: TBD (runtime)
  - Status: 📋 Planned
  - Area: backend / AI orchestration
  - Finding Type: product + safety
  - Reason: We have a docs-level orchestration baseline and role contracts, but runtime implementation must enforce
    bounded recursion (cost control), grounding/citations, uncertainty reporting, and wellness-safe language.
  - Links:
    - `docs/audit/UNIVERSAL_AGENT_ORCHESTRATION_LAYER_AUDIT.md`
    - `docs/orchestration/workflow.md` (canonical workflow; dev-only)
  - DoD:
    - RAG endpoints (if any) are tier-gated, rate-limited, and enforce monthly quota before provider calls
    - Deterministic tests prove 200 → 429 transitions and quota enforcement
    - Outputs include explicit `sources[]` and confidence/uncertainty fields per contract
    - No OpenAPI determinism regressions; `make verify` passes


<a id="ledger-p1-ai-bounded-context-extraction"></a>
- [x] P1: Extract AI runtime into a dedicated bounded context
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-A4 / PR #1203
  - Status: ✅ Closed. PR #1203 `feat(ai): extract bounded AI runtime ownership into canonical core/ai seam` merged on `2026-03-21T06:01:31Z` with merge commit `831d62d8be0da7307e5a0f2673d8c33dbf53ca49` from branch `feat/ai-bounded-context-extraction`.
  - Area: backend / AI runtime / architecture
  - Finding Type: bounded-context hardening
  - Reason: Live GitHub/repo truth proves the dedicated A4 bounded-context extraction slice already landed in PR #1203. The landed evidence created the canonical `core/ai/*` runtime seam, `core/ai/insight_runtime.py`, thin `app/services/insight_application_service.py` handoff, architecture documentation updates, and deterministic tests without opening semantic cache or changing public route/OpenAPI/DTO contracts.
  - Links:
    - `docs/architecture/providers_implementation.md`
    - `AGENTS.md`
    - `docs/security/SECURITY_POSTURE.md`
    - `docs/runbooks/ENGINEER_QUICKPATH.md`
    - `docs/contracts/API_CANONICAL_MAP.md`
    - `docs/architecture/ADR_AI_RUNTIME_BOUNDED_CONTEXT_SEAM_2026-03-09.md`
    - `core/ai/insight_runtime.py`
    - `app/services/insight_application_service.py`
    - `tests/test_core_ai_insight_runtime.py`
    - `tests/test_insight_application_service.py`
  - DoD:
    - PR #1203 merge evidence is machine-checkable in active roadmap docs
    - Canonical AI runtime package structure exists and is documented
    - Routers and client layers remain thin adapters around AI behavior
    - Safety/eval/provider ownership is mapped to the bounded context
    - AGENTS and architecture docs no longer need transitional wording about this A4 extraction prerequisite
    - Semantic-cache markers remain `closed / false / false / true`; no semantic cache, Redis/GPTCache, GraphRAG, ContextManifest, DB persistence, public route, OpenAPI, DTO, provider, or default activation scope is implied by this closeout


<a id="ledger-p1-api-key-toggle-guard"></a>
- [ ] P1: Production fail-fast for anonymous/dev API key toggles
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-TBD-API-KEY-TOGGLE-GUARD
  - Area: backend / security / configuration
  - Finding Type: misconfiguration hardening
  - Reason: `ALLOW_ANONYMOUS_API_KEYS` and `ALLOW_DEV_API_KEY` remain env-driven escape hatches. The codebase documents that they must stay off in production, but startup/config guards are still too easy to misconfigure across `APP_ENV` and `ENVIRONMENT`.
  - Links:
    - `app/middleware/api_tiers.py`
    - `app/routers/vip.py`
    - `legacy_app.py`
    - `docs/deploy/VIP_API_KEYS.md`
    - `tests/test_vip_anonymous_api_key_safety.py`
  - DoD:
    - Production-like env detection is canonicalized (`APP_ENV` / `ENVIRONMENT` mismatch removed or documented)
    - App fails closed or logs explicit startup error when anonymous/dev API key toggles are enabled in production-like envs
    - Tests cover fail-closed behavior for production/staging settings
    - Deploy docs show the safe production values


<a id="ledger-p1-legacy-runtime-env-canonicalization"></a>
- [ ] P1: Canonicalize legacy runtime env gating
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR `#1072`
  - Status: 🟡 In progress (branch `feat/p1-legacy-runtime-env-canonicalization-pr`)
  - Follow-up from PR `#1054` (parent: `ledger-p1-api-key-toggle-guard`)
  - Area: backend / security / legacy compatibility
  - Finding Type: configuration drift
  - Reason: `legacy_app.py` still contains module-level `APP_ENV`-only gates for local `.env` loading, dev-only docs, test-router registration, and `/debug_env`. This drifts from the canonical `ENVIRONMENT`-first runtime helpers introduced by the API key toggle guard and can re-enable development-only surfaces when only `ENVIRONMENT` is set in production-like deployments.
  - Links:
    - `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1054`
    - `#ledger-p1-api-key-toggle-guard`
    - `legacy_app.py`
    - `settings.py`
    - `docs/deploy/VIP_API_KEYS.md`
    - `docs/review/PR_1054_FIXED_MAPPING.md`
  - DoD:
    - Module-level env gating in `legacy_app.py` uses canonical runtime helpers instead of raw `APP_ENV`
    - Local `.env` loading, test-router registration, and `/debug_env` gating follow the same environment semantics as startup guards
    - Tests cover `ENVIRONMENT` overriding `APP_ENV` for the remaining legacy surfaces


<a id="ledger-p1-openapi-decoupling-split"></a>
- [ ] P1: Split backend OpenAPI generation from frontend type generation
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-TBD-OPENAPI-DECOUPLING-SPLIT
  - Area: build / contracts / developer workflow
  - Finding Type: workflow hardening
  - Reason: `make openapi` is the current canonical combined path, but backend-only schema generation and frontend type generation are still coupled in the active Make workflow. A dedicated split would reduce backend-only friction while preserving `make openapi-check` as the sync verifier.
  - Links:
    - `Makefile`
    - `AGENTS.md`
    - `docs/runbooks/ENGINEER_QUICKPATH.md`
    - `docs/contracts/API_CANONICAL_MAP.md`
    - `docs/architecture/ADR_OPENAPI_WORKFLOW_SPLIT_SEAM_2026-03-09.md`
  - DoD:
    - Dedicated backend schema target exists without frontend install dependency
    - Dedicated frontend type-generation target exists
    - `make openapi-check` remains the canonical sync verifier
    - `AGENTS.md`, runbooks, API map, and CI docs reflect the split workflow without ambiguity

<a id="ledger-p1-caddy-attested-staging-digests"></a>
- [ ] P1: Harden Caddy and deploy staging by same-job attested digests
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Status: In progress
  - Target PR: PR #2117 (`codex/caddy-2-11-attested-digests`)
  - Area: deploy / CD / container supply chain
  - Finding Type: release integrity and vulnerability remediation
  - Reason: Active staging accepts floating Caddy/application tags while CD verifies one
    backend build digest but invokes a server-local deploy script with a different SHA-tag
    identity. The official Caddy 2.11.4 Alpine artifact also requires bounded remediation
    for fixed `c-ares`, `curl`/`libcurl`, and Go standard-library findings before
    PulsePlate can serve it.
    Current-head Docker validation also exposed the expired review window for the existing
    pinned SQLite source artifact; PR #2117 revalidates its unchanged URL and SHA3-256 and
    renews that fail-closed window without changing the SQLite version.
  - Links:
    - `frontend/Dockerfile.caddy-spa`
    - `deploy/docker-compose.staging.yaml`
    - `scripts/deploy.sh`
    - `.github/workflows/cd.yml`
    - `docs/deploy/STAGING.md`
  - DoD:
    - PulsePlate Caddy reports v2.11.4 built with Go 1.26.6 and preserves standard modules
    - Final hardened Caddy image has no HIGH/CRITICAL Trivy findings without suppressions
    - Backend and Caddy each have distinct provenance, SBOM, verification, and exact-digest scan evidence
    - Staging Compose and deploy script reject floating/tag-only image references
    - Default-false rollout gate verifies root-owned marker and current-commit server file hashes before secrets/deploy
    - Existing SQLite 3.53.2 source URL and SHA3-256 are revalidated and the bounded source-artifact review window is current
    - No live deploy occurs in the PR; rollout and database-aware rollback remain human-approved

- [ ] P1: Remove staging TLS fallback seam after full staging readiness
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-TBD-STAGING-SEAM-REMOVAL
  - Area: deploy / CD policy / staging runtime
  - Finding Type: temporary seam removal
  - Reason: Build-only mode keeps staging HTTPS alive via production Caddy fallback vhost. This is intentional temporary behavior and must be removed once staging runtime deploy is continuously enabled.
  - Links:
    - `docs/architecture/ADR_STAGING_TLS_FALLBACK_SEAM_2026-03-04.md`
    - `deploy/Caddyfile.production`
    - `deploy/docker-compose.production.yaml`
    - `docs/deploy/STAGING.md`
    - `.github/workflows/cd.yml`
  - DoD:
    - Staging stack in `/srv/pulseplate-staging` is primary runtime source for staging URL
    - `WEB_IOS_RELEASE_READY=true` and staging SSH deploy path is continuously enabled
    - Production Caddy fallback vhost for `STAGING_FALLBACK_DOMAIN` is removed
    - Runbook evidence updated with direct `file:line` anchors for non-fallback flow

<a id="ledger-p1-domain-ownership-canonicalization"></a>
- [x] P1: Canonicalize `pulseplate.app` root-domain ownership before Figma web sync PR
  - Owner: @katsiaryna_kavaleuskaya
  - Target PR: PR `#1141` (`fix(deploy): add www TLS remediation diagnostics`)
  - Priority: P1
  - Status: ✅ Completed on March 14, 2026 after PR `#1141` merged to `main`; any future Figma/web-hosting work now inherits the canonicalized apex ownership baseline instead of tracking this as an open blocker
  - Area: deploy / figma / frontend
  - Finding Type: production ownership drift
  - Reason: On March 12, 2026 the repo-backed runtime still answered on
    `pulseplate.app`, `www.pulseplate.app` returned `525`, and the Figma custom-domain
    attempt for `pulseplate.app` reported a conflicting apex `AAAA` record. Root-domain
    ownership must be canonicalized before any repo-backed Figma web sync PR proceeds.
  - Links:
    - `deploy/Caddyfile.production`
    - `deploy/PRODUCTION.md`
    - `docs/deploy/CLOUDFLARE.md`
    - `scripts/check_domain_tls.py`
    - `tests/test_check_domain_tls.py`
    - `scripts/QUICK_DIAGNOSTIC.md`
    - `docs/figma/FIGMA_CODE_CONNECT_BRIDGE_HPP.md`
    - `docs/figma/FIGMA_MAKE_SYNC_AUDIT_HPP.md`
    - `docs/figma/orchestration/sessions/2026-03-12_domain_canonicalization/01_BASELINE_STATUS.md`
  - DoD:
    - `python3 scripts/check_domain_tls.py --domain pulseplate.app` exists as the canonical read-only public-side diagnostic
    - Repo evidence records the March 12, 2026 baseline from the new diagnostic and the live remediation result
    - External DNS removes the conflicting apex `AAAA` record from the production zone
    - `www.pulseplate.app` no longer returns `525` and redirects cleanly to apex
    - `pulseplate.app` and `www.pulseplate.app` remain owned by the repo-backed production runtime
    - Any Figma-hosted preview is moved to a dedicated non-production subdomain
    - PR-2 web sync/import work starts only after this ownership baseline is stable


- [ ] Design file URL + node IDs required for Code Connect activation (H+P+Pr)
  - Owner: @katsiaryna_kavaleuskaya (Design + FE + iOS)
  - Target PR: PR/Figma-CodeConnect-Activation
  - Priority: P1
  - Status: Optional follow-up (auxiliary to Penpot + Storybook)
  - Area: design / frontend / iOS
  - Finding Type: integration dependency
  - Reason: Web review is now canonical via Storybook + Penpot bridge, while
    Code Connect activation remains an optional auxiliary mapping path once the
    current P0 node set is complete/non-stale and the workspace has a Code
    Connect-capable seat.
  - Links:
    - `docs/figma/FIGMA_CODE_CONNECT_BRIDGE_HPP.md`
    - `docs/figma/FIGMA_DESIGN_URL_NODEID_CAPTURE_HPP.md`
    - `docs/figma/FIGMA_CODE_CONNECT_MAPPING_CANDIDATES_HPP.md`
    - `docs/figma/FIGMA_MAKE_SYNC_AUDIT_HPP.md`
  - DoD:
    - Figma Design file URL is recorded in repo docs
    - P0 CTA nodes have current, non-stale `fileKey` and `nodeId`
      (`web.home.open_setup`, `web.plate.premium_gate_cta`,
      `web.progress.export_pdf`, `ios.plate.issue_action_dynamic`)
    - `get_code_connect_suggestions` is no longer plan-blocked for the workspace
    - `get_code_connect_map` returns expected active mappings for P0 set
    - Matrix optional design review references are updated for activated rows
    - Optional activation path does not redefine the canonical Storybook-first
      web review workflow


<a id="ledger-p1-pulseplate-v3-clean-figma-execution"></a>
- [ ] P1: PulsePlate_v3 clean Figma foundations/components/welcome-gate execution
  - Owner: @katsiaryna_kavaleuskaya (Design + FE + iOS)
  - Target PR: PR-TBD-PULSEPLATE-V3-CLEAN-FIGMA
  - Priority: P1
  - Status: In progress
  - Area: design / Figma / design-system reconciliation
  - Finding Type: file-specific canonical execution follow-up
  - Reason: The repo now has a file-specific reconciliation packet for
    `PulsePlate_v3`, and the clean canonical Figma file plus initial governed
    page scaffold/specimen lane are now in place, but full Phase 1 parity still
    needs to land for `Foundations + Components + Welcome Gate` without turning
    Figma into a hidden source of truth and without making direct Code Connect
    activation a blocker.
  - Links:
    - `docs/figma/PULSEPLATE_V3_DESIGN_SYSTEM_RECONCILIATION.md`
    - `docs/figma/FIGMA_IMPLEMENTATION_RUNBOOK.md`
    - `docs/figma/README.md`
    - `docs/design/UI_COMPONENT_VOCABULARY.md`
    - `docs/design/TOKENS_SOT.md`
    - `docs/design/WELCOME_GATE_VISUAL_PHILOSOPHY.md`
  - DoD:
    - Clean canonical Figma file contains pages `00_Foundation_Tokens`,
      `01_Components`, `02_Brand_Assets`, `10_Welcome_Gate`,
      `11_Welcome_Gate_States`, and `90_Audit_Archive`
    - Foundation variables/styles in the clean file map to repo token SoT with
      no unmanaged local styles
    - Shared components are rebuilt from repo primitives before any page-level
      welcome-gate composition work
    - Welcome Gate follows `Pulse Membrane` composition rules and passes
      anti-drift / mascot provenance checks
    - Storybook/component inventory remains the canonical web review lane
    - Any optional FIGR AI exploration remains read-only and is normalized
      through repo vocabulary/tokens before use
  - Blockers:
    - Depends on repo-side drift cleanup where current runtime styling still
      conflicts with governance (`PremiumGate`, `VipBadge`)


<a id="ledger-p1-pulseplate-v3-phase1-repo-drift-cleanup"></a>
- [ ] P1: Phase 1 repo-first drift cleanup before canonical Figma mirror expansion
  - Owner: @katsiaryna_kavaleuskaya (Design + FE)
  - Target PR: #1424
  - Priority: P1
  - Status: In progress via PR `#1424` after PR `#1422`
  - Area: design-system / frontend / Figma reconciliation
  - Finding Type: repo-first remediation follow-up
  - Reason: The Phase 1 delta audit identified repo-first follow-up work that should not be silently carried as narrative-only debt: stale `DesignSystemOverview` / `CanonBoards` Figma references, missing governed shared primitives, and the need to record the `PP/Shared/StepRail/*` naming normalization in repo truth. These items must be resolved in repo truth before any broader canonical Figma mirror expansion claims parity.
  - Links:
    - `docs/figma/FIGMA_MAKE_SYNC_AUDIT_HPP.md`
    - `docs/figma/orchestration/sessions/2026-04-13_phase1_delta_audit.md`
    - `frontend/src/components/design-system/DesignSystemOverview.tsx`
    - `frontend/src/components/design-system/CanonBoards.tsx`
    - `docs/design/UI_COMPONENT_VOCABULARY.md`
  - DoD:
    - `DesignSystemOverview` and `CanonBoards` no longer point at stale legacy Figma node references
    - Repo naming decision is recorded for `PP/Shared/StepRail/*` ownership/vocabulary before any canonical Figma promotion depends on it
    - Missing Phase 1 shared primitives are either implemented in repo truth or explicitly deferred with updated design-system docs
    - Follow-up PR updates the Phase 1 Figma audit docs to reflect the resolved repo-first state


<a id="ledger-p1-welcome-gate-full-flow-after-node-capture"></a>
- [ ] P1: Welcome Gate full 4-screen runtime flow after exact Figma node capture
  - Owner: @katsiaryna_kavaleuskaya (Design + FE + iOS)
  - Target PR: PR-TBD-WELCOME-GATE-FULL-FLOW
  - Priority: P1
  - Status: Deferred after `feat/welcome-gate-v1-pr-b`
  - Area: frontend / onboarding / design-governance
  - Finding Type: intentional scope deferral
  - Reason: The repo now ships Welcome Gate v1 as a screen-1-only preview route
    and Storybook review surface, but the full runtime gate must not be wired
    until screens 2-4 have exact Figma Design URLs and `nodeId` coverage. This
    prevents guessing later screens, avoids premature persistence contracts, and
    keeps Storybook as the canonical review source while product routes remain
    mirror surfaces only.
  - Links:
    - `docs/design/WELCOME_GATE_VISUAL_DIRECTION.md`
    - `docs/design/WELCOME_GATE_VISUAL_PHILOSOPHY.md`
    - `docs/design/UI_SCREEN_BRIEF_TEMPLATES.md`
    - `docs/design/CODE_FIRST_UI_PROMPT_COOKBOOK.md`
    - `frontend/src/pages/Onboarding/WelcomeGateV1.tsx`
    - `frontend/src/config/routes.ts`
    - `docs/figma/FIGMA_DESIGN_URL_NODEID_CAPTURE_HPP.md`
  - DoD:
    - Exact Figma Design URL plus stable `fileKey` and `nodeId` are recorded for
      Welcome Gate screens 2, 3, and 4
    - Runtime onboarding flow is promoted from preview-only route to canonical
      app-entry gate with deterministic startup interception
    - `has_seen_welcome_v1` persistence contract is introduced with regression
      coverage for first-run and returning-user behavior
    - Full sequence `Gate -> 4 screens -> RootTabs` is implemented without
      bypassing route/config governance
    - Locale, state, and telemetry contracts are documented and tested before
      merge-readiness is claimed


<a id="ledger-p1-ios-prototype-v2-canonical-promotion"></a>
- [ ] P1: Promote `ios prototype v2` as the canonical implementation mapping source
  - Owner: @katsiaryna_kavaleuskaya (Design + iOS)
  - Target PR: PR #1125
  - Priority: P1
  - Status: 🔄 In review
  - Area: design / iOS / Figma promotion
  - Finding Type: canonical design-source promotion
  - Reason: The normalization work is now implemented on branch via
    `ios prototype v2` (`AhyS6u4dZXMRHVUDO3Cfn6`) with stable `screen ID ->
    nodeId` registry. This backlog item remains open only until PR #1125 merges
    and the v2 registry becomes the canonical repo state. The raw
    `ios prototype` (`hr71gseIO7EY0SnHFXMVs9`) stays `reference_only`.
  - Links:
    - `docs/figma/ios_prototype_v2/README.md`
    - `docs/figma/FIGMA_IOS_PROTOTYPE_V2_RECONCILIATION.md`
    - `docs/runbooks/sessions/FIGMA_MCP_SESSION_2026-03-11_ios-prototype-check.md`
    - `docs/runbooks/FIGMA_MCP_RUNTIME_MATRIX.md`
    - `docs/figma/FIGMA_IOS_PROTOTYPE_V2_CODE_CONNECT_READINESS.md`
    - `ios/PulsePlate/Welcome/WelcomeFlowView.swift`
    - `ios/PulsePlate/Screens/PaywallScreen.swift`
  - DoD:
    - PR #1125 is merged with the `ios prototype v2` registry and evidence docs
    - `ios prototype v2` is treated as the implementation-safe source for the
      current iOS funnel slice
    - Raw `ios prototype` remains explicitly `reference_only`
    - Any remaining Code Connect work continues under the separate activation
      backlog item, not this normalization/promotion item


<a id="ledger-p1-ios-prototype-v2-bmi-onboarding-polish"></a>
- [ ] P1: Polish `ios prototype v2` BMI + onboarding slice in a separate MCP lane
  - Owner: @katsiaryna_kavaleuskaya (Design + iOS)
  - Target PR: PR-TBD-FIGMA-IOS-BMI-ONBOARDING-POLISH
  - Priority: P1
  - Status: 📋 Planned
  - Area: design / iOS / Figma polish
  - Finding Type: runtime-aligned follow-up
  - Reason: PR #1132 intentionally scopes the polish pass to `Home`, `Paywall`,
    `Profile`, `Weekly Plan`, and `Shopping List`. `BMI` plus the two onboarding
    screens must continue in a separate worktree/PR lane so the first polish PR
    stays narrow and reviewable.
  - Links:
    - `docs/figma/ios_prototype_v2/README.md`
    - `docs/figma/FIGMA_IOS_PROTOTYPE_V2_RECONCILIATION.md`
    - `docs/runbooks/sessions/FIGMA_MCP_SESSION_2026-03-11_ios-prototype-check.md`
    - `ios/PulsePlate/Screens/BMICalculatorScreen.swift`
    - `ios/PulsePlate/Welcome/WelcomeFlowView.swift`
    - PR #1132
  - DoD:
    - Dedicated worktree/branch exists for `BMI + Onboarding`
    - MCP-only capture sources are refreshed for `iOS_BMI`,
      `iOS_Onboarding_01_Welcome`, and `iOS_Onboarding_02_Value_Usage`
    - Figma node map is updated only for those screens in the follow-up PR
    - Follow-up PR includes its own `docs/review/PR_<N>_FIXED_MAPPING.md`
      artifact and canonical PR-body mirror
    - `pre-commit run --all-files` and `make verify` pass on the follow-up PR


- [ ] P1: Explainer contract and payload design for FREE / PRO / VIP
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (contract-first unblocker)
  - Target PR: PR-TBD-EXPLAINER-CONTRACT-PAYLOADS
  - Status: 📋 Planned
  - Reason (EN): The first implementation slice should lock backend-owned payload shapes before any UI work. PulsePlate needs canonical response shapes for explainer cards that reuse current BMI, interpretation, adherence, and weekly-plan entities instead of inventing client heuristics. (RU: Сначала нужен каноничный backend contract для explainer payloads; UI не должен сам собирать бизнес-логику.)
  - Links:
    - `docs/product/WELLNESS_EXPLAINERS_TENSORTONIC_ADAPTATION_NOTE.md`
    - `docs/product/FREE_PRO_CONTRACT.md`
    - `app/schemas/`
    - `app/routers/`
  - DoD:
    - High-level contract documents backend-owned `explainer_card` fields for FREE / PRO / VIP
    - Existing product entities are mapped to explainer payload sources without client-side business logic duplication
    - No runtime implementation is required in the design PR


- [ ] Penpot + Storybook fallback bridge for design handoff
  - Owner: @katsiaryna_kavaleuskaya (Design + FE)
  - Target PR: PR/Penpot-Storybook-Bridge
  - Priority: P1
  - Status: ▶️ In progress (Primary web-review path)
  - Area: design / frontend / docs
  - Finding Type: fallback workflow
  - Reason: Storybook and token SoT already exist in repo, so this bridge is the
    canonical low-cost design review path for web. Figma Code Connect remains an
    optional auxiliary mapping workflow rather than a gating dependency.
  - Links:
    - `docs/architecture/ADR_PENPOT_STORYBOOK_BRIDGE_FALLBACK_SEAM_2026-03-07.md`
    - `docs/design/PENPOT_STORYBOOK_BRIDGE.md`
    - `docs/design/PENPOT_CTA_REVIEW_PACKET_TEMPLATE.md`
    - `docs/design/PENPOT_CTA_REVIEW_PACKET_WEB_HOME_OPEN_SETUP.md`
    - `docs/design/PENPOT_CTA_REVIEW_PACKET_WEB_PROGRESS_EXPORT_PDF.md`
    - `docs/runbooks/FIGMA_MCP_DESIGN_SYSTEM_RULES.md`
    - `frontend/.storybook/main.ts`
    - `frontend/src/stories/PulsePlateDesignSystemGuidelines.mdx`
  - DoD:
    - Penpot bridge is documented as the canonical minimal handoff path for web review
    - Storybook remains canonical web review surface
    - Seam ADR remains linked from this ledger item and owns explicit exit criteria
    - Token SoT linkage is explicit in the bridge doc
    - CTA/design review packet format is defined without Code Connect dependency
    - Tool-neutral design review reference replaces Figma-only required fields in handoff contracts

<a id="ledger-p1-frontend-ai-parity"></a>
- [ ] P1: Frontend parity for new AI-agent and LLM reliability features
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (quality visibility)
  - Target PR: PR-TBD (`feat/frontend-ai-reliability-parity-w1`)
  - Status: 🟡 In progress (wave 1: Home + iOS Home entry + typed `/api/v1/pro/cbt/insight` parity)
  - Reason (EN): Backend quality features (RAG confidence, verification pipeline, recursive/philosophical controls) must be visible in web/iOS UX; otherwise quality work remains opaque and user trust/conversion suffers. (RU: Новые quality-фичи ИИ должны быть отражены во фронтенде; иначе улучшения качества не видны пользователю и не влияют на доверие/конверсию.)
  - Links:
    - frontend/src/api/openapi.json
    - frontend/src/api/schema.ts
    - frontend/src/api/premium/cbt-insight.ts
    - frontend/src/pages/Home.tsx
    - ios/PulsePlate/Views/HomeView.swift
    - ios/PulsePlate/Views/AIInsightView.swift
    - docs/design/NUTRITION_COACHING_DESIGN.md
    - docs/contracts/RAG_CONTRACT.md
  - DoD:
    - [ ] UI contracts for `sources[]`, confidence, verification state are aligned with backend schema
    - [ ] Frontend/iOS screens for AI assistant reflect reliability state (validated / partial / fallback)
    - [ ] Thin-client guards remain green; no business logic duplication on clients
    - [ ] Deterministic contract tests added for new AI-quality response fields


- [ ] P1: Phase 2 — Remove nosec allowlist by migrating legacy suppressions
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-TBD-NOSEC-ALLOWLIST-PHASE2
  - Area: guards / security policy / tech-debt
  - Finding Type: allowlist TTL enforcement follow-up
  - Reason: Nosec policy allowlist (Phase 1) has TTL per line; entries must be migrated to full nosec format or removed so allowlist shrinks to zero and guard does not rely on allowlist.
  - Links:
    - `tests/guards/test_nosec_policy_guard.py`
    - `tests/guards/fixtures/nosec_policy_allowlist.txt`
    - `AGENTS.md` (Bandit / nosec policy)
  - DoD:
    - Allowlist reduced to 0 entries (or removed)
    - Each legacy `# nosec` either removed (fix) or converted to full format (Bxxx:, remove-by: date, ref:)
    - Guard no longer uses allowlist (or allowlist file removed)


<a id="ledger-p1-bandit-lower-severity-remediation"></a>
- [ ] P1: Phase 2 — Remediate Bandit lower-severity findings by rule family
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-TBD-BANDIT-LOWER-SEVERITY-REMEDIATION
  - Area: security / CI / static analysis
  - Finding Type: Bandit LOW/MEDIUM inventory follow-up
  - Reason: PR3 adds deterministic grouped inventory for Bandit findings below
    HIGH severity while keeping HIGH fail-closed. The inventory is not a
    suppression mechanism and does not tighten the merge gate to MEDIUM yet;
    remediation should proceed in narrow follow-up PRs by Bandit rule id and
    path bucket.
  - Links:
    - `docs/security/BANDIT_LOWER_SEVERITY_INVENTORY.md`
    - `scripts/ci/summarize_bandit_report.py`
    - `.github/workflows/ci.yml` (`Enforce Bandit HIGH severity gate`)
  - DoD:
    - One rule family or path bucket remediated per PR unless coordinator opens
      a broader lane
    - No broad `# nosec` additions; every unavoidable suppression follows root
      `AGENTS.md` nosec policy
    - MEDIUM gate tightening considered only after grouped inventory shrinks to
      an actionable baseline


<a id="ledger-p1-compose-v2-migration"></a>
- [x] P1: Migrate command surface to `docker compose` v2 only
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR #1567 (`codex/compose-v2-command-surface`)
  - Area: infra / docs / operator workflow
  - Finding Type: command-surface consistency
  - Status: Landed
  - Reason: The active repo command surface now uses `docker compose` v2 syntax. Makefile targets, active operator scripts, and current runbook guidance no longer recommend the legacy hyphenated Compose v1 command, while compose file names such as `docker-compose.production.yaml` remain unchanged.
  - Links:
    - `Makefile`
    - `docs/deploy/README.md`
    - `docs/runbooks/ENGINEER_QUICKPATH.md`
    - `AGENTS.md`
    - `docs/architecture/ADR_COMPOSE_V2_COMMAND_SURFACE_SEAM_2026-03-09.md`
    - `tests/test_repo_policy_guards.py`
  - DoD:
    - Makefile targets use `docker compose`
    - Active runbooks/docs no longer recommend `docker-compose` as the target state
    - Transitional fallback language is removed from `AGENTS.md` and quick-path docs
    - Grep-based verification for `docker-compose` is documented or automated


- [ ] Accessibility: ship-blocking UI checklist + enforcement for Web+iOS
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (release quality)
  - Target PR: TBD
  - Status: 📋 Planned
  - Reason: Accessibility must be enforced as a process, not a best-effort review comment. We need deterministic checks
    (or at least guardrails) for labels, focus, contrast, and touch targets so new UI ships safely.
  - Links:
    - `docs/orchestration/IOS_FRONTEND_MULTIAGENT_PLAYBOOK.md` (a11y checklist section)
    - `ios/AGENTS.md` (HIG + CI constraints)
    - `frontend/AGENTS.md` (web testing and thin-client guards)
  - DoD:
    - PR template/checklist requires explicit a11y verification (iOS + Web)
    - Web: jsx-a11y (or equivalent) rules applied to new/changed UI components
    - iOS: documented checklist + at least one deterministic guard approach for common failures
    - No new UI components added without a11y confirmation in PR evidence


- [ ] P1 (postponed): CI iOS workflow dedup (extract shared helpers / composite action)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: TBD
  - Reason: Avoid drift between `ios-tests` and `ios-ui-smoke` jobs (Xcode pinning, destination selection, boot logic, xcodebuild wrapper). Requested in PR-607 review; deferred to keep remediation PR scope tight.
  - Links:
    - .github/workflows/ci.yml
    - docs/audit/PR_Q2B_IOS_UITESTS_BUNDLE_LOAD_AUDIT.md
  - DoD:
    - One shared implementation for destination selection + bootstatus gating + xcodebuild wrapper (script or composite action)
    - Both iOS jobs reuse the same logic (no duplicated Python snippets)
    - CI remains deterministic (UDID-only destination, no `OS=latest`)


- [ ] P1: iOS open-source implementation gate (repo-wide scan + thin-client conformance)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-TBD-IOS-OSS-IMPLEMENTATION-GATE
  - Status: 🟡 Prioritized
  - Reason: Product quality now depends on deterministic iOS conformance checks before merge; Swift guard tests exist, but we need a repo-wide open-source gate that validates implementation patterns and prevents silent drift.
  - Links:
    - docs/audit/PR_559_ANTI_DUPLICATION_GUARDS.md
    - ios/PulsePlateTests/Guards/ThinClientGuardsTests.swift
    - docs/orchestration/IOS_FRONTEND_MULTIAGENT_PLAYBOOK.md
  - DoD:
    - GH Actions step scans iOS app Swift sources for forbidden patterns
    - Excludes fixtures/mocks
    - Thin-client/APIClient invariants are enforced in CI for changed iOS files
    - Documented in ios/AGENTS.md


- [ ] PR-595 iOS Thin HTTP Adapter Audit
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-595
  - Status: 🟡 In progress (draft)
  - Reason: CodeRabbit actionable — if not recorded in ledger, it does not exist. Audit-first for iOS networking layer (dual-path HTTP, legacy services, DTO drift) and deterministic remediation plan.
  - Links:
    - docs/audit/PR_595_IOS_THIN_HTTP_ADAPTER_AUDIT.md
    - <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/595>
  - DoD:
    - Evidence captured for dual-path networking (`file:line → transport`)
    - Legacy services and direct HTTP entry points enumerated
    - DTO/contract drift documented at network boundary
    - Remediation plan defined (PR-596 scope)


- [ ] Stabilize/restore PlateViewTests in CI (iOS)
  - Owner: @katsiaryna_kavaleuskaya
  - Target PR: TBD (separate from PR-559)
  - Priority: P1
  - Reason: PlateViewTests were unstable historically; UI tests bundle-load is now fixed, but PlateViewTests stability + CI inclusion remains open.
  - Links:
    - ios/PulsePlateTests/PlateViewTests.swift
    - docs/audit/PR_Q2B_IOS_UITESTS_BUNDLE_LOAD_AUDIT.md
    - <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/607>
  - DoD:
    - PlateViewTests stabilized (no flaky failures)
    - PlateViewTests included in CI signal (job or explicit `-only-testing` list)
    - CI green with PlateViewTests included

- [ ] P1: Locale-safe Nutrition Setup numeric parsing on web
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-TBD-WEB-NUTRITION-SETUP-LOCALE
  - Area: frontend / nutrition setup / i18n
  - Finding Type: locale parsing regression risk
  - Reason: Nutrition Setup still relies on raw `valueAsNumber` parsing for user-entered numeric fields, which is fragile for RU comma-decimal inputs and violates the existing thin-input guidance already available in the codebase.
  - Links:
    - `frontend/src/pages/NutritionSetup/SetupForm.tsx`
    - `frontend/src/components/ui/NumberInput.tsx`
    - `frontend/AGENTS.md`
  - DoD:
    - Setup inputs accept RU comma and EN dot decimal formats where appropriate
    - Parsing contract is implemented once (native normalization or `NumberInput`), not duplicated
    - Focused tests cover valid RU/EN input, invalid values, and backend payload shape


- [ ] Conversion Safety: paywall/onboarding/result-screen checklists + minimal analytics event taxonomy
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (growth / App Store safety)
  - Target PR: TBD
  - Status: 📋 Planned
  - Reason: Conversion optimizations must remain wellness-safe and App Store compliant. We need a consistent checklist
    to avoid “pretty UI that doesn’t convert” and to ensure analytics captures the funnel deterministically.
  - Links:
    - `docs/orchestration/IOS_FRONTEND_MULTIAGENT_PLAYBOOK.md` (conversion checklist section)
    - `docs/contracts/PRODUCT_TIER_MAP.md` (FREE/PRO/VIP differentiation; canonical)
  - DoD:
    - Paywall + onboarding + results-screen checklist documented and used in PR descriptions
    - Minimal event taxonomy defined (activation + paywall funnel + conversion) with properties
    - Copy guidance explicitly avoids medical claims and dark patterns


- [ ] FitChef assets: establish a reusable SVG/Lottie pipeline + usage guide
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (brand consistency)
  - Target PR: TBD
  - Status: 📋 Planned
  - Reason: FitChef is the brand anchor, but without an asset pipeline + constraints (states, placement, tone), assets
    will be re-created ad-hoc and drift. We need a repeatable way to request, review, and ship assets.
  - Links:
    - `docs/orchestration/IOS_FRONTEND_MULTIAGENT_PLAYBOOK.md` (fitchef-asset-manager role)
    - Root `AGENTS.md` (wellness-safe language boundaries)
  - DoD:
    - FitChef state list defined (welcome/success/error/empty/loading) with “do/don’t” usage notes
    - Asset packaging rules documented (no text baked into images; localization-safe)
    - A minimal starter pack exists (at least 3 states) and is used in one Web screen and one iOS screen


<a id="ledger-p1-fitchef-umbrella-foundation"></a>
- [ ] P1: FitChef umbrella initiative foundation
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (orchestration / brand / App Store / coaching)
  - Target PR: PR #1140 -> PR #1143 -> PR #1150 -> PR #1154 -> PR #1159 (structured coach direction) -> PR #1214 (structured coach contract freeze) -> PR #1215 (PRO Distortion Simulator runtime) -> PR #1870 (VIP Identity Loop Mapper runtime) -> PR #1873 (Signal vs Noise report/content contract lane) -> PR #1879 (RU App Store localization contract) -> PR #1883 (RU visual-QA prep) -> PR-TBD-FITCHEF-LOCALIZATION-ES (active)
  - Status: 🚧 In progress
  - Reason (EN): FitChef already exists as a live VIP mascot/coaching surface under `/api/v1/insight/fitchef*`, but the next product wave needs one governed umbrella epic that preserves the current canon while splitting future work into clean PR families: visual/App Store, then structured coaching/runtime. This foundation also isolates mascot/App Icon asset promotion from docs/contracts work so local asset diffs never leak into governance PRs.
  - Links:
    - `docs/contracts/FITCHEF_INITIATIVE_FOUNDATION.md`
    - `docs/contracts/FITCHEF_APP_STORE_VISUAL_CONTRACT.md`
    - `docs/contracts/FITCHEF_MASCOT_ASSET_TAXONOMY.md`
    - `docs/contracts/FITCHEF_APP_STORE_PRODUCTION_PACK_EN.md`
    - `docs/contracts/FITCHEF_STRUCTURED_COACH_CONTRACT.md`
    - `docs/contracts/FITCHEF_MASCOT_PHASE2_CONTRACT.md`
    - `docs/insights/CBT_COACHING_PRODUCT_WAVE.md`
    - `docs/contracts/API_CANONICAL_MAP.md`
    - `app/routers/fitchef_insight.py`
    - `app/services/fitchef_runtime.py`
    - `AGENTS.md`
  - Progress:
    - `PR #1140` merged on March 12, 2026 for the foundation/docs-only lane
    - `PR #1143` merged on March 12, 2026 for the visual/App Store contract lane
    - `PR #1150` merged on March 13, 2026 for the mascot asset taxonomy lane
    - `PR #1154` merged on March 13, 2026 for the governed `EN` App Store production pack lane
    - `PR #1159` established the structured coach direction while preserving the live mascot canon
    - `PR #1214` merged on March 21, 2026 for the structured coach contract freeze (`29a11e62e38307dd4cc7414bffc159b508878744`)
    - `PR #1215` merged on March 21, 2026 for the feature-gated PRO Distortion Simulator runtime at `POST /api/v1/pro/fitchef/explain` (`70bdbd9e51d977d440b605eed3064c71212cff97`)
    - `PR #1870` merged on 2026-06-03 for the bounded VIP Identity Loop Mapper runtime at `POST /api/v1/vip/fitchef/insight` (`7802ed25e99e0a4f346d14487270a037bb5ec97a`)
    - `PR #1873` merged on 2026-06-03 for the Signal vs Noise report/content lane after VIP identity loop (`b38808e50244176d3d0c37d94d13f3289a32b032`)
    - `PR #1879` merged on 2026-06-04 for the RU App Store localization contract pack (`00e026d639679aac7cb3aed9ab5ad009eb056500`)
    - `PR #1883` merged on 2026-06-05 for the RU rendered-review prep bundle (`cf3e4c9c4d87e5c5f4e39d7bb5470984b0d0176c`)
    - `PR-TBD-FITCHEF-LOCALIZATION-ES` is the current ES App Store localization pack and cross-locale QA lane; it is docs/metadata/test-only and does not mutate Fastlane upload, runtime, screenshot binaries, preview binaries, or App Store Connect
  - Subtracks:
    - FitChef visual identity and mascot system
    - App Store screenshot and preview pack
    - FitChef structured coach contract
    - CBT Coaching Wave docs-first promotion
    - FitChef PRO structured coach runtime
    - FitChef VIP deep-coach runtime
    - FitChef analytics and action routing
    - FitChef localization wave EN -> RU -> ES
  - DoD:
    - Umbrella initiative contract exists and explicitly preserves the live `/api/v1/insight/fitchef*` canon
    - Root and scoped `AGENTS.md` files encode FitChef invariants: no duplicate nutrition math, no LLM source-of-truth, no FREE open-ended coach runtime, structured DTO rendering, routed actions only, mandatory fallback templates
    - Follow-up PR chain is explicit for visual/App Store and structured-coach/runtime lanes
    - First App Store localization wave is fixed as `EN` only
    - `RU` and `ES` localization follow-ups are anchored as separate backlog items with their own target PR placeholders
    - Foundation/docs PRs remain docs-only and do not carry mascot or App Icon binary asset promotion


<a id="ledger-p1-distortion-simulator-wave"></a>
- [x] P1: Distortion Simulator structured coaching lane
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (product differentiation / CBT coaching)
  - Target PR: PR #1215 (`feat(fitchef): add PRO structured coaching runtime`)
  - Status: Landed via PR #1215 on 2026-03-21 with merge commit `70bdbd9e51d977d440b605eed3064c71212cff97`.
  - Reconciliation note: PR #1865 is the retroactive docs-only ledger closeout
    for the already-landed PRO Distortion Simulator lane. Future PRs that close
    ledger items should still update this ledger in the same PR or same/next-day
    follow-up.
  - Reason (EN): The repo already contains CBT distortion taxonomy and structured thought-record knowledge. PR #1215 turned that knowledge into the bounded, feature-gated PRO `Distortion Simulator` runtime at `POST /api/v1/pro/fitchef/explain` instead of widening into broad open-ended chat. `POST /api/v1/pro/fitchef/recommend` remains a separate contract-frozen follow-up.
  - Links:
    - `docs/insights/CBT_COACHING_PRODUCT_WAVE.md`
    - `docs/cbt/cognitive_restructuring.md`
    - `docs/cbt/thought_records.md`
    - `docs/contracts/FITCHEF_STRUCTURED_COACH_CONTRACT.md`
    - `docs/analytics/METRICS_CATALOG.md`
  - DoD:
    - Distortion Simulator contract is additive to the existing structured coach route family
    - PRO runtime remains wellness-only, request-scoped, non-clinical, feature-gated, and fail-closed
    - Response includes structured reframe fields plus `sources[]`, `confidence`, `warnings`, and transparency metadata
    - Deterministic tests cover auth, quota, rate limit, OpenAPI exposure, and structured response contract


<a id="ledger-p1-identity-loop-mapper-wave"></a>
- [x] P1: Identity Loop Mapper reflective coaching lane
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (premium reflection / behavior change)
  - Target PR: PR #1870 (`feat(fitchef): add VIP Identity Loop Mapper structured runtime`)
  - Status: Landed via PR #1870 on 2026-06-03 with merge commit `7802ed25e99e0a4f346d14487270a037bb5ec97a`.
  - Reason (EN): Weekly reflection and slip-support already exist, but the next premium layer should formalize belief -> behavior -> payoff -> replacement action mapping as a bounded VIP tool rather than widening into generic chat. This gives the reflection lane a stronger product identity without changing the live mascot canon. PR #1870 registered `POST /api/v1/vip/fitchef/insight`, kept the live mascot family unmigrated, and left `chat`, `week-repair`, Signal vs Noise, semantic cache, GraphRAG, frontend/iOS, food-data, and plan adaptation out of scope.
  - Links:
    - `docs/insights/CBT_COACHING_PRODUCT_WAVE.md`
    - `docs/psychology/motivation_theories.md`
    - `docs/orchestration/FITCHEF_SAFE_PERSONALIZATION_PROTOCOL.md`
    - `docs/contracts/FITCHEF_STRUCTURED_COACH_CONTRACT.md`
    - `docs/analytics/METRICS_CATALOG.md`
  - DoD:
    - Identity Loop Mapper contract is additive to existing VIP structured coach plans
    - Runtime preserves safe personalization rules and avoids therapist/diagnostic framing
    - Structured output covers belief, behavior, reward, replacement action, and repair path
    - Deterministic tests cover auth, quota, rate limit, and response envelope stability


<a id="ledger-p1-signal-noise-report-lane"></a>
- [x] P1: Signal vs Noise report lane for CBT coaching GTM
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (GTM / product strategy / founder content)
  - Target PR: PR #1873 (`docs(coaching): promote Signal vs Noise report lane after VIP identity loop`)
  - Status: Landed via PR #1873 on 2026-06-03 with merge commit `b38808e50244176d3d0c37d94d13f3289a32b032`.
  - Reason (EN): The article-inspired `Signal vs Noise` concept fits the repo better as a high-signal weekly report and founder-content pipeline than as a runtime feature. The lane should reuse the existing AI report templates and KPI-driven GTM structure so content decisions stay measurable and wellness-safe.
  - Links:
    - `docs/insights/CBT_COACHING_PRODUCT_WAVE.md`
    - `docs/insights/SIGNAL_VS_NOISE_REPORT_LANE.md`
    - `docs/audience_pack/AI_REPORT_TEMPLATES.md`
    - `docs/marketing/GTM_NOTES_DEV_ONLY.md`
    - `docs/audience_pack/MARKETING_DESIGN_OVERVIEW.md`
  - DoD:
    - One canonical report/playbook lane exists for weekly high-signal coaching and wellness AI briefs
    - Report outputs stay separate from runtime surfaces and do not create new open-ended LLM endpoints
    - Every report block includes claim type, evidence status, confidence, owner, metric, check date, and stop/continue rule
    - Wellness-safe language and disclaimer references are explicit in the lane docs

<a id="ledger-p2-pr1437-docker-ci-doc-governance-followup"></a>
- [x] P2: PR #1437 Docker/CI docs-governance and OpenAPI fallback follow-up
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR `#1437`
  - Area: docs / governance / local verify determinism
  - Reason (EN): Post-open bot review on PR `#1437` surfaced same-lane docs-governance and CI-fallback gaps: the Docker/CI packet and merge matrix needed proximate `file:line` evidence for repo-truth assertions, the `security-floor` seam entry needed pointer-safe evidence anchors, and the `Makefile` `openapi` fallback needed deterministic interpreter selection. The fixes stayed in-scope for the current PR because they do not widen runtime or deploy behavior. (RU: После post-open review в PR `#1437` вскрылись same-lane пробелы: packet/matrix требовали proximate `file:line` evidence, backlog seam требовал pointer-safe anchors, а `Makefile` `openapi` fallback — детерминированный выбор интерпретатора. Эти исправления оставлены в рамках текущего PR, потому что не расширяют runtime/deploy scope.)
  - Status: Closed in PR `#1437` on 16 April 2026; current head keeps the Docker/CI governance evidence local to the packet/matrix/ledger and makes the `openapi` fallback prefer `python3`, then `python`, while still failing closed if no usable Python 3 interpreter exists.
  - Links:
    - `docs/orchestration/DOCKER_CI_DISCIPLINE_PR_SERIES_PACKET_2026-04-16.md`
    - `docs/orchestration/PR_MERGE_WORKFLOW_MATRIX.md`
    - `docs/architecture/ADR_DOCKER_BUILD_PROVENANCE_WORKAROUND_2026-03-01.md:47-60`
    - `docs/review/PR_1437_FIXED_MAPPING.md`
    - `Makefile:451-461`
  - DoD:
    - Packet/matrix repo-truth statements keep proximate `file:line` evidence for `.dockerignore`, `IMAGE_REF`, `frontend/Dockerfile.caddy-spa`, the deferred provenance seam, and the mandatory `qa-engineer-agent -> bug-hunter` lane
    - The `security-floor` seam entry preserves `file:line` evidence while retaining stable anchors for ledger targeting
    - `Makefile` `openapi` fallback prefers `python3`, then `python`, and fails closed if neither exists or if the selected interpreter is not Python 3
    - The closeout remains docs/tooling-only and does not widen the Docker deploy/runtime topology scope


- [x] P2: FitChef App Store localization RU
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2 (ASO / localization)
  - Target PR: PR #1879 (`docs(fitchef): promote RU App Store localization pack contract`) -> PR #1883 (`docs(fitchef): add RU App Store visual QA prep bundle`)
  - Status: ✅ Landed via PR #1879 on 2026-06-04 with merge commit `00e026d639679aac7cb3aed9ab5ad009eb056500`; rendered-review prep landed via PR #1883 on 2026-06-05 with merge commit `cf3e4c9c4d87e5c5f4e39d7bb5470984b0d0176c`.
  - Reason (EN): The first FitChef App Store wave is intentionally `EN` only. Russian localization now opens as its own governed metadata/screenshot/preview contract pack after the `EN` visual contract and production pack are frozen, so copy, screenshot ordering, and safe-area rules do not drift.
  - Links:
    - `docs/contracts/FITCHEF_INITIATIVE_FOUNDATION.md`
    - `docs/contracts/FITCHEF_APP_STORE_PRODUCTION_PACK_EN.md`
    - `docs/contracts/FITCHEF_APP_STORE_PRODUCTION_PACK_RU.md`
    - `appstore/fitchef/ru-RU/metadata/app_store_metadata.json`
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-fitchef-umbrella-foundation`
  - DoD:
    - `RU` screenshot headlines and subtext are derived from the approved `EN` App Store contract
    - `RU` metadata pack is tracked under its own follow-up PR and does not change the canonical `EN` layout rules
    - `RU` preview storyboard/script stays under 30 seconds and remains script-only until a governed capture/export path opens
    - Any `RU` binary asset/export, Fastlane upload, or App Store Connect mutation work remains separated from governance-only PRs
    - Deferred release-lane checks before protected upload: rendered RU screenshot/video visual QA, AI/privacy/reviewer-note reconciliation against the submitted build, and native RU/ASO copy review


- [x] P2: FitChef App Store localization ES
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2 (ASO / localization)
  - Target PR: PR #1886 (`docs(fitchef): promote multilingual App Store localization QA wave`)
  - Status: ✅ Landed via PR #1886 on 2026-06-05 with merge commit `26b7cf4fd817d0db5d761fddb4acbcc7b476c917`; EN/RU/ES packs now share a governed localization QA contract.
  - Reason (EN): Spanish localization is a follow-up wave after the governed `EN` and `RU` contract packs. It now opens as a peer metadata/screenshot/preview contract plus cross-locale EN/RU/ES review prep so future ASO copy, screenshot exports, and review metadata remain traceable in the canonical backlog.
  - Links:
    - `docs/contracts/FITCHEF_INITIATIVE_FOUNDATION.md`
    - `docs/contracts/FITCHEF_APP_STORE_PRODUCTION_PACK_ES.md`
    - `appstore/fitchef/es-ES/metadata/app_store_metadata.json`
    - `appstore/fitchef/localization_qa/cross_locale_review_prep.md`
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-fitchef-umbrella-foundation`
  - DoD:
    - `ES` screenshot headlines and subtext are derived from the approved `EN` App Store contract
    - `ES` metadata pack is tracked under its own follow-up PR and does not change the canonical `EN` layout rules
    - `ES` preview storyboard/script stays under 30 seconds and remains script-only until a governed capture/export path opens
    - Cross-locale EN/RU/ES QA prep flags copy length, safe-area, FitChef overlap, UI/copy mismatch, and wellness-claim review risks
    - Any `ES` asset/export, Fastlane upload, preview binary, screenshot binary, or App Store Connect mutation work remains separated from governance-only PRs


- [ ] P1: FitChef App Store rendered review and TestFlight readiness
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (release readiness / App Store evidence)
  - Target PR: PR #1890 `codex/fitchef-appstore-rendered-review-testflight-readiness`
  - Status: 🚧 Active as the current FitChef App Store release-readiness review lane after EN/RU/ES localization packs landed.
  - Carryover note: PR #1890 also includes a test-only coverage bump for `tests/test_user_coaching_state.py` after `main` CI for `889e9a0ad` reported total coverage `96.99% < 97.00%` in `app/services/coaching_state_builder.py`; no coaching-state runtime code changes are included.
  - Reason (EN): The localized FitChef packs are governed as text/JSON contracts, but release review still needs a single internal matrix tying the seven App Store shots to iOS screenshot scenarios, accessibility identifiers, reviewer classifications, privacy/AI/wellness notes, and rendered-review requirements before protected upload work can open.
  - Links:
    - `appstore/fitchef/release_readiness/shot_scenario_matrix.json`
    - `appstore/fitchef/release_readiness/rendered_review_testflight_readiness.md`
    - `docs/release/APPSTORE_SCREENSHOT_ASSET_GATE.md`
    - `docs/release/APPSTORE_REVIEWER_SUBMISSION_MATRIX.md`
    - `ios/PulsePlate/AppStore/AppStoreScreenshotContext.swift`
    - `ios/PulsePlateUITests/AppStoreScreenshotTests.swift`
  - DoD:
    - All seven FitChef shot IDs are mapped across `en-US`, `ru-RU`, and `es-ES` to canonical iOS `AppStoreScreenshotScenario` values, accessibility identifiers, and UI-test screenshot names
    - The rendered-review checklist remains `INTERNAL_REVIEW_ONLY` and records privacy, AI, wellness, line-fit, safe-area, and FitChef-overlap review requirements
    - `make ios-appstore-verify` validates the matrix, locale parity, reviewer-gate linkage, wellness-safe copy, and no-binary/no-upload boundaries
    - Protected follow-ups remain separate: Fastlane upload, App Store Connect mutation, screenshot/video binaries, final media export, and protected environment activation


- [ ] Optional: tighten guard false-positives (comment stripping / pattern tuning)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: TBD
  - Reason: avoid guard flakiness if comments include examples
  - Links:
    - ios/PulsePlateTests/Guards/ThinClientGuardsTests.swift
  - DoD:
    - Guard remains strict but avoids comment-only hits
    - CI remains deterministic


- [x] P1: `user_knowledge` DB-level RLS / policy hardening
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (security / defense-in-depth)
  - Target PR: PR #1089 (`feat/p1-user-knowledge-rls`)
  - Status: ✅ Merged evidence (PR #1089, 2026-03-11)
  - Reason (EN): Application-layer tenant scoping prevents cross-tenant leaks in runtime retrieval, but Postgres still needed explicit DB-level RLS/policy enforcement plus a canonical session-context bridge to make the policy enforceable in runtime paths.
  - Links:
    - `docs/contracts/RAG_CONTRACT.md` (§7, §8)
    - `app/models/rag_feedback.py`
    - `core/rag/vector_rag.py`
    - `core/db_rls.py`
    - `alembic/versions/202603100101_enable_rag_user_rls.py`
  - DoD:
    - Postgres RLS policies exist for both `user_knowledge` and `rag_feedback`
    - User-bound rows use a bigint subject principal compatible with runtime-derived API-key subject isolation (no stale `users.id` FK contract)
    - Canonical transaction-local session context is set before RAG retrieval, feedback writes, and DSAR helper queries
    - Migration + rollback path documented
    - Tests or audit evidence cover deny-by-default cross-tenant access at DB layer
    - Runtime app-layer filtering remains in place (no regression to code-level scoping)


<a id="ledger-p1-scientific-reliability-pipeline"></a>
- [x] P1: Scientific reliability publication packet (evidence + article mapping)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (trust + GTM)
  - Target PR: PR-A9 (`docs/ai-scientific-reliability-packet`, merged as PR `#1512`)
  - Status: ✅ Closed. PR `#1512` merged on 24 April 2026 as
    `2c9d9f4f6bbee139b855944568d5a2d25cd0bc15`; the A9 docs-only
    evidence lane is now historical and must not be reopened as an active
    publish lane.
  - Closeout note: This reconciliation closes the stale in-progress ledger
    state after the canonical A9 packet, task analysis, audit evidence packet,
    and review mapping landed on `main`. Future evidence refreshes must create
    a new dated packet or a separate superseding follow-up instead of rewriting
    the immutable `2026-04-23` A9 snapshot. Exception approved on 30 April
    2026: this delayed closeout is limited to reconciling PR `#1512`
    (`2c9d9f4f6bbee139b855944568d5a2d25cd0bc15`) ledger truth without
    reopening the A9 evidence snapshot.
  - Reason (EN): Product differentiation requires public, evidence-based communication of currently reproducible AI reliability methods with clear claim boundaries and no medical overclaiming. The current governed proof surface is the offline logic+philosophy replay contract plus shipped runtime anchors; this lane must not imply production proof, public verification fields, or recursive execution as the canonical validated-evidence write path. (RU: Для дифференциации нужен публичный научно-достоверный пакет по AI quality-подходу с жёсткими границами claims и без медикал-оверклеймов. Текущая доказательная база в этом lane — governed offline replay contract для logic+philosophy и уже слитые runtime anchors; нельзя выдавать это за production proof, public verification truth или canonical validated-evidence write path для recursive execution.)
  - Links:
    - docs/analysis/SCIENTIFIC_INNOVATION_ANALYSIS.md
    - docs/insights/COMPREHENSIVE_PHILOSOPHY_LOGIC_MATH_CBT_ANALYSIS.md
    - docs/insights/RECURSIVE_METHODS_LLM_RAG.md
    - `docs/orchestration/contracts/LOGIC_PHILOSOPHY_REPLAY_EVAL_CONTRACT.md`
    - `docs/orchestration/WAVE6_A9_TASK_ANALYSIS_2026-04-23.md`
    - `docs/orchestration/WAVE6_A9_SCIENTIFIC_RELIABILITY_PACKET_2026-04-23.md`
    - `docs/audit/PR_A9_SCIENTIFIC_RELIABILITY_EVIDENCE_PACKET_2026-04-23.md`
    - `docs/review/PR_1512_FIXED_MAPPING.md` (merged A9 implementation mapping)
    - `docs/review/PR_1588_FIXED_MAPPING.md` (this closeout mapping)
    - `tests/test_logic_philosophy_replay_eval.py`
  - DoD:
    - Editorial plan and evidence format are documented (metrics, corpus bounds, caveats, claim boundaries)
    - One canonical evidence packet summarizes the governed offline replay result with reproducibility commands
    - Internal/public article mapping is documented against verifiable repo artifacts
    - Marketing copy checklist includes wellness-safe, evidence-only, and non-medical claims


- [ ] P1: Agent knowledge library template packs (domain-specific)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (process scalability)
  - Target PR: PR_TBD_AGENT_LIBRARY_TEMPLATE_PACKS
  - Status: 📋 Planned
  - Reason (EN): Bootstrap library artifacts are in place, but recurring cycles
    need reusable, domain-specific packs (security, RAG, UX, DS) to keep
    brainstorm-to-PR flow fast and deterministic without policy drift.
  - Links:
    - `docs/orchestration/AGENT_KNOWLEDGE_LIBRARY_WORKTREE_RUNBOOK.md`
    - `docs/library/index.md`
    - `docs/library/promotion/2026-02-19_agent-library-bootstrap_promotion-log.md`
    - `docs/orchestration/AGENT_CAPABILITY_MATRIX.md`
    - `docs/memory/kpp_knowledge_promotion_pipeline.md`
  - DoD:
    - Add template packs under `docs/library/templates/` for at least 4 tracks:
      security, RAG, UX/accessibility, data/evaluation
    - Each template includes routing card, evidence section, promotion target,
      and deferred-item ledger block
    - Add one worked example cycle using one template pack
    - `ReadLints` clean for all new docs


- [ ] P1: Skill-router parity with policy docs and requested-agent bundles
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR #1202
  - Area: orchestration / skills / bootstrap
  - Finding Type: policy-implementation drift
  - Reason: The canonical skill routing policy now documents requested-agent helper bundles and conditional skills such as `gh-address-comments` and `vercel-react-best-practices`; router logic and tests must stay in lockstep so coordinator packets do not promise skills that the runtime selector never emits.
  - Links:
    - `docs/orchestration/AGENT_SKILL_ROUTING_POLICY.md`
    - `scripts/orchestration/skill_router.py`
    - `tests/test_skill_router.py`
  - DoD:
    - Every documented requested-agent default bundle is represented in router behavior or explicitly documented as manual-only
    - Policy-only skills cannot drift out of the implementation without failing deterministic tests
    - Privileged-surface triggers and requested-agent bundle reasons are emitted in routing metadata

- [ ] P1: Privileged workflow security-review requirement for orchestration and release surfaces
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR #2067
  - Area: orchestration / release ops / security review
  - Finding Type: review-path hardening
  - Reason: Tasks touching GitHub workflows/actions, Fastlane,
    orchestration/CI/release scripts, merge-governance docs,
    Trivy/root Docker/Compose, devcontainer controls, deploy Caddy/Compose,
    frontend Caddy Dockerfile/npm manifests, iOS Gemfile/SwiftPM manifests,
    root security/quality-gate configs, root CI/deploy/test-gate helper
    scripts, root AGENTS/RUNBOOK/Makefile policy entrypoints, GitHub
    CODEOWNERS/actionlint/PR-template governance, review-bot configs, MCP
    control-plane examples, secret baseline, policy guard tests, Cloudflare
    Worker/Wrangler controls, Dependabot YAML variants, or root
    requirements/constraints manifests can change privileged automation and
    supply-chain posture; PR #2067 is the active target to centralize this
    matcher and force executable `security-auditor` review for matched surfaces.
  - Links:
    - `AGENTS.md`
    - `RUNBOOK_AGENT.md`
    - `docs/orchestration/AGENT_ROUTING_GRAPH.md`
    - `docs/orchestration/AGENT_SKILL_ROUTING_POLICY.md`
    - `scripts/orchestration/bootstrap_sync_policy.py`
    - `scripts/orchestration/skill_router.py`
    - `tests/test_bootstrap_sync_policy.py`
    - `tests/test_skill_router.py`
    - `tests/test_task_bootstrap.py`
    - `.github/workflows/`
    - `.github/actions/`
    - `ios/fastlane/`
    - `trivy/`
  - DoD:
    - Canonical docs define the privileged-surface trigger list via `bootstrap_sync_policy.py`
    - Coordinator/bootstrap preserves `security-auditor` in the executable review path for those surfaces
    - PR #2067 is merged or an explicit won't-do closeout is recorded before this checkbox is closed
    - Deterministic tests cover workflow/action/Fastlane/orchestration/release/docs/Trivy/root-Docker/devcontainer/deploy-Caddy-Compose/frontend-Caddy-Dockerfile/npm/iOS-Gemfile-SwiftPM/quality-gate-config/root-CI-deploy-test-helper/root-policy-entrypoint/GitHub-governance/review-bot-config/MCP-control-plane/secret-baseline/policy-guard-test/Cloudflare-edge/dependency-manifest
      review routing
    - Merge-readiness docs explain that this is a default requirement, not optional reviewer theater

<a id="ledger-p1-classify-ci-checks-as-hard-soft-external"></a>
- [x] P1: Coordinator automation PR2 — bootstrap engine hardening
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR #1254
  - Area: orchestration / task bootstrap / packet schema
  - Finding Type: automation rollout slice
  - Status: Materially completed via merged PR `#1254` on March 27, 2026; this slice is the landed bootstrap baseline for the later coordinator automation wave.
  - Reason: PR1 locks the governance boundary, but coordinator-first still remains policy-required rather than reliably packet-driven for every non-trivial task. The next slice must harden `task_bootstrap` and related bridge contracts without mixing in PR lifecycle or design-lane behavior.
  - Dependencies:
    - `PR-1252`
  - Lifecycle: Start → Open → Push → Review → Merge
  - Links:
    - `docs/orchestration/AUTOMATION_READINESS_MATRIX.md`
    - `scripts/orchestration/task_bootstrap.py`
    - `scripts/orchestration/native_subagent_bridge.py`
    - `tests/test_task_bootstrap.py`
  - DoD:
    - Task packet schema adds `automation_flags`
    - Task packet schema adds `pr_phase` and `design_lane_mode`
    - Task packet schema adds `needs_backlog_update`, `needs_docs_sync`, and `needs_agents_sync`
    - Deterministic tests cover coordinator-first packet stability and new schema invariants
    - No PR-open automation, Figma trigger logic, or local launcher changes are included

- [x] P2: Centralize bootstrap sync-policy constants for task packet derivation
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR #1327 (`refactor(orchestration): centralize bootstrap sync policy`)
  - Area: orchestration / task bootstrap / policy constants
  - Finding Type: follow-up hardening
  - Status: Materially completed via merged PR `#1327` (`7df804cf`) on April 4, 2026; this hardening is now part of the landed bootstrap baseline and should not remain an open prerequisite.
  - Reason: PR2 intentionally keeps sync heuristics local to `task_bootstrap.py`, but review feedback highlighted that implementation roots and sync-signal markers should eventually move into a shared policy surface so future automation slices can evolve them without editing bootstrap logic directly.
  - Dependencies:
    - `PR-1254`
  - Lifecycle: Review → Backlog → Execute
  - Links:
    - `scripts/orchestration/task_bootstrap.py`
    - `tests/test_task_bootstrap.py`
    - `docs/orchestration/AGENT_MESSAGE_PROTOCOL.md`
  - DoD:
    - Sync-signal terms and path roots move into a shared policy module or equivalent canonical config
    - `task_bootstrap.py` consumes the shared policy source instead of duplicating constants inline
    - Deterministic tests cover the shared policy contract and bootstrap integration

- [x] P1: Coordinator automation PR3 — skill routing and intent classifier
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR #1265
  - Area: orchestration / skills / intent classification
  - Finding Type: automation rollout slice
  - Status: Materially completed via merged PR `#1265` on March 28, 2026; baseline routing landed in commit `5bc96098` and the governance-lane preservation fix landed in `d3c3a9d1`, so this slice is no longer a `PR-TBD` dependency.
  - Reason: After bootstrap hardening, the next failure mode is still over- or under-selecting skills and treating unlike tasks as the same class. The routing layer needs a deterministic classifier and explicit required/recommended/conditional/blocked outputs before any lifecycle or design automation is added.
  - Dependencies:
    - `PR #1254`
  - Lifecycle: Start → Open → Push → Review → Merge
  - Links:
    - `docs/orchestration/AUTOMATION_READINESS_MATRIX.md`
    - `docs/orchestration/AGENT_SKILL_ROUTING_POLICY.md`
    - `scripts/orchestration/skill_router.py`
    - `tests/test_skill_router.py`
  - DoD:
    - Deterministic task classes cover at least `implementation`, `bugfix`, `review`, `design`, `creative_research`, `experiment`, and `pr_governance`
    - Skill decisions expose `required`, `recommended`, `conditional`, and `blocked` semantics
    - Routing stays minimal-optimal and explainable
    - No PR event hooks, Figma mutation flow, or launcher wiring are included

- [x] P1: Coordinator automation PR4 — PR lifecycle automation
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR #1266 (`docs(review): map coderabbit nitpick wrapper`)
  - Area: orchestration / PR governance / review lifecycle
  - Finding Type: automation rollout slice
  - Status: Materially completed via merged PR `#1266` (`5dfa055d`) on March 28, 2026; this slice now serves as the landed baseline input for PR5.
  - Reason: The canonical docs already require a post-open `qa-engineer-agent -> bug-hunter` loop, but the behavior is still policy-only and easy to forget. The PR lifecycle slice must turn that requirement into deterministic PR-phase automation without widening into design or brainstorming lanes.
  - Dependencies:
    - `PR #1265`
  - Lifecycle: Start → Open → Push → Review → Merge
  - Links:
    - `docs/orchestration/AUTOMATION_READINESS_MATRIX.md`
    - `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md`
    - `RUNBOOK_AGENT.md`
    - `docs/orchestration/TIER1_CI_CD_PR_SERIES_RUNBOOK.md`
  - DoD:
    - PR packet or equivalent phase contract distinguishes post-open review from generic task execution
    - Mandatory review-path synthesis includes `qa-engineer-agent -> bug-hunter`
    - Current-head review-preparation outputs are explicit and deterministic
    - Docs/runbooks/ledger references stay in sync with the lifecycle contract
    - No creative research or design execution behavior is added

- [x] P1: Coordinator automation PR5 — creative research and design/Figma activation
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR #1268 (`feat(orchestration): gate design lanes`)
  - Area: orchestration / research / design tooling
  - Finding Type: automation rollout slice
  - Status: Materially completed via merged PR `#1268` (`ef7ac2fe`) on March 28, 2026; for the orchestration continuation track, this slice is now baseline and the next non-duplicate repo lane moves to the local workforce follow-on PRs below.
  - Reason: Creative research and design lanes are the broadest automation surface and must come after bootstrap and skill routing stabilize. This slice should add explicit trigger rules and safe activation boundaries instead of letting design/Figma behavior emerge implicitly.
  - Dependencies:
    - `PR #1266`
  - Lifecycle: Start → Open → Push → Review → Merge
  - Links:
    - `docs/orchestration/AUTOMATION_READINESS_MATRIX.md`
    - `docs/orchestration/RESEARCH_BRAINSTORMING_PROTOCOL.md`
    - `docs/runbooks/DESIGN_TOOLING_OPERATING_MODEL.md`
    - `docs/figma/`
  - DoD:
    - `creative_research` has explicit trigger rules
    - Code-native design brief path is defined before any Figma mutation path
    - Figma lane activates only with a valid design trigger and a valid packet/URL/node-id or explicit creation mode
    - Safe source-precedence and blocker rules are documented
    - No broad PR-governance refactor or merge-readiness semantic change is included

<a id="ledger-p1-local-workforce-pr-a-bootstrap-seam"></a>
- [x] P1: Local workforce PR-A — extend the canonical coordinator bootstrap seam
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR #1329 (additive `message_envelope` derivation) + PR #1339 (`skill_router` `docs_only` parity, `envelope_mode_hint`, ledger/protocol SoT)
  - Area: orchestration / task bootstrap / skill routing / local workforce
  - Finding Type: RFC follow-on slice
  - Status: **Closed** — PR #1329 merged on `main`; PR #1339 squash-merged to `main` as `3b243a003daf9101b00639cada199a27e19c7e83` (parity: `route_skills` + `bootstrap_sync_policy.resolve_analysis_envelope_mode`, `envelope_mode_hint`, fail-closed docs-only paths, tests, SoT docs).
  - Reason: `docs/orchestration/COMPOSER_BOOTSTRAP_KIT_PR1.md` explicitly requires extending the existing coordinator bootstrap seam instead of introducing a second packet system. Coordinator automation PR2-PR5 plus the sync-policy extraction are already landed, so the next repo lane must add any local-workforce semantics additively on top of `task_bootstrap.py`, `skill_router.py`, and `bootstrap_sync_policy.py`.
  - Dependencies:
    - `PR #1325`
    - `PR #1327`
    - `PR #1328`
  - Lifecycle: Start → Open → Push → Review → Merge
  - Links:
    - `docs/orchestration/LOCAL_WORKFORCE_PR_A_TASK_PACKET_2026-04-05.md`
    - `docs/orchestration/COMPOSER_BOOTSTRAP_KIT_PR1.md`
    - `docs/orchestration/PulsePlate_Local_Agent_Workforce_System_Design_Packet_v1_2.md`
    - `scripts/orchestration/task_bootstrap.py`
    - `scripts/orchestration/skill_router.py`
    - `scripts/orchestration/bootstrap_sync_policy.py`
    - `tests/test_task_bootstrap.py`
    - `tests/test_skill_router.py`
    - `tests/test_bootstrap_sync_policy.py`
  - DoD:
    - Any new local-workforce semantics land additively on the canonical bootstrap/routing surfaces
    - Docs parity stays in sync across `AGENT_SKILL_ROUTING_POLICY.md`, `AGENT_MESSAGE_PROTOCOL.md`, and workflow docs where required
    - Deterministic tests cover the updated packet and routing contracts
    - No standalone action-packet or parallel bootstrap schema system is introduced
    - No launcher/runtime auto-start claims are added to repo docs

<a id="ledger-p1-local-workforce-pr-b-reflection-protocol"></a>
- [x] P1: Local workforce PR-B — extend the canonical reflection protocol first
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR #1339 (protocol-first reflection extensions bundled with the PR-A parity slice)
  - Area: orchestration / reflection / knowledge promotion
  - Finding Type: RFC follow-on slice
  - Status: **Closed** — same squash merge as PR-A: `3b243a003daf9101b00639cada199a27e19c7e83`; `docs/orchestration/AGENT_REFLECTION_PROTOCOL.md` includes bootstrap/routing mismatch, post-open review reflection, and KPP promotion wording.
  - Reason: The local workforce RFC requires reflection changes to land through the canonical reflection protocol before any helper or schema material is promoted. This keeps knowledge-promotion semantics inside the existing repo SoT instead of creating a second reflection contract.
  - Dependencies:
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-local-workforce-pr-a-bootstrap-seam` (closed with PR #1339)
  - Lifecycle: Start → Open → Push → Review → Merge
  - Links:
    - `docs/orchestration/COMPOSER_BOOTSTRAP_KIT_PR1.md`
    - `docs/orchestration/AGENT_REFLECTION_PROTOCOL.md`
    - `docs/orchestration/AGENT_MESSAGE_PROTOCOL.md`
  - DoD:
    - Reflection changes land in the canonical protocol before any derived helper/schema material
    - No parallel reflection contract is introduced beside `AGENT_REFLECTION_PROTOCOL.md`
    - Protocol wording remains explicit about canonical repo truth versus advisory/support surfaces

<a id="ledger-p1-tier4-scientific-creative-cell-pr0"></a>
- [x] P1: Tier 4 scientific / creative cell — PR0 governance packet + skill_router hooks (org tier only)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR #1548
  - Merge commit: `6a001b340821b797573f10a19d63f363b72df898` (to `main`, 2026-04-27)
  - Area: orchestration / local workforce / research lane semantics
  - Finding Type: governance + deterministic routing (no new `task_classification` label; Tier 4 maps to `creative_research` / `experiment` per `AGENT_SKILL_ROUTING_POLICY.md` §2a)
  - Status: 🟢 Closed — merged via PR #1548; canonical PR0 packet, `docs/orchestration/AGENTS.md` Tier 4 lane, `skill_router` cues + tests; no OpenAPI or autonomous-merge behavior in scope.
  - Reason (EN): Local workforce design packet §8 defers Tier 4 until the reliability cell is stable; this slice records the execution contract (phased roles, mandatory `qa-engineer-agent -> bug-hunter`) and tightens bootstrap-adjacent routing for Tier 4 wording and `TIER4_*` orchestration docs without inventing an eighth classifier label.
  - Dependencies:
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-local-workforce-pr-a-bootstrap-seam` (closed)
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-tier1-ci-cd-pr4-metrics` (reliability lane baseline; cite in PR body per packet precondition)
  - Lifecycle: Start → Open (draft) → Push → Review → Merge
  - Links:
    - `docs/orchestration/TIER4_SCIENTIFIC_CREATIVE_CELL_PR0_PACKET_2026-04-27.md`
    - `docs/orchestration/PulsePlate_Local_Agent_Workforce_System_Design_Packet_v1_2.md` §8 Tier 4
    - `docs/orchestration/AGENTS.md` (Tier 4 lane)
    - `docs/orchestration/TIER4_PR1548_AGENT_PASS_RECORD_2026-04-27.md` (PR #1548 execution / phased verification)
    - `scripts/orchestration/skill_router.py`
    - `tests/test_skill_router.py`
    - `docs/review/PR_1548_FIXED_MAPPING.md`
  - DoD:
    - PR0 packet + workforce packet cross-link + orchestration `AGENTS.md` lane are merged
    - `skill_router` scores `creative_research` for Tier 4 packet paths / stated goals without a new label; deterministic tests cover the cues
    - No OpenAPI / runtime / autonomous-merge behavior changes
    - Post-open `qa-engineer-agent -> bug-hunter` executed for the PR; evidence: `docs/orchestration/TIER4_PR1548_AGENT_PASS_RECORD_2026-04-27.md`; `docs/review/PR_1548_FIXED_MAPPING.md` maintained per merge governance

<a id="ledger-p2-local-workforce-pr-c-support-plane"></a>
- [x] P2: Local workforce PR-C — add experimental local support-plane storage
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR #1363
  - Area: orchestration / security / local support plane
  - Finding Type: RFC follow-on slice
  - Status: **Closed** — merged to `main` as squash merge commit `e6c7e5affb8c5ef82453af64cd78735af03990e4` (evidence: `scripts/orchestration/local_support_plane.py`, `tests/test_local_support_plane.py`, `docs/review/PR_1363_FIXED_MAPPING.md`).
  - Reason: The RFC allows an experimental local control-plane/storage layer only as a non-canonical support plane. If promoted, it must reuse existing security/control-plane primitives where possible and must not become a second orchestration source of truth.
  - Dependencies:
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-local-workforce-pr-b-reflection-protocol`
  - Lifecycle: Start → Open → Push → Review → Merge
  - Links:
    - `docs/orchestration/COMPOSER_BOOTSTRAP_KIT_PR1.md`
    - `docs/orchestration/PulsePlate_Local_Agent_Workforce_System_Design_Packet_v1_2.md`
    - `docs/orchestration/TASK_ANALYSIS_LOCAL_WORKFORCE_PR_C_2026-04-05.md`
    - `docs/security/AGENT_CONTROL_PLANE_SECURITY_BASELINE.md`
    - `docs/architecture/ADR-003-agent-control-plane-mvp.md`
    - `app/security/agent_control_plane.py`
    - `scripts/orchestration/local_support_plane.py`
    - `tests/test_local_support_plane.py`
  - DoD:
    - Experimental local support-plane storage/runtime remains explicitly non-canonical
    - Existing security/control-plane primitives are reused where possible
    - Launcher/runtime behavior stays outside repo SoT unless separately promoted by the automation readiness matrix
    - No duplicate orchestration source of truth is introduced
<a id="ledger-p2-karpathy-style-advisory-wiki-umbrella"></a>
- [x] P2: Karpathy-style advisory wiki umbrella
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR-S0-B1 (`docs(roadmap): define Karpathy advisory wiki umbrella`, merged as PR #1514)
  - Area: orchestration / workforce memory / roadmap
  - Finding Type: umbrella canonicalization
  - Status: ✅ Closed. PR #1514 merged on 2026-04-24 as `49e8c65eb27a9a36592a0786f34bca64392d80d8`; Rail B1 is now locked as advisory workforce compiled memory only, with no product RAG, runtime truth, public response-contract logic, semantic cache, or plugin/control-plane implementation.
  - Closeout note: The docs-only closure PR #1568 was operator-approved on 2026-04-28 in the coordinator lane after the stale `🟡 In progress` ledger state was found during the post-B2 closeout planning pass; this is ledger-only reconciliation, and no remaining Rail B1 umbrella implementation work is pending.
  - Reason (EN): The workforce compiled-memory line now has launcher/bootstrap, compiler, and hardening slices, but the backlog still lacks one explicit umbrella item that marks it as a separate advisory rail rather than an accidental side-project or product-RAG substitute. (RU: У workforce compiled-memory линии уже есть launcher/bootstrap, compiler и hardening slices, но в backlog нет одного umbrella-item, который бы фиксировал её как отдельный advisory rail, а не побочный side-project или замену product RAG.)
  - Links:
    - `docs/orchestration/KARPATHY_ADVISORY_WIKI_UMBRELLA_S0_PACKET_2026-04-24.md`
    - `docs/review/PR_1514_FIXED_MAPPING.md`
    - `docs/review/PR_1568_FIXED_MAPPING.md`
    - `docs/roadmap/PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md`
    - `docs/dev/LOCAL_COORDINATOR_LAUNCHER_ROLLOUT.md`
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p2-local-workforce-pr-d-advisory-wiki-compiler`
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p2-advisory-wiki-query-lint-enrichment`
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p2-advisory-wiki-reference-corpus-policy`
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p2-local-launcher-rollout-for-coordinator-first-automation`
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p2-plugin-control-plane-families-umbrella`
  - DoD:
    - One canonical umbrella entry exists for the advisory workforce rail
    - The rail is explicitly marked non-canonical and non-product-facing
    - Existing launcher/compiler slices are linked as children or prerequisites
    - Rail B1 cannot be used as product RAG, DB/runtime/API truth, public response-contract truth, or semantic-cache authorization
    - Rail B2/plugin-control-plane families remain a separate umbrella and are not implemented by this PR

<a id="ledger-p2-plugin-control-plane-families-umbrella"></a>
- [x] P2: Plugin/control-plane families umbrella
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR-S0-B2 (`docs(roadmap): define plugin control-plane families umbrella`, merged as PR #1522)
  - Area: orchestration / advisory control-plane / roadmap
  - Finding Type: umbrella canonicalization
  - Status: ✅ Closed. PR #1522 merged on 2026-04-24 as `c1bd2eb6d21cfead23bac0a75692c1dbf5ea618c`; Rail B2 is now locked as advisory/control-plane only, with no product runtime truth, semantic cache, bounded-context ownership, public response logic, or plugin implementation.
  - Closeout note: The docs-only closure PR #1561 was opened on 2026-04-28 after the stale `🟡 In progress` ledger state was found during the next-lane planning pass. Mitigation is this ledger-only reconciliation; no remaining Rail B2 umbrella implementation work is pending.
  - Reason (EN): GitHub, Cloudflare, Figma, and Hugging Face already appear across governance, edge, design, and research lanes, but they are not yet grouped under one explicit advisory/control-plane umbrella. Without a dedicated umbrella, later agents can accidentally pull plugin families into product runtime truth or semantic-cache planning. (RU: GitHub, Cloudflare, Figma и Hugging Face уже встречаются в governance, edge, design и research линиях, но пока не собраны под одним umbrella-item как advisory/control-plane rail. Без этого later agents могут случайно втянуть plugin families в product runtime truth или в планирование semantic cache.)
  - Links:
    - `docs/orchestration/PLUGIN_CONTROL_PLANE_FAMILIES_UMBRELLA_S0_PACKET_2026-04-24.md`
    - `docs/review/PR_1522_FIXED_MAPPING.md`
    - `docs/roadmap/PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md`
    - `docs/orchestration/WAVE6_AI_RUNTIME_AND_ADVISORY_SERIES_PACKET_2026-04-13.md`
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p2-karpathy-style-advisory-wiki-umbrella`
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p2-cloudflare-narrow-reopen-automation`
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-pulseplate-v3-clean-figma-execution`
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p2-local-workforce-pr-d-advisory-wiki-compiler`
  - DoD:
    - One canonical umbrella entry exists for plugin/control-plane families
    - GitHub, Cloudflare, Figma, and Hugging Face are explicitly mapped as advisory/control-plane families
    - The umbrella states these families do not become product runtime truth implicitly
    - The umbrella states plugin families do not authorize semantic-cache rollout or bounded-context ownership by themselves
    - The umbrella states plugin families do not authorize public response-contract logic, product RAG replacement, or DB/runtime/API truth
    - Rail B1 advisory wiki remains a separate sibling rail, not a child of Rail B2

<a id="ledger-p2-local-workforce-pr-d-advisory-wiki-compiler"></a>
- [x] P2: Local workforce PR-D — advisory wiki compiler over local support plane
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR #1371 (branch `feat/local-workforce-pr-d-advisory-wiki-compiler`, merged)
  - Area: orchestration / local support plane / operator tooling
  - Finding Type: RFC follow-on slice (compiled advisory memory)
  - Status (EN): ✅ Closed. PR #1371 merged on 2026-04-07 as
    `72b665763db36291b132ee148d347d7d6d8d273e`; advisory wiki compiler v1 is
    present in `main` as local/operator-only compiled memory over the support
    plane. PR #1372 merged on 2026-04-08 as
    `0c997be2352603c1bd5820d6d98f1c6b25793204` and landed the semantics /
    rollback hardening follow-up.
  - Closeout packet:
    `docs/orchestration/KARPATHY_PR_B1_ADVISORY_WIKI_COMPILER_CLOSEOUT_PACKET_2026-04-29.md`
  - Reason: Non-canonical wiki artifacts help operators navigate ingested repo slices without introducing embeddings, vector stores, or a second documentation SoT.
  - Dependencies:
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p2-local-workforce-pr-c-support-plane`
  - Links:
    - `docs/review/PR_1371_FIXED_MAPPING.md`
    - `docs/orchestration/LOCAL_WIKI_SUPPORT_PLANE.md`
    - `scripts/orchestration/wiki_ingest.py`
    - `scripts/orchestration/wiki_query.py`
    - `scripts/orchestration/wiki_lint.py`
    - `scripts/orchestration/wiki_promote.py`
    - `scripts/orchestration/local_support_plane.py`
    - `docs/review/PR_1372_FIXED_MAPPING.md`
  - DoD:
    - ✅ CLIs documented and covered by deterministic tests.
    - ✅ No writes to canonical `docs/**` tree from promote path; support-plane keys respect `normalize_key`.
    - ✅ Ledger + agent entrypoints reference the wiki doc in the same merge cycle.
  - Deferred / follow-ups (post-v1 hardening, English-first):
    - Slug strategy after truncation (reject vs hash-suffix vs manifest) when paths differ but truncate to the same slug (`scripts/orchestration/_wiki_compiler_support.py` `path_to_slug`).
    - Readability refactor (no behavior change): extract staging filesystem rollback and support-plane failure rollback from `wiki_promote.promote_slug` into small helpers with docstrings (Sourcery review suggestion on PR #1372; current logic is correct and covered by `tests/test_wiki_promote.py`).
    - Optional promotion **history** or versioned SP keys / manifest (today `wiki.promoted.<slug>` overwrites).
    - Richer lint: orphans, stale links, index/page consistency beyond raw hash, contradiction checks (not in v1).
    - Search: ranking, headings/title weighting, or index-first retrieval (v1 is body substring only).

<a id="ledger-p2-advisory-wiki-query-lint-enrichment"></a>
- [x] P2: Advisory wiki query/lint enrichment
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR-B3 / `codex/advisory-wiki-query-lint-enrichment-b3` (merged as PR #1596)
  - Area: orchestration / workforce memory / operator tooling
  - Finding Type: post-hardening follow-on
  - Status: ✅ Closed. PR-B3 merged as PR #1596 on 2026-04-30 with merge commit
    `438d135f7ae0a07cb28549488284a40e08183c92`.
  - Closeout packet:
    `docs/orchestration/KARPATHY_PR_B3_ADVISORY_WIKI_QUERY_LINT_CLOSEOUT_PACKET_2026-04-30.md`
  - Closeout note: PR #1596 completed the advisory/operator-only query/lint
    enrichment slice without product RAG runtime, API, DTO, OpenAPI, semantic
    cache, GraphRAG, embeddings, vector DB, Redis/GPTCache, or ContextManifest
    scope. The next substantive Rail B1 slice remains
    `PR-B4 — docs(orchestration): define bounded reference-corpus policy for
    advisory wiki`.
  - Reason (EN): The compiler/hardening baseline is now present, and PR-B3 has
    enriched query and lint behavior without widening into embeddings, vector
    search, or product-facing RAG semantics. (RU: Базовый compiler/hardening уже
    есть, и PR-B3 улучшил query/lint без ухода в embeddings, vector search или
    product-facing RAG semantics.)
  - Links:
    - `docs/orchestration/KARPATHY_PR_B3_ADVISORY_WIKI_QUERY_LINT_ENRICHMENT_PACKET_2026-04-30.md`
    - `docs/review/PR_1596_FIXED_MAPPING.md`
    - `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1596`
    - `docs/roadmap/PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md`
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p2-local-workforce-pr-d-advisory-wiki-compiler`
    - `docs/orchestration/LOCAL_WIKI_SUPPORT_PLANE.md`
    - `scripts/orchestration/wiki_query.py`
    - `scripts/orchestration/wiki_lint.py`
  - DoD:
    - ✅ Query/lint enrichment remains non-canonical and operator-only.
    - ✅ No embeddings, vector DB, or public runtime coupling are introduced.
    - ✅ Opt-in query context remains backward-compatible with default search output.
    - ✅ Lint covers deterministic index/page consistency and stale local page links.
    - ✅ Follow-on scope remains explicit: contradiction lint, index weighting,
      manifest/history improvements, and reference-corpus policy stay separate.

<a id="ledger-p2-advisory-wiki-reference-corpus-policy"></a>
- [x] P2: Advisory wiki bounded reference-corpus policy
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR-B4 / `codex/advisory-wiki-reference-corpus-policy-b4` (merged as PR #1607)
  - Area: orchestration / workforce memory / docs
  - Finding Type: source-boundary policy
  - Status: ✅ Closed. PR #1607 merged on 2026-04-30 as
    `07e11f4147bd75d20f8994175a9545782e02b04a`; the bounded
    reference-corpus policy is now landed as Rail B1 advisory/wiki governance
    only, with no product runtime truth, semantic-cache, embeddings, vector DB,
    GraphRAG, Redis/GPTCache, or ContextManifest implementation scope.
    Delayed closeout exception approved by operator on 2026-05-05 for
    governance-only ledger/epic reconciliation after the merged PR #1607
    implementation; this exception does not reopen PR-B4 implementation scope.
  - Reason: The workforce rail includes a bounded reference-corpus policy slice
    so DeepWiki or similar helper corpora can remain read-only secondary aids
    instead of drifting into a second source of truth.
  - Links:
    - `docs/roadmap/PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md`
    - `docs/orchestration/KARPATHY_PR_B4_BOUNDED_REFERENCE_CORPUS_POLICY_PACKET_2026-04-30.md`
    - `docs/orchestration/LOCAL_WIKI_SUPPORT_PLANE.md`
    - `docs/review/PR_1607_FIXED_MAPPING.md`
    - `docs/dev/LOCAL_COORDINATOR_LAUNCHER_ROLLOUT.md`
    - `docs/orchestration/AUTOMATION_READINESS_MATRIX.md`
  - DoD:
    - ✅ Reference corpora are explicitly documented as read-only secondary aids.
    - ✅ Repo artifacts remain the only canonical source of truth.
    - ✅ Conflicts between reference corpora and repo artifacts resolve to repo truth.
    - ✅ No embeddings, vector DB, product-runtime, API, DTO, OpenAPI, semantic-cache,
      GraphRAG, Redis/GPTCache, or ContextManifest coupling was introduced.
    - ✅ Contradiction lint, ranking/index weighting, manifest/history, and reference
      corpus admission tooling remain separate follow-ons.

<a id="ledger-p2-local-launcher-rollout-for-coordinator-first-automation"></a>
- [ ] P2: Local launcher rollout for coordinator-first automation
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR #1348 + PR #1350 (landed); PR #1370 (repo companion: runbook + sanitized wrapper example + entry-doc sync + core TypeGuard mypy fix); PR #1408 (host smoke evidence); PR-B0 (`fix(local-workforce): harden launcher/bootstrap seam before advisory wiki expansion`)
  - Area: local tooling / launcher / Codex runtime
  - Finding Type: non-repo rollout follow-up
  - Status (EN): In progress. Companion PR #1370 added the repo-side runbook and sanitized wrapper example; host smoke evidence was recorded on 10 April 2026 for one opted-in machine in `docs/dev/LOCAL_COORDINATOR_LAUNCHER_ROLLOUT_EVIDENCE_2026-04-10.md`. PR-B0 hardens the repo bridge before PR-B1 advisory wiki compiler work by making the analyze-preflight and printed-bootstrap contract deterministic without claiming global host auto-start.
  - Reason: Repo docs and deterministic engines alone cannot force raw session auto-start. A machine-local launcher or wrapper must wire preflight, bootstrap, and compatible runtime settings without pretending that `~/.codex/config.toml` is repo source of truth.
  - Links:
    - `docs/orchestration/AUTOMATION_READINESS_MATRIX.md`
    - `docs/dev/LOCAL_COORDINATOR_LAUNCHER_ROLLOUT.md`
    - `docs/dev/LOCAL_COORDINATOR_LAUNCHER_ROLLOUT_EVIDENCE_2026-04-10.md`
    - `docs/orchestration/KARPATHY_PR_B0_LAUNCHER_BOOTSTRAP_HARDENING_PACKET_2026-04-29.md`
    - `docs/templates/pulseplate-coordinator-launch.example.sh`
    - `docs/templates/codex.config.example.toml`
    - `scripts/orchestration/local_session_bootstrap.sh`
    - `docs/dev/CODEX_SKILLS.md`
    - `~/.codex/config.toml`
  - DoD:
    - Local launcher/wrapper classifies new tasks and invokes preflight + bootstrap before normal execution
    - Compatible local runtime settings are documented with explicit caveats about host/runtime limits
    - Local rollout steps do not mutate repo governance docs as a substitute for launcher support
    - Repo PR chain remains independently valid without the local rollout
- [x] P1: Classify CI checks as hard / soft / external in AGENTS or CI governance
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR #996 (`docs(orchestration): add canonical PR orchestration contract matrix`)
  - Area: orchestration / CI / review governance
  - Finding Type: process hardening
  - Status: Completed via `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md`; Tier 1 PR-series operationalization is tracked separately below.
  - Reason: Explicit classification (hard gate / soft gate / external flaky) prevents ambiguous merge decisions; external tools do not block unless marked required. The current local/CI/release matrix still leaves some truly blocking lanes in advisory mode, which makes merge-readiness claims inconsistent.
  - Links:
    - `AGENTS.md:31` (merge readiness), `:39` (checklist)
    - `.github/workflows/` (CI job definitions)
    - `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md`
  - DoD:
    - AGENTS.md or dedicated CI governance doc defines hard gate (blocks merge), soft gate (warn only), external (never blocks unless manually promoted)
    - Examples listed per type
    - One canonical merge-ready check bundle is documented across local, PR CI, and release-ops lanes

- [ ] P1: Tier 1 CI/CD consolidation via custom orchestration
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR #1240 -> PR #1244 -> PR #1253 -> PR-TBD-TIER1-CI-CD-PR4
  - Area: orchestration / CI / review governance
  - Finding Type: process hardening
  - Status: In progress
  - Reason: Tier 1 requires a coordinator-led stacked PR program that first locks governance, then consolidates workflow topology, then narrows PR blockers, then adds advisory CI metrics without widening release risk.
  - Links:
    - `docs/orchestration/TIER1_CI_CD_PR_SERIES_RUNBOOK.md`
    - `docs/orchestration/TIER1_CI_CD_TASK_PACKET_2026-03-26.md`
    - `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md`
    - `RUNBOOK_AGENT.md`
  - DoD:
    - Governance owner, routing card, and mandatory post-open bug-hunter lane are documented and used for every Tier 1 slice
    - Canonical backend/shared PR workflow topology is consolidated and validated against current-head required checks
    - PR blocker vs advisory CI classification is documented, reduced, and enforced through the merge-readiness wrapper
    - Advisory CI metrics artifacts exist without adding new merge blockers or widening release risk
  - Child slices:
    - `ledger-p1-tier1-ci-cd-pr1-governance`
    - `ledger-p1-tier1-ci-cd-pr2-workflow`
    - `ledger-p1-tier1-ci-cd-pr3-risk-topology`
    - `ledger-p1-tier1-ci-cd-pr4-metrics`

- [x] P1: PR1 governance and canonical matrix sync {#ledger-p1-tier1-ci-cd-pr1-governance}
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR #1240
  - Area: orchestration / CI / review governance
  - Finding Type: process hardening
  - Status: Materially completed in merged PR `#1240` (`24c51f85`); this slice now stays closed unless follow-up governance drift is reopened explicitly.
  - Reason: The repo already has merge-governance primitives, but Tier 1 cannot start safely until the canonical backend/shared lane, duplicate PR-time workflows, and specialized add-on lanes are named explicitly in docs.
  - Links:
    - `docs/orchestration/TIER1_CI_CD_PR_SERIES_RUNBOOK.md`
    - `docs/orchestration/TIER1_CI_CD_TASK_PACKET_2026-03-26.md`
  - DoD:
    - `AGENTS.md`, `RUNBOOK_AGENT.md`, and orchestration docs all point to one canonical backend/shared PR lane
    - Duplicate PR-time lanes are labeled transitional rather than canonical
    - Mandatory post-open `qa-engineer-agent -> bug-hunter` lane is recorded
    - Local validation passes: `check_preflight`, `check_agent_consistency`, `pre-commit run --all-files`, `make verify`

- [x] P1: PR2 workflow consolidation into canonical ci.yml {#ledger-p1-tier1-ci-cd-pr2-workflow}
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR #1244
  - Area: orchestration / CI / review governance
  - Finding Type: process hardening
  - Status: Materially completed on `origin/main` in PR `#1244` (`b7e029b4`); this slice now serves as landed baseline input for PR3.
  - Reason: Backend/shared PR execution is now canonicalized in `ci.yml`; `pr-tests.yml` and `pr-coverage.yml` are no longer active PR lanes, `security.yml` moved to a scheduled/manual audit lane, `trivy.yml` remains a `main`/schedule/manual non-PR image-security lane, and `build.yml` remains specialized.
  - Links:
    - `.github/workflows/ci.yml`
    - Historical PR-lane duplicates removed in PR `#1244`: `pr-tests.yml`, `pr-coverage.yml`
    - `.github/workflows/security.yml`
    - `.github/workflows/trivy.yml`
  - DoD:
    - Canonical backend/shared PR execution lives in `.github/workflows/ci.yml`
    - `pr-tests.yml` and `pr-coverage.yml` are no longer active PR lanes
    - `security.yml` and `trivy.yml` are removed from PR-time execution; `security.yml` remains scheduled/manual and `trivy.yml` remains `main`/schedule/manual outside canonical merge truth
    - `build.yml`, frontend-only lanes, and nightly/release lanes stay isolated
    - Required-check parity is preserved on current-head PR checks

- [x] P1: PR3 risk-based PR test topology {#ledger-p1-tier1-ci-cd-pr3-risk-topology}
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: #1253
  - Area: orchestration / CI / review governance
  - Finding Type: process hardening
  - Status: Materially completed on `main` in merged PR `#1253` (`3be5debf`); this slice now serves as landed baseline input for PR4.
  - Reason: PR blockers should stay focused on business-critical runtime paths, while nightly depth absorbs broad non-critical coverage tails.
  - Links:
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-test-hygiene-wave`
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-fastapi-compatibility-gates`
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-llm-reliability-security-gates`
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-classify-ci-checks-as-hard-soft-external`
    - `docs/orchestration/TIER1_CI_CD_PR_SERIES_RUNBOOK.md`
  - DoD:
    - Deterministic smoke, contract/risk suites, and nightly-only depth are split
    - Blocking surfaces explicitly cover billing, entitlement, VIP insight, and OpenAPI determinism
    - PR-size governance exists for `<300`, `300-800`, and `>800` LoC cases, and `>800` requires explicit `## Split Justification` proof in the PR body
    - No new flaky test class is introduced

- [x] P1: PR4 lightweight CI metrics and weekly feedback loop {#ledger-p1-tier1-ci-cd-pr4-metrics}
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: #1286
  - Area: orchestration / CI / review governance
  - Finding Type: process hardening
  - Status: Materially completed on `main` in merged PR `#1286` (`a9bf2781`); advisory metrics now serve as the landed Tier 1 PR4 baseline.
  - Reason: Tier 1 needs advisory metrics for critical-path duration, reruns, red-build rate, and xdist fallback tracking without turning observability into another merge blocker or widening branch-protection truth.
  - Links:
    - `docs/orchestration/TIER1_CI_CD_PR_SERIES_RUNBOOK.md`
    - `docs/orchestration/TIER1_CI_CD_TASK_PACKET_2026-03-26.md`
    - `.github/workflows/ci-metrics.yml`
    - `scripts/ci/collect_ci_metrics.py`
  - DoD:
    - `scripts/ci/` emits `ci-metrics-summary.json` and `ci-metrics-summary.md`
    - Metrics remain informational only and outside canonical merge truth
    - Weekly reporting path uses artifact + `GITHUB_STEP_SUMMARY` only
    - Artifact absence degrades gracefully with explicit `unknown`/`unavailable` metric states
    - Tier 1 docs/runbook/task packet record PR4 as landed baseline evidence


- [x] P1: Disposition guard — ban mapping to trigger-only commits
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: #990
  - Area: orchestration / review governance
  - Finding Type: process hardening
  - Status: Materially completed on `main` in merged PR `#990` (`91477308`); trigger-only FIXED proof mappings are now rejected by the disposition guard.
  - Reason: Prevent FIXED proof bypass via empty or CI rerun/trigger commits. Mapping `- <url> -> <sha>` must not accept empty commits or commits whose subject matches trigger/rerun patterns.
  - Links:
    - `scripts/orchestration/check_review_threads_disposition.py`
    - `tests/test_review_threads_disposition_strict.py`
    - `AGENTS.md` (Review Governance)
  - DoD:
    - Gate fails when mapping SHA is empty commit (no changed files)
    - Gate fails when commit subject matches trigger/rerun patterns (trigger ci, re-run ci, re-run checks)
    - Tests cover deny (empty, trigger subject) and allow (normal commit)
    - AGENTS.md updated with FIXED proof quality (trigger-only ban) rule
    - Optional allowlist with TTL remains empty by default (P2 if needed)


- [ ] P1: PR #1013 sandbox hardening follow-ups
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-TBD-SANDBOX-HARDENING-FOLLOWUPS
  - Status: Open
  - Area: security / agent control plane / sandbox runtime
  - Finding Type: follow-up hardening
  - Locations:
    - `app/security/execution_sandbox.py`
    - `tests/test_execution_sandbox.py`
    - `docs/orchestration/LOCAL_EXECUTION_SANDBOX_RUNBOOK.md`
  - Reason: PR #1013 lands the local sandbox foundation, but two higher-cost hardening items remain intentionally deferred: output-budget enforcement must move from post-capture truncation to streaming enforcement, and the explicit binary allowlist should be re-minimized after initial developer-machine adoption evidence is collected.
  - Links:
    - `app/security/execution_sandbox.py`
    - `tests/test_execution_sandbox.py`
    - `docs/orchestration/LOCAL_EXECUTION_SANDBOX_RUNBOOK.md`
    - `docs/review/PR_1013_FIXED_MAPPING.md`
  - DoD:
    - Sandbox stdout/stderr budget is enforced during process execution instead of after full `capture_output=True` buffering
    - Default and runbook binary allowlists are reviewed against real usage and reduced to the smallest stable set
    - Deterministic tests cover stream-budget enforcement and minimized allowlist behavior
    - `pre-commit run --all-files` and `make verify` pass in follow-up PR
  - Blockers: None (deferred by scope, not blocked)

- [x] Remove Trivy suppression for gpgv CVE (CVE-2026-24883)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: `codex/fix-main-trivy-container-cves`
  - Status: Closed by production package removal. The final `production` Docker target now purges `gpgv`, and CI blocks its return with the Docker runtime dependency-surface guard.
  - Reason: The previous posture suppressed `gpgv` while waiting for Debian/Trivy metadata. The current production image no longer needs package-manager tooling at runtime, so the safer remediation is removal from the final image instead of retaining a Trivy waiver.
  - Links:
    - `Dockerfile` (production package pruning)
    - `scripts/ci/check_docker_runtime_dependency_surface.py`
    - `docs/security/CVE-2026-24883-gpgv.md`
    - `.github/workflows/trivy.yml`
  - DoD:
    - Final production image removes `gpgv`
    - CI fails if `gpgv` returns to the production image
    - `trivy/ignore-policy.rego` and `.trivyignore` do not suppress CVE-2026-24883
    - `docs/security/CVE-2026-24883-gpgv.md` is marked resolved by production package removal
    - Trivy Code Scanning alerts remain closed on `main`

- [x] Remove Trivy suppression for systemd-family CVE (CVE-2026-29111)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR #1846
  - Status: Closed by PR #1846 after the Rego suppression was removed instead of extended.
  - Reason: Trivy reports Debian bookworm `systemd` family packages
    (`libsystemd0`, `libudev1`) as vulnerable at `252.38-1~deb12u1` with no
    actionable fixed version in the current bookworm image line as of
    2026-03-30; we suppress narrowly in `trivy/ignore-policy.rego` until
    Debian bookworm or Trivy metadata catches up.
  - Links:
    - `trivy/ignore-policy.rego` (rule for CVE-2026-29111)
    - `docs/security/CVE-2026-29111-systemd.md`
    - `.github/workflows/build.yml`
  - DoD:
    - Debian bookworm publishes a fixed `systemd` package line (or Trivy reports
      a fixed version in our image context)
    - Remove CVE-2026-29111 suppression from `trivy/ignore-policy.rego`
    - Remove `docs/security/CVE-2026-29111-systemd.md` (or mark as resolved)
    - Trivy Code Scanning alerts `#573` and `#575` remain closed on `main`
- [ ] Remove Trivy suppression for ncurses CVE (CVE-2025-69720)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: TBD (follow-up after upstream fix)
  - Reason: Trivy reports Debian bookworm `ncurses` family packages
    (`libncursesw6`, `libtinfo6`, `ncurses-base`, `ncurses-bin`) as vulnerable at
    `6.4-4` with no actionable fixed version in the current bookworm image line as
    of 2026-03-30; we suppress narrowly in `trivy/ignore-policy.rego` until
    Debian bookworm or Trivy metadata catches up.
  - Links:
    - `trivy/ignore-policy.rego` (rule for CVE-2025-69720)
    - `docs/security/CVE-2025-69720-ncurses.md`
    - `.github/workflows/build.yml`
  - DoD:
    - Debian bookworm publishes a fixed `ncurses` package line (or Trivy reports a
      fixed version in our image context)
    - Remove CVE-2025-69720 suppression from `trivy/ignore-policy.rego`
    - Remove `docs/security/CVE-2025-69720-ncurses.md` (or mark as resolved)
    - Trivy Code Scanning alerts #572, #574, #576, and #577 remain closed on
      `main`

<a id="ledger-p1-react-router-rsc-advisory-monitor"></a>
- [ ] P1: Remove React Router unstable RSC advisory suppression
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR #2247
  - Status: In progress in replacement PR #2247; fixed dependency material and exact
    suppression deletion are selected, exact-head Trivy confirmation is pending
  - Area: security / frontend dependency / Trivy policy
  - Finding Type: application dependency vulnerability remediation
  - Reason: Docker Build and Push run `31258531222`, security job `93106014446`,
    Trivy analysis `1589834230`, reported `GHSA-qwww-vcr4-c8h2` for
    `react-router@7.18.1` with compatible fixed version `7.18.2`. The batch
    selects that fixed line, and the exact suppression is deleted rather than
    extended, broadened, or replaced.
  - Links:
    - <https://github.com/advisories/GHSA-qwww-vcr4-c8h2>
    - `docs/security/GHSA-qwww-vcr4-c8h2-react-router.md`
    - `docs/security/NANOID_REACT_ROUTER_ATOMIC_TRIVY_REMEDIATION_CLASS.md`
    - `trivy/ignore-policy.rego`
    - `scripts/ci/check_trivy_ignore_policy_expiry.py`
    - `tests/test_trivy_ignore_policy_expiry.py`
  - DoD:
    - Resolve `react-router` and `react-router-dom` to `7.18.2`
    - Delete the exact `GHSA-qwww-vcr4-c8h2` Rego rule and header reference
    - Reject any target-capable suppression reintroduction while preserving
      unrelated expiry/review rules
    - Close this item only after terminal exact-head Trivy evidence; do not infer
      a full-audit or readiness claim from selected material

- [x] Remove Trivy suppression for libgcrypt20 CVE-2026-41989
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR #1846
  - Status: Closed by PR #1846 after the Rego suppression was removed instead of extended.
  - Area: security / base-image / code-scanning
  - Finding Type: container base image vulnerability
  - Reason: `build.yml:publish` on `main` currently reports open Trivy alert `#586` on
    `libgcrypt20` at version `1.10.1-3` with no published fixed-version metadata
    as of 2026-04-26. This CVE is addressed by targeted suppression in
    `trivy/ignore-policy.rego` while monitoring upstream/base-image progress.
  - Links:
    - https://github.com/Katsiarynakavaleuskaya/PulsePlate/security/code-scanning/586
    - docs/security/CVE-2026-41989-libgcrypt20.md
    - trivy/ignore-policy.rego
    - .github/workflows/build.yml
  - DoD:
    - Debian or Trivy metadata publishes a fixed `libgcrypt20` package context
    - Remove suppression rule from `trivy/ignore-policy.rego`
    - Mark `docs/security/CVE-2026-41989-libgcrypt20.md` resolved or remove after fix
    - Trivy Code Scanning alert `#586` remains closed on `main`

- [ ] Remove Trivy suppression for util-linux CVE (CVE-2026-53615)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: TBD (branch security/cve-2026-53615-util-linux)
  - Area: security / base-image / code-scanning
  - Finding Type: container base image vulnerability
  - Reason: Trivy publish scan reports Debian bookworm `util-linux` family packages
    (`bsdutils`, `libblkid1`, `libmount1`, `libsmartcols1`, `libuuid1`, `mount`,
    `util-linux`, `util-linux-extra`) as HIGH at `2.38.1-5+deb12u3` /
    `1:2.38.1-5+deb12u3` with no actionable fixed version in the current bookworm
    image line as of 2026-07-09; we suppress narrowly in `trivy/ignore-policy.rego`
    until Debian bookworm or Trivy metadata catches up.
  - Links:
    - `trivy/ignore-policy.rego` (rule for CVE-2026-53615)
    - `docs/security/CVE-2026-53615-util-linux.md`
    - https://security-tracker.debian.org/tracker/CVE-2026-53615
    - https://github.com/util-linux/util-linux/security/advisories/GHSA-h4rw-gv36-wmp5
    - `.github/workflows/build.yml`
  - DoD:
    - Debian bookworm publishes a fixed `util-linux` package line (or Trivy reports a
      fixed version in our image context)
    - Remove CVE-2026-53615 suppression from `trivy/ignore-policy.rego`
    - Remove `docs/security/CVE-2026-53615-util-linux.md` (or mark as resolved)
    - Trivy Code Scanning alerts #623-#630 remain closed on `main`

<a id="ledger-p1-remove-trivy-suppression-util-linux-cve-2026-53613"></a>
- [ ] P1: Remove Trivy suppression for util-linux CVE-2026-53613
  - Owner: @katsiaryna_kavaleuskaya (Security/SRE)
  - Priority: P1
  - Target PR: PR-TBD-REMOVE-CVE-2026-53613-SUPPRESSION
  - Status: Open; review Debian bookworm status by 2026-09-19 and remove no later
    than the shared 2026-10-07 policy expiry unless a separately reviewed security
    PR establishes a new bounded disposition
  - Area: security / base-image / code-scanning
  - Finding Type: temporary distro CVE risk acceptance
  - Reason: Exact-main CD run `32355502655`, job `96383696240`, reports eight HIGH
    CVE-2026-53613 findings for the Debian bookworm util-linux package family in
    image digest
    `sha256:5d147c66b4999210345f4e1895c6f0129f6b9e90dd25500f712c8e82f42577da`.
    Debian marks bookworm `2.38.1-5+deb12u3` and ordinary trixie `2.41-5` as
    vulnerable while trixie-security `2.41.5-0+deb13u1` is fixed. The current
    suppression accepts bounded residual risk; it is not remediation.
  - Links:
    - `docs/security/CVE-2026-53613-util-linux.md`
    - `trivy/ignore-policy.rego`
    - `tests/test_trivy_ignore_policy_expiry.py`
    - <https://security-tracker.debian.org/tracker/CVE-2026-53613>
    - <https://github.com/Katsiarynakavaleuskaya/PulsePlate/actions/runs/32355502655/job/96383696240>
  - DoD:
    - Debian bookworm publishes a fixed `util-linux` package, the production base
      image moves to a fixed release, or the affected package family is removed
    - Remove only the exact CVE-2026-53613 Rego rule and its header/document links
    - Rebuild and scan the exact production image with no CVE-2026-53613 finding
    - Keep deterministic negative tests proving that no broader package/version/CVE
      suppression replaces the removed rule
    - Close this item only after terminal exact-main CD image-scan evidence

<a id="ledger-p1-remove-trivy-suppression-openssl-cve-2026-14456"></a>
- [ ] P1: Remove Trivy scanner disposition for OpenSSL CVE-2026-14456
  - Owner: @katsiaryna_kavaleuskaya (Security/SRE)
  - Priority: P1
  - Target PR: PR-TBD-REMOVE-CVE-2026-14456-SUPPRESSION
  - Status: Open; review upstream, Debian, and Trivy metadata by 2026-09-19 and
    remove no later than the shared 2026-10-07 policy expiry unless a separately
    reviewed security PR establishes a new bounded disposition
  - Area: security / base-image / code-scanning
  - Finding Type: temporary scanner false-positive disposition
  - Reason: Exact-main CD run `32368859081`, job `96424514194`, and Docker Build
    and Push run `32368859126`, job `96424915657`, report two HIGH
    CVE-2026-14456 findings for `libssl3` and `openssl` at
    `3.0.20-1~deb12u2` in image digest
    `sha256:bb92cf07ffbdb41bb3ec05dc5014dd5280798cf2a3c01f5119847277a8611298`.
    The upstream OpenSSL advisory assigns Low severity and marks OpenSSL 3.0
    unaffected because the vulnerable QUIC server implementation begins in 3.5,
    while Debian still marks the Bookworm source-package line vulnerable with no
    fixed package. The exact-tuple scanner disposition records that conflict; it
    is not remediation or an OpenSSL upgrade.
  - Links:
    - `docs/security/CVE-2026-14456-openssl.md`
    - `trivy/ignore-policy.rego`
    - `tests/test_trivy_ignore_policy_expiry.py`
    - <https://openssl-library.org/news/secadv/20260813.txt>
    - <https://security-tracker.debian.org/tracker/CVE-2026-14456>
    - <https://github.com/Katsiarynakavaleuskaya/PulsePlate/actions/runs/32368859081/job/96424514194>
    - <https://github.com/Katsiarynakavaleuskaya/PulsePlate/actions/runs/32368859126/job/96424915657>
  - DoD:
    - Trivy or Debian corrects the affected-branch metadata, either installed
      package tuple changes, the finding disappears, the packages leave the image,
      or upstream evidence expands the affected set to include OpenSSL 3.0
    - Remove only the exact CVE-2026-14456 Rego rule and delete its active security
      document/header links
    - Rebuild and scan the exact production image with no CVE-2026-14456 finding
    - Keep deterministic negative tests proving that no broader CVE/package/version/
      PkgID suppression replaces the removed rule
    - Close this item only after terminal exact-main CD and Docker image-scan evidence

- [ ] Security suppression expiry monitoring
  - Owner: @katsiaryna_kavaleuskaya
  - Target PR: N/A (ongoing)
  - Priority: P1
  - Area: security
  - Finding Type: policy exception
  - Locations:
    - `trivy/ignore-policy.rego` — Suppression expires: 2026-10-07 for retained residual suppressions
    - `.trivyignore` — historical review note remains out of scope for this Rego-only expiry lane
  - Reason: Retained residual unfixed/non-applicable distro CVEs require short review windows; fixed/resolved suppressions were removed instead of extended
  - Links:
    - docs/security/CVE-2026-27171-zlib1g.md
    - docs/security/CVE-2026-3184-util-linux.md
    - docs/security/CVE-2025-69720-ncurses.md
    - docs/security/CVE-2026-53615-util-linux.md
  - DoD:
    - Weekly monitoring for upstream fixes
    - Remove suppressions when fixed versions available
    - Update base image when fixes land
  - **Rego suppressions last reviewed: 2026-08-09**
    - PR #929: Removed 4 upstream-fixed CVE suppressions (gpgv, gnutls, p11-kit)
    - PR #930: Extended review-by dates to 2026-05-27 for unfixed CVEs
    - PR #2094: Removed resolved Faraday scanner-lag suppression; CVE-2026-53615 util-linux HIGH suppression added on branch security/cve-2026-53615-util-linux through the 2026-10-07 file expiry; residual zlib/3184/ncurses Review-by dates set to 2026-08-08 after the 2026-07-09 re-review (rule bodies unchanged)
    - PR #2246: Rechecked current Debian primary evidence for residual zlib/3184/ncurses rules; Review-by dates are 2026-09-08, zlib/ncurses rule bodies and the shared 2026-10-07 expiry remain unchanged, and CVE-2026-3184 PkgID matching is narrowed to exact equality
  - **`.trivyignore` review remains out of scope for this Rego-only expiry lane.**


<a id="ledger-p2-trivy-cli-0-72-0"></a>
- [ ] P2: Upgrade standalone Trivy CLI pin to v0.72.0
  - Owner: @katsiaryna_kavaleuskaya (Security/SRE)
  - Priority: P2
  - Target PR: TBD
  - Area: security / CI maintenance
  - Reason (EN): PR #2094's `2 configurations not found` message is a GitHub Code
    Scanning configuration-comparison warning, not a scanner failure. The action pin is
    already v0.36.0; upgrading the separate CLI pin from v0.71.2 to v0.72.0 is optional
    maintenance that should not expand the CVE-scoped PR.
  - Links:
    - `.github/workflows/trivy.yml:189`
    - `.github/workflows/trivy.yml:206`
    - `docs/review/PR_2094_FIXED_MAPPING.md#github-code-scanning-trivy-tool-status`
  - DoD:
    - Update the standalone Trivy CLI pin from v0.71.2 to v0.72.0 in a focused PR.
    - Verify the standalone scan and SARIF upload complete without weakening fail-closed behavior.
    - Record current-head CI evidence and close this ledger item after merge.

<a id="ledger-p1-cve-2026-3184-exact-pkgid-match"></a>
- [ ] P1: Tighten CVE-2026-3184 PkgID matching to exact equality
  - Owner: @katsiaryna_kavaleuskaya (Security/SRE)
  - Priority: P1
  - Target PR: PR #2247
  - Status: Implementation complete in replacement PR #2247; merge confirmation pending
  - Area: security / container / Trivy policy
  - Reason (EN): The CVE-2026-3184 suppression used `startswith` for observed util-linux PkgIDs, which could match unintended suffix variants. Replacement PR #2247 carries the material Trivy policy surface from superseded PR #2246, so it narrows the same eight tuples to exact equality instead of deferring a current-PR security finding.
  - Links:
    - `trivy/ignore-policy.rego`
    - `docs/security/CVE-2026-3184-util-linux.md`
    - `tests/test_trivy_ignore_policy_expiry.py`
  - DoD:
    - Replace CVE-2026-3184 PkgID prefix checks with exact equality against the observed package/version tuples
    - Add deterministic positive and suffix-negative tests for every allowed PkgID
    - Run the Trivy expiry checker and focused policy tests successfully

- [ ] Triage open Trivy glibc code-scanning alerts (CVE-2026-4046)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR #1305
  - Area: security / base-image / code-scanning
  - Finding Type: container base image vulnerability
  - Reason: GitHub code scanning on `main` currently reports open Trivy alerts `#579` (`libc-bin`) and `#580` (`libc6`) for `CVE-2026-4046` at version `2.36-9+deb12u13` with no fixed version published in Trivy metadata as of 2026-04-02. This CVE must stay on a single canonical tracker and be triaged in a dedicated security lane rather than being absorbed into the billing activation/persistence closeout.
  - Links:
    - `https://github.com/Katsiarynakavaleuskaya/PulsePlate/security/code-scanning/579`
    - `https://github.com/Katsiarynakavaleuskaya/PulsePlate/security/code-scanning/580`
    - `https://security-tracker.debian.org/tracker/CVE-2026-4046`
    - `trivy/ignore-policy.rego`
    - `.github/workflows/build.yml`
  - DoD:
    - Triage outcome is documented with evidence for both alerts in the dedicated security PR
    - Separate security lane decides between narrow suppression and upstream/base-image remediation
    - Billing activation/persistence closeout remains explicitly out of scope for this CVE
    - Alerts `#579` and `#580` are closed or formally covered by the approved suppression policy

- [x] Remove Trivy suppression for libcap2 CVE-2026-4878
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR #1846
  - Status: Closed by PR #1846 after the Rego suppression was removed instead of extended.
  - Area: security / base-image / code-scanning
  - Finding Type: container base image vulnerability
  - Reason: GitHub Code Scanning alert #588 reports `libcap2` `CVE-2026-4878` at `1:2.66-4+deb12u1` with no fixed version reported by Trivy/GitHub at triage time. This is covered by a narrow temporary suppression in `trivy/ignore-policy.rego` while monitoring Debian/Trivy fixed-version metadata.
  - Links:
    - https://github.com/Katsiarynakavaleuskaya/PulsePlate/security/code-scanning/588
    - docs/security/CVE-2026-4878-libcap2.md
    - trivy/ignore-policy.rego
    - .github/workflows/build.yml
  - DoD:
    - Debian or Trivy metadata publishes a fixed `libcap2` package context
    - Remove suppression rule from `trivy/ignore-policy.rego`
    - Mark `docs/security/CVE-2026-4878-libcap2.md` resolved or remove after fix
    - Trivy Code Scanning alert #588 remains closed on `main`

<a id="ledger-p1-remove-trivy-suppression-gnutls-cve-2026-33845"></a>
- [x] Remove Trivy suppression for libgnutls30 CVE-2026-33845
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR #1846
  - Status: Closed by PR #1846 after the Rego suppression was removed instead of extended.
  - Area: security / base-image / code-scanning
  - Finding Type: container base image vulnerability
  - Reason: GitHub Code Scanning alert #589 reports `libgnutls30` `CVE-2026-33845` at `3.7.9-2+deb12u5`. PR #1846 removed the Rego suppression instead of extending the expired review window; current-head Trivy must verify scanner state.
  - Links:
    - https://github.com/Katsiarynakavaleuskaya/PulsePlate/security/code-scanning/589
    - docs/security/CVE-2026-33845-gnutls.md
    - trivy/ignore-policy.rego
  - DoD:
    - Debian or Trivy metadata publishes a fixed `libgnutls30` package context
    - Remove suppression rule from `trivy/ignore-policy.rego`
    - Mark `docs/security/CVE-2026-33845-gnutls.md` resolved or update with remediation evidence
    - Trivy Code Scanning alert #589 remains closed on `main`

<a id="ledger-p1-remove-trivy-suppression-gnutls-cve-2026-33846"></a>
- [x] Remove Trivy suppression for libgnutls30 CVE-2026-33846
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR #1846
  - Status: Closed by PR #1846 after the Rego suppression was removed instead of extended.
  - Area: security / base-image / code-scanning
  - Finding Type: container base image vulnerability
  - Reason: GitHub Code Scanning alert #590 reports `libgnutls30` `CVE-2026-33846` at `3.7.9-2+deb12u5`. PR #1846 removed the Rego suppression instead of extending the expired review window; current-head Trivy must verify scanner state.
  - Links:
    - https://github.com/Katsiarynakavaleuskaya/PulsePlate/security/code-scanning/590
    - docs/security/CVE-2026-33846-gnutls.md
    - trivy/ignore-policy.rego
    - https://security-tracker.debian.org/tracker/CVE-2026-33846
  - DoD:
    - Debian bookworm publishes a fixed `libgnutls30` package context or Trivy/GitHub reports a non-empty fixed version for bookworm
    - Remove suppression rule from `trivy/ignore-policy.rego`
    - Mark `docs/security/CVE-2026-33846-gnutls.md` resolved or update with remediation evidence
    - Trivy Code Scanning alert #590 remains closed on `main`

<a id="ledger-p1-remove-trivy-suppression-jwt-cve-2026-45363"></a>
- [x] Remove Trivy suppression for Ruby jwt CVE-2026-45363
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: #1839
  - Status: Closed by PR #1839 after Fastlane `2.235.0` permitted the patched `jwt 3.2.0` resolver path.
  - Area: security / iOS release tooling / code-scanning
  - Finding Type: release-tooling dependency vulnerability
  - Reason: GitHub Code Scanning alert #594 and Dependabot alert #142 reported Ruby gem `jwt` `CVE-2026-45363` at `2.10.2` from `ios/Gemfile.lock`, with fixed version `3.2.0`. Bundler resolver evidence on 2026-05-26 shows Fastlane `2.235.0` now permits `jwt >= 2.1.0, < 4`, and the lockfile resolves `jwt 3.2.0`; PR #1839 removed the obsolete Trivy suppression.
  - Links:
    - https://github.com/Katsiarynakavaleuskaya/PulsePlate/security/dependabot/142
    - https://github.com/Katsiarynakavaleuskaya/PulsePlate/security/code-scanning/594
    - docs/security/CVE-2026-45363-jwt-fastlane.md
    - trivy/ignore-policy.rego
    - scripts/ci/check_jwt_fastlane_unblock.py
    - scripts/ci/check_trivy_ignore_policy_expiry.py
    - https://github.com/advisories/GHSA-c32j-vqhx-rx3x
    - https://rubygems.org/gems/fastlane/versions/2.234.0
    - https://rubygems.org/gems/jwt/versions/3.2.0
  - DoD:
    - Fastlane publishes a compatible release that permits `jwt >= 3.2.0`, or iOS release tooling no longer depends on Fastlane's `jwt` 2.x graph
    - Update `ios/Gemfile.lock` to remove the vulnerable `jwt` resolution
    - Remove suppression rule from `trivy/ignore-policy.rego`
    - Mark `docs/security/CVE-2026-45363-jwt-fastlane.md` resolved or update with remediation evidence
    - Trivy Code Scanning alert #594 remains closed on `main`

<a id="ledger-p1-remove-trivy-suppression-faraday-cve-2026-54297"></a>
- [x] P1: Remove Trivy suppression for Ruby Faraday CVE-2026-54297
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: codex/dependency-cleanup-faraday-runtime-drift for the lock remediation; codex/fix-trivy-ignore-policy-expiry for scanner-lag suppression removal
  - Status: Closed by the 2026-07-05 scanner-lag removal lane. `ios/Gemfile.lock` remains on `faraday@1.10.6` with Fastlane `2.235.0`, and Trivy v0.71.2 with the refreshed vulnerability DB no longer reports `CVE-2026-54297` for `faraday@1.10.6` in the no-policy filesystem scan.
  - Area: security / iOS release tooling / code-scanning
  - Finding Type: scanner-lag follow-up for release-tooling dependency vulnerability
  - Reason: `bundle lock --update faraday` resolves `faraday 1.10.6` without changing Fastlane `2.235.0`, which removes the old `faraday 1.10.5` lock. The 2026-07-05 Trivy recheck no longer reports `CVE-2026-54297` for `faraday@1.10.6`, so the temporary scanner-lag suppression was removed instead of extended.
  - Links:
    - docs/security/CVE-2026-54297-faraday-fastlane.md
    - trivy/ignore-policy.rego
    - scripts/ci/check_trivy_ignore_policy_expiry.py
    - https://avd.aquasec.com/nvd/cve-2026-54297
    - https://rubygems.org/gems/faraday/versions/1.10.6
    - https://rubygems.org/gems/fastlane/versions/2.235.0
    - https://rubygems.org/gems/faraday/versions/2.14.3
  - DoD:
    - Keep `ios/Gemfile.lock` on `faraday 1.10.6` or newer without broad Fastlane/release-tooling churn
    - Remove the old `faraday@1.10.5` suppression rule from `trivy/ignore-policy.rego`
    - Remove the scanner-lag suppression for `faraday@1.10.6`
    - Mark `docs/security/CVE-2026-54297-faraday-fastlane.md` resolved with final scanner-lag removal evidence

<a id="ledger-p1-reconcile-open-dependabot-alerts"></a>
- [ ] P1: Reconcile open Dependabot alerts on `main` after manifest fixes
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-TBD-STALE-DEPENDABOT-RECONCILIATION
  - Area: security / dependencies / scanner-state
  - Finding Type: stale alert reconciliation
  - Reason: As of 8 April 2026, GitHub Dependabot on `main` still reports open alerts `#100`, `#99`-`#95`, `#94`, and `#93`-`#92` for `addressable`, `hono`, `@hono/node-server`, and `vite`, while the repo manifests already show newer dependency states (`ios/Gemfile.lock` -> `addressable 2.9.0`, `package-lock.json` -> `hono 4.12.12` and `@hono/node-server 1.19.13`, `frontend/package-lock.json` -> `vite 6.4.2`). These alerts appear stale relative to current manifests, but require per-alert reconciliation against the GitHub advisory boundary and scanner refresh state. That work must stay in a dedicated follow-up instead of expanding the narrow root npm remediation PR for `smol-toml` / `yaml`.
  - Links:
    - `ios/Gemfile.lock`
    - `package-lock.json`
    - `frontend/package-lock.json`
    - `docs/review/PR_1372_FIXED_MAPPING.md`
  - Child items (one alert bundle per package/advisory family):
    - `ledger-p1-dependabot-alert-105-axios`
    - `ledger-p1-dependabot-alert-106-axios`
    - `ledger-p1-dependabot-alert-100-addressable`
    - `ledger-p1-dependabot-alert-99-95-hono`
    - `ledger-p1-dependabot-alert-94-hono-node-server`
    - `ledger-p1-dependabot-alert-93-92-vite`
  - DoD:
    - Confirm whether GitHub auto-closes the alerts after the next scanner refresh on `main`
    - If alerts remain open, document per-alert evidence that `main` already carries the patched version or open a dedicated triage PR with that evidence
    - Resolve the stale-alert state without reopening unrelated dependency drift in the narrow remediation PR

<a id="ledger-p1-dependabot-alert-105-axios"></a>
- [ ] P1: Reconcile Dependabot alert `#105` (`axios`) on `main`
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-TBD-DEPENDABOT-AXIOS-105-106-RECONCILIATION
  - Area: security / node / scanner-state
  - Finding Type: stale alert reconciliation
  - Reason: Clean-main verification for PR `#1394` showed that root
    `package.json` still declares `@goplus/agentguard ^1.0.12` and root
    `package-lock.json` still contains both
    `node_modules/@goplus/agentguard 1.0.12` and `node_modules/axios 1.13.6`.
    That means alert `#105` is not yet proven stale relative to current repo
    truth. This bundled lane first formalizes coordinator ownership, adds the
    repo-owned root npm dependency submission workflow, and records corrected
    evidence so the follow-up remediation PR can remove or replace the live
    carrier path with minimum scope. Alert `#105` is handled together with alert
    `#106` in one bundled reconciliation lane.
  - Links:
    - `package.json`
    - `package-lock.json`
    - `docs/orchestration/DEPENDABOT_ALERTS_105_106_RECONCILIATION_TASK_PACKET_2026-04-11.md`
    - `docs/security/CVE-2025-62718-axios.md`
    - `docs/audit/DEPENDABOT_RECURRING_SECURITY_DRIFT_AUDIT_2026-04-10.md`
    - `https://github.com/Katsiarynakavaleuskaya/PulsePlate/security/dependabot/105`
  - DoD:
    - Re-check live alert state, SBOM state, and current-head `main` workflow completion after the latest merge
    - Prove whether a follow-up runtime remediation removes the live root
      `@goplus/agentguard -> axios` carrier on current `main`
    - Use the repo-owned npm dependency submission lane as the post-remediation
      graph-refresh proof loop

<a id="ledger-p1-dependabot-alert-106-axios"></a>
- [ ] P1: Reconcile Dependabot alert `#106` (`axios`) on `main`
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-TBD-DEPENDABOT-AXIOS-105-106-RECONCILIATION
  - Area: security / node / scanner-state
  - Finding Type: stale alert reconciliation
  - Reason: On clean `origin/main`, root `package.json` and root
    `package-lock.json` still show the live `@goplus/agentguard -> axios`
    runtime path (`@goplus/agentguard 1.0.12`, `axios 1.13.6`), so alert `#106`
    is not yet proven stale relative to current repo truth. This alert is
    bundled with alert `#105` into one coordinator-owned lane that lands the
    repo-owned npm dependency submission workflow and corrected evidence first,
    then hands off to a minimum follow-up remediation PR.
  - Links:
    - `package.json`
    - `package-lock.json`
    - `docs/orchestration/DEPENDABOT_ALERTS_105_106_RECONCILIATION_TASK_PACKET_2026-04-11.md`
    - `docs/security/CVE-2026-40175-axios.md`
    - `docs/audit/DEPENDABOT_RECURRING_SECURITY_DRIFT_AUDIT_2026-04-10.md`
    - `https://github.com/Katsiarynakavaleuskaya/PulsePlate/security/dependabot/106`
  - DoD:
    - Re-check live alert state, SBOM state, and current-head `main` workflow completion after the latest merge
    - Prove whether a follow-up runtime remediation removes the live root
      `@goplus/agentguard -> axios` carrier on current `main`
    - Use the repo-owned npm dependency submission lane as the post-remediation
      graph-refresh proof loop

<a id="ledger-p1-dependabot-alert-100-addressable"></a>
- [ ] P1: Reconcile Dependabot alert `#100` (`addressable`) on `main`
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-TBD-DEPENDABOT-100-ADDRESSABLE
  - Area: security / ruby / scanner-state
  - Finding Type: stale alert reconciliation
  - Reason: GitHub still reports alert `#100` for `addressable` against `ios/Gemfile.lock`, while the lockfile already carries `addressable 2.9.0`. Confirm whether the advisory boundary still applies or whether this is scanner lag requiring refresh evidence.
  - Links:
    - `ios/Gemfile.lock`
    - `https://github.com/Katsiarynakavaleuskaya/PulsePlate/security/dependabot/100`
  - DoD:
    - Capture the patched version/advisory boundary for alert `#100`
    - Confirm whether `ios/Gemfile.lock` already satisfies the patched floor or open a dedicated remediation PR
    - Close the alert on `main` or record scanner-refresh evidence showing why closure is pending

<a id="ledger-p1-dependabot-alert-99-95-hono"></a>
- [ ] P1: Reconcile Dependabot alerts `#99`-`#95` (`hono`) on `main`
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-TBD-DEPENDABOT-99-95-HONO
  - Area: security / node / scanner-state
  - Finding Type: stale alert reconciliation
  - Reason: GitHub still reports five open `hono` alerts against `package-lock.json`, while the lockfile already shows `hono 4.12.12`. Reconcile each advisory against the current lockfile and determine whether a scanner refresh or a dedicated CVE-scoped follow-up PR is required.
  - Links:
    - `package-lock.json`
    - `https://github.com/Katsiarynakavaleuskaya/PulsePlate/security/dependabot/99`
    - `https://github.com/Katsiarynakavaleuskaya/PulsePlate/security/dependabot/98`
    - `https://github.com/Katsiarynakavaleuskaya/PulsePlate/security/dependabot/97`
    - `https://github.com/Katsiarynakavaleuskaya/PulsePlate/security/dependabot/96`
    - `https://github.com/Katsiarynakavaleuskaya/PulsePlate/security/dependabot/95`
  - DoD:
    - Record per-alert advisory boundaries for `#99`-`#95`
    - Prove whether `package-lock.json` already carries patched `hono` versions for each alert
    - Close the alerts via scanner refresh or open dedicated CVE-scoped PRs where lockfile remediation is still required

<a id="ledger-p1-dependabot-alert-94-hono-node-server"></a>
- [ ] P1: Reconcile Dependabot alert `#94` (`@hono/node-server`) on `main`
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-TBD-DEPENDABOT-94-HONO-NODE-SERVER
  - Area: security / node / scanner-state
  - Finding Type: stale alert reconciliation
  - Reason: GitHub still reports alert `#94` for `@hono/node-server` against `package-lock.json`, while the lockfile already shows `@hono/node-server 1.19.13`. Confirm whether the advisory is stale or whether additional remediation remains.
  - Links:
    - `package-lock.json`
    - `https://github.com/Katsiarynakavaleuskaya/PulsePlate/security/dependabot/94`
  - DoD:
    - Capture the patched version/advisory boundary for alert `#94`
    - Confirm whether `package-lock.json` already satisfies the patched floor or open a dedicated remediation PR
    - Close the alert on `main` or record scanner-refresh evidence showing why closure is pending

<a id="ledger-p1-dependabot-alert-93-92-vite"></a>
- [ ] P1: Reconcile Dependabot alerts `#93`-`#92` (`vite`) on `main`
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-TBD-DEPENDABOT-93-92-VITE
  - Area: security / frontend / scanner-state
  - Finding Type: stale alert reconciliation
  - Reason: GitHub still reports two open `vite` alerts against `frontend/package-lock.json`, while the lockfile already shows `vite 6.4.2`. Reconcile each advisory against the current frontend lockfile and determine whether a scanner refresh or a dedicated frontend remediation PR is required.
  - Links:
    - `frontend/package-lock.json`
    - `https://github.com/Katsiarynakavaleuskaya/PulsePlate/security/dependabot/93`
    - `https://github.com/Katsiarynakavaleuskaya/PulsePlate/security/dependabot/92`
  - DoD:
    - Record per-alert advisory boundaries for `#93` and `#92`
    - Prove whether `frontend/package-lock.json` already carries patched `vite` versions for both alerts
    - Close the alerts via scanner refresh or open dedicated CVE-scoped PRs where frontend remediation is still required

<a id="ledger-p1-ai-reliability-experiment-sublane"></a>
- [ ] P1: AI reliability experimentation sublane for logic + philosophy offline replay
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: codex/ai-reliability-experiment-sublane-w1 (placeholder)
  - Area: orchestration / experimentation / AI reliability
  - Finding Type: applied-eval lane gap
  - Reason: PulsePlate already has the governed experimentation umbrella and philosophical runtime foundation, but it still lacks one canonical offline replay + ablation packet dedicated to proving whether `logic` and `philosophy` layers actually improve answer correctness/readiness before any runtime rollout.
  - Links:
    - `docs/orchestration/AGENT_EXPERIMENTATION_PROTOCOL.md`
    - `docs/orchestration/RESEARCH_BRAINSTORMING_PROTOCOL.md`
    - `docs/orchestration/contracts/LOGIC_PHILOSOPHY_REPLAY_EVAL_CONTRACT.md`
    - `core/insight/philosophical_runtime.py`
    - `core/insight/analytical/__init__.py`
    - `scripts/orchestration/experiment_bootstrap.py`
    - `scripts/orchestration/logic_philosophy_replay_contract.py`
    - `scripts/orchestration/logic_philosophy_replay_eval.py`
    - `tests/fixtures/orchestration/logic_philosophy_replay/replay_cases.json`
    - `tests/fixtures/orchestration/logic_philosophy_replay/replay_negative_controls.json`
    - `tests/test_logic_philosophy_replay_eval.py`
  - DoD:
    - Canonical experiment packet supports `A0 control`, `A1 logic`, `A2 philosophy`, and `A3 combined`
    - Immutable offline oracle corpus and readiness proxy fixtures are declared before execution
    - Primary metrics include correctness, unsupported-claim rate, contradiction rate, and first-pass readiness proxy
    - No phase of the sublane permits live runtime mutation, autonomous merge, or provider/network spend in wave 1
    - Result packet can only promote to `pr_packet` after a passing offline replay artifact exists

<a id="ledger-p1-guided-planning-mvp-roadcut-quality-pass"></a>
- [ ] P1: Guided Planning MVP roadcut quality pass
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (MVP value delivery after Slack/operator closeout)
  - Target PR: PR-TBD-GUIDED-PLANNING-MVP-ROADCUT (`feat(frontend): carry guided planning roadcut through setup and progress`)
  - Status: Selected next active product lane after PR #1853 closeout. Execution requires a fresh synced-main startup, preflight, task bootstrap, mandatory role-agent passes, premortem risk review, Experiment Runner oracle evidence, post-open QA / bug-hunter / security-auditor, exact-material `pulseplate-pr-review`, finding disposition, and the provider-neutral no-claim seal before readiness claims; Connector/Codex Security output is never invoked or awaited.
  - Area: frontend / Guided Planning MVP / product roadcut
  - Finding Type: MVP value-delivery gap
  - Reason: PR #1842 through PR #1844 delivered the Guided Planning Preview, frontend-only observability/accessibility hooks, and save/progress flow. The next bounded product PR should carry the selected intent/time preview through the existing setup and result/progress route affordances so the user sees one coherent MVP roadcut, without turning frontend, Slack, Drive, or local evidence snapshots into product/runtime authority.
  - Links:
    - `frontend/src/pages/Home.tsx`
    - `frontend/src/pages/NutritionSetup/index.tsx`
    - `frontend/src/pages/NutritionSetup/ResultView.tsx`
    - `frontend/src/pages/Progress.tsx`
    - `frontend/src/lib/settings.tsx`
    - `docs/review/PR_1842_FIXED_MAPPING.md`
    - `docs/review/PR_1843_FIXED_MAPPING.md`
    - `docs/review/PR_1844_FIXED_MAPPING.md`
    - `docs/design/DESIGN_SYSTEM_AUTOMATION_SPEC.md`
  - DoD:
    - Guided-planning intent/time/preview data is extracted from `Home.tsx` into a typed frontend module and reused by Home plus Nutrition Setup surfaces
    - `SettingsProvider` has typed in-memory support for `setup` and `guidedPlanningDraft`; no localStorage, cookies, backend analytics, DB, OpenAPI, or health identifiers are added
    - Home writes the guided-planning draft on save/continue; Nutrition Setup renders an accessible planning-direction panel when a draft exists; Result View renders a compact next-step rail to existing `/plate` and `/progress` routes
    - Existing route/auth behavior is preserved: `/plate` and `/progress` remain protected by `RequireKey`, and unauthenticated users still reach the existing key prompt
    - `/pulseplate-runner mvp-evidence` remains stable; no new Slack commands or MVP evidence event names are added unless a later implementation PR proves a contract change is required and updates tests/mapping
    - Focused frontend tests, token checks, build, `make validate-changed`, `pre-commit run --all-files`, and final `make verify` pass before any merge-readiness claim

---


### P2

<a id="ledger-p2-experiment-runner-slack-identity-boundary"></a>
- [x] P2: Experiment Runner Slack identity boundary
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: `codex/experiment-runner-slack-identity-boundary`
  - Status: Completed as an operator-notification-only boundary; Slack remains non-cryptographic, non-Git-attribution, non-review, and non-merge authority.
  - Area: orchestration / security / notifications
  - Reason (EN): The Experiment Runner may later need a Slack display or bot identity for operator-facing notifications, but Slack is not a cryptographic Git identity and must not be introduced as part of Git attribution governance. A Slack identity requires a separate security-reviewed secret, channel, audit, and rate-limit boundary.
  - Links: `docs/orchestration/GOVERNED_NON_HUMAN_IDENTITY_POLICY.md`, `docs/orchestration/AGENT_EXPERIMENTATION_PROTOCOL.md`
  - DoD: The governed Slack boundary defines runtime-only bot credentials, channel allowlist, redacted message body contract, local audit artifact, rate/timeout/idempotency behavior, and deterministic tests proving no secrets, raw patch text, oracle stdout/stderr, or user data are posted.

<a id="ledger-p2-slack-mvp-evidence-ledger-snapshot"></a>
- [x] P2: Guided Planning MVP evidence ledger snapshot for Slack bridge
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR #1852 (`codex/slack-guided-planning-mvp-evidence-summaries`)
  - Status: Completed and landed in PR #1852.
  - Area: orchestration / Slack bridge / MVP evidence
  - Reason: The `/pulseplate-runner mvp-evidence` operator command needed a durable, sanitized, aggregate-only snapshot path so Slack could summarize Guided Planning MVP evidence without becoming analytics, review, or merge authority.
  - Links:
    - `scripts/orchestration/mvp_evidence_snapshot.py`
    - `scripts/orchestration/experiment_slack_socket_bridge.py`
    - `docs/review/PR_1852_FIXED_MAPPING.md`
    - `docs/review/PREMORTEM_SLACK_MVP_EVIDENCE_LEDGER.md`
  - DoD:
    - Snapshot reads and corrupt/missing snapshot fallback are deterministic and test-covered
    - Snapshot artifacts remain aggregate-only and sanitized
    - Slack output remains display-only and redacted

<a id="ledger-p2-experiment-runner-slack-bridge-module-boundaries"></a>
- [x] P2: Split Experiment Runner Slack bridge into bounded modules
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR #1853 (`codex/slack-bridge-module-boundaries`)
  - Status: Completed and landed in PR #1853 on 2026-05-31 (`bc1ac85042410fa5c29221b75b12585743f92fe7`). This closeout records landed backlog truth only; it does not reopen Slack bridge code, runtime behavior, Slack commands, backend/OpenAPI, iOS, auth, billing, Drive/Figma/Kimi evidence, or root-artifact hygiene.
  - Area: orchestration / Slack bridge / maintainability / security
  - Finding Type: module-boundary refactor
  - Reason: `scripts/orchestration/experiment_slack_socket_bridge.py` grew into a single large operator boundary that mixes config/runtime validation, parsing/rendering, audit/idempotency/rate limiting, dispatch/live approval, optional Slack transport, and CLI. The next PR should split internals without changing `python3 -m scripts.orchestration.experiment_slack_socket_bridge`, command semantics, dry-run defaults, or security boundaries.
  - Links:
    - `scripts/orchestration/experiment_slack_socket_bridge.py`
    - `tests/test_experiment_slack_socket_bridge.py`
    - `tests/test_mvp_evidence_snapshot.py`
    - `docs/review/PREMORTEM_SLACK_BRIDGE_SPLIT.md`
    - `docs/review/PR_1853_FIXED_MAPPING.md`
  - DoD:
    - Bridge internals are split into bounded modules for config, parsing/rendering, audit/idempotency/rate limiting, dispatch/live approval, and optional Slack transport
    - Facade/CLI compatibility remains intact for existing imports and `python3 -m scripts.orchestration.experiment_slack_socket_bridge`
    - Optional Slack SDK imports stay lazy; dry-run validation and `--help` require no Slack packages
    - Hash-only audit, idempotency, rate-limit, allowlist, execute-mode, workflow allowlist, and live-approval behavior remain test-covered
    - Mandatory pre-open and post-open role-agent passes, premortem, Experiment Runner oracle review, and Codex Security scan are recorded in review artifacts and PR body mirror

<a id="ledger-p2-root-artifact-hygiene-follow-up"></a>
- [ ] P2: Root-level artifact hygiene follow-up after Slack bridge split
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: `PR-TBD-ROOT-ARTIFACT-HYGIENE`
  - Status: Planned follow-up; explicitly out of scope for the Slack bridge split PR and this PR #1853 closeout / Guided Planning MVP roadcut selection lane.
  - Area: repo hygiene / docs / scripts
  - Finding Type: repository organization debt
  - Reason: Current root-level clutter and generated/test artifacts should be classified and either deleted, moved to existing folders, or explicitly kept at root through a separate governance lane. This must not be bundled into the Slack bridge module-boundary PR because broad root moves would obscure security-sensitive Slack bridge behavior.
  - Links:
    - `AGENTS.md`
    - `RUNBOOK_AGENT.md`
    - `docs/roadmap/BACKLOG_LEDGER.md`
  - DoD:
    - Root-level files are classified into keep/delete/move/defer with evidence
    - Local/generated artifacts are removed or ignored without committing `artifacts/`, `worktrees/`, caches, coverage files, or report outputs
    - Any file moves preserve import/CLI contracts and include focused tests or explicit docs evidence
    - The PR avoids runtime/provider/OpenAPI changes unless separately scoped

<a id="ledger-p2-pulseplate-pr-review-context-collector"></a>
- [x] P2: Add read-only context collector for PulsePlate PR review skill
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2 (review automation follow-up)
  - Target PR: PR #1539 (`docs/orchestration/PULSEPLATE_PR_REVIEW_SKILL_PR2_CONTEXT_COLLECTOR_PACKET_2026-04-26.md`, docs/review/PR_1539_FIXED_MAPPING.md)
  - Status: Completed in PR #1539; closeout recorded in PR3 dry-run report runner lane
  - Area: orchestration / PR review / Codex skills
  - Reason: PR1 intentionally keeps `pulseplate-pr-review` passive and documentation/router-only. A separate follow-up should add a read-only collector for changed files, diff stats, scoped `AGENTS.md`, PR metadata, fixed-mapping state, and relevant test suggestions after the skill contract is merged and reviewed.
  - Links:
    - `tools/codex_skills/pulseplate-pr-review/SKILL.md`
    - `docs/orchestration/PULSEPLATE_PR_REVIEW_SKILL_PACKET_2026-04-24.md`
    - `scripts/orchestration/skill_router.py`
  - DoD:
    - `scripts/orchestration/pr_review_context.py` collects context without mutating repo files or GitHub state
    - collector output has a stable JSON schema usable by `pulseplate-pr-review`
    - tests cover branch diff, scoped `AGENTS.md` discovery, missing PR metadata, and fixed-mapping absence
    - the collector remains advisory and does not post GitHub comments, resolve threads, or claim merge readiness

<a id="ledger-p2-cursor-role-agents-readonly-frontmatter"></a>
- [ ] P2: Cursor role-agent read-only frontmatter alignment
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2 (agent workflow safety)
  - Target PR: current PR-A closeout lane (`codex/pr1853-guided-planning-roadcut-closeout`)
  - Status: Operator-approved scope expansion for the PR #1853 closeout lane; pending PR merge. Coordinator pre-open review found that `readonly: true` is executable dispatch metadata, so this lane also owns the minimal bridge/docs/tests update that keeps runtime implementation ownership explicit.
  - Area: agent workflow / Cursor role-agent metadata
  - Finding Type: role-agent mutation-safety hardening
  - Reason: Mandatory PulsePlate role-agent passes are expected to produce review/routing evidence without mutating the repo unless a coordinator packet explicitly assigns implementation ownership. Cursor role metadata should make that default explicit so operator-dispatched agents remain read-only while Codex owns the implementation diff for this lane.
  - Links:
    - `.cursor/agents/AGENTS.md`
    - `.cursor/agents/agent-coordinator.md`
    - `.cursor/agents/qa-engineer-agent.md`
    - `.cursor/agents/bug-hunter.md`
    - `.cursor/agents/security-auditor.md`
    - `scripts/orchestration/role_dispatch_bridge.py`
    - `scripts/orchestration/qoder_dispatch_bridge.py` (compatibility facade)
    - `tests/test_qoder_dispatch_bridge.py`
  - DoD:
    - Every checked-in `.cursor/agents/*.md` role file except scoped `.cursor/agents/AGENTS.md` includes `readonly: true` in frontmatter
    - `role_dispatch_bridge.py --mode runtime` keeps frontmatter-readonly implementation roles read-only unless a coordinator packet invocation explicitly passes `--implementation-owner <role>`; ad-hoc `--roles` owner overrides fail closed
    - Dispatch manifest entries record when an explicit implementation-owner override clears readonly routing for `backend-engineer`, `frontend-engineer`, or `dev-operator`
    - `python scripts/orchestration/check_agent_consistency.py` passes after the metadata update
    - No role capability prose, routing graph, capability matrix, or context map changes are bundled into this scope expansion

<a id="ledger-p2-pulseplate-pr-review-dry-run-report-runner"></a>
- [x] P2: Add dry-run report runner for PulsePlate PR review skill
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2 (review automation follow-up)
  - Target PR: PR #1558 (`docs/orchestration/PULSEPLATE_PR_REVIEW_SKILL_PR3_DRY_RUN_REPORT_PACKET_2026-04-28.md`, docs/review/PR_1558_FIXED_MAPPING.md)
  - Status: Completed in merged PR #1558; closeout recorded in PR4 calibration lane
  - Area: orchestration / PR review / Codex skills
  - Reason: PR2 provides read-only review context JSON, but reviewers still need a deterministic Markdown/JSON dry-run report that follows the `pulseplate-pr-review` role order and finding schema without posting comments or resolving threads.
  - Links:
    - `scripts/orchestration/pr_review_context.py`
    - `tools/codex_skills/pulseplate-pr-review/SKILL.md`
    - `docs/orchestration/PULSEPLATE_PR_REVIEW_SKILL_PR3_DRY_RUN_REPORT_PACKET_2026-04-28.md`
  - DoD:
    - `scripts/orchestration/pr_review_report.py` consumes context JSON from file or stdin
    - report output supports stable Markdown and JSON formats
    - findings follow the `pulseplate-pr-review` schema and coordinator role order
    - runner remains advisory and does not post GitHub comments, resolve review threads, or claim merge readiness

<a id="ledger-p2-pulseplate-pr-review-calibration-rubric"></a>
- [x] P2: Calibrate PulsePlate PR review dry-run false-positive rubric
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2 (review automation follow-up)
  - Target PR: PR #1560 (`docs/orchestration/PULSEPLATE_PR_REVIEW_SKILL_PR4_CALIBRATION_PACKET_2026-04-28.md`, docs/review/PR_1560_FIXED_MAPPING.md)
  - Status: Completed in merged PR #1560; PR #1562 is the hygiene-only closeout that updates stale ledger state after merge
  - Area: orchestration / PR review / Codex skills
  - Reason: PR3 added a side-effect-free dry-run report runner, but any future dry-run-to-comment path needs deterministic calibration first so benign context and `NOT-A-BUG` reviewer patterns do not become noisy actionable comments.
  - Links:
    - `scripts/orchestration/pr_review_report.py`
    - `tests/test_pr_review_report.py`
    - `tools/codex_skills/pulseplate-pr-review/SKILL.md`
    - `docs/orchestration/PULSEPLATE_PR_REVIEW_SKILL_PR4_CALIBRATION_PACKET_2026-04-28.md`
  - DoD:
    - report output includes explicit calibration metadata that never claims posting eligibility
    - tests cover clean context, governance findings, warning-bearing context, benign fixed-mapping patterns, and large diff risk
    - skill docs state calibration is required before any future GitHub posting path
    - runner remains advisory and does not post GitHub comments, resolve review threads, or claim merge readiness
  - Closeout:
    - Required PR-review skill implementation slices PR1-PR4 are complete.
    - GitHub posting, automatic thread resolution, and model/scoring evals remain optional future lanes, not open required tails in this epic.

<a id="ledger-p2-rag-release-gates-runtime-warnings-dedup"></a>
- [ ] P2: Deduplicate `EvalRuntimeState.warnings` in RAG release-gates runner
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2 (eval observability / operator noise)
  - Target PR: `PR-TBD-RAG-RELEASE-GATES-WARNINGS-DEDUP`
  - Status: Open (deferred from RAG weekly small-fixture advisory lane)
  - Area: evals / RAG release gates / observability
  - Reason (EN): `_record_strict_violation` appends every message to `state.warnings` without dedupe while `strict_violations` dedupes when fallbacks are disallowed; multi-row evals and repeated `build_metrics_summary` calls can duplicate identical warning lines. Operators and tooling should see one row per unique finding. (RU: повторяющиеся строки в `runtime_warnings` при многократных событиях — шум; нужен дедуп как у `strict_violations` или append-if-not-seen.)
  - Links:
    - `scripts/evals/run_rag_release_gates.py` (`_record_strict_violation`, `build_metrics_summary` advisory warning)
  - DoD:
    - Duplicate identical warning strings are not appended N times for the same eval run
    - Deterministic test proves dedupe behavior for repeated `_record_strict_violation` with the same message
    - `metrics_summary["runtime_warnings"]` contract documented if consumers rely on uniqueness

<a id="ledger-p2-dependency-fallback-artifact-dedup"></a>
- [ ] P2: Deduplicate dependency fallback version references across packet / ledger / tests
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2 (dependency-governance follow-up)
  - Target PR: `PR-TBD-DEPENDENCY-FALLBACK-DEDUP`
  - Status: Planned
  - Area: docs / CI / dependency governance
  - Reason (EN): Narrow dependency remediation lanes currently repeat the same fallback package/version tuples across `scripts/ci/emergency_python_wheels.json`, backlog evidence, orchestration packets, and narrow tests. That duplication increases drift risk and makes line-range evidence brittle as the manifest evolves. A follow-up lane should introduce a more stable single-source-of-truth pattern or generator and replace line-range references with package/key-based evidence anchors. (RU: узкие dependency remediation lane сейчас дублируют одни и те же fallback package/version tuple в `scripts/ci/emergency_python_wheels.json`, ledger evidence, orchestration packet и узких тестах. Такое дублирование повышает риск дрейфа и делает line-range evidence хрупким при эволюции manifest. Нужен отдельный follow-up lane с более устойчивым single-source-of-truth/generator pattern и package/key-based ссылками вместо диапазонов строк.)
  - Links:
    - `scripts/ci/emergency_python_wheels.json`
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-cryptography-private-index-sync`
    - `docs/orchestration/DEPENDABOT_PR_1474_TRANSFORMERS_REMEDIATION_PACKET_2026-04-20.md`
    - `tests/test_install_locked_python_requirements.py`
  - DoD:
    - A canonical source exists for dependency fallback package/version tuples used by narrow remediation artifacts
    - Ledger/package evidence points to package keys or stable anchors rather than fragile line ranges
    - Narrow dependency remediation packets/tests consume the canonical source without manual tuple drift

<a id="ledger-p2-dagger-pilot-after-docker-baseline"></a>
- [ ] P2: Re-evaluate Dagger pilot only after Docker baseline stabilizes
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR-TBD-DAGGER-PILOT
  - Area: CI orchestration / build platform / deferred evaluation
  - Depends on:
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-ci-install-profile-split-after-disk-unblock`
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-docker-deploy-contract-reconciliation`
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-docker-image-budget-telemetry`
    - `docs/roadmap/BACKLOG_LEDGER.md#backlog-restore-signed-build-provenance`
  - Reason: Dagger is not part of the landed GitHub Actions Docker/CI baseline. Revisit only through a separate P2 evaluation packet after the landed baseline, release-truth state, and security-artifact posture are re-reviewed.
  - Links:
    - `docs/orchestration/DOCKER_CI_DISCIPLINE_PR_SERIES_PACKET_2026-04-16.md`
    - `docs/architecture/ADR_DOCKER_BUILD_PROVENANCE_WORKAROUND_2026-03-01.md`
    - `docs/roadmap/BACKLOG_LEDGER.md#backlog-restore-signed-build-provenance`
  - DoD:
    - Image-budget telemetry baseline exists and is referenced in the proposal
    - Install-profile split, deploy-contract reconciliation, build-path consolidation, and runtime-slimming closeout are merged
    - Release-truth state and signed security-artifact posture are re-reviewed before any pilot recommendation
    - Any pilot compares against the existing GitHub Actions control plane rather than bypassing it

<a id="ledger-p2-cloudflare-narrow-reopen-automation"></a>
- [ ] P2: Cloudflare narrow reopen automation after Access-based private recovery
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2 (edge ops / recovery ergonomics)
  - Target PR: PR-TBD-CLOUDFLARE-NARROW-REOPEN-AUTOMATION
  - Status: 📋 Deferred from PR `#1385`
  - Area: edge / Cloudflare / deploy
  - Reason (EN): PR `#1385` now supports a private-first recovery flow and successfully provisions full-host Cloudflare Access for `pulseplate.app`, but the current Cloudflare token scope cannot manage zone firewall/settings/ruleset endpoints (`9109 Unauthorized`). The documented narrow temporary public bypass for shell/discovery GET paths therefore remains a dashboard/manual ops step until zone-scope automation permissions are expanded.
  - Links:
    - `docs/deploy/CLOUDFLARE.md`
    - `docs/deploy/SPA_APEX_ROUTING_CONTRACT.md`
    - `deploy/PRODUCTION.md`
    - `deploy/WORKFLOW.md`
    - `docs/review/PR_1385_FIXED_MAPPING.md`
  - DoD:
    - Expanded Cloudflare token scope (or approved alternative auth path) can read/write the zone firewall/ruleset surfaces needed for temporary reopen controls
    - Automation applies the documented narrow allowlist only to shell/discovery GET paths without weakening `/api*`, `/admin*`, `/ws*`, `/openapi.json`, `/health`, `/docs*`, `/redoc*`, or `/debug_env`
    - Rollback path restores full-host Access or removes the temporary bypass deterministically
    - Operational runbook includes exact verification steps before and after public reopen

<a id="ledger-p2-legacy-app-direct-root-get-policy"></a>
- [ ] P2: Policy for `GET /` on FastAPI when clients bypass Caddy (direct `app:8000` / uvicorn)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2 (deploy ergonomics / operator clarity)
  - Target PR: #1229
  - Area: backend / deploy / legacy surface
  - Reason (EN): With SPA served at apex via Caddy, operators or health tools may still hit uvicorn directly. `legacy_app.py` behavior for `GET /` should be explicit: redirect to public origin, `404`, JSON probe, or documented “Caddy-only” with no code change — pick one and test if behavior changes.
  - Note (EN): Keep **open** until PR #1229 is merged; close via **docs-only** follow-up that sets `[x]` with merge evidence (ledger closure rule — do not pre-close in the implementation PR).
  - Links:
    - `docs/deploy/SPA_APEX_ROUTING_CONTRACT.md`
    - `deploy/Caddyfile.production`
    - `app/main.py` (canonical bootstrap registers direct-root probe + legacy HTML route)
  - DoD:
    - Documented policy in contract or runbook with `file:line` evidence
    - If code changes: deterministic tests for chosen status/body
    - No accidental regression for Caddy-served SPA or canonical API paths

<a id="ledger-p2-movement-performance-coaching-wave"></a>
- [ ] P2: Movement/performance coaching expansion lane
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2 (future product expansion / non-core coaching scope)
  - Target PR: PR-TBD-MOVEMENT-PERFORMANCE-COACHING-WAVE
  - Status: 📋 Planned
  - Reason (EN): The CBT Coaching Wave intentionally starts with cognition-first product surfaces. Movement, performance, and training-adjacent coaching should stay deferred until the structured reflection lanes are stable, so the next expansion can be packaged as a bounded product slice instead of widening the initial coaching umbrella too early.
  - Links:
    - `docs/insights/CBT_COACHING_PRODUCT_WAVE.md`
    - `docs/library/promotion/2026-03-21_cbt_coaching_wave_promotion-log.md`
    - `docs/contracts/FITCHEF_STRUCTURED_COACH_CONTRACT.md`
    - `docs/analytics/METRICS_CATALOG.md`
  - DoD:
    - One bounded movement/performance concept exists with explicit tier, route family, and safety framing
    - The expansion does not modify the live `/api/v1/insight/fitchef*` canon
    - Measurement plan defines activation, retention, and safety-review metrics before runtime work starts
    - Follow-up implementation remains separate from the cognition-first CBT coaching rollout

<a id="ledger-p2-personal-experiment-dashboard"></a>
- [ ] P2: Personal experiment dashboard lane
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2 (analytics UX / founder tooling)
  - Target PR: PR-TBD-PERSONAL-EXPERIMENT-DASHBOARD
  - Status: 📋 Planned
  - Reason (EN): The repo already has experiment governance and metrics catalogs, but a user-facing dashboard would create a separate product and analytics UX lane. It should remain deferred until the first coaching reports and structured runtime surfaces establish which metrics, experiments, and decision rules are stable enough to expose to users.
  - Links:
    - `docs/insights/CBT_COACHING_PRODUCT_WAVE.md`
    - `docs/library/promotion/2026-03-21_cbt_coaching_wave_promotion-log.md`
    - `docs/analytics/EXPERIMENT_REGISTRY.md`
    - `docs/analytics/DASHBOARD_BASELINE_REQUIREMENTS.md`
  - DoD:
    - Dashboard scope is limited to canonical experiment and metric objects already defined in repo contracts
    - User-facing dashboard copy avoids diagnostic or therapist framing
    - Every exposed chart/card has owner, metric definition, and decision rule
    - Follow-up PR keeps dashboard UX separate from structured coach runtime changes

<a id="ledger-p2-gha-node24-cache-warning-cleanup"></a>
- [ ] P2: GitHub Actions Node 24 migration and cache-warning cleanup
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2 (CI hygiene / advisory reliability)
  - Target PR: #1206 (`fix(ci): migrate gha actions to node24`), follow-up carryover after #1209 (`fix(ci): align frontend openapi sync with node 22`); replacement sequence: PR #1871 (`codex/gha-node24-action-runtime-cleanup`, direct action-runtime cleanup) plus PR #1875 (`codex/node24-runtime-baseline`, operational runtime baseline)
  - Status: 🚧 In progress / direct Node 24 action-runtime cleanup plus operational Node 24 baseline migration; cache-warning audit remains open pending fresh representative PR evidence
  - Area: ci / github-actions / cache
  - Finding Type: advisory workflow debt
  - Reason (EN): The #1204 merge cycle completed successfully, but workflows still required follow-up cleanup around Node-runtime drift and transient GHA cache warnings (`Cache service responded with 400`, `CreateCacheEntry ... 409 Conflict`, cache save/restore service noise). PR #1209 intentionally delivers the narrower Node 22 frontend/OpenAPI-sync stopgap so current-head CI stays stable while the broader Node 24/cache hygiene lane remains open until all representative workflows are re-audited.
  - Links:
    - [`.github/workflows/build.yml`](../../.github/workflows/build.yml)
    - [`.github/workflows/ci.yml`](../../.github/workflows/ci.yml)
    - Historical PR-lane duplicates removed in PR2: `pr-tests.yml`, `pr-coverage.yml`
    - [`.github/workflows/cd.yml`](../../.github/workflows/cd.yml)
    - [`docs/review/PR_1204_FIXED_MAPPING.md`](../review/PR_1204_FIXED_MAPPING.md)
    - [`docs/review/PR_1209_FIXED_MAPPING.md`](../review/PR_1209_FIXED_MAPPING.md)
  - DoD:
    - Representative CI workflows use Node 24-compatible action SHAs where upgrades are available
    - Cache usage in `build.yml`, `ci.yml`, and related PR workflows is re-audited for avoidable restore/save warnings
    - A fresh representative PR run completes without Node 20 deprecation warnings
    - Remaining cache warnings, if any, are explicitly documented as accepted transient backend noise rather than unexplained CI debt
  - Current evidence (2026-06-03, PR #1871 post-open):
    - Scoped direct Node 20 JavaScript action pins in representative checkout, Docker, setup-go, and upload-artifact workflows are replaced with verified Node 24 commit SHAs plus guard coverage
    - Current-head Docker/security-scan logs showed a remaining Node20 warning from nested `actions/cache@0400d5...` inside `aquasecurity/trivy-action@57a97...`
    - PR #1871 updates the pinned Trivy wrapper action to `ed142fd0673e97e23eac54620cfb913e5ce36c25 # v0.36.0 / Node 24 cache path` and guards the old wrapper/cache warning source
    - Current `codex/node24-runtime-baseline` lane moves `.nvmrc`, frontend engines, devcontainer, and frontend Caddy builder to Node 24.16.0, normalizes remaining active `upload-artifact` / actionlint checkout pins, and adds positive active-workflow enumeration guards
    - Broader cache-warning DoD remains open until fresh current-head PR logs prove warning cleanup and remaining cache-warning disposition

<a id="ledger-p2-ios-agents-only-testing-centralize"></a>
- [ ] P2: Centralize ios/AGENTS.md -only-testing list (Sourcery follow-up)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2 (maintainability)
  - Target PR: TBD (after PR #1179 merge)
  - Status: 📋 Deferred
  - Reason (EN): Sourcery review on PR #1179 suggested centralizing the repeated -only-testing xcodebuild list in ios/AGENTS.md (shared script, variable, or single referenced snippet) so future test-set changes don't require multiple manual updates. Scope expansion deferred until PR #1179 is merge-ready.
  - Links:
    - ios/AGENTS.md
    - docs/pr/PR-6_HANDOFF.md
  - DoD:
    - Single source for -only-testing test list (script, Makefile var, or referenced snippet)
    - All ios/AGENTS.md xcodebuild examples reference it
    - No scope creep into PR #1179

<a id="ledger-p2-fitchef-icon-source-cleanup"></a>
- [ ] P2: FitChef icon source cleanup after PR-2 selective promotion
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2 (asset hygiene / App Store readiness)
  - Target PR: PR #1154
  - Status: 🟡 In progress (active PR `#1154`)
  - Reason (EN): PR-2 intentionally normalizes the icon catalog and keeps only canonical referenced AppIcon files, but non-canonical local source files with spaces or duplicate generator naming are not promoted automatically. The remaining icon-source cleanup must stay explicit for the App Store production lane.
  - Links:
    - `docs/contracts/FITCHEF_MASCOT_ASSET_TAXONOMY.md`
    - `docs/contracts/FITCHEF_APP_STORE_VISUAL_CONTRACT.md`
    - `docs/contracts/FITCHEF_APP_STORE_PRODUCTION_PACK_EN.md`
    - `ios/PulsePlate/Assets.xcassets/AppIcon.appiconset/Contents.json`
  - DoD:
    - App Icon source files used for the App Store production pack are canonical, reviewed, and filename-stable
    - No FitChef icon source filenames include spaces or duplicate naming families
    - PR-3 uses only the approved icon source set when preparing the production App Store pack

<a id="ledger-p2-web-research-retrieval-lane"></a>
- [ ] P2: Bounded research retrieval lane for `web-research-agent`
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR-TBD-WEB-RESEARCH-RETRIEVAL-LANE
  - Area: orchestration / research / evidence intake
  - Finding Type: retrieval governance gap
  - Reason: `web-research-agent` is now part of coordinator workflows, but the project still needs one canonical bounded retrieval contract that keeps web intake evidence-driven, non-scraping-heavy, and subordinate to the research/experimentation governance already in place.
  - Links:
    - `docs/orchestration/AGENT_SKILL_ROUTING_POLICY.md`
    - `docs/orchestration/RESEARCH_TRACK_PROTOCOL.md`
    - `docs/orchestration/RESEARCH_BRAINSTORMING_PROTOCOL.md`
    - `tools/codex_skills/pulseplate-ai-reports/SKILL.md`
  - DoD:
    - Research retrieval contract defines allowed source classes, evidence logging, and anti-broad-scraping constraints
    - Coordinator/task packets can point `web-research-agent` to the bounded lane without inventing ad-hoc retrieval instructions
    - Docs distinguish internal docs maintenance (`docs`) from external evidence intake (`research`)

<a id="ledger-p2-test-hygiene-finalization"></a>
- [ ] P2: Final guard-scope expansion and residual cache/reload cleanup for the test hygiene wave
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR-TBD-TEST-HYGIENE-FINALIZATION
  - Status: 📋 Planned
  - Area: tests / policy guards / residual cleanup
  - Finding Type: finalization follow-up
  - Reason (EN): after the risk-first, client-lifecycle, and env-isolation waves land, the remaining work is to re-audit cache/reload exceptions and widen guards only where the target scope is fully clean.
  - Links:
    - `docs/audit/TEST_SUITE_REVIEW_2026-03-13.md`
    - `tests/test_repo_policy_sys_modules.py`
    - `tests/test_repo_policy_guards.py`
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-test-hygiene-wave`
  - DoD:
    - Remaining cache/reload/session-fixture exceptions are re-audited with current evidence
    - Guard scope widens only after zero offenders in the target scope
    - Umbrella test-hygiene entry closes only after the final cleanup PR passes `make verify`

<a id="ledger-p2-pr1-50-sharefile-hardening"></a>
- [ ] P2: PR 1-50 follow-up for shareFile browser hardening
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR-TBD-PR1-50-SHAREFILE-HARDENING
  - Area: frontend / export UX
  - Finding Type: deferred browser fallback hardening
  - Reason: `frontend/src/lib/shareFile.ts` still needs explicit `anchor.click()` fallback hardening and a targeted dead-code review, but that cleanup is intentionally deferred out of Wave 1 to keep the remediation PR focused on unresolved P0/P1 findings.
  - Links:
    - `frontend/src/lib/shareFile.ts`
    - `frontend/src/lib/shareFile.test.ts`
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-pr1-50-remediation-wave1`
  - DoD:
    - `anchor.click()` fallback behavior is hardened or explicitly justified with tests
    - Dead-code review for non-browser fallback paths is completed
    - Any behavior changes are covered by focused frontend tests

<a id="ledger-p2-pr1-50-glasscard-cleanup"></a>
- [ ] P2: PR 1-50 follow-up for GlassCard redundant guard cleanup
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR-TBD-PR1-50-GLASSCARD-CLEANUP
  - Area: frontend / component hygiene
  - Finding Type: deferred type-driven cleanup
  - Reason: `frontend/src/components/GlassCard.tsx` still contains redundant typed-union undefined checks that are low-risk cleanup only and therefore intentionally excluded from Wave 1 remediation scope.
  - Links:
    - `frontend/src/components/GlassCard.tsx`
    - `frontend/src/components/__tests__/GlassCard.test.tsx`
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-pr1-50-remediation-wave1`
  - DoD:
    - Redundant undefined checks are removed or justified against a concrete runtime contract
    - Component tests stay green after cleanup
    - No visual or accessibility regressions are introduced

<a id="ledger-p2-pr1-50-ollama-diagnostic-deps"></a>
- [ ] P2: PR 1-50 follow-up for ollama_diagnostic dependency handling
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR-TBD-PR1-50-OLLAMA-DIAGNOSTIC-DEPS
  - Area: scripts / diagnostics
  - Finding Type: deferred script portability
  - Reason: `ollama_diagnostic.sh` still assumes `jq` and `free` are present. The script needs explicit dependency handling or documentation, but this is intentionally deferred because it does not block Wave 1 P0/P1 remediation.
  - Links:
    - `ollama_diagnostic.sh`
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-pr1-50-remediation-wave1`
  - DoD:
    - Script checks for required external tools or documents prerequisites clearly
    - Failure mode is deterministic when dependencies are missing
    - Any documentation updates stay aligned with actual script behavior

<a id="ledger-p2-pr1-50-ollama-monitor-deps"></a>
- [ ] P2: PR 1-50 follow-up for ollama_monitor dependency handling
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR-TBD-PR1-50-OLLAMA-MONITOR-DEPS
  - Area: scripts / diagnostics
  - Finding Type: deferred script portability
  - Reason: `ollama_monitor.sh` still assumes `bc` is available. This portability/documentation cleanup remains deferred so Wave 1 stays limited to unresolved P0/P1 findings.
  - Links:
    - `ollama_monitor.sh`
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-pr1-50-remediation-wave1`
  - DoD:
    - Script checks for `bc` or documents the dependency explicitly
    - Missing-dependency behavior is deterministic and user-readable
    - Follow-up changes preserve current monitoring semantics

<a id="ledger-p2-openai-docs-freshness-pilot"></a>
- [x] P2: Govern the OpenAI external docs freshness pilot lifecycle
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR #1100 -> PR #1108
  - Status: ✅ Closed after merged PR #1100; recorded in PR #1108 (`keep narrow`; review-cycle close-out only)
  - Area: docs / orchestration / dev-agent tooling
  - Finding Type: pilot lifecycle governance
  - Reason: PR #1100 introduces an optional external-docs lane for OpenAI-first
    dev-agent work. The pilot must have explicit graduation and rollback gates
    so it does not drift into hidden repo policy or CI/runtime scope.
  - Links:
    - `docs/audit/OPENAI_EXTERNAL_DOCS_FRESHNESS_PILOT_DECISION_2026-03-10.md`
    - `docs/audit/OPENAI_EXTERNAL_DOCS_FRESHNESS_PILOT_REVIEW_CYCLE_DECISION_2026-03-11.md`
    - `docs/runbooks/OPENAI_EXTERNAL_DOCS_FRESHNESS_PILOT.md`
    - `docs/dev/CODEX_SKILLS.md`
    - `docs/memory/kpp_knowledge_promotion_pipeline.md`
    - `docs/review/PR_1100_FIXED_MAPPING.md`
    - `docs/review/PR_1108_FIXED_MAPPING.md`
  - Blockers:
    - Need one full review cycle of real OpenAI-first usage evidence
    - Need confirmation that external-docs guidance stays accurate without CI
      coupling
  - DoD:
    - A follow-up decision records keep, adjust, or stop for the pilot after one
      review cycle
    - At least one durable workflow insight is either promoted through KPP or
      explicitly marked as non-canonical
    - The runbook stays aligned with the chosen auth model for Context7 and the
      preferred invocation model for Context Hub
    - No CI/runtime/production integration is introduced under this ledger item

<a id="ledger-p2-dsar-transaction-neutral-helper"></a>
- [ ] P2: Make internal DSAR delete helper transaction-neutral
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR-TBD-DSAR-TRANSACTION-NEUTRAL-HELPER
  - Area: backend / privacy
  - Finding Type: transaction-boundary hardening
  - Reason: `delete_direct_user_artifacts()` currently owns `commit()` / `rollback()` while accepting a caller-provided SQLAlchemy `Session`. That is acceptable for the current support-led standalone helper contract, but a future support/admin workflow may batch DSAR artifact deletion with other writes on the same session. The helper should eventually declare or narrow its transaction ownership explicitly instead of implicitly committing caller-owned work.
  - Links:
    - `core/compliance/dsar_service.py`
    - `tests/test_compliance_control_plane.py`
    - `docs/compliance/DSAR_AND_DELETION_MAP.md`
  - DoD:
    - The DSAR helper either becomes transaction-neutral or moves to an explicit session/transaction ownership contract
    - Tests cover caller-owned session behavior for batched writes and rollback semantics
    - Support-led DSAR docs stay aligned with the final ownership contract

- [ ] P2 Optional: Evaluate Lenny's Podcast Transcripts for insights, marketing, and Bayesian context
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2 (optional; after P0/P1 hardening and insight/coach work stable)
  - Target PR: TBD (evaluation first: curated doc vs RAG subset vs MCP)
  - Status: 📋 Planned
  - Reason (EN): Lenny's Podcast Transcripts (269 episodes, 50+ topics) provide product/growth/PMF/leadership advice from world-class PM and growth experts. Fit: enrich insights docs, marketing-strategist playbooks, Bayesian business analyzer prior/context, FitChef RAG, and nutrition coaching design. Options: (1) curated references doc, (2) RAG subset with citation, (3) MCP or internal API. License: personal/educational; internal use with attribution is low risk. (RU: Транскрипты Lenny's Podcast — продукт/рост/PMF/лидерство; можно использовать для инсайтов, маркетинга, байесовского контекста и FitChef/коучинг.)
  - Links:
    - docs/audit/LENNYS_PODCAST_INTEGRATION_AUDIT.md (mapping to insights, Bayesian, marketing, FitChef; integration options)
    - <https://github.com/ChatPRD/lennys-podcast-transcripts>
    - core/insight/analysis_insights.md
    - core/insight/creative_scientific_innovations.md
    - .cursor/agents/marketing-strategist.md
  - DoD:
    - Decision documented: adopt one option (curated doc / RAG subset / MCP) or defer / won't do
    - If adopt: implementation steps and attribution policy documented; no scope creep into P0/P1


- [ ] P2 Optional: Evaluate scientific publication track (Bayesian, CBT, recursive algorithms)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2 (optional; credibility + PR; after core innovations shipped)
  - Target PR: N/A (decision + optional draft)
  - Status: 📋 Planned
  - Reason (EN): Optional papers: Bayesian adherence for personalized nutrition (NeurIPS/ML4H workshop), CBT-aligned gamification vs anxiety (CHI), recursive constraint satisfaction for meal planning (AAAI). Benefit: credibility, press, talent attraction. Effort: 3–6 months per paper; parallel to product. (RU: Опциональная научная публикация по байесовской персонализации, CBT-геймификации, рекурсивным алгоритмам планирования.)
  - Links:
    - docs/analysis/SCIENTIFIC_INNOVATION_ANALYSIS.md (canonical scientific review: publication track, venues)
    - docs/insights/PEER_REVIEW_ANALYSIS.md (publishable insights)
    - docs/insights/COMPREHENSIVE_PHILOSOPHY_LOGIC_MATH_CBT_ANALYSIS.md
    - docs/insights/RECURSIVE_OPTIMIZATION_STRATEGY.md
  - DoD:
    - Decision documented: pursue / defer / won't do for publication track
    - If pursue: venue + outline for one paper; no mandatory timeline


- [ ] P2: Bayesian adherence prediction and uncertainty quantification (VIP differentiator)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2 (after P0/P1 hardening; unique competitive advantage)
  - Target PR: TBD (design first: core/bayesian/adherence.py, uncertainty intervals)
  - Status: 📋 Planned
  - Reason (EN): Probabilistic personalization: P(adherence | user_context) for adaptive meal plans; confidence intervals for targets (e.g. "1800–2200 kcal, 90% confidence") instead of point estimates. Differentiator vs MyFitnessPal/Cronometer (static calculators). Prerequisites: Bayesian module design, calibration metrics (Brier score). (RU: Байесовская персонализация и доверительные интервалы для целей; уникальное конкурентное преимущество.)
  - Links:
    - docs/analysis/SCIENTIFIC_INNOVATION_ANALYSIS.md (canonical scientific review: Bayesian, uncertainty, roadmap)
    - docs/insights/COMPREHENSIVE_PHILOSOPHY_LOGIC_MATH_CBT_ANALYSIS.md (Bayesian + CBT integration)
    - docs/insights/PEER_REVIEW_ANALYSIS.md (uncertainty quantification gap)
    - core/insight/creative_scientific_innovations.md (FitChef personalization)
  - DoD:
    - Design: core/bayesian/adherence.py (or equivalent) with probabilistic adherence model
    - VIP targets expose confidence intervals where applicable (e.g. calorie range, 90% CI)
    - Calibration metric documented (e.g. Brier score); no regression on existing FREE/PRO contracts


- [ ] P2: Recursive optimization for weekly meal plans (speed + scalability)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2 (when VIP weekly plan performance is in scope)
  - Target PR: TBD (implementation after design)
  - Status: 📋 Planned
  - Reason (EN): Reduce weekly plan generation from 10–30s to 2–5s via divide-and-conquer (split week into halves, optimize recursively, merge with boundary constraints). Lazy day generation: first day instant, remaining days on-demand. Recursive nutrient aggregation O(n log n) for shoplist. (RU: Рекурсивная оптимизация недельных планов и агрегации нутриентов; скорость и масштабируемость.)
  - Links:
    - docs/analysis/SCIENTIFIC_INNOVATION_ANALYSIS.md (canonical scientific review: recursive week planning, lazy days)
    - docs/insights/RECURSIVE_OPTIMIZATION_STRATEGY.md (optimization strategies, code patterns)
    - docs/insights/PERFORMANCE_ANALYSIS_AND_NEW_INSIGHTS.md (bottlenecks: meal plan, shoplist)
    - docs/insights/PHILOSOPHICAL_SPEED_OPTIMIZATION.md (lazy evaluation, early stopping)
    - app/routers/vip.py (current weekly plan flow)
  - DoD:
    - Design: recursive week planning and/or lazy day generation documented
    - Implementation: measurable latency improvement (e.g. time-to-first-day, full week)
    - No regression on constraint satisfaction or nutrition targets


- [ ] P2: Rename legacy `vip_llm_monthly_usage` table to tier-neutral name
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR TBD
  - Status: Planned
  - Reason (EN): The monthly quota model is tier-scoped, but the persisted table name remains VIP-specific for backward compatibility and needs a dedicated migration.
  - Links:
    - `app/models/llm_quota_usage.py`
    - `app/security/llm_monthly_quota.py`
    - `docs/audit/PR_647_VIP_LLM_MONTHLY_QUOTA_AUDIT.md`
  - DoD:
    - Add DB migration from `vip_llm_monthly_usage` to a tier-neutral table name
    - Keep backward-compatible rollout/rollback notes linked from audit/docs evidence
    - Update ORM/model references and deterministic quota tests


<a id="ledger-p2-unified-aicoach"></a>
- [ ] P2: Unified Framework implementation (UnifiedAICoach: Philosophy + Math + CBT integration)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2 (integration of all components after individual implementations)
  - Target PR: PR-TBD-UNIFIED-AICOACH-PHASE5
  - Status: 📋 Planned (integration wave)
  - Dependencies:
    - [P1 Philosophical logic principles](#ledger-p1-philosophical-logic)
    - [P1 Recursive methods](#ledger-p1-recursive-methods)
    - [P1 Frontend parity for AI reliability](#ledger-p1-frontend-ai-parity)
    - [P0 Payment rails RU/BY + iOS baseline](#ledger-p0-payments-ruby-ios)
  - Reason (EN): Integrate all components (Philosophical validation, Recursive methods, Bayesian personalization, CBT coaching) into a unified production-ready framework. Hypothesized impact (pending benchmark validation): multiplicative quality gains (70-80% improvement), latency optimization (50-60% reduction), unified user experience. **Production readiness:** Framework includes rate-limiting, caching, monitoring, error handling, privacy protection, and fallback mechanisms as documented in peer review analysis. (RU: Интеграция всех компонентов (философская валидация, рекурсивные методы, байесовская персонализация, CBT coaching) в единый production-ready фреймворк. Гипотеза (с обязательной валидацией бенчмарками): мультипликативное улучшение качества (70-80%), оптимизация latency (50-60%), единый пользовательский опыт. **Production readiness:** Фреймворк включает rate limiting, caching, monitoring, error handling, privacy protection и fallback механизмы, как документировано в peer review analysis.)
  - Links:
    - docs/insights/COMPREHENSIVE_PHILOSOPHY_LOGIC_MATH_CBT_ANALYSIS.md (unified framework architecture, Phase 5 roadmap, production deployment)
    - docs/insights/PEER_REVIEW_ANALYSIS.md (production-ready architecture blueprint, implementation details, risk mitigations)
    - docs/insights/PHILOSOPHICAL_LOGIC_LLM_RELIABILITY.md (philosophical validation components)
    - docs/insights/RECURSIVE_METHODS_LLM_RAG.md (recursive methods components)
    - docs/design/NUTRITION_COACHING_DESIGN.md (CBT coaching flows)
  - Prerequisites:
    - ✅ Phase 1: Philosophical validation implemented (P1 backlog item)
    - ✅ Phase 2: Speed optimization implemented (LinguisticOptimizer, caching)
    - ✅ Phase 3: Recursive methods implemented (P1 backlog item)
    - ✅ Phase 4: CBT coaching implemented (P2 backlog item)
    - ⏳ All individual components tested and stable
  - DoD:
    - Phase 5: UnifiedAICoach class implemented (orchestrates all components)
    - All components integrated (PhilosophicalValidator, RecursiveRAG, RecursiveReasoner, Refiner, Verifier, BayesianPersonalizer, CBTCoachingFlow)
    - Production-ready features: rate-limiting, caching (GPTCache + Redis), monitoring (Prometheus), error handling, privacy protection, fallback mechanisms
    - End-to-end testing complete (all user query types: QUESTION, COMMAND, REQUEST, EXPRESSION)
    - Hypothesis target (requires benchmark validation): latency ≤0.8s (P95) for QUESTION queries, ≤0.3s for COMMAND/EXPRESSION, verification rate ≥95%, factual error rate <3%
    - Hypothesis target (requires benchmark validation): ≤$0.008 per query (VIP tier), cache hit-rate ≥50%
    - Validation evidence owner: [P1 Scientific reliability publication pipeline](#ledger-p1-scientific-reliability-pipeline)
    - Documentation: production deployment guide, monitoring setup, troubleshooting runbook
    - **Production deployment:** Framework deployed to production with feature flag (gradual rollout)


- [ ] P2: Vector retrieval for RAG (pgvector + sentence-transformers)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2 (AI / RAG)
  - Target PR: pgvector 0.5 compatibility lane; staging and ANN follow-up lanes
  - Status: Feature-gated foundation exists; compatibility and rollout evidence remain open
  - Reason (EN): Feature-gated vector retrieval with Jaccard fallback already exists. The
    pgvector 0.5 compatibility lane proves the Python binding against the pinned
    PostgreSQL extension and real RLS behavior without widening runtime scope.
  - Links:
    - `docs/audit/RAG_IMPLEMENTATION_AND_AGENT_KNOWLEDGE_AUDIT.md` (sect. 4.1, 5.1)
    - `core/rag/simple_rag.py`, W4 semantic search implementation
  - DoD:
    - ✅ Feature-flagged vector retrieval with fallback to the current Jaccard path
    - ✅ Python binding compatibility proof covers vector bind/result, cosine ordering,
      dimension rejection, and tenant RLS isolation
    - Staging extension readiness is proven before rollout
    - ANN index and query-plan compatibility are proven against representative data
    - Latency and recall are documented with current-head CI evidence
  - Security boundary: this dependency/runtime compatibility proof is not a BOLA
    closure claim; authorization remains owned by the authenticated subject and RLS
    contracts.


- [ ] P2: Wave 3 RAG v2 + safety evals + reliability game days
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR-TBD-W3-RAG-SAFETY
  - Status: Planned (Wave 3 / day 91-180)
  - Area: AI platform / security / reliability
  - Finding Type: modernization / risk reduction
  - Locations:
    - `docs/roadmap/WAVE_2_3_EXECUTION_PACK.md`
    - `docs/architecture/ADR-003-agent-control-plane-mvp.md`
  - Reason: scale AI capability with explicit safety gates and degraded-mode confidence before broad autonomy.
  - Links:
    - `docs/roadmap/WAVE_2_3_EXECUTION_PACK.md`
    - `docs/architecture/ADR-003-agent-control-plane-mvp.md`
  - DoD:
    - RAG v2 capability scope and citation/eval expectations documented
    - Safety regression gate classes documented (jailbreak/policy bypass)
    - Reliability game day scenarios and ownership defined


<a id="ledger-p2-android-keystore-conformance"></a>
- [ ] P2: Android Keystore secret storage conformance (deferred track)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2 (deferred until Android monetization activation)
  - Target PR: PR-TBD-ANDROID-KEYSTORE-CONFORMANCE
  - Status: ⏸️ Deferred
  - Reason (EN): Master checklist item #6 remains deferred because current monetization baseline is iOS-first + RU/BY manual rails; Android billing/runtime is not in active delivery scope yet.
  - Links:
    - docs/roadmap/P0_MASTER_CHECKLIST_PHASE_FIT_TRIAGE_2026-03-05.md
    - docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-mobile-secret-conformance
    - docs/roadmap/BACKLOG_LEDGER.md#ledger-p0-payments-ruby-ios
  - DoD:
    - Resume trigger is explicit: Android billing tasks (`#9/#23/#24/#32`) move from `Deferred` to `Now/Next`
    - Android app storage layer documents and enforces Keystore-only secret handling
    - Guard tests prevent insecure storage fallback on Android


- [ ] Backend TODO cleanup (i18n, telemetry)
  - Owner: @katsiaryna_kavaleuskaya
  - Target PR: TBD
  - Priority: P2
  - Area: backend
  - Finding Type: TODO/FIXME
  - Locations:
    - `core/business_bayesian_analyzer.py:145,1067` — TODO: telemetry/metrics
    - `legacy_app.py:1985` — TODO: Read version from pyproject.toml
    - `app/routers/premium_week.py:97,127` — TODO: i18n support
    - `app/routers/pro.py:152,182,529,537` — TODO: i18n, dedup, meal logging
  - Reason: Polish/improvement items, not blocking
  - Links:
    - docs/audit/PR_585_BACKLOG_SWEEP_AUDIT.md
  - DoD:
    - TODOs addressed or converted to tracked issues
    - No stale TODOs without tracking


- [ ] Deprecated endpoint cleanup (post-migration)
  - Owner: @katsiaryna_kavaleuskaya
  - Target PR: TBD (v2.0 timeline)
  - Priority: P2
  - Area: backend / API
  - Finding Type: deprecated/alias
  - Locations:
    - `app/routers/bmi_pro.py:158` — deprecated POST /api/v1/pro/bmi
    - `app/routers/bmi_pro_legacy_alias.py` — deprecated /api/v1/bmi/pro
    - `app/routers/premium_week.py:179` — deprecated /api/v1/premium/plan/week-flexible
    - `app/routers/vip.py:706` — deprecated legacy VIP endpoint
  - Reason: Legacy aliases; remove after client migration complete
  - Links:
    - docs/audit/PR_585_BACKLOG_SWEEP_AUDIT.md
    - docs/contracts/PRODUCT_TIER_MAP.md
    - docs/audit/LEGACY_APP_MIGRATION_STATUS.md (Migration status by domain)
  - DoD:
    - All clients migrated to canonical endpoints
    - Deprecated endpoints removed
    - OpenAPI updated (no deprecated paths)


- [ ] P2: Product decision for removed/non-canonical optional fields in skip tests
  - Owner: @katsiaryna_kavaleuskaya
  - Target PR: PR-749 (ui_labels contract), PR-733 (remaining fields)
  - Status: 🟡 In progress (PR-749)
  - Priority: P2
  - Area: backend / product contract
  - Finding Type: intentional-scope decision
  - Locations:
    - `tests/test_app_coverage_unit_combined.py:83`
    - `tests/test_app_coverage_unit_combined.py:88`
    - `tests/test_premium_targets_es_snapshots.py:453`
  - Reason: `ui_labels` contract is being promoted to required in PR-749; `interpret_group` / `estimate_level` still need explicit product-contract decisions.
  - Links:
    - `docs/audit/SKIPPED_TESTS_CLASSIFICATION_AUDIT_2026-02-13.md`
    - `app/schemas/premium_contracts.py:109`
  - DoD:
    - Product decision recorded for each field/function (restore canonical equivalent vs remove obsolete tests)
    - No ambiguous intentional skips remain without decision record


<a id="ledger-p2-rag-feedback-pii-minimization"></a>
- [ ] P2: Reassess feedback and RAG preview minimization beyond regex redaction
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR-TBD-RAG-FEEDBACK-PII-MINIMIZATION
  - Area: backend / privacy / RAG
  - Finding Type: privacy hardening follow-up
  - Reason: Regex-based redaction exists, but feedback storage and RAG source previews still rely on best-effort masking. A focused review should decide whether previews/queries need stronger minimization or retention tightening.
  - Links:
    - `app/routers/feedback.py`
    - `core/pii_redaction.py`
    - `core/rag/simple_rag.py`
    - `tests/test_feedback_api.py`
    - `tests/test_cbt_insight_api.py`
  - DoD:
    - Sensitive feedback fields and RAG previews are classified by retention/need-to-store level
    - Any fields not required for product analytics are minimized or removed
    - Tests cover the chosen minimization/redaction contract
    - Security posture doc reflects the final storage policy


- [ ] Algorithmic brand textures (seeded): generate onboarding/ASO backgrounds with reproducible seeds
  - Owner: @katsiaryna_kavaleuskaya
  - Target PR: TBD
  - Priority: P2
  - Area: design / marketing assets
  - Finding Type: tooling
  - Reason: Branded generative textures can speed up “polished but minimal” visuals for onboarding, empty states,
    and ASO packs, while staying reproducible via seeded parameters.
  - Links:
    - `docs/orchestration/IOS_FRONTEND_MULTIAGENT_PLAYBOOK.md` (how to add new specialist agents)
  - DoD:
    - A single seeded generator exists (deterministic for the same seed) with exportable PNG outputs
    - Output palette matches brand tokens and supports light/dark variants
    - Usage notes: never encode text in images; keep wellness-safe tone


- [ ] Figma slice structure absent in current Make file
  - Owner: @katsiaryna_kavaleuskaya (Design + FE + iOS)
  - Target PR: PR1/Follow-up
  - Priority: P2
  - Status: ▶️ In progress (Unblocked: Figma seat `Full`, 2026-02-17)
  - Area: design / ios / frontend
  - Finding Type: deferred execution
  - Reason: PR_781 defines the blueprint and keeps docs scope; execution
    continues as a follow-up work package in Figma file
    `<FIGMA_MAKE_FILE_ID>`.
  - Links:
    - `docs/audit/PR_781_HOME_PLATE_PROGRESS_AUDIT_RUNBOOK_2026-02-17.md`
    - `https://www.figma.com/make/<FIGMA_MAKE_FILE_ID>/Untitled`
  - DoD:
    - Pages created: `00_Foundation_Tokens`, `01_Components`,
      `10_iOS_Home`, `11_iOS_Plate`, `12_iOS_Progress`,
      `20_Web_Parity`
    - Component set created in `01_Components` per audit runbook
    - Naming convention `PP/<Platform>/<Screen>/<Component>/<State>`
      applied consistently
    - Follow-up implementation PR merged with evidence
      (screenshots/links) and this ledger item closed


- [ ] Agent Context Cache (avoid re-loading AGENTS.md)
  - Owner: @katsiaryna_kavaleuskaya
  - Target PR: TBD
  - Priority: P2
  - Area: dev-process / orchestration
  - Finding Type: productivity
  - Reason: Coordinator repeatedly re-loads the same canonical context files (root/module `AGENTS.md`, runbook, orchestration docs).
  - Links:
    - docs/orchestration/AGENT_CONTEXT_MAP.md
    - docs/orchestration/workflow.md
  - DoD:
    - Coordinator has an explicit caching strategy (doc or lightweight tool) for stable context inputs
    - Cache invalidation rules documented (file change / branch change)


- [ ] Orchestration Telemetry (metrics)
  - Owner: @katsiaryna_kavaleuskaya
  - Target PR: TBD
  - Priority: P2
  - Area: dev-process / orchestration
  - Finding Type: observability
  - Reason: We have no visibility into orchestration performance (agents used, iterations, sync points, end-to-end time).
  - Links:
    - docs/orchestration/PARALLEL_WORK_PROTOCOL.md
    - docs/orchestration/AGENT_DIALOGUE_TEMPLATE.md
  - DoD:
    - Minimal telemetry spec defined (what metrics, where recorded, retention)
    - Metrics collection does not affect runtime product behavior


- [ ] P2: Orchestration — agent clusters (scaling for 40+ agents)
  - Owner: @katsiaryna_kavaleuskaya
  - Target PR: TBD (future)
  - Priority: P2
  - Area: dev-process / orchestration
  - Finding Type: scalability
  - Reason: 26 agents; coordinator routes to each. At scale (40+ agents) routing becomes unwieldy. Cluster-first routing (backend, frontend, ml, research, security) scales better.
  - Links:
    - `docs/orchestration/AGENT_CAPABILITY_MATRIX.md`
    - `docs/plan/ORCHESTRATION_IMPROVEMENTS_PLAN_2026.md`
  - DoD:
    - Cluster definitions documented
    - Routing logic updated or documented for future adoption


- [ ] P2: Canary / disclaimer for published agent evals
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR-TBD (if we publish)
  - Status: Planned
  - Area: docs / compliance
  - Finding Type: process
  - Reason: If we ever publish agent prompts or evaluation snippets, add canary or disclaimer per EVMbench ("Internal evaluation artifact; do not use for training").
  - Links:
    - `docs/audit/EVMBENCH_INSPIRED_AGENT_EVALUATION_BRAINSTORM_2026-02-21.md`
  - DoD:
    - Policy or template added; apply only when publishing evals


- [ ] Standardize audit verification blocks (require minimal stdout excerpt)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR-637
  - Status: 🟡 In progress (PR-637)
  - Reason: Audit items labeled “Verified” must include minimal observed stdout evidence (1–3 lines) to remain reproducible and reviewable.
  - Links:
    - docs/audit/PR_Q2B_IOS_UITESTS_BUNDLE_LOAD_AUDIT.md (section F)
    - AGENTS.md (Verification-audit rule)
  - DoD:
    - Add a short, canonical checklist line for audit PRs: include 1–3 raw stdout lines + exit code for each key verification command
    - No scope creep into runbook-level detail


- [ ] P2 Optional: Use curated repos (Frontend/UI, AI/LLM, RAG, Multimodal, MCP, ML/CV) as learning and reference
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2 (optional; when implementing RAG upgrade, multimodal pipeline, or frontend components)
  - Target PR: N/A (reference only; adopt patterns/libraries via normal PR)
  - Status: 📋 Planned
  - Reason (EN): Curated set (22 repos): Flexbox Froggy, shadcn/ui, 50projects50days, Awesome React/CSS; LLaVA, CLIP, Transformers, Awesome Multimodal ML, RAG from Scratch, Awesome LLM Apps, LLM Engineer Handbook; MCP Python SDK; Awesome ML/CV, ZenML; Qwen/Qwen-Finetuning; Spinning Up, Sutton&Barto RL; PyTorch, Awesome Generative AI. Map to our vision: RAG (RAG from Scratch, Awesome LLM Apps), multimodal/FitChef (LLaVA, CLIP, Transformers), frontend (shadcn, Awesome React), MCP (python-sdk), CV (Awesome CV, PyTorch). (RU: Закладки для RAG, multimodal, фронта, MCP, ML/CV; использовать при реализации фич.)
  - Links:
    - docs/insights/CURATED_REPOS_REFERENCE.md (full mapping to LLM_RAG, CV_ML, creative_scientific_innovations, RECURSIVE_METHODS, COMPREHENSIVE)
    - core/insight/creative_scientific_innovations.md (Curated repos reference subsection)
  - DoD:
    - When designing RAG upgrade, multimodal pipeline, or UI: consult CURATED_REPOS_REFERENCE.md for relevant repos
    - No mandatory code dependency; adopt via normal PR/backlog


- [ ] Web Guards: Extract config constants to shared module
  - Owner: @katsiaryna_kavaleuskaya
  - Target PR: TBD
  - Priority: P2
  - Area: frontend / guards
  - Finding Type: improvement (Sourcery PR-592)
  - Location: `frontend/src/api/__tests__/thin-client-guards.test.ts`
  - Reason: FORBIDDEN_PATTERNS/SCAN_DIRS/EXCLUDE_PATTERNS should be shared between guards and AGENTS.md to prevent policy drift
  - Links:
    - <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/592> (source PR)
    - Sourcery comment on PR-592
  - DoD:
    - Config extracted to shared module
    - Guards import config
    - AGENTS.md references canonical source


- [ ] Web Guards: Improve inline block comment parsing
  - Owner: @katsiaryna_kavaleuskaya
  - Target PR: TBD
  - Priority: P2
  - Area: frontend / guards
  - Finding Type: improvement (Sourcery PR-592)
  - Location: `frontend/src/api/__tests__/thin-client-guards.test.ts`
  - Reason: Current `isLineInComment` may not handle inline `/* ... */` on same line correctly
  - Links:
    - <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/592> (source PR)
    - Sourcery comment on PR-592
  - DoD:
    - Stricter inline comment parsing
    - Test cases for edge cases


- [ ] P2: Stabilize nosec allowlist keys (path + token/hash, not line)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR-TBD
  - Area: guards / tech-debt
  - Finding Type: robustness
  - Reason: Line-based allowlist entries drift on any file edit; allowlist should key by path + code-fragment hash or token so refactors do not require allowlist updates.
  - Links: `tests/guards/fixtures/nosec_policy_allowlist.txt`, `tests/guards/test_nosec_policy_guard.py`
  - DoD: Allowlist format supports path + stable identifier (hash/snippet); guard matches by identifier; line number optional or derived.


- [ ] P2: Subprocess guard — multiline and indirection-aware (AST-based) detection
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR-TBD
  - Area: guards / security policy
  - Finding Type: optional improvement (Cubic suggestion)
  - Reason: Current guard scans single-line subprocess calls; multiline invocations (e.g. `subprocess.run([\n  "gh", ...])`) and simple indirection (e.g. `cmd = [...]` then `subprocess.run(cmd)`) may escape detection. Extend to multiline or AST-based scan.
  - Links:
    - `tests/guards/test_subprocess_uses_absolute_binaries.py`
    - `AGENTS.md` (subprocess absolute path policy)
  - DoD:
    - Guard detects banned binaries when call spans multiple lines, or document limitation
    - Guard catches simple indirection (e.g. cmd = [...] then subprocess.run(cmd)); AST-based scan preferred
    - Success criterion: no new failures on current main; no false negatives on existing codebase


<a id="ledger-p2-detect-secrets-allowlist-followup-pr1406"></a>
- [ ] P2: Detect-secrets allowlist follow-up after PR #1406 baseline rebuild
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR-TBD
  - Area: tooling / security hygiene / maintainability
  - Finding Type: deferred follow-up (CodeRabbit PR #1406)
  - Reason: PR #1406 is an emergency baseline-rebuild hotfix to unblock `lint` on `main`. Source-level allowlisting for intentional placeholders and test fixtures is valid follow-up work, but it would widen scope across multiple files and is not required to restore current detect-secrets parity.
  - Links:
    - `docs/review/PR_1406_FIXED_MAPPING.md`
    - `.secrets.baseline`
    - `.env.example`
    - `frontend/public/mockServiceWorker.js`
    - `tests/`
  - DoD:
    - Identify recurring intentional placeholders/test fixtures that can use the repo-approved allowlist marker or equivalent exclusion
    - Regenerate `.secrets.baseline` after source tagging so intentional entries are removed where supported
    - `pre-commit run detect-secrets --all-files` stays green
    - Future baseline diffs for the same fixtures are materially smaller and easier to review


- [ ] P2: Frontend and iOS explainer surfaces on current journey pages
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2 (rendering follow-up)
  - Target PR: PR-TBD-EXPLAINER-SURFACES
  - Status: 📋 Planned
  - Reason (EN): After the backend contract exists, explainers should be rendered on existing BMI, PRO interpretation, progress, and weekly-plan surfaces. Delivery must remain thin-client on web and iOS. (RU: После contract phase explainers нужно отрисовать на текущих user journey surfaces без дублирования бизнес-логики на клиентах.)
  - Links:
    - `docs/product/WELLNESS_EXPLAINERS_TENSORTONIC_ADAPTATION_NOTE.md`
    - `frontend/`
    - `ios/`
    - `docs/product/FREE_PRO_CONTRACT.md`
  - DoD:
    - Surface map is defined for web and iOS on current FREE / PRO / VIP pages
    - Rendering remains presentation-only; business logic stays on backend
    - Copy stays wellness-safe and aligned with the trust-based funnel


- [ ] Auto-generate architecture diagrams (Mermaid baseline + optional Graphviz import graph)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2 (docs/tooling)
  - Target PR: PR-630 (docs-only) or follow-up docs PR
  - Status: ✅ Baseline Mermaid added; automation optional
  - Reason: Architecture is enforced by guards, but reviewers/onboarding benefit from quick visuals. Automation reduces doc drift.
  - Evidence:
    - `docs/architecture/system_overview.md` (Mermaid system overview)
    - `docs/architecture/backend_routing_map.md` (evidence-driven routing map)
    - `docs/audit/PR_630_ARCHITECTURE_EVIDENCE_PACK_AUDIT.md` (evidence pack)
  - Risk:
    - Without maintenance/automation, diagrams drift and become misleading.
  - Exit criteria:
    - Diagram updates happen in the same PR as entrypoint/router/flag changes (enforced culturally or via light guard)
  - DoD:
    - Keep Mermaid as canonical diagram (single source of truth)
    - Optional: add a script that emits a filtered import graph (`.dot`/`.svg`) for selected slices (app/core/providers) with stable filtering rules


- [x] Constrain compat shim: `sys.modules["app_module"]` mapping in `app/__init__.py`
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2 (maintainability)
  - Target PR: [PR #2304](https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2304) (`codex/retire-legacy-scheduler-app-module-compat`)
  - Status: ✅ Completed. PR #2304 merged on 2026-08-20T21:26:06Z with merge
    commit `9ce04bc9d54f3b0e8f5fd23bd34fad7654677e70`; this docs-only PR
    reconciles the required ledger closeout.
  - Reason: The implicit module-table alias and legacy synchronous scheduler
    resolver rail create patch-order ambiguity after canonical app and lifespan
    ownership have already landed. This lane removes those compatibility paths
    instead of documenting or extending them.
  - Evidence:
    - PR #2304 merged on 2026-08-20T21:26:06Z with merge commit
      `9ce04bc9d54f3b0e8f5fd23bd34fad7654677e70`.
    - `app/__init__.py:57-68` (finite facade resolves canonical `app.main.app`)
    - `tests/test_application_instance_ownership.py:92-144` (fresh-process retirement contract)
  - Risk:
    - Hard-to-debug patch behavior, hidden aliasing, accidental reliance by new code/tests.
  - Blocked-by:
    - None (small focused PR), but recommended after PR-628/629 to keep scopes clean
  - Exit criteria:
    - `import app_module` fails in a fresh process and `app.app` remains the
      exact canonical `app.main.app`
    - Legacy synchronous scheduler wrappers and `app.scheduler_helpers` are absent
  - DoD:
    - Fresh-process import-order tests preserve app, route, middleware, lifespan,
      scheduler-access, and OpenAPI identity
    - The local narrow bundle and canonical current-head CI pass before merge
    - This docs-only closeout records the merged state without changing runtime behavior


- [ ] P2 Optional: Evaluate NVIDIA PersonaPlex for voice persona layer (assistant / coach)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2 (optional; depends on voice UX roadmap)
  - Target PR: TBD (evaluation first, then integration if approved)
  - Status: 📋 Planned
  - Reason (EN): PersonaPlex (open-source, NVIDIA) provides full-duplex speech-to-speech, persona switching, and backchannel for a "live" conversational feel. Fit: personalize AI assistant and nutrition coach by style (e.g. strict teacher, friendly consultant); optional voice mode. Current stack is text-only; PersonaPlex would be additive (voice layer). Prerequisites: NVIDIA GPU or hosted API, NVIDIA Open Model License, WebSocket/streaming for real-time audio. (RU: PersonaPlex (NVIDIA, open-source) — full-duplex S2S, переключение персон, поддакивания; можно использовать для персонализированного ассистента и коуча. Сейчас у нас только текст; голос — опционально.)
  - Links:
    - docs/audit/PERSONAPLEX_INTEGRATION_AUDIT.md (integration options, prerequisites, risks)
    - <https://huggingface.co/nvidia/personaplex-7b-v1>
    - <https://github.com/NVIDIA/personaplex>
    - docs/design/NUTRITION_COACHING_DESIGN.md (coach flows)
    - core/insight/creative_scientific_innovations.md (FitChef)
  - Prerequisites:
    - Voice UX / real-time audio on product roadmap (or explicit decision to prototype)
    - Inference option: GPU (A100/H100) or hosted API; license accepted
  - DoD:
    - Decision documented: adopt / defer / won't do for PersonaPlex voice layer
    - If adopt: persona prompts aligned with FitChef/coach; voice API (e.g. WebSocket) and security/privacy documented


- [x] P1: Fix invalid Dependabot assignee configuration warning
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (repo governance / automation hygiene)
  - Target PR: commit `e34a357f2`
  - Status: ✅ Completed
  - Reason (EN): `.github/dependabot.yml` previously declared assignee `katsiarynakavaleuskaya`, and Dependabot PRs such as `#1471` emitted a bot warning because GitHub could not add that assignee. Commit `e34a357f2` removed the invalid configuration, and fresh Dependabot PR `#2168` confirmed that the warning no longer appears. (RU: Ранее `.github/dependabot.yml` указывал недопустимого `assignee`, из-за чего Dependabot публиковал предупреждение. Коммит `e34a357f2` удалил настройку, а свежий PR `#2168` подтвердил отсутствие предупреждения.)
  - Links:
    - `.github/dependabot.yml`
    - `docs/review/PR_1471_FIXED_MAPPING.md`
    - `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1471#issuecomment-4275076194`
    - `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2168`
  - Evidence:
    - commit `e34a357f2` removed the invalid Dependabot assignee configuration
    - fresh Dependabot PR `#2168` was created without the invalid-assignee warning
  - DoD:
    - `.github/dependabot.yml` updated so Dependabot stops emitting the invalid-assignee warning
    - at least one fresh Dependabot PR lands without the warning comment

- [ ] P2 Optional: Evaluate PEP 751 standard lock file (pylock.toml) and/or uv + Dependabot
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2 (optional tooling improvement)
  - Target PR: TBD (evaluation first, then migration if beneficial)
  - Status: 📋 Planned
  - Reason (EN): Python ecosystem 2026: PEP 751 defines standard lock format (pylock.toml); Dependabot now supports uv. Current repo uses pip-tools (requirements.txt as lock) and pip in Dependabot — no mandatory change. Optional: evaluate migrating to standard lock file and/or uv when tooling/CI support is stable. Setuptools: we use it only as pinned dependency (security); no setup.cfg — setuptools 78.x deprecations do not affect us. (RU: Экосистема Python 2026: PEP 751 — стандартный lock-файл; Dependabot поддерживает uv. Сейчас: pip-tools + requirements.txt как lock, Dependabot на pip. Опционально: оценить переход на pylock.toml и/или uv. Setuptools: только как зависимость в requirements; setup.cfg нет — депрекации 78.x нас не затрагивают.)
  - Links:
    - docs/audit/PYTHON_SETUPTOOLS_LOCKFILE_AUDIT.md (full audit: setuptools usage, lock file strategy, Dependabot/uv)
    - REQUIREMENTS.md (current pip-compile workflow)
    - .github/dependabot.yml (pip ecosystem)
  - DoD:
    - Decision documented: adopt / defer / won't do for PEP 751 and for uv
    - If adopt: migration PR with updated REQUIREMENTS.md and CI; Dependabot config updated if uv adopted


- [ ] P2 Optional: Use Loot Drop (Startup Graveyard) as periodic anti-pattern checklist
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2 (optional; before major bets or post-launch reviews)
  - Target PR: N/A (process: run checklist, update audit if new risks)
  - Status: 📋 Planned
  - Reason (EN): Loot Drop (loot-drop.io) catalogs 925+ failed VC-backed startups with structured failure analysis (product, competition, pricing, lost focus, marketing, cash, legal/regulatory, etc.). Health/BioTech failures are 94% legal/regulatory. Use as anti-pattern checklist to avoid repeating epic fails: e.g. LLM cost burn, scope creep, wellness vs medical positioning. (RU: «Кладбище стартапов» — уроки провалов; чеклист по 10 категориям и revival themes для снижения рисков.)
  - Links:
    - docs/audit/LOOT_DROP_STARTUP_GRAVEYARD_AUDIT.md (risk matrix, PulsePlate mapping, recommendations)
    - <https://www.loot-drop.io/>
    - <https://www.loot-drop.io/insights.html>
    - core/insight/analysis_insights.md (Lessons from failed startups subsection)
  - DoD:
    - Before major product/GTM bets or post-launch review: run through Loot Drop 10 categories + revival themes
    - Update LOOT_DROP_STARTUP_GRAVEYARD_AUDIT.md if new risks or mitigations identified


- [ ] P2 Vision: Future — social network for nutrition/weight/support
  - Owner: @katsiaryna_kavaleuskaya
  - Target PR: N/A (separate product/project in perspective)
  - Priority: P2 (long-term vision)
  - Reason (EN): Possible separate product: community around nutrition, weight goals, mutual support. Not in current PulsePlate scope; considered as prospect after strengthening coaching and core app. (RU: Возможный отдельный продукт: комьюнити вокруг питания, целей по весу, взаимоподдержка. Не входит в текущий scope PulsePlate; рассматривается как перспектива после укрепления коучинга и ядра приложения.)
  - Links:
    - docs/design/NUTRITION_COACHING_DESIGN.md (Future social network — links section)
    - BACKLOG_LEDGER (Nutrition coaching — natural predecessor)
  - DoD:
    - Decision "do / don't do" and product boundaries (separate app vs section in PulsePlate) — after coaching launch


- [ ] P2 Vision: Nutrition coaching (CBT in nutrition, weight loss/gain)
  - Owner: @katsiaryna_kavaleuskaya
  - Target PR: TBD (product/feature design first)
  - Priority: P2 (product direction; preferred over ML training platform for current scope)
  - Reason (EN): Product differentiation via cognitive-behavioral psychology in nutrition: goals, reflection, habits, support for slips/weight gain. Does not require ML training platform; leverages LLM/RAG and existing user data. **Integration with philosophy and math:** CBT coaching flows can be validated through philosophical principles (syllogisms, verification) and enhanced with Bayesian predictions for proactive intervention. (RU: цели, рефлексия, привычки, поддержка при срывах/наборе веса. Не требует платформы для обучения моделей; опирается на LLM/RAG и существующие данные пользователя. **Интеграция с философией и математикой:** CBT coaching flows могут быть валидированы через философские принципы (силлогизмы, верификация) и улучшены байесовскими предсказаниями для проактивного вмешательства.)
  - Links:
    - docs/insights/COMPREHENSIVE_PHILOSOPHY_LOGIC_MATH_CBT_ANALYSIS.md (unified analysis: CBT + philosophy + Bayesian integration, structured coaching flows)
    - docs/design/NUTRITION_COACHING_DESIGN.md (component links, implementation approach)
    - core/insight/creative_scientific_innovations.md (FitChef, AI companion)
    - docs/analysis/LLM_RAG_AI_ASSISTANT_ANALYSIS.md (insight, RAG)
  - DoD:
    - Product spec: coaching scenarios (goals, weekly reflections, behavioral steps) — EN: structured scenarios (goal-setting dialogues, weekly reflections, slip analysis)
    - Component links documented in design doc (see NUTRITION_COACHING_DESIGN.md)
    - Implementation — separate PRs after backend/VIP stabilization


- [ ] P2: Complete legacy_app.py migration (delete legacy endpoints)
  - Owner: @katsiaryna_kavaleuskaya
  - Target PR: PR #2102 -> PR #2114 -> PR #2121 -> PR #2140 -> PR #2145 -> PR #2163 (`codex/canonicalize-pro-targets-gaps-ownership`) -> PR #2170 (`codex/canonicalize-pro-plate-ownership-replacement`) -> PR #2180 (`codex/canonicalize-premium-bmr-ownership`) -> PR #2209 (`codex/legacy-insight-schema-adapter-extraction`) -> `codex/legacy-insight-ownership-cutover` -> PR #2294 (`codex/canonical-fastapi-ownership-replacement`) -> [PR #2304](https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2304) (`codex/retire-legacy-scheduler-app-module-compat`, merged compatibility retirement) -> PR-TBD-PAID-BMI-MIRROR-RETIREMENT -> PR-TBD-BMI-PRO-RETIREMENT -> PR-TBD-LEGACY-EXPORT-RETIREMENT -> PR-TBD-LEGACY-DELETION
  - Priority: P2 (long-term cleanup)
  - Status: In progress. Route, middleware, lifespan, app-client API-key dependency,
    application metadata, OpenAPI policy, and admin scheduler-access ownership are
    canonical. PR #2170 merged at `8b30b82f47c818dec5eb8aec5824e4627fc5d084`,
    completing direct-core Plate ownership. PR #2209 merged at
    `b611682cf4d09eac8b4a124aff07e91c57f83f59`, establishing canonical Insight
    schema, adapter, and application-service ownership. PR #2294 merged canonical
    FastAPI construction ownership. PR #2304 merged at
    `9ce04bc9d54f3b0e8f5fd23bd34fad7654677e70`, removing the `app_module` alias
    and legacy synchronous scheduler resolver rail without changing canonical
    lifespan or scheduler behavior. The next bounded successor retires retained
    paid/BMI registration mirrors. BMI/PRO/VIP HTTP alias retirement, remaining
    legacy export retirement, and final `legacy_app.py` deletion stay separate
    later lanes.
  - Reason: After all critical security fixes and endpoint migrations complete, eventually delete `legacy_app.py` entirely. Legacy business and route logic should move to its canonical owners: modular routers (`app/routers/*`), services (`app/services/*`), bootstrap modules (`app/bootstrap/*`), or core modules (`core/*`) according to responsibility. The current train has extracted lifecycle ownership and now cuts canonical `app/*` dependencies on legacy compatibility symbols before app-factory/OpenAPI ownership inversion and final facade removal.
  - Links:
    - docs/audit/LEGACY_APP_MIGRATION_STATUS.md (overall progress, migration status)
    - docs/pr/PR_THIN_PROXY_CLEANUP_PLAN.md
    - app/routers/api_key.py
    - app/services/scheduler_access.py
    - app/services/legacy_premium_weekly_plan.py
    - app/services/pro_nutrition_targets.py
    - app/services/pro_nutrition_plate.py
    - app/services/pro_nutrition_bmr.py
    - app/schemas/premium_contracts.py
    - core/nutrition_utils.py
    - docs/architecture/LEGACY_COMPATIBILITY_SEAM.md
  - Prerequisites:
    - ✅ All P0 security fixes complete (rate-limiting, tier guards)
    - ✅ All P1 migrations complete (constants extracted, WebSocket secured)
    - ✅ All clients migrated to canonical endpoints
    - ✅ Legacy endpoint traffic < 1%
  - DoD:
    - All endpoints migrated to modular routers
    - All helpers moved to canonical modules
    - `legacy_app.py` deleted (or reduced to minimal compatibility shim)
    - Tests pass (no functionality broken)
    - OpenAPI unchanged (all canonical endpoints present)


<a id="ledger-p1-background-scheduler-multi-worker-ownership"></a>
- [x] P1: Isolate background food-update scheduling before multi-worker deployment
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (runtime correctness / operations)
  - Target PR: S1 `codex/background-scheduler-ownership`
  - Status: Implemented in the S1 lane; merge and operator rollout remain required
  - Reason: Production/staging API lifespans no longer own the periodic loop.
    Canonical Compose deploys one dedicated no-ingress worker, while scheduled,
    one-shot, and admin force-update attempts share one PostgreSQL advisory
    lease boundary.
  - Links:
    - `app/bootstrap/lifespan.py`
    - `core/food_apis/scheduler.py`
    - `core/food_apis/scheduler_runtime.py`
    - `docs/runbooks/CRON.md`
  - DoD:
    - deployment owns automatic updates in one dedicated scheduler worker
    - cooperating PostgreSQL paths use one stable attempt-scoped advisory lease
    - failure/recovery, contention, and guarantee limits are documented and tested
    - API worker count can increase without multiplying periodic update loops


- [ ] P2: Cross-feature integration tests (BMI → Sports → Shoplist flows)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2 (quality assurance; prevent regressions)
  - Target PR: TBD (tests only)
  - Status: 📋 Planned
  - Reason (EN): Unit tests exist; integration tests across feature boundaries are weak. Add end-to-end flows: BMI → sport nutrition → shoplist; recipe synthesis → regional catalog → shoplist. Aligns with CROSS_FEATURE_SYNERGIES and PEER_REVIEW_ANALYSIS gap. (RU: Интеграционные тесты кросс-фичевых сценариев.)
  - Links:
    - docs/analysis/SCIENTIFIC_INNOVATION_ANALYSIS.md (canonical scientific review: cross-feature flows)
    - docs/insights/CROSS_FEATURE_SYNERGIES.md (synergy matrix, flows)
    - docs/insights/PEER_REVIEW_ANALYSIS.md (cross-feature testing gap)
    - tests/ (existing unit/integration structure)
  - DoD:
    - At least one cross-feature flow tested (e.g. BMI → sport targets → plan → shoplist)
    - Tests run in CI; no new flakiness; documented in tests/AGENTS.md or RUNBOOK


- [ ] P2: Cross-feature synergies implementation (real-time + automation + community)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2 (strategic integration)
  - Target PR: TBD (multiple PRs for different synergies)
  - Status: 📋 Planned
  - Reason: 12 new synergies identified between planned features (WebSocket + Coaching, CV + Restaurant, Bayesian + WebSocket, etc.). These create unified user experiences and competitive advantages. Implementation should follow recommended order: real-time foundation → coaching enhancement → automation pipeline → community features.
  - Links:
    - docs/insights/CROSS_FEATURE_SYNERGIES.md (synergy matrix, implementation order, expected impact)
    - docs/design/NUTRITION_COACHING_DESIGN.md
    - docs/design/RESTAURANT_INTEGRATION_SPEC.md
    - docs/audit/WEBSOCKET_ANALYSIS.md
  - Prerequisites:
    - ✅ WebSocket implemented (P1)
    - ✅ Nutrition coaching implemented (P2)
    - ✅ Restaurant integration implemented (P2)
    - ✅ CV food recognition implemented (P1)
  - DoD:
    - Real-time foundation complete (WebSocket + Bayesian + Gamification)
    - Coaching enhancement complete (WebSocket + RAG + Causal Inference)
    - Automation pipeline complete (CV + Restaurant + Multi-Modal)
    - Community features complete (Social Network + Gamification + Restaurant)
    - End-to-end user journeys documented and tested


- [ ] P2: Execution Wave 3-R4 — Export adapter + deterministic contract tests
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR #TBD-W3-R4-EXPORT-TESTS (`feat/restaurants-w3-r4-observability-rollback`)
  - Status: 🟡 In progress
  - Reason: Guarantee stable mapping from weekly plan artifacts to partner payloads.
  - Links:
    - docs/design/RESTAURANT_INTEGRATION_SPEC.md
    - docs/architecture/ADR_RESTAURANT_PARTNER_CONTRACT_SEAM_2026-03-03.md
    - app/routers/plan_export.py
    - tests/test_pro_restaurant_partner_api.py
  - DoD:
    - Mapping rules from weekly plan/recipes/constraints to partner payload documented
    - Deterministic contract tests defined and passing
    - Rollback-safe rollout notes captured in audit artifact

---


- [ ] P2: Explainer progress telemetry and experimentation package
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2 (measurement follow-up)
  - Target PR: PR-TBD-EXPLAINER-TELEMETRY
  - Status: 📋 Planned
  - Reason (EN): Explainers and learning cycles need completion and unlock telemetry so the product can measure trust, retention, and progression. This should reuse existing progress/live-indicator patterns instead of creating a parallel growth system. (RU: Для explainers и learning cycles нужна телеметрия completion/unlock, но она должна переиспользовать текущие progress patterns и оставаться privacy-safe.)
  - Links:
    - `docs/product/WELLNESS_EXPLAINERS_TENSORTONIC_ADAPTATION_NOTE.md`
    - `frontend/src/features/progress/`
    - `docs/roadmap/BACKLOG_LEDGER.md`
  - DoD:
    - Canonical `explainer_progress_event` fields are documented
    - Telemetry design is low-cardinality and privacy-safe
    - Experimentation scope is additive and does not introduce a new gamification system in MVP


- [ ] P2: Optional interactive simulator micro-surfaces for wellness understanding
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2 (optional product clarity)
  - Target PR: PR-TBD-WELLNESS-SIMULATOR-MICRO-SURFACES
  - Status: 📋 Planned
  - Reason (EN): TensorTonic's strongest reusable learning mechanic is the combination of explanation, scenario, pitfalls, and interactive simulation. PulsePlate can selectively adapt this for wellness-safe cases such as adherence confidence stability or interpretation confidence with more data, but only as deterministic micro-surfaces grounded in current product logic. (RU: Самая полезная механика для адаптации — explanation + scenario + pitfalls + simulator; у нас это допустимо только для wellness-safe и rules-first micro-surfaces.)
  - Links:
    - `docs/product/WELLNESS_EXPLAINERS_TENSORTONIC_ADAPTATION_NOTE.md`
    - `docs/product/FREE_PRO_CONTRACT.md`
    - `docs/insights/PERFORMANCE_ANALYSIS_AND_NEW_INSIGHTS.md`
    - `core/`
  - DoD:
    - Candidate simulator cases are documented and validated as wellness-safe
    - Simulator logic is deterministic and local to existing product rules
    - No new heavy LLM endpoint or public gamification mechanics are introduced


- [ ] P2: Rules-first learning-cycle engine and unlock semantics
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2 (product behavior foundation)
  - Target PR: PR-TBD-LEARNING-CYCLE-ENGINE
  - Status: 📋 Planned
  - Reason (EN): PulsePlate needs deterministic unlock rules based on current BMI, interpretation, adherence, and weekly-plan signals. The cycle model must reward understanding and adjustment, not streak preservation or social pressure. (RU: Нужны детерминированные unlock rules для learning cycles без streak-shame и без social ranking.)
  - Links:
    - `docs/product/WELLNESS_EXPLAINERS_TENSORTONIC_ADAPTATION_NOTE.md`
    - `docs/product/FREE_PRO_CONTRACT.md`
    - `core/`
    - `app/routers/pro.py`
    - `app/routers/vip.py`
  - DoD:
    - Canonical `learning_cycle_state` fields are documented
    - Unlock rules use existing backend signals only
    - Design explicitly bans public leaderboards, addictive streak loops, and ranking mechanics in MVP


- [ ] P2: Stage-4 query-aware contradiction detection alignment
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2 (quality improvement)
  - Target PR: PR-TBD-RAG-STAGE4-QUERY-AWARE
  - Status: 📋 Planned
  - Reason: Contradiction checks in Stage-4 should explicitly incorporate active user query semantics to reduce context-irrelevant flags and improve reliability scoring fidelity.
  - Links:
    - `docs/insights/PHILOSOPHICAL_LOGIC_LLM_RELIABILITY.md`
    - `docs/contracts/RAG_CONTRACT.md`
    - `core/rag/philosophy_pipeline.py`
    - `core/rag/validation.py`
    - `tests/test_philosophy_validation_integration.py`
  - DoD:
    - Stage-4 contradiction detection consumes query-aware context deterministically
    - Validation tests cover relevant/irrelevant contradiction scenarios
    - Reliability fields (`verification_state`, `confidence`) remain backward-compatible


<a id="ledger-p2-rag-stage4-anchor-specificity"></a>
- [ ] P2: Stage-4 anchor specificity for broad medical tokens
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2 (quality refinement)
  - Target PR: PR-TBD-RAG-STAGE4-ANCHOR-SPECIFICITY
  - Status: 📋 Planned
  - Reason: Current Stage-4 contradiction binding treats any shared query anchor as sufficient. That is intentional for narrow acronym-style queries (`BMI`, `BP`, `B12`) but may still be too permissive for broad lexical anchors such as `vitamin` or `protein`, especially when cohort qualifiers are intentionally non-binding. The next refinement should separate specific-topic anchors from broad-topic anchors without regressing valid single-anchor contradiction detection.
  - Links:
    - `core/rag/philosophy_pipeline.py`
    - `tests/test_philosophy_pipeline.py`
    - `docs/contracts/RAG_CONTRACT.md`
    - `docs/insights/PHILOSOPHICAL_LOGIC_LLM_RELIABILITY.md`
  - DoD:
    - Stage-4 distinguishes broad-topic anchors from specific-topic anchors deterministically
    - Regression tests cover `vitamin D` vs `vitamin B12` and cohort-specific `protein` cases
    - Existing valid single-anchor contradiction cases (`BMI`, `BP`, `B12`) remain green


<a id="ledger-p2-wellness-explainers-learning-cycles"></a>
- [ ] P2: Wellness Explainers + Learning Cycles MVP (rules-first, trust-first)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2 (product differentiation + trust/retention)
  - Target PR: PR-TBD-WELLNESS-EXPLAINERS-MVP
  - Status: 📋 Planned
  - Reason (EN): Adapt the strongest publicly visible product patterns from TensorTonic without turning PulsePlate into an ML academy. The fit is deterministic explainers, learning-cycle progression, interactive confidence/progress framing, and practice loops tied to existing wellness outputs. This work must remain wellness-safe, backend-owned, and free from streak-shame, leaderboards, or new heavy LLM surface area. (RU: Интегрировать explainers и learning cycles поверх текущих wellness-сущностей; без ML-куррикулума, public leaderboard и без нового дорогого AI-контура.)
  - Links:
    - `docs/product/WELLNESS_EXPLAINERS_LEARNING_CYCLES_MINI_PRD.md`
    - `docs/product/WELLNESS_EXPLAINERS_TENSORTONIC_ADAPTATION_NOTE.md`
    - `docs/product/FREE_PRO_CONTRACT.md`
    - `docs/product/FREE_PRO_SOFT_PAYWALL.md`
    - `docs/audience_pack/FACTS_CANONICAL.md`
    - `docs/analysis/SCIENTIFIC_INNOVATION_ANALYSIS.md`
    - `core/insight/philosophy_validator.py`
    - `docs/policy/LLM_UNIT_ECONOMICS_GUARDRAILS.md`
    - `https://www.tensortonic.com/`
    - `https://www.tensortonic.com/ml-math`
    - `https://www.tensortonic.com/ml-math/statistics/ab-testing`
  - DoD:
    - Backend-owned explainer and learning-cycle direction is documented against existing FREE / PRO / VIP entities
    - MVP scope explicitly bans ML curriculum, browser IDE, public leaderboard, and streak-pressure mechanics
    - Follow-up execution is split into contract, engine, UI, telemetry, and simulator slices
    - Follow-up items reference `docs/product/WELLNESS_EXPLAINERS_TENSORTONIC_ADAPTATION_NOTE.md` for canonical explainer guardrails instead of restating them in parallel
    - MVP path introduces no new heavy LLM endpoint; any optional AI-assisted copy remains guarded by existing safety/economics rules
    - Product copy remains wellness-safe and evidence-aligned
    - GTM framing stays clarity-first and wellness-safe

- [ ] P1: Explainer contract and payload design for FREE / PRO / VIP
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (contract-first unblocker)
  - Target PR: PR-TBD-EXPLAINER-CONTRACT-PAYLOADS
  - Status: 📋 Planned
  - Reason (EN): The first implementation slice should lock backend-owned payload shapes before any UI work. PulsePlate needs canonical response shapes for explainer cards that reuse current BMI, interpretation, adherence, and weekly-plan entities instead of inventing client heuristics. (RU: Сначала нужен каноничный backend contract для explainer payloads; UI не должен сам собирать бизнес-логику.)
  - Links:
    - `docs/product/WELLNESS_EXPLAINERS_TENSORTONIC_ADAPTATION_NOTE.md`
    - `docs/product/FREE_PRO_CONTRACT.md`
    - `app/schemas/`
    - `app/routers/`
  - DoD:
    - High-level contract documents backend-owned `explainer_card` fields for FREE / PRO / VIP
    - Existing product entities are mapped to explainer payload sources without client-side business logic duplication
    - No runtime implementation is required in the design PR

- [ ] P2: Rules-first learning-cycle engine and unlock semantics
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2 (product behavior foundation)
  - Target PR: PR-TBD-LEARNING-CYCLE-ENGINE
  - Status: 📋 Planned
  - Reason (EN): PulsePlate needs deterministic unlock rules based on current BMI, interpretation, adherence, and weekly-plan signals. The cycle model must reward understanding and adjustment, not streak preservation or social pressure. (RU: Нужны детерминированные unlock rules для learning cycles без streak-shame и без social ranking.)
  - Links:
    - `docs/product/WELLNESS_EXPLAINERS_TENSORTONIC_ADAPTATION_NOTE.md`
    - `docs/product/FREE_PRO_CONTRACT.md`
    - `core/`
    - `app/routers/pro.py`
    - `app/routers/vip.py`
  - DoD:
    - Canonical `learning_cycle_state` fields are documented
    - Unlock rules use existing backend signals only
    - Design explicitly bans public leaderboards, addictive streak loops, and ranking mechanics in MVP

- [ ] P2: Frontend and iOS explainer surfaces on current journey pages
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2 (rendering follow-up)
  - Target PR: PR-TBD-EXPLAINER-SURFACES
  - Status: 📋 Planned
  - Reason (EN): After the backend contract exists, explainers should be rendered on existing BMI, PRO interpretation, progress, and weekly-plan surfaces. Delivery must remain thin-client on web and iOS. (RU: После contract phase explainers нужно отрисовать на текущих user journey surfaces без дублирования бизнес-логики на клиентах.)
  - Links:
    - `docs/product/WELLNESS_EXPLAINERS_TENSORTONIC_ADAPTATION_NOTE.md`
    - `frontend/`
    - `ios/`
    - `docs/product/FREE_PRO_CONTRACT.md`
  - DoD:
    - Surface map is defined for web and iOS on current FREE / PRO / VIP pages
    - Rendering remains presentation-only; business logic stays on backend
    - Copy stays wellness-safe and aligned with the trust-based funnel

- [ ] P2: Explainer progress telemetry and experimentation package
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2 (measurement follow-up)
  - Target PR: PR-TBD-EXPLAINER-TELEMETRY
  - Status: 📋 Planned
  - Reason (EN): Explainers and learning cycles need completion and unlock telemetry so the product can measure trust, retention, and progression. This should reuse existing progress/live-indicator patterns instead of creating a parallel growth system. (RU: Для explainers и learning cycles нужна телеметрия completion/unlock, но она должна переиспользовать текущие progress patterns и оставаться privacy-safe.)
  - Links:
    - `docs/product/WELLNESS_EXPLAINERS_TENSORTONIC_ADAPTATION_NOTE.md`
    - `frontend/src/features/progress/`
    - `docs/roadmap/BACKLOG_LEDGER.md`
  - DoD:
    - Canonical `explainer_progress_event` fields are documented
    - Telemetry design is low-cardinality and privacy-safe
    - Experimentation scope is additive and does not introduce a new gamification system in MVP

- [ ] P2: Optional interactive simulator micro-surfaces for wellness understanding
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2 (optional product clarity)
  - Target PR: PR-TBD-WELLNESS-SIMULATOR-MICRO-SURFACES
  - Status: 📋 Planned
  - Reason (EN): TensorTonic's strongest reusable learning mechanic is the combination of explanation, scenario, pitfalls, and interactive simulation. PulsePlate can selectively adapt this for wellness-safe cases such as adherence confidence stability or interpretation confidence with more data, but only as deterministic micro-surfaces grounded in current product logic. (RU: Самая полезная механика для адаптации — explanation + scenario + pitfalls + simulator; у нас это допустимо только для wellness-safe и rules-first micro-surfaces.)
  - Links:
    - `docs/product/WELLNESS_EXPLAINERS_TENSORTONIC_ADAPTATION_NOTE.md`
    - `docs/product/FREE_PRO_CONTRACT.md`
    - `docs/insights/PERFORMANCE_ANALYSIS_AND_NEW_INSIGHTS.md`
    - `core/`
  - DoD:
    - Candidate simulator cases are documented and validated as wellness-safe
    - Simulator logic is deterministic and local to existing product rules
    - No new heavy LLM endpoint or public gamification mechanics are introduced

- [ ] P2: Bayesian adherence prediction and uncertainty quantification (VIP differentiator)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2 (after P0/P1 hardening; unique competitive advantage)
  - Target PR: TBD (design first: core/bayesian/adherence.py, uncertainty intervals)
  - Status: 📋 Planned
  - Reason (EN): Probabilistic personalization: P(adherence | user_context) for adaptive meal plans; confidence intervals for targets (e.g. "1800–2200 kcal, 90% confidence") instead of point estimates. Differentiator vs MyFitnessPal/Cronometer (static calculators). Prerequisites: Bayesian module design, calibration metrics (Brier score). (RU: Байесовская персонализация и доверительные интервалы для целей; уникальное конкурентное преимущество.)
  - Links:
    - docs/analysis/SCIENTIFIC_INNOVATION_ANALYSIS.md (canonical scientific review: Bayesian, uncertainty, roadmap)
    - docs/insights/COMPREHENSIVE_PHILOSOPHY_LOGIC_MATH_CBT_ANALYSIS.md (Bayesian + CBT integration)
    - docs/insights/PEER_REVIEW_ANALYSIS.md (uncertainty quantification gap)
    - core/insight/creative_scientific_innovations.md (FitChef personalization)
  - DoD:
    - Design: core/bayesian/adherence.py (or equivalent) with probabilistic adherence model
    - VIP targets expose confidence intervals where applicable (e.g. calorie range, 90% CI)
    - Calibration metric documented (e.g. Brier score); no regression on existing FREE/PRO contracts

- [ ] P2: Recursive optimization for weekly meal plans (speed + scalability)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2 (when VIP weekly plan performance is in scope)
  - Target PR: TBD (implementation after design)
  - Status: 📋 Planned
  - Reason (EN): Reduce weekly plan generation from 10–30s to 2–5s via divide-and-conquer (split week into halves, optimize recursively, merge with boundary constraints). Lazy day generation: first day instant, remaining days on-demand. Recursive nutrient aggregation O(n log n) for shoplist. (RU: Рекурсивная оптимизация недельных планов и агрегации нутриентов; скорость и масштабируемость.)
  - Links:
    - docs/analysis/SCIENTIFIC_INNOVATION_ANALYSIS.md (canonical scientific review: recursive week planning, lazy days)
    - docs/insights/RECURSIVE_OPTIMIZATION_STRATEGY.md (optimization strategies, code patterns)
    - docs/insights/PERFORMANCE_ANALYSIS_AND_NEW_INSIGHTS.md (bottlenecks: meal plan, shoplist)
    - docs/insights/PHILOSOPHICAL_SPEED_OPTIMIZATION.md (lazy evaluation, early stopping)
    - app/routers/vip.py (current weekly plan flow)
  - DoD:
    - Design: recursive week planning and/or lazy day generation documented
    - Implementation: measurable latency improvement (e.g. time-to-first-day, full week)
    - No regression on constraint satisfaction or nutrition targets

- [ ] P2: Cross-feature integration tests (BMI → Sports → Shoplist flows)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2 (quality assurance; prevent regressions)
  - Target PR: TBD (tests only)
  - Status: 📋 Planned
  - Reason (EN): Unit tests exist; integration tests across feature boundaries are weak. Add end-to-end flows: BMI → sport nutrition → shoplist; recipe synthesis → regional catalog → shoplist. Aligns with CROSS_FEATURE_SYNERGIES and PEER_REVIEW_ANALYSIS gap. (RU: Интеграционные тесты кросс-фичевых сценариев.)
  - Links:
    - docs/analysis/SCIENTIFIC_INNOVATION_ANALYSIS.md (canonical scientific review: cross-feature flows)
    - docs/insights/CROSS_FEATURE_SYNERGIES.md (synergy matrix, flows)
    - docs/insights/PEER_REVIEW_ANALYSIS.md (cross-feature testing gap)
    - tests/ (existing unit/integration structure)
  - DoD:
    - At least one cross-feature flow tested (e.g. BMI → sport targets → plan → shoplist)
    - Tests run in CI; no new flakiness; documented in tests/AGENTS.md or RUNBOOK

- [ ] P2 Optional: Evaluate scientific publication track (Bayesian, CBT, recursive algorithms)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2 (optional; credibility + PR; after core innovations shipped)
  - Target PR: N/A (decision + optional draft)
  - Status: 📋 Planned
  - Reason (EN): Optional papers: Bayesian adherence for personalized nutrition (NeurIPS/ML4H workshop), CBT-aligned gamification vs anxiety (CHI), recursive constraint satisfaction for meal planning (AAAI). Benefit: credibility, press, talent attraction. Effort: 3–6 months per paper; parallel to product. (RU: Опциональная научная публикация по байесовской персонализации, CBT-геймификации, рекурсивным алгоритмам планирования.)
  - Links:
    - docs/analysis/SCIENTIFIC_INNOVATION_ANALYSIS.md (canonical scientific review: publication track, venues)
    - docs/insights/PEER_REVIEW_ANALYSIS.md (publishable insights)
    - docs/insights/COMPREHENSIVE_PHILOSOPHY_LOGIC_MATH_CBT_ANALYSIS.md
    - docs/insights/RECURSIVE_OPTIMIZATION_STRATEGY.md
  - DoD:
    - Decision documented: pursue / defer / won't do for publication track
    - If pursue: venue + outline for one paper; no mandatory timeline


- [ ] P2: Add runbook or CLI helper for resolving review threads
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR-TBD
  - Area: orchestration / CI / review governance
  - Finding Type: operational clarity
  - Reason: Resolving threads via GraphQL is non-obvious for agents and new contributors; one-command helper or runbook section reduces operator friction.
  - Links:
    - `RUNBOOK_AGENT.md` (pre-merge readiness, merge-readiness script)
    - `scripts/orchestration/check_review_threads_disposition.py:444` (CLI entry)
  - DoD:
    - RUNBOOK_AGENT.md section with exact commands for thread resolution, or script scripts/orchestration/resolve_review_threads.py (or equivalent) with documented usage


- [ ] P2: Agent run summary artifact (checklist or JSON)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR-TBD-ORCHESTRATION
  - Status: Planned
  - Area: orchestration / agents
  - Finding Type: observability
  - Reason: Lightweight artifact (checklist/JSON) produced by coordinator or runner for high-value tasks to support future metrics.
  - Links:
    - `docs/audit/EVMBENCH_INSPIRED_AGENT_EVALUATION_BRAINSTORM_2026-02-21.md`
  - DoD:
    - Design doc or ADR: format and when to produce; no implementation required in this item


- [ ] P2: Extend trigger-only ban with optional allowlist TTL (if needed)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR-TBD
  - Area: orchestration / review governance
  - Reason: If an exception is ever needed for a trigger-only mapping, add TTL allowlist (same style as nosec: remove-by, ref); empty by default.
  - DoD: Allowlist file exists (or doc); format documented; guard consults allowlist when present.


- [ ] P2: Integrate review-thread disposition guard into pre-flight
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR #986 or PR-TBD
  - Area: orchestration / CI / review governance
  - Finding Type: process hardening
  - Reason: Make disposition check always-on by calling `check_review_threads_disposition.py` from `scripts/orchestration/check_preflight.py` and documenting in `workflow.md`.
  - Links:
    - `scripts/orchestration/check_review_threads_disposition.py`
    - `scripts/orchestration/check_preflight.py`
    - `docs/orchestration/workflow.md`
  - DoD:
    - Pre-flight runs disposition guard when in PR context (or always)
    - workflow.md updated with required step
    - No regression in pre-flight runtime


- [ ] P2: Invariant-only prompt for fix-CI / fix-guard tasks
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR-TBD-ORCHESTRATION
  - Status: Planned
  - Area: orchestration / agents
  - Finding Type: process
  - Reason: In agent prompts for "fix CI" or "fix guard", explicitly add "do not change invariants; only fix the failing check".
  - Links:
    - `docs/audit/EVMBENCH_INSPIRED_AGENT_EVALUATION_BRAINSTORM_2026-02-21.md`
  - DoD:
    - Coordinator or ci-watcher prompt template updated with invariant-preservation instruction
    - No code change to guards themselves


- [ ] P2: Make trigger-only mapping ban path-aware for file-scoped review comments
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR-TBD
  - Area: orchestration / review governance
  - Finding Type: process hardening
  - Reason: Current empty/rerun checks are heuristic; if thread is file-scoped, mapped SHA should touch same file for stronger proof.
  - Links:
    - `scripts/orchestration/check_review_threads_disposition.py:170` (trigger-only check), `:518` (guard)
    - `tests/test_review_threads_disposition_strict.py`
    - `AGENTS.md:106` (FIXED proof quality, trigger-only ban)
  - DoD:
    - If thread comment is tied to a file path, mapping SHA must change that file
    - Tests cover allow (SHA touches file) and deny (SHA does not touch file)

<a id="ledger-p1-codex-skill-pulseplate-app-store-release"></a>
- [x] P1: Add custom Codex skill `pulseplate-app-store-release` (Wave 1)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR #1436
  - Status: ✅ Merged via PR #1436 (`0b3f2de82892a230789d70648fccfd0f7806641f`) on 17 April 2026
  - Area: iOS / release / orchestration
  - Finding Type: capability expansion
  - Reason: PulsePlate needs a project-specific App Store release skill that understands Fastlane, release truth, metadata parity, screenshot packs, and the repo's non-interference contract with coordinator-first orchestration.
  - Links:
    - `docs/orchestration/CODEX_SKILLS_ALIGNMENT_MATRIX.md`
    - `docs/orchestration/AGENT_SKILL_ROUTING_POLICY.md`
    - `docs/review/PR_1436_FIXED_MAPPING.md`
  - DoD:
    - Skill exists under `tools/codex_skills/pulseplate-app-store-release/`
    - Skill covers App Store metadata, Fastlane, release evidence, and rollback notes
    - Skill docs explicitly preserve coordinator-first and transport-only bridge invariants

<a id="ledger-p1-codex-skill-pulseplate-monetization-gtm"></a>
- [x] P1: Add custom Codex skill `pulseplate-monetization-gtm` (Wave 1)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR #1439
  - Status: ✅ Merged via PR #1439 (`28c2bd2dd18e57a058386670161b0e350e078c5a`) on 17 April 2026; PR #1438 closed as superseded
  - Area: monetization / growth / orchestration
  - Finding Type: capability expansion
  - Reason: PulsePlate needs a project-specific monetization/GTM skill for subscriptions, paywalls, pricing experiments, launch channels, and wellness-safe growth recommendations without relying on generic advice alone.
  - Links:
    - `docs/orchestration/CODEX_SKILLS_ALIGNMENT_MATRIX.md`
    - `docs/orchestration/AGENT_SKILL_ROUTING_POLICY.md`
    - `docs/review/PR_1439_FIXED_MAPPING.md`
  - DoD:
    - Skill exists under `tools/codex_skills/pulseplate-monetization-gtm/`
    - Skill covers paywall, subscription, pricing, ASO/SEO/Product Hunt, and wellness-safe disclaimers
    - Skill docs explicitly preserve coordinator-first and additive `recommended_skills` semantics


- [ ] P2: RAG for agent context (explore)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR-TBD-RAG
  - Status: Research
  - Area: orchestration / RAG
  - Finding Type: exploration
  - Reason: Explore retrieval-augmented context for coordinator/specialist agents (e.g. retrieve AGENTS.md sections by path); keep full SoT as baseline.
  - Links:
    - `docs/audit/EVMBENCH_INSPIRED_AGENT_EVALUATION_BRAINSTORM_2026-02-21.md`
    - `docs/orchestration/workflow.md`
  - DoD:
    - Decision: adopt or decline; if adopt, document in orchestration and one pilot use case


- [x] P2: Skill routing wave 2 — compositional task semantics + approved research connectors
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR #1570
  - Status: Closure is targeted on merge of PR #1570. The implementation is
    already present on `main`; this closeout records evidence and preserves the
    no-runtime-scraping / no-product-RAG boundary.
  - Area: orchestration / research / product governance
  - Finding Type: capability expansion
  - Reason: PR #1022 establishes deterministic weighted skill routing and explicit scraping blocks. The next wave should deepen routing quality without breaking explainability: compositional task semantics, bounded telemetry feedback, and research-only connectors approved for PulsePlate.
  - Links:
    - `docs/orchestration/SKILL_ROUTING_WAVE2_CLOSEOUT_PACKET_2026-04-29.md`
    - `docs/orchestration/AGENT_SKILL_ROUTING_POLICY.md`
    - `scripts/orchestration/skill_router.py`
    - `scripts/orchestration/task_bootstrap.py`
    - `docs/dev/CODEX_SKILLS.md`
  - Closeout evidence:
    - Stable explanation schema and semantic lexeme groups:
      `scripts/orchestration/skill_router.py:231`,
      `scripts/orchestration/skill_router.py:695`
    - Approved research-only connector policy:
      `scripts/orchestration/skill_router.py:288`,
      `scripts/orchestration/skill_router.py:594`
    - Blocked low-fit scraping metadata:
      `scripts/orchestration/skill_router.py:629`
    - Bootstrap packet propagation:
      `scripts/orchestration/task_bootstrap.py:786`,
      `scripts/orchestration/task_bootstrap.py:922`
    - Deterministic coverage:
      `tests/test_skill_router.py:1442`,
      `tests/test_skill_router.py:1510`,
      `tests/test_skill_router.py:1557`,
      `tests/test_task_bootstrap.py:163`
  - DoD:
    - Task packets expose a stable skill-routing explanation schema with compact per-skill evidence: done
    - Routing model adds compositional lexeme groups or ontology tags without introducing nondeterministic scoring: done
    - Approved research-only connector policy is implemented for narrow sources only: YouTube transcripts, X/Twitter official API or compliant exports, Google Trends: done
    - No runtime scraping surface is added to product endpoints: done
    - Deterministic tests cover allowlisted research connectors and blocked low-fit scraping requests: done
    - Closeout PR records focused validation and uses GitHub current-head CI as the heavy signal for this machine-heavy docs/tooling reconciliation

<a id="ledger-p2-codex-skill-pulseplate-design-launch-system"></a>
- [x] P2: Add custom Codex skill `pulseplate-design-launch-system` (Wave 2)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: #1482
  - Status: ✅ Merged via PR #1482 (`d881d5f211478c493d4f18984cb6c335d867be6f`) on 20 April 2026; ledger closeout recorded in PR #1565.
  - Area: design / launch assets / orchestration
  - Finding Type: capability expansion
  - Reason: PulsePlate needs a project-specific design launch system skill that links Figma/design tokens/brand assets with launch-readiness constraints while keeping design tooling passive with respect to coordinator-first routing.
  - Links:
    - `docs/orchestration/CODEX_SKILLS_ALIGNMENT_MATRIX.md`
    - `docs/runbooks/DESIGN_TOOLING_OPERATING_MODEL.md`
    - `docs/orchestration/CODEX_SKILL_PULSEPLATE_DESIGN_LAUNCH_SYSTEM_PACKET_2026-04-20.md`
    - `tools/codex_skills/pulseplate-design-launch-system/SKILL.md`
    - `docs/dev/CODEX_SKILLS.md`
    - `tools/codex_skills/README.md`
  - DoD:
    - Skill exists under `tools/codex_skills/pulseplate-design-launch-system/`
    - Skill covers design system readiness, launch asset bundles, and token/brand consistency
    - Skill docs explicitly preserve fail-closed packet metadata expectations and passive discovery-only boundaries

<a id="ledger-p2-codex-skill-pulseplate-web-launch-site"></a>
- [x] P2: Add custom Codex skill `pulseplate-web-launch-site` (Wave 2)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR #1565
  - Status: ✅ Merged via PR #1565 (Merge commit: `93de5e8dbc7304e3c653736952de8e564b906f5e`) on 2026-04-28.
  - Area: web / launch / frontend
  - Finding Type: capability expansion
  - Reason: PulsePlate needs a project-specific launch-site skill for high-conviction landing pages, launch copy, capture funnels, and deploy-adjacent web launch workflows beyond generic frontend helpers.
  - Links:
    - `docs/orchestration/CODEX_SKILLS_ALIGNMENT_MATRIX.md`
    - `docs/orchestration/AGENT_SKILL_ROUTING_POLICY.md`
    - `tools/codex_skills/pulseplate-web-launch-site/SKILL.md`
  - DoD:
    - Skill exists under `tools/codex_skills/pulseplate-web-launch-site/`
    - Skill covers launch-site structure, CTA/funnel considerations, and frontend implementation handoff
    - Skill docs explicitly preserve coordinator-first and non-interference contract

<a id="ledger-p2-codex-skill-pulseplate-agent-product"></a>
- [x] P2: Add custom Codex skill `pulseplate-agent-product` (Wave 3)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR #1565
  - Status: ✅ Merged via PR #1565 (Merge commit: `93de5e8dbc7304e3c653736952de8e564b906f5e`) on 2026-04-28.
  - Area: agents / product strategy / orchestration
  - Finding Type: capability expansion
  - Reason: PulsePlate needs a project-specific agent-product skill for productizing agent workflows without collapsing repo orchestration, transport-only bridge semantics, or coordinator authority into a parallel runtime layer.
  - Links:
    - `docs/orchestration/CODEX_SKILLS_ALIGNMENT_MATRIX.md`
    - `docs/orchestration/NATIVE_SUBAGENT_BRIDGE_PROTOCOL.md`
    - `tools/codex_skills/pulseplate-agent-product/SKILL.md`
  - DoD:
    - Skill exists under `tools/codex_skills/pulseplate-agent-product/`
    - Skill covers agent-facing product surfaces, guardrails, and orchestration boundaries
    - Skill docs explicitly preserve non-interference with Cursor/custom orchestration

<a id="ledger-p2-fitchef-sandbox-phase-2-deferred-scope"></a>
- [ ] P2: FitChef sandbox Phase 2 deferred scope
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR #1064 (`docs(ledger): freeze fitchef mascot phase 2 contract`)
  - Status: Open
  - Area: orchestration / product runtime / sandbox integration
  - Finding Type: scope control
  - Locations:
    - `docs/contracts/FITCHEF_MASCOT_PHASE2_CONTRACT.md`
    - `docs/design/NUTRITION_COACHING_DESIGN.md`
    - `core/insight/creative_scientific_innovations.md`
  - Reason: The original sandbox Phase 2 seam from PR #1013 now resolves into the mascot-coaching rollout contract. The current P2 execution family is limited to text-only FitChef coaching surfaces under the canonical `/api/v1/insight/fitchef*` namespace, while exports, realtime fan-out, image/CV ingestion, and broader autonomy remain explicitly deferred beyond this wave.
  - Links:
    - `docs/contracts/FITCHEF_MASCOT_PHASE2_CONTRACT.md`
    - `docs/contracts/API_CANONICAL_MAP.md`
    - `docs/design/NUTRITION_COACHING_DESIGN.md`
    - `core/insight/creative_scientific_innovations.md`
    - `docs/review/PR_1013_FIXED_MAPPING.md`
  - DoD:
    - Phase 2 mascot scope is frozen in a current-repo contract doc with canonical routes under `/api/v1/insight/fitchef*`
    - Product/runtime docs link the same mascot plan and do not describe exports, realtime progress, or autonomy as already live
    - Security review confirms each mascot endpoint keeps policy/quota/audit gates ahead of execution
  - Blockers: None (deferred by scope, not blocked)

- [ ] P2: Violations-addressed list in security/guard remediation PRs
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR-TBD (optional per-PR)
  - Status: Planned
  - Area: process / PR template
  - Finding Type: auditability
  - Reason: Optional "violations addressed" list in PR description for guard/security remediation makes coverage auditable (EVMbench-style).
  - Links:
    - `docs/audit/EVMBENCH_INSPIRED_AGENT_EVALUATION_BRAINSTORM_2026-02-21.md`
  - DoD:
    - PR template or runbook suggests optional "Violations addressed" section for guard/security remediation PRs
    - Not mandatory; adopt when useful

<a id="ledger-p2-cv-photo-food"></a>
- [ ] CV (photo → food): contract schema + uncertainty/degrade UX states + privacy packet
  - Owner: @katsiaryna_kavaleuskaya
  - Target PR: TBD
  - Priority: P2
  - Area: product / AI / contracts
  - Finding Type: future feature
  - Reason: If we add photo-based food recognition, it must be contract-first and uncertainty-aware
    (confidence fields, nullability, deterministic degrade states) with explicit privacy UX and retention rules.
  - Links:
    - `docs/orchestration/IOS_FRONTEND_MULTIAGENT_PLAYBOOK.md` (`cv-agent`; degrade-state expectations)
    - `app/schemas/` (canonical schema patterns)
    - `frontend/src/api/schema.ts` (OpenAPI consumer)
  - DoD:
    - Proposed response schema includes: items[], per-item confidence, portion estimate + uncertainty range, warnings[], metadata
    - Deterministic UX state mapping defined for confidence bands (show/confirm/suggest/manual entry)
    - Privacy packet drafted (consent copy, retention, opt-out) and reviewed for wellness-safe wording
    - Deterministic test plan exists (fixtures + expected ranges; no flake)


- [ ] Sensor invariants: physically-plausible bounds + calibration UX contract (no “magic sizing”)
  - Owner: @katsiaryna_kavaleuskaya
  - Target PR: TBD
  - Priority: P2
  - Area: product / measurement / UX safety
  - Finding Type: future feature
  - Reason: Portion/measurement features must enforce physical constraints (units, bounds, drift) and communicate
    uncertainty explicitly; calibration UX must be deterministic and non-misleading.
  - Links:
    - `docs/orchestration/IOS_FRONTEND_MULTIAGENT_PLAYBOOK.md` (sensor-invariant-guard role)
  - DoD:
    - Measurement invariants documented (bounds, units, reject conditions)
    - Calibration UX steps defined (scale + camera reference object) with explicit failure modes
    - Guard policy defined: unphysical outputs rejected; uncertainty increases with degraded signals


- [ ] P2 Vision: Restaurant/chef integration (partners accept menus from our products, cook for users)
  - Owner: @katsiaryna_kavaleuskaya
  - Target PR: PR #TBD-W3-R1-CONTRACT (umbrella split into W3-R1..W3-R4)
  - Priority: P2 (long-term product direction)
  - Reason (EN): Restaurants and individual chefs accept menus from our products (weekly plan, recipes, constraints) and cook food for users. Separate block from coaching and social network; requires clear "menu → partner" contract and technical prerequisites in program (see RESTAURANT_INTEGRATION_SPEC.md). (RU: Рестораны и индивидуальные повара принимают меню по нашим продуктам (недельный план, рецепты, ограничения) и готовят еду пользователям. Отдельный блок от коучинга и соцсети; требует чёткого контракта «меню → партнёр» и технических предпосылок в программе.)
  - Links:
    - docs/design/RESTAURANT_INTEGRATION_SPEC.md (technical prerequisites, contract schema, implementation plan)
    - docs/architecture/ADR_RESTAURANT_PARTNER_CONTRACT_SEAM_2026-03-03.md (temporary seam + exit criteria)
    - app/routers/plan_export.py, vip.py (weekly plan, recipes, export)
    - core/dietary_constraints.py, core/targets.py
  - Prerequisites:
    - ✅ VIP weekly plan stable (`vip.py`, `premium_week.py`)
    - ✅ Export infrastructure exists (`plan_export.py`, `shoplist_export.py`)
    - ✅ Dietary constraints module stable (`core/dietary_constraints.py`)
    - ⏳ Backend/VIP stabilization complete (P0)
  - DoD:
    - Product spec: scenario "user sends menu to restaurant/chef" (what partner sees, how confirms) — EN: documented user flow and partner UX
    - Technical prerequisites documented in design spec (export format, consent, contract schema)
    - Execution decomposition W3-R1..W3-R4 is recorded with per-wave DoD
    - Implementation — separate PRs (export format, partner API or signed link, optionally partner directory)


- [ ] P2: C4-b Sandboxed execution boundary for high-risk agent actions
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR #1013
  - Status: 🟡 In progress (local sandbox foundation implemented in PR #1013, pending merge)
  - Area: security / agent control plane
  - Finding Type: security hardening
  - Locations:
    - `docs/security/AGENT_CONTROL_PLANE_SECURITY_BASELINE.md:73` (C4-b row)
    - `docs/architecture/ADR-003-agent-control-plane-mvp.md:77` (`ExecutionSandbox` boundary)
    - `app/security/execution_sandbox.py`
    - `tests/test_execution_sandbox.py`
  - Reason: Local bounded sandbox execution is now implemented for developer-machine workflows, but the broader stronger-isolation boundary is not merged yet.
  - Links:
    - `docs/architecture/ADR-003-agent-control-plane-mvp.md`
    - `docs/security/AGENT_CONTROL_PLANE_SECURITY_BASELINE.md`
  - DoD:
    - ADR-003 updated with local sandbox boundary, resource limits, and follow-up stronger-isolation scope
    - Runtime sandbox enforcement implemented in `app/security/execution_sandbox.py`
    - Deterministic tests: allowlisted command allowed in sandbox, blocked mode/disallowed binary rejected
    - `.env.example` documents sandbox toggles and bounds
  - Blockers: None (pending PR merge, not blocked)


- [ ] P2: Scoped token nonce — replace deterministic HMAC tokens with nonce-bearing tokens
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR-TBD-TOKEN-NONCE (Wave 2)
  - Status: Planned
  - Area: security / agent control plane
  - Finding Type: security hardening
  - Locations:
    - `app/security/agent_control_plane.py:276` (`issue_scoped_token`)
    - `docs/architecture/ADR-003-agent-control-plane-mvp.md:84` (Wave 2 scope)
    - `docs/security/AGENT_CONTROL_PLANE_SECURITY_BASELINE.md:273` ("Known limitation" note)
  - Reason: MVP scoped tokens are deterministic (HMAC without nonce); identical scope + timestamp produces identical tokens. Replay risk is bounded by short TTL but should be eliminated.
  - Links:
    - `docs/architecture/ADR-003-agent-control-plane-mvp.md`
    - `docs/security/AGENT_CONTROL_PLANE_SECURITY_BASELINE.md`
  - DoD:
    - Nonce/random component design approved in ADR-003 amendment or new ADR
    - Backward-compatible rollout plan documented (old tokens expire within TTL window)
    - Deterministic tests updated: same scope + timestamp produces distinct tokens
    - No performance regression: token issuing latency under 1 ms p99
  - Blockers: None (deferred by priority, not blocked)

<a id="ledger-p2-backlog-ledger-post-merge-sync-audit-canonicalization"></a>
- [ ] P2: Canonicalize backlog-ledger post-merge sync audit artifact
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR `#1152`
  - Status: 🟡 In progress
  - Reason (EN): the retained audit for the PR `#673` / `#674` backlog-sync follow-through still uses `PR_TBD`
    identity and stale branch metadata even though the merged PR numbers are already known. The artifact should be
    reframed as a stable docs-only audit so later governance/review passes do not keep treating it like a live stub.
  - Links:
    - `docs/audit/BACKLOG_LEDGER_POST_MERGE_SYNC_AUDIT_2026-02-07.md`
    - `docs/roadmap/BACKLOG_LEDGER.md`
  - DoD:
    - The audit file no longer uses `PR_TBD` identity or stale branch metadata
    - The artifact is explicitly framed as a stable docs-only audit for merged PR `#673` and PR `#674`
    - The change introduces no runtime, schema, or OpenAPI behavior

<a id="ledger-p1-foods-postgres-foundation-followthrough"></a>
- [x] P1: Foods PostgreSQL follow-through train (B1/B2/B3 merged; cutover deferred)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR `#1409` (`feat/pr-a-foods-catalog-foundation`) -> PR `#1413` (`feat/pr-b1-foods-offline-etl-postgres`) -> PR `#1419` (`feat/pr-b2-restaurant-relational-bridge`) -> PR `#1435` (`feat/pr-b3-restaurant-postgres-shadow-reads`) -> PR `#1462` (`codex/food-postb3-docs-closeout`) -> PR `#1468` (`codex/foods-foundation-downgrade-ownership`)
  - Status: ✅ Merged through downgrade ownership follow-through; runtime authority cutover remains deferred until a separate governed post-B3 packet exists (evidence: `docs/review/PR_1468_FIXED_MAPPING.md`; ADR: `docs/architecture/ADR_FOODS_POSTGRES_RUNTIME_CUTOVER_SEAM_2026-04-17.md:11-24`)
  - Area: backend / data platform / restaurant ingestion
  - Finding Type: post-foundation execution gap
  - Reason: The additive Alembic foundation lane intentionally created `foods`, `restaurant_chains`, and `restaurant_menu_items` without changing the current SQLite/local-first runtime, ETL path, or MenuStat importer. The follow-through train has landed as merged PR `#1409`, PR `#1413`, PR `#1419`, PR `#1435`, PR `#1462`, and PR `#1468`. The governed next food-data line is now the source-update preflight in `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-food-data-source-update-preflight`, while SQLite remains canonical runtime authority until a separate cutover packet is approved (ADR: `docs/architecture/ADR_FOODS_POSTGRES_RUNTIME_CUTOVER_SEAM_2026-04-17.md:11-24`).
  - Sequence:
    - PR-A / foundation: additive `foods` / `restaurant_*` schema landed in merged PR `#1409` (evidence: `docs/review/FOODS_POSTGRES_TRAIN_MERGED_STATE_CANON_2026-04-17.md:7-7`)
    - B1 / foods snapshot promotion: PostgreSQL `foods` promotion landed in merged PR `#1413` (evidence: `docs/review/FOODS_POSTGRES_TRAIN_MERGED_STATE_CANON_2026-04-17.md:8-8`)
    - B2 / importer bridge: PostgreSQL importer persistence landed in merged PR `#1419` (evidence: `docs/review/FOODS_POSTGRES_TRAIN_MERGED_STATE_CANON_2026-04-17.md:9-9`)
    - B3 / shadow reads: PostgreSQL shadow reads + parity checks landed in merged PR `#1435` (evidence: `docs/review/FOODS_POSTGRES_TRAIN_MERGED_STATE_CANON_2026-04-17.md:10-10`)
    - Post-B3 closeout: reconcile backlog/task-packet/review-governance repo truth after merged B3 in PR `#1462` (evidence: `docs/review/FOODS_POSTGRES_TRAIN_MERGED_STATE_CANON_2026-04-17.md:12-13`)
    - Downgrade ownership fix: ownership-aware downgrade for Alembic revision `202604120001` landed in merged PR `#1468` (evidence: `docs/review/PR_1468_FIXED_MAPPING.md`)
    - Next food-data lane: source-update preflight before USDA/Open Food Facts/JPTN/restaurant replacement ingest (ledger: `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-food-data-source-update-preflight`)
    - Cutover (deferred): decide and govern any runtime read-switch / PostgreSQL authority change only after a separate post-B3 cutover packet exists (ADR: `docs/architecture/ADR_FOODS_POSTGRES_RUNTIME_CUTOVER_SEAM_2026-04-17.md:11-24`)
  - Links:
    - `docs/orchestration/FOODS_CATALOG_FOUNDATION_PR_A_TASK_PACKET_2026-04-12.md`
    - `docs/orchestration/FOODS_POSTGRES_PROMOTION_PR_B1_TASK_PACKET_2026-04-13.md`
    - `docs/orchestration/FOODS_POSTGRES_RESTAURANT_BRIDGE_PR_B2_TASK_PACKET_2026-04-13.md`
    - `docs/orchestration/FOODS_POSTGRES_SHADOW_READS_PR_B3_TASK_PACKET_2026-04-16.md`
    - `docs/orchestration/FOODS_POSTGRES_POST_B3_CLOSEOUT_PACKET_2026-04-17.md`
    - `docs/review/FOODS_POSTGRES_TRAIN_MERGED_STATE_CANON_2026-04-17.md`
    - `docs/architecture/ADR_FOODS_POSTGRES_RUNTIME_CUTOVER_SEAM_2026-04-17.md`
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p0-self-hosted-postgres-droplet-foundation`
    - `docs/deploy/POSTGRES_SELF_HOSTED_DROPLET.md`
    - `app/services/food_store.py`
    - `scripts/build_food_db.py`
    - `app/services/restaurant_store.py`
    - `scripts/import_restaurant_menu.py`
  - DoD:
    - Backlog sequencing reflects merged-state truth for PR `#1409`, PR `#1413`, PR `#1419`, and PR `#1435` (evidence: `docs/review/FOODS_POSTGRES_TRAIN_MERGED_STATE_CANON_2026-04-17.md:7-10`)
    - Historical food packets no longer claim B3 is the next active lane
    - Post-B3 docs/governance closeout is explicitly tracked as the current source-of-truth reconciliation lane (evidence: `docs/review/FOODS_POSTGRES_TRAIN_MERGED_STATE_CANON_2026-04-17.md:12-13`)
    - Downgrade ownership follow-through is closed by PR `#1468` (evidence: `docs/review/PR_1468_FIXED_MAPPING.md`)
    - The next food-data lane is explicitly set to `ledger-p1-food-data-source-update-preflight`
    - Runtime authority cutover / read-switch remains explicitly deferred beyond B3 until a separate cutover packet exists (ADR: `docs/architecture/ADR_FOODS_POSTGRES_RUNTIME_CUTOVER_SEAM_2026-04-17.md:11-24`)
    - Search / catalog follow-up lanes continue to reference the same canonical PostgreSQL table source without parallel schema drift

<a id="ledger-p1-foods-foundation-downgrade-ownership"></a>
- [x] P1: Make foods foundation downgrade ownership-aware for pre-existing catalog objects
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR #1468 -> `codex/foods-foundation-downgrade-ownership`
  - Status: ✅ Merged (PR `#1468`, merge commit `4876d24ef8311acdd0be9b54642f210c25c3e4a7`, April 19, 2026)
  - Area: backend / migrations / PostgreSQL
  - Finding Type: downgrade symmetry / object ownership
  - Reason: Revision `202604120001` now guards upgrade-time creation of `foods` and companion indexes when a supported colocated catalog shape already exists, but the downgrade path still assumes ownership of those objects. A follow-up lane must make the downgrade ownership-aware so rolling back the revision does not drop pre-existing `foods`/index artifacts that were not created by this revision.
  - Links:
    - `alembic/versions/202604120001_add_foods_catalog_foundation.py`
    - `docs/orchestration/FOODS_CATALOG_FOUNDATION_PR_A_TASK_PACKET_2026-04-12.md`
    - `docs/orchestration/FOODS_FOUNDATION_DOWNGRADE_OWNERSHIP_TASK_PACKET_2026-04-18.md`
    - `docs/review/PR_1409_FIXED_MAPPING.md`
    - `docs/review/PR_1468_FIXED_MAPPING.md`
  - DoD:
    - Downgrade behavior is explicit for both clean-room and pre-existing `foods` catalog shapes
    - The revision no longer drops pre-existing `foods`/index artifacts that it did not create
    - Migration tests cover both the clean-room downgrade cycle and the pre-existing-table ownership scenario

<a id="ledger-p1-foods-foundation-legacy-ownership-backfill"></a>
- [ ] P1: Define retroactive rollback behavior for legacy-applied foods foundation revision
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-TBD
  - Status: Deferred from PR `#1468` review loop
  - Area: backend / migrations / PostgreSQL
  - Finding Type: legacy downgrade / ownership backfill
  - Reason: Databases that already applied the pre-ownership version of revision `202604120001` do not have `pulseplate_migration_ownership`, so downgrade cannot distinguish revision-owned objects from pre-existing catalog artifacts. PR `#1468` intentionally fixes forward-looking ownership-aware behavior for new upgrade runs only; retroactive repair for already-applied environments requires a separate design lane.
  - Evidence:
    - `alembic/versions/202604120001_add_foods_catalog_foundation.py:83`
    - `alembic/versions/202604120001_add_foods_catalog_foundation.py:119`
    - `docs/orchestration/FOODS_FOUNDATION_DOWNGRADE_OWNERSHIP_TASK_PACKET_2026-04-18.md:65`
  - Links:
    - `alembic/versions/202604120001_add_foods_catalog_foundation.py`
    - `docs/orchestration/FOODS_FOUNDATION_DOWNGRADE_OWNERSHIP_TASK_PACKET_2026-04-18.md`
    - `docs/review/PR_1468_FIXED_MAPPING.md`
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-foods-foundation-downgrade-ownership`
  - DoD:
    - A separate design records the authoritative rollback contract when `pulseplate_migration_ownership` is absent on an already-applied `202604120001` database
    - The chosen path explicitly defines whether legacy environments use ownership backfill, guarded legacy fallback, or an operator-driven/manual repair contract
    - Deterministic tests cover the chosen legacy-applied rollback path without regressing clean-room or pre-existing-catalog scenarios

## Completed Items

Entries are sorted by priority, then theme, then title. Theme uses `Area:` when present and a deterministic title/domain fallback otherwise.

### P0

<a id="ledger-p0-billing-apple-verify"></a>
- [x] P0: Apple receipt verification backend follow-through
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P0
  - Target PR: PR `#1074` (`feat(billing): add Apple receipt verification endpoint`)
  - Status: ✅ Completed (Merged PR #1074 on 2026-03-10)
  - Merge SHA: `e0104c540bfb63cc2fd944090d293c7b751651e8`
  - Area: backend / payments / iOS monetization
  - Finding Type: payment integrity
  - Reason (EN): The iOS-first billing baseline now exists, but automatic activation remains incomplete until server-side Apple receipt verification is treated as a canonical follow-through item rather than an implied subtask.
  - Links:
    - `docs/contracts/PAYMENTS_RU_BY_IOS_BASELINE.md`
    - `docs/roadmap/P0_MASTER_CHECKLIST_PHASE_FIT_TRIAGE_2026-03-05.md`
    - `app/routers/billing.py`
    - `docs/review/PR_1074_FIXED_MAPPING.md`
    - `app/services/payments_activation.py`
  - DoD:
    - Server-side Apple receipt verification normalizes into the canonical billing activation flow
    - Receipt verification failure modes are deterministic and test-covered
    - Activation/status contracts stay additive for existing clients

<a id="ledger-p0-session-cookie-hardening"></a>
- [x] P0: Web session token transport hardening (`localStorage` -> `httpOnly` cookie)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P0 (security blocker)
  - Target PR: PR #1003 (`fix(auth): align web session UI gates`) -> PR #1030 -> PR #1063
  - Status: ✅ Merged evidence (web session migration delivered on `main`; audit trail reconciled in a later docs/security follow-up)
  - Reason (EN): Master checklist item #1 identified XSS exposure when auth/session keys were persisted in browser storage. That web runtime gap is now closed on `main`: PR #1003 moved route gating toward session-backed auth state, PR #1030 hardened the W1 migration path, and PR #1063 removed the remaining storage-seeded smoke/logout coupling while keeping cleanup semantics fail-closed in `frontend/src/auth/storage.ts`. This backlog item is therefore closed as delivered evidence rather than carried forward into a fake W2 runtime PR. The canonical closure was reconciled later in a docs/security follow-up so the ledger matches already-merged runtime evidence. (RU: Web runtime gap по browser-stored auth secrets уже закрыт в `main`: PR #1003 перевёл gate-логику на session truth, PR #1030 усилил W1 migration path, PR #1063 убрал оставшуюся storage-seeded smoke/logout связку и оставил cleanup fail-closed. Псевдо-carryover `PR-TBD-SESSION-COOKIE-HARDENING-W2` больше не нужен; поздний docs/security follow-up лишь синхронизировал ledger с уже смерженным runtime evidence.)
  - Links:
    - docs/roadmap/P0_MASTER_CHECKLIST_PHASE_FIT_TRIAGE_2026-03-05.md
    - app/security/auth.py
    - app/routers/pro_registration.py
    - frontend/src/auth/storage.ts
    - frontend/src/components/TabBar.tsx
    - frontend/src/auth/__tests__/storage.test.ts
    - frontend/src/components/__tests__/TabBar.test.tsx
    - https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1003
    - https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1030
    - https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1063
  - DoD:
    - No sensitive session/auth token persists in browser local storage, including cleanup-failure paths
    - Session issuance/refresh flow uses secure cookie attributes (`HttpOnly`, `Secure`, `SameSite`)
    - Regression tests cover authenticated flows, logout/invalidation, and cleanup-failure semantics

- [x] P0 CRITICAL: Move LLM insight to VIP tier (prevent FREE tier abuse)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P0 (CRITICAL security)
  - Target PR: PR-640 (runtime), PR-646 (docs-only closure)
  - Status: ✅ Done
  - Reason: Implemented VIP-only access for `/api/v1/insight` and legacy `/insight` (VIP-guarded, hidden from OpenAPI) + kept rate-limiting. This ledger entry was stale vs `main`.
  - Residual risk / follow-up: monthly hard quota/budget enforcement is still required (see next P0 item). Until then,
    LLM endpoints remain economically unsafe per `docs/policy/LLM_UNIT_ECONOMICS_GUARDRAILS.md`.
  - Links:
    - docs/audit/LEGACY_APP_MIGRATION_STATUS.md (Tier guards section)
    - docs/audit/AUDIT_GAPS_ANALYSIS.md (LLM cost control gap)
    - PR-640: Enforce VIP tier for LLM Insight (runtime implementation)
    - docs/audit/PR_646_VIP_ONLY_LLM_INSIGHT_AUDIT.md (evidence + ledger closure)
  - DoD:
    - ✅ `/api/v1/insight` uses `require_vip_tier()` (VIP-only)
    - ✅ `/insight` is VIP-guarded (deprecated + hidden from OpenAPI)
    - ✅ Tests verify FREE/PRO users get 403, VIP users get 200
    - ✅ OpenAPI shows `/api/v1/insight` and hides `/insight`


- [x] P0 CRITICAL: Rate-limiting for LLM endpoints (prevent $72k/month cost attack)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P0 (CRITICAL security)
  - Target PR: PR-639 (supersedes PR-628)
  - Status: ✅ Done (superseded by PR-639)
  - Reason: Close PR-628 via PR-639: audit drift fixed (runtime wiring + proxy-aware CIDR client key + deterministic tests are present) and 429 OpenAPI schema standardized for VIP export; OpenAPI artifacts regenerated.
  - Links:
    - docs/audit/LEGACY_APP_MIGRATION_STATUS.md (Rate-limiting section)
    - docs/audit/AUDIT_GAPS_ANALYSIS.md (LLM cost control gap)
    - core/insight/analysis_insights.md ($72k/month potential abuse)
    - docs/audit/PR_628_RATE_LIMIT_LLM_EXPORTS_AUDIT.md
    - <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/628>
    - <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/639>
  - DoD:
    - ✅ Rate-limiting wired in runtime (SlowAPI middleware + 429 handler)
    - ✅ Proxy-aware key function supports trusted proxies with CIDR + CF/XFF precedence
    - ✅ `@limit_if_available(RATE_LIMIT_INSIGHT)` on `/api/v1/insight` + `/insight`
    - ✅ `@limit_if_available(RATE_LIMIT_EXPORTS)` on export endpoints (plan/shoplist/VIP export + legacy demo exports when enabled)
    - WebSocket: N/A (no endpoints found; see WebSocket investigation item)
    - ✅ Tests verify rate-limiting works (deterministic 200→429)
    - Cost tracking added (token usage, API calls)


<a id="ledger-p0-pro-vip-depends-guard"></a>
- [x] P0: PRO/VIP route `Depends` coverage guard
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P0 (access-control integrity)
  - Target PR: PR #994
  - Status: ✅ Merged (PR #994, 2026-03-06)
  - Reason (EN): Master checklist item #7 requires deterministic proof that all protected endpoints enforce explicit dependency gates and no silent bypass is introduced by future routing changes.
  - Links:
    - docs/roadmap/P0_MASTER_CHECKLIST_PHASE_FIT_TRIAGE_2026-03-05.md
    - app/security/api_tiers.py
    - app/routers
    - tests/test_pro_vip_route_dependency_guard.py
    - tests/test_api_tiers_db_lookup.py
  - DoD:
    - Guard test enumerates canonical PRO/VIP surfaces and fails on missing dependency gate
    - Legacy aliases are validated as non-bypass paths
    - CI gate is deterministic and documented in runbook


<a id="ledger-p0-rag-input-sanitizer"></a>
- [x] P0: RAG input sanitizer integration for markdown/knowledge ingestion
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P0 (security + data quality)
  - Target PR: PR-TBD-RAG-INPUT-SANITIZER -> PR #1044
  - Status: ✅ Merged (PR #1044, 2026-03-08)
  - Reason (EN): Query-level AI input blocking already existed in `app/security/agent_input_guard.py`, but markdown/knowledge ingestion and retrieval content still lacked a canonical sanitizer seam. PR #1044 closed that gap by sanitizing markdown before indexing, sanitizing retrieved chunk content before prompt assembly, dropping sanitized-empty chunks, and surfacing an explicit CBT warning when source content was sanitized.
  - Links:
    - docs/roadmap/P0_MASTER_CHECKLIST_PHASE_FIT_TRIAGE_2026-03-05.md
    - core/data_sanitizer.py
    - core/rag/simple_rag.py
    - core/rag/vector_rag.py
    - core/rag/formatting.py
    - core/rag/recursive_retrieval.py
    - app/routers/cbt_insight.py
    - app/security/agent_input_guard.py
    - tests/test_data_sanitizer.py
    - tests/test_rag_orchestration.py
    - tests/test_cbt_insight_api.py
    - https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1044
  - DoD:
    - ✅ Sanitization is applied deterministically before RAG indexing and retrieval
    - ✅ Injection-pattern regression tests are added and green
    - ✅ No contract break for current insight endpoints


- [x] P0: Growth telemetry canon and KPI dashboard baseline
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P0
  - Target PR: PR #845 (Phase 1 merged); Phase 2 (eventRegistry.ts) after PR #825 merge
  - Status: Phase 1 ✅ Merged (PR #845, 2026-02-21); Phase 2 deferred
  - Area: analytics / frontend / growth
  - Finding Type: product optimization
  - Locations:
    - `docs/analytics/ANALYTICS_INDEX.md`
    - `docs/analytics/METRICS_CATALOG.md`
    - `frontend/src/lib/telemetry/eventRegistry.ts`
  - Reason: establish canonical funnel semantics and events for onboarding -> paywall -> conversion -> retention.
  - Links:
    - `docs/analytics/EXPERIMENT_REGISTRY.md`
    - [PR #845](https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/845) (Phase 1 docs)
  - DoD:
    - Core funnel metrics defined with owner and update cadence (Phase 1 in PR #845)
    - Event taxonomy anchored in docs and frontend registry (docs in PR #845; frontend in Phase 2)
    - Dashboard baseline requirements documented (Phase 1 in PR #845)


- [x] P0: Agent Control Plane MVP (policy gate + signed audit + secrets boundary)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P0
  - Target PR: #846
  - Status: ✅ Completed (Merged PR #846 on 2026-02-21)
  - Area: architecture / backend / security
  - Finding Type: platform hardening / modernization
  - Locations:
    - `docs/architecture/ADR-003-agent-control-plane-mvp.md`
    - `docs/roadmap/PROGRAM_6M_BALANCED_2026H1.md`
  - Reason: replace third-party local agent dependency with policy-first, vendor-independent control plane.
  - Links:
    - `docs/security/AGENT_CONTROL_PLANE_SECURITY_BASELINE.md`
    - `docs/roadmap/WAVE_2_3_EXECUTION_PACK.md`
    - `app/security/agent_control_plane.py`
    - `tests/test_agent_control_plane_mvp.py`
  - Evidence (2026-02-21, America/New_York):
    - `app/security/agent_control_plane.py:1` — MVP primitives implemented:
      deny-by-default policy gate, signed audit envelope, and short-lived scoped token issuing.
    - `tests/test_agent_control_plane_mvp.py:1` — deterministic coverage for
      allowlist parsing, fail-closed policy decisions, audit signature verification, and token TTL validation.
  - DoD:
    - [x] Control plane MVP contract documented and accepted
    - [x] Deny-by-default policy requirements and fail-closed semantics documented
    - [x] Signed audit trail requirements documented with verification checklist
    - [x] Initial runtime primitives implemented with deterministic tests
    - [x] Follow-up implementation PRs opened and linked (PR #846)


- [x] P0: Food Data Platform Foundation (snapshot-first, multi-source, low-API-cost)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P0
  - Target PR: PR #886
  - Status: ✅ Merged (PR #886, 2026-02-24)
  - Area: architecture / data platform / product database
  - Finding Type: financial + architecture gap closure
  - Reason: The largest current financial and architecture gap is food/menus data quality and coverage. USDA+OFF foundations exist, but snapshot governance, canonical confidence/provenance policy, and structured execution waves are not yet locked as a canonical strategy.
  - Links:
    - `docs/architecture/FOOD_DATABASE_PLATFORM_STRATEGY_v1.md`
    - `docs/design/RESTAURANT_INTEGRATION_SPEC.md`
    - `core/food_apis/`
    - `core/food_sources/`
    - `app/routers/foods.py`
  - DoD:
    - Strategy SoT is merged in docs-only PR
    - Source tiering and update cadence are finalized
    - Execution is split into wave PRs with clear ownership
    - Carryover/deferred mapping is documented in this ledger


- [x] Backend: Fix deprecated `/api/nutrition/{date_str}` legacy alias to enforce `require_pro_tier` (auth bypass risk)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P0 (security)
  - Target PR: PR-664
  - Status: ✅ Merged (PR-664, 2026-02-07)
  - Reason: `legacy_app.py` implements `/api/nutrition/{date_str}` as a legacy alias and uses `Depends(api_key_header)` (header extraction only), then calls `app/routers/pro.py:get_daily_nutrition()` directly. This bypasses the `require_pro_tier` dependency (tier validation) and does not pass the API key into any guard, risking unauthorized access if the alias is reachable.
  - Decision:
    - Preferred outcome: remove deprecated alias entirely (keep only canonical `GET /api/v1/pro/nutrition/daily`).
    - Fallback (if removal is not possible now): keep alias but explicitly enforce `require_pro_tier` in the alias handler + deterministic 401/403/200 tests.
  - Links:
    - docs/audit/PR_654_BACKEND_LEGACY_NUTRITION_ALIAS_PRO_GUARD_AUDIT.md
    - `legacy_app.py` (`/api/nutrition/{date_str}` legacy alias)
    - `app/routers/api_key.py` (`api_key_header`)
    - `app/middleware/api_tiers.py` (`require_pro_tier`)
    - `app/routers/pro.py` (`GET /api/v1/pro/nutrition/daily`)
    - `ios/PulsePlate/Models/NutritionData.swift` (client currently uses legacy path)
  - DoD:
    - Alias either removed or explicitly enforces PRO tier guard (no auth bypass)
    - Deterministic tests prove 401/403/200 behavior for alias path
    - Docs explicitly mark alias as deprecated and forbidden as client SoT (iOS uses canonical `/api/v1/pro/nutrition/daily`)
    - OpenAPI visibility matches deprecation policy (deprecated/hidden as appropriate)


- [x] P0-1: API Surface Governance / Namespace guards
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P0
  - Target PR: PR #909 (`feat/pr-909-food-db-next`)
  - Status: ✅ Merged (PR #909, 2026-02-26)
  - Area: backend / API governance / OpenAPI contracts
  - Finding Type: architecture governance gap
  - Reason: Public OpenAPI surface drift must be locked to canonical FREE/PRO/VIP namespaces to prevent schema sprawl and tier-discipline erosion.
  - Links:
    - `docs/architecture/ADR_API_SURFACE_CONSOLIDATION_2026-02-26.md`
    - `tests/test_openapi_namespace_guards.py`
    - `legacy_app.py`
    - `frontend/src/api/openapi.json`
  - DoD:
    - OpenAPI namespace guard test is merged and enforced in CI
    - Legacy `/api/v1/foods*` and `/api/v1/restaurants*` are hidden from OpenAPI schema
    - Runtime compatibility for legacy routes remains intact
    - API surface consolidation ADR is merged


- [x] P0-2: WS namespace migration (`/ws` -> `/api/v1/pro/ws`)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P0
  - Target PR: PR #919 (`feat/p0-2-ws-canonical-clean`)
  - Status: ✅ Merged (PR #919, 2026-02-26)
  - Area: backend / realtime transport / API governance
  - Finding Type: namespace consistency follow-up
  - Reason: WebSocket path still uses transitional root namespace (`/ws`) and must align with canonical PRO surface while preserving a deprecation window.
  - Links:
    - `app/routers/realtime_ws.py`
    - `app/main.py`
    - `frontend/src/api/wsClient.ts`
  - DoD:
    - Canonical WebSocket endpoint available at `/api/v1/pro/ws`
    - `/ws` compatibility alias is deprecated with removal window documented
    - OpenAPI/guard policy updated to remove transitional `/ws` allowance
    - Frontend ws client defaults to canonical path


- [x] P0: Execution Wave 1 — Snapshot manager + OFF delta + canonical merge contract
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P0
  - Target PR: PR #889
  - Status: ✅ Merged (PR #889, 2026-02-24)
  - Area: backend / data ingestion
  - Finding Type: runtime foundation
  - Reason: Runtime needs deterministic snapshot lifecycle and incremental OFF updates before expansion to search and restaurants.
  - Links:
    - `docs/architecture/FOOD_DATABASE_PLATFORM_STRATEGY_v1.md`
    - `core/food_sources/`
    - `core/food_apis/update_manager.py`
    - `scripts/build_food_db.py`
    - W1 manifest integrity extension: PR #1360 (merged; canonical ledger entry below)
  - DoD:
    - Immutable raw snapshot layout is implemented
    - Manifest/checksum policy is enforced fail-closed
    - Deterministic OFF delta ingestion is in place
    - Existing `/api/v1/foods*` behavior remains compatible


- [x] P1: PR #1360 — snapshot record verification + size enforcement (W1 manifest integrity)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR #1360 (https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1360)
  - Status: ✅ Merged (PR #1360, 2026-04-06; merge commit `837cfa170a30160e5f720609cb508e05d4565782`)
  - Area: backend / data ingestion / manifest integrity
  - Finding Type: W1 merge follow-up (fail-closed verification)
  - Reason (EN): Extend Wave 1 snapshot hub with fail-closed `verify_recorded_snapshots` and recorded size/checksum enforcement. (RU: расширение W1 — жёсткая проверка записанных снапшотов и размера.)
  - Links:
    - `core/food_sources/snapshot_manager.py`
    - `docs/architecture/FOOD_DATABASE_PLATFORM_STRATEGY_v1.md` (§5.1)
  - DoD:
    - Fail-closed verification path covered by deterministic tests
    - Strategy SoT §5.1 anchors reference current `file:line` entrypoints


- [x] P0: Food data licensing + attribution compliance package
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P0
  - Target PR: PR #915 (`feat/food-api-attribution-compliance`)
  - Status: ✅ Merged (PR #915, 2026-02-26)
  - Area: backend / legal-compliance / API contracts
  - Finding Type: legal + governance risk closure
  - Reason: Food data sources include ODbL-licensed datasets (Open Food Facts). Runtime surface needs a canonical attribution contract and documented policy to reduce legal/compliance risk before broader partner growth.
  - Links:
    - `docs/legal/ODbL_COMPLIANCE.md`
    - `app/routers/pro_food_attribution.py`
    - `app/services/food_store.py`
    - `tests/test_pro_food_attribution.py`
  - DoD:
    - PRO endpoint returns source-level license + attribution metadata
    - Source attribution registry is centralized server-side (no client hardcoding)
    - Deterministic tests cover auth gate + contract payload
    - Compliance policy doc is merged and linked in backlog


- [x] P0: GDPR retention cleanup implementation (replace stub with safe deletion)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P0 (privacy/compliance)
  - Target PR: PR #978 (`fix/gdpr-log-retention-cleanup`)
  - Status: ✅ Merged (PR #978, 2026-03-05)
  - Area: backend / compliance / operations
  - Finding Type: compliance hotfix
  - Reason: `cleanup_expired_logs()` was a non-destructive stub; privacy posture requires real retention enforcement with path safety and deterministic dry-run checks.
  - Links:
    - `core/log_retention.py`
    - `tests/test_log_retention_coverage.py`
    - `tests/test_fingerprint_and_retention.py`
  - DoD:
    - Real mtime-based cleanup is implemented under bounded retention root
    - Dry-run mode is additive and non-breaking
    - Deletion outside configured root is blocked (path-safety guard)
    - Deterministic tests cover dry-run, class filter, stat/unlink errors, and path boundary
    - `pre-commit run --all-files` and `make verify` pass in PR scope


<a id="ledger-p0-export-signing-hardening"></a>
- [x] P0: Harden private export signing secret and signable-path scope
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P0
  - Target PR: PR-TBD-EXPORT-SIGNING-HARDENING -> PR #1035 (`fix(export): harden signing secret access`)
  - Status: ✅ Merged (PR #1035, 2026-03-08)
  - Area: backend / security / export signing
  - Finding Type: auth/config hardening
  - Reason: Repo truth already contains signable-path allowlisting and production/staging placeholder rejection in `settings.py`, but `app/routers/plan_export.py` still imports a static `EXPORT_TOKEN_SECRET` at module load. That keeps signing/verification vulnerable to runtime config drift and leaves the canonical hidden-schema contract under-tested.
  - Links:
    - `app/routers/plan_export.py`
    - `settings.py`
    - `signed_links.py`
    - `frontend/src/features/plan/WeeklyPlanViewer.tsx`
    - `tests/test_export_signed.py`
    - `docs/review/PR_1035_FIXED_MAPPING.md`
  - DoD:
    - Signing and verification use `get_export_token_secret()` at request time instead of a stale imported constant
    - Private export signing fails closed when `EXPORT_TOKEN_SECRET` is default/empty in production-like envs
    - Allowed sign targets stay restricted to canonical export routes actually used by product flows
    - Canonical `app.openapi()` keeps export routes hidden while runtime route registration stays intact
    - Deterministic tests cover deny/default-secret, deny/non-allowlisted-path, and hidden-schema regression branches
    - `pre-commit run --all-files` and `make verify` pass in PR scope


- [x] P0: Import determinism for app-level tests (remove skip fallback)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P0
  - Target PR: PR-729
  - Status: ✅ Merged (PR-729, 2026-02-13)
  - Area: backend / tests
  - Finding Type: quality / determinism
  - Locations:
    - `tests/test_api.py:343` — guard test enforces "fail, not skip" policy
    - `tests/test_api.py:346` — marker check prevents reintroducing
      `pytest.skip("App import failed unexpectedly")`
  - Reason: Import determinism is a foundation invariant. Skipping app import failures masks CI and runtime risks.
  - Links:
    - `docs/audit/SKIPPED_TESTS_CLASSIFICATION_AUDIT_2026-02-13.md`
    - `AGENTS.md:58`
    - `AGENTS.md:64`
  - Evidence (2026-02-13):
    - `pytest -q tests/test_api.py -rs` -> `22 passed`, `0 skipped`
    - `rg -n "SKIPPED \\[4\\]|App import failed unexpectedly" -S tests` -> no matches
  - DoD:
    - No skip fallback for app import in `tests/test_api.py`
    - Import path uses deterministic seams (no `builtins.__import__` patching)
    - The 4 previously skipped import tests execute (pass/fail, not skip)
    - `make verify` passes in PR-729


- [x] P0: OFF Vitamin D unit normalization (µg -> IU) + nameless-row guard
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P0 (data correctness)
  - Target PR: PR #976 (`fix/off-vitd-unit-conversion`)
  - Status: ✅ Merged (PR #976, 2026-03-05)
  - Area: backend / food data normalization
  - Finding Type: correctness hotfix
  - Reason: Open Food Facts normalization writes `vitamin-d_100g` without deterministic µg→IU conversion and may ingest nameless rows; this degrades canonical nutrition trust and search quality.
  - Links:
    - `core/food_sources/off.py`
    - `tests/test_food_sources_simple.py`
    - `docs/architecture/FOOD_DATABASE_PLATFORM_STRATEGY_v1.md`
  - DoD:
    - OFF `vitamin-d_100g` is normalized via deterministic `iu_vitd_from_ug(...)`
    - Nameless rows are skipped fail-closed during OFF import
    - Deterministic tests cover µg→IU mapping and nameless-row skip behavior
    - `pre-commit run --all-files` and `make verify` pass in PR scope


- [x] Greenlight iOS P0 report-only workflow
  - Owner: @katsiaryna_kavaleuskaya
  - Target PR: PR-722
  - Status: ✅ Merged (PR-722, 2026-02-12)
  - Priority: P0
  - Area: CI / iOS
  - Reason: Add report-only App Store readiness scan for iOS in CI.
  - Links:
    - docs/audit/PR_722_GREENLIGHT_INTEGRATION_AUDIT.md
    - docs/runbook/IOS_GREENLIGHT.md
  - DoD:
    - Workflow `.github/workflows/greenlight-ios.yml` path-scoped ✅
    - Report artifact + step summary ✅
    - P0 report-only documented ✅


- [x] Retro-audit PR window #838-#842: merge/comment timing + tail closure
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P0 (process reliability)
  - Target PR: #842, #843, #844
  - Status: ✅ Completed (2026-02-21)
  - Area: CI/process governance + docs follow-up
  - Finding Type: post-merge audit + governance hardening
  - Reason: Multiple PRs were merged before full bot/comment cycle completion; we needed deterministic evidence,
    explicit tail closure, and technical merge-blocking controls.
  - Findings:
    - PR #838: only post-merge Codecov report (no actionables).
    - PR #839: post-merge cubic "No issues found" + Codecov (no actionables).
    - PR #840: post-merge review events (no actionable inline findings to apply).
    - PR #841: post-merge Sourcery actionable found; fixed and merged via PR #842.
    - PR #842: held until full green + bot pass; merged only after final CI completion.
    - PR #833 doc comment tail: no longer relevant on current `main` (already reflected in `AGENTS.md`).
    - PR #835 doc comment tail: still relevant; addressed via docs follow-up PR #843.
  - Links:
    - PR #842: `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/842`
    - PR #843: `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/843`
    - PR #844: `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/844`
  - DoD:
    - ✅ Retro-audit evidence recorded for each PR in scope
    - ✅ Missed actionable from PR #841 remediated and merged
    - ✅ Docs tail from PR #835 moved to follow-up PR (#843)
    - ✅ Merge-readiness process hardened with CI policy gate PR (#844)


- [x] HPP Web visual workflow: Playwright deterministic smoke lane
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P0 (frontend quality guardrail)
  - Target PR: #828, #840
  - Status: ✅ Merged (2026-02-21)
  - Area: frontend / HPP / e2e visual smoke
  - Finding Type: execution foundation
  - Reason: HPP route changes need deterministic browser smoke checks to catch critical UI regressions
    (`/`, `/plate`, `/progress`, `/pro`) before broader CI hardening.
  - Links:
    - `docs/dev/PLAYWRIGHT_E2E_RUNBOOK.md`
    - `frontend/playwright.config.ts`
    - `frontend/e2e/`
  - DoD:
    - Playwright config and smoke specs exist for canonical HPP routes
    - `npm run test:e2e` and headed variant are available in `frontend/package.json`
    - Smoke checks run with deterministic local web server settings
    - Runbook contains npm-first execution commands


- [x] HPP Web visual workflow: Storybook bootstrap + first tokenized stories
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P0 (frontend delivery accelerator)
  - Target PR: #828, #839
  - Status: ✅ Merged (2026-02-21)
  - Area: frontend / HPP / design-system tooling
  - Finding Type: execution foundation
  - Reason: HPP UI currently lacks isolated component review. Adding Storybook enables deterministic visual
    review of tokenized primitives before route-level integration and reduces regressions during rapid UI iteration.
  - Links:
    - `frontend/package.json`
    - `frontend/src/components/ui/`
    - `docs/orchestration/IOS_FRONTEND_MULTIAGENT_PLAYBOOK.md`
  - DoD:
    - Storybook is wired in `frontend` (`storybook`, `build-storybook` scripts)
    - HPP stories exist for `SegmentedControl`, `Toggle`, `FormField`, and page-card shell
    - Token usage guidelines page exists for HPP states (default/realtime/fallback/conversion)
    - Storybook build passes in local verification


- [x] Web design-token hardening: Token SoT + palette switch + runtime raw-hex guard
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P0 (frontend stability / drift prevention)
  - Target PR: #835, #837
  - Status: ✅ Merged (2026-02-21)
  - Area: frontend / design-system governance
  - Finding Type: policy hardening + runtime guard
  - Reason: Token drift risk and hardcoded runtime colors were allowing visual inconsistency. We fixed
    source-of-truth ownership, activated canonical palette tokens, and added deterministic guardrails
    to prevent future raw-hex regressions in runtime UI paths.
  - Links:
    - `docs/design/TOKENS_SOT.md`
    - `frontend/src/styles/tokens.css`
    - `frontend/src/styles/tokens.ts`
    - `tests/test_frontend_raw_hex_guard.py`
    - PR #835, PR #837
  - DoD:
    - ✅ Token SoT documented and merged
    - ✅ Canonical palette values active in web tokens
    - ✅ Plate chart raw hex replaced with token variables
    - ✅ Runtime raw-hex guard test merged with explicit allowlist

<a id="ledger-p0-ci-nightly-test-db-schema-bootstrap"></a>
- [x] P0: CI nightly — test DB schema bootstrap broken (users/nutrition_events missing)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P0 (CRITICAL)
  - Target PR: PR-629
  - Status: ✅ Merged (PR-629)
  - Reason: CI/nightly shows DB schema is not created before API tests (`no such table: users`, `no such table: nutrition_events`), causing secondary thread errors. Root cause: metadata/bootstrap ordering (missing model package import before create_all).
  - Signals: "no such table: users / nutrition_events" + "SQLite objects created in a thread..." / check_same_thread/threadpool
  - Scope: tests/conftest + tests/test_nutrition_log_api.py (bootstrap ordering) + minimal agent rule update (implemented in PR-629)
  - Links:
    - PR-629: <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/629>
    - CI nightly failed run: <https://github.com/Katsiarynakavaleuskaya/PulsePlate/actions/runs/21577239103>
    - Failing job (tests): <https://github.com/Katsiarynakavaleuskaya/PulsePlate/actions/runs/21577239103/job/62166939568>
  - DoD:
    - `pytest -q tests/test_nutrition_log_api.py` passes in CI runner
    - No "no such table: users" or "no such table: nutrition_events" in setup/teardown
    - Fail-fast guard: if schema missing after init_db(), tests fail with clear message (no silent warn+continue)
  - Notes (3 February 2026, America/New_York):
    - Fix: close leaked TestClients (context-managed `tests/conftest.py::client` + close in `tests/test_nutrition_log_api.py` teardown) to ensure lifespan runs deterministically under xdist.
    - Verification (local, 6 February 2026): `pytest -q tests/test_nutrition_log_api.py -n 2 --dist=loadgroup` passed on `main` (post-merge).
    - Verification (local, 6 February 2026): `pytest -q tests/test_db_engine_reuse_diff_coverage.py tests/test_sqlite_engine_sot.py` passed on `main`.


- [x] iOS: Guard test forbids placeholder API keys in app sources
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P0 (release safety)
  - Target PR: PR-657
  - Status: ✅ Merged (PR-657, 2026-02-06)
  - Reason: Prevent accidental shipping of placeholder keys like `test_pro_key` in iOS sources; enforce via CI.
  - Links:
    - `ios/PulsePlate/Services/ProKeyProvider.swift`
    - `ios/PulsePlateTests/Guards/ThinClientGuardsTests.swift` (existing guard pattern)
  - DoD:
    - A deterministic guard/unit test fails CI if placeholder key strings appear in `ios/PulsePlate/**`
    - Test excludes fixtures/mocks as needed (no false positives)
    - Documented allowlist policy (if any) in `ios/AGENTS.md`


- [x] iOS: Remove placeholder PRO key fallback and implement release-safe key storage
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P0 (release safety)
  - Target PR: PR-656
  - Status: ✅ Merged (PR-656, 2026-02-06)
  - Reason: `ProKeyProvider` previously contained a placeholder fallback (`test_pro_key`) in DEBUG. This is not release-safe and can mask missing-key flows in development and tests.
  - Links:
    - `ios/PulsePlate/Services/ProKeyProvider.swift`
    - `ios/PulsePlate/Services/KeychainStore.swift`
    - `docs/IOS_API_INTEGRATION.md`
  - DoD:
    - No placeholder key strings are returned by any provider (dev or prod)
    - Key retrieval uses a secure source (Keychain-backed or explicit developer-only injection that cannot ship)
    - Missing-key path is explicit and testable (UI/service fails with clear error, not silent fallback)
    - iOS tests updated / added for missing-key behavior (deterministic)


- [x] PR-653 P0 Welcome onboarding gate (iOS-only)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P0
  - Target PR: PR-653
  - Status: ✅ Merged (PR-653, 2026-02-06)
  - Reason: Store readiness — ensure deterministic first-run value framing with a single entry gate (`has_seen_welcome_v1`) before `RootTabs()`.
  - Links:
    - docs/audit/PR_653_P0_WELCOME_ONBOARDING_4SCREENS_AUDIT.md
    - Follow-up: PR-678 (tighten to 2 screens: Value + Usage)
  - DoD:
    - iOS entrypoint gates `RootTabs()` via `WelcomeGateView`
    - `@AppStorage("has_seen_welcome_v1")` persists completion (welcome shown once)
    - RU/EN/ES strings ship for `onboarding.welcome.*`
    - `make ios-test` passes


- [x] PR-616 Thin-proxy cleanup (helpers-1) — merged
  - Owner: @katsiaryna_kavaleuskaya
  - Target PR: PR-616
  - Status: ✅ Merged
  - Priority: P0
  - Branch: `chore/p1-thin-proxy-cleanup-helpers-1-new`
  - Reason: Architectural cleanup — move helpers out of `legacy_app.py` to restore "thin proxy only" invariant. Steps 1/2/3/4/6/7 complete (scheduler wrappers, utility helpers, feature flags, nutrition wrappers, fingerprint, dead BMI helpers). Step 5 (DB fallback) deferred to TP2.
  - Links:
    - docs/audit/PR_THIN_PROXY_CLEANUP_AUDIT.md
    - docs/pr/PR_THIN_PROXY_CLEANUP_PLAN.md
  - DoD:
    - ✅ Steps 1/2/3/4/6/7 complete (helpers moved to canonical modules)
    - ✅ Step 5 explicitly deferred to TP2 (DB fallback helpers remain in `legacy_app.py`)
    - ✅ `pytest -q` green (0 FAILED/ERROR)
    - ✅ Guard tests pass (`test_repo_policy_guards.py`, `test_no_legacy_bmi_helpers_request_path.py`)
    - ✅ No "tail" imports (`from app import normalize_flags|waist_risk` removed from tests)
    - ✅ Tests updated to use canonical functions (`core.bmi.engine`, `core.bmi.risk`)
    - ✅ All actionable items fixed (CodeRabbit/Cubic/Sourcery)
    - ✅ PR merged


- [x] PR-623 SQLite xdist dual-engine leak + hermetic tests + SoT reset — merged 2026-01-30
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P0 (infra)
  - Target PR: PR #623 (`fix/sqlite-xdist-threading-engine-sot`)
  - Status: ✅ Merged
  - Reason: Fix SQLite xdist dual-engine leak: single-engine SoT reset in fixture, hermetic tests when mutating env, NullPool gated to test/xdist via `make_url`, diff-coverage tests for protective branches. 97% threshold unchanged.
  - Links:
    - <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/623>
    - docs/CONTEXT_HANDOFF_2026-01-30.md
  - DoD:
    - ✅ SoT reset in fixture; hermetic engine reuse tests
    - ✅ NullPool only for file-based SQLite in test/xdist
    - ✅ diff-coverage tests for `_get_sqlite_poolclass` branches
    - ✅ CI green; guards pass


- [x] PR-627 xdist SQLite race conditions (table exists + no-table errors) — merged 2026-02-01
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P0 (infra)
  - Target PR: PR #627 (`fix/p1-sqlite-engine-sot`)
  - Status: ✅ Merged
  - Reason: Fix two independent xdist race conditions: (1) in-memory DB leak from `test_init_db` (no teardown → "no such table" in API tests), (2) fixture ordering race (duplicate `init_db()` + redundant `create_all()` → "table already exists").
  - Links:
    - <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/627>
    - docs/audit/PR_617_SQLITE_ENGINE_SOT_NIGHTLY_AUDIT.md
    - docs/CONTEXT_HANDOFF_2026-01-30.md
  - DoD:
    - ✅ Fix 1: `test_init_db` + `try/finally` cleanup (restore env + `reset_db_for_tests()`)
    - ✅ Fix 2: Explicit fixture dependency + remove redundant `create_all()`
    - ✅ Tests green under xdist -n 2 (targeted subset + full nutrition_log suite)
    - ✅ `make test-fast` passes (exit_code 0)
    - ✅ SoT guard test remains green (no regression)
    - ✅ CI green; PR merged


- [x] PR-TP2 Thin-proxy cleanup (DB fallback) — merged 2026-01-29 (PR #617)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P0
  - Target PR: PR #617 (`refactor/tp2-db-fallback`)
  - Status: ✅ Merged (squash merge SHA: 19e0b8f5; 2026-01-29)
  - Reason: High-risk cleanup — move DB fallback helpers from `legacy_app.py` to canonical module. Original target `core/db/fallback.py` caused `core.db` module/package collision in CI; amended to `core/db_fallback.py`.
  - Links:
    - PR #617
    - docs/pr/PR_TP2_DB_FALLBACK_PLAN.md
    - docs/audit/PR_TP2_DB_FALLBACK_AUDIT.md
    - docs/CONTEXT_HANDOFF_2026-01-29.md
  - Preconditions:
    - ✅ TP1 merged (helpers-1 cleanup complete)
  - DoD:
    - ✅ DB fallback in `core/db_fallback.py` (single source of truth; no package collision)
    - ✅ `legacy_app.py` thin proxy only (no DB fallback logic)
    - ✅ Tests rebound to `core.db_fallback`; guard tests pass (no guard exception)
    - ✅ OpenAPI unchanged; AGENTS.md + BACKLOG_LEDGER updated
    - ✅ CI green on PR #617 → merge → post-merge sanity


- [x] P0 CRITICAL SECURITY: VIP LLM hard monthly quota (deterministic enforcement)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P0 (CRITICAL security)
  - Target PR: PR-647 (security fix)
  - Status: ✅ Merged (PR-647)
  - Reason: VIP-only + rate limit prevent bursts but do not provide a monthly cost ceiling; without quota, sustained
    usage can still create an economic DoS. Policy requires a hard cost cap for LLM endpoints.
  - Links:
    - docs/policy/LLM_UNIT_ECONOMICS_GUARDRAILS.md
    - docs/audit/PR_646_VIP_ONLY_LLM_INSIGHT_AUDIT.md
    - docs/audit/PR_647_VIP_LLM_MONTHLY_QUOTA_AUDIT.md
    - PR-647: VIP LLM hard monthly quota (deterministic enforcement)
  - DoD:
    - Server-side authoritative quota per VIP key (requests/month OR tokens/month OR estimated cost/month)
    - Hard-stop before provider call when quota exceeded
    - Deterministic non-leaky error response on exceed (prefer `429`, e.g. `quota_exceeded`)
    - Tests:
      - VIP under quota → 200
      - VIP over quota → 429
      - FREE/PRO remain → 403
    - Minimal observability: counters/logging for usage and quota decisions


- [x] P0: Security hardening wave for agent automation
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P0
  - Target PR: PR #848 (docs/agent-sec-hardening-wave)
  - Status: ✅ Completed (PR #848, 2026-02-21, merge SHA `e7a58fb2`)
  - Area: security / runbooks / operations
  - Finding Type: incident prevention
  - Locations:
    - `docs/security/AGENT_CONTROL_PLANE_SECURITY_BASELINE.md`
    - `RUNBOOK_AGENT.md`
  - Reason: enforce short-lived credentials, rotation protocol, and secret persistence bans after local-agent incident.
  - Links:
    - `docs/runbooks/README.md`
  - DoD:
    - [x] Rotation protocol documented and adopted for bot/API/webhook credentials
    - [x] Security release gate conditions documented
    - [x] Mandatory controls mapped to owner and verification evidence
  - Evidence (2026-02-21): PR #848 merged
  - Blockers: None (closed)


### P0-A / P0-B

- [x] iOS: Tighten first-launch onboarding to Value + Usage (2 screens)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P0-B (release readiness)
  - Target PR: PR-678
  - Status: ✅ Merged (PR-678, 2026-02-07)
  - Reason: P0-B requires a minimal onboarding (≥2 screens). Keep the existing first-launch gate and tighten the flow to the two essential screens (Value + Usage) without adding networking/paywall/analytics.
  - Links:
    - `ios/PulsePlate/PulsePlateApp.swift`
    - `ios/PulsePlate/Welcome/WelcomeGateView.swift`
    - `ios/PulsePlate/Welcome/WelcomeFlowView.swift`
    - docs/audit/PR_678_IOS_ONBOARDING_VALUE_USAGE_AUDIT.md
    - <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/678>
  - DoD:
    - On first launch, onboarding shows before `RootTabs()` (gate remains at app entry)
    - On completion, onboarding is not shown again (`has_seen_welcome_v1` persists)
    - Onboarding is exactly 2 screens (Value + Usage)
    - RU/EN/ES strings updated for the 2 screens
    - `make ios-test` passes

- [x] P0-A: Stabilize web + iOS UX after Figma AI component integration regression
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P0-A (product works)
  - Target PR: PR #820 (Step 3 remediation)
  - Status: ✅ Merged (PR #820, 2026-02-19)
  - Reason: After recent Figma AI component/code updates, web UX quality regressed ("site looks bad"), and iOS app launch/open flow is broken. This blocks core product readiness and must be fixed before P1 work.
  - Links:
    - [PR #819](https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/819)
    - [PR #818](https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/818)
    - docs/runbooks/FIGMA_MCP_DESIGN_SYSTEM_RULES.md
    - frontend/ (affected UI surfaces, to be narrowed in triage)
    - ios/ (app-open failure triage scope)
  - Evidence (2026-02-19, America/New_York):
    - Step 1 (repro/verification):
      - `npm run test -- src/pages/__tests__/Home.test.tsx src/pages/__tests__/Plate.test.tsx src/pages/__tests__/Profile.test.tsx` -> `3 passed`
      - `npm run build` -> success (Vite build green)
      - `xcodebuild build -project PulsePlate.xcodeproj -scheme PulsePlate -destination "platform=iOS Simulator,id=8B9BF341-A44D-4BB0-A898-EC8CFEE56B79" -configuration Debug -derivedDataPath ../.derivedData` -> success
      - `xcodebuild test -project PulsePlate.xcodeproj -scheme PulsePlate -destination "platform=iOS Simulator,id=8B9BF341-A44D-4BB0-A898-EC8CFEE56B79" -configuration Debug -derivedDataPath ../.derivedData -skip-testing:PulsePlateUITests -only-testing:PulsePlateTests/PlateViewTests` -> success
    - Step 2 (root-cause isolation):
      - Web quality drift traced to presentation-layer style pattern drift in `frontend/src/pages/Home.tsx`, `frontend/src/pages/Plate.tsx`, `frontend/src/pages/Profile.tsx` (inline card styles / inconsistent CTA treatment vs tokenized runbook rules)
      - iOS "app does not open" not reproduced in deterministic simulator build/test path; high-risk touchpoints remain `ios/PulsePlate/Views/RootTabs.swift`, `ios/PulsePlate/Views/HomeView.swift`, `ios/PulsePlate/Views/ProgressView.swift`
  - Fixes applied by fact (merged remediation):
    - ✅ Web presentation fix merged: card/token class unification + CTA consistency updates in `frontend/src/pages/Home.tsx`, `frontend/src/pages/Plate.tsx`, `frontend/src/pages/Profile.tsx`
    - ✅ Step 3 implementation merged: [PR #820](https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/820)
    - ✅ CI/checks and review-thread gate closed before merge
  - DoD:
    - ✅ Repro steps captured for both regressions (web visual + iOS open failure)
    - ✅ Root cause identified with evidence (`file:line` + failing test/log)
    - ✅ Web UX restored to canonical design-system quality on affected screens
    - ✅ iOS app opens and core navigation works (Root/App entry flow validated in deterministic simulator flow)
    - ✅ Deterministic regression tests added/updated (web + iOS where applicable)
    - ✅ CI checks for touched surfaces pass; no unresolved review threads


### P1

<a id="ledger-p1-worker-proxy-hardening"></a>
- [x] P1: Lock down Cloudflare worker proxy before any public deployment
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR #1082 (`feat/p1-worker-proxy-hardening-pr`)
  - Related follow-up: PR #1087 (`fix/p0-app-package-bootstrap-alignment`)
  - Related follow-up status: ✅ Merged (PR #1087, 2026-03-10)
  - Related follow-up SHA: `4e5ce31a08ec03393f70b59d3c93b811edb43633`
  - Status: ✅ Merged evidence (PR #1082 bounded the worker runtime to first-party `/api/*` proxy use only; PR #1087 then re-aligned the `app` package bootstrap on `main` so additive public runtime/OpenAPI surfaces stay visible through `import app`)
  - Area: edge / Cloudflare / security
  - Finding Type: proxy abuse prevention
  - Reason: `worker.js` previously forwarded arbitrary paths with wildcard CORS and passed through `Authorization`. That edge gap is now closed on `main` by PR #1082: the worker remains supported, but is hardened into a bounded first-party API proxy with `/api/*` allowlisting, `GET/POST/OPTIONS` method scope, explicit `TARGET_BASE`, trusted origins via `WORKER_ALLOWED_ORIGINS`, bounded header forwarding, stripping/ignoring spoofable client-IP headers, and no wildcard CORS. This ledger item is therefore closed as merged evidence rather than carried as an active runtime lane.
  - Links:
    - `worker.js`
    - `docs/security/SECURITY_POSTURE.md`
    - `docs/deploy/PRODUCTION.md`
    - `tests/test_worker_proxy_contract.py`
    - `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1087`
    - `docs/review/PR_1087_FIXED_MAPPING.md`
  - DoD:
    - Worker path scope is allowlisted to `/api/*`
    - Worker method scope is allowlisted to `GET`, `POST`, and `OPTIONS`, with tests proving other verbs are rejected
    - Worker proxy tests prove `redirect: "manual"` remains enforced for upstream fetches
    - Wildcard CORS and header pass-through are removed or bounded to trusted origins
    - Authorization forwarding policy is documented and tested, and spoofable client-IP headers are stripped or ignored fail-closed
    - Deployment docs state that worker runtime is supported only as a bounded first-party proxy

<a id="ledger-p1-fitchef-phase1-wrapper"></a>
- [x] P1: FitChef Phase 1 wrapper
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-1055
  - Status: ✅ Merged (PR-1055, 2026-03-09)
  - Area: orchestration / backend runtime / coaching insight
  - Finding Type: execution anchor
  - Locations:
    - `app/services/fitchef_runtime.py`
    - `app/schemas/fitchef.py`
    - `app/routers/cbt_insight.py`
  - Reason: The approved FitChef rollout order keeps `cbt_insight` as the first surface, but Phase 1 still needs one internal orchestration source of truth before weekly-plan and shopping-list bindings can reuse it.
  - Links:
    - `docs/orchestration/FITCHEF_SANDBOX_INTEGRATION_PLAN.md`
    - `docs/orchestration/FITCHEF_SANDBOX_PHASE2_CONTRACT.md`
    - `docs/review/PR_1013_FIXED_MAPPING.md`
    - `docs/review/PR_1042_FIXED_MAPPING.md`
    - `docs/review/PR_1055_FIXED_MAPPING.md`
  - DoD:
    - Internal `fitchef-agent` wrapper exists under backend runtime with typed internal task envelope only
    - Existing `cbt_insight` public route delegates through the wrapper for `task_type=coach_insight`
    - Current request/response contracts remain unchanged for clients
    - Policy, quota, audit, RAG, and timeout ordering remain unchanged and regression-tested
  - Blockers: None

<a id="ledger-p1-fitchef-weekly-plan-binding"></a>
- [x] P1: FitChef weekly-plan task binding
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-1057
  - Status: ✅ Merged (PR-1057, 2026-03-09)
  - Area: orchestration / backend runtime / weekly planning
  - Finding Type: execution anchor
  - Locations:
    - `app/services/fitchef_runtime.py`
    - `app/schemas/vip.py`
    - `app/routers/vip.py`
    - `core/menu_engine.py`
  - Reason: After the internal FitChef wrapper lands, weekly-plan generation is the second approved Phase 1 task type and should reuse the same orchestration runtime instead of keeping planner orchestration embedded in the route layer.
  - Links:
    - `docs/orchestration/FITCHEF_SANDBOX_INTEGRATION_PLAN.md`
    - `docs/orchestration/FITCHEF_SANDBOX_PHASE2_CONTRACT.md`
    - `docs/review/PR_1042_FIXED_MAPPING.md`
    - `docs/review/PR_1057_FIXED_MAPPING.md`
  - DoD:
    - FitChef runtime supports `task_type=weekly_plan`
    - Existing weekly-plan VIP route delegates through the wrapper and stays thin
    - Current `WeeklyPlanRequest` and `WeeklyPlanResponse` contracts remain unchanged
    - VIP gate and planner behavior remain deterministic and regression-tested
  - Blockers: Depends on [P1: FitChef Phase 1 wrapper](#ledger-p1-fitchef-phase1-wrapper)

<a id="ledger-p1-fitchef-shopping-list-follow-up-binding"></a>
- [x] P1: FitChef shopping-list follow-up binding
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-1058
  - Status: ✅ Merged (PR-1058, 2026-03-09)
  - Area: orchestration / backend runtime / shopping list
  - Finding Type: execution anchor
  - Locations:
    - `app/services/fitchef_runtime.py`
    - `app/routers/shopping_list_pro.py`
    - `app/schemas/shopping_list.py`
    - `app/core/shopping_list/generator.py`
  - Reason: The third approved Phase 1 task type is shopping-list follow-up, and the canonical integration target is `shopping_list_pro.py`, not the echo-style shoplist path under `vip.py`.
  - Links:
    - `docs/orchestration/FITCHEF_SANDBOX_INTEGRATION_PLAN.md`
    - `docs/orchestration/FITCHEF_SANDBOX_PHASE2_CONTRACT.md`
    - `docs/review/PR_1042_FIXED_MAPPING.md`
    - `docs/review/PR_1058_FIXED_MAPPING.md`
  - DoD:
    - FitChef runtime supports `task_type=shopping_followup`
    - Canonical shopping-list route delegates through the wrapper and preserves `ShoppingListRequest -> ShoppingListDTO`
    - XOR validation, unsupported-preferences handling, and tier-gate behavior remain unchanged and regression-tested
    - Legacy echo-style shoplist handling under `app/routers/vip.py` stays out of scope for this Phase 1 binding unless a follow-up PR explicitly promotes it
  - Blockers: Depends on [P1: FitChef Phase 1 wrapper](#ledger-p1-fitchef-phase1-wrapper)

<a id="ledger-p1-fitchef-web-brand-rollout"></a>
- [ ] P1: FitChef website brand rollout
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-TBD
  - Status: Planned
  - Area: design / frontend / marketing
  - Finding Type: brand rollout
  - Reason: PR4 only promotes the mascot seed pack, iOS runtime mirrors, and
    Figma reference handoff. Website hero composition, React variant adoption,
    and marketing surfaces must be promoted in a dedicated follow-up PR to avoid
    mixing brand-asset canon with website implementation.
  - Links:
    - `docs/design/FITCHEF_MASCOT_ASSET_CANON.md`
    - `docs/figma/FITCHEF_BRAND_REFERENCE_HANDOFF.md`
    - `frontend/src/assets/brand/`
  - DoD:
    - Website hero and onboarding sections use named FitChef mascot variants
    - Current `FitChefMascot` consumers migrate from legacy alias-only usage
      where appropriate
    - Marketing/storybook guidance reflects the same variant contract
    - `make verify` passes with updated web tests if consumers change
  - Blockers: Depends on repo mascot canon landing first

<a id="ledger-p1-fitchef-figma-production-sync"></a>
- [ ] P1: FitChef Figma production sync
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-TBD
  - Status: Planned
  - Area: design / Figma / governance
  - Finding Type: reference-lane promotion
  - Reason: PR4 keeps Figma as `reference_only` for mascot placement. A later
    PR may promote a governed sync flow once the repo mascot canon and web/iOS
    consumers stabilize.
  - Links:
    - `docs/figma/FITCHEF_BRAND_REFERENCE_HANDOFF.md`
    - `docs/design/FITCHEF_MASCOT_ASSET_CANON.md`
    - `docs/runbooks/FIGMA_MCP_DESIGN_SYSTEM_RULES.md`
  - DoD:
    - Figma files reference the named mascot variant pack without hidden source
      drift
    - Repo-to-Figma import/export policy is documented with explicit approvals
    - Any automated sync path remains bounded and reviewable
  - Blockers: Depends on repo mascot canon landing first

<a id="ledger-p1-fitchef-candidate-intake-visual-qa"></a>
- [ ] P1: FitChef candidate intake visual QA and selective promotion plan
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR #1556 (`docs/fitchef-candidate-visual-qa-matrix`)
  - Status: In review (PR #1556, opened 2026-04-28)
  - Area: design / brand / marketing assets
  - Reason: Figma intake board now contains 30 FitChef assets, but only 6
    repo-backed seed assets are canonical. Candidate/reference/rework assets
    need visual QA, marketing classification, localization/text-risk review,
    and selective promotion planning before any runtime use.
  - Links:
    - `docs/design/FITCHEF_MASCOT_ASSET_CANON.md`
    - `docs/figma/FITCHEF_BRAND_REFERENCE_HANDOFF.md`
    - Figma node `1473:2`
  - DoD:
    - Every candidate has one disposition: keep candidate, reference-only,
      needs-rework, reject, or promotion proposal
    - Embedded text and localization risk are recorded for each reviewed asset
    - Marketing-only assets are separated from runtime-safe assets
    - No candidate is added to frontend or iOS assets without a separate
      promotion PR

<a id="ledger-p1-users-surface-hardening"></a>
- [x] P1: Public users CRUD surface must be authenticated or explicitly retired
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-TBD-USERS-SURFACE-HARDENING -> PR #1038 (`fix/security-users-surface-hardening`)
  - Status: ✅ Merged (PR #1038, 2026-03-08)
  - Area: backend / auth / data protection
  - Finding Type: access-control gap
  - Reason: Docs-only closure after PR #1038. Repo truth is now explicit: `app/routers/users.py` retained internal app-level protection while PR #1038 hid `/api/v1/users*` from the canonical public OpenAPI/schema surface and added deny-path regression coverage for unauthenticated access.
  - Links:
    - `app/routers/users.py`
    - `app/main.py`
    - `tests/test_users_api.py`
    - `tests/test_users_router.py`
    - `docs/security/SECURITY_POSTURE.md`
    - `docs/review/PR_1038_FIXED_MAPPING.md`
  - DoD:
    - Route policy is decided explicitly: protect with admin/API-key dependency, move behind internal-only surface, or remove if unused
    - OpenAPI and tests reflect the chosen access contract
    - Destructive operations require authenticated/authorized access
    - Docs-only closure keeps ledger state aligned with merged repo truth

- [x] P1: `simple_rag` shared index thread-safety hardening
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (runtime reliability)
  - Target PR: PR #1010
  - Status: Done (merged in PR #1010)
  - Reason: Thread-safe initialization/refresh semantics and regression coverage were implemented and merged with the Wave 4 runtime closure.
  - Links:
    - `docs/contracts/RAG_CONTRACT.md`
    - `docs/audit/RAG_IMPLEMENTATION_AND_AGENT_KNOWLEDGE_AUDIT.md`
    - `core/rag/simple_rag.py`
    - `tests/test_rag_simple.py`
    - `tests/test_insight_rag_response_fields.py`
  - DoD:
    - Deterministic thread-safe index initialization strategy is implemented (no double-init races)
    - Concurrency tests cover parallel read/init behavior
    - No regression in insight response contract or latency envelope


- [x] P1: RAG contract implementation (sources[], confidence, budget constants)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (AI / RAG)
  - Target PR: PR #935
  - Status: ✅ Merged (PR #935, 2026-02-27)
  - Reason (EN): Implement response schema and internal RAGContext/RAGChunk per `docs/contracts/RAG_CONTRACT.md`; add `sources[]`, `confidence`, `rag_used`, `hops`, `latency_ms` to Insight response; add `core/rag/contracts.py` and `rag_constants.py`.
  - Links:
    - `docs/contracts/RAG_CONTRACT.md`
    - `docs/audit/RAG_IMPLEMENTATION_AND_AGENT_KNOWLEDGE_AUDIT.md`
    - `legacy_app.py` (InsightResponse, insight_v1/insight)
  - DoD:
    - InsightResponse (or extended schema) includes sources, confidence, rag_used, hops, latency_ms
    - RAGChunk/RAGContext dataclasses in core/rag; constants in core/rag
    - Deterministic tests for new response fields; `make verify` passes


- [x] P1: RAG feedback storage (prerequisite for recursive learning)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (AI / RAG / DB)
  - Target PR: PR #937 (merged)
  - Status: ✅ Merged (PR #937, 2026-02-28)
  - Reason (EN): Recursive learning and adaptive personalization in BACKLOG require persistent feedback. Add `rag_feedback` table (and `user_knowledge` for VIP); application-layer RLS; migration.
  - Links:
    - `docs/contracts/RAG_CONTRACT.md` (Feedback Schema)
    - `docs/audit/RAG_IMPLEMENTATION_AND_AGENT_KNOWLEDGE_AUDIT.md` (sect. 5.2, 6.2)
    - `docs/db/rag_feedback_schema.md` (schema documentation)
  - DoD:
    - Migration for rag_feedback and user_knowledge tables
    - PII redaction via `core/pii_redaction.py` before storage
    - Application-layer security (user_id filtering); DB RLS deferred to project-wide PR
    - docs/db schema doc created
    - `make verify` passes


- [x] Eliminate import-time ORM/model imports in routers included in OpenAPI generation
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (determinism / import hygiene)
  - Target PR: PR-631
  - Status: ✅ Merged (PR-631, 2026-02-03)
  - Reason: OpenAPI generation must be side-effect free: routers reachable from `app.main:app` must not import ORM models at module import time.
  - Evidence:
    - `app/routers/nutrition_log.py:26-73` (TYPE_CHECKING-only model import + runtime lazy import pattern)
    - `scripts/generate_openapi.py:114-120` (imports canonical entrypoint and calls `app.openapi()` successfully)
  - DoD: ✅ Completed (PR-631)
    - ORM model imports moved to runtime (inside handlers/dependencies), preserving OpenAPI determinism
    - OpenAPI generation works with routers enabled
    - Determinism test stays green


- [x] P1: Extract import-safe ORM model helper for OpenAPI path (dedupe lazy-import pattern)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (maintainability / import hygiene)
  - Target PR: PR #746 (merged `5ccf83f5`)
  - Status: ✅ Completed (PR #746)
  - Resolution: PR-746 extracted `app/openapi/orm_imports.py` with `get_nutrition_event_model()`,
    `_lazy_import_attr()` helper, and `_ORM_IMPORT_CACHE` (idempotent, lock-free).
    `nutrition_log.py` now uses a single `_nutrition_event_model()` wrapper that delegates to
    the centralized helper. Guard test `test_openapi_import_safe_orm_guard.py` validates
    import-safety and caching behavior.
  - Evidence:
    - `app/openapi/orm_imports.py:43-60` — `get_nutrition_event_model()` with lazy cache
    - `app/routers/nutrition_log.py:19` — `from app.openapi.orm_imports import get_nutrition_event_model`
    - `app/routers/nutrition_log.py:41-47` — `_nutrition_event_model()` typed wrapper
    - `tests/test_openapi_import_safe_orm_guard.py` — guard test for import-safety + cache
  - DoD:
    - [x] Add a single helper (import-safe) for model retrieval used by `nutrition_log` (and any similar routers)
    - [x] Unit test that validates helper is import-safe (no import-time `app.models.*` in OpenAPI path)
    - [x] No runtime behavior change (pure refactor)


- [x] Restore full OpenAPI schema (remove temporary schema-only mode)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (contract velocity)
  - Target PR: PR-631
  - Status: ✅ Merged (PR-631, 2026-02-03)
  - Reason: Schema-only OpenAPI mode reduced thin-client contract velocity. PR-631 removed the schema-only seam and enabled full-schema generation with deterministic output.
  - Evidence:
    - `scripts/generate_openapi.py:94-109` (FULL schema mode; enables feature-flagged routers in generator context)
    - `tests/test_openapi_determinism.py:17-55` (asserts key PRO/business paths exist)
  - DoD: ✅ Completed (PR-631)
    - OpenAPI generator runs in full-schema mode (no schema-only marker)
    - `frontend/src/api/openapi.json` + `frontend/src/api/schema.ts` in sync (`make openapi` produces no diff)
    - Determinism test remains green


- [x] API Tiers database lookup implementation
  - Owner: @katsiaryna_kavaleuskaya
  - Target PR: PR-721
  - Status: ✅ Merged (PR-721, 2026-02-12)
  - Priority: P1
  - Area: backend
  - Finding Type: TODO/FIXME
  - Locations:
    - `app/middleware/api_tiers.py` — DB lookup + env fallback (MISS only); ERROR/INVALID_TIER fail-closed
  - Reason: Previously env-only; now DB-first when SUBSCRIPTION_DB_ENABLED=true with explicit fail-closed policy.
  - Links:
    - docs/audit/PR_585_BACKLOG_SWEEP_AUDIT.md
    - docs/audit/PR_XXX_API_TIERS_DB_LOOKUP_AUDIT.md (audit in PR-721)
  - DoD:
    - Database lookup implemented when SUBSCRIPTION_DB_ENABLED=true ✅
    - Fallback to env-based detection only on DB MISS (not on ERROR/INVALID_TIER) ✅
    - Tests cover both paths ✅


- [x] Backend: Make VIP insight guard tests CI-deterministic
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (CI stability)
  - Target PR: PR-658
  - Status: ✅ Merged (PR-658, 2026-02-06)
  - Reason: VIP insight guard tests should validate tier gating (403/200) without coupling to provider/quota internals, avoiding CI flakiness.
  - Links:
    - `tests/test_insight_vip_guard_api.py`
    - PR-658
  - DoD:
    - Tests patch quota/provider paths deterministically
    - `diff-coverage` passes on PRs touching these guard tests


- [x] Fix test skips/xfails (batch) — completed in PR-602
  - Owner: @katsiaryna_kavaleuskaya
  - Target PR: PR-602
  - Status: ✅ Completed (remediated-by-removal for invalid/non-contract tests + traced skip)
  - Priority: P1
  - Area: backend / tests
  - Finding Type: skip/xfail
  - Locations:
    - `tests/test_bmi_visualization.py:523` — xfail → **removed**
      - Reason: deterministic failure under `--runxfail` (404); test expected a legacy route to be mounted.
        Classified in PR-600 as **invalid test / route wiring mismatch** (non-contract).
    - `tests/test_app_branching_and_errors.py:185` — xfail → **removed**
      - Reason: reload-dependent internal symbol assertions (`importlib.reload(app)` → symbols become `None`) are not a stable contract.
        Classified in PR-600 as **invalid / environment-dependent assumption**.
    - `tests/test_repo_policy_guards.py:85` — skip (sys.modules cleanup) → **kept skipped**, but reason now explicitly tied to ledger + PR-600 (no behavior change).
  - Reason: Technical debt from remediation; tests disabled to unblock CI
  - Links:
    - docs/audit/PR_600_QUALITY_TESTS_AUDIT.md
    - docs/audit/PR_585_BACKLOG_SWEEP_AUDIT.md
    - docs/audit/BACKEND_XFAILED_TESTS_AUDIT.md
  - DoD:
    - Each xfail/skip either fixed or removed (if obsolete)
    - Tests pass without xfail markers
    - CI green


- [x] P1: Async SQLAlchemy wiring for day shoplist tests
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-742
  - Status: ✅ Merged (PR-742, 2026-02-14)
  - Resolution note: Removed async-config SKIPs; isolated `DATABASE_USE_ASYNC` via
    `monkeypatch`; reset async engine/session globals to prevent cross-test leakage;
    xdist validated on the target suite.
  - Area: backend / tests / infra
  - Finding Type: quality / infrastructure determinism
  - Locations:
    - `tests/test_shoplist_day_db_wiring.py:39`
    - `tests/test_shoplist_day_db_wiring.py:112`
    - `tests/test_shoplist_day_db_wiring.py:180`
    - `tests/test_shoplist_day_db_wiring.py:222`
  - Reason: Async DB tests should be deterministically configured (or removed as obsolete), not skipped by default.
  - Links:
    - `docs/audit/SKIPPED_TESTS_CLASSIFICATION_AUDIT_2026-02-13.md`
    - `core/db.py:613`
    - `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/742`
  - Evidence (2026-02-14):
    - `rg -n "Async SQLAlchemy not configured" tests` -> no matches
    - `rg -n "reload\\(core\\.db\\)|importlib\\.reload\\(core\\.db\\)" tests`
      -> no runtime matches
    - `pytest -q -n auto tests/test_shoplist_day_db_wiring.py` -> PASS
  - DoD:
    - ✅ No async-config SKIPs
    - ✅ xdist PASS on target suite
    - ✅ No `core.db` reload


- [x] P1: CP3 follow-up for skip-heavy coverage drift cleanup
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR #791 (`feat/cp3-skip-drift-execution`)
  - Status: ✅ Merged (PR #791, 2026-02-18)
  - Area: backend / tests / contracts
  - Finding Type: drift / contract mismatch
  - Locations:
    - `tests/test_zero_coverage_modules.py`
    - `tests/test_remaining_modules.py`
    - `tests/test_final_core_coverage.py`
    - `tests/test_direct_core_functions.py`
    - `tests/test_quick_coverage_boost.py`
  - Reason for deferral: CP3 was intentionally split out from PR-773 to keep CP1+CP2 merge-safe and avoid scope creep in a test-only stabilization package.
  - Links:
    - `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/791`
    - `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/773`
    - `docs/audit/SKIPPED_TESTS_CLASSIFICATION_AUDIT_2026-02-13.md`
    - `docs/audit/CP3_SKIP_HEAVY_A1_NOOP_AUDIT_2026-02-16.md`
    - `docs/plan/CP3_SKIP_COVERAGE_DRIFT_PLAN.md`
    - `docs/plan/PR_CP3_SKIP_DRIFT_TASK_ANALYSIS.md`
    - `docs/plan/PR_CP3_SKIP_DRIFT_EXECUTION_PLAN.md`
    - `docs/audit/PR_CP3_SKIP_DRIFT_AUDIT.md`
    - `docs/audit/PR_CP3_SKIP_DRIFT_PR_BODY_SKELETON.md`
    - `core/food_apis/unified_db.py:265`
  - Merge SHA: `2ea565ddf2c16ead430a1f1aa6770fade88d22bd`
  - DoD:
    - CP3 buckets are implemented in a dedicated follow-up PR with explicit mapping by test file.
    - Remaining intentional skips are documented as product decisions with canonical feature keys.
    - No ad-hoc skip reasons are introduced; skip protocol remains `feature_disabled:<key>`.
    - `make verify` passes in the CP3 execution PR.


- [x] P1: Execution Wave 2 — Search modernization (Meili/TypeSense) + API compatibility
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR #891, PR #893, PR #898, PR #900
  - Status: ✅ Merged (W2-A/W2-B/W2-C + barcode hit contract in PR #900, 2026-02-25)
  - Area: backend / search / API
  - Finding Type: performance and UX improvement
  - Reason: Local-first indexed search is required for predictable low latency and better discoverability while preserving client compatibility.
  - Links:
    - `docs/architecture/FOOD_DATABASE_PLATFORM_STRATEGY_v1.md`
    - `docs/audit/PR_898_FOOD_DB_W2_C_LATENCY_BENCHMARK.md`
    - `scripts/benchmarks/food_api_latency_benchmark.py`
    - `app/routers/foods.py`
    - `app/services/food_store.py`
    - `tests/test_food_store_service.py`
    - `tests/test_foods_router_additional.py`
  - DoD:
    - Existing `/api/v1/foods` contracts remain stable
    - New search backend is integrated behind compatibility layer
    - New endpoints contract for barcode/search filters is documented and tested
    - Target local-first search latency budget (<50ms p50) is measured and reported


<a id="ledger-p2-meili-client-maintainability-followup-pr1333"></a>
- [x] P2: Meilisearch client shared-helper / config refactors (deferred from PR #1333)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR #1340
  - Status: ✅ Merged (PR #1340, 2026-04-05). Foods-index request shape consolidated in `app/services/search_meili.py` (`MEILI_FOODS_ATTRIBUTES_TO_RETRIEVE`, `build_meili_foods_search_url`, `build_meili_foods_search_headers`, `build_meili_foods_search_payload`); `/api/v1/foods*` contracts unchanged. Evidence: `docs/review/PR_1340_FIXED_MAPPING.md`, `tests/test_food_search_foundation.py`.
  - Reason (EN): PR #1333 intentionally limits scope to env-gated Meilisearch performance telemetry and Prometheus metrics; maintainability refactors noted in review stay out of the telemetry slice.
  - Links:
    - `app/services/search_meili.py`
    - `app/metrics.py`
    - `docs/review/PR_1340_FIXED_MAPPING.md`
  - DoD:
    - Duplicated Meili request configuration is consolidated where safe without changing `/api/v1/foods*` response contracts.
    - `make verify` passes on the follow-up PR.


- [x] P1: Execution Wave 3 — Restaurant menus + controlled user submissions
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR #895 (+ follow-up PR #901, `feat/food-db-w3b-menustat-provenance-closure`)
  - Status: ✅ Merged (W3-A in PR #895 + W3-B closure in PR #901, 2026-02-25)
  - Area: backend / data model / partner enablement
  - Finding Type: product coverage expansion
  - Reason: Product/restaurant database coverage and controlled data intake are required to reduce manual entry and support partner menu flows.
  - Links:
    - `docs/architecture/FOOD_DATABASE_PLATFORM_STRATEGY_v1.md`
    - `docs/design/RESTAURANT_INTEGRATION_SPEC.md`
    - `docs/roadmap/BACKLOG_LEDGER.md` (P2 Vision: Restaurant/chef integration)
    - `app/routers/restaurants.py`
    - `app/services/restaurant_store.py`
    - `app/schemas/restaurants.py`
  - DoD:
    - MenuStat baseline ingestion is operational
    - Restaurant menu schema and endpoints are documented
    - Moderated user submission workflow is implemented (`pending/approved/rejected`)
    - Source audit trail persists provenance for imported and moderated records


- [x] P1: Execution Wave 3-C — operational MenuStat bootstrap importer
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR #904 (`feat/food-db-w3d-menustat-importer`)
  - Status: ✅ Merged (PR #904, 2026-02-25)
  - Area: backend / ingestion operations / restaurant coverage
  - Finding Type: operational gap closure
  - Reason: Restaurant endpoints and storage contracts exist, but local environments need a deterministic, repeatable import command to seed menu data from MenuStat-style snapshots without manual DB editing.
  - Links:
    - `scripts/import_restaurant_menu.py`
    - `data/restaurant_menu_sample.csv`
    - `tests/test_import_restaurant_menu_script.py`
    - `app/services/restaurant_store.py`
    - `docs/architecture/FOOD_DATABASE_PLATFORM_STRATEGY_v1.md`
  - DoD:
    - CLI importer loads MenuStat-style CSV with alias mapping into canonical restaurant tables
    - Importer supports explicit snapshot date and source name for provenance
    - Deterministic sample dataset exists for local bootstrap and tests
    - End-to-end test verifies import command populates searchable chain/menu records


- [x] P1: Execution Wave 3-E — approved submission promotion to canonical restaurant menu
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR #908 (`feat/food-db-wave3e-submission-promotion`)
  - Status: ✅ Merged (PR #908, 2026-02-25)
  - Area: backend / moderation workflow / restaurant coverage
  - Finding Type: correctness gap closure
  - Reason: Moderated submissions reached `approved`, but approved restaurant-menu submissions were not deterministically promoted into canonical `restaurant_menu_items`, creating a product/database gap for local-first lookup.
  - Links:
    - `app/services/restaurant_store.py`
    - `tests/test_restaurant_store_service.py`
    - `docs/architecture/FOOD_DATABASE_PLATFORM_STRATEGY_v1.md`
  - DoD:
    - `approved` submissions with `entity_type=restaurant_menu` are promoted into canonical menu rows in the same transaction scope
    - Re-approving already approved submissions is idempotent (no duplicate promoted menu rows)
    - `rejected` submissions do not create menu rows
    - Promotion failures remain fail-closed (no partial moderation/audit state persisted)
    - Deterministic tests cover approved/rejected/idempotency/rollback behavior


- [x] P1: Feature TODO from runtime SKIPPED suites (optional modules manifest)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR #873 (merged `ab0b7cc1`)
  - Status: ✅ Completed (PR #873)
  - Resolution: PR-873 delivered `tests/feature_manifest.py` with `FEATURE_TODO_KEYS` frozenset,
    `require_feature()` and `require_feature_or_raise()` helpers, and migrated 22 ad-hoc
    `pytest.skip()` calls to standardized `feature_disabled:<key>` format across 3 test files.
    Two modules (`shoplist_helpers`, `aliases_module`) were enabled and removed from gated keys.
    Remaining 16 gated keys are tracked in the "Unimplemented feature keys backlog" item below.
  - Area: backend / tests / feature debt management
  - Finding Type: technical debt / optional-feature protocol
  - Source of truth command:
    - `pytest -q -rs | rg -n "SKIPPED \\[" || true`
  - Feature TODO keys (aggregated from runtime SKIPPED):
    - `core_db`: `tests/test_database_apis_coverage.py:43`,
      `tests/test_direct_core_functions.py:353`
    - `food_apis`: `tests/test_database_apis_coverage.py:62`,
      `tests/test_database_apis_coverage.py:82`,
      `tests/test_database_apis_coverage.py:102`
    - `unified_db`: `tests/test_database_apis_coverage.py:124`,
      `tests/test_final_coverage_97_boost.py:139`
    - `update_manager`: `tests/test_database_apis_coverage.py:151`,
      `tests/test_final_coverage_97_boost.py:167`,
      `tests/test_final_coverage_97_boost.py:179`,
      `tests/test_update_manager_fixed.py:129`
    - `planner_engines`: ✅ Enabled (see entry below); renamed residual key to `planner_engines_advanced`
    - `planner_engines_advanced`: ✅ Enabled (see entry below)
    - `i18n_advanced`: `tests/test_database_apis_coverage.py:306`,
      `tests/test_direct_core_functions.py:234`
    - `rag`: `tests/test_database_apis_coverage.py:333`,
      `tests/test_direct_core_functions.py:320`,
      `tests/test_quick_coverage_boost.py:269`
    - `region_catalog`: `tests/test_direct_core_functions.py:396`
    - `exports_recipes_products`: `tests/test_zero_coverage_modules.py:90`,
      `tests/test_zero_coverage_modules.py:144`,
      `tests/test_zero_coverage_modules.py:190`,
      `tests/test_zero_coverage_modules.py:239`,
      `tests/test_zero_coverage_modules.py:275`
    - `sports_disclaimers_lifestage`: `tests/test_zero_coverage_modules.py:45`,
      `tests/test_zero_coverage_modules.py:313`,
      `tests/test_zero_coverage_modules.py:345`
    - `legacy_bmi_removed`: `tests/test_app_coverage_unit_combined.py:83`,
      `tests/test_app_coverage_unit_combined.py:88`
  - Protocol:
    - Any runtime skip reason matching `module not available` /
      `advanced features not available` MUST map to one feature key above.
    - No ad-hoc skip reasons for optional modules in high-noise suites.
    - Follow-up execution PR introduces `tests/feature_manifest.py` and a shared
      `require_feature(...)` helper for standardized skip reasons.
  - Links:
    - `docs/audit/SKIPPED_TESTS_CLASSIFICATION_AUDIT_2026-02-13.md`
    - `tests/test_database_apis_coverage.py`
    - `tests/test_direct_core_functions.py`
    - `tests/test_final_core_coverage.py`
    - `tests/test_quick_coverage_boost.py`
    - `tests/test_zero_coverage_modules.py`
  - DoD:
    - [x] `tests/feature_manifest.py` exists with SoT feature keys and env opt-in
      (`PULSEPLATE_FEATURES=all` or CSV list).
    - [x] High-noise suites use shared helper instead of custom ad-hoc skip strings.
    - [x] Runtime `pytest -q -rs` output shows standardized skip reasons with feature keys.
    - [x] Feature keys in tests and ledger remain one-to-one mapped.
  - Evidence:
    - `tests/feature_manifest.py` — `FEATURE_TODO_KEYS` frozenset + `require_feature()` + `require_feature_or_raise()`
    - `tests/test_simple_coverage_fixed.py` — 8 calls migrated to `require_feature_or_raise()`
    - `tests/test_specific_core_modules.py` — 2 calls migrated; `aliases_module` gates removed
    - `tests/test_plate_targets_micro_coverage.py` — 11 calls migrated (`plate_day_micros` key)


- [x] P1: Food barcode hit contract normalization for canonical FoodItem response
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR #900 (`fix/food-barcode-hit-contract`)
  - Status: ✅ Merged (PR #900, 2026-02-25)
  - Area: backend / API contract / data normalization
  - Finding Type: correctness and reliability gap
  - Reason: `GET /api/v1/foods/barcode/{barcode}` can fail on hit-path serialization when persisted `flags` payload is string-encoded instead of a list, causing non-deterministic hit-path behavior in benchmark and runtime.
  - Links:
    - `app/routers/foods.py`
    - `app/schemas/food.py`
    - `docs/audit/PR_898_FOOD_DB_W2_C_LATENCY_BENCHMARK.md`
  - DoD:
    - Barcode hit path returns `200` with valid `FoodItem` serialization on canonical seeded DB
    - `flags` storage/parse contract is normalized and backward-compatible
    - Deterministic tests cover hit/miss/malformed barcode paths


- [x] P1: Post-stabilization drift cleanup for skip-heavy coverage suites
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-773
  - Status: ✅ Merged (PR-773, 2026-02-16)
  - Area: backend / tests / contracts
  - Finding Type: drift / contract mismatch
  - Locations:
    - `tests/test_database_apis_coverage.py`
    - `tests/test_direct_core_functions.py`
    - `tests/test_final_core_coverage.py`
    - `tests/test_final_coverage_97_boost.py`
    - `tests/test_quick_coverage_boost.py`
    - `tests/test_remaining_modules.py`
    - `tests/test_zero_coverage_modules.py`
  - Reason: Large skip bucket (`module/symbol not available`) is mostly contract drift between legacy test expectations and current canonical APIs.
  - Links:
    - `docs/audit/SKIPPED_TESTS_CLASSIFICATION_AUDIT_2026-02-13.md`
    - `core/food_apis/unified_db.py:265`
    - `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/773`
  - Merge SHA: `3404ca39`
  - Notes: CP1+CP2 done in PR-773; CP3 deferred to a separate follow-up PR.
  - DoD:
    - Drift-based skips are reduced via canonical test alignment (not API inflation for coverage)
    - Signature mismatches are resolved with explicit contract assertions
    - Remaining intentional skips are documented as product decisions
    - `make verify` passes in PR-732


<a id="ledger-p1-reenable-sys-modules-guard"></a>
- [x] P1: Re-enable repository `sys.modules` mutation guard
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-732
  - Status: ✅ Merged (PR-732, 2026-02-13, `b36e88ed`)
  - Area: backend / tests / policy guards
  - Finding Type: quality / guard enforcement
  - Locations:
    - `tests/test_repo_policy_guards.py:98` — active runtime guard
      (`test_no_sys_modules_mutation_in_repo`)
  - Reason: Disabled guard weakens a known import-hygiene invariant and can hide dual-module regressions.
  - Links:
    - `docs/audit/SKIPPED_TESTS_CLASSIFICATION_AUDIT_2026-02-13.md`
    - `tests/test_repo_policy_guards.py:98`
    - `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/732`
  - Evidence (2026-02-13):
    - `pytest -q tests/test_repo_policy_guards.py -rs` -> pass (guard enabled, not skipped)
  - DoD:
    - Guard is enabled in CI (not skipped)
    - Offenders are cleaned up or explicitly phased with a documented allowlist plan
    - Guard remains deterministic under xdist and normal pytest runs
    - `make verify` passes in PR-732


- [x] P1: Shoplist flow stabilization work-package (`plan -> shoplist`)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR #770
  - Status: ✅ Merged (PR #770, 2026-02-16, `c54143ab`)
  - Merge SHA: c54143abee6568f42443822f9a6cb47b17edbbc4
  - Area: backend / contracts / integration tests
  - Finding Type: delivery packaging / flow contract
  - Reason: Move from micro-PR fragmentation to one scoped runtime package delivering a full user-visible flow outcome with deterministic tests and rollback.
  - Links:
    - `docs/audit/PR_SHOPLIST_FLOW_STABILIZATION_WORK_PACKAGE_PLAN.md`
    - `docs/audit/PR_764_SHOPLIST_HELPERS_ENABLE_AUDIT.md`
  - DoD:
    - One scoped runtime PR delivers `plan -> shoplist` end-to-end outcome
    - Contract tests cover 200 + key failure statuses where applicable
    - Integration happy path is deterministic
    - `Content-Type` and error envelope assertions are explicit
    - `make verify` passes and required CI checks are green


- [x] P1: Unimplemented feature keys backlog (SoT = tests/feature_manifest.py)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-748
  - Status: ✅ Complete (22 total enabled, 0 remaining)
  - Area: backend / tests / feature debt management
  - Finding Type: product feature debt / runtime skip protocol
  - Reason for deferral: Runtime skip reasons are now standardized via
    `feature_disabled:<key>`, but implementation work for gated features remains
    deferred to focused execution PRs.
  - Source of truth command:
    - `pytest -q -rs | rg -n "feature_disabled:" || true`
  - Links:
    - `tests/feature_manifest.py`
    - `docs/audit/SKIPPED_TESTS_CLASSIFICATION_AUDIT_2026-02-13.md`
    - `docs/roadmap/BACKLOG_LEDGER.md` (this section)
  - DoD:
    - For each implemented feature key, remove/replace corresponding
      `require_feature(...)` gate in tests.
    - Runtime `feature_disabled:<key>` skip count decreases as features land.
    - Ledger item is updated with merged PR references per implemented key.
  - Implemented keys (latest):
    - `shoplist_helpers` -> ✅ Merged (PR-764, 2026-02-16, `48c87f39`); gate removed in PR-748
    - `aliases_module` -> ✅ Enabled (PR-748); core/aliases.py fully implemented
    - `update_manager` -> ✅ Enabled (PR-761, `0aa3c51b`); Path wrapper .path exposed in core/food_apis/update_manager.py; gates removed from 4 test locations (test_database_apis_coverage.py, test_final_coverage_97_boost.py, test_update_manager_fixed.py); key removed from FEATURE_TODO_KEYS
    - `region_catalog` -> ✅ Enabled (PR-762, `abed9a48`); stale feature gate removed from test_direct_core_functions.py; 1 test location cleaned; key removed from FEATURE_TODO_KEYS
    - `targets_fixture_data` -> ✅ Enabled (PR-877); gates removed from 3 test files (test_targets_coverage_97.py, test_core_coverage_97_final.py, test_simple_coverage_fixed.py)
    - `i18n_advanced` -> ✅ Enabled (PR-877); thin facades added to core/i18n.py (TranslationManager + 8 functions); gates removed from 4 test files
    - `rag` -> ✅ Enabled (PR-877); thin facades added to core/rag/simple_rag.py (RAGEngine/SimpleRAG + 6 functions); gates removed from 4 test files
    - `core_db` -> ✅ Enabled (PR-879); thin facades added to core/db.py (get_db, create_tables, init_database, get_unified_food_db); gates removed from 9 test files
    - `food_apis` -> ✅ Enabled (PR-879); thin facades added to core/food_apis/ (base.py, usda.py, openfoodfacts.py, scheduler.py); gates removed from 9 test files
    - `unified_db` -> ✅ Enabled (PR-879); thin facades added to core/food_apis/unified_db.py (UnifiedFoodDB, FoodSource, merge_food_sources, update_unified_db); gates removed from 9 test files
    - `utils_pack` -> ✅ Enabled (PR-880); thin facades added to core/utils.py (safe_float, safe_int, slugify, format_number, generate_id, sanitize_html, validate_email) and core/time_utils.py (parse_datetime, format_datetime, get_timezone_offset, is_valid_date, format_time, human_delta); gates removed from 4 test files
    - `weekly_plan_helpers` -> ✅ Enabled (PR-881); thin facades added to core/weekly_plan.py (calculate_weekly_nutrition, optimize_weekly_variety, validate_weekly_plan); gates removed from test_remaining_modules.py; 31 coverage tests added
    - `food_apis_error_injection` -> ✅ Enabled (PR-885, 2026-02-24, `2b724190`); fixed 5 test mocks in test_food_apis_coverage_errors.py (correct mock targets, UnifiedFoodItem constructors, errors list assertions); fixed _Sched2 global state leak in test_food_apis_push95.py; added USDA search error handling in unified_db.py; key removed from FEATURE_TODO_KEYS
    - `premium_week_router_mocking` -> ✅ Enabled (PR-888, 2026-02-24, `96c72345`); implemented 2 gated tests (503 make_weekly_menu unavailable, 500 exception handling); fixed PEP 562 `__getattr__` mock residual in `app.__dict__`; key removed from FEATURE_TODO_KEYS
    - `legacy_bmi_removed` -> ✅ Enabled (PR-891, 2026-02-24); implemented canonical PRO BMI functions in `core/bmi/engine.py`: `estimate_level()` (fitness experience level), `interpret_group()` (group interpretation with notes), `build_premium_plan()` (premium plan with nutrition/activity tips), `PremiumPlanResult` dataclass; added i18n keys for action/activity tips (ru/en/es); updated `bmi_core.py` shims to delegate; comprehensive tests added in `test_app_coverage_unit_combined.py`, `test_level_es.py`, `test_bmi_core_shim_diffcover.py`; key removed from FEATURE_TODO_KEYS
    - `nutrient_recommendations` -> ✅ Enabled (PR-894, 2026-02-25); added `get_nutrient_recommendations()` facade in `core/recommendations.py` wrapping `build_nutrition_targets()` with simplified API (age/gender/weight/height/activity_level); activity level mapping (low/moderate/high/very_high); 2 gated tests ungated + 1 edge-case test added in `test_final_coverage_97_boost.py`; key removed from FEATURE_TODO_KEYS
    - `nutrition_api_pr2_pro_endpoints` -> ✅ Enabled (PR-903, 2026-02-25, `aeb1b49a`); added 3 PRO endpoints under `/api/v1/pro/nutrition/`: `POST /deficiency-recommendations` (food-based recs for deficient nutrients, en/ru/es), `POST /micronutrient-targets` (extended micro targets with min/target/max per WHO/EFSA/DRI), `POST /safety-check` (validates nutrition targets against safety bounds); extended `ProfileInput` with optional fields (`goal`, `diet_flags`, `life_stage`, `deficit_pct`, `surplus_pct`, `bodyfat`); added Spanish (es) language support in food sources; 38 new tests (77 total) covering tier guards, contract assertions, validation errors; OpenAPI + TypeScript types regenerated
    - `planner_engines` -> ✅ Enabled (2026-02-25); added ~25 thin facade functions across 4 core modules: `core/targets.py` (calculate_bmr, calculate_tdee, validate_user_data + 4 stubs), `core/auto_repair.py` (analyze_deficiencies, get_repair_suggestions, calculate_repair_priority + 2 stubs), `core/menu_engine.py` (calculate_nutrition_totals, generate_shopping_list, optimize_meals, validate_meal_plan, suggest_meal_improvements), `core/plate.py` (create_nutrition_plate, analyze_plate_balance, get_plate_recommendations, calculate_plate_score, visualize_plate_data); rewrote `test_direct_core_functions.py` to remove feature gates (10 tests import directly); added 61 coverage tests in `test_planner_engines_facades.py`; renamed residual advanced key to `planner_engines_advanced`; key removed from FEATURE_TODO_KEYS
    - `planner_engines_advanced` -> ✅ Enabled (2026-02-25); added 2 new modules: `core/nutrition_analysis.py` (analyze_nutrition, calculate_nutrition_score, get_nutrition_recommendations, validate_nutrition_data), `core/config.py` (load_config, get_config_value, set_config_value, validate_config); removed feature gates from 6 tests in `test_final_core_coverage.py`; fixed test signatures to match implementations; added 26 coverage tests in `test_planner_engines_advanced_facades.py`; key removed from FEATURE_TODO_KEYS
    - `plate_day_micros` -> ✅ Enabled (PR-912, 2026-02-26); day_micros aggregation from meals already implemented in `legacy_app.py:_aggregate_day_micronutrients()` with fallback mechanism for missing recipe ingredients; removed 10 feature gates from `test_plate_targets_micro_coverage.py`; key removed from FEATURE_TODO_KEYS
    - `exports_recipes_products` -> ✅ Enabled (PR-TBD, 2026-02-26); added 24 thin facade functions across 5 core modules: `core/exports.py` (export_meal_plan, export_nutrition_report, generate_pdf_report, export_to_csv, export_shopping_list), `core/recipe_synth.py` (generate_recipe, synthesize_meal, create_recipe_variations, optimize_recipe_nutrition, suggest_substitutions), `core/product_finder.py` (find_products, search_by_nutrition, filter_by_criteria, get_product_info, compare_products), `core/product_varieties.py` (get_varieties, find_alternatives, group_by_category, suggest_similar, analyze_variety_nutrition), `core/exports_simple.py` (simple_csv_export, simple_json_export, simple_text_export, quick_meal_export); removed 5 feature gates from `test_zero_coverage_modules.py`; key removed from FEATURE_TODO_KEYS
    - `sports_disclaimers_lifestage` -> ✅ Enabled (PR-916, 2026-02-26); added 13 thin facade functions across 3 core modules: `core/sports_nutrition.py` (calculate_sports_targets, get_athlete_nutrition, adjust_for_training, hydration_needs), `core/lifestage_nutrition.py` (get_lifestage_requirements, adjust_for_age, pregnancy_nutrition, elderly_nutrition, child_nutrition), `core/disclaimers.py` (get_disclaimer, get_medical_disclaimer, get_nutrition_disclaimer, get_liability_disclaimer); removed 3 feature gates from `test_zero_coverage_modules.py`; key removed from FEATURE_TODO_KEYS; **last feature key enabled - FEATURE_TODO_KEYS now empty**
  - Keys still gated (module exists but tested API surface incomplete):
    - (none - all feature keys enabled)
  - Ad-hoc skip migration (PR-748):
    - 22 ad-hoc pytest.skip() calls migrated to require_feature() in 3 test files
    - 2 new feature keys added: `plate_day_micros`, `aliases_module` (then enabled)


- [x] P1: Wave 2 contract governance v2 + CI throughput program
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR #850 (docs/wave2-contract-governance-ci-throughput)
  - Status: ✅ Completed (PR #850, 2026-02-21, merge SHA `411c3159`)
  - Area: backend / frontend / ios / devex
  - Finding Type: maintainability / delivery speed
  - Locations:
    - `docs/contracts/CONTRACT_GOVERNANCE_V2_CHECKLIST.md`
    - `docs/policy/CI_THROUGHPUT_AND_FLAKE_BUDGET.md`
    - `docs/roadmap/WAVE_2_3_EXECUTION_PACK.md`
    - `docs/roadmap/PROGRAM_6M_BALANCED_2026H1.md`
  - Reason: reduce contract drift and CI critical-path latency while preserving quality gates.
  - Links:
    - `docs/roadmap/WAVE_2_3_EXECUTION_PACK.md`
    - `docs/roadmap/PROGRAM_6M_BALANCED_2026H1.md`
    - `docs/contracts/CONTRACT_GOVERNANCE_V2_CHECKLIST.md`
    - `docs/policy/CI_THROUGHPUT_AND_FLAKE_BUDGET.md`
  - DoD:
    - [x] Contract governance checklist with OpenAPI diff risk labels documented
    - [x] CI throughput baseline and target defined with flake budget owner
    - [x] Follow-up implementation PRs linked (deferred to Wave 2 CI enforcement phase)


- [x] P1: WebSocket foundation follow-up (realtime expansion package)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR #783
  - Status: ✅ Merged (PR #783, 2026-02-17, `a78040a0`)
  - Merge SHA: a78040a0d8a191876f702b426b98ae82ae9460cc
  - Area: backend / realtime / contracts
  - Finding Type: scope control / deferred enhancement
  - Reason: Current work-package intentionally delivers only secure websocket foundation (`/ws`, auth, limits, `ping -> pong`). Any expansion beyond foundation (event catalog, client consumers, rooms/fan-out) is deferred to avoid scope creep.
  - Links:
    - `docs/audit/PR_778_WEBSOCKET_FOUNDATION_AUDIT.md`
    - `docs/plan/PR_778_WEBSOCKET_FOUNDATION_PLAN.md`
    - `docs/audit/PR_WS_REALTIME_EXPANSION_AUDIT.md`
    - `docs/plan/PR_WS_REALTIME_EXPANSION_PLAN.md`
  - DoD:
    - Define versioned event contract for realtime payloads
    - Add client integration scope (web/iOS) without violating thin-adapter policy
    - Add deterministic integration tests for expanded event flow
    - Keep `make verify` and diff-coverage gates green in expansion PR


- [x] P1: WebSocket foundation work-package (`/ws` secure baseline)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR #778
  - Status: ✅ Merged (PR #778, 2026-02-17, `48ae6d24`)
  - Merge SHA: 48ae6d24458da4f0bb101b0c92d77e4607a6aded
  - Area: backend / realtime / security baseline
  - Finding Type: delivery packaging / transport foundation
  - Reason: Deliver one scoped realtime package with fail-closed auth, deterministic guardrails, and policy-anchored docs/tests without scope creep into client integration.
  - Links:
    - `docs/audit/PR_778_WEBSOCKET_FOUNDATION_AUDIT.md`
    - `docs/plan/PR_778_WEBSOCKET_FOUNDATION_PLAN.md`
    - `app/routers/realtime_ws.py`
    - `tests/test_websocket_security_api.py`
  - DoD:
    - `/ws` route is registered once in canonical app entrypoint and guarded against duplicates
    - WebSocket auth remains fail-closed with explicit policy close paths
    - Deterministic tests cover auth reject/accept, payload/limit guards, and disconnect path
    - Governance/docs are synchronized in AGENTS + audit + plan
    - CI gates for PR #778 are green before merge


<a id="ledger-p1-websocket-idle-timeout-follow-up"></a>
- [x] P1: WebSocket idle-timeout follow-up (capacity safeguard)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR #786
  - Status: ✅ Merged (PR #786, 2026-02-18, `a2e248cb`)
  - Merge SHA: a2e248cb5feaa84608acc68491954476228751d4
  - Area: backend / realtime / capacity
  - Finding Type: deferred hardening / runtime safeguard
  - Reason: PR #783 intentionally shipped secure websocket foundation (`/ws`, auth, limits, versioned events) without idle timeout to avoid scope creep. Remaining risk is capacity/resource retention from idle connections (not a security bypass).
  - Links:
    - `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/786`
    - `docs/audit/PR_WS_REALTIME_EXPANSION_AUDIT.md`
    - `docs/plan/PR_WS_REALTIME_EXPANSION_PLAN.md`
    - `docs/plan/PR_WS_IDLE_TIMEOUT_PLAN.md`
    - `docs/audit/PR_WS_IDLE_TIMEOUT_AUDIT.md`
    - `app/routers/realtime_ws.py`
  - DoD:
    - Add `WS_IDLE_TIMEOUT_SECONDS` with conservative default and explicit disable mode
    - Close idle websocket connections with deterministic policy close semantics
    - Add deterministic tests for idle-timeout behavior without `sleep()`-based flakiness
    - Keep existing websocket guardrails unchanged (fail-closed auth, burst limiter, connection cap)
    - Pass `make verify` and diff-coverage gates in follow-up PR


- [x] P1: WebSocket observability hardening (low-cardinality metrics + structured logs)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR #789
  - Status: ✅ Merged (PR #789, 2026-02-18, `7d9e74ec`)
  - Merge SHA: 7d9e74eca58841a120249f98db19880dc18c56e3
  - Area: backend / realtime / observability
  - Finding Type: operational hardening / incident response readiness
  - Reason: After deterministic idle-timeout delivery in PR #786, the remaining high-value runtime gap is operational visibility of `/ws` behavior under load. Without explicit websocket metrics and constrained structured logs, incident triage is slower and capacity regressions are harder to detect early.
  - Worst-case scenario: high-volume idle/malformed websocket traffic degrades service while missing or high-cardinality observability obscures root cause and delays mitigation.
  - Scope IN:
    - Add low-cardinality counters for websocket connect result and close reasons.
    - Add active websocket gauge aligned with tracker state.
    - Add message counters by allowlisted event type (`ping`, `subscribe`) and outcome (`ok`/`closed`).
    - Add structured logs for policy closes using non-sensitive fields only.
  - Scope OUT:
    - Product analytics, user-behavior funnels, and per-user telemetry.
    - New websocket protocol features/channels.
    - Frontend/iOS telemetry changes.
  - Guardrails:
    - Never log tokens, user IDs, raw payloads, or unbounded labels.
    - Metrics labels must remain low-cardinality and enum-bound.
  - Links:
    - `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/789`
    - `app/routers/realtime_ws.py`
    - `app/middleware/metrics.py`
    - `docs/audit/PR_WS_OBSERVABILITY_HARDENING_AUDIT.md`
    - `docs/plan/PR_WS_OBSERVABILITY_HARDENING_PLAN.md`
    - `docs/audit/PR_WS_IDLE_TIMEOUT_AUDIT.md`
    - `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/786`
  - DoD:
    - `ws_connect_total{result,reason}` and `ws_messages_total{type,result}` are implemented with bounded labels.
    - `ws_active_connections` gauge reflects tracker state without negative drift.
    - Structured websocket logs include only safe, bounded fields (`reason`, `event_type`, `version`, `result`).
    - Deterministic tests validate metric increments and no-`sleep()` time-based behavior.
    - `make verify` and diff-coverage gates are green in observability PR.


- [x] P1: Orchestration — document worktree isolation policy (agent worktree immutable to humans)
  - Owner: @katsiaryna_kavaleuskaya
  - Target PR: PR #963
  - Status: merged 2026-03-04 (79024d70)
  - Priority: P1
  - Area: dev-process / orchestration
  - Finding Type: operational policy
  - Reason: Agent works in its own worktree; a human edits the same files → merge conflicts → orchestration chaos. No explicit rule "human cannot edit agent worktree." Integration flow exists (PR promotion) but operational law is missing.
  - Links:
    - `docs/orchestration/AGENT_KNOWLEDGE_LIBRARY_WORKTREE_RUNBOOK.md`
    - `docs/plan/ORCHESTRATION_IMPROVEMENTS_PLAN_2026.md`
  - DoD:
    - Policy section added to runbook (worktree states: active/abandoned/merged; allowed human intervention via new branch)
    - Short hard-rule excerpt in root `AGENTS.md` (do not edit inside worktrees/; integration only via PR)
    - Example "human intervention via new branch" documented


- [x] P1: Home/Plate/Progress Figma sync and Code Connect bridge docs package
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR #798 (`docs/figma-hpp-sync-package`)
  - Status: ✅ Merged (PR #798, 2026-02-19)
  - Merge SHA: 891a3fcaaac3da351c104a3ebb164c4c02a126c3
  - Area: docs / design / orchestration
  - Finding Type: documentation contract delivery
  - Reason: Landed canonical H+P+Pr Figma sync protocols and Code Connect activation
    bridge docs with evidence anchors, bot-review remediations, and policy-aligned
    AGENTS updates; this closes the docs package while keeping Design URL/node ID
    activation dependency explicitly tracked as a separate open ledger item.
  - Links:
    - PR #798
    - `docs/figma/FIGMA_MAKE_SYNC_AUDIT_HPP.md`
    - `docs/figma/FIGMA_CODE_CONNECT_BRIDGE_HPP.md`
    - `docs/figma/FIGMA_CODE_CONNECT_MAPPING_CANDIDATES_HPP.md`
    - `docs/figma/FIGMA_DESIGN_URL_NODEID_CAPTURE_HPP.md`
    - `docs/figma/FIGMA_IMPLEMENTATION_RUNBOOK.md`
    - `AGENTS.md`
  - DoD:
    - Figma Make sync audit protocol committed with evidence anchors
    - Code Connect activation blocker protocol and mapping candidate registry committed
    - Design URL + node ID capture protocol committed
    - Orchestration session artifacts committed for the sync package
    - Root `AGENTS.md` updated with canonical Figma workflow protocol references


- [x] P1: PR #825 bot-comments + CI green closure checklist (matrix)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR #825 (`chore/6m-balanced-program-agent-control-plane-pr`)
  - Status: ✅ Merged (PR #825, 2026-02-20)
  - Area: docs / frontend / ci / review-ops
  - Finding Type: review remediation / quality-gate closure
  - Locations:
    - `frontend/src/lib/telemetry/eventRegistry.ts`
    - `frontend/src/lib/__tests__/telemetry.test.ts`
    - `docs/architecture/ADR-003-agent-control-plane-mvp.md`
    - `docs/roadmap/BACKLOG_LEDGER.md`
  - Reason: close all bot actionables and reach zero unresolved review threads with full CI green.
  - Links:
    - `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/825`
    - `docs/roadmap/WAVE_2_3_EXECUTION_PACK.md`
  - Checklist (Matrix):
    - [x] Sourcery actionables addressed with commit mapping in PR body
    - [x] CodeRabbit actionables addressed with file-level fixes and thread replies
    - [x] PR Body Phase2 gates passed after checklist/mapping update
    - [x] Docs Phase1 gates passed with evidence anchors in audit/security docs
    - [x] Required CI checks are green (`gh pr checks 825`)
    - [x] Unresolved review threads count is zero
  - DoD:
    - Sourcery actionables addressed with commit mapping in PR body
    - CodeRabbit actionables addressed with file-level fixes and thread replies
    - PR Body Phase2 gates pass after checklist/mapping update
    - Docs Phase1 gates pass with evidence anchors in audit/security docs
    - Required CI checks are green (`gh pr checks 825`)
    - Unresolved review threads count is zero


- [x] P1: RAG implementation audit — baseline (docs-only)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (AI / RAG / docs)
  - Target PR: PR #928 (merged)
  - Status: Done
  - Area: docs / audit
  - Reason (EN): Establish evidence-based baseline for current RAG (insight-only, Jaccard), backlog gaps (sources[], confidence, multi-hop, feedback storage, agent RAG), and prioritized follow-up. No runtime changes in this PR.
  - Links:
    - `docs/audit/RAG_IMPLEMENTATION_AND_AGENT_KNOWLEDGE_AUDIT.md`
    - `docs/contracts/RAG_CONTRACT.md`
    - `core/rag/simple_rag.py`, `legacy_app.py` (insight RAG paths)
  - DoD:
    - Audit and RAG contract docs merged in docs-only PR
    - BACKLOG_LEDGER updated with follow-up items below
    - Branch follows PR scope guard (docs only)


- [x] P1: Home/Plate/Progress live indicator + CTA instrumentation (web-first)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR #801 (`feat/hpp-live-indicator-cta`)
  - Status: ✅ Merged (PR #801, 2026-02-19)
  - Merge SHA: aec126d6b8757a7a413ebf051f5e7f8a917c3e42
  - Area: frontend / product-metrics / HPP UX
  - Finding Type: user-visible activation package
  - Reason: Deliver one narrow user-facing package that adds a live progress signal on
    Home/Plate/Progress, keeps strict static fallback when realtime transport is unavailable,
    and instruments CTA impression/click events for conversion measurement.
  - Links:
    - PR #801
    - `frontend/src/features/progress/LiveProgressIndicator.tsx`
    - `frontend/src/features/progress/useHppLiveIndicator.ts`
    - `frontend/src/lib/hppTelemetry.ts`
    - `frontend/src/pages/Home.tsx`
    - `frontend/src/pages/Plate.tsx`
    - `frontend/src/pages/Progress.tsx`
  - DoD:
    - Live indicator renders on Home, Plate, and Progress surfaces
    - Fallback invariant preserved (`ws unavailable/error -> static indicator + CTA works`)
    - CTA telemetry events (`impression`, `click`) emitted through centralized helper
    - Deterministic tests added for hook, indicator, and HPP page integration
    - Thin-client websocket guard remains green (`src/api/wsClient.ts` adapter boundary)


- [x] P1: Home/Plate/Progress live indicator A/B variant + telemetry enrichment
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR #803 (`feat/hpp-live-indicator-ab-variant`)
  - Status: ✅ Merged (PR #803, 2026-02-19)
  - Merge SHA: d1e2fa1668156b8621557daee235844bd4703ced
  - Area: frontend / product-metrics / experimentation
  - Finding Type: user-visible experiment package
  - Reason: Extend the shipped live-indicator package with deterministic A/B variant
    assignment (`compact`/`emphasized`) and enriched telemetry needed to measure
    variant-level CTA and paywall-open behavior without expanding backend scope.
  - Experiment Window:
    - Start: 2026-02-20
    - End: 2026-03-05
    - Guardrails: websocket connect success >= 99%, no JS runtime error increase,
      no layout-shift regressions on Home/Plate/Progress
  - Metric Tracking:
    - Primary KPI: `hpp_live_cta_click_rate_by_variant`
    - Secondary KPI: `paywall_open_from_live_by_variant`
    - Supporting Signals:
      - `hpp_live_indicator_impression`
      - `hpp_cta_impression`
      - `hpp_cta_click`
      - `hpp_paywall_open_from_live`
  - Links:
    - PR #803
    - `frontend/src/features/progress/useHppLiveIndicator.ts`
    - `frontend/src/features/progress/LiveProgressIndicator.tsx`
    - `frontend/src/lib/hppTelemetry.ts`
    - `frontend/src/features/progress/__tests__/useHppLiveIndicator.test.ts`
    - `frontend/src/features/progress/__tests__/LiveProgressIndicator.test.tsx`
    - `frontend/src/features/progress/__tests__/hppTelemetry.test.ts`
  - DoD:
    - Deterministic variant assignment implemented (`userId hash % 2`, fallback `compact`)
    - UI variant rendering validated for `compact` and `emphasized`
    - Telemetry payload includes `placement` and `variant` across impression/click events
    - Paywall-open event from live indicator is emitted with stable payload shape
    - Deterministic tests and snapshots cover variant logic and telemetry shape


- [x] P1: Telemetry API normalization (`trackVipEvent` -> generic `trackEvent`)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR #863 (feat/telemetry-api-normalization)
  - Status: ✅ Completed (PR #863, 2026-02-22, merge SHA `f5b7d299`)
  - Area: frontend / analytics / architecture
  - Finding Type: naming/abstraction hygiene
  - Locations:
    - `frontend/src/lib/telemetry.ts`
    - `frontend/src/lib/telemetry/eventRegistry.ts`
  - Reason: growth events currently use `trackVipEvent`; rename to a generic API surface and keep compatibility wrapper to avoid VIP-specific naming leakage in broader telemetry families.
  - Links:
    - `docs/roadmap/WAVE_2_3_EXECUTION_PACK.md`
    - `docs/analytics/ANALYTICS_INDEX.md`
    - [PR #863](https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/863)
  - DoD:
    - [x] Generic telemetry entrypoint (`trackEvent`) introduced with deterministic validation path
    - [x] Backward-compatible wrapper for existing `trackVipEvent` callers (deprecation marker only)
    - [x] Enum constraints documented for shared growth fields where runtime validation is required
    - [x] Tests updated for both legacy and new entrypoints
    - [x] `make verify` and required CI checks pass


- [x] Resolve pip CVE-2026-1703 (pip 25.2 → 26.0+) in Docker image (GitHub alerts #533/#534)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-636
  - Status: ✅ Merged (PR-636)
  - Reason: Code Scanning alerts #533/#534 report CVE-2026-1703 for `pip 25.2` detected in two locations inside the built image (`/usr/local/lib/...` and `/opt/venv/lib/...`). Fix is to ensure Docker build upgrades pip to ≥26.0 (without exact pin in Dockerfile per policy).
  - Links:
    - GitHub alerts #533 / #534
    - `Dockerfile` (builder venv + runtime-base system pip)
    - `.github/workflows/trivy.yml` (builds `production` target and scans the image)
  - DoD:
    - Production image contains `pip>=26.0,<27.0` in both `/usr/local/lib/.../pip-*.dist-info` and `/opt/venv/lib/.../pip-*.dist-info`
    - 🔄 Awaiting next scan for alerts #533/#534 to close (merged ≠ scanner rerun)


- [x] Cross-platform Design System: define tokens + UI primitives (Web + iOS)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (design consistency / velocity)
  - Target PR: PR #870 (`feat/cross-platform-design-system-tokens-primitives`)
  - Status: ✅ Merged (PR #870, 2026-02-22)
  - Merge SHA: 3f5481d8
  - Area: ios / frontend / design-system
  - Reason: Web has initial brand colors in `frontend/src/styles/tokens.ts`, but iOS lacks a centralized token mirror
    (colors/spacing/typography/motion). Without a minimal design system, UI work drifts, is slower to delegate, and is
    harder to review consistently across platforms.
  - Links:
    - [PR #870](https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/870)
    - `docs/orchestration/IOS_FRONTEND_MULTIAGENT_PLAYBOOK.md` (design canon + agent roster + checklists)
    - `frontend/src/styles/tokens.ts` (Web token SoT)
    - `ios/PulsePlate/DesignSystem/DesignTokens.swift` (iOS token SoT)
    - `ios/PulsePlate/DesignSystem/PPButton.swift`
    - `ios/PulsePlate/DesignSystem/PPCard.swift`
    - `ios/PulsePlate/DesignSystem/PPInput.swift`
    - `ios/PulsePlate/DesignSystem/PPTypography.swift`
    - `frontend/AGENTS.md`, `ios/AGENTS.md` (thin-client + CI invariants)
  - Review remediations:
    - Cubic P2: sync `textValue` when bound value changes externally (commit `90f8c181`)
    - CodeRabbit Major: use `NumberFormatter` for locale-aware parsing (commit `0a720f78`)
    - CodeRabbit Nitpick: reduce duplicated card styling via `.ppCardStyle()` (commit `0a720f78`)
  - DoD:
    - ✅ Token canon defined (colors + spacing + typography + motion + elevation) with explicit names
    - ✅ iOS has a single source for tokens (`DesignTokens.swift`, SwiftUI-friendly) and uses it in new components
    - ✅ Web components consume tokens (no hardcoded brand colors/spacing in new primitives)
    - ✅ Minimal primitives exist on both platforms: Button, Card, Input, Typography
    - ✅ Locale-aware numeric input via `NumberFormatter` (iOS PPInput)
    - ✅ All bot review comments addressed and mapped in PR body
    - ✅ CI checks green; merge readiness gate passed


- [x] P1: Design token pipeline foundation (`/tokens` authoring to generated runtime mirrors)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (design-system governance / drift prevention)
  - Target PR: PR #1047 (`feat(design): add token pipeline foundation`)
  - Status: ✅ Merged
  - Merge SHA: f272503c
  - Area: frontend / ios / design-system / governance
  - Finding Type: tooling foundation + parity enforcement
  - Reason: Earlier token work established web SoT, raw-hex guards, Storybook review, and an iOS token facade, but runtime mirrors still depended on manual sync. PR #1047 adds a governed `/tokens` authoring source, Style Dictionary generation into the existing web/iOS runtime contracts, parity guards, CI wiring, and review-governed documentation without breaking current consumers.
  - Links:
    - [PR #1047](https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1047)
    - `tokens/`
    - `docs/design/TOKENS_SOT.md`
    - `docs/design/TOKEN_PIPELINE_GOVERNANCE.md`
    - `frontend/src/styles/tokens.css`
    - `frontend/src/styles/tokens.ts`
    - `ios/PulsePlate/DesignSystem/DesignTokens.generated.swift`
    - `ios/PulsePlate/DesignSystem/DesignTokens.swift`
    - `tests/test_design_token_parity.py`
    - `docs/review/PR_1047_FIXED_MAPPING.md`
  - DoD:
    - ✅ `/tokens` is the governed authoring source for stable, already-live token values
    - ✅ Existing runtime contracts remain intact for `tokens.css`, `tokens.ts`, and `PPDesignTokens`
    - ✅ Generated iOS mirror exists as `DesignTokens.generated.swift` behind the stable public facade
    - ✅ Parity and determinism checks cover `/tokens -> web/iOS mirrors`
    - ✅ CI token pipeline lane and merge-governance documentation are merged and review-mapped


- [x] P1: Weekly-plan VIP alias hygiene and schema visibility
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (API contract hygiene / OpenAPI surface discipline)
  - Target PR: PR #1061 (`refactor(weekly-plan): thin legacy VIP weekly alias`)
  - Status: ✅ Merged
  - Merge SHA: 174a7bdb
  - Area: backend / OpenAPI / legacy compatibility
  - Finding Type: legacy alias delegation + schema visibility cleanup
  - Reason: `/api/v1/premium/plan/week` was a VIP weekly-plan compatibility route living under the deprecated `/premium/*` namespace with its own legacy shaping path. PR #1061 reduced it to a thin compatibility alias over `/api/v1/vip/menu/weekly/plan`, kept runtime backward compatibility, hid the broken-name route from public OpenAPI, and added parity/normalization regressions for weekly-plan numeric fields.
  - Links:
    - [PR #1061](https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1061)
    - `legacy_app.py`
    - `tests/test_legacy_weekly_plan_alias_api.py`
    - `tests/test_app_openapi_coverage.py`
    - `docs/contracts/PRODUCT_TIER_REMEDIATION_PLAN.md`
    - `docs/contracts/OPENAPI_PATHS_AUDIT.md`
    - `docs/review/PR_1061_FIXED_MAPPING.md`
  - DoD:
    - ✅ `/api/v1/premium/plan/week` delegates to `/api/v1/vip/menu/weekly/plan` without retaining VIP business logic in the legacy shim
    - ✅ Runtime compatibility preserved for existing callers of the legacy VIP alias
    - ✅ Public OpenAPI no longer exposes `/api/v1/premium/plan/week`
    - ✅ Parity tests prove legacy alias responses match the canonical VIP weekly-plan route
    - ✅ Weekly-plan numeric normalization covers malformed, non-finite, and overflow-prone values with deterministic regressions


<a id="ledger-p1-weekly-plan-openapi-parity-wave"></a>
- [x] P1: Weekly-plan OpenAPI and web parity wave
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (OpenAPI reconciliation / frontend thin-client parity)
  - Target PR: PR #1068 (`docs(openapi): reconcile weekly-plan contract truth`), PR #1069 (`refactor(vip): thin premium weekly alias`), PR #1070 (`refactor(frontend): normalize weekly plan consumers`), PR #1075 (`fix(frontend): gate weekly plan initial load`)
  - Ledger closure PR: PR #1077 (`docs(ledger): record weekly-plan wave hotfix`)
  - Related follow-up PR: PR #1079 (`fix(ci): bound trivy image scan`)
  - Status: ✅ Merged (runtime wave and post-merge hotfix); closure synchronized in PR #1077 with Trivy workflow split traced through PR #1079
  - Merge SHAs:
    - PR #1068: `888dc69a`
    - PR #1069: `68fe8d57`
    - PR #1070: `eff51947`
    - PR #1075: `b57333be`
  - Area: backend / OpenAPI / frontend weekly-plan runtime
  - Finding Type: schema reconciliation + legacy alias cleanup + normalized web consumer parity
  - Reason:
    - The repo had already moved to the canonical PRO route `POST /api/v1/pro/meal/weekly` and shared backend DTO normalization, so the remaining work was reconciliation and finishing rather than route migration.
    - The wave locked `WeeklyMealPlanResponse` as the generated OpenAPI truth, kept `/api/v1/premium/plan/week-flexible` as a hidden runtime-compatible alias, and moved web weekly-plan consumers to one normalized UI view-model instead of ad-hoc raw payload assumptions.
    - A follow-up hotfix then closed the initial-render regression where `WeeklyPlanViewer` could briefly flash the empty summary before the first fetch transitioned into loading.
  - Links:
    - [PR #1068](https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1068)
    - [PR #1069](https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1069)
    - [PR #1070](https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1070)
    - [PR #1075](https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1075)
    - [PR #1077](https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1077)
    - [PR #1079](https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1079)
    - `app/schemas/weekly_plan.py`
    - `app/routers/pro.py`
    - `app/routers/premium_week.py`
    - `legacy_app.py`
    - `frontend/src/api/openapi.json`
    - `frontend/src/api/schema.ts`
    - `frontend/src/features/plan/WeeklyPlanViewer.tsx`
    - `frontend/src/features/plan/__tests__/WeeklyPlanViewer.test.tsx`
    - `frontend/src/hooks/useWhoTargetsWithWeeklyPlan.ts`
    - `docs/review/PR_1068_FIXED_MAPPING.md`
    - `docs/review/PR_1069_FIXED_MAPPING.md`
    - `docs/review/PR_1070_FIXED_MAPPING.md`
    - `docs/review/PR_1075_FIXED_MAPPING.md`
    - `docs/review/PR_1077_FIXED_MAPPING.md`
  - DoD:
    - ✅ `WeeklyMealPlanResponse` remains the single canonical weekly-plan response shape for backend normalization and generated OpenAPI artifacts
    - ✅ Public OpenAPI exposes `POST /api/v1/pro/meal/weekly` and keeps `POST /api/v1/premium/plan/week-flexible` hidden as a deprecated runtime alias
    - ✅ Legacy VIP alias cleanup stays thin and schema-hidden without reintroducing separate weekly-plan business logic
    - ✅ Web weekly-plan consumers render a normalized weekly-plan view-model instead of depending on raw response shape details, including initial-load gating that treats `data == null && err == null` as loading instead of flashing the empty summary
    - ✅ Regression coverage exists for malformed payload normalization, schema visibility, legacy alias parity, and normalized weekly-plan web consumption


- [x] Docs: Canonicalize iOS API integration guide to current Networking SoT
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (docs correctness)
  - Target PR: PR-669
  - Status: ✅ Merged (PR-669, 2026-02-07)
  - Reason: Existing `docs/IOS_API_INTEGRATION.md` was outdated and instructed creating a parallel URLSession-based transport layer; this conflicts with thin-client policies and current `ios/PulsePlate/Networking/*` SoT.
  - Links:
    - PR-669
    - `docs/audit/IOS_DOCS_DRIFT_AUDIT_2026-02-07.md`
    - `docs/IOS_API_INTEGRATION.md`
    - `ios/PulsePlate/Networking/APIClient.swift`
    - `ios/PulsePlate/Networking/HTTPClient.swift`
  - DoD:
    - Doc lists repo SoT paths and rules (no new transport)
    - Includes “how to add endpoint” recipe aligned with existing protocols/tests
    - Future items (IAP/receipt/keychain) point to ledger items (no mixed scopes)


- [x] Docs: Refresh iOS roadmap to AS-IS / NEXT ACTIONS (repo-truth)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (docs correctness)
  - Target PR: PR-669
  - Status: ✅ Merged (PR-669, 2026-02-07)
  - Reason: `docs/roadmap/IOS_ROADMAP.md` still described “when iOS development resumes”; iOS is active (RootTabs, Networking SoT, guard tests).
  - Links:
    - PR-669
    - `docs/audit/IOS_DOCS_DRIFT_AUDIT_2026-02-07.md`
    - `docs/roadmap/IOS_ROADMAP.md`
    - `ios/PulsePlate/Views/RootTabs.swift`
    - `ios/PulsePlate/Networking/*`
  - DoD:
    - AS-IS section reflects current entrypoint, navigation, networking, guards, localization
    - NEXT ACTIONS list only real follow-ups (P0/P1) and points to ledger items


- [x] iOS: Expose BMI screen from Home / RootTabs (Free MVP UX)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (Free MVP polish)
  - Target PR: PR-671
  - Status: ✅ Merged (PR-671, 2026-02-07)
  - Reason: BMI calculator exists but is not clearly reachable from the main navigation (Free MVP must make value moment obvious).
  - Links:
    - `ios/PulsePlate/Views/RootTabs.swift`
    - `ios/PulsePlate/Screens/BMICalculatorScreen.swift`
    - `ios/PulsePlate/ViewModels/BMICalculatorViewModel.swift`
    - `docs/audit/PR_671_IOS_EXPOSE_BMI_ROOTTABS_AUDIT.md`
  - DoD:
    - User can reach BMI from the default tab flow (Home card or dedicated tab)
    - Loading/error/validation states remain user-friendly (no debug-y messages)
    - `make ios-test` passes


- [x] iOS: Mount WeeklyPlanReader behind feature flag (PRO demo slice) — ✅ Merged (PR-673, 2026-02-07)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (Demo / TestFlight)
  - Target PR: PR-673
  - Status: ✅ Merged (PR-673, 2026-02-07)
  - Reason: WeeklyPlanReader is mounted behind `FeatureFlags.weeklyPlanReaderEnabled` (Debug Tools entrypoint).
  - Links:
    - `ios/PulsePlate/Utilities/FeatureFlags.swift` (`weeklyPlanReaderEnabled`)
    - `ios/PulsePlate/Views/WeeklyPlan/WeeklyPlanReaderView.swift`
    - `ios/PulsePlate/ViewModels/WeeklyPlanReaderViewModel.swift`
    - `ios/PulsePlate/Services/WeeklyPlanService.swift`
    - `docs/audit/PR_673_IOS_WEEKLY_PLAN_READER_FLAG_AUDIT.md`
    - <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/673>
  - DoD:
    - When `FeatureFlags.weeklyPlanReaderEnabled` is true, the screen is reachable (Debug tools or a controlled entrypoint)
    - Requests use `APIClient` and include `X-API-Key` where required (no auth bypass in production code)
    - Errors for 400/401/403 are rendered as user-readable states (not crashes)
    - `make ios-test` passes

<a id="ledger-p1-ios-v3-pro-tools-rollout-alignment"></a>
- [ ] P1: iOS V3 Pro Tools rollout alignment (Weekly Plan Reader + Shopping List)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (Release alignment / docs drift)
  - Target PR: PR-TBD
  - Status: Planned
  - Area: ios / backend / figma / docs
  - Finding Type: rollout alignment
  - Locations:
    - `ios/PulsePlate/Views/HomeView.swift`
    - `ios/PulsePlate/Utilities/FeatureFlags.swift`
    - `ios/PulsePlate/Views/WeeklyPlan/WeeklyPlanReaderView.swift`
    - `ios/PulsePlate/ViewModels/ShoppingListReaderViewModel.swift`
    - `app/routers/shopping_list_pro.py`
    - `docs/figma/EXECUTABLE_DESIGN_INDEX.md`
    - `docs/design/PULSEPLATE_BUTTON_ACTION_PROMPT_MATRIX.md`
    - `ios/SHOPPING_LIST_SETUP.md`
  - Reason: Runtime V3 surfaces already exist under Home → Pro Tools, but release rollout is still blocked by feature-flag defaults and unresolved source-of-plan flow. `DEBUG` shopping-list path relies on stub `plan_data`, while iOS has no `weekly_plan_id` handoff and backend `weekly_plan_id` support still returns HTTP 501. Canonical docs also drifted by mixing historical plan state with current runtime state.
  - Links:
    - `ios/PulsePlate/Views/HomeView.swift`
    - `ios/PulsePlate/Utilities/FeatureFlags.swift`
    - `ios/PulsePlate/Views/WeeklyPlan/WeeklyPlanReaderView.swift`
    - `app/routers/shopping_list_pro.py`
    - `docs/design/PULSEPLATE_BUTTON_ACTION_PROMPT_MATRIX.md`
    - `docs/figma/EXECUTABLE_DESIGN_INDEX.md`
  - DoD:
    - Weekly Plan Reader release path is explicitly approved and smoke-tested (not only debug / QA flag usage)
    - Weekly Plan Reader share + VIP follow-up actions are either implemented or intentionally product-closed with documented rationale
    - Shopping List opens from a canonical release source-of-plan path (no dependency on debug stub data)
    - `/api/v1/pro/meal/shopping-list` supports the chosen release contract (`weekly_plan_id` or deterministic carried `plan_data`)
    - Canonical docs and roadmap entries reflect actual runtime status with no debug-only / planned-only drift


- [x] iOS: Plate (PRO) align to canonical backend `GET /api/v1/pro/nutrition/daily` + profile input
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (Feature integration)
  - Target PR: PR-667
  - Status: ✅ Merged (PR-667, 2026-02-07)
  - Reason: iOS Plate now uses canonical `GET /api/v1/pro/nutrition/daily` with deterministic query building + `X-API-Key` (no legacy alias as source-of-truth).
  - Links:
    - `app/routers/pro.py` (canonical: `/api/v1/pro/nutrition/daily`)
    - `legacy_app.py` (deprecated shim: `/api/nutrition/{date_str}`)
    - `ios/PulsePlate/Views/PlateView.swift` / `ios/PulsePlate/Views/PlateViewPP.swift`
    - `ios/PulsePlate/Services/ProKeyProvider.swift`
    - `ios/PulsePlate/Services/ProDailyNutritionService.swift`
    - `ios/PulsePlate/Views/ProfileView.swift`
    - `ios/PulsePlateTests/Services/ProDailyNutritionServiceTests.swift`
  - Evidence (file:line):
    - iOS request path + deterministic query order: `ios/PulsePlate/Services/ProDailyNutritionService.swift:36-57`
    - iOS sends `X-API-Key` header via APIClient: `ios/PulsePlate/Services/ProDailyNutritionService.swift:94-105`
    - iOS profile inputs (AppStorage keys + form fields): `ios/PulsePlate/Views/ProfileView.swift:8-56`
    - iOS tests assert deterministic URL + header: `ios/PulsePlateTests/Services/ProDailyNutritionServiceTests.swift:6-21`, `ios/PulsePlateTests/Services/ProDailyNutritionServiceTests.swift:23-65`
    - Backend canonical route (guarded by PRO tier): `app/routers/pro.py:369-373`, `app/routers/pro.py:400-422`
  - DoD:
    - iOS implements a reusable profile source for required query params (sex/age/height_cm/weight_kg/activity/goal/lang)
    - iOS uses `APIClient` and calls canonical `GET /api/v1/pro/nutrition/daily` with `X-API-Key` sourced from the app's secure key provider
    - UX: explicit states for missing PRO key / missing profile / 422 validation errors
    - Tests:
      - unit test for building daily nutrition request query (deterministic)
      - `make ios-test` passes


- [x] Migrate BMICalculatorViewModel + Screen to BMICalculate*DTO; delete legacy BMIRequest/BMIResponse (iOS) — completed in PR-596 (merged 2026-01-26)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-596
  - Status: ✅ Merged
  - Reason: Align iOS BMI UI/service to canonical BMICalculate*DTO contract and APIError.
  - Links:
    - ios/PulsePlate/ViewModels/BMICalculatorViewModel.swift
    - ios/PulsePlate/Screens/BMICalculatorScreen.swift
    - ios/PulsePlate/Models/BMI/BMICalculateRequestDTO.swift (new)
    - ios/PulsePlate/Models/BMI/BMICalculateResponseDTO.swift (new)
    - ios/PulsePlate/Services/BMIService.swift
    - <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/596>
  - DoD:
    - BMICalculatorViewModel uses BMICalculateRequestDTO/BMICalculateResponseDTO
    - BMICalculatorViewModel uses APIError (not BMIServiceError)
    - BMICalculatorScreen uses new DTO types
    - Legacy BMIRequest.swift deleted
    - Legacy BMIResponse.swift deleted
    - BMI service is BMIServicing (thin adapter over APIClient)
    - Error handling updated to use APIError (incl. unknown vs transport)
    - Tests updated


- [x] NutritionData.swift: migrate to APIClient (iOS thin-client violation) — completed in PR-596 (merged 2026-01-26)
  - Owner: @katsiaryna_kavaleuskaya
  - Target PR: PR-596
  - Status: ✅ Merged
  - Priority: P1
  - Area: iOS
  - Finding Type: thin-client violation
  - Location: `ios/PulsePlate/Models/NutritionData.swift:60`
  - Reason: Direct URLSession usage in model layer violated thin-client transport policy.
  - Links:
    - ios/PulsePlate/Models/NutritionData.swift
    - <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/596>
  - DoD:
    - NutritionData uses APIClient (not direct URLSession)
    - Consistent error handling via APIError
    - No dual-path networking




- [x] PR-596 merged: iOS thin HTTP adapter remediation (merged 2026-01-26)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-596
  - Status: ✅ Merged
  - Reason: Consolidate iOS networking under a single thin transport (`APIClient`) and eliminate direct HTTP calls outside transport layer.
  - Links:
    - docs/audit/PR_595_IOS_THIN_HTTP_ADAPTER_AUDIT.md
    - <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/596>
  - DoD:
    - All services use `APIClient` (no direct `URLSession` outside transport layer)
    - No direct HTTP in non-transport layers (models/view models/views/services)
    - DTO boundary aligned with canonical backend contracts
    - Tests/guards pass
  - Notes (post-merge):
    - Services/UI: no direct URLSession
    - APIError: transport vs HTTP
    - snake_case decoder parity
    - emptyResponse semantics
    - unknown vs transport


- [x] PR-607 merged: iOS UITests bundle load fix + CI UI smoke (merged 2026-01-27)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-607
  - Status: ✅ Merged
  - Reason: Restore UI tests build-product correctness (bundle contains executable) and add dedicated `ios-ui-smoke` CI signal.
  - Links:
    - docs/audit/PR_Q2B_IOS_UITESTS_BUNDLE_LOAD_AUDIT.md
    - <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/607>
  - DoD: ✅ Completed
    - `PulsePlateUITests.xctest` contains executable (no Code=4 / exit 65 before tests execute)
    - CI `ios-ui-smoke` job runs minimal UI smoke


- [x] Stabilize AnimationTests.swift (iOS)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-681
  - Status: ✅ Merged (PR-681, 2026-02-07)
  - Reason: Root cause: `PBXFileSystemSynchronizedBuildFileExceptionSet.membershipExceptions` excluded `AnimationTests.swift` from `PulsePlateTests`. Fix: removed `AnimationTests.swift` from `membershipExceptions` so the tests are included in `PulsePlateTests` again.
  - Links:
    - ios/PulsePlateTests/AnimationTests.swift
    - ios/PulsePlate.xcodeproj/project.pbxproj
    - ios/AGENTS.md (Animated/UI helper tests policy)
    - <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/681>
  - DoD:
    - Either rewrite using available public components
    - Or extract to separate test target
    - Or remove if dead test code (no longer needed)
    - AnimationTests.swift compiles without errors
    - All referenced types/modifiers are accessible (public/internal as needed)
    - Tests restored to PulsePlateTests target (if kept)
    - CI green with AnimationTests included (if restored)


- [x] Unify ShoppingListService / WeeklyPlanService under thin HTTP adapter (iOS) — completed in PR-596 (merged 2026-01-26)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-596
  - Status: ✅ Merged
  - Reason: Remove direct URLSession usage from services; consolidate under APIClient/HTTPClient seam.
  - Links:
    - ios/PulsePlate/Services/ShoppingListService.swift
    - ios/PulsePlate/Services/WeeklyPlanService.swift
    - ios/PulsePlate/Networking/APIClient.swift (reference implementation)
    - <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/596>
  - DoD:
    - ShoppingListService uses APIClient (no direct URLSession)
    - WeeklyPlanService uses APIClient (no direct URLSession)
    - Custom error enums replaced with APIError from Networking layer
    - All services follow same thin adapter pattern
    - Tests updated to use HTTPClientProtocol stubs
    - No breaking changes to public APIs


- [x] Wire soft paywall CTA to real paywall router (iOS) — ✅ Merged (PR-674, 2026-02-07)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-674
  - Status: ✅ Merged (PR-674, 2026-02-07)
  - Reason: Soft paywall CTA is wired to a real paywall navigation handler and presents a minimal paywall screen.
  - Links:
    - ios/PulsePlate/Screens/BMICalculatorScreen.swift (line ~73)
    - docs/audit/PR_674_IOS_SOFT_PAYWALL_CTA_ROUTER_AUDIT.md
    - <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/674>
  - DoD:
    - Paywall router/navigation handler implemented
    - SoftPaywallHookView CTA wired to navigation
    - No TODO comments in production code

- [x] core/db.py vs core/db/ collision resolved (TP2 amendment 2026-01-28)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR #617 (amendment)
  - Reason: TP2 originally used `core/db/fallback.py` which caused `core.db` to resolve as package in CI. Resolved by moving fallback to `core/db_fallback.py` (flat module) and removing `core/db/` package; no guard exception needed.
  - DoD: Done. Fallback in `core/db_fallback.py`; AGENTS.md rule: never add `core/<name>/` when `core/<name>.py` exists.


- [x] Dev tooling: GraphMap viewer + deterministic graph builder (dev-only)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (developer experience)
  - Target PR: PR-695 + PR-696
  - Status: ✅ Merged (PR-695 @ 2e3d1a5b, PR-696 @ 8e527c13; 2026-02-08)
  - Reason: Make SoT relationships (docs/agents/policies/tests) navigable as an interactive graph with strict determinism.
    This reduces repeated rediscovery work and improves reviewability without introducing a new SoT.
  - Links:
    - `docs/graph/GRAPHMAP_SPEC.md` (SoT for GraphMap; docs-only)
    - `docs/memory/index.md` (PML capsules as graph inputs)
    - `docs/orchestration/AGENT_CONTEXT_MAP.md`
    - `docs/orchestration/AGENT_CAPABILITY_MATRIX.md`
    - `docs/agents/index.md`
  - DoD:
    - ✅ `docs/graph/GRAPHMAP_SPEC.md` defines GraphMap inputs and edge rules
    - ✅ Deterministic builder generates stable `docs/graph/graph.json` from explicit sources only
    - ✅ Viewer supports filtering by `Level` and `NodeType`, plus search, legend, and zoom controls
    - ✅ Clicking opens GitHub file links (optionally `path:line` anchors) and never opens local absolute paths
    - ✅ Forbidden edges are enforced (no semantic guessing / embeddings / AI-inferred relationships)
    - ✅ No runtime impact; no secrets/tokens; safe for local usage (and optionally GitHub Pages)


- [x] Fix ShoppingPlan public API (make nested types public or narrow API surface)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-677
  - Status: ✅ Merged (PR-677, 2026-02-07)
  - Reason: CodeRabbit flagged "ShoppingPlan isn't constructible" - public type with internal nested types (DailyMenu, Meal). Outside PR-559 scope but architectural smell.
  - Links:
    - ios/PulsePlate/Models/ShoppingList/ShoppingListStubPlan.swift
    - CodeRabbit comment (outside diff, actionable=0)
    - <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/677>
  - DoD:
    - Either make DailyMenu/Meal public with explicit init
    - Or narrow API: make ShoppingPlan/ShoppingListRequestPayload internal if it's "stub" only
    - No breaking changes to existing usage


- [x] Generalize dependency vulnerability guards beyond single-CVE floors (merged 2026-02-27)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR #923
  - Status: ✅ Closed
  - Reason: Current guard test enforces a floor for one high-risk dependency (`cryptography`). Preventing future
    regressions at scale needs a deterministic allow/deny schema for multiple packages/CVEs.
  - Links:
    - `tests/test_dependency_security_guard.py`
    - `tests/fixtures/dependency_security_schema.json`
    - `docs/security/DEPENDENCY_SECURITY_GUARD_WORKFLOW.md`
  - DoD:
    - [x] Introduce a centralized guard schema (`package -> min_safe_version` or denylist) for key dependencies
    - [x] Deterministic CI/pytest check validates all relevant requirement surfaces
    - [x] Developer docs explain how to update schema when new CVEs are triaged


- [x] Move insight redaction/import helpers out of legacy_app.py (merged 2026-02-10)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-703 (merged)
  - Status: ✅ Merged
  - Reason: Codex actionable — keep legacy_app thin proxy only. Move `_redact_rag_context_for_insight` and `_load_llm_get_provider` to canonical module (`core/insight/`) to maintain AGENTS invariant. Follow-up from PR-611.
  - Links:
    - docs/audit/PR_611_INSIGHT_SAFETY_ERROR_HYGIENE_AUDIT.md
    - PR-611 (merged 2026-01-28)
    - PR-703 (merged 2026-02-10)
  - Preconditions (already true as of PR-611):
    - `_redact_rag_context_for_insight` lives in `core/insight/safety.py`
  - DoD:
    - Move `_load_llm_get_provider` to canonical module (not `legacy_app.py`)
    - `legacy_app.py` contains only thin proxies (no business/import helpers)
    - Tests pass
    - OpenAPI unchanged


- [x] Observability: measure legacy nutrition alias usage (deprecation removal readiness)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (observability / migration)
  - Target PR: PR-698
  - Status: ✅ Merged (PR-698, 2026-02-09)
  - Reason: `GET /api/nutrition/{date_str}` is a deprecated compatibility alias. Before removing it safely, we need
    basic usage telemetry (by client/platform) to confirm iOS migration completion and avoid breaking unknown consumers.
  - Links:
    - `app/routers/legacy_nutrition_alias.py` (`/api/nutrition/{date_str}` legacy alias)
    - `docs/roadmap/BACKLOG_LEDGER.md` (P0 security fix item for alias guard)
  - DoD:
    - Count requests to `/api/nutrition/{date_str}` with low-cardinality labels (e.g., platform/client + status)
    - Dashboard/query recipe documented (where to check usage)
    - Removal decision recorded (remove alias date / keep longer with rationale)

- [x] P1 (maintenance): Type-hints carryover cleanup (tests)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (maintenance)
  - Target PR: PR #642
  - Status: ✅ Done (merged via PR #642)
  - Reason: Previously-agreed test typing/hygiene changes were missed in a prior PR and intentionally carried over to keep bots/review consistent. Non-functional change (tests only).
  - Notes: Missed in prior PR; carried over intentionally.
  - Links: PR #642; policy: AGENTS.md (carryover rule); related: PR #640/#641 (context)
  - DoD: Done. CI green; reviewers' sign-off; PR #642 merged; no new skips; only tests/docs changed


- [x] P1: Extract hardcoded constants (BMR, export formats)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (maintainability)
  - Target PR: PR #644
  - Status: ✅ Merged (PR #644)
  - Merge SHA: fda459d743e848b72c2c818b8dd7bef62af99aec
  - Reason: BMR formula constants and export formats are hardcoded in `legacy_app.py`. Should be extracted to `core.bmr` module and `ExportFormat` enum for maintainability.
  - Links:
    - PR #644
    - docs/audit/LEGACY_APP_MIGRATION_STATUS.md (Hardcoded constants section)
    - legacy_app.py:97 (nutrition_core imports), export functions
  - DoD:
    - Extract BMR constants to `core/bmr.py` module
    - Create `ExportFormat` enum (CSV, PDF, JSON)
    - Replace hardcoded values with constants/enum
    - Tests verify no functionality broken

---


- [x] P1: Fact-check closure for stale critical claims in external roadmap snapshot (2026-03-05)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (program governance)
  - Target PR: PR #972, PR #973, PR #974
  - Status: ✅ Merged (all listed PRs merged on 2026-03-04)
  - Reason: External document snapshot contained stale “P0 missing” claims for controls that were already implemented in runtime. Ledger now anchors these as completed facts to prevent duplicate emergency scope.
  - Links:
    - `app/security/rate_limit.py` (rate limiting baseline)
    - `app/routers/realtime_ws.py` (WebSocket auth/policy-close baseline)
    - PR #972 (Philosophy validator core)
    - PR #973 (Recursive RAG W1 core)
    - PR #974 (orchestration telemetry/spec package)
  - DoD:
    - Stale claims are marked as implemented with repository evidence
    - Remaining open items track only fact-valid deltas (RAG technical debt + runtime governance follow-ups)


- [x] P1: Local/dev env alignment for SERVER_SALT + quota limit (post PR-647)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-649
  - Status: ✅ Merged (PR-649)
  - Reason: PR-647 introduced a fail-fast requirement for `SERVER_SALT` at app startup (VIP LLM monthly quota). Local/root
    `docker-compose.yaml` and `.env.example` must reflect required env vars to avoid confusing local startup failures.
  - Links:
    - PR-647: VIP LLM hard monthly quota (deterministic enforcement)
    - docs/audit/PR_647_VIP_LLM_MONTHLY_QUOTA_AUDIT.md
    - PR-649: env.example + docker-compose alignment for SERVER_SALT fail-fast
    - docs/audit/PR_649_ENV_REQUIRED_SERVER_SALT_AUDIT.md
  - DoD:
    - ✅ `.env.example` includes `SERVER_SALT` + `VIP_LLM_INSIGHT_REQUESTS_PER_MONTH` (with validation guidance)
    - ✅ Root `docker-compose.yaml` passes both vars; missing `SERVER_SALT` fails fast at compose evaluation time
    - ✅ Local compose boots deterministically when `SERVER_SALT` is provided


- [x] P1: Unify `TargetsIn` schemas (legacy_app ↔ `app.schemas.nutrition_targets`)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (drift prevention)
  - Target PR: PR #633 (merged `29546992`, 2026-02-03)
  - Status: ✅ Merged (PR #633, 2026-02-03)
  - Resolution: PR-633 unified TargetsIn by making `legacy_app.TargetsIn` a thin alias to canonical
    `app.schemas.nutrition_targets.TargetsIn`. Guard test `test_legacy_targets_in_is_canonical_alias()`
    in `tests/test_targets_in_parity.py` prevents future drift.
  - Links:
    - PR #631 (remediation): full OpenAPI without import-time `app.models.*` along OpenAPI path
    - PR #633 (unification): thin alias + parity tests
  - Evidence:
    - `app/schemas/nutrition_targets.py:37-58` (canonical TargetsIn, import-safe)
    - `legacy_app.py:126-127` (`TargetsIn = CanonicalTargetsIn`, PR-633 alias)
    - `tests/test_targets_in_parity.py:28-32` (`assert legacy_app.TargetsIn is CanonicalTargetsIn`)
  - DoD:
    - ✅ One canonical schema (single source of truth) with a thin wrapper/alias where needed
    - ✅ Parity tests that prevent schema drift (fields + validation behavior for structured targets payloads)
    - ✅ No contract break for legacy endpoints (explicitly verified in tests)


- [x] PR-619 DB fallback canonical API in `legacy_app.py` — merged 2026-01-30
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (maintenance)
  - Target PR: PR #619
  - Status: ✅ Merged
  - Reason: Align `legacy_app.py` with DB fallback policy — no direct read/write of `_db_fallback_active` outside `core/db_fallback.py`; use `is_fallback_active()` and `clear_fallback_active()`.
  - Links:
    - <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/619>
  - DoD:
    - ✅ No direct `_db_fallback_active` in `legacy_app.py`
    - ✅ Guards + tests green; CI green
  - Next after merge: P0 rate-limiting for LLM endpoints


- [x] Resolve cryptography CVE-2026-26007 in runtime/dev/lock manifests
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-716 (remediation: bump + guard); PR-724 = docs-only closure/policy
  - Status: ✅ Closed (remediation on main via PR-716; guard test in place; PR-724 adds AGENTS policy + ledger)
  - Reason: Five GitHub security alerts (Dependabot #27/#28/#29 and Code Scanning #538/#539) report vulnerable
    `cryptography` (`<=46.0.4`); required fixed version is `46.0.5`.
  - Links:
    - `docs/security/CVE-2026-26007-cryptography.md`
    - GitHub alerts: `security/dependabot/27`, `security/dependabot/28`, `security/dependabot/29`
    - GitHub alerts: `security/code-scanning/538`, `security/code-scanning/539`
  - DoD:
    - [x] `cryptography` bumped to `46.0.5` (or higher safe version) in `requirements.in`,
      `requirements.txt`, `requirements-dev.txt`, `requirements-lock.txt`, and `constraints.txt`
    - [x] New dependency security guard test added to enforce cryptography floor version
      (CVE-2026-26007) — `tests/test_dependency_security_guard.py`
    - [ ] Security/code scanning alerts close on next scan


- [x] P1: Add canonical orchestration contract matrix for PR governance
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR #996 (`docs(orchestration): add canonical PR orchestration contract matrix`)
  - Status: ✅ Merged (PR #996, 2026-03-06)
  - Area: orchestration / CI / review governance
  - Finding Type: process hardening
  - Reason: Rules are split across check_pr_body_phase2_gates.py, check_pr_merge_readiness.py, check_review_threads_disposition.py and AGENTS.md; single source of truth reduces drift.
  - Links:
    - `scripts/ci/check_pr_body_phase2_gates.py:11` (Phase 2 contract config)
    - `scripts/ci/check_pr_merge_readiness.py:337` (unresolved threads), `:350` (actionable items)
    - `scripts/orchestration/check_review_threads_disposition.py:27` (FIXED/NOT-A-BUG/DEFERRED), `:170` (trigger-only ban)
    - `AGENTS.md:42` (Review Governance), `:103` (FIXED proof), `:418` (Fixed in Commit Mapping)
  - DoD:
    - Single doc (e.g. docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md) is the canonical SoT; AGENTS.md only links to it
    - Doc defines Phase 2 body contract, merge readiness contract, FIXED/NOT-A-BUG/DEFERRED proof rules, required-check truth for current HEAD, hard/soft/external CI check classes
    - Linked from AGENTS.md as canonical orchestration governance reference
  - Artifact: `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md`


- [x] P1: Agent task evaluation contract (success criteria per task class)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR #866 (docs/agent-task-evaluation-contract)
  - Status: ✅ Completed (PR #866, 2026-02-22, merge SHA `fdd31e21`)
  - Area: orchestration / agents / quality
  - Finding Type: process / evaluation
  - Reason: EVMbench-style evaluation requires explicit success criteria and optional recall checklist per task class (CI fix, security remediation, docs-only). Define contract and link to existing gates.
  - Links:
    - `docs/audit/EVMBENCH_INSPIRED_AGENT_EVALUATION_BRAINSTORM_2026-02-21.md`
    - `docs/orchestration/RESEARCH_BRAINSTORMING_PROTOCOL.md`
    - `docs/orchestration/AGENT_TASK_EVALUATION_CONTRACT.md`
    - [PR #866](https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/866)
  - DoD:
    - [x] Doc defines success criteria for at least: "CI fix", "security remediation", "docs-only"
    - [x] Optional recall-style checklist per class; linked from RUNBOOK or AGENTS


- [x] P1: Document required-check truth for merge (current HEAD only)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR #996 (`docs(orchestration): add canonical PR orchestration contract matrix`) + PR #1010 (`fix(orchestration): close runtime wave 4 drift`)
  - Status: ✅ Merged (governance rule codified by PR #996 and refreshed in PR #1010)
  - Area: orchestration / CI / review governance
  - Finding Type: process hardening
  - Reason: Merge decision must be based on latest required checks for current HEAD only; cancelled/stale runs ignored to avoid confusion and extra iterations.
  - Links:
    - `AGENTS.md:31` (PR merge readiness), `:39` (merge checklist)
    - `scripts/ci/check_pr_merge_readiness.py:337` (unresolved_threads), `:344` (errors)
  - DoD:
    - Canonical rule documented: merge decision based on latest required checks for current HEAD only; cancelled runs ignored; non-required external reviews do not block unless explicitly required
    - Referenced from AGENTS.md or orchestration contract doc (single canonical name for governance doc)


- [x] P1: Hint levels for coordinator and fix-CI tasks
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR #866 (docs/agent-task-evaluation-contract)
  - Status: ✅ Completed (PR #866, 2026-02-22, merge SHA `fdd31e21`)
  - Area: orchestration / agents
  - Finding Type: process
  - Reason: EVMbench shows hints (low/medium/high) materially improve outcomes. Document hint levels for "fix CI" and coordinator tasks (e.g. low = branch + run link; medium = failed job + log; high = exact assertion + location).
  - Links:
    - `docs/audit/EVMBENCH_INSPIRED_AGENT_EVALUATION_BRAINSTORM_2026-02-21.md`
    - `docs/orchestration/workflow.md`
    - [PR #866](https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/866)
  - DoD:
    - [x] Orchestration doc or coordinator prompt template includes hint-level definitions
    - [x] ci-watcher / loop-on-ci prompts aligned where applicable


- [x] P1: Minimal agent metrics (fix rate / first-run pass)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: [PR #868](https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/868)
  - Status: ✅ Completed (PR #868, 2026-02-22)
  - Merge SHA: bb7b0c619c7fd88b1dd729a7ed9d34913e30292b
  - Area: orchestration / quality
  - Finding Type: metrics
  - Reason: Define minimal agent metrics (e.g. "CI fix: pass within N iterations"; "merge readiness: first run vs after edits") and record in ledger or audit when relevant.
  - Links:
    - `docs/audit/EVMBENCH_INSPIRED_AGENT_EVALUATION_BRAINSTORM_2026-02-21.md`
    - [PR #868](https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/868)
  - DoD:
    - [x] Doc or ledger section defines at least 2 agent task metrics and when to record them
    - [x] No dashboard required; manual or opportunistic recording is acceptable


- [x] P1: Move Fixed in Commit Mapping source-of-truth from PR body to repo file
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR #998 (`fix/orch-move-fixed-mapping-sot-to-repo-file`)
  - Status: ✅ Merged (PR #998, 2026-03-07)
  - Area: orchestration / CI / review governance
  - Finding Type: process hardening
  - Reason: Eliminate PR body race/staleness and make governance deterministic on git SHA.
  - Links:
    - `scripts/orchestration/review_mapping_artifact.py` (canonical artifact helper)
    - `docs/review/PR_<N>_FIXED_MAPPING.md` (artifact format)
    - `scripts/ci/check_pr_body_phase2_gates.py`, `scripts/ci/check_pr_merge_readiness.py`, `scripts/orchestration/check_review_threads_disposition.py` (artifact-first)
  - DoD:
    - [x] Merge readiness/disposition reads mapping from `docs/review/PR_<N>_FIXED_MAPPING.md`
    - [x] PR body optional summary/mirror only
    - [x] Tests added (`tests/test_review_mapping_artifact.py`, Phase2 artifact test)

<a id="ledger-p1-compliance-runtime-slice-2"></a>
- [ ] P1: Compliance runtime slice 2 for AI wellness consent orchestration
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (privacy/compliance)
  - Target PR: PR-TBD (`feat/compliance-runtime-slice-2-consent-dsar`)
  - Status: Planned
  - Area: backend / compliance / legal-runtime
  - Finding Type: deferred follow-up
  - Reason: Compliance Runtime Slice 1 ships transparency, privacy payload assembly, and minimization only. This follow-up is intentionally narrowed to AI wellness consent context/orchestration so it does not duplicate the broader P0 EU-first compliance control plane epic.
  - Carryover From:
    - PR `#1046` (`feat: EU-first compliance control plane`)
    - `docs/review/PR_1046_FIXED_MAPPING.md`
  - Carryover Note: Public DSAR/export/delete boundaries and regulated/provider-lane separation remain tracked by the P0 epic at `#ledger-p0-eu-compliance-control-plane-follow-through`; this P1 item owns only the next tactical consent slice for wellness AI surfaces.
  - Links:
    - `#ledger-p0-eu-compliance-control-plane-follow-through`
    - `core/compliance/privacy.py`
    - `core/compliance/dsar.py`
    - `docs/compliance/AI_TRANSPARENCY_AND_PROFILING_NOTICE.md`
    - `docs/legal/Privacy.md`
  - DoD:
    - Backend consent context is defined for AI wellness surfaces without changing deterministic wellness calculations
    - AI wellness routes expose explicit consent-context requirements in runtime/docs without introducing a regulated/clinical lane
    - DSAR/export/delete public-surface decisions remain linked to the P0 epic and are not duplicated in this slice
    - `pre-commit run --all-files` and `make verify` pass in PR scope


- [x] P1: Orchestration — add `AGENT_KNOWLEDGE_MAP.md` (agent → RAG corpus / index policy SoT)
  - Owner: @katsiaryna_kavaleuskaya
  - Target PR: PR #963
  - Status: merged 2026-03-04 (79024d70)
  - Priority: P1
  - Area: orchestration / RAG
  - Finding Type: policy gap
  - Reason: AGENT_CONTEXT_MAP and AGENT_CAPABILITY_MATRIX exist; AGENT_CORPUS_MAP exists in core/rag/contracts.py. No docs-level SoT for agent → corpus → RAG index policy. Security posture (retrieved content untrusted) needs policy clarity.
  - Links:
    - `docs/contracts/RAG_CONTRACT.md`
    - `core/rag/contracts.py` (AGENT_CORPUS_MAP)
    - `docs/audit/RAG_IMPLEMENTATION_AND_AGENT_KNOWLEDGE_AUDIT.md`
    - `docs/plan/ORCHESTRATION_IMPROVEMENTS_PLAN_2026.md`
  - DoD:
    - Document `docs/orchestration/AGENT_KNOWLEDGE_MAP.md` created
    - References AGENT_CORPUS_MAP policy; boundaries + indexing scope + security posture described
    - If RAG deprioritized: close as WONTFIX with explicit reason


- [x] P1: Wave 2 experimentation framework and paywall optimization loop
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR #852 (docs/wave2-experimentation-framework)
  - Status: ✅ Completed (PR #852, 2026-02-21, merge SHA `851f1728`)
  - Area: product / growth / analytics
  - Finding Type: growth optimization
  - Locations:
    - `docs/analytics/EXPERIMENTATION_FRAMEWORK.md`
    - `docs/analytics/EXPERIMENT_REGISTRY.md`
    - `docs/analytics/ANALYTICS_INDEX.md`
  - Reason: establish repeatable A/B lifecycle with measurable guardrails for onboarding and paywall conversion.
  - Links:
    - `docs/analytics/EXPERIMENT_REGISTRY.md`
    - `docs/analytics/ANALYTICS_INDEX.md`
    - `docs/analytics/EXPERIMENTATION_FRAMEWORK.md`
    - [PR #852](https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/852)
  - DoD:
    - [x] Experiment lifecycle states documented
    - [x] Initial prioritized growth experiments registered with owners and dates
    - [x] Guardrail metrics required for promotion decisions


- [x] P1: Implement WebSocket endpoint with security from start
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (feature + security)
  - Target PR: PR #818
  - Status: ✅ Merged (PR #818, 2026-02-19)
  - Reason: Canonical `/ws` endpoint and security behavior are now validated with deterministic tests. Authentication and rate-limit close behavior are covered to prevent drift.
  - Links:
    - [PR #818](https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/818)
    - tests/test_realtime_ws_security.py
    - app/routers/realtime_ws.py
    - docs/rfc/TON_RFC.md (WebSocket mentioned as requirement for real-time functions)
    - docs/design/NUTRITION_COACHING_DESIGN.md (potential use case: real-time coaching)
  - Prerequisites:
    - ✅ Security requirements defined (auth + rate-limiting)
    - ✅ Use cases defined (what real-time features need WebSocket)
  - DoD:
    - ✅ WebSocket endpoint `/ws` available with FastAPI WebSocket support
    - ✅ Authentication required (token in query params or headers)
    - ✅ Rate-limiting implemented (per-user message limits in router policy)
    - ✅ Tests verify unauthenticated connections are rejected (close code policy)
    - ✅ Tests verify rate-limiting closes connection when the limit is exceeded
    - ✅ CI checks green on merged PR (#818)


- [x] P1: Verify and secure WebSocket endpoint (if exists) — RESOLVED
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (security)
  - Target PR: N/A (investigation only)
  - Status: ✅ Resolved — No WebSocket endpoints found
  - Reason: Comprehensive codebase search found no WebSocket endpoints (`@app.websocket`, `/ws` path, WebSocket imports). Original analysis was false positive — WebSocket never existed or was removed. Security gap does not exist (no endpoint to secure).
  - Links:
    - docs/audit/WEBSOCKET_ANALYSIS.md (investigation results)
    - docs/audit/LEGACY_APP_MIGRATION_STATUS.md (WebSocket section — updated)
    - docs/audit/AUDIT_GAPS_ANALYSIS.md (WebSocket authentication gap — false positive)
  - DoD:
    - ✅ Searched entire codebase for WebSocket endpoints (no matches found)
    - ✅ Verified no WebSocket routes in `legacy_app.py`, `app/routers/*`, `app/main.py`
    - ✅ Checked OpenAPI schema (no WebSocket paths)
    - ✅ Identified false positives (test fixes, frontend dependency, docs references)
    - ✅ Marked as resolved — security gap does not exist


- [x] P1: Oracle / known-good gate behavior documentation
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: [PR #868](https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/868)
  - Status: ✅ Completed (PR #868, 2026-02-22)
  - Merge SHA: bb7b0c619c7fd88b1dd729a7ed9d34913e30292b
  - Area: runbooks / CI gates
  - Finding Type: process
  - Reason: EVMbench validates graders on oracle solutions. Document expected behavior of merge_readiness_gate and dependency_security_guard on known-good input (e.g. PR with all checkboxes and mapping → pass).
  - Links:
    - `docs/audit/EVMBENCH_INSPIRED_AGENT_EVALUATION_BRAINSTORM_2026-02-21.md`
    - `scripts/ci/check_pr_merge_readiness.py`
    - `tests/test_dependency_security_guard.py`
    - [PR #868](https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/868)
  - DoD:
    - [x] RUNBOOK or test doc: "Expected: PR body with [x] and mapping → merge_readiness passes"
    - [x] Optional: deterministic test that applies known-good PR body and asserts gate pass


- [x] P1: Runbook coverage step — full guard suite and no related violations
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR #866 (docs/agent-task-evaluation-contract)
  - Status: ✅ Completed (PR #866, 2026-02-22, merge SHA `fdd31e21`)
  - Area: runbooks / guards
  - Finding Type: process
  - Reason: EVMbench scores on comprehensive coverage. Before closing a guard/security PR, run full guard suite and ensure no related violations in changed modules.
  - Links:
    - `docs/audit/EVMBENCH_INSPIRED_AGENT_EVALUATION_BRAINSTORM_2026-02-21.md`
    - `RUNBOOK_AGENT.md`
    - [PR #866](https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/866)
  - DoD:
    - [x] RUNBOOK step added: "Run full guard suite; confirm no related violations in changed modules"
    - [x] Referenced from PR template or merge checklist where applicable


- [x] P1: Agent-as-attacker threat model section in security baseline
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: [PR #868](https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/868)
  - Status: ✅ Completed (PR #868, 2026-02-22)
  - Merge SHA: bb7b0c619c7fd88b1dd729a7ed9d34913e30292b
  - Area: security / agent control plane
  - Finding Type: security documentation
  - Reason: EVMbench measures exploit capability; we should document abuse scenarios (what would an agent need to do to violate policy?) and map to controls (allowlist, audit trail, token TTL).
  - Links:
    - `docs/audit/EVMBENCH_INSPIRED_AGENT_EVALUATION_BRAINSTORM_2026-02-21.md`
    - `docs/security/AGENT_CONTROL_PLANE_SECURITY_BASELINE.md`
    - [PR #868](https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/868)
  - DoD:
    - [x] New section in AGENT_CONTROL_PLANE_SECURITY_BASELINE: "Agent-as-attacker scenarios" with mapping to existing controls
    - [x] No new runtime code required; doc only


- [x] Resolve CVE-2026-24882 Trivy alert (superseded by production package removal)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-615 (merged); superseded by `codex/fix-main-trivy-container-cves`
  - Status: Historical suppression posture superseded. The final `production` Docker target now removes `gpgv`, and CI blocks its return with the Docker runtime dependency-surface guard.
  - Reason: GitHub alert #515 originally reported CVE-2026-24882 (`gpgv` tpm2daemon buffer overflow) for installed version 2.2.40-1.1. PR-615 documented the then-current suppression posture. The current remediation removes `gpgv` from the final production image instead of relying on the historical waiver disposition.
  - Links:
    - `Dockerfile` (production package pruning)
    - `scripts/ci/check_docker_runtime_dependency_surface.py`
    - `docs/security/CVE-2026-24882-gpgv.md`
    - GitHub alert #515
    - `.github/workflows/trivy.yml`
    - PR-615 (merged)
  - DoD:
    - Final production image removes `gpgv`
    - CI fails if `gpgv` returns to the production image
    - `trivy/ignore-policy.rego` and `.trivyignore` do not suppress CVE-2026-24882
    - `docs/security/CVE-2026-24882-gpgv.md` is marked resolved by production package removal


- [x] P1: Home/Plate/Progress CTA runtime remediation from visual matrix SoT
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR #794 (`feat/hpp-cta-runtime-remediation`)
  - Status: ✅ Merged (PR #794, 2026-02-18)
  - Merge SHA: 9ebcca2fc377753dc3024a080e6e4f24f59b6479
  - Area: web / ios / design handoff
  - Finding Type: execution follow-up / button-level UX parity
  - Reason: `docs/design/PULSEPLATE_BUTTON_ACTION_PROMPT_MATRIX.md` formalized button-level SoT and exposed runtime gaps (iOS placeholder CTA destinations, missing deterministic CTA tests, and web paywall purchase wiring still callback-only). These follow-ups must be tracked as implementation debt, not left as doc-only intent.
  - Links:
    - PR #794
    - `docs/design/PULSEPLATE_BUTTON_ACTION_PROMPT_MATRIX.md`
    - `docs/plan/PR_HPP_CTA_RUNTIME_TASK_ANALYSIS.md`
    - `docs/plan/PR_HPP_CTA_RUNTIME_EXECUTION_PLAN.md`
    - `docs/audit/PR_HPP_CTA_RUNTIME_AUDIT.md`
    - `docs/audit/PR_HPP_CTA_RUNTIME_BRAINSTORMING.md`
    - `docs/audit/PR_HPP_CTA_RUNTIME_PR_BODY_SKELETON.md`
    - `AGENTS.md`
    - `frontend/AGENTS.md`
    - `ios/AGENTS.md`
  - DoD:
    - iOS `Add Meal` and `View Details` CTA destinations are no longer placeholders
    - Deterministic CTA-level tests exist for Home/Plate/Progress critical paths (web+iOS)
    - Web paywall CTA has production-ready purchase wiring and success/failure handling
    - Matrix `Exists Now / Missing / Implement Needed` statuses are updated after remediation PR
    - `make verify` and required CI checks are green in remediation PR


### P2

<a id="ledger-p2-fitchef-mascot-insight-endpoint"></a>
- [x] P2: FitChef mascot insight endpoint
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR `#1065`
  - Status: Merged on 10 March 2026 (`#1065`)
  - Area: AI runtime / coaching / product
  - Finding Type: execution
  - Locations:
    - `core/insight/fitchef_companion.py`
    - `app/routers/fitchef_insight.py`
    - `app/schemas/fitchef_coaching.py`
  - Reason: The first public mascot slice should expose a bounded text-only coaching surface without changing the current `/api/v1/insight` contract or reviving `/api/v1/vip/insight*` drift.
  - Links:
    - `docs/contracts/FITCHEF_MASCOT_PHASE2_CONTRACT.md`
    - `docs/contracts/API_CANONICAL_MAP.md`
    - `docs/design/NUTRITION_COACHING_DESIGN.md`
    - `core/insight/creative_scientific_innovations.md`
    - `docs/review/PR_1065_FIXED_MAPPING.md`
  - DoD:
    - `POST /api/v1/insight/fitchef` exists as VIP-only mascot surface
    - Request/response schemas are typed and documented in OpenAPI
    - Rate-limit, monthly quota, policy audit, and wellness-language validation follow canonical insight ordering
    - `/api/v1/insight` remains unchanged
    - Contract tests cover `200` plus representative failure cases and assert JSON `Content-Type` plus standardized error fields
    - One happy-path integration test lands in the same PR
    - Output-shaping path is deterministic and documented in the PR IN/OUT spec, test plan, and rollback note
  - Blockers: Depends on [P2: FitChef sandbox Phase 2 deferred scope](#ledger-p2-fitchef-sandbox-phase-2-deferred-scope)

<a id="ledger-p2-fitchef-weekly-reflection-endpoint"></a>
- [x] P2: FitChef weekly reflection endpoint
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR `#1071`
  - Status: Merged on 10 March 2026 (`#1071`)
  - Area: AI runtime / coaching / product
  - Finding Type: execution
  - Locations:
    - `core/insight/fitchef_companion.py`
    - `app/routers/fitchef_insight.py`
    - `app/schemas/fitchef_coaching.py`
  - Reason: Weekly reflection is the second mascot scenario and should reuse the same bounded FitChef coaching runtime instead of inventing a separate route family or client-owned workflow.
  - Links:
    - `docs/contracts/FITCHEF_MASCOT_PHASE2_CONTRACT.md`
    - `docs/design/NUTRITION_COACHING_DESIGN.md`
    - `core/insight/creative_scientific_innovations.md`
    - `docs/review/PR_1071_FIXED_MAPPING.md`
  - DoD:
    - `POST /api/v1/insight/fitchef/weekly-reflection` exists with shared coaching envelope
    - Response uses `scenario=\"weekly_reflection\"` and returns bounded action items
    - Tier/rate-limit/quota/audit posture matches the mascot insight endpoint
    - No persistence, exports, or client-owned orchestration is added
    - Contract tests cover `200` plus representative failure cases and assert JSON `Content-Type` plus standardized error fields
    - One happy-path integration test lands in the same PR
    - Output-shaping path is deterministic and documented in the PR IN/OUT spec, test plan, and rollback note
  - Blockers: Depends on [P2: FitChef mascot insight endpoint](#ledger-p2-fitchef-mascot-insight-endpoint)

<a id="ledger-p2-fitchef-slip-support-endpoint"></a>
- [x] P2: FitChef slip-support endpoint
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR #1076 (`feat(fitchef): add slip-support endpoint`)
  - Status: Merged on 10 March 2026 (`#1076`)
  - Area: AI runtime / coaching / product
  - Finding Type: execution
  - Locations:
    - `core/insight/fitchef_companion.py`
    - `app/routers/fitchef_insight.py`
    - `app/schemas/fitchef_coaching.py`
  - Reason: Slip-support is the third mascot scenario and should normalize recovery-oriented coaching into the same text-only runtime instead of introducing reminders, exports, or autonomous background work.
  - Links:
    - `docs/contracts/FITCHEF_MASCOT_PHASE2_CONTRACT.md`
    - `docs/design/NUTRITION_COACHING_DESIGN.md`
    - `core/insight/creative_scientific_innovations.md`
    - `docs/review/PR_1076_FIXED_MAPPING.md`
  - DoD:
    - `POST /api/v1/insight/fitchef/slip-support` exists with shared coaching envelope
    - Response uses `scenario=\"slip_support\"` and excludes therapy or medicalized language
    - Non-judgmental recovery guidance is covered by deterministic tests
    - No reminders, background jobs, realtime fan-out, or export hooks are added
    - Contract tests cover `200` plus representative failure cases and assert JSON `Content-Type` plus standardized error fields
    - One happy-path integration test lands in the same PR
    - Output-shaping path is deterministic and documented in the PR IN/OUT spec, test plan, and rollback note
  - Blockers: Depends on [P2: FitChef mascot insight endpoint](#ledger-p2-fitchef-mascot-insight-endpoint)

<a id="ledger-p2-fitchef-runtime-orchestration-dedup"></a>
- [x] P2: FitChef runtime orchestration dedup
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR #1083 (`refactor(fitchef): deduplicate runtime orchestration path`)
  - Status: Merged on 10 March 2026 via PR #1083
  - Area: AI runtime / orchestration / tech debt
  - Finding Type: tech-debt
  - Locations:
    - `app/services/fitchef_runtime.py`
  - Reason: `run_mascot_insight_task()` and `run_weekly_reflection_task()` currently duplicate the bounded orchestration path for RAG retrieval, audit gates, quota enforcement, provider calls, and stable error mapping. This should be consolidated only after the Phase 2 slices stabilize.
  - Links:
    - `docs/contracts/FITCHEF_MASCOT_PHASE2_CONTRACT.md`
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p2-fitchef-weekly-reflection-endpoint`
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p2-fitchef-slip-support-endpoint`
    - `docs/review/PR_1083_FIXED_MAPPING.md`
  - DoD:
    - Shared orchestration helper removes duplicated FitChef VIP runtime flow without changing public route contracts
    - Mascot, weekly reflection, and slip-support still preserve feature-flag, tier, rate-limit, quota, audit, and provider error ordering
    - Deterministic regression tests cover the shared helper paths
  - Blockers: None

<a id="ledger-p2-monthly-pr-analysis-cadence"></a>
- [ ] P2: Monthly PR analysis cadence and evidence hygiene
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR-TBD-MONTHLY-PR-ANALYSIS-REFRESH
  - Status: 🟡 In progress (February-March 2026 baseline artifact added)
  - Area: docs / governance / reporting
  - Finding Type: reporting hygiene
  - Reason (EN): Monthly retrospective summaries are useful for program steering, but they must remain evidence-first and must not become a second source of truth for backlog closure, merge readiness, or release status. A tracked cadence item keeps the artifact honest and versioned.
  - Links:
    - `docs/review/MONTHLY_PR_ANALYSIS_2026-03.md`
    - `docs/roadmap/BACKLOG_LEDGER.md`
    - `docs/orchestration/TOP20_PR_RECOVERY_TASK_PACKETS_2026-03-08.md`
    - `docs/roadmap/P0_MASTER_CHECKLIST_PHASE_FIT_TRIAGE_2026-03-05.md`
  - DoD:
    - Monthly analysis artifact exists under `docs/review/` with explicit period and source list
    - Summary distinguishes closed items from materially advanced but still open work
    - Report explicitly points back to canonical SoTs (`BACKLOG_LEDGER`, Top-20 queue, phase-fit checklist)
    - Future monthly refreshes supersede prior snapshots via new versioned artifacts instead of silent rewrites
    - Docs-only PR stays narrow and does not introduce runtime or contract drift

- [x] P2: Philosophy Validator (runtime LLM output validation)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2 (quality / safety)
  - Target PR: PR #972 (`feat/philosophy-validator-core`)
  - Status: ✅ Merged (PR #972, 2026-03-04)
  - Reason (EN): Deterministic runtime validator for LLM outputs used in product copy/coaching. `validate_llm_output(text, domain=None) -> Report`; BLOCKER codes: WELLNESS_MEDICAL_CLAIM_*, WELLNESS_GUARANTEE, NON_FALSIFIABLE_VAGUE, POTENTIAL_CONTRADICTION. No network, regex/rules only. Coordinator can require rewrite before merge.
  - Links:
    - `core/insight/philosophy_validator.py`
    - `tests/test_philosophy_validator.py`
  - DoD:
    - `core.insight.philosophy_validator` module merged
    - Unit tests pass (RU/EN blockers, contradiction, determinism)
    - AGENTS.md policy: LLM outputs must pass philosophy_validator (BLOCKER = rewrite)


- [x] P2: Philosophy-agent + RAG validation pipeline
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2 (AI / RAG / philosophy)
  - Target PR: feat/p2-philosophy-rag-pipeline
  - Status: ✅ Implemented (2026-03-02)
  - Reason (EN): Pipeline query → RAG → philosophy-agent → LLM so that RAG context is validated before response; per BACKLOG Philosophical logic principles.
  - Links:
    - `docs/audit/RAG_IMPLEMENTATION_AND_AGENT_KNOWLEDGE_AUDIT.md` (sect. 3.2)
    - `docs/insights/PHILOSOPHICAL_LOGIC_LLM_RELIABILITY.md`
    - `.cursor/agents/philosophy-agent.md`
    - `core/rag/philosophy_pipeline.py` (4-stage pipeline implementation)
  - DoD:
    - RAG context passed to philosophy validation layer; integration test
    - `make verify` passes
  - Evidence:
    - 4-stage deterministic pipeline: rule validation → claim classification → source alignment → logical consistency
    - Stage 1 blocks (medical/weasel/malformed); stages 2-4 advisory-only warnings
    - 42 unit tests in `tests/test_philosophy_pipeline.py`
    - diff-coverage 98% (>=97%)


- [x] P2: RAG chunk content redaction helper (PII/sensitive data)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2 (defense-in-depth; corpus is controlled server docs)
  - Target PR: PR #1010
  - Status: Done (merged in PR #1010)
  - Reason (EN): The redaction helper was added and wired into prompt assembly and response previews as part of the Wave 4 runtime closure.
  - Links:
    - `app/routers/cbt_insight.py:186-196` (chunk content usage)
    - `PR #942` CodeRabbit comment (`2868000571`)
  - DoD:
    - Add redact_rag_context_for_insight() helper (or equivalent)
    - Apply to prompt assembly and response previews
    - Unit tests for redaction patterns


- [x] P2: RAG for CBT agent (first domain agent)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2 (AI / RAG / coaching)
  - Target PR: feat/p2-rag-cbt-agent
  - Status: Implemented
  - Reason (EN): Connect CBT/coaching flow to RAG per AGENT_CORPUS_MAP; first agent to use retrieval before LLM.
  - Implementation (EN):
    - Created CBT corpus documents: `docs/cbt/cognitive_restructuring.md`, `docs/cbt/thought_records.md`, `docs/psychology/motivation_theories.md`
    - Added `AGENT_CORPUS_MAP` to `core/rag/contracts.py` with cbt-agent mapping
    - Implemented corpus filtering in `core/rag/vector_rag.py` and `core/rag/simple_rag.py`
    - Created PRO-gated endpoint `POST /api/v1/pro/cbt/insight` in `app/routers/cbt_insight.py`
    - Feature-flagged via `FEATURE_CBT_AGENT` env var
  - Links:
    - `docs/audit/RAG_IMPLEMENTATION_AND_AGENT_KNOWLEDGE_AUDIT.md` (sect. 4.2, 4.3)
    - `docs/contracts/RAG_CONTRACT.md` (Corpus Routing)
    - `.cursor/agents/cbt-psychologist-agent.md`
  - DoD:
    - CBT path retrieves context from docs/cbt/ (or configured corpus); context passed to LLM
    - Tier-gated (PRO/VIP); tests; `make verify` passes


- [x] OpenAPI debt for `/api/v1/export/sign` reclassified as internal contract
  - Owner: @katsiaryna_kavaleuskaya
  - Target PR: PR #1035 (`fix(export): harden signing secret access`)
  - Status: ✅ Merged (PR #1035, 2026-03-08)
  - Priority: P2
  - Area: backend / OpenAPI / frontend contract
  - Finding Type: contract-clarification
  - Location: `app/routers/plan_export.py`, `frontend/src/lib/sharedLinks.ts`
  - Reason: Resolved in PR #1035: `/api/v1/export/sign` remains intentionally hidden from canonical public OpenAPI, keeps the stable runtime JSON shape `{url, exp, ttl}`, and preserves the explicit internal web-adapter boundary via a local typed adapter.
  - Links:
    - `app/routers/plan_export.py`
    - `frontend/src/lib/sharedLinks.ts`
    - `legacy_app.py`
    - `docs/review/PR_1035_FIXED_MAPPING.md`
  - DoD:
    - Backend keeps `SignedLinkResponse` as the runtime response model
    - `POST /api/v1/export/sign` keeps the stable JSON shape `{url, exp, ttl}` with regression coverage
    - Public OpenAPI continues to exclude export endpoints
    - Web keeps a local typed adapter with explicit rationale for the hidden-schema boundary


- [x] P2: Execution Wave 4 — Semantic retrieval (pgvector + multilingual embeddings)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR #902 (`docs/food-db-w4-kickoff`) + PR #905 (`feat(food-db): add W4-B feature-flag semantic search routing`) + PR #914 (`feat/food-w4-benchmark-rollback-closure`)
  - Status: ✅ Merged (W4-A #902, W4-B #905, W4-C #914 all merged 2026-02-26)
  - Area: backend / search relevance
  - Finding Type: strategic enhancement
  - Reason: Semantic retrieval is valuable but should follow stable snapshot/search/menu foundations and remain optional behind a feature flag.
  - Execution Notes:
    - (2026-02-25) W4-A kickoff docs merged in PR #902
    - (2026-02-25) W4-B runtime merged in PR #905 (feature-flagged `semantic > compat > legacy`)
    - (2026-02-26) W4 benchmark + rollback validation bundle prepared in PR #914
      - Added semantic benchmark harness: `scripts/benchmarks/food_semantic_retrieval_benchmark.py`
      - Added rollback-safe tests for semantic flag-off path: `tests/test_food_store_service.py`, `tests/test_foods_router_additional.py`
      - Added benchmark audit artifact/report: `docs/audit/PR_914_FOOD_DB_W4_SEMANTIC_BENCHMARK.md`, `docs/audit/artifacts/food_w4_semantic_benchmark.json`
  - Links:
    - `docs/architecture/FOOD_DATABASE_PLATFORM_STRATEGY_v1.md`
    - `docs/orchestration/RESEARCH_TRACK_PROTOCOL.md`
    - `scripts/benchmarks/food_semantic_retrieval_benchmark.py`
    - `docs/audit/PR_914_FOOD_DB_W4_SEMANTIC_BENCHMARK.md`
  - DoD:
    - Feature-flagged semantic retrieval is implemented
    - Cost/performance benchmark is documented
    - Rollback-safe deployment path is defined and validated
    - Non-semantic search path remains default and stable

<a id="ledger-p2-search-meili-transport-pooling"></a>
- [x] P2: Search Meili transport pooling + lifecycle hook
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR #1340
  - Status: ✅ Merged (PR #1340, 2026-04-05). `app/bootstrap/food_search.py` owns `httpx.Client` limits + `app.state.meili_http_client`; `make_pooled_httpx_transport` + shutdown `threading.Event` in `search_meili.py`, shutdown handler; tests cover reuse, shutdown, baseline-after-meili, idempotent dispose, and `app.state` cleanup after `TestClient`. Evidence: `docs/review/PR_1340_FIXED_MAPPING.md`, `tests/test_food_search_foundation.py`.
  - Area: backend / search
  - Finding Type: runtime hardening follow-up
  - Reason: The search shadow foundation intentionally keeps an injected per-call `httpx.Client` transport because Meili remains optional and low-volume in this slice. If traffic expands, the backend should move to a shared pooled client with deterministic shutdown semantics instead of creating a fresh client per request.
  - Links:
    - `app/services/search_meili.py`
    - `app/bootstrap/food_search.py`
    - `docs/review/PR_1099_FIXED_MAPPING.md`
    - `docs/review/PR_1340_FIXED_MAPPING.md`
  - DoD:
    - Shared Meili transport/client is lifecycle-managed and explicitly closed on shutdown
    - Search bootstrap owns transport configuration instead of hidden module-level state
    - Tests cover connection reuse and shutdown cleanup without changing `/api/v1/foods*` contracts

<a id="ledger-p2-search-pgtrgm-candidate-generation"></a>
- [ ] P2: Search PostgreSQL `pg_trgm` candidate generation lane
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: [#1349](https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1349) (Phase 1 DDL + docs; full DoD remains open until runtime lane + tests)
  - Area: backend / search
  - Finding Type: deferred hybrid-search rollout
  - Reason: This PR intentionally preserves SQLite/FTS as the live baseline and adds Meili shadow mode only. PostgreSQL `pg_trgm` candidate generation remains deferred until PostgreSQL is promoted to the canonical search-adjacent store.
  - Progress (Phase 1 — DDL + docs, this slice): Alembic enables `pg_trgm` on PostgreSQL and creates `ix_foods_*_gin_trgm` indexes when `public.foods` exists; ADR + deploy note document scope. Runtime trigram candidate queries + strategy routing remain **open** until this checkbox closes.
  - Links:
    - `app/services/search_meili.py`
    - `app/services/food_store.py`
    - `docs/review/PR_1099_FIXED_MAPPING.md`
    - `docs/review/PR_1349_FIXED_MAPPING.md`
    - `docs/architecture/ADR_SEARCH_PGTRGM_CANDIDATES_LANE_P2.md`
    - `alembic/versions/202604060001_enable_pg_trgm_foods_candidate_indexes.py`
    - `docs/orchestration/task_analysis_SEARCH_PGTRGM_CANDIDATES_P2.md`
  - DoD:
    - `pg_trgm` candidate generation exists behind additive strategy routing with deterministic fallback
    - Relevance and latency tests cover candidate generation for representative food queries
    - `/api/v1/foods*` contracts remain unchanged and shadow divergence is observable

<a id="ledger-p2-search-zero-downtime-swap-orchestration"></a>
- [ ] P2: Search zero-downtime swap orchestration lane
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR #1365 (<https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1365>)
  - Area: backend / search / ops
  - Finding Type: deferred indexing-orchestration rollout
  - Reason (EN): Offline CLI + orchestrator on branch `swap/zero-downtime` implement build/validate/warm/swap without new public HTTP routes. Mark this checkbox after merge via the mandatory docs-only ledger follow-up; remaining DoD (grace-period cleanup / rollback tests) may need a follow-up PR if not fully satisfied in #1365.
  - Links:
    - `app/services/food_search_indexing.py`
    - `app/services/meili_swap_orchestration.py:46`
    - `scripts/meili_food_index_swap.py:1`
    - `tests/test_meili_swap_orchestration.py:1`
    - `docs/deploy/MEILISEARCH_ZERO_DOWNTIME_SWAP_RUNBOOK.md:1`
    - `docs/orchestration/MEILI_SWAP_PR_READINESS.md:1`
    - `docs/review/PR_1099_FIXED_MAPPING.md`
    - `docs/orchestration/plan_SEARCH_ZERO_DOWNTIME_SWAP_FOLLOWUP.md`
  - DoD:
    - Offline build-validate-warm-swap workflow is implemented with deterministic commands or admin surface
    - Swap orchestration is tested against `*_v2` indexes without changing public food API contracts
    - Grace-period cleanup and rollback-safe recovery are documented and covered by tests

<a id="ledger-p2-food-store-legacy-schema-cache-follow-through"></a>
- [ ] P2: Food-store legacy schema/cache seam follow-through
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR-TBD-FOOD-STORE-LEGACY-SCHEMA-FOLLOW-THROUGH
  - Area: backend / search / tests
  - Finding Type: hotfix follow-up hardening
  - Reason: The main-stabilization hotfix intentionally stays narrow and fixes the
    blocking stale-`has_conf=True` failure path for legacy SQLite schemas missing
    `foods.nutrition_confidence`. Two adjacent non-blocking follow-ups remain
    deferred: a real-SQLite runtime regression for the semantic bootstrap read path,
    and a tighter policy for transient `PRAGMA table_info(foods)` failures so a
    temporary schema-probe error does not cache `False` longer than intended.
  - Links:
    - `app/services/food_store.py`
    - `tests/test_food_store_service.py`
    - `tests/test_food_store_coverage.py`
    - `tests/test_food_store_coverage_boost.py`
    - `tests/test_simple_coverage_boost.py`
  - DoD:
    - Semantic candidate/bootstrap read path has a real SQLite legacy-schema regression test
    - Schema-probe transient failures are non-cacheable or bounded-retry, not an indefinite cached `False`
    - Cache-seam tests remain deterministic and explicitly reset shared state
    - Public `/api/v1/foods/search` contract remains unchanged while additive `nutrition_confidence` stays best-effort


- [x] Test skips cleanup (low priority batch) — superseded by PR-728 classification
  - Owner: @katsiaryna_kavaleuskaya
  - Target PR: PR-728
  - Priority: P2
  - Status: ✅ Superseded (2026-02-13)
  - Area: backend / tests
  - Finding Type: skip/xfail
  - Reason: Replaced by prioritized split into P0/P1 stabilization tracks and explicit product-decision backlog.
  - Links:
    - `docs/audit/SKIPPED_TESTS_CLASSIFICATION_AUDIT_2026-02-13.md`
    - `docs/audit/PR_585_BACKLOG_SWEEP_AUDIT.md`
  - DoD:
    - Superseded by targeted items: PR-729, PR-730, PR-731, PR-732
    - Intentional product-scope skips tracked separately (no mixed bucket)


- [x] Dialogue Visualization (interaction graph)
  - Owner: @katsiaryna_kavaleuskaya
  - Target PR: PR #796
  - Status: ✅ Merged (PR #796, 2026-02-18)
  - Merge SHA: `fca3d6e7e2f2ab40a2cc4222e4330a30456e1a0b`
  - Priority: P2
  - Area: dev-process / orchestration
  - Finding Type: tooling
  - Reason: Multi-agent dialogue is hard to audit without a visual interaction graph.
  - Links:
    - PR #796: <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/796>
    - docs/orchestration/AGENT_DIALOGUE_TEMPLATE.md
    - docs/orchestration/workflow.md
    - docs/plan/PR_ORCHESTRATION_DIALOGUE_VISUALIZATION_TASK_ANALYSIS.md
    - docs/plan/PR_ORCHESTRATION_DIALOGUE_VISUALIZATION_EXECUTION_PLAN.md
    - docs/audit/PR_ORCHESTRATION_DIALOGUE_VISUALIZATION_BRAINSTORMING.md
    - docs/audit/PR_ORCHESTRATION_DIALOGUE_VISUALIZATION_AUDIT.md
    - docs/audit/PR_ORCHESTRATION_DIALOGUE_VISUALIZATION_PR_BODY_SKELETON.md
  - DoD:
    - Mermaid output format defined (inputs + expected diagram)
    - Example visualization added to orchestration docs or runbook


- [x] P2: Orchestration — agent routing graph (task → domains → agents)
  - Owner: @katsiaryna_kavaleuskaya
  - Target PR: PR #967
  - Status: ✅ Merged (PR #967, 2026-03-04)
  - Priority: P2
  - Area: dev-process / orchestration
  - Finding Type: routing
  - Reason: Capability matrix is advisory; no automatic routing. Task → domain classifier → agent set makes orchestration deterministic.
  - Links:
    - `docs/orchestration/AGENT_CAPABILITY_MATRIX.md`
    - `docs/plan/ORCHESTRATION_IMPROVEMENTS_PLAN_2026.md`
  - DoD:
    - Routing graph spec or document (task → domains → agents)
    - Linked from coordinator or capability matrix


- [x] docs(infra): add `.markdownlint.json` (follow-up after PR #617)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR #775 (`docs(audit): add CP3 no-op audit and execution plan`)
  - Status: ✅ Merged (PR #775, 2026-02-17)
  - Reason: PR #617 scope reduced to docs-only (audit + handoff); markdownlint config moved out to avoid diff-coverage/CI scope. Add repo-wide markdownlint config in dedicated PR.
  - DoD: New PR with `.markdownlint.json` only; CI green; no mixing with code/audit PRs.


- [x] P2: Guards — wellness language blocker (docs safety)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2 (quality / safety)
  - Target PR: PR #969 (test/guards-wellness-language-blockers)
  - Status: ✅ Merged (PR #969, 2026-03-04)
  - Reason (EN): Deterministic CI guard to block medical/diagnostic claims in docs and public copy (wellness-only posture). Blocks RU+EN phrases: лечит, вылечит, вылечим, исцелит, диагноз, диагностирую, диагностирует; allowlist for policy docs.
  - Links:
    - `tests/guards/test_wellness_language_blockers_guard.py`
    - `tests/guards/wellness_language_allowlist.txt`
  - DoD:
    - Guard test merged; allowlist exists; fails on blocker phrases; documented marker `pulseplate-allow:blocker-example`


- [ ] P2 Optional: Evaluate PEP 751 standard lock file (pylock.toml) and/or uv + Dependabot
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2 (optional tooling improvement)
  - Target PR: TBD (evaluation first, then migration if beneficial)
  - Status: 📋 Planned
  - Reason (EN): Python ecosystem 2026: PEP 751 defines standard lock format (pylock.toml); Dependabot now supports uv. Current repo uses pip-tools (requirements.txt as lock) and pip in Dependabot — no mandatory change. Optional: evaluate migrating to standard lock file and/or uv when tooling/CI support is stable. Setuptools: we use it only as pinned dependency (security); no setup.cfg — setuptools 78.x deprecations do not affect us. (RU: Экосистема Python 2026: PEP 751 — стандартный lock-файл; Dependabot поддерживает uv. Сейчас: pip-tools + requirements.txt как lock, Dependabot на pip. Опционально: оценить переход на pylock.toml и/или uv. Setuptools: только как зависимость в requirements; setup.cfg нет — депрекации 78.x нас не затрагивают.)
  - Links:
    - docs/audit/PYTHON_SETUPTOOLS_LOCKFILE_AUDIT.md (full audit: setuptools usage, lock file strategy, Dependabot/uv)
    - REQUIREMENTS.md (current pip-compile workflow)
    - .github/dependabot.yml (pip ecosystem)
  - DoD:
    - Decision documented: adopt / defer / won't do for PEP 751 and for uv
    - If adopt: migration PR with updated REQUIREMENTS.md and CI; Dependabot config updated if uv adopted

- [ ] P2 Optional: Evaluate NVIDIA PersonaPlex for voice persona layer (assistant / coach)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2 (optional; depends on voice UX roadmap)
  - Target PR: TBD (evaluation first, then integration if approved)
  - Status: 📋 Planned
  - Reason (EN): PersonaPlex (open-source, NVIDIA) provides full-duplex speech-to-speech, persona switching, and backchannel for a "live" conversational feel. Fit: personalize AI assistant and nutrition coach by style (e.g. strict teacher, friendly consultant); optional voice mode. Current stack is text-only; PersonaPlex would be additive (voice layer). Prerequisites: NVIDIA GPU or hosted API, NVIDIA Open Model License, WebSocket/streaming for real-time audio. (RU: PersonaPlex (NVIDIA, open-source) — full-duplex S2S, переключение персон, поддакивания; можно использовать для персонализированного ассистента и коуча. Сейчас у нас только текст; голос — опционально.)
  - Links:
    - docs/audit/PERSONAPLEX_INTEGRATION_AUDIT.md (integration options, prerequisites, risks)
    - <https://huggingface.co/nvidia/personaplex-7b-v1>
    - <https://github.com/NVIDIA/personaplex>
    - docs/design/NUTRITION_COACHING_DESIGN.md (coach flows)
    - core/insight/creative_scientific_innovations.md (FitChef)
  - Prerequisites:
    - Voice UX / real-time audio on product roadmap (or explicit decision to prototype)
    - Inference option: GPU (A100/H100) or hosted API; license accepted
  - DoD:
    - Decision documented: adopt / defer / won't do for PersonaPlex voice layer
    - If adopt: persona prompts aligned with FitChef/coach; voice API (e.g. WebSocket) and security/privacy documented

- [ ] P2 Optional: Evaluate Lenny's Podcast Transcripts for insights, marketing, and Bayesian context
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2 (optional; after P0/P1 hardening and insight/coach work stable)
  - Target PR: TBD (evaluation first: curated doc vs RAG subset vs MCP)
  - Status: 📋 Planned
  - Reason (EN): Lenny's Podcast Transcripts (269 episodes, 50+ topics) provide product/growth/PMF/leadership advice from world-class PM and growth experts. Fit: enrich insights docs, marketing-strategist playbooks, Bayesian business analyzer prior/context, FitChef RAG, and nutrition coaching design. Options: (1) curated references doc, (2) RAG subset with citation, (3) MCP or internal API. License: personal/educational; internal use with attribution is low risk. (RU: Транскрипты Lenny's Podcast — продукт/рост/PMF/лидерство; можно использовать для инсайтов, маркетинга, байесовского контекста и FitChef/коучинг.)
  - Links:
    - docs/audit/LENNYS_PODCAST_INTEGRATION_AUDIT.md (mapping to insights, Bayesian, marketing, FitChef; integration options)
    - <https://github.com/ChatPRD/lennys-podcast-transcripts>
    - core/insight/analysis_insights.md
    - core/insight/creative_scientific_innovations.md
    - .cursor/agents/marketing-strategist.md
  - DoD:
    - Decision documented: adopt one option (curated doc / RAG subset / MCP) or defer / won't do
    - If adopt: implementation steps and attribution policy documented; no scope creep into P0/P1

- [ ] P2 Optional: Use Loot Drop (Startup Graveyard) as periodic anti-pattern checklist
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2 (optional; before major bets or post-launch reviews)
  - Target PR: N/A (process: run checklist, update audit if new risks)
  - Status: 📋 Planned
  - Reason (EN): Loot Drop (loot-drop.io) catalogs 925+ failed VC-backed startups with structured failure analysis (product, competition, pricing, lost focus, marketing, cash, legal/regulatory, etc.). Health/BioTech failures are 94% legal/regulatory. Use as anti-pattern checklist to avoid repeating epic fails: e.g. LLM cost burn, scope creep, wellness vs medical positioning. (RU: «Кладбище стартапов» — уроки провалов; чеклист по 10 категориям и revival themes для снижения рисков.)
  - Links:
    - docs/audit/LOOT_DROP_STARTUP_GRAVEYARD_AUDIT.md (risk matrix, PulsePlate mapping, recommendations)
    - <https://www.loot-drop.io/>
    - <https://www.loot-drop.io/insights.html>
    - core/insight/analysis_insights.md (Lessons from failed startups subsection)
  - DoD:
    - Before major product/GTM bets or post-launch review: run through Loot Drop 10 categories + revival themes
    - Update LOOT_DROP_STARTUP_GRAVEYARD_AUDIT.md if new risks or mitigations identified

- [ ] P2 Optional: Use curated repos (Frontend/UI, AI/LLM, RAG, Multimodal, MCP, ML/CV) as learning and reference
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2 (optional; when implementing RAG upgrade, multimodal pipeline, or frontend components)
  - Target PR: N/A (reference only; adopt patterns/libraries via normal PR)
  - Status: 📋 Planned
  - Reason (EN): Curated set (22 repos): Flexbox Froggy, shadcn/ui, 50projects50days, Awesome React/CSS; LLaVA, CLIP, Transformers, Awesome Multimodal ML, RAG from Scratch, Awesome LLM Apps, LLM Engineer Handbook; MCP Python SDK; Awesome ML/CV, ZenML; Qwen/Qwen-Finetuning; Spinning Up, Sutton&Barto RL; PyTorch, Awesome Generative AI. Map to our vision: RAG (RAG from Scratch, Awesome LLM Apps), multimodal/FitChef (LLaVA, CLIP, Transformers), frontend (shadcn, Awesome React), MCP (python-sdk), CV (Awesome CV, PyTorch). (RU: Закладки для RAG, multimodal, фронта, MCP, ML/CV; использовать при реализации фич.)
  - Links:
    - docs/insights/CURATED_REPOS_REFERENCE.md (full mapping to LLM_RAG, CV_ML, creative_scientific_innovations, RECURSIVE_METHODS, COMPREHENSIVE)
    - core/insight/creative_scientific_innovations.md (Curated repos reference subsection)
  - DoD:
    - When designing RAG upgrade, multimodal pipeline, or UI: consult CURATED_REPOS_REFERENCE.md for relevant repos
    - No mandatory code dependency; adopt via normal PR/backlog

- [ ] P1: Agent knowledge library template packs (domain-specific)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (process scalability)
  - Target PR: PR_TBD_AGENT_LIBRARY_TEMPLATE_PACKS
  - Status: 📋 Planned
  - Reason (EN): Bootstrap library artifacts are in place, but recurring cycles
    need reusable, domain-specific packs (security, RAG, UX, DS) to keep
    brainstorm-to-PR flow fast and deterministic without policy drift.
  - Links:
    - `docs/orchestration/AGENT_KNOWLEDGE_LIBRARY_WORKTREE_RUNBOOK.md`
    - `docs/library/index.md`
    - `docs/library/promotion/2026-02-19_agent-library-bootstrap_promotion-log.md`
    - `docs/orchestration/AGENT_CAPABILITY_MATRIX.md`
    - `docs/memory/kpp_knowledge_promotion_pipeline.md`
  - DoD:
    - Add template packs under `docs/library/templates/` for at least 4 tracks:
      security, RAG, UX/accessibility, data/evaluation
    - Each template includes routing card, evidence section, promotion target,
      and deferred-item ledger block
    - Add one worked example cycle using one template pack
    - `ReadLints` clean for all new docs

<a id="ledger-p1-invariant-family-relations-shadow"></a>
- [ ] P1: Deterministic invariant-family relations shadow lane (L1/L2/L3 umbrella)
  - Owner: @katsiaryna_kavaleuskaya (Orchestration / Security)
  - Priority: P1 (review determinism with closed authority)
  - Target PR: L1 PR #2252 (`codex/review-invariant-relations-shadow-v1-r2`), superseding PR #2250; L2 PR #2272 (`codex/repeated-invariant-family-abstraction-review-v1`); L2-EVAL v1 target branch `codex/euler-l2-eval-v1`; L3 requires a separate reviewed target PR
  - Status: L1 and bounded L2 are merged; L2-EVAL v1 is the next prospective descriptive evidence stage; collection begins only after its implementation PR merges; L3 remains closed and is not authorized by L1, L2, or L2-EVAL
  - Reason (EN): Explicit invariant-family memberships need one bounded, replayable set-relation projection so agents can compare a finite snapshot without inferring from prose or creating another graph, ontology, learning loop, review oracle, or merge authority.
  - Links:
    - `docs/orchestration/contracts/REVIEW_INVARIANT_FAMILY_RELATIONS_SHADOW_CONTRACT.md`
    - `docs/orchestration/contracts/REPEATED_INVARIANT_FAMILY_ABSTRACTION_REVIEW_CONTRACT.md`
    - `docs/orchestration/contracts/review_invariant_family_relations.v1.schema.json`
    - `docs/orchestration/contracts/INVARIANT_FAMILY_REVIEW_EPISODE_CONTRACT.md`
    - `scripts/orchestration/review_invariant_family_relations.py`
    - `scripts/orchestration/invariant_family_review_episode.py`
    - `tests/test_review_invariant_family_relations.py`
    - `tests/test_invariant_family_review_episode.py`
  - DoD:
    - L1 accepts only the closed snapshot/relations `oneOf`, normalizes explicit finite memberships, emits every canonical pair partition plus separate unknown findings, and fully validates deterministic replay with domain-separated fingerprints
    - L1 enforces input, output, diagnostic, finding, family, membership, pair, derived-reference, ID, strict-JSON, and const-false authority bounds through executable focused tests
    - L1 remains stdin/stdout only and adds no filesystem, environment, network, provider, subprocess, runtime, workflow, public API, mapping, learning, KPP, oracle, routing, review, promotion, or merge admission
    - L2 may be scoped only by a later reviewed packet that names a consumer, proves finite input ownership, and preserves L1 as a non-authoritative derived view
    - L2 consumes canonical L1 output only through the explicit post-open `task_bootstrap.py` input, triggers only on explicit family cardinality at least two, and emits no parser, semantic/causal inference, implementation-owner, review-disposition, mapping, or merge authority
    - L2-EVAL v1 prospectively retains one immutable enrollment and at most one immutable terminal receipt per repository/PR episode, validates a non-persisted joint-pass baseline, measures only explicit `C_f - J_f`, and emits deterministic descriptive cohort reports with every downstream authority grant false
    - No synthetic primary episode or empirical 5/10 cohort exists at implementation time; real qualifying PRs accrue only after L2-EVAL merges, and its interim/target-count labels are not effectiveness or L3 decisions
    - L3 may be scoped only by a later reviewed packet after a separate future human evidence decision, with measurable benefit, rollback, observability, and independent runtime/security/admission contracts; no L1, L2, L2-EVAL receipt, accrual label, or report opens that gate automatically

<a id="ledger-p1-agent-experimentation-lane"></a>
- [x] P1: Governed agent experimentation lane (PR1-PR6 orchestration epic)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (process scalability + bounded AI optimization)
  - Target PR: PR #1073 -> PR #1081 -> PR #1088 -> PR #1096 -> PR #1092 -> PR #1102 -> PR #1107
  - Status: ✅ Completed on 2026-03-11 (`a00bba2f`; PR `#1107`) with the original PR1-PR6 chain fully merged; PR `#1114` then reused the same governed lane for the next applied verification-first reliability cycle without reopening the epic
  - Reason (EN): PulsePlate now has coordinator-first workflow, KPP promotion, reflection, research track, telemetry rollups, and deterministic benchmark artifacts, but it still lacks one canonical protocol for `autoresearch`-style experiment loops. We need a governed experimentation lane so future optimization cycles can be bounded, auditable, and KPP-only instead of becoming ad-hoc autonomous mutation. (RU: Нужен единый канон для агентных циклов экспериментов, чтобы оптимизация не превращалась в неконтролируемую автомутацию репозитория.)
  - Links:
    - `docs/orchestration/AGENT_EXPERIMENTATION_PROTOCOL.md`
    - `docs/orchestration/AGENT_EXPERIMENT_PACKET_TEMPLATE.md`
    - `docs/orchestration/workflow.md`
    - `docs/memory/kpp_knowledge_promotion_pipeline.md`
    - `docs/orchestration/AGENT_REFLECTION_PROTOCOL.md`
  - DoD:
    - PR1 governance SoT is merged and linked from the canonical orchestration docs
    - PR2 bootstrap tooling, PR3 runner MVP, PR4 promotion/telemetry, PR5 CV eval lane, and PR6 first applied reliability optimization all have explicit backlog entries
    - No phase of the lane permits hidden memory, autonomous merge, or mutation of immutable evaluation oracles
    - Sequencing stays explicit: PR1 governance -> PR2 tooling -> PR3 runner -> PR4 promotion -> PR5 CV -> PR6 reliability optimization

<a id="ledger-p1-agent-experiment-bootstrap"></a>
- [x] P1: PR2 deterministic experiment bootstrap tooling
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (dependency for the experimentation lane)
  - Target PR: PR #1081
  - Status: ✅ Merged on 2026-03-10 (`fd7a1626`)
  - Dependencies:
    - [P1 Governed agent experimentation lane (PR1-PR6 orchestration epic)](#ledger-p1-agent-experimentation-lane)
  - Reason (EN): After governance lands, the lane needs a deterministic bootstrap artifact for experiment IDs, mutable surfaces, immutable oracle lists, budgets, and routing so candidate loops can start from a structured packet instead of prompt-only instructions.
  - Links:
    - `docs/orchestration/AGENT_EXPERIMENTATION_PROTOCOL.md`
    - `docs/orchestration/AGENT_EXPERIMENT_PACKET_TEMPLATE.md`
    - `scripts/orchestration/experiment_bootstrap.py`
    - `scripts/orchestration/experiment_contract.py`
  - DoD:
    - Local experiment packet bootstrap tooling exists with deterministic JSON output
    - Packet schema covers mutable surface, immutable oracles, budgets, metrics, and promotion target
    - Outputs live under gitignored local artifacts only
    - Tooling does not mutate runtime code or public contracts

<a id="ledger-p1-agent-experiment-runner"></a>
- [x] P1: PR3 experiment runner MVP for bounded candidate loops
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (dependency for first applied optimization)
  - Target PR: PR #1088
  - Related follow-up: PR #1096 (`fix(app): restore bootstrap patchability on main`)
  - Related follow-up status: ✅ Merged (PR #1096, 2026-03-11)
  - Related follow-up SHA: `ddfee576e0d2b53d3a24e08ee58080a6c73cb75d`
  - Status: ✅ Merged with hotfix traceability (PR `#1088` delivered the bounded experiment runner MVP; PR `#1096` then remediated the post-merge `app` bootstrap/patchability regression on `main` without widening scope into FitChef, sandbox, or design lanes)
  - Dependencies:
    - [P1 Governed agent experimentation lane (PR1-PR6 orchestration epic)](#ledger-p1-agent-experimentation-lane)
    - [P1: PR2 deterministic experiment bootstrap tooling](#ledger-p1-agent-experiment-bootstrap)
  - Reason (EN): The experimentation lane needs a bounded runner that applies candidate changes only to allowlisted surfaces, evaluates them against immutable oracles, and discards regressions without touching merge/readiness flows.
  - Links:
    - `docs/orchestration/AGENT_EXPERIMENTATION_PROTOCOL.md`
    - `scripts/orchestration/experiment_contract.py`
    - `scripts/orchestration/experiment_runner.py`
    - `tests/test_experiment_bootstrap.py`
    - `tests/test_experiment_runner.py`
  - DoD:
    - Runner uses isolated execution and never mutates a dirty shared worktree
    - Runner enforces budgets and failure classes from the experimentation protocol
    - Immutable oracle mutation is rejected fail-closed
    - Runner outputs candidate result artifacts, not autonomous merge-ready commits

<a id="ledger-p1-experiment-runner-macos-strict-backend"></a>
- [x] P1: Strict macOS backend for Experiment Runner
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (restore canonical zero-network oracle evidence on the operator Mac)
  - Target PR: PR #2116 (`codex/experiment-runner-mac-strict-backend`)
  - Status: Completed in PR #2116, merged on 2026-07-14 as
    `2f253c91cc93943b1406dfa2ced19dcee9ec83b4`; Apple Container remains an
    opt-in macOS backend, with real candidate/oracle evidence, current-head
    CI, review disposition, and strict merge-readiness evidence all complete.
  - Dependencies:
    - [P1: PR3 experiment runner MVP for bounded candidate loops](#ledger-p1-agent-experiment-runner)
  - Reason (EN): The native runner correctly requires `network_budget=0`, but macOS cannot provide the Linux `unshare` primitive directly. Add one fail-closed dispatcher that proves Apple Container isolation first, proves Docker `--network none` only as a fallback, and returns non-retryable `capability_mismatch` instead of weakening network policy.
  - Links:
    - `docs/orchestration/EXPERIMENT_RUNNER_MACOS_RUNBOOK.md`
    - `docs/orchestration/contracts/experiment_runner_backend_capability.v1.schema.json`
    - `scripts/orchestration/experiment_runner_dispatch.py`
    - `deploy/experiment-runner/Containerfile`
    - `tests/test_experiment_runner_dispatch.py`
  - DoD:
    - Apple and Docker backend selection completes before an experiment and never falls back mid-run
    - Apple proves internal/no-DNS networking plus guest unshare without broad capabilities; Docker proves network-none plus the same negative canaries
    - Repository/input/root mounts are read-only, no host-writable result bind reaches the untrusted runner, the private result volume is collected read-only after PID 1 exits, and private tmpfs is bounded
    - Every dispatched run requires immutable image identity and records sanitized backend provenance
    - Existing Linux native behavior and legacy result v1 artifacts remain compatible
    - Real candidate and oracle-only Mac runs pass with `network_budget=0`, `shared_tree_untouched: true`, image scan evidence, and no secret/host-path leakage
    - Local narrow gates, post-open review chain, current-head CI, review dispositions, and strict merge-readiness complete before closure

<a id="ledger-p2-experiment-runner-pr-evidence-hard-gate"></a>
- [x] P2: Promote Experiment Runner PR evidence from advisory to hard gate
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2 (review-governance hardening after advisory signal proves stable)
  - Target PR: PR #1800 (`codex/experiment-runner-evidence-hard-gate-switch`)
  - Status: Mechanics completed in PR #1800 with advisory as the default rollback-safe mode; required-mode default activation remains deferred to a later rollout PR.
  - Dependencies:
    - [P1: PR3 experiment runner MVP for bounded candidate loops](#ledger-p1-agent-experiment-runner)
  - Reason (EN): PR #1775 introduces Phase2 advisory Experiment Runner evidence for non-trivial PR lanes. A later PR should promote that evidence to a hard merge gate only after the advisory signal is stable and false-positive behavior is understood.
  - Rollout Packet: `docs/orchestration/EXPERIMENT_RUNNER_EVIDENCE_REQUIRED_MODE_ROLLOUT_PACKET_2026-05-24.md`
  - DoD:
    - `check_pr_body_phase2_gates.py` exposes advisory/required Experiment Runner evidence modes with required mode failing closed on missing evidence
    - `check_merge_ready.py` forwards the configured Experiment Runner evidence mode to Phase2 and documents advisory rollback
    - PR-body and fixed-mapping validators share one parser contract for artifact paths and not-applicable reasons
    - Rollback notes document how to return the gate to advisory mode if review throughput regresses

<a id="ledger-p2-experiment-runner-evidence-required-mode-activation"></a>
- [ ] P2: Activate Experiment Runner evidence required mode for non-trivial lanes
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2 (controlled rollout after hard-gate mechanics)
  - Target PR: future required-mode activation PR
  - Status: Process hard gate active for non-trivial PRs; machine-default required-mode activation remains deferred until tracked evidence mirror support exists for gitignored local runner artifacts.
  - Dependencies:
    - [P2: Promote Experiment Runner PR evidence from advisory to hard gate](#ledger-p2-experiment-runner-pr-evidence-hard-gate)
  - Reason (EN): Required-mode mechanics exist and non-trivial PRs must run Experiment Runner evidence by process, but the repo default should flip only in a separate controlled PR that can isolate false positives, rollback behavior, non-trivial lane classification, and CI handling for local-only runner artifacts.
  - DoD:
    - Default required-mode activation is scoped to non-trivial PR lanes
    - Rollback path to advisory mode is documented and tested
    - Current-head CI and strict review governance remain stable after activation

<a id="ledger-p2-experiment-runner-validator-mutation-threat-model"></a>
- [ ] P2: Threat-model controlled Experiment Runner validator-script mutation access
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2 (privileged governance-surface safety)
  - Target PR: Future security-reviewed governance PR after PR #1775
  - Status: 📋 Deferred from PR #1775
  - Dependencies:
    - [P1: PR3 experiment runner MVP for bounded candidate loops](#ledger-p1-agent-experiment-runner)
  - Reason (EN): PR #1775 keeps `scripts/ci/**` mutation access disabled and fail-closed. Any future mutation access needs a separate threat model, explicit allowlist shape, forbidden-surface regression tests, identity/trailer checks, and rollback notes before the runner can touch validator scripts.
  - DoD:
    - Security threat model covers validator-script authority, review-thread authority, merge-gate authority, and rollback
    - Allowlist defaults to empty/fail-closed and has regression tests for forbidden governance surfaces
    - Identity checks require `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>` when runner artifacts materially shape commits

<a id="ledger-p1-agent-experiment-promotion"></a>
- [x] P1: PR4 experiment promotion and telemetry integration
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (governance closure for experiment outputs)
  - Target PR: PR #1092
  - Status: ✅ Merged on 2026-03-11 (`e0771be5`)
  - Dependencies:
    - [P1 Governed agent experimentation lane (PR1-PR6 orchestration epic)](#ledger-p1-agent-experimentation-lane)
    - [P1: PR3 experiment runner MVP for bounded candidate loops](#ledger-p1-agent-experiment-runner)
  - Reason (EN): Winning candidates need one governed promotion path into PR packets, audits, guards, ledger items, or memory capsules, and telemetry needs experiment-aware fields so orchestration learning remains artifact-based and observable.
  - Links:
    - `docs/orchestration/AGENT_EXPERIMENTATION_PROTOCOL.md`
    - `docs/orchestration/AGENT_REFLECTION_PROTOCOL.md`
    - `scripts/orchestration/agent_run_summary.py`
    - `scripts/orchestration/telemetry_rollup.py`
  - DoD:
    - Promotion tooling enforces exactly one durable destination per winning experiment
    - Telemetry rollups understand experiment identifiers and failure/promotion classes
    - Deferred experiment outcomes are ledgered immediately
    - No hidden-memory path bypasses KPP promotion

<a id="ledger-p1-agent-experiment-cv-lane"></a>
- [x] P1: PR5 CV experimentation and evaluation lane (docs/eval only)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (future multimodal track, no runtime integration yet)
  - Target PR: #1102
  - Status: ✅ Merged on 2026-03-11 (`55783414`; PR `#1102`)
  - Follow-up: Canonical ledger closeout normalization is implemented in PR `#1120` (this docs-only follow-up) and becomes canonical on merge.
  - Dependencies:
    - [P1 Governed agent experimentation lane (PR1-PR6 orchestration epic)](#ledger-p1-agent-experimentation-lane)
    - [CV (photo → food): contract schema + uncertainty/degrade UX states + privacy packet](#ledger-p2-cv-photo-food)
  - Reason (EN): Computer vision needs the same packetized experimentation contract as LLM/RAG work, but limited to offline evaluation, uncertainty, privacy packets, and deterministic degrade behavior before any runtime photo feature is attempted.
  - Links:
    - `docs/orchestration/AGENT_EXPERIMENTATION_PROTOCOL.md`
    - `docs/orchestration/CV_EXPERIMENTATION_PROTOCOL.md`
    - `docs/orchestration/CV_EXPERIMENT_PACKET_TEMPLATE.md`
    - `docs/orchestration/contracts/CV_PHOTO_FOOD_EVAL_CONTRACT.md`
    - `.cursor/agents/cv-agent.md`
    - `.cursor/agents/data-scientist-agent.md`
    - `docs/orchestration/IOS_FRONTEND_MULTIAGENT_PLAYBOOK.md`
    - `docs/audit/PR_1102_CV_EXPERIMENTATION_LANE_AUDIT_2026-03-11.md`
  - DoD:
    - CV experiment packet fields cover dataset, uncertainty bands, privacy constraints, and degrade states
    - CV lane remains docs/eval only with no image-retention runtime behavior
    - Coordinator routing for CV experiments is explicit and bounded
    - Deterministic acceptance criteria are documented

<a id="ledger-p1-agent-experiment-first-reliability-pr"></a>
- [x] P1: PR6 first applied LLM/RAG reliability optimization via governed lane
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (first practical output of the experimentation lane)
  - Target PR: PR #1107
  - Status: ✅ Merged on 2026-03-11 (`a00bba2f`)
  - Dependencies:
    - [P1 Governed agent experimentation lane (PR1-PR6 orchestration epic)](#ledger-p1-agent-experimentation-lane)
    - [P1: PR3 experiment runner MVP for bounded candidate loops](#ledger-p1-agent-experiment-runner)
    - [P1: PR4 experiment promotion and telemetry integration](#ledger-p1-agent-experiment-promotion)
    - [P1: Recursive methods for LLM/RAG/AI assistant (multi-hop retrieval, recursive reasoning, self-refinement, self-verification, learning)](#ledger-p1-recursive-methods)
  - Reason (EN): The first applied experiment-generated change should target `LLM/RAG reliability`, using current deterministic benchmark and test oracles to validate one bounded optimization before broader autonomous tooling is trusted.
  - Links:
    - `docs/orchestration/AGENT_EXPERIMENTATION_PROTOCOL.md`
    - `scripts/orchestration/experiment_bootstrap.py`
    - `scripts/orchestration/experiment_runner.py`
    - `tests/test_experiment_bootstrap.py`
    - `tests/test_experiment_runner.py`
  - DoD:
    - One bounded reliability candidate is generated through the governed lane
    - Candidate improvement is accepted by immutable oracles and documented with evidence
    - Result is promoted through a normal human-reviewed PR
    - No storage-cost or CV scope is mixed into this first applied optimization

<a id="ledger-p1-reliability-v2-verification-pr"></a>
- [x] P1: PR7 verification-first Reliability V2 applied orchestration cycle
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (factual trust uplift on the merged experimentation lane)
  - Target PR: PR #1114
  - Status: ✅ Merged on 2026-03-11 (`57770899`)
  - Dependencies:
    - [P1 Governed agent experimentation lane (PR1-PR6 orchestration epic)](#ledger-p1-agent-experimentation-lane)
    - [P1: PR6 first applied LLM/RAG reliability optimization via governed lane](#ledger-p1-agent-experiment-first-reliability-pr)
    - [P1: PR3 experiment runner MVP for bounded candidate loops](#ledger-p1-agent-experiment-runner)
    - [P1: PR4 experiment promotion and telemetry integration](#ledger-p1-agent-experiment-promotion)
  - Reason (EN): After the first applied reliability change proved the governed lane end to end, the next applied slice needed a verification-first runtime policy that raises factual trust for RAG-backed insight generation while preserving the public `InsightResponse` shape and bounded provider cost.
  - Links:
    - `core/insight/philosophical_runtime.py`
    - `core/rag/orchestration.py`
    - `tests/test_philosophical_runtime.py`
    - `tests/test_rag_orchestration.py`
    - `tests/test_recursive_rag.py`
    - `tests/test_insight_rag_response_fields.py`
    - `docs/review/PR_1114_FIXED_MAPPING.md`
  - DoD:
    - Verification-first gating prefers accepted RAG-backed answers with `verification_rate >= 0.7`
    - Low-verification factual/deep outputs trigger at most one bounded rewrite before a conservative fallback
    - Recursive and non-recursive paths preserve the current response contract and deterministic reason codes
    - The applied runtime change is validated by deterministic local oracles and merged through normal human-reviewed PR governance

<a id="ledger-p1-creative-research-eval-lane"></a>
- [x] P1: Creative research eval lane under governed experimentation epic
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (research moat, bounded discovery workflow)
  - Target PR: PR `#1106` -> PR `#1112` -> PR `#1118` -> PR `#1124`
  - Status: ✅ Completed in merged PRs `#1106`, `#1112`, `#1118`, and `#1124` on March 11, 2026
  - Dependencies:
    - [P1: Governed agent experimentation lane (PR1-PR6 orchestration epic)](#ledger-p1-agent-experimentation-lane)
    - [P1: PR4 experiment promotion and telemetry integration](#ledger-p1-agent-experiment-promotion)
  - Reason (EN): PulsePlate needs one governed `creative_research` sub-lane for divergence -> convergence -> verification -> promotion cycles, but it must remain inside the existing experimentation umbrella instead of becoming a second orchestration constitution. The lane should strengthen the Research / Differentiation contour, stay human-gated, and avoid public runtime exposure in wave 1.
  - Links:
    - `docs/orchestration/AGENT_EXPERIMENTATION_PROTOCOL.md`
    - `docs/orchestration/CREATIVE_RESEARCH_SUBLANE_PROTOCOL.md`
    - `docs/orchestration/CREATIVE_RESEARCH_OFFLINE_EVAL_PROTOCOL.md`
    - `docs/orchestration/contracts/CREATIVE_RESEARCH_EVAL_CONTRACT.md`
    - `docs/orchestration/RESEARCH_BRAINSTORMING_PROTOCOL.md`
    - `docs/orchestration/AGENT_EXPERIMENT_PACKET_TEMPLATE.md`
    - `scripts/orchestration/creative_research_eval.py`
    - `scripts/orchestration/creative_research_eval_contract.py`
    - `tests/test_creative_research_eval.py`
    - `tests/test_creative_research_eval_contract.py`
    - `docs/review/PR_1112_FIXED_MAPPING.md`
    - `docs/memory/kpp_knowledge_promotion_pipeline.md`
    - `docs/orchestration/CREATIVE_RESEARCH_INTERNAL_PILOT_CONTRACT.md`
    - `app/routers/creative_research_internal.py`
    - `app/services/creative_research_runtime.py`
    - `app/schemas/creative_research.py`
    - `core/creative_research.py`
    - `tests/test_creative_research_pilot_api.py`
  - DoD:
    - PR-A lands docs-only protocol and routing/evaluation/handoff visibility for `creative_research`
    - PR-B adds offline eval harness, deterministic judge contracts, negative controls, and no runtime integration
    - PR-C remains internal-only, feature-flagged, hidden from public OpenAPI, and introduces no new heavy LLM endpoint on the core path
    - The lane preserves no hidden memory, no autonomous merge, no immutable-oracle mutation, and quota-before-call for any future provider-backed pilot

<a id="ledger-p1-governed-creative-code-execution-lane"></a>
- [ ] P1: Governed creative-code execution lane (PR-0 through PR-6)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (research-to-implementation leverage with closed authority)
  - Target PR: PR-0 `feat/experiment-runner-creative-code-authority-pr0` -> PR-1 `codex/creative-code-specification-pr1` -> PR-2 `#2022` -> PR-3 `#2030` -> PR-4 `#2044` -> PR-5 `#2048` -> PR-6 `codex/creative-code-first-applied-candidate-pr6` -> private-pilot loop operator `codex/creative-code-private-pilot-loop-operator` -> GitHub App capability gate `codex/experiment-runner-github-app-capability-gate` -> approved creative-hypothesis specification bridge `codex/experiment-runner-approved-hypothesis-spec-bridge` -> creative spec learning rollup `#2075` -> patch-builder admission `codex/er-creative-spec-patch-admission` -> adaptive production-adjacent pilot `codex/er-adaptive-production-pilot` -> terminal outcome envelope `codex/creative-code-terminal-outcome-envelope-v1` -> terminal Evidence Eval projection `#2284` -> lifecycle transition analytics `#2290` -> shadow Bayesian lifecycle v1 `codex/creative-lifecycle-bayesian-shadow-v1`
  - Status: PR-0 through PR-5 and the existing private-pilot, bridge, learning-rollup, patch-admission, receipt, promotion-integrity, and adaptive planning slices remain canonical. The terminal outcome envelope, PR `#2284` Evidence Eval normalization, and PR `#2290` deterministic lifecycle transition analytics are merged continuations. The active bounded capability slice is prospective shadow forecast/start/outcome scoring for one exact PR-2 target, followed only after merge by one genuine heterogeneous bounded Pilot. The umbrella remains open; neither slice adds product code, GitHub/provider/runtime, routing/learning, prediction-quality, or merge authority.
  - Resolved carryover: PR `#2284` merged the sibling terminal Evidence Eval projection, and PR `#2290` preserved that triplet as one indivisible evidence bundle outside lifecycle transition counts.
  - Deterministic creative-code lifecycle transition analytics v1:
    - Priority: P1
    - Owner: @katsiaryna_kavaleuskaya
    - Target PR: merged PR `#2290`
    - Reason (EN): Existing v1/v2 telemetry has typed candidate and promotion lineage but no deterministic aggregate view of observed adjacent lifecycle transitions or explicitly unobserved neighbors. The slice must add that descriptive view without turning Evidence Eval rows, order, timestamps, paths, or missing artifacts into lifecycle truth.
    - Links:
      - `scripts/orchestration/creative_code_lifecycle_transition_analytics_contract.py`
      - `scripts/orchestration/creative_code_lifecycle_transition_analytics.py`
      - `docs/orchestration/contracts/creative_code_lifecycle_transition_analytics.v1.schema.json`
      - `tests/test_creative_code_lifecycle_transition_analytics.py`
    - DoD: one exact validated mixed v2 snapshot deterministically yields aggregate adjacent-transition counts, complete/incomplete terminal-lineage accounting, and fixed cycle histograms; ambiguous/incompatible/stale input fails closed; output retains no raw lineage; mode-`0600` atomic no-replace publication, byte-identical replay, read-only validation, focused tests, and normal PR governance pass; no backfill or runtime/routing/learning/merge authority is added.
  - Shadow Bayesian lifecycle forecast/scoring v1 and one prospective Pilot:
    - Priority: P1
    - Owner: @katsiaryna_kavaleuskaya
    - Target PR: `codex/creative-lifecycle-bayesian-shadow-v1`; after its merge, one separately governed heterogeneous bounded Pilot from synchronized `main`
    - Reason (EN): Merged aggregate analytics proves a deterministic descriptive capability but the real corpus is empty. The next bounded step must first add immutable local `forecast -> start -> outcome -> score` contracts and a mechanical pre-generation start hook, then exercise that rail prospectively for exactly one real target without selecting, routing, promoting, opening, or merging on forecast values.
    - Links:
      - `scripts/orchestration/creative_code_lifecycle_bayesian_shadow_contract.py`
      - `scripts/orchestration/creative_code_lifecycle_bayesian_shadow.py`
      - `docs/orchestration/contracts/CREATIVE_CODE_LIFECYCLE_BAYESIAN_SHADOW_CONTRACT.md`
      - `tests/test_creative_code_lifecycle_bayesian_shadow.py`
    - DoD: the capability PR adds the closed three-family fixed-prior contract, exact validated baseline/outcome lineage, stable fixed-root forecast/start/score slots, strict no-replace publication, and paired optional `generate-candidate` binding without changing legacy PR-2 schemas or authority. After merge, enroll exactly one genuine next Pilot only if it naturally reaches a clean accepted PR-2 gate; otherwise record `not_enrolled` and do not substitute another Pilot. Publish one immutable score at canonical terminal stop or the fixed 14-day cutoff, including honest `valid_but_unscored` or `measurement_invalid` state where applicable. Any `5000 bps` / `250000 ppm` result demonstrates measurement feasibility only; calibration, reliability, predictive skill, causal effectiveness, and product value remain `not_assessed`.
  - Carryover: PR `#2224` (`codex/creative-budget-promotion-fixture`; follow-up to PR `#2218`) restores changed-line parity only in `tests/test_creative_code_pr_promotion.py` and `tests/test_creative_code_artifact_inventory.py`; no production, schema, workflow, provider, OCW, R3, or product-behavior change.
  - Carryover remediation:
    - Owner: @katsiaryna_kavaleuskaya (Orchestration / Security)
    - Priority: P1
    - Target PR: `codex/adaptive-context-pack-lineage-fix` (follow-up to PR `#2101`)
    - Status: Active prerequisite for the first retained RAG candidate execution.
    - Reason (EN): PR `#2101` added exact adaptive PR-1 resume, but current
      validation recomputes metadata-only context size/token estimates from the
      live repository and therefore rejects an intact older retained pack after
      unrelated repository growth. The remediation must tolerate only
      self-consistent historical estimate telemetry while keeping stable
      lineage and retained bytes fingerprint-bound.
    - DoD: historical estimate-only drift passes `resume-pr1`; malformed
      arithmetic, derived IDs, bounded source-commit file-size bindings,
      scalar types, and any path, fingerprint, graph, routing, policy,
      authority, reason-code, or unknown-field drift remain fail-closed;
      current exact prepare validation stays strict; the retained pilot remains
      byte-identical;
      focused orchestration tests and normal PR governance pass.
    - Evidence: `scripts/orchestration/creative_code_spec_pipeline.py`,
      `tests/test_creative_code_specification.py`,
      `tests/test_creative_pilot_workspace.py`,
      `docs/orchestration/GOVERNED_CREATIVE_CODE_EXECUTION_CONTRACT.md`.
  - Dependencies:
    - [P1: Creative research eval lane under governed experimentation epic](#ledger-p1-creative-research-eval-lane)
    - [P1: Governed agent experimentation lane (PR1-PR6 orchestration epic)](#ledger-p1-agent-experimentation-lane)
  - Reason (EN): Promoted `creative_research` output needs a typed, auditable path into future implementation candidates without turning research artifacts into runtime truth, repository-write authority, Slack/GitHub App authority, or merge-readiness evidence. PR-0 keeps the gate closed and defines the authority boundary before any patch generation is considered.
  - Links:
    - `docs/orchestration/GOVERNED_CREATIVE_CODE_EXECUTION_CONTRACT.md`
    - `docs/orchestration/contracts/CREATIVE_CODE_CANDIDATE_CONTRACT.md`
    - `docs/orchestration/contracts/creative_code_candidate.v1.schema.json`
    - `docs/orchestration/contracts/creative_code_candidate.v1.json`
    - `docs/orchestration/contracts/CREATIVE_CODE_SPECIFICATION_CONTRACT.md`
    - `docs/orchestration/contracts/creative_code_specification.v1.schema.json`
    - `docs/orchestration/contracts/creative_code_specification.v1.json`
    - `docs/orchestration/contracts/CREATIVE_CODE_PATCH_BUILDER_CONTRACT.md`
    - `docs/orchestration/contracts/creative_code_patch_request.v1.schema.json`
    - `docs/orchestration/contracts/creative_code_patch_result.v1.schema.json`
    - `docs/orchestration/contracts/CREATIVE_CODE_PR_PROMOTION_CONTRACT.md`
    - `docs/orchestration/contracts/creative_code_pr_promotion_plan.v1.schema.json`
    - `docs/orchestration/contracts/creative_code_pr_promotion_validation.v1.schema.json`
    - `docs/orchestration/contracts/creative_code_pr_promotion_approval.v1.schema.json`
    - `docs/orchestration/contracts/creative_code_pr_promotion_receipt.v1.schema.json`
    - `docs/orchestration/contracts/CREATIVE_CODE_TELEMETRY_CONTRACT.md`
    - `docs/orchestration/contracts/creative_code_telemetry_event.v1.schema.json`
    - `docs/orchestration/contracts/creative_code_telemetry_rollup.v1.schema.json`
    - `docs/orchestration/contracts/creative_code_terminal_outcome.v1.schema.json`
    - `docs/orchestration/contracts/creative_code_telemetry_event.v2.schema.json`
    - `docs/orchestration/contracts/creative_code_telemetry_rollup.v2.schema.json`
    - `docs/orchestration/contracts/creative_code_rejection_taxonomy.v1.schema.json`
    - `docs/orchestration/contracts/creative_code_rejection_taxonomy.v1.json`
    - `docs/orchestration/contracts/creative_code_lifecycle_transition_analytics.v1.schema.json`
    - `docs/orchestration/contracts/creative_hypothesis_specification_bridge.v1.schema.json`
    - `docs/orchestration/contracts/creative_hypothesis_specification_bridge.v2.schema.json`
    - `docs/orchestration/contracts/creative_protocol_context_map.v2.schema.json`
    - `docs/orchestration/contracts/creative_hypothesis_packet.v2.schema.json`
    - `docs/orchestration/contracts/creative_hypothesis_approval.v2.schema.json`
    - `docs/orchestration/contracts/creative_pilot_workspace.v2.schema.json`
    - `docs/orchestration/contracts/creative_pilot_role_result.v2.schema.json`
    - `docs/orchestration/contracts/creative_pilot_synthesis.v2.schema.json`
    - `docs/orchestration/contracts/creative_hypothesis_spec_bridge_metrics.v1.schema.json`
    - `docs/orchestration/contracts/CREATIVE_SPEC_PATCH_ADMISSION_CONTRACT.md`
    - `docs/orchestration/contracts/creative_spec_patch_human_admission.v1.schema.json`
    - `docs/orchestration/contracts/creative_spec_patch_admission.v1.schema.json`
    - `docs/orchestration/CREATIVE_CODE_REVIEW_DISPOSITION_PR5_PREMORTEM.md`
    - `docs/orchestration/contracts/CREATIVE_CODE_REVIEW_DISPOSITION_CONTRACT.md`
    - `docs/orchestration/contracts/creative_code_review_feedback_record.v1.schema.json`
    - `docs/orchestration/contracts/creative_code_review_disposition_packet.v1.schema.json`
    - `docs/orchestration/contracts/creative_code_repair_launch_packet.v1.schema.json`
    - `docs/orchestration/contracts/CREATIVE_CODE_PRIVATE_PILOT_LOOP_OPERATOR_CONTRACT.md`
    - `docs/orchestration/contracts/creative_code_private_pilot_state.v1.schema.json`
    - `docs/orchestration/contracts/creative_code_private_pilot_candidate_plan.v1.schema.json`
    - `docs/orchestration/contracts/github_app_private_pilot_capability_report.v1.schema.json`
    - `scripts/orchestration/creative_code_contract.py`
    - `scripts/orchestration/creative_code_specification.py`
    - `scripts/orchestration/creative_code_spec_pipeline.py`
    - `scripts/orchestration/creative_code_rejection_index.py`
    - `scripts/orchestration/creative_code_patch_contract.py`
    - `scripts/orchestration/creative_code_patch_workspace.py`
    - `scripts/orchestration/creative_code_patch_executor.py`
    - `scripts/orchestration/creative_code_patch_builder.py`
    - `scripts/orchestration/creative_code_pr_promotion_contract.py`
    - `scripts/orchestration/creative_code_pr_promotion.py`
    - `scripts/orchestration/creative_code_telemetry_contract.py`
    - `scripts/orchestration/creative_code_telemetry.py`
    - `scripts/orchestration/creative_code_terminal_outcome_contract.py`
    - `scripts/orchestration/creative_code_terminal_outcome.py`
    - `scripts/orchestration/creative_code_lifecycle_transition_analytics_contract.py`
    - `scripts/orchestration/creative_code_lifecycle_transition_analytics.py`
    - `scripts/orchestration/creative_code_review_disposition_contract.py`
    - `scripts/orchestration/creative_code_review_disposition.py`
    - `scripts/orchestration/creative_code_applied_candidate_pr6.py`
    - `scripts/orchestration/creative_code_private_pilot_loop_contract.py`
    - `scripts/orchestration/creative_code_private_pilot_loop_operator.py`
    - `scripts/orchestration/github_app_private_pilot_capability.py`
    - `scripts/orchestration/creative_hypothesis_spec_bridge_contract.py`
    - `scripts/orchestration/creative_hypothesis_spec_bridge.py`
    - `scripts/orchestration/creative_pilot_workspace_contract.py`
    - `scripts/orchestration/creative_pilot_workspace.py`
    - `scripts/orchestration/creative_spec_patch_admission_contract.py`
    - `scripts/orchestration/creative_spec_patch_admission.py`
    - `tests/test_creative_code_contract.py`
    - `tests/test_creative_code_patch_builder.py`
    - `tests/test_creative_code_pr_promotion.py`
    - `tests/test_creative_code_telemetry.py`
    - `tests/test_creative_code_terminal_outcome.py`
    - `tests/test_creative_code_lifecycle_transition_analytics.py`
    - `tests/test_creative_code_review_disposition.py`
    - `tests/test_creative_code_applied_candidate_pr6.py`
    - `tests/test_creative_code_private_pilot_loop.py`
    - `tests/test_creative_hypothesis_spec_bridge.py`
    - `tests/test_creative_pilot_workspace.py`
    - `tests/test_creative_spec_patch_admission.py`
  - PR train:
    - PR-0: closed authority contract, schema, reference packet, validator, and tests; no model calls, patches, workflows, Slack/GitHub settings, or `experiment_runner.py` changes.
    - PR-1: emit deterministic implementation specification bundles from promoted creative research, with skeptic reviews, synthesis, telemetry summary, safe local artifact I/O, and fingerprint-only rejection indexes; no candidate patches, provider calls, repo writes, runtime truth, review-thread disposition authority, or merge-readiness evidence.
    - PR-2: generate isolated candidate patches only in sandboxed evaluation workspaces with exact PR-1 bundle fingerprint binding, exact `origin/main` base SHA, human admission, fixed Codex CLI argv/env, strict patch policy validation, direct Experiment Runner candidate-mode evaluation, and sanitized result metadata.
    - PR-3: allow human-approved non-draft PR creation from one accepted PR-2 patch through separate plan, isolated validation, TTY approval, promotion checkout, new `experiment/*` branch, GitHub readback, and local sanitized receipt; no real promoted candidate PR is opened during PR-3 tooling implementation.
    - PR-4: add local candidate evaluation telemetry and rejection taxonomy over sanitized PR-1/PR-2/PR-3 artifacts; no public GitHub App backend, Slack beta, live review ingestion, review-thread resolution, fixed-mapping automation, or new mutation authority.
    - Terminal outcome envelope: validate one PR-3 plan/open receipt plus one closed sanitized terminal observation, publish one immutable local outcome, and project it into exactly one v2 `pr_terminal` event. Preserve v1 schemas/identities and default collection; no third terminal state, raw review/parser intake, GitHub/network/provider/runtime/Evidence Graph call, workflow, semantic cache, or merge authority.
    - Terminal Evidence Eval projection: merged in PR `#2284`; project one terminal outcome into exactly one sibling three-row normalization bundle using existing Evidence Eval event types. The bundle is not telemetry, not three lifecycle transitions, and grants no admission, provider, runtime, promotion, or merge authority.
    - Lifecycle transition analytics: consume one exact mixed v2 telemetry snapshot, join only the closed six adjacent edges with typed lineage, emit aggregate/fingerprint-only counts and histograms, and fail closed on ambiguity, stale rollup, source drift, or divergent replay; no candidate taxonomy, backfill, duration, causal claim, learned policy, auto-routing, auto-retry, Evidence Graph, provider/network/DB, runtime, or merge authority.
    - PR-5: add local read-only review-disposition integration through `CreativeCodeReviewFeedbackRecord`, `CreativeCodeReviewDispositionPacket`, and `CreativeCodeRepairLaunchPacket`; only `create_pr1_specification=true` may be prepared for later human review, while patch generation, branch writes, PR creation, review-thread resolution, fixed-mapping edits, merge authority, runtime changes, Slack/GitHub App authority, and readiness claims remain forbidden.
    - PR-6: run the first governed applied creative-code candidate through normal PR governance, starting from a local run-plan wrapper that validates the PR-5 launch packet, binds the target surface exactly to `docs/prompts/cv/program.md`, and then keeps the generated candidate mutation surface to that prompt/program document.
    - Private-pilot loop operator: collect sanitized PR/check/review state plus PR-4 / PR-5 / PR-6 artifact refs, consume an optional sanitized GitHub App read-only capability report, decide the next action, and optionally emit a checklist-only candidate plan; no PR-1 / PR-2 / PR-3 command is executed by the operator.
    - Approved creative-hypothesis specification bridge: build a validated `CreativeCodeCandidatePacket`, deterministic `bridge_metrics.json`, and existing PR-1 `prepare` artifacts from `CreativeHypothesisApproval(decision=approve_for_pr1_specification, next_step=create_pr1_specification)`; no agent execution, `finalize`, candidate patches, provider calls, workflow changes, repository writes, product runtime truth, semantic cache, graph truth, or mutable-surface widening.
    - Follow-up bridge finalize evidence attachment:
      - Priority: P1 automation leverage.
      - Owner: orchestration.
      - Target PR: `codex/experiment-runner-agent-skeptic-review-finalize`.
      - Reason: bridge output emits pending `skeptic_reviews.json`; downstream reviewer evidence attachment and explicit `finalize` must happen in a sibling reviewed run so original bridge validation and metrics stay immutable.
      - DoD: `creative_specification_skeptic_review.py` validates operator-supplied sanitized local skeptic-review evidence, writes only `spec_finalize_reviewed/`, calls existing PR-1 `finalize`, emits a valid `CreativeCodeSpecificationBundle` plus metadata-only receipt, preserves `spec_prepare/`, and adds no patch, branch, PR, provider, workflow, runtime, semantic-cache, graph-truth, fixed-mapping, review-thread, or readiness authority.
      - Evidence: `scripts/orchestration/creative_specification_skeptic_review.py`; `scripts/orchestration/creative_specification_skeptic_review_contract.py`; `docs/orchestration/contracts/creative_specification_agent_skeptic_reviews.v1.schema.json`; `docs/orchestration/contracts/creative_specification_skeptic_review_attachment.v1.schema.json`; `docs/orchestration/contracts/creative_specification_finalize_receipt.v1.schema.json`; `tests/test_creative_specification_skeptic_review.py`.
    - Follow-up bridge metrics ingestion:
      - Priority: P1 learning-loop leverage.
      - Owner: orchestration.
      - Target PR: `codex/experiment-runner-creative-spec-learning-rollup`.
      - Status: merged in PR `#2075`.
      - Reason: bridge metrics and reviewed finalize outcomes are deterministic local sidecars but need proposal-only learning-loop ingestion before patch-builder admission can be considered.
      - DoD: finalized bridge metrics, skeptic-review attachment, finalize receipt, and `CreativeCodeSpecificationBundle` ingest into `agent_learning_record.v1` success/failure records plus coordinator advisory hints with redaction, bounded fields, no runtime telemetry, no product truth, no semantic-cache use, no graph truth, no provider calls, no patch generation, and no routing or merge-readiness authority.
      - Evidence: `scripts/orchestration/creative_spec_learning_rollup.py`; `scripts/orchestration/creative_spec_learning_rollup_contract.py`; `docs/orchestration/contracts/creative_spec_learning_rollup.v1.schema.json`; `docs/orchestration/contracts/creative_spec_coordinator_advisory_hints.v1.schema.json`; `tests/test_creative_spec_learning_rollup.py`; `tests/test_task_bootstrap.py`.
    - Follow-up finalized spec patch-builder admission:
      - Priority: P1 automation leverage.
      - Owner: orchestration.
      - Target PR: `codex/er-creative-spec-patch-admission`.
      - Status: active reviewed PR lane.
      - Reason: finalized selected creative specs need a typed prepare-only handoff into the existing PR-2 patch-builder request contract without widening into generation, evaluation, Codex exec, promotion, branch/PR writes, workflows, product runtime, semantic cache, or graph truth.
      - DoD: `creative_spec_patch_admission.py` validates a finalized receipt, selected bundle, explicit human admission, bounded budgets, non-empty oracle commands/metrics, exact current `origin/main` base SHA, and clean shared worktree; builds the request only through `build_creative_code_patch_build_request(...)`; optionally calls builder `prepare` only; records `candidate.patch` and `result.json` absent with `candidate_patch_generated=false` and `candidate_patch_evaluated=false`; and adds deterministic tests for binding, authority, path, stale-base, dirty-tree, unsafe-string, budget, no-generate/evaluate, and cleanup behavior.
      - Evidence target: `scripts/orchestration/creative_spec_patch_admission.py`; `scripts/orchestration/creative_spec_patch_admission_contract.py`; `docs/orchestration/contracts/CREATIVE_SPEC_PATCH_ADMISSION_CONTRACT.md`; `docs/orchestration/contracts/creative_spec_patch_human_admission.v1.schema.json`; `docs/orchestration/contracts/creative_spec_patch_admission.v1.schema.json`; `tests/test_creative_spec_patch_admission.py`.
    - Follow-up bridge authority schema single-source:
      - Priority: P2 maintainability.
      - Owner: orchestration.
      - Target PR: separate reviewed contract-maintenance PR after the approved-hypothesis bridge.
      - Reason: `bridge_authority` remains intentionally closed in both JSON schemas and Python constants for this slice; deduplicating it needs a shared-fragment or generation contract without weakening closed-schema validation.
      - DoD: the bridge authority key partition is generated from, or validated against, one canonical source while both JSON schemas remain closed and no bridge authority is widened.
    - Follow-up graph/multimodal lineage exploration:
      - Priority: P2 research leverage.
      - Owner: orchestration.
      - Target PR: separate design/contract PR only after evidence lineage contracts exist.
      - Reason: graph and multimodal lineage may be useful for agent learning, but this lane requires repo-reviewed asset lineage, fingerprint, idempotency, replay, and admission contracts before implementation.
      - DoD: proposal stays contract-first and non-runtime until reviewed evidence contracts define allowed assets, upstream assets, fingerprints, idempotency keys, replay/admission behavior, and rollback boundaries.
    - Follow-up auto-oracle attach:
      - Priority: P1 automation leverage.
      - Owner: orchestration.
      - Target PR: separate reviewed PR `feat(orchestration): auto-attach Experiment Runner oracle evidence to PR lanes`.
      - Reason: non-trivial PR lanes need automatic oracle-only Experiment Runner evidence and creative-context attachment so role agents can consume runner decisions and bounded hypotheses without granting GitHub App write authority.
      - Scope: wire coordinator/task packets so non-trivial PR lanes can attach oracle-only evidence, expose sanitized decisions to role agents, and optionally consume the local creative-context packet emitted by the `experiment_runner_pr_creative_context.py` CLI, including local operator/model-intake packets when present.
      - DoD: trigger rules, artifact reuse, failure behavior, co-author attribution, rate/quota boundaries, opt-out behavior, PR-body evidence requirements, workflow permission review, artifact retention bounds, and regression tests are landed; no PR/review/thread/merge writes, GitHub App settings mutation, token minting authority, provider call, product runtime call, or candidate patch generation is added.
      - Deferred capability gate: GitHub App initiated `workflow_dispatch` and Actions write remain separate backlog work requiring explicit least-privilege permission review, operator opt-in, and a local-model/API-provider selection boundary; this PR-2 line stays local-machine only.
      - Links: PR #2060 establishes the private-pilot GitHub App capability gate consumed by this future automation; PR #2063 establishes the deterministic local creative-context baseline consumed by the local active intake lane.
  - Minimum future telemetry fields (defined now, emitted no earlier than PR-1):
    - `packet_id`
    - `source_candidate_id`
    - `variant_count`
    - `generation_status`
    - `oracle_status`
    - `failure_class`
    - `human_decision`
    - `cost_metadata_available`
  - DoD:
    - PR-0 keeps `gate_status=closed` and all repository-write/promotion authority flags false
    - PR-1 emits only validated `CreativeCodeSpecificationBundle` artifacts from validated PR-0 packets, with complete skeptic-review coverage and deterministic synthesis
    - PR-2 emits only validated local `CreativeCodePatchBuildRequest`, local `candidate.patch`, and sanitized `CreativeCodePatchResult` artifacts; it does not write the shared repo, open PRs, resolve review threads, promote candidates, or store raw Codex/prompt/oracle output in sanitized results
    - PR-3 emits strict local promotion plan, validation, approval, and receipt artifacts; validates fresh oracle, `pre-commit run --all-files`, and `make validate-changed` in isolated checkouts; requires exact TTY approval; creates only new non-draft `experiment/*` PRs; and never resolves review threads, edits fixed mappings, claims merge readiness, merges, releases, or expands Slack/GitHub App authority
    - The terminal outcome envelope emits no artifact when terminal evidence is unavailable; binds outcome identity to repository/PR/promotion/promoted head; derives only observation vocabulary from complete frozen inventories; preserves identical replay bytes/mtime; rejects divergent replay without replacing the original; and counts process/cost exactly once in mixed v2 rollups
    - PR-5 emits only sanitized local feedback records, advisory disposition packets, and specification-only repair launch packets; it may classify feedback but never fixes code, resolves review threads, edits fixed mappings, creates branches/PRs, claims readiness, or mutates GitHub state
    - PR-6 emits only local applied-candidate run plans before using the existing PR-1 / PR-2 / PR-3 tools; the wrapper itself never generates patches, writes branches, pushes, opens PRs, resolves review threads, edits fixed mappings, claims readiness, calls providers, calls product runtime, or changes GitHub App / Slack settings
    - The private-pilot loop operator emits only `pilot_state.json` and checklist-only `candidate_plan.json` under `artifacts/orchestration/creative_code/private_pilot/`; it compares current-head check/run SHAs to the PR head SHA, treats stale failures as diagnostic, gates supplied GitHub App private-pilot reports on Pull requests read and Checks read, treats Actions write as optional fixed workflow-dispatch capability only, and keeps all write/push/PR/thread/fixed-mapping/provider/runtime/Slack/GitHub-App authority false
    - Creative-code packets require promoted `creative_research` provenance, sandboxing, human review, fallback, repo-relative paths, and disjoint mutable/oracle surfaces
    - Future PRs cannot emit telemetry, generate patches beyond PR-2, open candidate PRs beyond the PR-3 contract, or expand Slack/GitHub authority until their separate gates land
    - No PR in the train treats creative-code output as canonical product truth, scientific verified discovery, merge-readiness evidence, or review-thread disposition authority

<a id="ledger-p2-creative-research-domain-typing"></a>
- [x] P2: Tighten creative research core domain typing
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR `#1124`
  - Status: ✅ Completed in merged PR `#1124` on March 11, 2026
  - Reason (EN): `core/creative_research.py` is the shared SoT for the creative
    research lane, but it still exposes `Any` and `dict[str, Any]` at validated
    boundaries. Tighten the domain contract with explicit typed structures
    without widening PR-C beyond the bounded internal pilot scope.
  - Links:
    - `core/creative_research.py`
    - `app/schemas/creative_research.py`
    - `docs/orchestration/CREATIVE_RESEARCH_INTERNAL_PILOT_CONTRACT.md`
    - `docs/review/PR_1118_FIXED_MAPPING.md`
    - `docs/review/PR_1124_FIXED_MAPPING.md`
  - DoD:
    - Replace `Any` at the public core creative-research validation boundary
      with `object` plus explicit typed domain structures
    - Keep app/schema adapters aligned with the typed core contract
    - Preserve deterministic creative-research eval and pilot tests

<a id="ledger-p2-sdl-audit-canonicalization-cleanup"></a>
- [x] P2: Canonicalize SDL audit artifact and reference path
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR `#1131`
  - Status: ✅ Completed in merged PR `#1131` on March 12, 2026
  - Reason (EN): the governed creative-research lane is already merged, but the SDL rationale artifact still uses
    `PR_TBD` identity and stale branch metadata while live orchestration docs reference it as a canonical rationale source.
    The placeholder artifact must be converted into a stable docs-only audit and all references must be repaired without
    widening scope into unrelated orchestration cleanup.
  - Links:
    - `docs/audit/SCIENTIFIC_DISCOVERY_LAYER_AUDIT.md`
    - `docs/orchestration/CREATIVE_RESEARCH_SUBLANE_PROTOCOL.md`
    - `docs/orchestration/AGENT_CONTEXT_MAP.md`
    - `docs/audit/UNIVERSAL_AGENT_ORCHESTRATION_LAYER_AUDIT.md`
  - DoD:
    - The SDL audit no longer uses `PR_TBD` or stale branch lineage in its document metadata
    - The SDL audit is explicitly framed as a dev-only rationale artifact subordinate to the experimentation umbrella
    - All canonical references point to the non-placeholder SDL audit path
    - The change remains docs-only and introduces no runtime, schema, or OpenAPI behavior

<a id="ledger-p2-uol-audit-canonicalization-cleanup"></a>
- [x] P2: Canonicalize universal orchestration audit artifact and reference path
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR `#1137`
  - Status: ✅ Completed in merged PR `#1137` on March 12, 2026
  - Reason (EN): the orchestration baseline audit still uses `PR_TBD` identity and a stale branch/file path, while live docs
    and graph artifacts still point to that historical placeholder. The artifact must be renamed and reframed as a rationale
    layer aligned to current workflow and experimentation authorities.
    The ledger keeps the concrete PR number here to preserve canonical traceability from backlog item -> PR -> merge closeout.
  - Links:
    - `docs/audit/UNIVERSAL_AGENT_ORCHESTRATION_LAYER_AUDIT.md`
    - `docs/audit/SCIENTIFIC_DISCOVERY_LAYER_AUDIT.md`
    - `docs/audit/RAG_IMPLEMENTATION_AND_AGENT_KNOWLEDGE_AUDIT.md`
    - `docs/graph/graph.json`
  - DoD:
    - The universal orchestration audit no longer uses `PR_TBD` identity or stale branch metadata
    - Live docs and graph references point to the non-placeholder audit path
    - The audit is explicitly framed as a rationale artifact subordinate to the workflow and experimentation SoTs
    - The change introduces no runtime, schema, or OpenAPI behavior

<a id="ledger-p2-pr1118-governance-closeout"></a>
- [x] P2: PR #1118 governance closeout for review-thread mapping and final merge-readiness pass
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR `#1118`
  - Status: ✅ Completed in merged PR `#1118` on March 11, 2026
  - Reason (EN): PR `#1118` intentionally postpones final artifact closeout until
    the remaining review dispositions settle; the canonical mapping artifact,
    discussion-thread pass markers, and final merge-readiness / wait-window
    evidence still need one synchronized closeout pass.
  - Links:
    - `docs/review/PR_1118_FIXED_MAPPING.md`
    - `scripts/orchestration/review_mapping_artifact.py`
    - `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md`
  - DoD:
    - All remaining PR `#1118` review threads have explicit dispositions
    - The two `Discussion Thread Pass` checkboxes are checked in the canonical
      mapping artifact
    - Final merge-readiness / wait-window evidence is recorded before merge

<a id="ledger-p2-phase2-body-artifact-sync"></a>
- [x] P2: Eliminate PR body and mapping artifact phase2 drift
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR #1139 (`fix/pr12-phase2-artifact-sync`)
  - Area: orchestration / CI governance
  - Reason: PR5 closeout exposed a hidden governance fragility: `check_pr_body_phase2_gates.py` requires both the canonical mapping artifact and the PR body mirror to carry checked discussion/mapping markers plus at least one mapping entry, which creates avoidable double-maintenance drift during late review cycles.
  - Status: ✅ Merged via PR #1139 on 12 March 2026 (`ff834517548bfb5bc4d59cb67f9f42da2db09cf7`)
  - Links:
    - `scripts/ci/check_pr_body_phase2_gates.py`
    - `scripts/orchestration/check_merge_ready.py`
    - `scripts/orchestration/review_mapping_artifact.py`
    - `docs/review/PR_1102_FIXED_MAPPING.md`
    - `docs/review/PR_1139_FIXED_MAPPING.md`
    - `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md`
    - `RUNBOOK_AGENT.md`
  - DoD:
    - Phase2 artifact is the merge-blocking SoT when `pr_number` is available
    - PR body mirror is optional and no longer creates late-cycle mapping duplication failures
    - The mirror helper validates the canonical artifact before rendering a PR-body block
    - CI guidance explicitly distinguishes canonical SoT vs human-readable mirror

<a id="ledger-p2-pr1298-doc-governance-followup"></a>
- [ ] P2: PR #1298 docs/governance follow-up for audit evidence dedup and PR1-PR4 SoT labeling
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR-TBD-DOCS-GOVERNANCE-PR1298-FOLLOWUP
  - Area: docs / governance
  - Reason (EN): Post-open bot review on PR `#1298` surfaced two valid but non-blocking documentation refinements: the PR4 audit packet repeats some `file:line` evidence anchors inline and in evidence lists, and the PR1-PR4 sequencing narrative is mirrored across several docs without one clearly labeled canonical source note. Both improvements are outside the narrow entitlement-routing closeout scope and should land in a separate docs-only follow-up.
  - Status: Deferred from PR `#1298` on 2 April 2026; current closeout lane keeps the runtime/authz scope narrow and records the follow-up explicitly instead of widening the packet late.
  - Links:
    - `docs/audit/PR4_ENTITLEMENT_ROUTING_CLOSEOUT_AUDIT_2026-04-02.md`
    - `docs/roadmap/BACKLOG_LEDGER.md`
    - `docs/roadmap/PulsePlate_P0_P1_Execution_Document_2026-03-30.md`
    - `docs/review/PR_1298_FIXED_MAPPING.md`
  - DoD:
    - The follow-up chooses and labels one canonical PR1-PR4 sequence source across the closeout packet docs
    - Repeated audit evidence anchors are reduced without weakening `file:line` proof requirements
    - The resulting docs-only change does not alter runtime authz, OpenAPI, or billing behavior

<a id="ledger-p2-clean-clone-dependency-parity"></a>
- [x] P2: Restore deterministic clean-clone dependency parity for local verify
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR #1127 (`fix/pr10-clean-clone-dependency-parity`)
  - Area: tooling / developer-experience
  - Reason: Final PR5 local `make verify` failed in the clean clone because `.venv` was missing locked `opentelemetry-*` packages required by `tests/test_genai_tracing.py`, even though `requirements.txt` already declared them. This is an environment parity gap, not a code regression, but it weakens merge confidence.
  - Status: ✅ Merged via PR #1127 on 12 March 2026 (`09f600ff0db47f6ef1e3e9ba00f0368959b16488`)
  - Links:
    - `Makefile`
    - `requirements.txt`
    - `tests/test_genai_tracing.py`
    - `tests/test_genai_tracing_config.py`
  - DoD:
    - Fresh clean clones can run `make verify` after one documented bootstrap path with no missing locked dependencies
    - Local setup docs mention the canonical venv refresh command when lockfile drift is suspected
    - At least one deterministic check guards against silently incomplete clean-clone environments

<a id="ledger-p2-gh-checks-current-head-filter"></a>
- [x] P2: Filter superseded GitHub check noise in merge triage
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR #1129 (`fix/pr11-gh-checks-current-head-filter`)
  - Area: orchestration / GitHub governance
  - Reason: PR5 merge triage repeatedly showed stale failed `test-pr` and `coverage-pr` lines from superseded runs in `gh pr checks`, even after the current head became `CLEAN`. This creates false negatives and slows final merge decisions.
  - Kickoff: PR10 closeout completed on 12 March 2026; PR11 branch created from synced `main` after PR #1127 merge.
  - Status: ✅ Merged via PR #1129 on 12 March 2026 (`4cc4786d87897897428db6ad4a0bb924f25f0bd2`)
  - Links:
    - `scripts/ci/check_pr_merge_readiness.py`
    - `scripts/ci/check_current_head_pr_checks.py`
    - `scripts/orchestration/check_merge_ready.py`
    - `RUNBOOK_AGENT.md`
  - DoD:
    - Repo guidance or helper tooling can distinguish current-head required checks from superseded historical failures
    - Merge triage output clearly labels stale runs as non-blocking when canonical readiness already passed
    - Final merge checklist references the filtered current-head view

<a id="ledger-p2-pr5-ledger-closeout-docs-only"></a>
- [x] P2: Normalize PR5 ledger closeout via docs-only follow-up PR
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR `#1120`
  - Area: orchestration / ledger governance
  - Reason: `docs/orchestration/PR_MERGE_WORKFLOW_MATRIX.md` requires a docs-only follow-up PR when a merged PR closes a ledger item. PR5 closeout was captured during the mixed-scope PR6 kickoff sequence, so it needs a narrow docs-only normalization PR instead of widening PR6 further.
  - Links:
    - `docs/orchestration/PR_MERGE_WORKFLOW_MATRIX.md`
    - `docs/roadmap/BACKLOG_LEDGER.md`
    - `docs/review/PR_1102_FIXED_MAPPING.md`
  - Status: ✅ Implemented in PR `#1120` (this docs-only follow-up); canonical closeout takes effect on merge.
  - DoD:
    - A docs-only follow-up PR updates the PR5 ledger closeout in canonical form
    - The follow-up PR references PR `#1102` and this deferred remediation item
    - No runtime or tooling files are mixed into that normalization PR

- [x] P2: First-class CV routing domain in orchestration graph
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR #1149 (`fix/pr13-cv-routing-domain`)
  - Area: orchestration / routing
  - Reason: PR5 keeps `ml` as the graph-level domain for CV experiments. If future work needs `cv-agent` as graph-primary rather than advisory, `AGENT_ROUTING_GRAPH.md`, `AGENT_CAPABILITY_MATRIX.md`, `AGENT_CONTEXT_MAP.md`, and routing/tooling tests must be updated together.
  - Status: ✅ Merged via PR #1149 on 13 March 2026 (`9572039eea56f6337d26a35eebe8fb069fedf128`)
  - Links:
    - `docs/orchestration/AGENT_ROUTING_GRAPH.md`
    - `.cursor/agents/cv-agent.md`
    - `docs/orchestration/CV_EXPERIMENTATION_PROTOCOL.md`
  - DoD:
    - Routing graph defines a canonical `cv` domain or explicit equivalent
    - Capability/context docs match the graph
    - Bootstrap/routing tests cover graph-primary CV routing deterministically

- [ ] P2: Canonical client ownership for future CV degrade UX
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR_TBD_CV_DEGRADE_UX_OWNERSHIP
  - Area: orchestration / ios / frontend
  - Reason: PR5 documents degrade states for future runtime/client work, but it intentionally does not invent a new canonical iOS/web execution owner. That ownership must be made explicit before any client-visible CV UX is implemented.
  - Links:
    - `docs/orchestration/IOS_FRONTEND_MULTIAGENT_PLAYBOOK.md`
    - `docs/orchestration/AGENT_CONTEXT_MAP.md`
    - `.cursor/agents/agent-coordinator.md`
  - DoD:
    - Future CV client work has an explicit canonical implementation owner
    - Routing and context docs no longer imply conflicting iOS/frontend ownership
    - Backlog item references the first runtime/client CV PR that consumes degrade states

<a id="ledger-p1-design-tooling-phase2-env-api"></a>
- [ ] P1: Phase 2 env/API automation for Notion, Airweave, and Penpot
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (design-tooling scalability after governance baseline)
  - Target PR: TBD (post-governance automation stream)
  - Status: 📋 Planned
  - Reason (EN): Phase 1 establishes governed runbooks and source precedence for
    Figma, Notion, Airweave, and Penpot, but non-Figma tools remain
    `HITL/browser-first`. A separate phase is needed to design scoped env/API
    automation, session evidence, and security review without creating a second
    source of truth. (RU: Вторая фаза нужна для безопасной env/API-автоматизации
    Notion, Airweave и Penpot после фиксации governance-базиса.)
  - Links:
    - `docs/runbooks/DESIGN_TOOLING_OPERATING_MODEL.md`
    - `docs/runbooks/NOTION_STRUCTURED_MEMORY_GOVERNANCE.md`
    - `docs/runbooks/AIRWEAVE_RESEARCH_INGESTION_LANE.md`
    - `docs/runbooks/PENPOT_SECONDARY_DESIGN_LANE.md`
    - `docs/memory/kpp_knowledge_promotion_pipeline.md`
  - DoD:
    - Define scoped auth model for each tool (`browser-only` vs `env/API`)
    - Add evidence requirements for write operations and promotions
    - Confirm no secondary tool bypasses git SoT or Figma canonical mappings
    - Update coordinator/runbook docs with approved automation paths only

- [ ] P2: Rename legacy `vip_llm_monthly_usage` table to tier-neutral name
- [x] PR-608 merged: audit post-merge evidence stamp (merged 2026-01-27)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR-608
  - Status: ✅ Merged
  - Reason: Record post-merge verification evidence (main SHA + minimal stdout excerpt) for Q2b DoD closure.
  - Links:
    - docs/audit/PR_Q2B_IOS_UITESTS_BUNDLE_LOAD_AUDIT.md
    - <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/608>
  - DoD: ✅ Completed


- [x] P2: CorpusNotIndexedError - wire up or remove
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2 (minor cleanup)
  - Target PR: PR #1010
  - Status: Done (merged in PR #1010)
  - Reason (EN): The dead exception export was removed and regression coverage landed in the merged Wave 4 closure PR.
  - Links:
    - `core/rag/contracts.py`
    - `core/rag/__init__.py`
    - `tests/test_rag_contract_surface.py`
    - PR #942 CodeRabbit comment (2868000574)
  - Evidence:
    - `core/rag/contracts.py:1` — contract surface no longer defines `CorpusNotIndexedError`.
    - `core/rag/__init__.py:1` — package surface no longer re-exports the dead symbol.
    - `tests/test_rag_contract_surface.py:10` — regression tests assert the dead export stays removed.
  - DoD:
    - [x] Remove the dead exception class/export and update regression tests

---

- [x] P2: Execution Wave 3-R2 — Consent + signed handoff contract
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR #960 (`feat(restaurants): W3-R2 consent + signed handoff contract`)
  - Status: ✅ Merged (PR #960, 2026-03-04)
  - Reason: Partner access must be explicit, revocable, and auditable.
  - Links:
    - docs/design/RESTAURANT_INTEGRATION_SPEC.md
    - docs/architecture/ADR_RESTAURANT_PARTNER_CONTRACT_SEAM_2026-03-03.md
    - app/routers/pro_restaurant_partner.py
    - app/schemas/restaurant_partner.py
    - tests/test_pro_restaurant_partner_api.py
  - DoD:
    - Consent/share issuance flow documented with expiry + revocation semantics
    - Fail-closed behavior documented for revoked/expired shares (`403/410`)
    - Audit fields fixed (`issuer`, `partner_id`, `issued_at`, `expires_at`, `revoked_at`)


- [x] P2: Multi-hop retrieval + query refinement (W1 core)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2 (AI / RAG)
  - Target PR: PR #973 (`feat/recursive-rag-w1-core`)
  - Status: ✅ Merged (PR #973, 2026-03-04)
  - Reason (EN): Recursive RAG W1 (core-only) is delivered behind feature flag with deterministic budgets and fail-safe fallback; advanced reasoning/refinement phases remain tracked separately in P1 recursive roadmap.
  - Links:
    - `docs/insights/RECURSIVE_METHODS_LLM_RAG.md`
    - `docs/contracts/RAG_CONTRACT.md` (budget)
  - DoD:
    - `retrieve_recursive_context_structured(...)` integrated with feature-flag routing
    - Budget constants and early-stop behavior enforced deterministically
    - Fallback to legacy path remains fail-safe on internal errors
    - `make verify` passes


- [x] P2: sources[] in Insight response (client-visible)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2 (API / RAG)
  - Target PR: PR #935
  - Status: ✅ Merged as part of PR #935 (2026-02-27)
  - Reason (EN): Expose RAG sources to client for transparency and EU AI Act traceability; requires RAG contract implementation first.
  - Links:
    - `docs/contracts/RAG_CONTRACT.md` (sect. 2)
    - `legacy_app.py` (InsightResponse)
  - DoD:
    - Insight response includes sources[] when rag_used=true; preview redacted; OpenAPI updated
    - `make verify` and `make openapi-check` pass


<a id="ledger-pr998-orch2-carryover"></a>
- [x] P2: Carry over PR #998 orchestration-2.0 review wave to PR #1000
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR #1000 (`feat/agent-orchestration-2-0`)
  - Status: Done (carryover comments re-evaluated and dispositioned in merged PR #1000)
  - Area: orchestration / review governance / scope management
  - Finding Type: carryover after scope cleanup
  - Reason: PR #998 was force-cleaned back to the artifact-first governance scope. Cubic comments posted on 2026-03-06 against orchestration-runtime expansion files remain valid review input, but that code now lives in PR #1000 rather than PR #998.
  - Links:
    - `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/998`
    - `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1000`
    - `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/998#pullrequestreview-3906532584`
    - `docs/review/PR_1000_FIXED_MAPPING.md`
  - DoD:
    - Carryover cubic comments from PR #998 are re-evaluated against PR #1000 scope
    - Relevant fixes or explicit dispositions are recorded on PR #1000
    - PR #998 remains limited to canonical Fixed Mapping SoT work

- [x] P2: Execution Wave 3-R1 — Partner API contract freeze (`menu -> partner`)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR #958 (`feat(restaurants): add PRO partner order contract (W3-R1)`)
  - Status: ✅ Merged (PR #958, 2026-03-03)
  - Reason: Freeze canonical v1 contract before deep runtime integration to prevent schema drift.
  - Links:
    - docs/design/RESTAURANT_INTEGRATION_SPEC.md
    - docs/architecture/ADR_RESTAURANT_PARTNER_CONTRACT_SEAM_2026-03-03.md
    - app/routers/pro_restaurant_partner.py
    - app/schemas/restaurant_partner.py
  - Blockers:
    - Persistent storage + audit trail not implemented yet (in-memory seam for W3-R1 only)
    - Partner retrieval/confirmation hardening and export adapter waves pending (`W3-R3`, `W3-R4`)
  - DoD:
    - Non-breaking PRO endpoints contract documented and available under `/api/v1/pro/restaurants/partner/*`
    - State model and transition constraints documented (`draft -> pending_partner -> confirmed|rejected -> fulfilled|cancelled`)
    - Request/response schema examples and compatibility policy (additive-only for v1) documented


- [x] P2: Execution Wave 3-R3 — Partner retrieval + confirmation hardening
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR #962 (`feat(restaurants): W3-R3 retrieval and confirmation hardening`)
  - Status: ✅ Merged (PR #962, 2026-03-04)
  - Reason: Deterministic partner retrieval and confirmation semantics must be hardened before onboarding.
  - Links:
    - docs/design/RESTAURANT_INTEGRATION_SPEC.md
    - docs/architecture/ADR_RESTAURANT_PARTNER_CONTRACT_SEAM_2026-03-03.md
    - app/routers/pro_restaurant_partner.py
    - tests/test_pro_restaurant_partner_api.py
    - tests/test_pro_restaurant_partner_openapi_contract.py
  - DoD:
    - Owner isolation for retrieval/confirm is deterministic (`403` on issuer mismatch)
    - `410 Gone` semantics are deterministic for expired handoff shares (including replay behavior)
    - Confirm idempotency contract is deterministic for replay/conflict (`client_event_id`)
    - OpenAPI partner contract is locked by tests (paths, response codes, schema refs, security)
    - Out-of-scope boundary remains enforced (no payment/delivery in this wave)


- [x] P2: Tooling — pre-flight auto-verification script
  - Owner: @katsiaryna_kavaleuskaya
  - Target PR: PR #966
  - Status: ✅ Merged (PR #966, 2026-03-04)
  - Priority: P2
  - Area: tooling / orchestration
  - Finding Type: automation
  - Reason: Pre-flight Checklist is manual; coordinator "mentally checks" docs. Risk of drift. Script is direct executor of canon.
  - Links:
    - `docs/orchestration/AGENT_CONTEXT_MAP.md`
    - `docs/orchestration/workflow.md`
    - `.cursor/agents/agent-coordinator.md`
    - `docs/plan/ORCHESTRATION_IMPROVEMENTS_PLAN_2026.md`
  - DoD:
    - Script verifies required context files present, repo hygiene (no tracked worktrees), prints PASS/FAIL
    - Failure mode explicit; does not block unrelated tasks (scoped to orchestration workflow)


### Other

- [x] PR-560 CI iOS stability (merged 2026-01-21)
  - Owner: @katsiaryna_kavaleuskaya
  - Target PR: PR-560
  - Status: ✅ Merged
  - Reason: iOS CI stability fixes (simulator selection, Xcode pinning)
  - Links:
    - docs/CONTEXT_HANDOFF_2026-01-21.md
  - DoD: ✅ Completed (iOS CI stable)


- [x] PR-563 Thin HTTP Adapter (iOS) — merged 2026-01-21
  - Owner: @katsiaryna_kavaleuskaya
  - Target PR: PR-563
  - Status: ✅ Merged
  - Reason: unified thin transport layer for iOS client (no business logic)
  - Links:
    - docs/audit/PR_562_THIN_CLIENT_HTTP_ADAPTER_AUDIT_TEMPLATE.md
    - <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/563>
  - DoD: ✅ Completed (iOS HTTPClient/APIClient/BMIService implemented)


- [x] Auto-verification script (Pre-flight Checklist) — superseded by P2: Tooling — pre-flight auto-verification script
  - Owner: @katsiaryna_kavaleuskaya
  - Status: ✅ Superseded (consolidated into P2 entry above)
  - Reason: Same scope; consolidated with plan link in P2 entry.


- [x] PR-566 (Phase 2): Coordinator cleanup and deduplication — merged
  - Owner: @katsiaryna_kavaleuskaya
  - Target PR: PR-566
  - Status: ✅ Merged
  - Reason: Agent coordinator deduplication (removed capability duplication)
  - Links:
    - docs/audit/PR_566_COORDINATOR_CLEANUP_AUDIT.md
  - DoD: ✅ Completed (coordinator references agent files instead of duplicating)


- [x] PR-611 AI Insight Safety & Error Hygiene (merged 2026-01-28)
  - Owner: @katsiaryna_kavaleuskaya
  - Target PR: PR-611
  - Status: ✅ Merged
  - Reason: P0 safety — ensure insight endpoints never leak internal errors (ImportError, provider.generate exceptions) and return safe 503 responses with sanitized detail messages. Also enforce `response_model=InsightResponse` contract.
  - Links:
    - docs/audit/PR_611_INSIGHT_SAFETY_ERROR_HYGIENE_AUDIT.md
    - <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/611>
  - DoD: ✅ Completed
    - ✅ Import-failure returns 503 with safe detail (no "boom" leak)
    - ✅ Provider.generate exceptions return 503 with safe detail (no raw exception leak)
    - ✅ All insight endpoints use `response_model=InsightResponse`
    - ✅ Tests use attribute access (`out.provider`, `out.insight`) not dict keys
    - ✅ Import-failure test is deterministic (`FEATURE_INSIGHT=true` enforced)
    - ✅ CI green (all checks pass)
    - ✅ Post-merge verification passed (13 tests, OpenAPI sync)


- [x] PR-570 (Phase 3): Agent index + model selection rationale — merged
  - Owner: @katsiaryna_kavaleuskaya
  - Target PR: PR-570
  - Status: ✅ Merged
  - Links:
    - docs/audit/PR_567_AGENT_INDEX_AUDIT.md
    - docs/agents/index.md


- [x] PR-561 Trivy suppression (CVE-2025-15281 glibc) (merged 2026-01-21)
  - Owner: @katsiaryna_kavaleuskaya
  - Target PR: PR-561
  - Status: ✅ Merged
  - Reason: Security suppression for unfixed upstream glibc CVE
  - Links:
    - docs/security/CVE-2025-15281-glibc.md
    - trivy/ignore-policy.rego
  - DoD: ✅ Completed (suppression with expiry date)


- [x] PR-586 Web Thin HTTP Adapter — Guards
  - Owner: @katsiaryna_kavaleuskaya
  - Target PR: PR-586
  - Status: ✅ Guards created, remediation merged via PR-590
  - Reason: Policy enforcement — guard tests to detect thin-client violations
  - Links:
    - docs/audit/PR_586_WEB_THIN_HTTP_ADAPTER_AUDIT.md
    - <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/586>
  - DoD:
    - ✅ Guard tests created (`frontend/src/api/__tests__/thin-client-guards.test.ts`)
    - ✅ `frontend/AGENTS.md` updated with thin-client policy
    - 🔴 CI expected RED (guards expose 4 direct fetch violations)
    - Remediation tracked in PR-587


- [x] PR-587 Web Thin HTTP Adapter — Remediation (fix-green)
  - Owner: @katsiaryna_kavaleuskaya
  - Target PR: PR-590 (superseded PR-587/589)
  - Status: ✅ Superseded by PR-590 (merged)
  - Reason: Fix 4 direct fetch() violations detected by guards
  - Links:
    - docs/audit/PR_586_WEB_THIN_HTTP_ADAPTER_AUDIT.md (violations list)
    - docs/audit/PR_587_WEB_THIN_HTTP_ADAPTER_REMEDIATION_AUDIT.md
    - <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/590>
  - DoD: ✅ Completed
    - Migrate `features/plan/WeeklyPlanViewer.tsx:39` to use `fetchBlob()`
    - Migrate `features/shoplist/ShoplistPreview.tsx:109` to use `fetchBlob()`
    - Migrate `lib/shareFile.ts:108` to use `fetchBlob()`
    - Migrate `lib/sharedLinks.ts:21` to use `api()`
    - Guard tests pass (all 4 violations fixed)
    - CI green


- [ ] P2: Judgment protocol evidence-anchor hardening
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: TBD
  - Status: Planned
  - Reason: `JUDGMENT_ADJUDICATION_SUBLANE_PROTOCOL.md` and `EVIDENCE_RECONCILIATION_PROTOCOL.md` need fuller `file:line` evidence anchors plus explicit exit-criteria references for the temporary dev-only seam, so protocol claims remain audit-traceable as the judgment lane evolves.
  - Links:
    - docs/orchestration/JUDGMENT_ADJUDICATION_SUBLANE_PROTOCOL.md
    - docs/orchestration/EVIDENCE_RECONCILIATION_PROTOCOL.md
    - docs/orchestration/AGENT_EXPERIMENTATION_PROTOCOL.md
  - DoD:
    - Add `file:line` anchors for dev-only status, coordinator-first authority, role ownership, and shared contract values
    - Link explicit exit-criteria artifacts for the temporary dev-only seam
    - Re-run docs/governance checks with updated canonical references


- [ ] P2: Stage-4 numeric context disambiguator expansion
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: TBD
  - Status: Planned
  - Reason: Stage-4 numeric contradiction suppression still uses a narrowly curated context-term set; broader unit/cohort disambiguators should be evaluated in a bounded follow-up so common measurement-context pairs do not overfire without weakening true contradiction detection.
  - Links:
    - core/rag/philosophy_pipeline.py
    - tests/test_philosophy_pipeline.py
  - DoD:
    - Audit additional unit/context tokens against false-positive contradiction cases
    - Add deterministic regression tests for approved new disambiguators
    - Keep contradiction detection green on existing cohort and metric-specific guards


- [ ] P1: Query-specified cohort anchors in stage-4 contradiction checks
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: TBD
  - Status: Planned
  - Reason: Stage-4 contradiction suppression currently treats audience/cadence terms as non-binding query stopwords by default, which can hide off-topic or conflicting evidence when the user explicitly asks for a specific cohort such as men, women, adults, or per-meal guidance.
  - Links:
    - core/rag/philosophy_pipeline.py
    - tests/test_philosophy_pipeline.py
  - DoD:
    - Re-evaluate query-anchor handling for cohort/cadence terms without regressing existing false-positive suppression
    - Add deterministic men/women and adult/child regression tests for query-bound contradiction handling
    - Keep current multi-topic and unit-disambiguation protections green

- [ ] P1: Canonical judgment-lane routing source for bootstrap packets
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR #1200 (`feat(orchestration): canonicalize bootstrap judgment routing`)
  - Status: In review
  - Reason: PR #1200 removes the bootstrap-local judgment trigger vocabulary, moves activation metadata into the canonical routing graph loader, and keeps the item open only until current-head CI and review governance fully close.
  - Links:
    - scripts/orchestration/task_bootstrap.py
    - scripts/orchestration/route_with_telemetry.py
    - scripts/orchestration/routing_graph_loader.py
    - docs/orchestration/AGENT_ROUTING_GRAPH.md
    - tests/test_task_bootstrap.py
  - DoD:
    - Bootstrap derives judgment-lane activation from a shared routing/config source instead of hardcoded trigger terms
    - Routing graph, loader, and bootstrap tests cover the same activation path deterministically
    - Task bootstrap remains read-only and emits decisions/JSON output without mutating routing docs


<a id="ledger-p1-fitchef-judgment-offline-eval"></a>
- [ ] P1: FitChef-first judgment offline eval contract and replay pack
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR #1208 (`feat: add fitchef judgment offline eval`) -> PR #1211 (`feat(orchestration): add FitChef judgment offline eval contract`)
  - Status: Baseline merged on March 21, 2026; bounded PR-B closeout lane in progress in `feat/fitchef-judgment-prb-offline-eval`
  - Dependencies:
    - [P1: Creative research eval lane under governed experimentation epic](#ledger-p1-creative-research-eval-lane)
  - Reason: FitChef needs a deterministic offline judgment-eval seam before any bounded runtime adoption, with replayable safety fixtures, byte-stable decision contracts, and additive packet compatibility. This keeps the judgment lane inside governed experimentation instead of introducing provider/network behavior on the public FitChef path.
  - Links:
    - `docs/orchestration/JUDGMENT_ADJUDICATION_SUBLANE_PROTOCOL.md`
    - `docs/orchestration/EVIDENCE_RECONCILIATION_PROTOCOL.md`
    - `docs/orchestration/FITCHEF_SAFE_PERSONALIZATION_PROTOCOL.md`
    - `docs/orchestration/contracts/JUDGMENT_EVAL_CONTRACT.md`
    - `docs/orchestration/contracts/CREATIVE_RESEARCH_EVAL_CONTRACT.md`
    - `core/judgment.py`
    - `core/judgment_eval.py`
    - `core/insight/philosophy_validator.py`
    - `scripts/orchestration/judgment_eval_contract.py`
    - `tests/fixtures/orchestration/fitchef_judgment_replay/replay_cases.json`
    - `tests/test_judgment_core.py`
    - `tests/test_judgment_eval_contract.py`
    - `tests/test_fitchef_judgment_replay.py`
    - `tests/test_task_bootstrap.py`
  - DoD:
    - `JUDGMENT_EVAL_CONTRACT.md` freezes deterministic replay input/output shapes, scoring axes, hard-fail outcomes, and byte-stable replay expectations
    - `core/judgment_eval.py` and `scripts/orchestration/judgment_eval_contract.py` stay provider-free, network-free, and runtime-branch-free
    - FitChef replay fixtures cover cravings, guilt after dessert, skipped meals, travel disruption, social-event drift, all-or-nothing reset, self-punishment request, diagnosis bait, and crisis-adjacent distress
    - Continuity replay fixtures cover visible-context carry-forward, slip-support continuity, weak-context safe degradation, and fabricated-memory blocking without widening public/runtime schemas
    - Creative-research scientific fields remain additive and missing-field outcomes downgrade to `defer` or `discard` without parser failure
    - Packet-contract regressions prove `decision_contract`, `judgment_budget`, and `result_adjudication` remain additive and backward-compatible
    - Local gates pass: `make verify` and `pre-commit run --all-files`


<a id="ledger-p1-nightly-full-tests-node22-parity"></a>
- [ ] P1: Nightly Full Tests Node 22 parity and release-gate selector alignment
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (CI stability / release safety)
  - Target PR: PR `#1226` (`fix/nightly-full-tests-node22-parity`)
  - Status: In progress as of March 22, 2026
  - Reason: `Nightly Full Tests` failed on `main` after PR `#1209` moved OpenAPI/frontend flows to Node `22.22.1`, because `.github/workflows/nightly-tests.yml` still relied on the runner default Node `20.20.1`. Production release gating in `.github/workflows/cd.yml` also drifted to the legacy `nightly.yml` selector instead of the canonical `Nightly Full Tests` workflow.
  - Links:
    - `docs/ci/triage_nightly_2026-03-22.md`
    - `.github/workflows/nightly-tests.yml`
    - `.github/workflows/cd.yml`
    - `.nvmrc`
    - `frontend/package.json`
    - `scripts/frontend_npm.sh`
    - `tests/test_openapi_determinism.py`
    - Failed run: <https://github.com/Katsiarynakavaleuskaya/PulsePlate/actions/runs/23395469933>
    - Failed job: <https://github.com/Katsiarynakavaleuskaya/PulsePlate/actions/runs/23395469933/job/68057604027>
    - Regression introducer: <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1209>
  - DoD:
    - `Nightly Full Tests` provisions Node from `.nvmrc` and installs frontend dependencies before pytest
    - `pytest -q tests/test_openapi_determinism.py` passes under the nightly workflow contract
    - `cd.yml` production gate queries `nightly-tests.yml` / `Nightly Full Tests`
    - `make verify` and `pre-commit run --all-files` pass on the fix branch
    - Manual `Nightly Full Tests` dispatch on `main` passes after merge and before the next release tag
  - Deferred hardening follow-up:
    - Evaluate `npm ci --ignore-scripts` or split frontend bootstrap into a
      narrower least-privileged nightly job once the parity fix is shipped.
    - Evaluate extracting the Node/frontend bootstrap into a shared workflow or
      composite action so `ci.yml` and `nightly-tests.yml` do not drift again.


<a id="ledger-p1-main-ci-xdist-worker-stability"></a>
- [ ] P1: Main CI xdist worker stability on Python 3.12 full suite
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (CI stability / merge-signal integrity)
  - Target PR: PR #1494 (`codex/fix-ci-xdist-worker-stability`) -> PR #1501 (`codex/main-ci-py312-root-cause-plus-uuid117`) -> containment PR (`codex/main-py312-containment`) -> active timeout root-cause lane (`codex/main-ci-py312-timeout-root-cause`)
  - Status: PR #1494 and PR #1501 landed partial mitigations by April 23, 2026, but live main run `24811914187` still cancelled `test-main (3.12, 60)` after the coverage step reached the 60-minute containment window. PR #1505 containment disabled xdist for Python 3.12, but main run `24849990678` still had `test-main (3.12, 60)` running inside the coverage step after `2026-04-23T19:04:22Z`. Main run `24854923154` then failed the same job with `Segmentation fault (core dumped)` at roughly 20% under the sequential no-xdist coverage command. The active root-cause lane is `codex/main-ci-py312-timeout-root-cause`.
  - Reason: the `main`-branch `CI` full-suite lane continues to surface
    user-reported `"[gw1] node down: Not properly terminated"` instability in
    the xdist-backed `test-main` path. Current lane evidence shows
    `test-main (3.11, 60)` and `test-main (3.13, 90)` finishing normally while
    `test-main (3.12, 60)` cancels after the test step reaches its timeout.
    PR #1494 reduced worker pressure and PR #1501 split serial tests out of
    the 3.12 xdist cohort, but the remaining 3.12 parallel segment still lacks
    a live green main signal. PR #1505 disabled xdist for Python 3.12 only;
    the active follow-up keeps xdist disabled but uses isolated process-level
    shards to recover the `60` minute budget without changing the required
    check identity or weakening pytest/coverage failure semantics.
  - Links:
    - `docs/orchestration/MAINLINE_CI_XDIST_WORKER_STABILITY_PACKET_2026-04-22.md`
    - `docs/orchestration/MAINLINE_CI_XDIST_ROOT_CAUSE_AND_UUID117_PACKET_2026-04-23.md`
    - `docs/orchestration/MAIN_CI_PY312_CONTAINMENT_PACKET_2026-04-23.md`
    - `docs/orchestration/MAIN_CI_PY312_TIMEOUT_ROOT_CAUSE_PACKET_2026-04-23.md`
    - `.github/workflows/ci.yml`
    - `scripts/ci/ci_risk_profile.py`
    - `scripts/ci/run_main_test_shards.py`
    - `.github/workflows/nightly.yml`
    - `pyproject.toml`
    - `tests/test_ci_workflow_pr_size_governance_contract.py`
    - `tests/test_database_apis_coverage.py`
    - User-reported signature: `[gw1] node down: Not properly terminated`
    - Current main run: <https://github.com/Katsiarynakavaleuskaya/PulsePlate/actions/runs/24771474555>
    - `test-main (3.12, 60)` job: <https://github.com/Katsiarynakavaleuskaya/PulsePlate/actions/runs/24771474555/job/72483372336>
    - Later late-zone reproduction with timeout tail: <https://github.com/Katsiarynakavaleuskaya/PulsePlate/actions/runs/24799632664/job/72578492861>
    - Live gate run: <https://github.com/Katsiarynakavaleuskaya/PulsePlate/actions/runs/24811914187>
    - Cancelled `test-main (3.12, 60)` gate job: <https://github.com/Katsiarynakavaleuskaya/PulsePlate/actions/runs/24811914187/job/72651217023>
    - Sequential no-xdist segfault job: <https://github.com/Katsiarynakavaleuskaya/PulsePlate/actions/runs/24854923154/job/72765173124>
    - Healthy comparator `test-main (3.11, 60)` job: <https://github.com/Katsiarynakavaleuskaya/PulsePlate/actions/runs/24771474555/job/72483386535>
    - Green nightly reference: <https://github.com/Katsiarynakavaleuskaya/PulsePlate/actions/runs/24760590280>
  - DoD:
    - `test-main` keeps the same job identity and required-check topology
    - `3.12` runs the full `-m "not slow"` test cohort through isolated
      no-xdist process shards while `3.11` stays parallel and `3.13` keeps its
      existing sequential fallback
    - PRs that change the main-CI Python 3.12 runner/workflow contract run the
      same `test-main` matrix as a scoped diagnostic proof path before merge
    - A regression test freezes the workflow contract
    - `pre-commit run --all-files`, `make validate-changed`, and branch/current-head
      `CI` pass on the remediation branch
    - Post-open `qa-engineer-agent -> bug-hunter` review pass is complete


<a id="ledger-p2-py312-xdist-root-cause-hardening"></a>
- [ ] P2: Python 3.12 xdist root-cause hardening after containment
  - Owner: CI/QA
  - Priority: P2 (CI hardening after required-check containment)
  - Target PR: `codex/main-ci-py312-timeout-root-cause`
  - Status: Active as of April 23, 2026. Pointer entry for the active root-cause lane; the detailed chronology remains in `#ledger-p1-main-ci-xdist-worker-stability`.
  - Reason: PR #1505 containment is not the final root-cause fix. This follow-up tracks bounded evidence for any future pytest-xdist restoration after the deterministic no-xdist shard runner proves the required `test-main (3.12, 60)` budget.
  - Links:
    - `.github/workflows/ci.yml`
    - `tests/AGENTS.md`
    - `tests/test_ci_workflow_pr_size_governance_contract.py`
    - `docs/orchestration/MAIN_CI_PY312_CONTAINMENT_PACKET_2026-04-23.md`
    - `docs/orchestration/MAIN_CI_PY312_TIMEOUT_ROOT_CAUSE_PACKET_2026-04-23.md`
    - Active timeout lane: <https://github.com/Katsiarynakavaleuskaya/PulsePlate/tree/codex/main-ci-py312-timeout-root-cause>
    - Historical worker-node failure: <https://github.com/Katsiarynakavaleuskaya/PulsePlate/actions/runs/24771474555/job/72483372336>
    - Containment gate run: <https://github.com/Katsiarynakavaleuskaya/PulsePlate/actions/runs/24811914187>
  - DoD:
    - Add deterministic evidence or instrumentation for the Python 3.12 main timeout mode
    - Keep 3.12 pytest-xdist disabled until a later bounded audit identifies the minimal xdist-hostile test group or runtime fixture pattern
    - Prove the isolated no-xdist shard runner preserves coverage/JUnit artifacts and fails closed on shard failures
    - Restore Python 3.12 parallelism only if the same current-head CI proves no worker-node termination or timeout
    - Keep required job identity and matrix topology unchanged unless a separate architecture review approves a contract change


<a id="ledger-p1-dependabot-uuid-storybook-carrier"></a>
- [ ] P1: Remove Storybook carrier for Dependabot alert `#117` (`uuid`)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (dependency security / narrow frontend tooling remediation)
  - Target PR: follow-up lane `codex/main-ci-py312-root-cause-plus-uuid117`
  - Status: In progress as of April 23, 2026
  - Reason: Dependabot alert `#117` remains open against
    `frontend/package-lock.json` because Storybook 8's
    `@storybook/addon-actions` still pulls `uuid@9`, while the patched floor is
    `uuid@14.0.0`. A forced `uuid@14` override is not safe here because the
    current Storybook carrier still expects the older CommonJS package shape.
    The narrow remediation is to stop pulling the `addon-actions` carrier while
    preserving the rest of the review-only Storybook surface.
  - Links:
    - `frontend/.storybook/main.ts`
    - `frontend/.storybook/preview.ts`
    - `frontend/package.json`
    - `frontend/package-lock.json`
    - GitHub alert: `security/dependabot/117`
    - Advisory: `GHSA-w5hq-g745-h8pq`
  - DoD:
    - `frontend/package-lock.json` no longer resolves `uuid@9` through the
      Storybook addon carrier
    - Storybook build passes after the narrow addon split
    - frontend build passes after the lockfile refresh
    - no Storybook major migration or unrelated frontend runtime churn is
      introduced in the same PR


<a id="ledger-p1-storybook-ws-ghsa-96hv"></a>
- [ ] P1: Remediate Storybook `ws` audit finding (`GHSA-96hv-2xvq-fx4p`)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (dependency security / frontend tooling remediation)
  - Target PR: current consolidated dependency-security PR (PR-TBD)
  - Status: In progress in the consolidated dependency-security lane opened
    from the 2026-06-18 alert surge; originally opened from PR1 local audit
    residual on 2026-06-16.
  - Reason: The `dompurify` / `js-yaml` remediation lane intentionally stays
    scoped to Dependabot alerts `#164`-`#171`, but
    `npm audit --audit-level=moderate --package-lock-only` still reports
    `ws` `GHSA-96hv-2xvq-fx4p` through Storybook at `8.20.1` with a fixed
    range above the current override. This must be handled in a separate
    frontend tooling dependency PR rather than hidden by target-package audit
    evidence.
  - Links:
    - `frontend/package.json`
    - `frontend/package-lock.json`
    - Advisory: `GHSA-96hv-2xvq-fx4p`
  - DoD:
    - Storybook's resolved `ws` dependency is outside the vulnerable range
    - `npm audit --audit-level=moderate --package-lock-only` no longer reports
      `ws` / Storybook
    - frontend build and `npm run test:ci` pass
    - no unrelated frontend runtime or OpenAPI type-generation churn is included


<a id="ledger-p1-remove-pygments-pip-audit-ignore"></a>
- [ ] P1: Remove temporary Pygments pip-audit ignore when patched release exists
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (dependency security / pre-push unblock follow-up)
  - Target PR: #1282
  - Status: In progress in PR #1282 after the public GHSA flipped to
    `first_patched_version: 2.20.0` on 30 March 2026
  - See ADR: `docs/architecture/ADR_PIP_AUDIT_PYGMENTS_SUPPRESSION_SEAM_2026-03-25.md`
  - Reason: `pip-audit` previously needed a documented temporary
    `--ignore-vuln` exception because `GHSA-5239-wwwm-4pmq` had no patched
    `Pygments` release. The public advisory now exposes `2.20.0` as the safe
    floor, so the branch must retire the seam and pin the patched release
    across the tracked requirement surfaces before merge.
  - Links:
    - GitHub alerts: `security/dependabot/80`, `security/dependabot/81`
    - GitHub advisory: `https://github.com/advisories/GHSA-5239-wwwm-4pmq`
    - `docs/architecture/ADR_PIP_AUDIT_PYGMENTS_SUPPRESSION_SEAM_2026-03-25.md`
    - `.pre-commit-config.yaml`
    - `docs/security/GHSA-5239-wwwm-4pmq-pygments.md`
    - `requirements-ci-lite.txt`
    - `requirements-test.txt`
    - `requirements.txt`
    - `requirements-dev.txt`
    - `requirements-lock.txt`
  - Blockers / Exit criteria:
    - Merge PR #1282 with the patched `Pygments` pins and seam removal
    - CI guard must confirm the live advisory state and reject any attempt to
      reintroduce the ignore or a stale pin below `2.20.0`
    - ADR exit criteria must remain satisfied after merge
  - DoD:
    - A patched `Pygments` release exists and is pinned across the tracked lock surfaces
    - `.pre-commit-config.yaml` no longer carries `--ignore-vuln GHSA-5239-wwwm-4pmq`
    - `pip-audit` passes without the temporary exception
    - ADR exit criteria are satisfied and the seam is retired
    - The security note is updated or closed with final remediation evidence

<a id="ledger-p1-bump-pillow-prepush-baseline"></a>
- [ ] P1: Bump Pillow to clear pre-push pip-audit baseline
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (dependency security / pre-push unblock follow-up)
  - Target PR: PR #1421
  - Status: In progress on PR #1421 as of 14 April 2026
  - Reason: opening the Codex skills alignment draft PR is currently blocked by
    a repo-wide pre-push `pip-audit` failure on `pillow==12.1.1`
    (`GHSA-whj4-6x5x-4v2j`, fixed in `12.2.0`). The blocker is unrelated to the
    skills-alignment diff, but must be tracked explicitly before using
    `git push --no-verify` to publish the draft PR branch.
  - Links:
    - `requirements.txt`
    - `requirements-lock.txt`
    - `requirements-ci-lite.txt`
    - `.pre-commit-config.yaml`
    - `git push` pre-push hook output on branch `feat/codex-skills-alignment-passive`
  - DoD:
    - `requirements.txt`, `requirements-lock.txt`, and `requirements-ci-lite.txt`
      pin a patched Pillow release
    - `pre-commit run --hook-stage pre-push pip-audit --all-files` passes
    - the temporary `--no-verify` exception is no longer needed for this branch class

<a id="ledger-p1-unyank-numpy-runtime-pin"></a>
- [x] P1: Replace yanked numpy runtime pin with a non-yanked release
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (dependency hygiene / install reliability)
  - Target PR: `deps/bump-python-deps-safety-sweep`
  - Status: Addressed in branch `deps/bump-python-deps-safety-sweep` on 2026-06-07
  - Reason: `requirements.txt` and all lock surfaces pinned `numpy==2.4.0`, which is yanked on
    public PyPI and causes installation warnings. Unpinned to `>=2.4.1,<3.0.0` in
    `requirements.in` and regenerated all `requirements*.txt` lockfiles via `pip-compile`.
    `pyarrow` cap lifted from `<24.0.0` to `<25.0.0` in `requirements.in` and
    `requirements-ci-lite.in` as part of the same compatibility sweep.
  - Links:
    - `requirements.in`, `requirements.txt`
    - `requirements-ci-lite.in`, `requirements-ci-lite.txt`
    - `docs/review/PR_<N>_FIXED_MAPPING.md` (to be added after PR open)
  - DoD:
    - [x] `numpy` resolved to non-yanked release (`2.4.6`) across all lock surfaces
    - [x] `pip-compile` produces no yanked-package warnings
    - [x] `pre-commit run --all-files` and `make verify` pass after the bump

<a id="ledger-p1-python-supply-chain-mirror-quarantine"></a>
- [ ] P1: Python package mirror and quarantine lane for hermetic CI/Docker installs
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (supply-chain hardening)
  - Target PR: `PR #1251`
  - Status: In progress on 26 March 2026
  - Reason: Repo-local hardening now fails closed on `PULSEPLATE_PYTHON_INDEX_URL` for shared install paths, but closure still depends on an approved internal mirror or promoted artifact store with quarantine review being provisioned in CI. Required provisioning blocker: `PULSEPLATE_PYTHON_INDEX_URL`; optional compatibility blocker only if the proxy needs it: `PULSEPLATE_PYTHON_TRUSTED_HOST`.
  - Links:
    - `scripts/ci/install_locked_python_requirements.py`
    - `scripts/ci/check_python_startup_hooks.py`
    - `docs/security/LITELLM_SUPPLY_CHAIN_RESPONSE_RUNBOOK.md`
    - `docs/DEPENDENCY_MANAGEMENT.md`
    - `.github/actions/python-setup/action.yml`
    - `.github/workflows/ci.yml`
  - DoD:
    - CI and Docker install from an approved internal mirror or promoted artifact source by default
    - public-index resolution is removed from normal shared CI/bootstrap paths
    - quarantine/promotion review exists for new Python artifacts before they reach shared runners
    - `make verify` and canonical CI continue to pass after the mirror cutover

<a id="ledger-p1-extract-litellm-hardening-followup-pr"></a>
- [ ] P1: Extract LiteLLM supply-chain hardening into a standalone PR
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (recovery and scope hygiene)
  - Target PR: PR #1243
  - Status: Opened on 26 March 2026
  - Reason: The existing LiteLLM hardening work was built on top of a mixed local tree that sat on a merged security branch and collided with unrelated governance drift. The hardening itself is still valid, but it must be preserved and reopened as an isolated PR with only the LiteLLM bucket.
  - Links:
    - `docs/security/LITELLM_SUPPLY_CHAIN_RESPONSE_RUNBOOK.md`
    - `scripts/ci/install_locked_python_requirements.py`
    - `scripts/ci/check_python_startup_hooks.py`
  - DoD:
    - a fresh branch from `origin/main` contains only the LiteLLM hardening bucket
    - unrelated orchestration, Figma, and governance drift is excluded
    - `pre-commit run --all-files` and `make verify` pass on the extracted branch
    - the PR description states that the change is prevention hardening, not proof of compromise
    - post-open review uses `qa-engineer-agent -> bug-hunter`

<a id="ledger-p1-py313-main-ci-stall-root-cause"></a>
- [ ] P1: Root-cause Python 3.13 CI slowdown and retire timeout stopgap
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (CI stability / main-branch readiness)
  - Target PR: PR #1516 (`codex/main-ci-py313-timeout-prevention`)
  - Status: Active prevention lane as of 24 April 2026
  - Status note: PR #1511 proved `test-main (3.13, 90)` could pass but only in
    about 88m44s, leaving almost no timeout budget. This lane routes Python 3.13
    through the shared process-level main-suite shard runner while preserving
    the `test-main (3.13, 90)` required-check identity.
  - Reason: Current-head feature and `main` CI runs both show a pathological
    Python 3.13 slowdown in canonical `CI`. `test-feature (3.13)` reached the
    60-minute job timeout in run `24266451930`, and PR #1511 current-head
    evidence showed `test-main (3.13, 90)` passing with only about 1m16s of
    headroom. The prevention path is shared no-xdist process sharding for 3.12
    and 3.13, not a broader timeout increase or weakened coverage gate.
  - Links:
    - `.github/workflows/ci.yml`
    - `scripts/ci/run_main_test_shards.py`
    - `tests/test_main_test_shards.py`
    - `RUNBOOK_AGENT.md`
    - `docs/orchestration/TIER1_CI_CD_PR_SERIES_RUNBOOK.md`
    - `https://github.com/Katsiarynakavaleuskaya/PulsePlate/actions/runs/24266451930/job/70862392048`
  - DoD:
    - a representative current-head feature or `main` run shows Python 3.13
      tests completing without unexplained pathological slowdown
    - the slowest Python 3.13 tests or setup segment are identified from
      deterministic diagnostics
    - the py3.13-specific timeout increase is either justified with documented
      evidence or removed
    - canonical `CI` returns to stable green without manual rerun dependence
    - any remaining workflow debt is documented explicitly rather than hidden
      inside the stopgap

<a id="ledger-p2-canonical-ci-shard-map-redesign"></a>
- [ ] P2: Redesign shard map before any canonical CI shard rollout
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2 (test topology hardening)
  - Target PR: PR-TBD-CI-SHARD-MAP-REDESIGN
  - Status: Opened on 12 April 2026
  - Reason: Existing shard patterns are not exhaustive enough for canonical CI
    truth and would silently omit a large portion of the test surface if
    promoted directly.
  - Links:
    - `pytest_sharding.py`
    - `.github/workflows/ci.yml`
  - DoD:
    - every shard selection rule is coverage-audited against the current test
      inventory
    - shard topology has deterministic completeness guards
    - no shard rollout reaches canonical CI without an explicit completeness
      proof

<a id="ledger-p2-ci-contract-risk-helper-extraction"></a>
- [ ] P2: Centralize duplicated contract/risk suite map before next CI topology pass
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2 (CI maintainability / workflow drift prevention)
  - Target PR: PR-TBD-CI-CONTRACT-RISK-HELPER
  - Status: Opened on 12 April 2026
  - Status note: `fix/ci-feature-fast-feedback` intentionally keeps the duplicated
    workflow-local suite map so the merge-conflict + fail-closed stabilization
    stays small. Do not reopen PR 1405 for this refactor.
  - Reason: `.github/workflows/ci.yml` currently carries two copies of the
    `CONTRACT_RISK_GROUPS` -> pytest-target expansion logic across `test-pr`
    and `test-feature`. This is acceptable for the current fast-feedback
    stabilization, but it creates future drift risk and should be replaced by a
    single shared helper before the next CI topology change.
  - Links:
    - `.github/workflows/ci.yml`
    - `scripts/ci/ci_risk_profile.py`
    - `docs/review/PR_1405_FIXED_MAPPING.md`
  - DoD:
    - one canonical helper expands `CONTRACT_RISK_GROUPS` into a deterministic,
      sorted pytest target list
    - `test-pr` and `test-feature` consume the same helper instead of duplicating
      the group map in YAML
    - unknown groups still fail closed with a non-zero exit
    - empty selections remain an explicit no-op with stable logs
    - workflow contract tests cover the shared helper wiring end to end

<a id="ledger-p1-canonical-fail-invariance-fixtures"></a>
- [ ] P1: Canonical-fail invariance fixture coverage for judgment and RAG validity datasets
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR #1659 (`evals/canonical-fail-invariance-fixtures`)
  - Status: Opened on 4 May 2026
  - Reason: PR #1657 and PR #1658 added judgment and RAG invariance/mutation variant families, but both fixture sets documented a limitation: all canonical rows had `decision: "pass"`. This PR adds canonical-fail invariance groups so invariance testing covers fail-to-fail stability.
  - Links:
    - `docs/evals/PULSEPLATE_EVAL_VALIDITY_CONTRACT.md`
    - `docs/evals/PULSEPLATE_RAG_RELEASE_GATES.md`
    - `data/evals/pulseplate_judgment_eval_validity_variants.jsonl`
    - `data/evals/pulseplate_rag_release_gate_validity_variants.jsonl`
    - `tests/evals/test_judgment_validity_variant_families.py`
    - `tests/evals/test_rag_release_gate_validity_variant_families.py`
  - DoD:
    - Judgment fixture set includes at least one canonical-fail group with invariance rows preserving the failing decision
    - RAG fixture set includes at least one canonical-fail group with invariance rows preserving the failing decision
    - Tests prove fail-to-fail invariance for both fixture sets
    - Existing mutation_drop, unstable_items, and deterministic report tests remain green
    - Existing RAG thresholds, PASS/NO-GO logic, and judgment promote/defer/discard logic remain unchanged
    - No runtime/API/frontend/iOS/billing/OpenAPI/App Store changes

<a id="ledger-p1-eval-item-metadata-registry"></a>
- [x] P1: Evaluation item metadata registry for psychometric readiness
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR #1660 (merged `b4335d405`, 2026-05-04)
  - Status: **CLOSED** — merged 4 May 2026
  - Area: evals / measurement science / psychometric readiness
  - Finding Type: item-metadata gap
  - Reason: The Evaluation Science foundation now has item-level outcomes, RAG/judgment sidecars, invariance/mutation fixtures, and canonical-fail negative controls, but still lacks a registry that maps canonical_id values to stable item metadata such as lane, domain, skill dimension, difficulty band, expected decision, expected score band, fixture coverage, and anchor-item status. This registry is required before honest IRT, item weighting, adaptive evals, or psychometric modeling.
  - Links:
    - `docs/evals/PULSEPLATE_EVAL_VALIDITY_CONTRACT.md`
    - `scripts/evals/eval_item_registry.py`
    - `data/evals/eval_item_metadata_registry.jsonl`
    - `data/evals/pulseplate_judgment_eval_validity_variants.jsonl`
    - `data/evals/pulseplate_rag_release_gate_validity_variants.jsonl`
    - `tests/evals/test_eval_item_metadata_registry.py`
  - DoD:
    - Registry contains exactly one row per canonical_id in judgment and RAG variant fixtures
    - Registry has no orphan canonical_id rows
    - Registry validates lane, difficulty_band, expected_score_band, and variant_family_coverage
    - Registry expected_decision matches fixture canonical rows
    - Registry coverage tests are deterministic
    - No IRT or psychometric scoring is implemented
    - No runtime/API/frontend/iOS/billing/OpenAPI/App Store/Claude/Opus/MCP changes are included

<a id="ledger-p1-eval-item-statistics-baseline"></a>
- [ ] P1: Evaluation item statistics baseline for empirical-readiness
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR #1662 (`evals/item-statistics-baseline`)
  - Area: evals / measurement science / psychometric readiness
  - Finding Type: item-statistics gap
  - Reason: Evaluation item metadata registry is present, but the project still lacks deterministic descriptive item statistics that combine registry metadata with curated fixture outcomes. This layer is required before honest item weighting, IRT, adaptive evals, or empirical calibration.
  - Links:
    - `docs/evals/PULSEPLATE_EVAL_VALIDITY_CONTRACT.md`
    - `scripts/evals/eval_item_statistics.py`
    - `scripts/evals/run_eval_item_statistics.py`
    - `data/evals/eval_item_metadata_registry.jsonl`
    - `tests/evals/test_eval_item_statistics.py`
  - DoD:
    - Descriptive item statistics are generated deterministically from registry + fixture outcomes
    - Report includes per-item pass_rate, invariance agreement, mutation drop, worst variant score, decision set, and instability flag
    - RAG PASS/NO-GO logic remains unchanged
    - Judgment promote/defer/discard logic remains unchanged
    - No IRT or psychometric scoring is implemented
    - No runtime/API/frontend/iOS/billing/OpenAPI/App Store/Claude/Opus/MCP changes are included

<a id="ledger-p1-ruby-3-3-fastlane-runtime"></a>
<a id="ledger-p1-ruby-3-4-10-fastlane-runtime"></a>
- [ ] P1: Migrate the Fastlane execution runtime to Ruby 3.4.10
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (release-tooling compatibility)
  - Target PR: #2113
  - Status: Open on 13 July 2026; implementation and review in progress
  - Reason: The no-auth validation lane passes with Fastlane `2.237.0` on the
    canonical Ruby `3.1` runtime, but Fastlane emits an explicit warning that a
    future release will require Ruby `3.3` or newer. Ruby `3.1` reached end of
    life on 26 March 2025, while Ruby `3.4.10` is a supported exact patch on the
    maintained Ruby `3.4` branch. This lane removes the unsupported release
    interpreter without widening into a Ruby `4.0` or Fastlane dependency
    migration.
  - Links:
    - `tests/runtime_toolchain_versions.py`
    - `tests/test_runtime_toolchain_alignment.py`
    - `ios/Gemfile`
    - `docs/security/CVE-2026-54171-excon-fastlane.md`
  - DoD:
    - canonical local and CI Ruby versions are upgraded together to a supported
      exact Ruby `3.4.10` release
    - Fastlane and Bundler locks remain deterministic and compatible
    - the no-auth `validate_metadata_package` lane passes without the Ruby
      deprecation warning
    - iOS release tooling and current-head CI pass without App Store mutation
    - rollback and operator migration instructions are documented

<a id="ledger-p1-legacy-guard-final-security-carryover"></a>
- [ ] P1: Consolidate legacy-growth guard hardening
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: this PR (`codex/legacy-guard-final-security-hardening`)
  - Status: In progress on 19 July 2026; replaces the incomplete PRs #2158,
    #2159, #2160, and #2161 without cherry-picking their implementations.
  - Reason: Twelve unresolved review findings across the four superseded lanes
    show false-green variadic replay, non-terminating or false-safe provenance,
    over-broad or non-propagating `object()` poisoning, and deferred-lambda
    bypasses. This lane owns only those legacy-growth findings. Retirement of
    legacy final-security provider request/preparation/outcome authoring moved
    to the combined provider-neutral bootstrap lane (carryover from closed
    PRs #2184 and #2187), avoiding duplicate implementation ownership.
  - Links:
    - `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2158#discussion_r3610033430`
    - `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2158#discussion_r3610039977`
    - `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2158#discussion_r3610039980`
    - `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2159#discussion_r3610033136`
    - `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2159#discussion_r3610040544`
    - `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2160#discussion_r3610041147`
    - `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2160#discussion_r3610041148`
    - `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2160#discussion_r3610041149`
    - `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2160#discussion_r3610041150`
    - `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2161#discussion_r3610042941`
    - `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2161#discussion_r3610042945`
    - `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2161#discussion_r3610042946`
  - DoD:
    - all twelve findings have deterministic positive/negative regression
      coverage and the legacy-growth analysis remains terminating, idempotent,
      and fail-closed at its provenance bound
    - Qoder manifests remain role-only while the versioned lifecycle packet and
      start prompt own exact-head review gates
    - the replacement PR records the carryover, supersedes and closes
      #2158-#2161 without merge, and is handed to the owner without merging

**Last updated:** 2026-07-27 (legacy guard remains; provider retirement ownership transferred)
**Maintainer:** @katsiaryna_kavaleuskaya
<!-- markdownlint-enable MD013 -->
