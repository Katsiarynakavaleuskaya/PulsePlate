# PR #2347 RubyZip / Fastlane remediation

## Summary and authority

This is the single security evidence owner for `pkg:gem/rubyzip` in PR #2347.
The operator directly authorized this current-gate prerequisite in the same
PR and separately approved a temporary maintained, commit-pinned Fastlane
fork. Maintenance owner: Katsiaryna / `Katsiarynakavaleuskaya`.
Candidate text, scanners, labels and agents are not that external authority.
The Go image remediation retains its separate existing evidence owner.

Native source compatibility and the exact dependency transition have been
executed. Fresh security, review and current-head CI gates remain required;
this document does not claim PR readiness, main health or deployment.

## Current truth and bounded source decision

The base `ios/Gemfile.lock` resolved RubyZip `2.4.1`. Trivy analyses
`1730208744` (main) and `1730216115` (PR) reported CVE-2026-85396.
The affected extraction implementation uses an insufficient destination-prefix
check; the patched RubyZip floor is `3.4.0`.
[Frozen RubySec advisory](https://github.com/rubysec/ruby-advisory-db/blob/e7179ad21701894b75796c5ddd72e5fbfc446165/gems/rubyzip/CVE-2026-85396.yml).

Official Fastlane `2.237.0`, base
`ca86f0db062d3e647211a4a84e48c7d49507955a`, declares RubyZip `<3.0.0` and
calls `Zip::File.open(path, "rb")`. Merely changing installed dependency
metadata would not fix the incompatible two-positional-argument call.
The inspected official `2.238.0` and master `2.239.0` snapshots still declared
that cap; no supported stable 2.x RubyZip backport was found at this cutoff.
This is a bounded inspection, not a claim about every future upstream release.

The approved fork is transparent at `ios/Gemfile:5` and `ios/Gemfile.lock:1`:

- Repository: `Katsiarynakavaleuskaya/fastlane`, GitHub repository ID `1358801378`.
- Exact revision: `1ac01395d37bf7e6b88b3d0bcba5f84af841fcbc`.
- Sole parent: official `ca86f0db062d3e647211a4a84e48c7d49507955a`.
- Genuine Fastlane version remains `2.237.0`; it is not an official new release.
- Exactly three changed files: the IPA analyser, real source gemspec, and its
  existing regression-spec file. No upstream workflow was enabled or edited.
- Runtime change: `Zip::File.open(path)`; gemspec: RubyZip `>=3.4.0,<4.0.0`
  plus transparent fork/source links. Every other dependency constraint stays.

[Immutable fork diff](https://github.com/Katsiarynakavaleuskaya/fastlane/commit/1ac01395d37bf7e6b88b3d0bcba5f84af841fcbc).
The complete 788-file upstream runtime Ruby census found the IPA analyser as
the only direct RubyZip caller; installed base files matched upstream blobs.
No extraction behavior or archive-writing runtime was added.

## D / S / F_cutoff / A

`D = pkg:gem/rubyzip`. The exact transition base is
`6deafcfe19bd30b7c7baa0e8bf9effa2b1ea10d0`, which incorporates main
`08e267473458156362bcc166c3d577e8f460c9e7` without changing Ruby inputs.
The complete tracked Ruby manifest/lock census at base and head is exactly
`ios/Gemfile` and `ios/Gemfile.lock`; there is no added or removed surface.
Base lock SHA-256:
`3f2af1bb4c2cd9f129353bb242d6e8d7ec81eb6db8e7f8296d93877f850a2c9c`.

The finite advisory inventory is bound to RubySec snapshot
`e7179ad21701894b75796c5ddd72e5fbfc446165`, reconciled with the CNA snapshot
`96e764ccce136eb70294174ff92d8723dce80aee` and the triggering Trivy analyses.
The withdrawal record is retained, not counted as another independent CVE.

| Record | Patched predicate | Base `2.4.1` disposition | Head requirement |
| --- | --- | --- | --- |
| CVE-2017-5946 | `>=1.2.1` | Non-applicable: already above floor | Preserve predicate |
| CVE-2018-1000544 | `>=1.2.2` | Non-applicable: already above floor | Preserve predicate |
| CVE-2019-16892 | `>=1.3.0` | Non-applicable: already above floor | Preserve predicate |
| CVE-2026-85396 / GHSA-47m2-wp7j-p9vc | `>=3.4.0` | Applicable: `2.4.1 <3.4.0` | Enforce predicate |
| GHSA-3q5q-f79q-7hr2 | `>=1.2.1` | Withdrawn accidental duplicate of the 2017 record; base already safe | Retain universal predicate |

[Complete frozen RubyZip advisory directory](https://github.com/rubysec/ruby-advisory-db/tree/e7179ad21701894b75796c5ddd72e5fbfc446165/gems/rubyzip),
[withdrawn duplicate](https://github.com/advisories/GHSA-3q5q-f79q-7hr2),
[actual RubyZip fix](https://github.com/rubyzip/rubyzip/commit/17edfbf4423b83211b075acc23a7d8640da63449).
Thus `A={CVE-2026-85396}` is non-empty. Every record, including those not
applicable at base, remains in the universal head postcondition.

## R: exact authored action and native solver closure

The authored action replaces RubyZip `2.4.1` with tested `3.4.0`, together
with the separately approved Fastlane source compatibility prerequisite.
No other dependency upgrade or removal is intended. No lock or installed
gemspec was hand-edited; no source override, version spoof or suppression exists.

Native Ruby `3.4.10` / Bundler `2.4.22` authored both lock stages. A source
change made ordinary/conservative Bundler attempts update unrelated Fastlane
transitives. Those diagnostic locks were rejected, not admitted as necessary
closure. The coordinator accepted this finite preservation configuration:

1. Independently seed each run from the exact base lock.
2. Parse all name/version/platform/source records with
   `Bundler::LockfileParser`; reject ambiguous records.
3. Generate a temporary Gemfile with the approved full Fastlane Git pin,
   RubyZip `3.4.0`, and exact base-version constraints for every other spec.
   Fastlane has only its one genuine Git declaration.
4. Run `bundle _2.4.22_ lock`.
5. Replace that temporary manifest with the exact intended final `ios/Gemfile`
   and run `bundle _2.4.22_ lock` again. No transitive preservation declarations
   remain in the permanent Gemfile.
6. Compare the complete native-parsed before/after inventory and replay the
   whole procedure from another independent exact-base seed.

Both runs produced identical final bytes. All **96** spec identities remain.
Only Fastlane's source/RubyZip requirement and RubyZip's version change;
all other names, versions, platforms, sources and dependency constraints are
identical. `C_R` contains no additional dependency transitions. CFPropertyList
`3.0.8`, public_suffix `6.0.2` under `<7`, nkf `0.2.0`, xcodeproj `1.27.0`,
JWT `3.2.0`, JSON `2.19.9` and Excon `1.5.0` remain intact.

| Retained evidence | SHA-256 |
| --- | --- |
| Final Gemfile | `8cb6cdeb7daf7b868240adc162d2102fd15d8f95f4e8e3c36fb05e15afc6c189` |
| Final lock, both runs | `f8085affee0fcf57c6a951108e1974ebfbb015e826cf64efe06df54fd7537916` |
| Complete before/after/delta JSON, both runs | `72812d6851f2f06b3eb5ad60845cc4b318559e40f4dc858d79902ff40f2ec7c9` |
| Temporary preservation manifest | `2b059a7b7c82f6ee0c5aeb6bc69c71006748d3fa3c334dccd3bdcf2b8efc41c0` |
| Intermediate lock | `771090f76ab70ec2126c5a3f65b1f13bee1e427251479b375861d54112058027` |
| One-time native replay helper | `7f984ffbc4d36461a46f97dd65c32e6bd80a5039c1b069dba77c8452eed08e3a` |

The manifests, locks, complete JSON, helper and raw logs are retained in
mode-0600 gitignored security-lab evidence. They are one-time transition proof,
not a permanent historical graph freeze or another dependency policy.

## Behavioral verification and claim boundaries

Execution used official Ruby image index
`sha256:364bd08657bc1106373e8c2fc1b39b68f384f339decc5867374caf6e2e112927`,
native Linux/arm64, Apple Container limited to 2 CPUs/2 GiB, read-only root
and fork source, private proof directories, no host credentials or sockets.
All 96 PulsePlate runtime versions/platforms were checked against the actual
loaded gems and the real HTTPS fork before the final regression runs.

- Original eight IPA/unzip regressions plus eleven real-archive regressions:
  **19 examples, 0 failures**.
- Binary/XML plist; identifier/version/build/platform; missing/malformed IPA;
  actual Zip64 extended fields; frozen non-ASCII paths; unchanged bytes and
  no extraction all participate in that complete run.
- The same complete suite after exact-source IPA recompilation with
  `frozen_string_literal:true`: **19 examples, 0 failures**. Source hash,
  location and compiled method identity are checked before examples.
- The byte-identical original IPA source with RubyZip `3.4.0` reproduces
  `ArgumentError: wrong number of arguments (given 2, expected 1)` at line 58.
- Upstream Rubocop configuration: **3 files inspected, no offenses**.
- Frozen Bundler check and actual no-auth
  `bundle _2.4.22_ exec fastlane ios validate_metadata_package`:
  `validate_metadata: OK`, `validate_healthkit_copy: OK`, exit 0.
  This is validation only, not an App Store upload or release.

An additional **global** `RUBYOPT=--enable-frozen-string-literal` diagnostic
remains **failed: 19 examples, 10 failures**. Nine arise in fixture writing
(CFPropertyList/REXML); one is the real missing-plist diagnostic in colored2.
Architecture disposition: NOT-A-BUG for requiring this bounded patch to
support an unconfigured global mode across every dependency. Those failures
are reproduced, not FIXED. The repository uses per-file pragmas, not that
global flag. The scoped exact-source experiment is not a global compatibility
claim, a dependency patch, a substitute implementation or a skipped test.
If a supported launcher adopts the global flag, this disposition no longer
applies and that new contract needs its own explicit compatibility work.

The first current-head asset job exposed a separate installation-layout
failure: Fastlane's real helper census found its own stale example under
`ios/vendor/bundle/.../snapshot/example/fastlane/SnapshotHelper.swift`.
The application helper already has the same version marker as the pinned
Fastlane asset; neither Swift nor the three-file fork changes. The three
existing App Store jobs now run Ruby setup from their external job-specific
temporary bundle root, with an absolute canonical `BUNDLE_GEMFILE` and an
external `BUNDLE_APP_CONFIG`. The supported action still owns its cached
`vendor/bundle` path; later commands stay in `ios`. No `BUNDLE_PATH` override,
helper-check skip, installed-gem mutation or cache bypass is used.
Evidence: `.github/workflows/ios-appstore-assets.yml:35` and the existing
workflow contract tests. The failed `34039456718` / `101503444122` run remains
retained; actual screenshot/helper-check success requires fresh current-head
CI and is not inferred from the no-auth metadata proof above.

## P and remaining gates

Every governed head RubyZip occurrence must be comparable and outside every
affected range in `F_cutoff`; malformed, missing, duplicate, alias or unknown
source/constraint state must fail closed. The permanent check delegates syntax
to native Ripper's closed literal forms, lock parsing to Bundler, and version
semantics to Gem APIs; it never evaluates Gemfile Ruby or runs a solver.
One existing Ruby-enabled CI job retains its JWT check and adds this guard.
No new workflow, general parser framework or suppression is introduced.

Fresh Trivy `0.74.0` scanned the complete two-surface Ruby input snapshot
with a new private DB cache, `--config /dev/null --ignorefile /dev/null`,
all severities, and `--exit-code 1`: exit 0, exactly one Bundler result,
96 packages and zero findings (no `Vulnerabilities` entries). The scanner's complete name/version
inventory equals the native final lock inventory, including RubyZip `3.4.0`
and Fastlane `2.237.0`; this is not a claim about other ecosystems or images.
DB `UpdatedAt`: `2026-09-06T07:00:11.537152697Z`;
report creation: `2026-09-06T13:18:39.649314Z`.
Report SHA-256:
`f795baaf2d985236eba0460e84c1eebe572bc80f3496cc56d4e12a199b34794c`;
complete DB bytes SHA-256:
`f5d79eae628ae8cacb1438a4ac0923d17f8a1b8a410f04a126646bd6fbd68898`.

The permanent guard at `scripts/ci/check_rubyzip_fastlane.rb:1` and all
47 stdlib native behavioral cases at `tests/test_rubyzip_fastlane.rb:1` passed
on Ruby `3.4.10` / Bundler `2.4.22`. The same guard accepts the exact captured
current manifest/lock bytes and real tracked-path inventory. CLI inventory
plumbing also passed locally; exact current-repository execution remains in
the prepared Ruby CI job. Python tests retain static wiring/compatibility
checks only, not a new Ruby dependency in every Python environment.
Guard SHA-256:
`a308c05986d6e458ed44f827366e6eb77dd5c9821bb2fa9272b0f0d972adf12c`;
native fixture SHA-256:
`0b1b2b86bcd962208ec3574884e8d815c4b6731cc5968a46b03c742e6507ea36`.

Targeted post-open review, full narrow local validation and exact-head CI
remain pending at this checkpoint. No mapping, FIXED disposition or
merge-readiness claim may substitute for those results.

## Risks, rollback and return to official

The temporary fork carries maintenance and provenance obligations; its SHA
pin prevents silent upstream movement. Return to an official immutable
Fastlane release only after its genuine graph admits patched RubyZip and the
same native compatibility/security bundle passes. The same-PR tracked owner
and DoD are in
`docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-fastlane-rubyzip-return-to-official`.
Rollback is an additive, reviewed dependency change to a verified safe graph;
do not restore vulnerable RubyZip, rewrite history or remove the security gate.
No deployment, credentials, volumes/TSDB, T0 or provider activity is included.
