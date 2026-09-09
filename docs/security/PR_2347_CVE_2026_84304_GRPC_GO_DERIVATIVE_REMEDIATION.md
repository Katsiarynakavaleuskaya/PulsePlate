# PR #2347 CVE-2026-84304 gRPC image remediation

## Summary

This remains the single security evidence owner for PR #2347's bounded
`google.golang.org/grpc` remediation. Caddy selects `v1.83.1`;
Prometheus now selects the immutable official `main-distroless` image whose
two binaries contain `v1.83.2`. No suppression or scanner exception is added.

The operator explicitly revised C3 on 2026-09-08: use the verified official
image through the existing v2 selector and remove the unused, unmerged
derivative implementation. C3-v1 (owned derivative publication) is
**superseded, not achieved**. C3-v2 still requires the current-head gates,
merge and exact-main proof; this document does not claim those later results.

The original pgvector compatibility classifier, terminal main/tag reuse
recheck, staging app/worker/local PostgreSQL DSN binding, Caddy, RubyZip,
review, post-merge and continuity requirements remain unchanged.

## Exact selected subject

Canonical source: `deploy/prometheus/image-manifest.json:1`.

| Field | Observed value |
| --- | --- |
| Repository | `prom/prometheus` |
| Source revision reported by both binaries | `53144df54e01b689bf6c45e811c6230631b132e7` |
| Index digest | `sha256:62464aea89547566d3e26b33566a40d8a9d2ddef947fde9d37454040c9c636b1` |
| Platform | `linux/amd64` |
| Platform manifest digest | `sha256:76f21be0a8e8c825cccb0e2021699dcbfb02037cc594c1f48d44993f8a415f2d` |
| Dynamically verified config digest | `sha256:2868ff918dc719b3dbcabb8585a7c2aa330499df5620a6892ffb146a2fbc727e` |

The runtime reference is the repository plus the platform manifest digest,
not a floating tag or the index digest. The record retains exactly seven v2
fields; config identity remains verified by the existing consumer rather than
adding a schema field. Both registry objects retain the existing Docker
manifest-list/image media types.

The config declares user `65532`, entrypoint `/bin/prometheus`, working
directory `/prometheus`, and the existing configuration/storage arguments.
All three Compose consumers use the same new immutable reference.
Existing index/platform/config, RepoDigest, version, promtool, security and
synthetic-runtime checks remain in `.github/workflows/cd.yml:49`.
The staging and production readers remain fail-closed in
`scripts/deploy.sh:147` and `scripts/deploy_production.sh:441`.

