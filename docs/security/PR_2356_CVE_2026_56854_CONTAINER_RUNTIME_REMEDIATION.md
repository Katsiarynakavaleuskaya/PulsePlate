# PR #2356: CVE-2026-56854 container-runtime dependency remediation

## Decision and authority boundary

The operator explicitly authorized the existing PR
[#2356](https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2356) to widen
only far enough to repair its required Caddy scan after the same PR had already
replaced the affected Prometheus carrier. This is the direct external authority
for one Go-module identity, `golang.org/x/crypto`, and one reconciled advisory,
[GO-2026-6303 / CVE-2026-56854](https://pkg.go.dev/vuln/GO-2026-6303), across
the three affected container-binary occurrences enumerated below.

That instruction does not authorize another dependency identity, advisory,
ecosystem, suppression, waiver, floating image, broad Go-module refresh, Caddy
module redesign, deployment, or future batch. Candidate code, tests, this
document, scanners, agents, and the PR body cannot create or widen that
authority. The remediation remains fail-closed on the existing suppression-free
current-head image scans.

The operator also directed the completed backlog outcome to remain in this
implementation PR rather than a later docs-only carrier. The checked Caddy
ledger item therefore describes the intended merged result and states that it
becomes current-main truth only when PR #2356 merges; it is not a claim that the
open PR is already merged or ready.

Status: the Prometheus image replacement is present in the PR. The Caddy
resolver replay and the local exact linux/amd64 Apple Container final-image
build, runtime checks, and scoped Trivy scan below pass on the candidate diff.
Current-head GitHub build/scan, complete PR CI, review, and merge-readiness
proof are still required. This document therefore records a transition decision
and bounded local evidence; it does not claim that the PR is green or ready.

## Exact base failure evidence

The finite evidence cutoff for this identity is
`PR2356-GO-2026-6303-2026-09-01`. Its advisory inventory is exactly:

- `F_cutoff = {GO-2026-6303 / CVE-2026-56854}`;
- the fixed module version reported by the Go vulnerability record and the
  Trivy findings is `golang.org/x/crypto v0.55.0`;
- no second advisory or dependency identity is admitted by this owner.

The base-applicable inventory is non-empty. The raw failing CI evidence is:

- Caddy: run
  [33441869876](https://github.com/Katsiarynakavaleuskaya/PulsePlate/actions/runs/33441869876),
  job
  [99651961031](https://github.com/Katsiarynakavaleuskaya/PulsePlate/actions/runs/33441869876/job/99651961031),
  reported `usr/bin/caddy`, `golang.org/x/crypto`, installed `v0.53.0`,
  fixed `0.55.0`, `CVE-2026-56854`, `CRITICAL`;
- Prometheus: run
  [33430879253](https://github.com/Katsiarynakavaleuskaya/PulsePlate/actions/runs/33430879253),
  job
  [99615659984](https://github.com/Katsiarynakavaleuskaya/PulsePlate/actions/runs/33430879253/job/99615659984),
  reported the same `CRITICAL` advisory for both `usr/bin/prometheus` and
  `usr/bin/promtool`, each with installed `v0.54.0` and fixed `0.55.0`.

Those rows prove affected comparable base occurrences. They do not prove that
every call path reaches the vulnerable SSH routine, and exploitability is not
needed to satisfy the repository's suppression-free image gate.

## D / S / A / R / P reconciliation

### D — dependency identity

`D` is the ecosystem-qualified Go-module identity
`go:golang.org/x/crypto`. Aliases, packages with similar names, the Go standard
library, and the resolver-induced `golang.org/x/*` neighbors are not additional
authored dependency identities.

### S — complete governed occurrence surface

The mechanically reconciled `S_base ∪ S_head` for this transition contains
exactly three binary occurrences:

1. `usr/bin/caddy`, produced by the closed temporary Go module in
   `frontend/Dockerfile.caddy-spa:8-72`;
2. `usr/bin/prometheus`, carried by the exact linux/amd64 image selected in
   `deploy/prometheus/image-manifest.json:1-9`;
3. `usr/bin/promtool`, carried by that same exact Prometheus image and executed
   independently in `.github/workflows/cd.yml:285-299`.

`S_base` is Caddy `v0.53.0`, Prometheus `v0.54.0`, and promtool `v0.54.0`, as
reported by the two CI jobs above. `S_head` requires `v0.55.0` in all three
occurrences. The Prometheus record binds one exact source revision, OCI index,
linux/amd64 platform manifest, and digest-only runtime reference at
`deploy/prometheus/image-manifest.json:2-8`; CD cross-binds the selected binary
revision and runs the exact promtool carrier at `.github/workflows/cd.yml:261-299`.

The Prometheus image transition is explicit rather than inferred from a tag:

- base v1 index:
  `sha256:50c707e96da5ade383cb1707790576480485e93de06aa60ad8802cb5f744bd0a`;
- base v1 linux/amd64 manifest:
  `sha256:934c331c7aa29ffdb23b4befec6f34321c518453e63713d741d8ac1737c8e049`;
- base runtime:
  `prom/prometheus:v3.14.0-distroless@sha256:934c331c7aa29ffdb23b4befec6f34321c518453e63713d741d8ac1737c8e049`;
- head source revision: `09fdfcd2659dd9c816e9e23c992fc161c0091757`;
- head v2 index:
  `sha256:1b88c17bf5f023ee6daf6bb1ee5605e1f69fd2df9e87fca3658949c44b0588ab`;
- head v2 linux/amd64 manifest:
  `sha256:84f0d46e960e86b6965d2e4d99a06f92f176dd75a31ead99126a009891e00f22`;
- head runtime:
  `prom/prometheus@sha256:84f0d46e960e86b6965d2e4d99a06f92f176dd75a31ead99126a009891e00f22`.

The three Compose consumers and two deploy validators are downstream consumers
of the same Prometheus image identity; they do not add independent
`golang.org/x/crypto` occurrences. Other repository dependencies and unrelated
container images are outside this exact transition rather than silently
classified safe.

### A — applicable advisory inventory

`A = F_cutoff`. The one candidate advisory has affected, comparable witnesses
in every `S_base` occurrence. There are no non-applicable candidates requiring a
separate disposition and no disposition-only lane.

### I_R — one authored replacement action

The single operator-intent action is:

> Replace every governed occurrence of `go:golang.org/x/crypto` with
> `v0.55.0`, without a suppression or a mutable runtime identity.

For Caddy, the sole resolver command expressing that action is
`go get golang.org/x/crypto@v0.55.0`. For the two Prometheus binaries, the same
identity-wide action is materialized by the already-selected immutable
upstream-main image whose exact source revision contains `v0.55.0`. These are
two surface expressions of one authored dependency action, not authority for
two independent upgrades.

### C_R — deterministic resolver closure

The Caddy replay produced one nine-transition dependency delta. The first row
is the sole `I_R` transition; the other eight rows are deterministic solver
closure `C_R` and carry no independent operator intent:

| Classification | Module | Exact base | Exact head | Binary status |
|---|---|---:|---:|---|
| `I_R` | `golang.org/x/crypto` | `v0.53.0` | `v0.55.0` | embedded |
| `C_R` | `golang.org/x/mod` | `v0.37.0` | `v0.38.0` | graph-only |
| `C_R` | `golang.org/x/net` | `v0.56.0` | `v0.57.0` | embedded |
| `C_R` | `golang.org/x/sync` | `v0.21.0` | `v0.22.0` | embedded |
| `C_R` | `golang.org/x/sys` | `v0.46.0` | `v0.47.0` | embedded |
| `C_R` | `golang.org/x/telemetry` | `v0.0.0-20260625142307-59b4966ccb57` | `v0.0.0-20260708182218-49f421fb7959` | graph-only |
| `C_R` | `golang.org/x/term` | `v0.44.0` | `v0.45.0` | embedded |
| `C_R` | `golang.org/x/text` | `v0.39.0` | `v0.41.0` | embedded |
| `C_R` | `golang.org/x/tools` | `v0.47.0` | `v0.48.0` | graph-only |

No transition is manual or unclassified. A diagnostic follow-up
`go get golang.org/x/text@v0.41.0` left the normalized graph byte-identical, so
the implementation omits it: `x/text v0.41.0` remains solver closure rather
than a second authored action.

### P — required universal head postcondition

The remediation postcondition is the conjunction of all of the following:

- every governed head occurrence is advisory-comparable and embeds
  `golang.org/x/crypto v0.55.0`, or the occurrence is executably absent;
- the final Caddy binary reports the exact identities listed below;
- both Prometheus binaries remain bound to the exact digest-only runtime record
  and report `golang.org/x/crypto v0.55.0` under the current scanner;
- the final Caddy and Prometheus images pass the existing suppression-free
  `CRITICAL,HIGH` scans on the exact current PR head;
- focused tests, the narrow local bundle, current-head CI, review disposition,
  canonical closeout, and strict merge readiness all pass.

Partial success fails. An unparseable module row, omitted occurrence,
unexpected transition, unresolved image identity, stale scan, or failed check
leaves `P` false.

## Exact Apple Container resolver replay

This replay was run with Apple Container on `linux/amd64` using exactly:

- image:
  `golang:1.26.6-alpine3.23@sha256:5978cc992ad5ef96a7469713c8af849c1433824761ce3be2c56381403cd8d9a3`;
- environment: `CGO_ENABLED=0`, `GOTOOLCHAIN=local`,
  `GOPROXY=https://proxy.golang.org,direct`, and `GOSUMDB=sum.golang.org`;
- observed toolchain: `go env GOVERSION` returned `go1.26.6`;
- one ephemeral `mktemp` directory, with no retained `go.mod` or `go.sum`
  promoted into the repository.

The exact command sequence was:

```text
go mod init pulseplate.local/caddy-build
go get github.com/caddyserver/caddy/v2/cmd/caddy@v2.11.4
go get google.golang.org/grpc@v1.82.1
go get golang.org/x/text@v0.39.0
# capture normalized sorted Path/Version/Replace base graph
go get golang.org/x/crypto@v0.55.0
# capture normalized sorted Path/Version/Replace head graph and complete delta
go mod download all
go mod verify
go build -mod=readonly -trimpath \
  -ldflags '-X github.com/caddyserver/caddy/v2.CustomVersion=v2.11.4' \
  -o /go/bin/caddy github.com/caddyserver/caddy/v2/cmd/caddy
go version -m /go/bin/caddy
```

`go mod verify` returned `all modules verified`, and the build completed. The
resulting binary inspection contained these exact expected rows:

- Go `go1.26.6`;
- `github.com/caddyserver/caddy/v2 v2.11.4`;
- `google.golang.org/grpc v1.82.1`;
- `golang.org/x/crypto v0.55.0`;
- `golang.org/x/net v0.57.0`;
- `golang.org/x/sync v0.22.0`;
- `golang.org/x/sys v0.47.0`;
- `golang.org/x/term v0.45.0`;
- `golang.org/x/text v0.41.0`.

`x/mod`, `x/telemetry`, and `x/tools` are graph-only closure and are not
misrepresented as embedded binary rows.

This replay established resolver and build feasibility before the repository
recipe was changed. It is not reproducibility proof, provenance attestation,
behavioral-equivalence proof, deployment authorization, or a no-vulnerability
claim.

## Local exact candidate image evidence

After the bounded implementation, Apple Container rebuilt the exact candidate
from `frontend/Dockerfile.caddy-spa:8-116` for `linux/amd64`. The builder-stage
command at `frontend/Dockerfile.caddy-spa:15-72` passed every closed graph,
checksum, build, and embedded-metadata comparison:

```text
all modules verified
governed graph rows: 11 / 11
Caddy version: v2.11.4
Go version: go1.26.6
governed embedded rows: 8 / 8
replacement rows: 0
```

The full candidate build then produced these local OCI identities:

- image index: `sha256:07365198133493f3f6458cc9699b043607711af0098eafea81445f00ea92ff85`;
- linux/amd64 manifest: `sha256:5a1f5c9e9768b0e6aaefcaa625404d0041cb097c66b0eed8c0c3bdfab4381dab`;
- config: `sha256:77b5e563b49e6a5079eb759c1e0a4d2d63e8be555fa3da48dca86b6029ae9e45`;
- exported OCI archive SHA-256:
  `df803fbad6a9310916619d140ffe9b9c931f65651b3a2faecded8b0fccc4403b`.

Apple Container executed the completed linux/amd64 image with Rosetta, no DNS,
a read-only root filesystem, dropped capabilities except
`NET_BIND_SERVICE`, and explicit temporary data/config mounts. The exact local
runtime checks passed:

```text
caddy version: v2.11.4
caddy build-info Go row: go1.26.6
/usr/bin/caddy cap_net_bind_service=ep
standard module-name parity: identical to the exact official Caddy base
staging Caddyfile: Valid configuration
production Caddyfile: Valid configuration
```

Trivy `v0.72.0` ran separately in Apple Container against the extracted exact
OCI layout. Its vulnerability database was downloaded before the scan; the
scan itself used no DNS, an explicitly empty regular ignore file, scanners
`vuln,secret`, package types `os,library`, severities `CRITICAL,HIGH`, and
blocking exit code `1`. The report SHA-256 is
`01a98afd60a4d85ac11102e70f05ec93a927d1b05770d14b38e9db9fc1c0974f` and the
bounded result was:

```text
trivy_high_critical_findings=0
```

This is a local exact-image observation for the named platform, image,
Trivy version, database snapshot, scanners, package types, severities, and
ignore posture. It does not establish universal image safety, complete
provenance, reproducible builds, all-platform coverage, or the absence of
future findings. GitHub Frontend CI and CD must independently rebuild and scan
the unchanged PR head.

## Repository enforcement and final proof still required

The implementation must keep the current closed Caddy recipe and add only the
exact crypto selection plus resolved embedded-module assertions. The resulting
closed recipe and negative mutation contract are enforced at
`tests/test_caddy_deploy_provenance.py:282-460`;
the Prometheus manifest and CD identity contract is enforced at
`tests/test_deploy_contract_scripts.py:210-269,309-380`.

Final evidence must come from the unchanged PR head after implementation:

1. the focused Caddy provenance tests prove the exact command order, all nine
   transition identities, expected embedded rows, and rejection of vulnerable
   or missing values;
2. the canonical GitHub runner builds the final Caddy image and inspects the
   exact completed binary, standard-module parity, capabilities, Caddyfile,
   provenance, and SBOM;
3. Caddy and Prometheus each pass their exact-image Trivy `vuln,secret` scan
   with severities `CRITICAL,HIGH`, exit code `1`, and an empty dedicated ignore
   file; the Prometheus form is visible at `.github/workflows/cd.yml:301-369`;
4. all other current-head required checks, review threads, mapping, and strict
   closeout pass.

The word “exact” in this document means equality to the finite identities and
records listed here. It does not mean complete upstream provenance, universal
behavioral equivalence, absence of vulnerabilities outside the scanned
database/severity/types, or general supply-chain safety.

## Rollback and exit criteria

Rollback is forward-only. Before merge, a failed resolver, build, module-parity,
capability, provenance, SBOM, or scan gate stops this PR; it does not admit the
known-affected Caddy or Prometheus image, a suppression, or a partial rollback.
After merge, any defect is corrected by a new PR selecting another verified
fixed identity and rerunning the same gates. No force-push, mutable tag, broad
module downgrade, or test-only rollback is permitted.

Caddy exit criteria are independent of Prometheus: retire the explicit
`golang.org/x/crypto v0.55.0` selection only after an official Caddy release's
canonical Go 1.26.6 resolver graph selects `v0.55.0` or later without that
override, the complete graph delta is reconciled, embedded-module and standard
module parity checks pass, and the exact rebuilt image passes the existing
suppression-free scan and current-head gates.

Prometheus exit criteria are independent of Caddy: replace the temporary
upstream-main bridge only with an official Prometheus semver release whose exact
index/platform digests, binary revision, both binary module inventories,
runtime/config contract, and suppression-free scan satisfy the existing v2
admission checks. Neither exit may be inferred from the other component's
release or scan.
