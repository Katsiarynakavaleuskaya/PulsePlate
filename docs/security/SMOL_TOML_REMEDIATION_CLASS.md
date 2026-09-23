# DEP-SEC-02: root npm `smol-toml` remediation class

## Authority and boundary

The owner-accepted DEP-SEC-02 plan authorizes one npm dependency identity:
`D = npm:smol-toml`. The exact base is
`bcaf6d03c1746886e522f2ac24485338b4ec6e92`. The sole authored dependency
action is replacement of the existing root override from `1.6.1` to `1.9.0`
at `package.json:28`. Native npm resolution supplies the lock changes at
`package-lock.json:1285`. CSpell is the consumer, through
`cspell@9.2.1 -> cspell-config-lib@9.2.1 -> smol-toml`; the dependency is
development tooling, not a new product runtime or public API surface.

This document owns transition evidence for the current PR. Permanent tests in
`tests/test_root_npm_dependency_guards.py:35` independently discover the current
tracked surfaces and check their current occurrences. They do not pin this
historical base, five-file topology, exact lock hash, or resolver delta.

## S: independently enumerated npm surfaces

`S_base` came from `git ls-tree -r -z <base>`; `S_head` came independently from
`git ls-files --cached -z` and regular, non-symlink worktree reads. Both select
every tracked basename `package.json`, `package-lock.json`, or
`npm-shrinkwrap.json`. Both sets contain the same five regular files. The
candidate head below is the working tree before the later PR material commit;
the canonical review mapping will bind its eventual exact head.

| Surface | Base SHA-256 | Candidate head SHA-256 |
| --- | --- | --- |
| `frontend/package-lock.json` | `218ce00de53a874d486dd9fbbc275b9f00445435283c93acd1963a9569810423` | `218ce00de53a874d486dd9fbbc275b9f00445435283c93acd1963a9569810423` |
| `frontend/package.json` | `7d38cb173973ea0cab7ff49b1d2c7af37d6a1bc482b85a4e4c419245b3faba10` | `7d38cb173973ea0cab7ff49b1d2c7af37d6a1bc482b85a4e4c419245b3faba10` |
| `package-lock.json` | `a1c5411b103a80fc78b293c628d0fd8d6f47de065d2c75a208d06e40c683d9e8` | `bfb717b8a82095aaccb782af2d1754dd6a6d3758737f63b539970483ead2cd40` |
| `package.json` | `9bcbc2307471c1eb4be4c87cffeb88587339e911e6a4898d5c9234fff7b0766c` | `466203ec7350daf9bae1971385c01b829b5936b33ced8781feeb2bdb102620c8` |
| `scripts/business_collateral/package.json` | `8005a3491db7d92f36ac66369861589f9c47123d3a7c71e643fc2c06168cd45` | `8005a3491db7d92f36ac66369861589f9c47123d3a7c71e643fc2c06168cd45` |

At base, the recognized occurrences are the root manifest override `1.6.1`
and root lock package `node_modules/smol-toml` at `1.6.1`. At candidate head,
both are `1.9.0`; the other three surfaces have no recognized `smol-toml`
carrier. The dependent `^1.4.2` edge in `cspell-config-lib` is a range
requirement, not a second installed version. The guard discovers direct,
nested, renamed-alias, override, and canonical-tarball lock identities rather
than relying on a text search alone.

## F_cutoff and A: advisory reconciliation

