# GHSA-qwww-vcr4-c8h2 - React Router unstable RSC APIs

## Disposition

- Status: temporarily suppressed under a bounded, point-in-time risk decision
- Package: `react-router`
- Installed version: `7.18.1`
- Trivy fixed version: `8.3.0`
- Advisory: https://github.com/advisories/GHSA-qwww-vcr4-c8h2
- Review-by: 2026-08-24

The advisory affects React Router's unstable React Server Components (RSC)
server APIs. Current PulsePlate repository evidence shows the stable
declarative `react-router-dom` SPA surface and no intentional use of those
server APIs. The exact Trivy record is temporarily suppressed instead of taking
an unrelated major-version migration.

## Applicability evidence

- `frontend/package.json:47` pins `react-router-dom` to 7.18.1, while
  `frontend/package-lock.json:9168`, `frontend/package-lock.json:9169`,
  `frontend/package-lock.json:9191`, and `frontend/package-lock.json:9196`
  resolve both router packages to that exact line.
- A point-in-time repository review on 2026-07-27 found no
  `unstable_matchRSCServerRequest` or `unstable_routeRSCServerRequest` use,
  `react-router/internal/react-server` import, `@vitejs/plugin-rsc` dependency,
  `react-server-dom-*` dependency, or intentional `react-server` build
  condition in the current frontend surface.
- `trivy/ignore-policy.rego:212` begins the exact suppression rule, whose five
  tuple predicates occupy `trivy/ignore-policy.rego:213` through
  `trivy/ignore-policy.rego:217`.
- `scripts/ci/check_trivy_ignore_policy_expiry.py` enforces the exact five-field
  tuple, rejects duplicate, broader, malformed, or alternate-head ignore rules,
  and enforces the suppression expiry and review dates.
- `tests/test_trivy_ignore_policy_expiry.py` covers the exact tuple, lexical
  Rego structure, comments, quoted/raw-string decoys, expiry, review dates, and
  stable read failures.

This point-in-time repository evidence is not
a complete source-applicability proof. There is no claim that a finite marker
inventory can prove every present or future RSC usage shape; the evidence must
be refreshed during the weekly review and whenever the frontend dependency or
execution model changes.

## Threat and bounded decision

The reported issue can allow an action to execute before a rejected request
returns HTTP 400, but only through the affected unstable RSC request-handling
surface. That surface was not found in the point-in-time evidence above. This
disposition does not claim that React Router 7.18.1 is generally unaffected,
that the dependency is vulnerability-free, that all possible source forms were
proven safe, or that an applicability scanner passed.

Upgrading the application across a major router boundary solely to clear a
scanner record whose triggering surface was not found in the point-in-time
evidence would add product migration risk without reducing the observed
PulsePlate attack surface. The temporary exact suppression is the smaller,
reversible action.

## Monitor and removal

Owner: `@katsiaryna_kavaleuskaya`

Review the GitHub advisory and Dependabot alert #241 weekly. Remove the
suppression immediately when any of these conditions is true:

1. Current or future review finds an affected unstable RSC API, internal RSC
   server import, RSC Vite plugin, React Server DOM package, or `react-server`
   build condition.
2. The installed React Router line moves away from 7.18.1.
3. Trivy changes any field in the suppressed finding tuple.
4. A compatible non-affected dependency line is approved and validated.

The canonical tracking item is
`docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-react-router-rsc-advisory-monitor`.
Rollback is removal of the single Rego rule; no runtime code or dependency
state is changed by this disposition.
