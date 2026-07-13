# PR #2112 Fixed in Commit Mapping SoT

PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2112

Branch: `codex/adaptive-context-pack-lineage-fix`

## Summary

Preserve byte-identical historical context-pack lineage for adaptive PR-1
resume while keeping stable semantic fields, target/oracle continuity, current
base checks, and all downstream authorities fail-closed.

## Lane Start Provenance

- Coordinator packet and role outputs are retained locally under the
  gitignored `artifacts/orchestration/` control plane.
- Pre-open and post-open role ordering was executed under the active
  coordinator packet.
- Experiment Runner evidence contributed to the validator, replay, and commit
  decisions; implementation commits carry the canonical co-author trailer.

## Implementation Commits

- `6eef22de7512fc8bd388feb41dd96a701fe40196` - normalize only the
  size-derived `no_context_reduction` reason and clarify scalar-type wording.
- `114111b50a8aa039ef40cf6b894594e1725a80c4` - fail `build-handoff`
  before any bridge, candidate, or prepare output when `origin/main` no longer
  equals the approved workspace target head.

## Discussion Thread Pass

- [x] Discussion-thread pass completed.
- [x] Fixed in commit mapping completed.
- [x] Post-open `qa-engineer-agent -> bug-hunter -> security-auditor` completed.
- [x] Codex Security diff scan completed for the final material source diff.
- [ ] Canonical current-head CI completed.
- [ ] Strict authenticated merge readiness and mandatory wait window completed.

## Fixed in Commit Mapping

Disposition: FIXED
Commit: 6eef22de7512fc8bd388feb41dd96a701fe40196
Evidence: `tests/test_creative_code_specification.py` covers added, removed, and duplicate size-derived reason tampering while stable fields remain exact.
Reason: Historical comparison now normalizes only `no_context_reduction` when retained arithmetic proves that reason is size-derived.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2112#discussion_r3570809856 -> 6eef22de7512fc8bd388feb41dd96a701fe40196

Disposition: FIXED
Commit: 6eef22de7512fc8bd388feb41dd96a701fe40196
Evidence: `docs/orchestration/GOVERNED_CREATIVE_CODE_EXECUTION_CONTRACT.md` now states `boolean-to-integer or other scalar-type substitution` explicitly.
Reason: The documentation no longer uses the ambiguous boolean/integer wording.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2112#discussion_r3571608033 -> 6eef22de7512fc8bd388feb41dd96a701fe40196

Disposition: FIXED
Commit: 114111b50a8aa039ef40cf6b894594e1725a80c4
Evidence: `tests/test_creative_pilot_workspace.py::test_build_handoff_rejects_origin_main_drift_before_any_output` proves the bundle and prepare paths are not called, the workspace remains byte-identical, and no handoff output exists.
Reason: `build-handoff` now rejects temporal base drift before any artifact materialization or write.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2112#discussion_r3571890953 -> 114111b50a8aa039ef40cf6b894594e1725a80c4

## Experiment Runner Evidence

The retained `rag-confidence-provenance-pilot-2f` replay reached
`agent-skeptic-review` with `replay=new` and then `replay=idempotent`; no PR-2
generation attempt was consumed. Evidence remains local-only and gitignored.

## Validation Evidence

- PASS: orchestration preflight and agent consistency.
- PASS: focused creative-code specification and pilot-workspace suites.
- PASS: production mypy for the changed orchestration modules.
- PASS: `make validate-changed`.
- PASS: `pre-commit run --all-files`.
- PASS: pre-push pip-audit, focused backend tests, full-repo Bandit, and Docker
  build hook.
- PENDING: canonical current-head GitHub CI and strict authenticated merge
  readiness.

Full local `make verify` was not run because repository policy prohibits that
machine-heavy invocation without a one-time human override.

## Security Review

- PASS: sealed Codex Security source-diff scan `scan_pr2112_114111b50` at
  `114111b50a8aa039ef40cf6b894594e1725a80c4` reviewed all three source-like
  rows. Two defensive candidates were explicitly validated and rejected; zero
  reportable findings survived final reportability policy.
- The scan is retained locally and gitignored at
  `artifacts/security_lab/pr-2112-final/`.

## Risks / Rollback

If historical compatibility or build-handoff gating regresses, revert PR #2112
as one unit and keep the dependent RAG creative-code lane blocked. No database,
runtime, provider, cache, API, or client rollback is required.

## Deferred / Follow-ups

After PR #2112 merges, restart the RAG creative-code lane from fresh
`origin/main`. Bayesian routing, learned Markov behavior, semantic-cache
serving, Evidence Graph product truth, and OCW runtime remain outside this PR.
