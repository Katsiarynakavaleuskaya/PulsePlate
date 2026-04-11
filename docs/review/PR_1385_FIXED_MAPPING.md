# PR #1385 — Fixed in Commit Mapping (SoT)

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

Bot and human review threads must be dispositioned below when actionable comments appear; resolve conversations on GitHub only after mapping per `AGENTS.md`.

## Fixed in Commit Mapping

Disposition: FIXED
Commit: ea218498c
Evidence: `scripts/deploy_production.sh` (autodetected compose bundle sync), `scripts/diagnose_web.sh` (404 admin-canary hard fail), `deploy/WORKFLOW.md` (production scripts path), `tests/test_app_endpoints_combined.py` (deterministic sitemap assertions + public_discovery coverage), `tests/test_deploy_contract_scripts.py`
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1385#pullrequestreview-4092727607 -> ea218498c
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1385#discussion_r3066824729 -> ea218498c
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1385#discussion_r3066957607 -> ea218498c
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1385#discussion_r3066979098 -> ea218498c
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1385#discussion_r3066967048 -> ea218498c
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1385#discussion_r3066967058 -> ea218498c
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1385#discussion_r3066967065 -> ea218498c
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1385#discussion_r3066979107 -> ea218498c

Disposition: FIXED
Commit: 8862ba28b
Evidence: `docs/deploy/SPA_APEX_ROUTING_CONTRACT.md` (temporary reopen contract keeps `/health*` and `/ready` edge-protected), final closure of cubic review `pullrequestreview-4092738799` after earlier inline recovery fixes landed in `ea218498c`
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1385#pullrequestreview-4092738799 -> 8862ba28b
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1385#discussion_r3066979099 -> 8862ba28b

Disposition: FIXED
Commit: 556655280
Evidence: `scripts/deploy_production.sh` (shell-bundle compose sync preserves the actual compose target path), `tests/test_deploy_contract_scripts.py` (`COMPOSE_FILE=deploy/...` regression coverage)
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1385#discussion_r3067165839 -> 556655280

Disposition: FIXED
Commit: a062111c6
Evidence: `scripts/deploy_production.sh` (autodetects canonical `deploy/docker-compose.production.yaml` + `deploy/.env`, rejects compose sync targets outside `DEPLOY_DIR`), `tests/test_deploy_contract_scripts.py`
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1385#pullrequestreview-4092928735 -> a062111c6
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1385#pullrequestreview-4092938795 -> a062111c6
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1385#pullrequestreview-4092941266 -> a062111c6
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1385#discussion_r3067175262 -> a062111c6
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1385#discussion_r3067185585 -> a062111c6
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1385#discussion_r3067187995 -> a062111c6

Disposition: FIXED
Commit: 63b775fd6
Evidence: `scripts/deploy_production.sh` (default `ENV_FILE` selection now handles absolute `COMPOSE_FILE` paths under `$DEPLOY_DIR/deploy/*`), `tests/test_deploy_contract_scripts.py` (absolute deploy compose regression coverage, valid JSON curl stub payload)
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1385#pullrequestreview-4093040042 -> 63b775fd6
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1385#pullrequestreview-4093041205 -> 63b775fd6
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1385#discussion_r3067290930 -> 63b775fd6
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1385#discussion_r3067292082 -> 63b775fd6

Disposition: FIXED
Commit: 327f5d4a0
Evidence: `scripts/deploy_production.sh` now fails fast when `RESOLVED_COMPOSE_FILE` points to a missing file, `tests/test_deploy_contract_scripts.py` locks the preflight contract, and this commit is the final closure for CodeRabbit review `pullrequestreview-4092919899`
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1385#pullrequestreview-4092919899 -> 327f5d4a0

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1385#discussion_r3067307203
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1385#pullrequestreview-4093057434
Disposition: NOT-A-BUG
Evidence: `tests/test_deploy_contract_scripts.py:1268`, `tests/test_deploy_contract_scripts.py:1310`
Reason: `curl_stub` is a plain triple-quoted string, not an f-string, so the JSON braces in `payload='{\"ok\": true}'` are literal shell-script content and do not require `{{ ... }}` escaping.

## Merge Readiness

- [ ] Current-head CI green for PR branch head
- [ ] Required checks complete (no pending jobs)
- [ ] All review threads resolved on GitHub after disposition updates
- [x] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`

### Scope Notes

- This PR keeps the recovery lane scoped to private-first apex recovery, backend-owned `/sitemap.xml`, Access-aware diagnostics, and public reopen documentation.
- Cloudflare Access API surfaces are available from the current token, but zone firewall/settings endpoints return `9109 Unauthorized`, so narrow temporary bypass automation remains an ops/dashboard step unless token scope is expanded.
- Public scanner truth (MDN Observatory / external header scans) remains out of release-truth while full-host Access or Cloudflare interstitials are active.

### Local Verification

- `python3 scripts/orchestration/check_preflight.py`
- `python3 scripts/orchestration/check_agent_consistency.py`
- `pytest -q tests/test_app_endpoints_combined.py tests/test_deploy_contract_scripts.py`
- `pre-commit run --all-files`
- `make verify`

## Deferred / Follow-ups

- `docs/roadmap/BACKLOG_LEDGER.md#ledger-p2-cloudflare-narrow-reopen-automation` — automate the documented narrow temporary reopen bypass once Cloudflare zone firewall/ruleset permissions are available.
