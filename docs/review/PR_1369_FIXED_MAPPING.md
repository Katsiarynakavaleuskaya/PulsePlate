# PR #1369 — Fixed in Commit Mapping (SoT)

## Discussion Thread Pass

- No GitHub review threads at artifact creation time. Re-run disposition mapping when bots or humans add actionables.

## Fixed in Commit Mapping

_(No threads yet — add \`- <thread_url> -> <sha>\` rows only after explicit disposition per AGENTS.md.)_

## Merge Readiness

- [ ] Current-head CI green for PR branch head
- [ ] Required checks complete (no pending jobs)
- [ ] Any new review threads dispositioned below

### Local / design verification

- Branch head: `ab392be0c` (ADR SoT + smoke comments + mapping scaffold)
- Evidence: `docs/architecture/ADR_DOCKER_BUILD_PROVENANCE_WORKAROUND_2026-03-01.md` (updated Context, Decision, Evidence Anchors)
- Evidence: `.github/workflows/docker-openapi-smoke.yml:75`-`78` (load vs attestations rationale)