Official means the artifact was observed in the canonical upstream registry
namespace with these immutable bindings. It is not a PulsePlate-owned build,
signed provenance, or independent source-to-binary reproducibility claim.
The embedded revision was also authenticated as a repository-addressable
[upstream commit](https://github.com/prometheus/prometheus/commit/53144df54e01b689bf6c45e811c6230631b132e7);
that addressability does not independently prove the embedded string.

## Applicable finding and scan snapshot

The previous selected platform manifest `sha256:84f0d46e960e86b6965d2e4d99a06f92f176dd75a31ead99126a009891e00f22`
contained gRPC `v1.83.0` in both Prometheus binaries.
[CD run 34224689387](https://github.com/Katsiarynakavaleuskaya/PulsePlate/actions/runs/34224689387/job/102055884345)
reported CVE-2026-84304 as HIGH in both, with fixed version `1.83.1`.
The selected replacement contains `v1.83.2` in both governed occurrences.
Caddy's existing exact module/binary selection remains `v1.83.1` at
`frontend/Dockerfile.caddy-spa:21`.

A fresh Trivy 0.74.0 scan of the replacement completed at
`2026-09-08T13:23:53.580426Z`, exit 0. It used remote-only image access,
a fresh private database, vulnerability and secret scanners, OS/library
package coverage, empty config/ignore inputs, and no Rego suppression.

| Target | Packages with non-empty names and versions | HIGH | CRITICAL | Secrets |
| --- | ---: | ---: | ---: | ---: |
| Debian 13.6 | 6 | 0 | 0 | 0 |
| `usr/bin/prometheus` | 241 | 0 | 0 | 0 |
| `usr/bin/promtool` | 198 | 0 | 0 | 0 |

Both Go targets report main module `3.14.0`, gRPC `v1.83.2`, and
stdlib `v1.27.1`. Package coverage and non-empty name/version fields were
checked across every reported package. Missing coverage is not zero findings.

- Report SHA-256: `e3550cae9a80beaab3737c4b35e0fafa8509521c576585bb2434b0f14d9b8dc7`.
- Database update: `2026-09-08T07:08:01.235696926Z`.
- Database bytes SHA-256: `852bdc39628443d9415c2df73424d36800e7a11421a826cde575c9b464dc9f88`.
- Observed Trivy executable SHA-256: `5fd45afccbd5efd7a88e6da92a7b3a52c2e3ffd30d5b954f324123d6d1d24469`.

These are scoped scanner observations for one immutable subject and database
epoch, not a universal or permanent safety claim. Current-head and exact-main
security gates must scan the selected subject again at their own epochs.

## Bounded executable observations

Network-zero Apple Container probes ran the exact linux/amd64 digest using
Rosetta, UID/GID 65532, read-only root, one CPU and 512 MiB per probe.
Both `/bin/prometheus --version` and `/bin/promtool --version` exited 0:

```text
version 3.14.0 (branch: main, revision: 53144df54e01b689bf6c45e811c6230631b132e7)
go version: go1.27.1
platform: linux/amd64
```

The directory-mounted, byte-identical public configuration passed
`promtool check config --syntax-only`, exit 0:

```text
Checking /etc/prometheus/prometheus.yml
 SUCCESS: /etc/prometheus/prometheus.yml is valid prometheus config file syntax
```

The earlier direct-file mount failed because Apple Container required a
directory mount; its log is retained separately and is not counted as a
successful probe. No real scrape secret, host deployment, production TSDB,
migration or long-running scrape was exercised. Probe containers were removed.

Raw registry objects, the full report/database/checksums and probe outputs
remain sanitized, gitignored local evidence under
`artifacts/security_lab/pr2347-official-prometheus.KlH9mH/` and
`artifacts/security_lab/pr2347-official-version.OBT0Dt/`, with private
receipt files mode 0600. They are not committed or uploaded as raw evidence.

## Retired derivative and preserved authority

The bounded caller census found no surviving shared implementation caller.
This revision deletes only the unmerged derivative Containerfile, controller,
private transport, candidate-only job/inputs, and their exclusive test/doc
consumers. Historical source remains in
[pre-retirement commit e5dc45e](https://github.com/Katsiarynakavaleuskaya/PulsePlate/commit/e5dc45e39be37bd0656df3462cbe1ccc3cf2bf94).
Do not restore its executable publisher as dead shipping code.

[Cloud run 34226292747](https://github.com/Katsiarynakavaleuskaya/PulsePlate/actions/runs/34226292747)
completed historical two-build equality, scan and local admission through
receipt 30. Its candidate was
`sha256:a7bb3eb7ff0f3dcc27a4ca58cee42dc84d1cc1a3501ab54c111e70773385f2e6`.
Receipts 00-30 and earlier failures remain unchanged. Receipts 40-80 and owned
publication never occurred; no publication credential is needed for C3-v2.

`.github/workflows/build.yml:9` preserves the ordinary build/security/publish
chain, disabled manual default, explicit normal-mode admission, PR publication
denial, permissions and same-SHA serialization. The native expression
`inputs.mode == 'normal'` retains GitHub's case-insensitive string comparison;
bounded test fixtures do not implement a general expression evaluator.
[GitHub expression semantics](https://docs.github.com/en/actions/reference/workflows-and-actions/expressions).

No runtime selector update authorizes deployment, public exposure, credential
changes, volume deletion, `T0`, merge, or review-thread disposition.
Unrelated CVE-2026-16742 remains on its existing separate tracked boundary.

## Validation and rollback

Preserve all surviving pgvector, DSN, Caddy, selected-image, CD admission and
failure-propagation tests. New negative topology tests prove that disabled,
missing, empty, retired-candidate and other non-normal manual modes cannot
reach ordinary publication. Full focused, dependency/security, changed-surface
and all-files hooks, fresh Runner/self-review, current-head CI and strict
closeout remain required.

Rollback is an ordinary reviewed revert, never history rewriting or an
automatic host operation. Reverting the image selection would restore the
previous vulnerable subject and cannot be called security recovery. Reassess
the exact image and current findings before any later operational rollback.
