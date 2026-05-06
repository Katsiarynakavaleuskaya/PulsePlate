# PR 1688 Premortem: Production Release Evidence Wiring

Mode: `pr-premortem`
Skill: `pulseplate-premortem-risk-review`
Packet: `artifacts/orchestration/task_packets/5fc8577f508e.json`

## Frame

It is 48 hours from now. This CI/CD release-governance PR made production
release evidence validation weaker or misleading. We are looking backward to
understand why.

## Scope Inspected

- `.github/workflows/cd.yml`
- `docs/release/PRODUCTION_RELEASE_EVIDENCE_WIRING.md`
- `docs/release/RELEASE_CONTROL_PLANE_EPIC.md`
- `docs/orchestration/RELEASE_CONTROL_PLANE_TASK_PACKET_2026-04-29.md`
- `docs/roadmap/BACKLOG_LEDGER.md`
- `tests/test_production_release_evidence_wiring.py`
- `tests/test_release_control_plane_ci_gate.py`
- `tests/test_build_equivalence.py`

## Findings

### P1: Production evidence artifact could belong to a different tag commit

**Failure story:** The production tag workflow downloaded a real-looking
release-control-plane artifact from the configured prior run. The existing
checker verified the release manifest, RAG gate result, build-equivalence
result, hashes, and supply-chain fields against each other, but the workflow did
not independently prove that the manifest build git SHA matched the commit
selected by the production tag. A stale or wrong evidence artifact could pass
internal consistency checks while representing a different commit.

**Underlying assumption:** Internal evidence coherence was enough without a
tag-commit cross-check at the production workflow boundary.

**Fix:** `ci(release): require production evidence to match tag commit`
(`0bc019fd0`) adds a production workflow check that resolves
`${GITHUB_REF#refs/tags/}^{commit}`, reads
`release_manifest.json` `build_identity.git_sha`, and fails closed when they do
not match.

**Evidence:**

- `.github/workflows/cd.yml` production evidence job uses checkout
  `fetch-depth: 0` before resolving the tag commit.
- `.github/workflows/cd.yml` validates `manifest_git_sha != tag_commit` as a
  blocking error.
- `tests/test_production_release_evidence_wiring.py::test_production_job_rejects_evidence_for_different_tag_commit`
  covers the workflow contract.

**Disposition:** FIXED.

### P1: Production evidence artifact could come from an ungoverned source run

**Failure story:** The workflow accepted a numeric run id and non-fixture
artifact name, then downloaded the artifact before verifying the run that
produced it. An arbitrary same-repository run could upload a matching-looking
release-control-plane artifact for the tag commit. The content-level manifest
git SHA check would catch cross-commit drift, but not whether the evidence came
from a completed, successful, governed release-evidence producer.

**Underlying assumption:** Artifact content validation was enough without
checking the GitHub Actions run provenance for the evidence-producing run.

**Fix:** The production evidence download step now calls
`gh run view "$RELEASE_CONTROL_PLANE_EVIDENCE_RUN_ID" --json status,conclusion,headSha,event,workflowName,url`
before download and fails closed unless the source run is completed, successful,
matches the production tag commit, is a `workflow_dispatch` run, and has a
release-control-plane workflow name.

**Evidence:**

- `.github/workflows/cd.yml` verifies source run metadata before
  `gh run download`.
- `docs/release/PRODUCTION_RELEASE_EVIDENCE_WIRING.md` documents source-run
  provenance requirements and fail-closed rules.
- `tests/test_production_release_evidence_wiring.py::test_production_job_verifies_evidence_run_provenance_before_download`
  covers the workflow contract.

**Disposition:** FIXED.

## Failure Modes Rechecked

1. Production deploy can proceed without `release_manifest.json`.
   - Disposition: NOT-A-BUG after inspection.
   - Evidence: production evidence job checks `release_manifest.json` exists
     before invoking the checker; checker also returns `missing_release_manifest`.

2. Production deploy can proceed without `rag_gate_result.json`.
   - Disposition: NOT-A-BUG after inspection.
   - Evidence: production evidence job checks `rag_gate_result.json` exists
     before invoking the checker; checker also returns `missing_rag_gate_result`.

3. Production deploy can proceed without `build_equivalence_result.json`.
   - Disposition: NOT-A-BUG after inspection.
   - Evidence: production evidence job checks `build_equivalence_result.json`
     exists before invoking the checker; checker also returns
     `missing_build_equivalence`.

