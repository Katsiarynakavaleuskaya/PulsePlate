# PR #1385 — Fixed in Commit Mapping (SoT)

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

Bot and human review threads must be dispositioned below when actionable comments appear; resolve conversations on GitHub only after mapping per `AGENTS.md`.

## Fixed in Commit Mapping

- No actionable review comments

## Merge Readiness

- [ ] Current-head CI green for PR branch head
- [ ] Required checks complete (no pending jobs)
- [ ] All review threads resolved on GitHub after disposition updates
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`

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

- If Cloudflare token scope is later expanded to zone firewall/ruleset management, automate the narrow temporary reopen bypass as a separate ops lane instead of widening the current Access-only contract.
