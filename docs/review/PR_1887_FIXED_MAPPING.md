# PR 1887 Fixed in Commit Mapping

## Scope

This PR adds an internal-only Verification Provenance Admission Report v1 for
the already-merged `VerificationProvenance` metadata. The report is a
deterministic guard/report over existing runtime/RAG admission paths and does
not change public API, OpenAPI, DB schema, provider selection, frontend, iOS,
Slack, semantic cache, GraphRAG, or runtime behavior.

## Lane Start Provenance

- Starter: `scripts/orchestration/start_pr_lane.sh`
- Branch: `codex/verification-provenance-admission-report-v1`
- Base: `origin/main` at `1f24ab80296aeca598f14ccb1992cb41b82a02e6`
- Packet: `artifacts/orchestration/task_packets/65d287e516d0.json`
- Operator override: branch start proceeded while the operator monitored
  post-merge `main` health.
- Required pre-open role order completed:
  `agent-coordinator -> cursor-specialist-agent -> security-auditor -> architecture-specialist`
- Architecture pass note: read-only fallback transport was used after native
  transport was unavailable; the repo role slug and packet context remained the
  authority.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed
- Post-open actionable Codex and Cubic review threads are mapped below with
  disposition evidence.

## Fixed in Commit Mapping

Disposition: FIXED
Commit: 68bb09c1f
Evidence: source refs now validate real AST-defined symbols, redaction_source existence is checked, schema raw-leak scan is enforced, and regression tests cover all Cubic findings.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1887#pullrequestreview-4436023126 -> 68bb09c1f
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1887#discussion_r3362439281 -> 68bb09c1f
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1887#discussion_r3362439282 -> 68bb09c1f
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1887#discussion_r3362439283 -> 68bb09c1f
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1887#discussion_r3362439286 -> 68bb09c1f

Disposition: FIXED
Commit: afd995a5c
Evidence: recursive schema/report validation now catches nested required/properties drift, digestLabel definition is pinned, source refs are resolved fail-closed under the repository before reads, direct/local path reporting no longer claims verification-first checks, disabled runtime verification records inherited failed bundle semantics, and focused report/docs/runtime tests pass.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1887#discussion_r3362309639 -> afd995a5c
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1887#discussion_r3362309643 -> afd995a5c
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1887#discussion_r3362504259 -> afd995a5c
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1887#discussion_r3362504265 -> afd995a5c
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1887#discussion_r3362504268 -> afd995a5c

Disposition: FIXED
Commit: 68bb09c1f
Evidence: schema raw-leak validation was added in `68bb09c1f`; follow-up regression coverage in `afd995a5c` also covers workflow-log, token, and local-path schema annotation leakage together.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1887#discussion_r3362405132 -> 68bb09c1f

Disposition: FIXED
Commit: 68bb09c1f
Evidence: `redaction_source` is validated against the actual AST-defined `core.verification.registry.redacted_sha256_label` symbol.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1887#discussion_r3362405138 -> 68bb09c1f

## Implementation Evidence

- Implementation commit:
  `0bada0dc35c603cc3f102850a2623f3adb80e902`
- Review hardening commit:
  `afd995a5c76eee6a06015dbfa7a96c3ab59be2e4`
- Evidence:
  - `docs/orchestration/contracts/VERIFICATION_PROVENANCE_ADMISSION_REPORT.json`
  - `docs/orchestration/contracts/VERIFICATION_PROVENANCE_ADMISSION_REPORT.schema.json`
  - `scripts/ci/check_verification_provenance_admission_report.py`
  - `tests/test_verification_provenance_admission_report.py`
  - `scripts/ci/check_docs_phase1_gates.py`
  - `.github/workflows/ci.yml`

## Premortem Findings

- Disposition: FIXED
  Evidence: the checker uses stdlib AST/source inspection instead of importing
  runtime builders, preventing Docs Phase1 from depending on runtime/backend
  dependencies.
- Disposition: FIXED
  Evidence: CLI output uses repo-relative labels and
  `tests/test_verification_provenance_admission_report.py` rejects local-path,
  token, Slack ID, workflow-log, provider-log, and raw prompt/context/answer
  leakage.
