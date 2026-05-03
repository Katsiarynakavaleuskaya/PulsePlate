# PR #1643 Fixed in Commit Mapping

## Summary

PR #1643 adds a CPU-only RAG/vector dependency profile (`requirements-rag-vector-cpu.in/.txt`)
for local development without CUDA. Docs updated in `docs/DEPENDENCY_MANAGEMENT.md`.

## Scope

- `requirements-rag-vector-cpu.in` — new CPU-only `.in` file
- `requirements-rag-vector-cpu.txt` — compiled lockfile
- `docs/DEPENDENCY_MANAGEMENT.md` — dependency management docs

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

### Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1643#discussion_r3178009660
  Disposition: FIXED
  Commit: 44a03e5a3
  Evidence: docs/DEPENDENCY_MANAGEMENT.md — `rag-vector-cpu` note moved from CI Install Profiles section to Local CPU profile section

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1643#discussion_r3178009661
  Disposition: NOT-A-BUG
  Evidence: `.github/workflows/python-dependency-submission.yml` uses `component-detection-dependency-submission-action` which auto-detects all pip files in the repo; path triggers only control when the workflow fires, not what it scans. Adding local-only dev profiles to trigger paths would cause unnecessary CI runs.
  Reason: Local-only profile does not need CI dependency submission trigger; auto-detection covers it.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1643#discussion_r3178009662
  Disposition: NOT-A-BUG
  Evidence: `requirements-rag-vector.in` (the GPU sibling) also omits marshmallow. Marshmallow is not a direct or transitive dependency of the RAG/vector stack (sentence-transformers, transformers, torch, pgvector). The CVE floor rule applies to surfaces that actually use marshmallow, not every lockfile in the repo. The `-c requirements.txt` constraint covers shared pins.
  Reason: marshmallow is not a dependency of the RAG/vector stack.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1643#discussion_r3178013507
  Disposition: FIXED
  Commit: 44a03e5a3
  Evidence: requirements-rag-vector-cpu.in:2 — added `--extra-index-url https://download.pytorch.org/whl/cpu` to prefer CPU-only torch wheel resolution

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1643#discussion_r3178013509
  Disposition: FIXED
  Commit: 44a03e5a3
  Evidence: docs/DEPENDENCY_MANAGEMENT.md — `rag-vector-cpu` note moved from CI Install Profiles section to Local CPU profile section (same fix as comment r3178009660)

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1643#pullrequestreview-4216104748
  Disposition: NOT-A-BUG
  Evidence: Sourcery rate-limited — no actionable review content
  Reason: Bot hit weekly rate limit, no review comments generated

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1643#pullrequestreview-4216213282
  Disposition: NOT-A-BUG
  Evidence: CodeRabbit review summary — inline comments addressed individually above
  Reason: Summary review; individual comments mapped separately

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1643#pullrequestreview-4216217185
  Disposition: NOT-A-BUG
  Evidence: Cubic review summary — inline comments addressed individually above
  Reason: Summary review; individual comments mapped separately

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1643#discussion_r3178158472
  Disposition: FIXED
  Commit: 52fcc677f
  Evidence: docs/DEPENDENCY_MANAGEMENT.md:108-113 and requirements-rag-vector-cpu.in:8-12 — corrected wording from "force" to "prefer" and clarified that --extra-index-url adds a secondary index, with the compiled .txt lockfile as the actual deterministic contract

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1643#discussion_r3178169478
  Disposition: FIXED
  Commit: 58117c356
  Evidence: docs/review/PR_1643_FIXED_MAPPING.md:39 — aligned mapping evidence wording from "force" to "prefer" for internal consistency

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1643#pullrequestreview-4216342856
  Disposition: NOT-A-BUG
  Evidence: Cubic re-review summary — inline comments addressed individually above (r3178158472 FIXED in 52fcc677f)
  Reason: Summary review triggered by push; individual inline comments already mapped

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1643#pullrequestreview-4216351027
  Disposition: NOT-A-BUG
  Evidence: CodeRabbit re-review summary — inline comment addressed individually above (r3178169478 FIXED in 58117c356)
  Reason: Summary review triggered by push; individual inline comments already mapped

## Deferred / Follow-ups

- No deferred items.

## Validation

- `pre-commit run --all-files` — PASS
- `make test-fast` — PENDING (docs-only + local-only req files; no runtime impact)

## Merge Readiness

- [ ] CI green
- [ ] review mapping artifact created
- [ ] no actionable bot comments remain
- [ ] mandatory wait-window elapsed
