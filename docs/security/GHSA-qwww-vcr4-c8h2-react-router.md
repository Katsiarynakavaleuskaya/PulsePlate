# GHSA-qwww-vcr4-c8h2 - React Router unstable RSC APIs

## Disposition

- Status: temporarily not applicable to the PulsePlate runtime
- Package: `react-router`
- Installed version: `7.18.1`
- Trivy fixed version: `8.3.0`
- Advisory: https://github.com/advisories/GHSA-qwww-vcr4-c8h2
- Review-by: 2026-08-24

The advisory affects React Router's unstable React Server Components (RSC)
server APIs. PulsePlate uses the stable declarative `react-router-dom` SPA
surface and does not enable those server APIs. The exact Trivy record is
temporarily suppressed instead of taking an unrelated major-version migration.

## Applicability evidence

- `frontend/package.json:47` pins `react-router-dom` to 7.18.1, while
  `frontend/package-lock.json:9168`, `frontend/package-lock.json:9169`,
  `frontend/package-lock.json:9191`, and `frontend/package-lock.json:9196`
  resolve both router packages to that exact line.
- The frontend has no `unstable_matchRSCServerRequest` or
  `unstable_routeRSCServerRequest` use. The canonical marker inventory is at
  `scripts/ci/check_react_router_rsc_premise.py:44`, and the current repository
  absence proof is asserted at `tests/test_trivy_ignore_policy_expiry.py:642`.
- The frontend has no `react-router/internal/react-server` import,
  `@vitejs/plugin-rsc` dependency, `react-server-dom-*` dependency or lockfile
  resolution/alias, or `react-server` build condition. The token-bounded build
  condition matcher is at `scripts/ci/check_react_router_rsc_premise.py:50`.
- `scripts/ci/check_react_router_rsc_premise.py:244` scans package metadata,
  and `scripts/ci/check_react_router_rsc_premise.py:709` combines that scan with
  every source-like file. It fails closed when an affected marker is introduced;
  metadata and runtime regressions are covered at
  `tests/test_trivy_ignore_policy_expiry.py:645` and
  `tests/test_trivy_ignore_policy_expiry.py:705`.
- `scripts/ci/check_trivy_ignore_policy_expiry.py:444` detects any suppression
  capable of matching the canonical tuple, and
  `scripts/ci/check_trivy_ignore_policy_expiry.py:446` invokes
  the premise guard. The existing blocking `trivy_ignore_policy_expiry` CI job
  therefore enforces expiry and the complete premise scan together.
- `trivy/ignore-policy.rego:212` begins the exact suppression rule, whose five
  tuple predicates occupy `trivy/ignore-policy.rego:213` through
  `trivy/ignore-policy.rego:217`. The guard's canonical predicate tuple is
  defined at `scripts/ci/check_trivy_ignore_policy_expiry.py:26` and compared
  exactly at `scripts/ci/check_trivy_ignore_policy_expiry.py:262`.
- Exact-tuple and fail-closed wrapper regressions are at
  `tests/test_trivy_ignore_policy_expiry.py:1519` and
  `tests/test_trivy_ignore_policy_expiry.py:1915`.

## Threat and bounded decision

The reported issue can allow an action to execute before a rejected request
returns HTTP 400, but only through the affected unstable RSC request-handling
surface. That surface is absent from PulsePlate today. This disposition does
not claim that React Router 7.18.1 is generally unaffected, that the dependency
is vulnerability-free, or that a scanner passed.

Upgrading the application across a major router boundary solely to clear a
currently non-applicable scanner record would add product migration risk
without reducing the current PulsePlate attack surface. The temporary exact
suppression is the smaller, reversible action.

## Monitor and removal

Owner: `@katsiaryna_kavaleuskaya`

Review the GitHub advisory and Dependabot alert #241 weekly. Remove the
suppression immediately when any of these conditions is true:

1. PulsePlate adopts an affected unstable RSC API, internal RSC server import,
   RSC Vite plugin, React Server DOM package, or `react-server` build condition.
2. The installed React Router line moves away from 7.18.1.
3. Trivy changes any field in the suppressed finding tuple.
4. A compatible non-affected dependency line is approved and validated.

The canonical tracking item is
`docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-react-router-rsc-advisory-monitor`.
Rollback is removal of the single Rego rule; no runtime code or dependency
state is changed by this disposition.
