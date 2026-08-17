# Experiment Runner container CVE remediation

**Status:** Current-base exact image re-admitted locally; final oracle and current-head PR/merge evidence pending
**Suppression expires:** N/A (no suppression added)
**Last reviewed:** 2026-08-17

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

Direct package pins alone do not freeze the transitive RPM closure. Each stage
therefore verifies a sorted inventory over the complete installed NEVRA,
package-header SHA-256, payload digest, and payload digest algorithm. The
accepted build locks 107 packages in `python-runtime`, 108 in `builder`, and
129 in the final runner. Any repository-side change to a direct or transitive
RPM now fails the build even if its package name and direct request remain
unchanged.

## Historical exact image evidence (2026-07-23)

The canonical Apple dispatcher built:

`pulseplate/experiment-runner:ubi-cve-review-fix@sha256:5b3abbad998dc1b23f9d99e72a8fde931558401b81a2aec8c5eeeff90b128a70`

This is retained as the complete prior admission record, not as the current
eligible image. Its original scan result below remains historical evidence.

The admission chain verified:

- top image index:
  `sha256:5b3abbad998dc1b23f9d99e72a8fde931558401b81a2aec8c5eeeff90b128a70`;
- one `linux/arm64` manifest:
  `sha256:c46d2bd8a174b6b10b9ed06c1c145eeb1ca131d326c67b4c72589ea84e6d1750`;
- manifest-bound config/history:
  `sha256:b96621e97fd78527a93f9853970d1f17baffa46e8d188e5341899fc6a1efaa1d`;
- all five manifest-referenced OCI layer blobs as regular files with exact
  descriptor byte lengths and SHA-256 digests;
- no configured proxy-secret name or current secret value in config/history;
- UID/GID `65532:65532`, Python `3.13.14`, exact patched parser checksum, and
  exact RPM/runtime tool versions;
- exactly 129 runtime RPMs with complete inventory SHA-256
  `bf2426b194df76bfc9f26642a23b7b94f208ee11692510707d737476368a34b2`;
- Red Hat 10.2 with 129 OS packages and one Python dependency manifest, with
  zero HIGH/CRITICAL findings from the official checksum-verified Trivy 0.72.0
  binary across the unfiltered OS-and-language scan, using
  `--config /dev/null`, `--ignorefile /dev/null`, empty `--ignore-policy=`,
  `--ignore-status=`, and `--vex=` inputs, `--ignore-unfixed=false`, and
  `--exit-code 1`;
- strict Apple Container 1.1.0 isolation with every required digest, network,
  mount, root-read-only, result-volume, and cleanup control true.

The same freshly downloaded Trivy 0.72.0 database used for the current
re-admission was also applied to this exact historical OCI layout. Database
schema `2` was updated at `2026-08-17T06:55:37.603156251Z`; its `trivy.db`
SHA-256 was
`444bb0cefab136b303ccfc458c4f86c4a6b69201722568d91204d90cc0db78cf`.
The historical image still projected 136 Python packages, but the refreshed
report (SHA-256
`303ca24537fa079f3d18149e74dd0f986b2b05033205e720823d0cbeede0c80e`)
now reports two HIGH findings in `cryptography==48.0.1`:

- `CVE-2026-69247`, fixed in `50.0.0`;
- `CVE-2026-69249`, fixed in `49.0.0`.

That result is a fail-closed reason not to reuse the old digest. It does not
rewrite or discard the original July receipt.

## Historical aa9 exact image re-admission (2026-08-17)

The canonical Apple dispatcher built the then-current `aa9ddb97` repository
lock and the rebaselined final-stage RPM inventory as:

`pulseplate/experiment-runner:inventory-refresh-aa9ddb97@sha256:7fd5b16759d979c277f42fd3a982ba9620723a8049093b66ebfef7b5bbf389da`

The digest-bound OCI traversal verified:

- top image index:
  `sha256:7fd5b16759d979c277f42fd3a982ba9620723a8049093b66ebfef7b5bbf389da`;
