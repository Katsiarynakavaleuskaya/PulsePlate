<!-- markdownlint-disable MD013 MD034 -->
# PR 1716 Fixed In Commit Mapping

- PR: <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1716>
- Branch: `codex/fix-build-equivalence-evidence-vulnerability`
- Title: `fix(release): bind build-equivalence digests to governed sources`
- Initial reviewed head: `897294216ab1315e9fbe4797b6a7cb234fc5b92a`
- Review-fix commit: `64b6c33d0b951a05fe3bf0b607096e20337d22c7`
- Status: binds review/production digests to governed build-source artifacts (implementation); Phase2 mapping + tighter upload regression test tracked in bookkeeping commit atop this SHA.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

Open review-bot actionables were dispositioned against the governance YAML change (`64b6c33`). This file plus the bookkeeping commit add merge-gate SoT coverage and assertions. PR body mirrors Phase2 checklist items only.

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1716#discussion_r3212916333 -> 64b6c33d0b951a05fe3bf0b607096e20337d22c7
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1716#discussion_r3212921878 -> 64b6c33d0b951a05fe3bf0b607096e20337d22c7
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1716#pullrequestreview-4257513239 -> 64b6c33d0b951a05fe3bf0b607096e20337d22c7
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1716#pullrequestreview-4257518721 -> 64b6c33d0b951a05fe3bf0b607096e20337d22c7

Disposition: FIXED

Commit: 64b6c33d0b951a05fe3bf0b607096e20337d22c7

Evidence: `.github/workflows/build-equivalence-evidence.yml` validates `review_artifact_digest_source` / `production_candidate_artifact_digest_source` via governed `artifact_digest.txt` downloads and oci-digest checks before emitting equivalence evidence; upload uses `steps.generate-build-equivalence-evidence.outputs.artifact_name` (not `${{ inputs.evidence_artifact_name }}`).

Evidence: `.github/workflows/build.yml` publishes `release-control-plane-build-sources/artifact_digest.txt` from the Docker build digest output.

Evidence: `tests/test_build_equivalence_evidence_workflow.py` asserts upload-artifact binds the artifact `name` to the generation step output, step ordering versus the generate step, and rejects wiring the upload `with.name` straight to `${{ inputs.* }}`.

Evidence: Aggregate review links disposition to the same governed-digest workflow commit noted above.

## Local Validation Evidence

- `.venv/bin/python3 -m pytest tests/test_build_equivalence_evidence_workflow.py` — PASS

## Security Notes

- Reduces trust in operator-supplied digest strings by requiring matching governed build-source artifacts and successful source-run metadata checks.

## Risks / Rollback

- Risk: callers must supply new JSON source inputs for equivalence runs. Mitigation: migration notes in PR description.
- Rollback: revert `64b6c33d0b951a05fe3bf0b607096e20337d22c7` to drop governed digest enforcement; revert bookkeeping commits that added this artifact if merge policy must unwind.

## Deferred / Follow-ups

- None for this mapping cycle.