4. Fixture evidence is used in production tag path.
   - Disposition: NOT-A-BUG after inspection.
   - Evidence: fixture job is `main` only, production artifact names reject
     fixture naming, and production workflow tests assert no fixture paths in
     the production job.

5. Release-control-plane gate is advisory or `continue-on-error`.
   - Disposition: NOT-A-BUG after inspection.
   - Evidence: production evidence job invokes
     `scripts/ci/check_release_control_plane.py` without `continue-on-error`;
     deploy jobs depend on the evidence job.

6. Workflow requires App Store secrets in normal PR/main validation path.
   - Disposition: NOT-A-BUG after inspection.
   - Evidence: production evidence job uses only `secrets.GITHUB_TOKEN`; tests
     assert no App Store/Fastlane secret terms in the production evidence job.

7. Workflow adds Fastlane/App Store upload mutation.
   - Disposition: NOT-A-BUG after inspection.
   - Evidence: changed files do not include `ios/fastlane/**`; production
     workflow tests assert no Fastlane/App Store upload terms.

8. Evidence git SHA mismatch is ignored.
   - Disposition: FIXED.
   - Evidence: P1 finding above fixed in `0bc019fd0`.

8b. Evidence run provenance is ignored.
    - Disposition: FIXED.
    - Evidence: second P1 finding above fixed before mapping; focused workflow
      tests assert source-run metadata is checked before artifact download.

9. SBOM/provenance evidence is ignored.
   - Disposition: NOT-A-BUG after inspection.
   - Evidence: PR-5 checker still blocks missing/invalid SBOM/provenance
     digests and unverified attestation; PR-6 invokes that checker in the
     production tag path.

10. Release gate artifact is not uploaded.
    - Disposition: NOT-A-BUG after inspection.
    - Evidence: production evidence job uploads
      `release-control-plane-ci-gate-cd-production` with JSON and Markdown
      output paths.

11. Workflow breaks normal PR CI path.
    - Disposition: NOT-A-BUG after inspection.
    - Evidence: CD workflow still triggers on `main` and `v*` tags only; the
      production evidence job is tag-only and deploy-active only.

12. Ledger incorrectly claims full App Store readiness complete.
    - Disposition: NOT-A-BUG after inspection.
    - Evidence: ledger says full App Store readiness is not complete and train
      is not production-ready.

13. Runtime/API/iOS/OpenAPI files are changed.
    - Disposition: NOT-A-BUG after inspection.
    - Evidence: diff is limited to workflow, release docs, ledger, and tests.

14. Mapping/checklists are used instead of fixing findings.
    - Disposition: NOT-A-BUG after inspection.
    - Evidence: the P1 finding was fixed in workflow/tests before this artifact
      records it.

## Decision

`proceed with changes` -> after the tag-commit cross-check and source-run
provenance fixes, no unresolved P0/P1 premortem findings remain.

Unresolved P0/P1: none.
Unresolved P2: none.

## Validation Evidence

- `python3 scripts/orchestration/check_preflight.py` PASS
- `python3 scripts/orchestration/check_agent_consistency.py` PASS
- `. .venv/bin/activate && pytest -q tests/test_production_release_evidence_wiring.py` PASS (`12 passed`) before the source-run provenance fix
- `. .venv/bin/activate && pytest -q tests/test_production_release_evidence_wiring.py tests/test_release_control_plane_ci_gate.py tests/test_build_equivalence.py` PASS (`61 passed`) after the source-run provenance fix
- Bounded release-control-plane suite PASS before the premortem fix (`11`, `26`, `20`, `22`, `48`, `12`, and `14` passing test groups)
- `python3 scripts/ci/check_docs_phase1_gates.py --files docs/release/PRODUCTION_RELEASE_EVIDENCE_WIRING.md docs/release/RELEASE_CONTROL_PLANE_EPIC.md docs/orchestration/RELEASE_CONTROL_PLANE_TASK_PACKET_2026-04-29.md docs/roadmap/BACKLOG_LEDGER.md` PASS
- `make validate-changed` PASS (`59 passed`) before the premortem fix; rerun required after this artifact lands.
- `pre-commit run --all-files` PASS before the premortem fix; rerun required after this artifact lands.