- exactly one `linux/arm64` manifest:
  `sha256:5516d0172fe2810db681afd6a42006c89026ff034edf00891119ac5640abe759`;
- manifest-bound config/history:
  `sha256:d464ad9a67ccc553cf141bb88d14cc037ba862d6e71426358996785edd370d8d`;
- five regular layer blobs, each verified against its descriptor size and
  SHA-256:
  - `sha256:58f664164ca85fb5b417ce6f6fffea1e66eaf780a7dedb2c483cdd5286d5ee2b`
    (`33,053,422` bytes);
  - `sha256:5a3a20a454b64d6fc36b0af64f0db4999e4f570a9ef29f1c800110739b6dd59a`
    (`18,843,366` bytes);
  - `sha256:2917935a83d987f74a954d19f8a313cf2558074fc2f09c8fbe9f5da380630769`
    (`20,809,268` bytes);
  - `sha256:f52a86905632f47ae608ee268431330471493068cf852c7885424dd301339e0d`
    (`148,004,165` bytes);
  - `sha256:4f4fb700ef54461cfa02571ae0db9a0dc1e0cdb5577484a6d75e68dc38e8acc1`
    (`32` bytes).

Config/history contained neither configured proxy-secret names nor any
non-empty current secret value. Runtime remained UID/GID `65532:65532`, Python
`3.13.14`, the checksum-pinned CPython parser patch, and the exact requested
runtime tool versions.

### Complete RPM inventory delta and provenance

The exact old and new inventories both contain 129 rows. Of those, 127 full
rows are byte-identical and 127 NEVRA identities are shared. There is no
same-NEVRA header or payload mutation. The complete four-row delta is:

```text
-openssh-0:9.9p1-23.el10_2.aarch64 6b968c0f96817c905f452c37c5d75c79298eae0a9066df91c0a9c830e653b50d c92ddb49b63d0779eab294e41ed151e1a8b3cccea69d69f0f93d7baaff1487a4 8
-openssh-clients-0:9.9p1-23.el10_2.aarch64 105fcd23e18730bc3dec02a36cb5ddb78776dc5d7431d9994c85556d34cf1687 b467e84963c7e075274ad40ac54a5581853f40a7bea98e5a637b05445485a32e 8
+openssh-0:9.9p1-25.el10_2.aarch64 daaf6c87cc989d9e8b7bac399b5c800eb814210d6f3567295c2955bb46883054 253f1ce45f3d87c669a83f95bf754b057b792d16e69be4921d2ccebb509edcc9 8
+openssh-clients-0:9.9p1-25.el10_2.aarch64 08cfffa1a014e730ccb3cca41cb636effe699012ca7aace4fff52f299e55de17 3c408d3af0bf935baa1908515fe181bf245a5cbceb443ce1d1ed81fd914dc695 8
```

Both old rows come from `openssh-9.9p1-23.el10_2.src.rpm`; both new rows come
from `openssh-9.9p1-25.el10_2.src.rpm`. Every row names vendor `Red Hat, Inc.`,
packager `Red Hat, Inc. <http://bugzilla.redhat.com/bugzilla>`, build host
`konflux.redhat.com`, and RSA/SHA256 signature key
`199e2f91fd431d51`. The installed `gpg-pubkey-fd431d51-4ae0493b` identifies
that suffix as Red Hat release key 2, and all UBI repositories keep
`gpgcheck = 1` with `RPM-GPG-KEY-redhat-release`.

The base digest, checksum-pinned sources, EPEL key/release RPM, and four direct
runner requests did not change. `git-core-2.52.0-1.el10.aarch64` requires
`openssh-clients`, which in turn requires `openssh`; therefore both changed
rows are transitive Red Hat closure, not direct requests. The resulting final
inventory SHA-256 changed from
`bf2426b194df76bfc9f26642a23b7b94f208ee11692510707d737476368a34b2`
to
`156a9229dcfa857f0b093926e669b54f7bf8e0a91bc3b4b5038f536d4a0798fa`.
The `python-runtime` inventory remains exactly 107 rows with SHA-256
`89d2a8bb1a6216d563f194d6c65b556dc5a1672c9b126afed5d1b6775a9c0125`;
the `builder` inventory remains exactly 108 rows with SHA-256
`877f449d91c786a5353d0f25d95423facc1cf06eb6e748c6c0be04f6ced7c26b`.

