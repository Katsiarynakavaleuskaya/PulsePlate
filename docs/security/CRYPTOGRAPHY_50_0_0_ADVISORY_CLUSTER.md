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

## Dependency-remediation admission v1

Evidence is closed over reachable base history
`643eb78d01476835523a3e800f1e88cb36f0aa8f`, the current tracked worktree
`S_head`, and reconciliation cutoff `2026-08-04T10:18:11Z`; it is not an
open-world or future-safety claim. The deterministic guard loads only the base
from Git history, then mechanically enumerates the current tracked worktree as
`S_head`: four `.in` manifests, `constraints.txt`, and five generated locks.
It fails closed unless that base is an ancestor of current `HEAD`.
At the base every occurrence was `cryptography==48.0.1` (or the corresponding
`>=48.0.1,<49.0.0` source floor); current `S_head` requires the 50.0.0 floor/pin.

`F_cutoff` contains exactly these OSV records keyed by their GHSA aliases,
frozen at their published timestamps and first-patched versions. The exact OSV
GET inputs were `https://api.osv.dev/v1/vulns/GHSA-m2h6-j472-rp4c`,
`https://api.osv.dev/v1/vulns/GHSA-g6cj-pr64-35w5`, and
`https://api.osv.dev/v1/vulns/GHSA-jwv3-5hgf-82ww`, evaluated at the recorded
cutoff:

| Advisory record | Published / OSV modified (UTC) | OSV affected range | First patched | Base applicability | Universal head safety | pip-audit receipt |
|---|---|---|---|---|---|---|
| GHSA-m2h6-j472-rp4c / CVE-2026-69248 / medium | 2026-08-03T21:26:57Z / 2026-08-03T21:30:27.883493382Z | `>=0,<49.0.0` | `49.0.0` | applicable: all ten base witnesses are 48.0.1 | 50.0.0 is outside range | exact-base pip-audit exits 1 and reports this advisory |
| GHSA-g6cj-pr64-35w5 / CVE-2026-69247 / high | 2026-08-03T21:17:00Z / 2026-08-03T21:30:27.876121715Z | `>=44.0.0,<50.0.0` | `50.0.0` | applicable: all ten base witnesses are 48.0.1 | 50.0.0 is outside range | exact-base pip-audit exits 1 and reports this advisory |
| GHSA-jwv3-5hgf-82ww / CVE-2026-69249 / high | 2026-08-03T21:26:50Z / 2026-08-03T21:30:27.873716043Z | `>=0,<49.0.0` | `49.0.0` | applicable: all ten base witnesses are 48.0.1 | 50.0.0 is outside range | exact-base pip-audit exits 1 and reports this advisory |

OSV is the applicability authority because pip-audit consumes its records: at
the exact base it exits 1 with `Found 3 known vulnerabilities in 1 package`
and identifies `cryptography==48.0.1` for all three aliases. Direct GitHub
Advisory REST was queried in the same pass, but its `<=48.0.0` projection for
the m2h6 and jwv3 records conflicts with the OSV ranges. GitHub REST remains
recorded secondary metadata and grants no narrowing authority.

Thus `F_cutoff=A={GHSA-m2h6-j472-rp4c, GHSA-g6cj-pr64-35w5,
GHSA-jwv3-5hgf-82ww}`: every member is derived from exact affected 48.0.1 base
witnesses, not advisory severity or a broad label. Universal predicate `P`
requires every head occurrence to be at least 50.0.0 and outside every
`F_cutoff` OSV affected range. The non-empty intent set is exactly `I_R={requirements.in,
requirements-docker-runtime.in, requirements-ci-lite.in, requirements-dev.in,
constraints.txt}`; the replay-consistent compiled set is exactly
`C_R={requirements.txt, requirements-docker-runtime.txt,
requirements-ci-lite.txt, requirements-dev.txt, requirements-lock.txt}`.
The unchanged `setuptools==83.0.0` relocation in two locks is a non-semantic
representation movement, not independent intent. The guard fails closed if a
surface or advisory is omitted, a head witness is unsafe, or a material
transition is unclassified or cannot be replayed from its base witness.

The serialized replay applied only `I_R` edits in a temporary clone, first with
`LOCK_PROFILES="runtime" UPGRADE_PACKAGES="cryptography==50.0.0" make requirements-locks`,
then, after committing that replay intermediate, with
`LOCK_PROFILES="docker-runtime ci-lite dev aggregate" UPGRADE_PACKAGES="cryptography==50.0.0" make requirements-locks`,
using the same approved proxy. Historical replay receipt metadata was recorded
at `5383a5bfe5c81eb5b9f07699dd67983d09118882`; executable admission does not
request that object. Instead it binds the current five `C_R` lock contents
directly to these byte-identical SHA-256 receipts:

```text
requirements.txt                 8d7e5b6f9e15344ca031060407e6928a57ee82e2a1fdcaaed5f3137de1a61def
requirements-docker-runtime.txt  3b263517b8193dda2b57bbea62fbbcf6237dd2b35ca3be7f897d380aa0413467
requirements-ci-lite.txt         cf7187511aa6c588f74b9d27a1f64c66756bd395a64954ff9c1bb3e4c4641f7d
requirements-dev.txt             a8414bd336b64ef7e1f6eec0286eb8086f3b6ffbcffe966d7d2972335f744b09
requirements-lock.txt            8dbd199fb77e532079af840d3ebf2ff91dd4a5d1ce08d20b950cc83f725ec0b4
```

The historical replay identifier is documentary receipt metadata only. The
separate live `REQUIREMENT_SURFACES` floor guard continues to enforce
`>=50.0.0` on current main and may evolve with later unrelated dependency
rotations.

Base inventory uses Git history through the guard's `git ls-tree` and `git show`
operations. Current `S_head` inventory uses `git ls-files` plus direct reads of
tracked worktree requirement surfaces. Both inventories reconcile to the same
ten governed surfaces. The exact-head
`pip-audit -r requirements.txt --no-deps --disable-pip -f json` exits 0 with
`No known vulnerabilities found` and `cryptography==50.0.0` `vulns: []`.
These finite command receipts bind the current transition only and do not make
an all-future safety claim.

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
