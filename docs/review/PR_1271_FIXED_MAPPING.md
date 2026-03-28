# PR 1271 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

### Fixed in Commit Mapping
Disposition: FIXED
Commit: de778e4a
Evidence: scripts/deploy_production.sh:7-8, scripts/deploy_production.sh:82-89
Reason: The production deploy script now restores CI-provided `IMAGE_REF` and `TAG` after sourcing `.env`, so repo-local env files cannot silently override the pinned rollout image selected by CI.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1271#pullrequestreview-4026050229 -> de778e4a
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1271#discussion_r3005351120 -> de778e4a

Disposition: FIXED
Commit: de778e4a
Evidence: scripts/ops/postgres_backup.sh:11-12, scripts/ops/postgres_restore.sh:15-16, tests/test_deploy_contract_scripts.py:15-23, tests/test_deploy_contract_scripts.py:197-229
Reason: The Postgres helpers now fail fast when `POSTGRES_USER` or `POSTGRES_DB` is missing, and the deploy-contract test now reports missing log steps with explicit assertions instead of a bare `StopIteration`.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1271#pullrequestreview-4026047834 -> de778e4a
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1271#discussion_r3005349493 -> de778e4a

Disposition: FIXED
Commit: de778e4a
Evidence: scripts/QUICK_FIX_PRODUCTION.sh:55, scripts/QUICK_FIX_PRODUCTION.sh:165-170, scripts/PRODUCTION_ENV_FIX.md:58-59, docs/deploy/PRODUCTION.md:450-468
Reason: The quick-fix script now counts duplicate keys safely, resolves the readiness domain from `PRODUCTION_DOMAIN`, handles `jq` availability explicitly, and the production docs now use absolute backup/restore helper paths.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1271#pullrequestreview-4026053309 -> de778e4a
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1271#discussion_r3005353298 -> de778e4a
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1271#discussion_r3005353303 -> de778e4a
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1271#discussion_r3005353306 -> de778e4a
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1271#discussion_r3005353309 -> de778e4a

Disposition: FIXED
Commit: 1d03adc8
Evidence: scripts/PRODUCTION_ENV_FIX.md:24, scripts/PRODUCTION_ENV_FIX.md:42, scripts/PRODUCTION_ENV_FIX.md:81
Reason: The production env runbook now treats `API_KEY_REQUIRED` as a compatibility request-time flag instead of describing it as a startup fail-closed production guard, matching the current runtime contract.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1271#pullrequestreview-4026074209 -> 1d03adc8
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1271#discussion_r3005374426 -> 1d03adc8

Disposition: NOT-A-BUG
Evidence: app/AGENTS.md:27-36, docs/deploy/PRODUCTION.md:222, deploy/docker-compose.production.yaml:51, deploy/docker-compose.staging.yaml:49
Reason: The repository health-endpoint contract explicitly reserves `/health` for liveness and `/ready` for dependency-aware readiness, and it states that orchestrators such as Docker and Caddy should use `/ready` for traffic gating. CodeRabbit's `/health` suggestion conflicts with that source-of-truth contract; the separate `API_KEY_REQUIRED` doc wording comment was fixed in `1d03adc8`.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1271#pullrequestreview-4026052294

## Merge Readiness
- [x] Local hard gate passed (`make verify`)
- [ ] Required checks PASS with no pending required jobs
- [ ] No unresolved review threads
- [ ] No actionable bot comments
- [ ] Final post-bot wait cycle completed

## Post-open QA Evidence
- Mandatory post-open lane completed on `28 марта 2026 года`:
  `qa-engineer-agent (Linnaeus) -> bug-hunter (Faraday)`.
- Internal post-open fixes shipped in commit `0a3dc812`.
- Evidence surface:
  `scripts/ops/postgres_backup.sh`, `scripts/ops/postgres_restore.sh`,
  `scripts/deploy.sh`, `scripts/deploy_production.sh`,
  `docs/deploy/PRODUCTION.md`, `tests/test_deploy_contract_scripts.py`.