### Historical aa9 Python closure and same-database scan

The `aa9ddb97` locked Python closure contains 134 distributions. Relative to
the July historical image, that already-merged lock raised 12 package versions
(`cryptography`, `cyclonedx-python-lib`, `distlib`, the six OpenTelemetry
packages, `pip-tools`, `pre-commit`, and `prometheus-client`) and no longer
requires the `importlib-metadata` and `zipp` backports. No dependency file was
changed by this re-admission.

The normalized `importlib.metadata` runtime projection and Trivy's Python
package projection each contain exactly 134 unique name/version identities.
Both have SHA-256
`c2e2b687d71be007a1986133b5d8dca040074e3359b4e12871659e329ac5fddb`,
and their exact diff is empty. This proves that the 136-to-134 change was an
actual `aa9ddb97` lock-closure change, not a Trivy parsing artifact.

The official checksum-verified Trivy 0.72.0 macOS ARM64 asset has SHA-256
`88f208680dc05da2b459e19b4f5aa2b4dc7c2117892ba4aab2ae63baba330016`.
The same database used for both old and new comparisons has schema `2`,
`UpdatedAt=2026-08-17T06:55:37.603156251Z`, `DownloadedAt=2026-08-17T11:49:34.13304Z`,
metadata SHA-256
`5241141b35a0c92af31ca55e03c1892db62e538ad6d3123cc9dfc1bfcf905eed`,
and database SHA-256
`444bb0cefab136b303ccfc458c4f86c4a6b69201722568d91204d90cc0db78cf`.
The `aa9ddb97` exact-image report has SHA-256
`8477aa59b2d70b552ce75cc81ec7ae98ca7a8bee4fa0ea4661db0035ac069e71`.
It reports Red Hat 10.2, 129 OS packages, 134 Python packages, and zero
HIGH/CRITICAL findings with the existing unsuppressed isolated scan policy.

The first `aa9ddb97` image admission correctly stopped before the probe at
`trivy_admission_report_invalid:python_package_count`, because its validator
still required the historical count of 136. That negative report is retained
with SHA-256
`eab987248cb1f33f6b929e4243201487b870e2882a698c5750c9109494ce424e`.
After synchronizing only the strict count assertion and adding an executable
stale-136 rejection test, the complete runbook restarted from the beginning
and passed.

The strict Apple Container 1.1.0 artifact is bound to the exact image digest
and has SHA-256
`b8805cc968bbe405f8285ec93e360700d4a02e459e071792e9019df6aab5c343`.
It reports `strict_isolation=true`, `linux_arm64`, no blocking reasons, and all
runtime availability, guest-platform, digest, outer/inner DNS, host, direct-IP,
source/input read-only, private-tmpfs, root-read-only, result-volume,
unshare-without-broad-capabilities, and cleanup checks true.

The scan consumed only the manifest-bound OCI layout exported from that exact
historical Apple image reference. Local artifacts remain gitignored and are
evidence, not canonical repository files.

## Current c731 exact image re-admission (2026-08-17)

After `main` advanced to `c731f12117e7da922134509ad47808614c0dfcca`, the
canonical Apple dispatcher rebuilt the same pinned image recipe under a unique
tag and returned this immutable reference:

`pulseplate/experiment-runner:inventory-refresh-c731f121@sha256:e78a2453138295e2615343bdb4696272f4bee5054281a3ea5d25e52af51d014b`

That digest is distinct from both historical images above. The complete
runbook was restarted from its first step against that exact reference. Its
digest-bound OCI traversal verified:

- top image index:
  `sha256:e78a2453138295e2615343bdb4696272f4bee5054281a3ea5d25e52af51d014b`;
- exactly one `linux/arm64` manifest:
  `sha256:785245ef5562180f3be86f8129ad140bbb74d624b2e8da27534acfed4ec31911`;