Snapshot interval: **2026-09-23T08:23:32Z–2026-09-23T08:23:36Z**. The retained
inputs are the maintainer's four published security advisories, the three
then-visible GitHub Advisory Database entries, authenticated repository
[Dependabot alert #292](https://github.com/Katsiarynakavaleuskaya/PulsePlate/security/dependabot/292),
and npm registry metadata for `1.9.0`. Alert #292 was open and named only
GHSA-7w5x-hrqm-74c2. The fourth advisory was published upstream but was not
yet visible in the general database at this cutoff. Its range and patch are
included conservatively; an independent primary corroboration claim is **not**
made. The release notes corroborate the selected version, including its
`null`-prototype object change, but do not replace that source limitation.

| Advisory | Reconciled affected stable versions | Base `1.6.1` | Head `1.9.0` |
| --- | --- | --- | --- |
| [GHSA-r4xh-jqrq-34v2](https://github.com/squirrelchat/smol-toml/security/advisories/GHSA-r4xh-jqrq-34v2) | `<=1.8.0`; patch `1.9.0`; upstream only at cutoff | affected | outside |
| [GHSA-7w5x-hrqm-74c2](https://github.com/advisories/GHSA-7w5x-hrqm-74c2) | `<=1.7.0`; patch `1.7.1` | affected | outside |
| [GHSA-v3rj-xjv7-4jmq](https://github.com/advisories/GHSA-v3rj-xjv7-4jmq) | `<1.6.1` (upstream `<=1.6.0`); patch `1.6.1` | outside | outside |
| [GHSA-pqhp-25j4-6hq9](https://github.com/advisories/GHSA-pqhp-25j4-6hq9) | `<=1.3.0`; patch `1.3.1` | outside | outside |

Thus `A`, the exact base-applicable subset of `F_cutoff`, is the first two
rows. The latter two have independently comparable `1.6.1` base occurrences
outside their ranges and remain in the universal head check. All four
affected ranges are encoded at `tests/test_root_npm_dependency_guards.py:35`.
This bounded claim is about those four dated advisories, not immunity to
undisclosed or future vulnerabilities.

Retained ignored input SHA-256 values:

| Input under `artifacts/orchestration/dep-sec-02/` | SHA-256 |
| --- | --- |
| `upstream-advisories.json` | `e5239fc92e4a6f7133ca7618bc7968dc8847c5e72fcc21f4ce35149abdee6a54` |
| `github-advisories.json` | `8149bef815fc7a672ca38b002a9d19d4332ad423b9daabaed8d986fb834a995a` |
| `dependabot-alert-292.json` | `40403e303ff6ed6535c12af9f1d695c48e4178189111f546d08f8634c19b0c18` |
| `npm-registry-1.9.0.json` | `df5ba24df816b1b448ac5eef78e5e7a05fa8d94c1b7bc0671f3aa3f0c9461b27` |

## R: one authored action and replay-proven resolver closure

Node `v24.18.1` and npm `11.16.0` ran
`npm install --package-lock-only --ignore-scripts --no-audit --no-fund`.
Two independent clean directories were seeded with the exact base manifest
and lock bytes, each receiving only the authorized override replacement before
that command. Both outputs are byte-identical to the candidate files. The
complete recursive dependency JSON delta contains exactly four leaves:

| File and JSON pointer | Before | After | Class |
| --- | --- | --- | --- |
| `package.json` `/overrides/smol-toml` | `1.6.1` | `1.9.0` | authored `I_R` |
| `package-lock.json` `/packages/node_modules~1smol-toml/version` | `1.6.1` | `1.9.0` | resolver `C_R` |
| `package-lock.json` `/packages/node_modules~1smol-toml/resolved` | `https://registry.npmjs.org/smol-toml/-/smol-toml-1.6.1.tgz` | `https://registry.npmjs.org/smol-toml/-/smol-toml-1.9.0.tgz` | resolver `C_R` |
| `package-lock.json` `/packages/node_modules~1smol-toml/integrity` | `sha512-dWUG8F5sIIARXih1DTaQAX4SsiTXhInKf1buxdY9DIg4ZYPZK5nGM1VRIYmEbDbsHt7USo99xSLFu5Q1IqTmsg==` | `sha512-hpd+HLON7HdZXqYchMM/+LaTTbdK0AU3NngIJ4KVyWbY9bfQqdL9cD+4yf6dUoU2Ap4VsU0JkQi6FxAI1B2mXQ==` | resolver `C_R` |

The new tarball URL and integrity match the retained npm registry metadata.
No other dependency identity, file, or dependency JSON field changed. The
ignored `surface-inventory.json` and `resolver-delta.json` retain the complete
machine-readable comparison; both replay directories retain the actual output
bytes until archive verification.

## P: current-head safety and consumer compatibility

At this candidate head, all recognized `smol-toml` manifest and lock
occurrences are exact stable `1.9.0`, outside every member of `F_cutoff`.
`tests/test_root_npm_dependency_guards.py:930` requires every currently
tracked occurrence to be advisory-comparable and checks canonical registry
tarball identity, version equality, and nonempty integrity. Existing global
manifest opaque-source and lock provenance guards remain active. New negative
tests reject `1.7.1`, `1.8.0`, nested/alias carriers, malformed version and
foreign or mismatched tarballs; a safe `1.9.0` manifest/lock pair passes.
An opaque future carrier that escapes the bounded recognizer is unresolved,
not evidence of safety.

Focused root and frontend dependency guard suites passed. Worktree-local
`npm ci --no-audit --no-fund` installed 135 packages; `npm ls smol-toml --all`
showed `cspell@9.2.1 -> cspell-config-lib@9.2.1 -> smol-toml@1.9.0 overridden`.
The installed `createReaderWriter().readConfig()` loaded a valid small TOML
file, preserved its language and words settings with a `null` prototype,
serialized them, and rejected malformed TOML promptly. Initial smoke harness
attempts assumed an exported package JSON and a `ParseError` class name;
both assumptions were corrected after inspecting the actual package export
and reader error wrapper. Those failures were test-harness errors, not an
observed CSpell regression. No unbounded denial-of-service proof of concept
was executed.

A separate installed CSpell CLI smoke used a task-local `cspell.config.toml`
with `version = "0.2"` and `words = ["florblax"]` on separate lines, then
linted an input containing `florblax` through `node_modules/.bin/cspell lint`.
It exited 0. The first CLI attempt exited 1 because the shell-created
fixture joined the two settings on one line; `readConfig()` identified that
fixture as invalid TOML. Correcting the newline made the CLI pass. This was
a test-fixture error, not a CSpell compatibility regression.

This is a local implementation checkpoint. Premortem, Runner, post-open role
review, exact-material self-review, required current-head CI/security/diff
coverage, mapping/seal, strict authenticated readiness, review wait window,
human merge approval, merged-main checks, and Drive readback remain separate
claims. Do not dismiss alert #292 manually. If a later material change occurs,
repeat the affected checks and update this evidence. A post-merge revert of
this security update would restore vulnerability debt and requires a separate
owner decision and explicit tracking.
