# `cryptography` 50.0.0 advisory-cluster security floor

## Status

PulsePlate requires `cryptography>=50.0.0,<51.0.0` on every canonical shared
source surface and pins `cryptography==50.0.0` in every corresponding lock.
Version 50.0.0 is the lowest common release that clears the three advisories in
this bounded cluster. It is not a claim that 50.0.0 is permanently safe from
future advisories.

Current repository evidence is `requirements.in:43`, `requirements.txt:39`,
and `tests/fixtures/dependency_security_schema.json:4`.

## Advisory cluster

| Advisory | Affected versions | First patched version | Bounded impact summary |
|---|---:|---:|---|
| [GHSA-m2h6-j472-rp4c](https://github.com/advisories/GHSA-m2h6-j472-rp4c) | `<=48.0.0` | `49.0.0` | Wildcard DNS certificate verification can escape a permitted name subtree. |
| [GHSA-g6cj-pr64-35w5](https://github.com/advisories/GHSA-g6cj-pr64-35w5) | `>=44.0.0,<50.0.0` | `50.0.0` | PKCS#7 EnvelopedData decryption can expose a Bleichenbacher oracle through distinguishable failures and timing. |
| [GHSA-jwv3-5hgf-82ww](https://github.com/advisories/GHSA-jwv3-5hgf-82ww) | `<=48.0.0` | `49.0.0` | Duplicate self-signed intermediates can cause exponential certificate path-building and resource exhaustion. |

The two certificate-verification findings clear at 49.0.0. The PKCS#7 finding
does not clear until 50.0.0, so 50.0.0 is the common clearing floor for this
cluster.

## Reachability context

The finite tracked-Python scan on the remediation base found direct production
imports only for:

- Fernet in `secure_config.py:16` and `app/security/web_session.py:20`;
- AES-GCM through `AESGCM` in `app/telemetry/vault.py:16`.

No tracked production Python call site directly imported the affected PKCS#7
decrypt helpers or `cryptography.x509.verification` APIs in this scan. This
reduces apparent direct reachability for the reported entry points, but it does
not waive the update: the canonical dependency-security floor is
dependency-wide, future call sites must inherit it, and a reachability snapshot
is not proof that every transitive or native path is unreachable.

## Approved-index and lock evidence

On 2026-08-04 the governed lock compiler resolved the exact upgrade through
only the approved PulsePlate proxy:

```text
PULSEPLATE_PYTHON_INDEX_URL=https://packages.pulseplate.app/root/pulseplate/+simple/
UPGRADE_PACKAGES=cryptography==50.0.0
```

The runtime profile was compiled first. Docker-runtime, CI-lite, dev, and
aggregate profiles were then compiled in one ordered batch. All five locks pin
exactly `cryptography==50.0.0`. The resolver changed no other package version or
dependency graph node. Current pip-tools output only relocated the unchanged
`setuptools==83.0.0` line from the legacy unsafe footer into the normal sorted
block in runtime and Docker-runtime locks.

No public index, extra index, find-links source, emergency wheel, waiver,
ignore, or audit suppression was used. The retired emergency manifest remains
an empty compatibility marker and is not modified by this lane.

## Platform artifact and runtime evidence

The [upstream 49.0.0 changelog](https://cryptography.io/en/stable/changelog/#v49-0-0)
records that upstream removed `x86_64` macOS support and now publishes only
arm64 macOS wheels. In the bounded approved proxy observation on 2026-08-04,
the `cryptography==50.0.0` project page advertised 46 exact artifacts. Its macOS
artifacts were macOS arm64 only; it advertised no macOS `x86_64` or `universal2`
wheel.

In a separate isolated Apple Silicon environment, exact 50.0.0 was installed
from the approved proxy. The import check and Fernet/AESGCM smoke checks passed,
followed by all 133 consumer tests selected for the three direct production
carriers at `secure_config.py:16`, `app/security/web_session.py:20`, and
`app/telemetry/vault.py:16`.

For developers, the devcontainer remains recommended for
backend/web/docs/orchestration work. A host `.venv` is supported only when the
approved proxy supplies a compatible binary wheel. Apple Silicon exact-50 was
validated; Intel macOS backend bootstrap must use the devcontainer at this
floor. iOS/Xcode development stays host-native. The installer enforces the
binary-only boundary at
`scripts/ci/install_locked_python_requirements.py:998` and
`scripts/ci/install_locked_python_requirements.py:1066`; source-build fallback
is not supported.

This dated arm64 result does not prove Intel macOS compatibility, future wheel
availability, every platform/runtime combination, or any open-world
compatibility claim.

## Finite claim

This remediation claims completeness only for:

- the three GHSA records and patched-version facts listed above;
- the four canonical shared source manifests, `constraints.txt`, and five
  generated shared locks named by the dependency-security guard;
- the direct tracked-Python Fernet/AESGCM reachability scan described above;
- the approved-proxy and deterministic validation commands recorded for this
  change.

It does not claim open-world recognition of future vulnerabilities, all native
backend behavior, every downstream consumer, or permanent safety of release
50.0.0.

## Validation

- `tests/test_dependency_security_guard.py` proves all ten canonical surfaces
  enforce 50.0.0 and explicitly rejects a complete former-48.0.1 surface.
- The approved-proxy preflight must serve every enforced floor without public
  fallback or an emergency artifact.
- Real Fernet and AESGCM consumer tests cover web sessions, secure config, and
  the telemetry vault.
- Canonical manifest audit and lock-delta checks must show no vulnerable pin or
  unrelated dependency graph change.

## Rollback

The mechanical repository rollback is a revert of this change; there is no data
migration. A revert does not make 48.0.1 safe and must keep release/deployment
blocked until a separately reviewed patched replacement is available. Do not
silently repin below 50.0.0 as an operational rollback.

## Prohibited shortcuts

- No public PyPI fallback, `--extra-index-url`, or unrestricted `--find-links`.
- No emergency-wheel reactivation or new emergency manifest entry.
- No Safety, pip-audit, Dependabot, Trivy, or GHSA ignore/waiver/suppression.
- No repin below 50.0.0 to restore CI.
- No unrelated dependency upgrade or graph migration.
- No claim that low current reachability waives the dependency update.