- manifest-bound config/history:
  `sha256:c310b97f4b8c95faeb514b534212cc02f4ffe7e20ac113bcdba7ef928d6af5cd`;
- five regular layer blobs, each verified against its descriptor size and
  SHA-256:
  - `sha256:58f664164ca85fb5b417ce6f6fffea1e66eaf780a7dedb2c483cdd5286d5ee2b`
    (`33,053,422` bytes);
  - `sha256:5a3a20a454b64d6fc36b0af64f0db4999e4f570a9ef29f1c800110739b6dd59a`
    (`18,843,366` bytes);
  - `sha256:2917935a83d987f74a954d19f8a313cf2558074fc2f09c8fbe9f5da380630769`
    (`20,809,268` bytes);
  - `sha256:c279e4d7671ec177ba25360d8ed1e4da8b20a701164622c26962bf28223c5fd8`
    (`148,065,658` bytes);
  - `sha256:4f4fb700ef54461cfa02571ae0db9a0dc1e0cdb5577484a6d75e68dc38e8acc1`
    (`32` bytes).

The inspect receipt has SHA-256
`ba8eb6d0b13e8470ad358da3cf8bf125fcf5d5b41473cbb8333a943687b0280f`.
Config/history again contained neither configured proxy-secret names nor any
non-empty current secret value. Runtime remained UID/GID `65532:65532`, Python
`3.13.14`, the checksum-pinned CPython parser patch, and the exact requested
runtime tool versions.

### Current RPM and Python closure

The pinned source, base digest, EPEL key/release checksums, direct RPM requests,
and RPM formatter are unchanged from the historical aa9 re-admission. The
fresh `c731f121` build reproduced the exact stage contracts: 107
`python-runtime` rows with SHA-256
`89d2a8bb1a6216d563f194d6c65b556dc5a1672c9b126afed5d1b6775a9c0125`,
108 `builder` rows with SHA-256
`877f449d91c786a5353d0f25d95423facc1cf06eb6e748c6c0be04f6ced7c26b`,
and 129 final rows with SHA-256
`156a9229dcfa857f0b093926e669b54f7bf8e0a91bc3b4b5038f536d4a0798fa`.
The full RPM delta and Red Hat signature/provenance explanation in the
historical aa9 section therefore remains the complete RPM rebaseline: there is
no additional RPM row change on `c731f121`.

The current normalized runtime and Trivy Python projections each contain 134
unique name/version identities. Both have SHA-256
`b4690ca8af9ca4b320edca9723ccbd9b12c9ab9fe18675c54d4df6c3007d0ed5`,
and their exact diff is empty. Relative to the historical aa9 projection there
are no added or removed distribution names and exactly these five version
substitutions:

```text
alembic 1.18.4 -> 1.19.1
greenlet 3.3.2 -> 3.5.5
psycopg 3.3.3 -> 3.3.4
psycopg-binary 3.3.3 -> 3.3.4
SQLAlchemy 2.0.48 -> 2.0.52
```

The complete substitution projection has SHA-256
`e54f3aa6a8c84448c868d758fa1775b25881802ce3f33be1fa92ce3e27f6a0a6`.
This evidence is specific to the exact image, stage, architecture, source head,
and admission time; it is not a universal dependency-safety claim.

### Current same-database scan and strict probe

The checksum-verified official Trivy 0.72.0 macOS ARM64 asset remained
byte-identical with SHA-256
`88f208680dc05da2b459e19b4f5aa2b4dc7c2117892ba4aab2ae63baba330016`.
The refreshed database identity also remained byte-identical to the historical
comparison: schema `2`,
`UpdatedAt=2026-08-17T06:55:37.603156251Z`,
`DownloadedAt=2026-08-17T11:49:34.13304Z`, metadata SHA-256
`5241141b35a0c92af31ca55e03c1892db62e538ad6d3123cc9dfc1bfcf905eed`,
and database SHA-256
`444bb0cefab136b303ccfc458c4f86c4a6b69201722568d91204d90cc0db78cf`.
Because that identity did not change, the retained same-database historical
scan remains the valid comparison; no replacement scan of the July image was
needed.

