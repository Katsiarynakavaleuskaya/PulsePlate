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

- `frontend/package.json` and `frontend/package-lock.json` resolve the stable
  React Router 7.18.1 line.
- The frontend has no `unstable_matchRSCServerRequest` or
  `unstable_routeRSCServerRequest` use.
- The frontend has no `react-router/internal/react-server` import,
  `@vitejs/plugin-rsc` dependency, `react-server-dom-*` dependency or lockfile
  resolution/alias, or `react-server` build condition.
- `scripts/ci/check_react_router_rsc_premise.py` fails closed if one of those
  affected RSC markers is introduced while the suppression remains. The guard
  recursively inspects package-lock keys and string values and scans every
  source-like file, including test, spec, and story paths that a bundler could
  import. `.github/workflows/ci.yml` invokes it unconditionally from the
  blocking `trivy_ignore_policy_expiry` job.
- `trivy/ignore-policy.rego` matches only the observed GHSA, package, installed
  version, package ID, and fixed version tuple.
- Repository evidence is owned by
  `scripts/ci/check_react_router_rsc_premise.py`,
  `tests/test_check_react_router_rsc_premise.py`,
  `tests/test_trivy_ignore_policy_expiry.py`, and
  `trivy/ignore-policy.rego`.

## Threat and bounded decision

The reported issue can allow an action to execute before a rejected request
returns HTTP 400, but only through the affected unstable RSC request-handling
surface. That surface is absent from PulsePlate today. This disposition does
not claim that React Router 7.18.1 is generally unaffected and does not suppress
any changed scanner record.

Upgrading the application across a major router boundary solely to clear a
non-applicable scanner record would add product migration risk without reducing
the current PulsePlate attack surface. The temporary exact suppression is the
smaller, reversible action.

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
