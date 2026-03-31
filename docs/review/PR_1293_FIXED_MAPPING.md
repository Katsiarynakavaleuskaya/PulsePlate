# PR 1293 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

Disposition: FIXED
Commit: 104fb8ef
Evidence: scripts/redeploy_caddy.sh, docs/review/PR_1293_FIXED_MAPPING.md
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1293#discussion_r3018067514 -> 104fb8ef
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1293#discussion_r3018083269 -> 104fb8ef

Disposition: FIXED
Commit: a90c3d38
Evidence: scripts/diagnose_web.sh, scripts/redeploy_caddy.sh, docs/roadmap/DEPLOY_WEB_DIAGNOSIS_AND_FIX.md, tests/test_deploy_contract_scripts.py
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1293#discussion_r3018067523 -> a90c3d38

Disposition: FIXED
Commit: e0c21998
Evidence: scripts/diagnose_web.sh, docs/deploy/SPA_APEX_ROUTING_CONTRACT.md, tests/test_deploy_contract_scripts.py
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1293#discussion_r3018061433 -> e0c21998
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1293#discussion_r3018061438 -> e0c21998
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1293#discussion_r3018083267 -> e0c21998
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1293#discussion_r3018169451 -> e0c21998

Disposition: NOT-A-BUG
Evidence: docs/review/PR_1293_FIXED_MAPPING.md
Reason: These bot review summary URLs aggregate actionable child comments that are individually dispositioned in this artifact; the summary shells do not require separate code changes.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1293#pullrequestreview-4039790421
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1293#pullrequestreview-4039796943
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1293#pullrequestreview-4039815684
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1293#pullrequestreview-4039829187
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1293#pullrequestreview-4039911668

## Merge Readiness
- [ ] All required checks pass
- [ ] No unresolved review threads (re-check on current head before merge)
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
- [x] Pre-commit green
- [x] `make verify` green
- PR-2 lane: restore deterministic SPA shell diagnosis, preserve the baked `/srv/frontend` contract, and keep legacy/API surfaces off SPA fallback.