The current exact-image report has SHA-256
`6286a379ae13716ebac825df3f91653bd87e6efdcb6e8f7daeceac12886bf703`.
It reports a container image, Red Hat 10.2, 129 OS packages, 134 Python
packages, and zero HIGH/CRITICAL findings under the existing unsuppressed,
isolated scan policy. The runtime contract output has SHA-256
`d9a768cc34f94b9a93f49a8de761377f78d6ada7e2c3841041580288557cc7c6`.

The strict Apple Container 1.1.0 artifact is bound to the current exact image
digest and has SHA-256
`d0be192e5371f371ee70cdbfcb867e668fbd3415052d12d41065f5f8f5522db3`.
It reports `strict_isolation=true`, `linux_arm64`, no blocking reasons, and all
required runtime availability, guest-platform, digest, outer/inner DNS, host,
direct-IP, source/input read-only, private-tmpfs, root-read-only,
result-volume, unshare-without-broad-capabilities, and cleanup checks true.

The scan consumes only the manifest-bound OCI layout exported from this exact
Apple image reference. Local artifacts under
`artifacts/orchestration/security/runner-e78a2453138295e2615343bdb4696272f4bee5054281a3ea5d25e52af51d014b/`
remain gitignored evidence, not canonical repository files. Current-head CI
and PR governance remain separate required signals. The final immutable-oracle
review runs only after material freeze; its result is recorded in closeout
evidence and is not back-written into this material security note.

## Sanitized command receipts

The current canonical build command was:

```bash
python3 scripts/orchestration/experiment_runner_dispatch.py build-image \
  --backend apple-container \
  --tag pulseplate/experiment-runner:inventory-refresh-c731f121
```

Exit status: `0`. Sanitized dispatcher output:

```json
{"backend": "apple-container", "image": "pulseplate/experiment-runner:inventory-refresh-c731f121@sha256:e78a2453138295e2615343bdb4696272f4bee5054281a3ea5d25e52af51d014b", "sanitized": "true"}
```

The complete runbook admission restarted from its first step and exited `0`.
Its success-only receipt, SHA-256
`441c3ce288cc1164e8df01e55eed5c244839b80a5c09b8feeb6ba75ca5d308c6`,
is:

```text
trivy_checksum_exit=0
image_inspect_exit=0
oci_descriptor_validation_exit=0
oci_layer_count=5
config_history_validation_exit=0
runtime_contract_exit=0
trivy_exit=0
trivy_artifact_type=container_image
trivy_os_family=redhat
trivy_os_version=10.2
trivy_os_package_count=129
trivy_python_package_count=134
trivy_high_critical_findings=0
apple_probe_exit=0
```

The retained runtime and strict-probe outputs are:

```text
uid_gid=65532:65532
python_version=3.13.14
rpm_package_count=129
rpm_inventory_sha256=156a9229dcfa857f0b093926e669b54f7bf8e0a91bc3b4b5038f536d4a0798fa
runtime_contract=passed
{"artifact": "mac-strict-capability-e78a2453138295e2615343bdb4696272f4bee5054281a3ea5d25e52af51d014b.json", "strict_isolation": true}
```

## Historical aa9 sanitized command receipts (2026-08-17)

The `aa9ddb97` canonical build command was:

```bash
python3 scripts/orchestration/experiment_runner_dispatch.py build-image \
  --backend apple-container \
  --tag pulseplate/experiment-runner:inventory-refresh-aa9ddb97
```

Exit status: `0`. Sanitized dispatcher output:

```json
{"backend": "apple-container", "image": "pulseplate/experiment-runner:inventory-refresh-aa9ddb97@sha256:7fd5b16759d979c277f42fd3a982ba9620723a8049093b66ebfef7b5bbf389da", "sanitized": "true"}
```

The restarted complete runbook admission exited `0`. Its success-only receipt
is:

