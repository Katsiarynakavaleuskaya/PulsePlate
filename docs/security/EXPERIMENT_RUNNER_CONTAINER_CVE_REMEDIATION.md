# Experiment Runner container CVE remediation

**Status:** Exact image and oracle admitted locally; current-head PR/merge evidence pending
**Suppression expires:** N/A (no suppression added)
**Last reviewed:** 2026-07-23

## Security decision

The previous immutable Experiment Runner image is not acceptable for mandatory
oracle evidence. Database-refreshed scans with local Trivy 0.71.2 and the
official checksum-verified Trivy 0.72.0 release produced the same baseline:

- 61 HIGH/CRITICAL occurrences: 17 CRITICAL and 44 HIGH;
- 27 unique vulnerability IDs;
- Debian 12.14 with 120 installed OS packages.

The affected package set included `util-linux`, Perl, ncurses, expat, SQLite,
gzip, ACL, curl, and SSH libraries. The immutable baseline remains gitignored
negative evidence. It is not a waiver, an admission result, or a reason to
rerun the same vulnerable image.

## Rejected candidates

The first candidate moved both stages to the exact official
`python:3.13.14-slim-trixie` digest and minimized direct runtime packages. It
built successfully as Apple image index
`sha256:ee233e13a3663e86bcf8922fe0944e183c9220e600e2f33447e8acf483fa8940`.
The manifest-bound config/history was secret-clean, but the official
unsuppressed Trivy 0.72.0 scan still found 60 occurrences across 25 unique
CVEs (16 CRITICAL and 44 HIGH). That exact image is not admitted.

The Alpine 3.24 candidate was rejected before image admission. The locked
installer required binary wheels, while `matplotlib==3.10.8` had no compatible
Linux ARM64 musllinux wheel. The diagnostic used the approved private Python
index secret; it did not fall back to public PyPI. Weakening the dependency
lock, binary-wheel policy, or index boundary was not authorized.

## Remediation

The admitted recipe derives the shared Python layer, builder, and final runner
from the official UBI 10 minimal digest
`sha256:04140c8d78c6c6915b5c1fdad2f16d10eac3630c3339999ccdf659d8c903be50`.
The exact base alone was recognized by Trivy 0.72.0 as Red Hat 10.2 and had zero
HIGH/CRITICAL findings.

Python 3.13.14 is installed from exact EPEL 10 RPM versions. The recipe
checksum-pins the official EPEL 10 public key and release RPM, imports the key,
requires the RPM signature from key `e37ed158`, and verifies
`epel-release-10-8.el10_2.noarch`. It does not use `--nogpgcheck`, checksum
bypass, weak dependencies, or an unversioned package request.

The Python Software Foundation published `CVE-2026-15308` after Python 3.13.14:
incremental `html.parser.HTMLParser` processing could cause CPU denial of
service. Trivy did not project this fresh EPEL/Python finding into the image
scan, so a clean scanner result alone was insufficient. The recipe overlays
the official CPython 3.13 backport from commit
`7933f4bf7131aa4140750f9404f5de0aa2969ced`, pins the runtime file to SHA-256
`4274e9112adf3fa57c7f9afa7c9b5c631456b18b7403cc627cc5027d02cdd2ae`, removes
stale bytecode, and asserts the patched buffering fields before the build can
continue.

The final stage installs exact `git-core`, `make`, `shadow-utils`, and
`util-linux-core` versions with weak dependencies disabled, removes the EPEL
repository package, and preserves non-root UID/GID 65532. The Python dependency
lock still installs only through BuildKit secret mounts and the repository's
direct-proxy installer. No vulnerability ignore, suppression, scan-severity
reduction, package-manager upgrade, `@latest`, or public-index fallback was
added.

## Exact image evidence

The canonical Apple dispatcher built:

`pulseplate/experiment-runner:ubi-cve-final@sha256:135a0da911661487b074ae710c8f02d523e7a33d51f1ac41607a37c4b752f1ff`

The admission chain verified:

- top image index:
  `sha256:135a0da911661487b074ae710c8f02d523e7a33d51f1ac41607a37c4b752f1ff`;
- one `linux/arm64` manifest:
  `sha256:45b20d721b0609c5c5c9caa23dedb8a12ea5ae9359a16729a9da470d3b5cc2bf`;
- manifest-bound config/history:
  `sha256:5d2e196f149dfcd063bdcd966637d2175fbb1fa1699befe7fc44727ef18e65b6`;
- no configured proxy-secret name or current secret value in config/history;
- UID/GID `65532:65532`, Python `3.13.14`, exact patched parser checksum, and
  exact RPM/runtime tool versions;
