# PR 1229 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

### Batch A — direct root probe + Codex P1 relocation
Disposition: FIXED
Commit: d0e43d20
Evidence: `app/main.py:125`, `app/bootstrap/direct_api_root.py:28`, `tests/test_direct_api_root_probe.py:21`, `tests/test_spanish_end_to_end_smoke.py:103`, `tests/test_app_basic_combined.py:88`, `docs/deploy/SPA_APEX_ROUTING_CONTRACT.md:46`

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1229#discussion_r2972124555
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1229#discussion_r2972124557
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1229#discussion_r2972124559
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1229#discussion_r2972129621

### Batch B — route endpoint identity, legacy HTML CSP/fetch, test contract, ledger
Disposition: FIXED
Commit: de54e75f
Evidence: `app/main.py:68`, `app/main.py:148`, `app/bootstrap/legacy_bmi_web_html.py:20`, `app/bootstrap/legacy_bmi_web_html.py:198`, `app/bootstrap/legacy_bmi_web_html.py:260`, `tests/test_direct_api_root_probe.py`, `tests/test_legacy_bmi_web_html_guard.py`, `docs/roadmap/BACKLOG_LEDGER.md`

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1229#discussion_r2972135430
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1229#discussion_r2972140766
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1229#discussion_r2972140768
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1229#discussion_r2972145442

## Merge Readiness
- [ ] All required checks pass
- [ ] No unresolved review threads (resolve on GitHub after push)
- [x] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
- [ ] Pre-commit green