```text
trivy_checksum_exit=0
image_inspect_exit=0
oci_descriptor_validation_exit=0
oci_layer_count=5
config_history_validation_exit=0
runtime_contract_exit=0
trivy_exit=0
trivy_artifact_type=container_image
trivy_os_family=redhat
trivy_os_version=10.2
trivy_os_package_count=129
trivy_python_package_count=134
trivy_high_critical_findings=0
apple_probe_exit=0
```

The retained runtime and strict-probe outputs are:

```text
uid_gid=65532:65532
python_version=3.13.14
rpm_package_count=129
rpm_inventory_sha256=156a9229dcfa857f0b093926e669b54f7bf8e0a91bc3b4b5038f536d4a0798fa
runtime_contract=passed
{"artifact": "mac-strict-capability-7fd5b16759d979c277f42fd3a982ba9620723a8049093b66ebfef7b5bbf389da.json", "strict_isolation": true}
```

## Historical sanitized command receipts (2026-07-23)

The admitted build command was:

```bash
python3 scripts/orchestration/experiment_runner_dispatch.py build-image \
  --backend apple-container \
  --tag pulseplate/experiment-runner:ubi-cve-review-fix
```

Exit status: `0`. Sanitized dispatcher output:

```json
{"backend": "apple-container", "image": "pulseplate/experiment-runner:ubi-cve-review-fix@sha256:5b3abbad998dc1b23f9d99e72a8fde931558401b81a2aec8c5eeeff90b128a70", "sanitized": "true"}
```

The runbook admission block was executed against that immutable reference with
the official checksum-verified Trivy 0.72.0 binary. The scan exited `0`. After
the first security diff review identified an incomplete-report fail-open in the
old jq count, the exact retained report was admitted through the new
fail-closed self-contained Python coverage guard. Guard exit status: `0`. The
subsequent exact-head diff review also required byte-level verification of
every referenced OCI layer and explicit isolation from ambient Trivy
configuration and suppression inputs. Those controls now run before the
coverage guard and strict probe. The refreshed digest-bound
`admission-exit-statuses.txt` receipt was:

```text
trivy_checksum_exit=0
image_inspect_exit=0
oci_descriptor_validation_exit=0
oci_layer_count=5
config_history_validation_exit=0
runtime_contract_exit=0
trivy_exit=0
trivy_artifact_type=container_image
trivy_os_family=redhat
trivy_os_version=10.2
trivy_os_package_count=129
trivy_python_package_count=136
trivy_high_critical_findings=0
apple_probe_exit=0
```

The retained sanitized runtime and probe outputs were:

```text
uid_gid=65532:65532
python_version=3.13.14
rpm_package_count=129
rpm_inventory_sha256=bf2426b194df76bfc9f26642a23b7b94f208ee11692510707d737476368a34b2
runtime_contract=passed
{"artifact": "mac-strict-capability-5b3abbad998dc1b23f9d99e72a8fde931558401b81a2aec8c5eeeff90b128a70.json", "strict_isolation": true}
```

The retained isolated-policy Trivy JSON has SHA-256
`a6dbec30f4cb29ade7a782ff72e470071e35622c0eaa2fbf86c36d6a052f794b`.
It identifies `redhat` `10.2`, a `container_image` artifact, 129 OS packages,
and 136 packages in the Python manifest. The layer guard rejects missing,
duplicate, non-regular, wrong-size, or digest-mismatched blobs before Trivy
runs. The report guard requires all four coverage facts, Trivy schema v2,
unique non-empty package identities, and well-formed vulnerability arrays
before accepting zero selected findings. Missing `Results`, OS-only,
Python-only, malformed, ambiguous, or non-zero finding reports fail closed.
Because the isolated scan command also uses `--exit-code 1`, its recorded exit
status of `0` independently confirms that the unsuppressed scan found zero
selected findings.

The rejected exact trixie admission used the same unfiltered Trivy flags.
Exit status: `1`. Its sanitized summary was:

```json
{"family":"debian","version":"13.6","high":44,"critical":16,"total":60}
```

