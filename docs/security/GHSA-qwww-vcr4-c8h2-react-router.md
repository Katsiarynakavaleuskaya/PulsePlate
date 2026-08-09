# GHSA-qwww-vcr4-c8h2 - React Router remediation and suppression removal

## Disposition

- Status: dependency remediation selected; exact suppression removed
- Package: `react-router`
- Base installed version: `7.18.1`
- Selected fixed version: `7.18.2`
- Advisory: <https://github.com/advisories/GHSA-qwww-vcr4-c8h2>
- Scanner snapshot: Docker Build and Push run `31258531222`, security job
  `93106014446`, Trivy analysis `1589834230`

The exact analysis reported `react-router@7.18.1` in
`frontend/package-lock.json`, severity HIGH, with fixed versions `7.18.2` and
`8.3.0`. This batch selects the compatible `7.18.2` line. It does not rely on
the earlier point-in-time RSC non-use rationale, lower severity, or continue
after a scanner failure.

## Material transition

The frontend manifest moves `react-router-dom` from `7.18.1` to `7.18.2`.
Canonical npm resolution moves both installed lock entries to `7.18.2` and
keeps the `react-router-dom` carrier edge aligned. The combined batch owner is
`docs/security/NANOID_REACT_ROUTER_ATOMIC_TRIVY_REMEDIATION_CLASS.md`; this
single-advisory note is subordinate evidence and grants no batching authority.
The permanent tracked-surface guard parses exact npm SemVer rather than PEP 440
for both manifest carriers and installed lock entries, including Node-semver's
raw 256-character maximum and JavaScript-safe numeric-component ceiling. Direct
and lock values are bounded before trimming; npm aliases and tarballs bound the
extracted version token rather than their carrier framing. It rejects affected,
prerelease (including numeric `-0`), unversioned, out-of-bounds, or open-range
`react-router-dom` declarations and any prerelease `react-router` lock entry,
while permitting future exact stable carriers outside the reconciled affected
ranges. Lock identity discovery is origin-neutral so a renamed mirror URL cannot
hide the package; canonical npm-registry provenance, tarball/version equality,
and integrity are validated only after the occurrence is found. Special-scheme
backslashes are normalized before URL parsing to match the relevant WHATWG/Node
path semantics instead of letting a target path disappear into the authority.

The exact suppression was deleted: the former five-predicate Rego rule for
`GHSA-qwww-vcr4-c8h2` and its header reference were removed from
`trivy/ignore-policy.rego`. No replacement,
broader rule, severity exception, allowlist, or scanner bypass was added.
`scripts/ci/check_trivy_ignore_policy_expiry.py` now fails closed if any
supported Rego ignore rule or active `.trivyignore` entry can match this
advisory, while preserving the generic parser, expiry, and review-date checks
for unrelated active rules. `tests/test_trivy_ignore_policy_expiry.py` covers
exact and alternate target-capable Rego shapes, every target of a chained
`with` modifier, an active `.trivyignore` reintroduction, and
unrelated/comment-only negative controls.

Executable evidence is owned by
`scripts/ci/check_trivy_ignore_policy_expiry.py::_ignore_block_can_match_react_router_target`
(`scripts/ci/check_trivy_ignore_policy_expiry.py:355`) and
`scripts/ci/check_trivy_ignore_policy_expiry.py::_validate_react_router_rsc_trivyignore_absent`
for conservative target matching across both active sources, plus
`tests/test_trivy_ignore_policy_expiry.py::test_react_router_rsc_suppression_is_absent_and_guarded_against_reintroduction`
and
`tests/test_trivy_ignore_policy_expiry.py::test_react_router_rsc_trivyignore_reintroduction_fails_closed`
for the exact absence and adversarial reintroduction contracts. The deleted
policy surface remains anchored at `trivy/ignore-policy.rego:1`.

## Bounded claim

The recorded pre-remediation analysis proves the exact base finding. The
dependency and suppression deltas are intended to remove that finding from the
next exact-head Trivy result, but this document does not claim that a future
run has completed, that all repository vulnerabilities are absent, or that the
PR is ready. Current scanner evidence must be assessed independently.

The tracking item is
`docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-react-router-rsc-advisory-monitor`.
Rollback must not restore `7.18.1` or the retired suppression; any dependency
rollback requires a separately safe version and current scanner evidence.