- Disposition: FIXED
  Evidence: the schema is closed with `additionalProperties: false`, and tests
  reject unknown keys, authority expansion, schema drift, invalid digest labels,
  and missing provenance coverage.
- Disposition: FIXED
  Evidence: semantic-cache gate validation passes and roadmap/backlog wording
  keeps semantic cache and GraphRAG out of scope.

## Experiment Runner Evidence

- Artifact: `artifacts/orchestration/experiments/results/exp-5e268f722354.json`
- Mode: `oracle_only_governance_reviewer`
- Status: `accepted`
- Contribution kind: `oracle_review`
- `shared_tree_untouched`: `true`
- `oracle_commands_executed`: `3`
- `source_diff_applied`: `true`
- `coauthor_required`: `true`
- Co-author trailer is present on
  `0bada0dc35c603cc3f102850a2623f3adb80e902`.

## Validation

- PASS: `python3 scripts/orchestration/check_preflight.py --path ...`
- PASS: `python3 scripts/ci/check_verification_provenance_admission_report.py --check`
- PASS: `python3 scripts/ci/check_docs_phase1_gates.py --files docs/orchestration/contracts/VERIFICATION_PROVENANCE_ADMISSION_REPORT.json docs/orchestration/contracts/VERIFICATION_PROVENANCE_ADMISSION_REPORT.schema.json docs/roadmap/EVIDENCE_GRAPH_RUNTIME_EPIC.md docs/roadmap/BACKLOG_LEDGER.md`
- PASS: `python3 scripts/ci/check_semantic_cache_gate.py --doc docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md`
- PASS: focused pytest for
  `tests/test_verification_provenance_admission_report.py`,
  `tests/test_docs_phase1_gates.py`,
  `tests/test_remaining_modules.py::TestVerificationRegistryCoverageTail`,
  `tests/test_rag_orchestration.py`,
  `tests/test_philosophical_runtime.py`,
  `tests/test_insight_application_service.py`,
  `tests/test_knowledge_promotion.py`, and
  `tests/test_semantic_cache_gate.py`.
- PASS: `make validate-changed`
- PASS: `pre-commit run --all-files`
- PASS: pre-push hooks during `git push`, including changed-files mypy,
  pip-audit, backend pre-push pytest, full-repo bandit, and docker build test.
- Not run: full local `make verify`. This is an operator-approved
  machine-heavy deferral; this PR relies on focused local gates plus canonical
  current-head CI parity before merge-readiness claims.

## Semantic Gate Recheck

- PASS: `python3 scripts/ci/check_semantic_cache_gate.py --doc docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md`
- Semantic-cache markers remain `closed / false / false / true`.
- This is a closed-gate assertion only, not semantic-cache activation.

## Post-Open Review Gates

- [x] `qa-engineer-agent`: completed. Findings on mapping/body drift and nested
  schema false-green risk were fixed in `c296721e9` and `f3974d211`.
- [x] `bug-hunter`: completed with no blocking findings after QA fixes.
- [x] `security-auditor`: completed with status `PASS_NO_FINDINGS_NOT_MERGE_READY`;
  confirmed no changed `app/`, `core/`, `frontend/`, `ios`, OpenAPI, Slack, or
  runtime API files; no new secret, workflow_dispatch, live-token, semantic-cache,
  or runtime-authority behavior in the diff.
- [x] Codex Security diff scan / finding discovery: completed with 12/12 explicit
  PR diff files closed in the local work ledger, no raw candidates, validated
  markdown report, and rendered HTML report. The default plugin diff rank helper
  excluded governance/docs/test paths, so the scan recorded that limitation and
  used the explicit `git diff --name-only origin/main...HEAD` worklist.
- [x] `pulseplate-pr-review`: completed in dry-run report mode. It produced one
  advisory large-diff note because generated report/schema/test changes exceed
  the review-risk threshold; disposition is non-blocking because the PR scope is
  intentionally one deterministic governance contract/report slice and
  `make validate-changed` passed.

## Merge Readiness

- Not claimed.
- Current-head CI, bot review state, final discussion-thread pass, strict
  disposition checks, strict merge-readiness checks, and wait-window remain
  pending.