The Alpine compatibility check stopped at the existing binary-wheel contract.
Its exploratory console output was not retained and is explicitly not used as
audit proof or as fallback evidence. Reconsidering Alpine requires a fresh,
complete, digest-bound build and admission receipt.

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
  `deploy/experiment-runner/Containerfile:37` begins the three complete RPM
  inventory checks; `deploy/experiment-runner/Containerfile:75` preserves the
  private-index installer; and `deploy/experiment-runner/Containerfile:119`
  defines the exact non-root runtime package contract.
- `tests/test_experiment_runner_dispatch.py:371` proves complete layer
  verification; `tests/test_experiment_runner_dispatch.py:396` rejects
  incomplete or changed blobs; `tests/test_experiment_runner_dispatch.py:435`
  proves the complete clean scanner report; and
  `tests/test_experiment_runner_dispatch.py:484` rejects incomplete,
  malformed, and non-zero-finding reports.
- `tests/test_experiment_runner_dispatch.py:504` guards stage/base identity;
  `tests/test_experiment_runner_dispatch.py:518` guards source and patch
  verification; `tests/test_experiment_runner_dispatch.py:548` enumerates exact
  packages and inventories; `tests/test_experiment_runner_dispatch.py:587`
  rejects suppression and dependency-policy weakening; and
  `tests/test_experiment_runner_dispatch.py:640` guards the complete executable
  runbook admission order.
- `docs/orchestration/EXPERIMENT_RUNNER_MACOS_RUNBOOK.md:230` records the
  negative candidates; its executable digest-bound admission sequence starts
  at `docs/orchestration/EXPERIMENT_RUNNER_MACOS_RUNBOOK.md:273`, its layer
  verifier is at `docs/orchestration/EXPERIMENT_RUNNER_MACOS_RUNBOOK.md:399`,
  and its fail-closed Trivy coverage call is at
  `docs/orchestration/EXPERIMENT_RUNNER_MACOS_RUNBOOK.md:585`.
- `docs/roadmap/BACKLOG_LEDGER.md:338` keeps the prerequisite open until its PR is
  merged; ledger closure remains a later docs-only action.

## Required validation and admission

Do not use the source diff as scan evidence. A material rebuild requires a new
canonical Apple `build-image` result and the complete runbook admission chain.
Admission requires all of the following:

1. The image index, one `linux/arm64` manifest, all five referenced layer
   blobs, config, and runtime metadata cryptographically bind to the
   Apple-returned digest; every layer is a regular file whose size and SHA-256
   match its descriptor.
2. The verified official Trivy 0.72.0 binary reports zero HIGH/CRITICAL OS or
   language-package findings without package-type filtering, ignore policy,
   unfixed filtering, or severity reduction. Both database and scan commands
   ignore ambient configuration; all external ignore-policy, ignore-status,
   and VEX inputs are explicitly empty. The executable runbook Python guard
   must additionally prove the exact schema, artifact/OS identity, one
   129-package Red Hat result, and one 134-package Python result before the
   zero-finding receipt is written.
3. Exact Python/RPM/CPython patch and non-root assertions pass inside that same
   image, including the complete 107/108/129 package inventories over NEVRA,
   header SHA-256, payload digest, and payload digest algorithm.
4. The strict Apple Container probe passes for that exact digest.
5. After material freeze, the oracle-only result is accepted with
   `network_budget=0`,
   `shared_tree_untouched: true`, expected backend provenance, and no host path
   or secret.

Any failed condition is a stop signal, not an infrastructure pass and not a
reason to retry with weaker controls.

## Rollback

If a later current-head or runtime regression appears, preserve the failed
evidence, keep the vulnerable runner blocked, and revert only the UBI
base/package/CPython patch candidate plus its image-specific tests and evidence
documentation. The fail-closed OCI layer guard, isolated Trivy invocation, and
Trivy coverage guard must not be removed to restore execution; a guard
regression requires a fix-forward while the runner remains blocked. The result
contract and capability schema are unchanged. Neither the failed trixie image,
incompatible Alpine recipe, nor blocked bookworm baseline is a fallback.
Restore only a separately admitted immutable runner reference; never
downgrade, suppress, or use a mutable tag to restore execution.