- Red Hat 10.2 with 125 OS packages and one Python dependency manifest, with
  zero HIGH/CRITICAL findings from the official checksum-verified Trivy 0.72.0
  binary across the unfiltered OS-and-language scan, using
  `--ignorefile /dev/null`, `--ignore-unfixed=false`, and `--exit-code 1`;
- strict Apple Container 1.1.0 isolation with every required digest, network,
  mount, root-read-only, result-volume, and cleanup control true.
- one accepted oracle-only review with all three immutable oracles passing,
  `network_budget=0`, the exact five-file source diff applied in isolation,
  `mutated_paths: []`, and `shared_tree_untouched: true`.

The scan consumes only the manifest-bound OCI layout exported from that exact
Apple image reference. Local artifacts remain gitignored and are evidence, not
canonical repository files. Current-head CI and PR governance remain separate
required signals.

## Source evidence

- NVD record sourced from the Python Software Foundation:
  <https://nvd.nist.gov/vuln/detail/CVE-2026-15308>
- Official CPython 3.13 backport:
  <https://github.com/python/cpython/commit/7933f4bf7131aa4140750f9404f5de0aa2969ced>
- Official CPython issue:
  <https://github.com/python/cpython/issues/153030>
- Official Red Hat Universal Base Image documentation:
  <https://developers.redhat.com/products/rhel/ubi>
- Official EPEL getting-started documentation:
  <https://docs.fedoraproject.org/en-US/epel/getting-started/>
- Official EPEL 10 key and release RPM:
  <https://dl.fedoraproject.org/pub/epel/RPM-GPG-KEY-EPEL-10> and
  <https://dl.fedoraproject.org/pub/epel/epel-release-latest-10.noarch.rpm>
- Official Trivy 0.72.0 release:
  <https://github.com/aquasecurity/trivy/releases/tag/v0.72.0>
- Trivy vulnerability scanner documentation:
  <https://trivy.dev/docs/latest/guide/scanner/vulnerability/>

## Repository evidence

- `deploy/experiment-runner/Containerfile:3` pins the UBI base;
  `deploy/experiment-runner/Containerfile:7` starts checksum-pinned external
  sources; `deploy/experiment-runner/Containerfile:19` verifies EPEL/Python;
  `deploy/experiment-runner/Containerfile:60` preserves the private-index
  installer; and `deploy/experiment-runner/Containerfile:104` defines the exact
  non-root runtime package contract.
- `tests/test_experiment_runner_dispatch.py:173` guards stage/base identity;
  `tests/test_experiment_runner_dispatch.py:187` guards source and patch
  verification; `tests/test_experiment_runner_dispatch.py:215` enumerates exact
  packages; and `tests/test_experiment_runner_dispatch.py:235` rejects
  suppression and dependency-policy weakening.
- `docs/orchestration/EXPERIMENT_RUNNER_MACOS_RUNBOOK.md:230` records the
  negative candidates and executable digest-bound admission sequence.
- `docs/roadmap/BACKLOG_LEDGER.md:27` keeps the prerequisite open until its PR is
  merged; ledger closure remains a later docs-only action.

## Required validation and admission

Do not use the source diff as scan evidence. A material rebuild requires a new
canonical Apple `build-image` result and the complete runbook admission chain.
Admission requires all of the following:

1. The image index, one `linux/arm64` manifest, config, and runtime metadata
   cryptographically bind to the Apple-returned digest.
2. The verified official Trivy 0.72.0 binary reports zero HIGH/CRITICAL OS or
   language-package findings without package-type filtering, ignore policy,
   unfixed filtering, or severity reduction.
3. Exact Python/RPM/CPython patch and non-root assertions pass inside that same
   image.
4. The strict Apple Container probe passes for that exact digest.
5. The oracle-only result is accepted with `network_budget=0`,
   `shared_tree_untouched: true`, expected backend provenance, and no host path
   or secret.

Any failed condition is a stop signal, not an infrastructure pass and not a
reason to retry with weaker controls.

## Rollback

If a later current-head or runtime regression appears, preserve the failed
evidence, keep the vulnerable runner blocked, and revert only the UBI
base/package/CPython patch candidate plus its tests and evidence documentation.
The dispatcher, result contract, and capability schema are unchanged and are
outside this rollback. Neither the failed trixie image, incompatible Alpine
recipe, nor blocked bookworm baseline is a fallback. Restore only a separately
admitted immutable runner reference; never downgrade, suppress, or use a
mutable tag to restore execution.
