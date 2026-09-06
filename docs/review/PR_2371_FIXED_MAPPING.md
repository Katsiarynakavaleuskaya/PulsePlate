# PR 2371 — Review Governance

Review-Seal-Version: v1

## Lane Start Provenance
Packet: `artifacts/orchestration/task_packets/132db9936aa1.json`

## Experiment Runner Evidence
Artifact: `artifacts/orchestration/experiments/results/pr2371-final-material-06f9-oracle-result.json`

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

Disposition: FIXED
Commit: 937db0926f257684cc57ef39b1dcf78589643aeb
Evidence: tests/test_frontend_dependency_guards.py:1490 and tests/test_frontend_dependency_guards.py:2752; selector compatibility is checked for every demand on its own lock surface; focused suite 173 passed
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2371#discussion_r3911578160 -> 937db0926f257684cc57ef39b1dcf78589643aeb

Disposition: FIXED
Commit: 937db0926f257684cc57ef39b1dcf78589643aeb
Evidence: tests/test_frontend_dependency_guards.py:2551; the permanent guard evaluates the current tracked surface universe without freezing historical carrier equality
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2371#discussion_r3911621759 -> 937db0926f257684cc57ef39b1dcf78589643aeb

Disposition: FIXED
Commit: 937db0926f257684cc57ef39b1dcf78589643aeb
Evidence: tests/test_frontend_dependency_guards.py:1484 and tests/test_frontend_dependency_guards.py:2658; SHA-512 SRI is base64-decoded and required to contain a 64-byte digest
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2371#discussion_r3911621767 -> 937db0926f257684cc57ef39b1dcf78589643aeb

Disposition: FIXED
Commit: 937db0926f257684cc57ef39b1dcf78589643aeb
Evidence: tests/test_frontend_dependency_guards.py:2557 and tests/test_frontend_dependency_guards.py:2589; exact expected and applicable advisory identities are asserted independently
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2371#discussion_r3911621776 -> 937db0926f257684cc57ef39b1dcf78589643aeb

Disposition: FIXED
Commit: 937db0926f257684cc57ef39b1dcf78589643aeb
Evidence: tests/test_frontend_dependency_guards.py:2773 and tests/test_frontend_dependency_guards.py:2800; only exact boolean optional peer metadata permits absence and malformed or mandatory forms fail closed
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2371#discussion_r3911621782 -> 937db0926f257684cc57ef39b1dcf78589643aeb

Disposition: FIXED
Commit: 79a2dc7b059bf4530a4ec910743571167da84fda
Evidence: docs/security/FRONTEND_BROWSERSLIST_REMEDIATION_CLASS.md:197; the replay reconstructs package.json and package-lock.json from the exact frozen base via git show before invoking the resolver
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2371#discussion_r3911627835 -> 79a2dc7b059bf4530a4ec910743571167da84fda

Disposition: FIXED
Commit: 47fea5211b835a8ed5c0cfad4dc207d130b3900b
Evidence: tests/test_frontend_dependency_guards.py:569, tests/test_frontend_dependency_guards.py:2776, and tests/test_frontend_dependency_guards.py:2793; Node ancestor lookup rejects an unrelated sibling and honors nearest-occurrence precedence; focused suite 175 passed
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2371#discussion_r3912113765 -> 47fea5211b835a8ed5c0cfad4dc207d130b3900b

Disposition: FIXED
Commit: 684409902cf3a05ff1badbac3b27fac6fd758c1e
Evidence: tests/test_frontend_dependency_guards.py:469 and tests/test_frontend_dependency_guards.py:2799; malformed lock package records and non-object dependency containers fail closed; focused suite 179 passed
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2371#discussion_r3912338088 -> 684409902cf3a05ff1badbac3b27fac6fd758c1e

Disposition: FIXED
Commit: b6450b4c661512184334c9daf52ff57b3cf30115
Evidence: docs/review/PR_2371_FIXED_MAPPING.md; the mapping-only commit after the comment resealed material head a1ff72da36ba617d423879fc8f6e9d7158199022 with digest sha256:1d1d14eb8f179789368bb828bc49607665d9b3d95ea16172f037d5d9064b14c4
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2371#discussion_r3912338102 -> b6450b4c661512184334c9daf52ff57b3cf30115

Disposition: FIXED
Commit: 684409902cf3a05ff1badbac3b27fac6fd758c1e
Evidence: tests/test_frontend_dependency_guards.py:1478 and tests/test_frontend_dependency_guards.py:2813; a root lock target demand is rejected even with a safe installed occurrence; focused suite 179 passed
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2371#discussion_r3912338112 -> 684409902cf3a05ff1badbac3b27fac6fd758c1e

Disposition: FIXED
Commit: 684409902cf3a05ff1badbac3b27fac6fd758c1e
Evidence: tests/test_frontend_dependency_guards.py:1481 and tests/test_frontend_dependency_guards.py:2840; renamed npm aliases and registry-tarball demands are rejected instead of resolving through the canonical path; focused suite 179 passed
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2371#discussion_r3912451752 -> 684409902cf3a05ff1badbac3b27fac6fd758c1e

Disposition: FIXED
Commit: 0bd2df4dbb8f004114b28e9fe14fbf0fa6232542
Evidence: tests/test_frontend_dependency_guards.py:1475 and tests/test_frontend_dependency_guards.py:2815; both empty and dot root lock keys are rejected with safe installed occurrences; focused suite 180 passed
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2371#discussion_r3912644864 -> 0bd2df4dbb8f004114b28e9fe14fbf0fa6232542

Disposition: FIXED
Commit: 792bcc8bd06719c1e5c71b2a15802f2b0468a912
Evidence: tests/test_frontend_dependency_guards.py:1274 and tests/test_frontend_dependency_guards.py:2836; malformed manifest dependency, override, bundled, and workspace containers fail closed; focused suite 187 passed
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2371#discussion_r3912690951 -> 792bcc8bd06719c1e5c71b2a15802f2b0468a912

Disposition: FIXED
Commit: 792bcc8bd06719c1e5c71b2a15802f2b0468a912
Evidence: tests/test_frontend_dependency_guards.py:1297 and tests/test_frontend_dependency_guards.py:2852; tracked target-named workspace members are rejected as manifest carriers; focused suite 187 passed
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2371#discussion_r3912947938 -> 792bcc8bd06719c1e5c71b2a15802f2b0468a912

Disposition: FIXED
Commit: 1694db0a6d367f58380e6f623e363c5a73ca96e2
Evidence: docs/security/FRONTEND_BROWSERSLIST_REMEDIATION_CLASS.md:167 and docs/security/DEPENDABOT_ALERT_INVENTORY.md:39; both anchors now point to the actual boundary and all-occurrence guard lines
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2371#discussion_r3912947942 -> 1694db0a6d367f58380e6f623e363c5a73ca96e2

Disposition: FIXED
Commit: 792bcc8bd06719c1e5c71b2a15802f2b0468a912
Evidence: tests/test_frontend_dependency_guards.py:489 and tests/test_frontend_dependency_guards.py:3083; same-name optionalDependencies precedence is applied before selector validation; focused suite 187 passed
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2371#discussion_r3912947949 -> 792bcc8bd06719c1e5c71b2a15802f2b0468a912

Disposition: FIXED
Commit: d2b34cfbd301ad3dc9c4a854732ee8d9ad9aa6e1
Evidence: docs/security/FRONTEND_BROWSERSLIST_REMEDIATION_CLASS.md:35 and docs/security/FRONTEND_BROWSERSLIST_REMEDIATION_CLASS.md:41 rebind the synchronized base and reachable material head; the regenerated current mapping seal binds the same live material projection
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2371#discussion_r3913104631 -> d2b34cfbd301ad3dc9c4a854732ee8d9ad9aa6e1

Disposition: FIXED
Commit: d2b34cfbd301ad3dc9c4a854732ee8d9ad9aa6e1
Evidence: docs/security/FRONTEND_BROWSERSLIST_REMEDIATION_CLASS.md:41 binds reachable material head f159534e0160bff57ec94985b51191d309f6bb32 after base synchronization; no pre-merge squash SHA is claimed
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2371#discussion_r3913469111 -> d2b34cfbd301ad3dc9c4a854732ee8d9ad9aa6e1

Disposition: FIXED
Commit: f159534e0160bff57ec94985b51191d309f6bb32
Evidence: docs/security/FRONTEND_BROWSERSLIST_REMEDIATION_CLASS.md:216 defines the timestamped registry cutoff and immutable lock receipt, and requires fresh admission for later registry output
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2371#discussion_r3913469127 -> f159534e0160bff57ec94985b51191d309f6bb32

Disposition: FIXED
Commit: f159534e0160bff57ec94985b51191d309f6bb32
Evidence: docs/security/FRONTEND_BROWSERSLIST_REMEDIATION_CLASS.md:82 and tests/test_frontend_dependency_guards.py:2711 bind the recomputed 4a0b408d receipt digest to the exact retained advisory JSON
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2371#discussion_r3913469139 -> f159534e0160bff57ec94985b51191d309f6bb32

Disposition: FIXED
Commit: 4aa1f47c65407e5e37e5c4cde1d94da9f5ac08ad
Evidence: tests/test_frontend_dependency_guards.py:1283 and tests/test_frontend_dependency_guards.py:2985; recursive workspace globs fail closed instead of creating executable absence; focused suite 194 passed
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2371#discussion_r3913604731 -> 4aa1f47c65407e5e37e5c4cde1d94da9f5ac08ad

Disposition: FIXED
Commit: 4aa1f47c65407e5e37e5c4cde1d94da9f5ac08ad
Evidence: tests/test_frontend_dependency_guards.py:2787 binds retained ecosystem, package, normalized ranges, first-patched versions, advisory IDs, and receipt digest; focused suite 194 passed
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2371#discussion_r3913842489 -> 4aa1f47c65407e5e37e5c4cde1d94da9f5ac08ad

Disposition: FIXED
Commit: 4aa1f47c65407e5e37e5c4cde1d94da9f5ac08ad
Evidence: tests/test_frontend_dependency_guards.py:1687 and tests/test_frontend_dependency_guards.py:3013 reject symbolic-link target lock records; focused suite 194 passed
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2371#discussion_r3913842499 -> 4aa1f47c65407e5e37e5c4cde1d94da9f5ac08ad

Disposition: FIXED
Commit: 08c1e90e47dcf35bcfd41e36b981fe8400718ae1
Evidence: tests/test_frontend_dependency_guards.py:1340 and tests/test_frontend_dependency_guards.py:2930 accept boolean bundle declarations while continuing target discovery; focused suite 194 passed
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2371#discussion_r3914064058 -> 08c1e90e47dcf35bcfd41e36b981fe8400718ae1

Disposition: FIXED
Commit: 08c1e90e47dcf35bcfd41e36b981fe8400718ae1
Evidence: tests/test_frontend_dependency_guards.py:418 and tests/test_frontend_dependency_guards.py:3172 recognize Git and GitHub target sources in manifest and lock demands; focused suite 194 passed
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2371#discussion_r3915247265 -> 08c1e90e47dcf35bcfd41e36b981fe8400718ae1

Disposition: FIXED
Commit: 3b34e69d02fa3a936e3e2f81078af05b328dec30
Evidence: docs/security/FRONTEND_BROWSERSLIST_REMEDIATION_CLASS.md:41 binds the exact reachable delegated-guard commit a51a14f9f5c986f8e9a676f5d1add97746252a39; git cat-file and ancestry checks pass
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2371#discussion_r3915400734 -> 3b34e69d02fa3a936e3e2f81078af05b328dec30

Disposition: FIXED
Commit: a51a14f9f5c986f8e9a676f5d1add97746252a39
Evidence: tests/test_frontend_dependency_guards.py:1486 delegates all opaque Git source classes to the installed-npm classifier; package-specific git+file parsing was removed; focused file 177 passed
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2371#discussion_r3915400750 -> a51a14f9f5c986f8e9a676f5d1add97746252a39

Disposition: FIXED
Commit: a51a14f9f5c986f8e9a676f5d1add97746252a39
Evidence: tests/test_frontend_dependency_guards.py:1486 rejects every non-registry local or workspace source through the single installed-npm classifier; bare-path heuristics were removed; focused file 177 passed
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2371#discussion_r3915400761 -> a51a14f9f5c986f8e9a676f5d1add97746252a39

Disposition: FIXED
Commit: a51a14f9f5c986f8e9a676f5d1add97746252a39
Evidence: tests/test_frontend_dependency_guards.py:1527 rejects duplicate GAD receipt keys before canonical hashing; focused file 177 passed
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2371#discussion_r3915400764 -> a51a14f9f5c986f8e9a676f5d1add97746252a39

Disposition: FIXED
Commit: a51a14f9f5c986f8e9a676f5d1add97746252a39
Evidence: tests/test_frontend_dependency_guards.py:1486 delegates hosted Git shorthands to npm-package-arg and fails closed on every non-version/range source; npm 11.16.0 classifies GitLab and Bitbucket shorthands as opaque
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2371#discussion_r3915698591 -> a51a14f9f5c986f8e9a676f5d1add97746252a39

Disposition: FIXED
Commit: a51a14f9f5c986f8e9a676f5d1add97746252a39
Evidence: tests/test_frontend_dependency_guards.py:1373 delegates peer placement and required-edge validity to hermetic npm ls --all --package-lock-only instead of handwritten ancestor lookup
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2371#discussion_r3915698598 -> a51a14f9f5c986f8e9a676f5d1add97746252a39

Disposition: FIXED
Commit: 604ef0e50b8a48cd8fea3faf9e4cda4bb1bd2a49
Evidence: docs/security/DEPENDABOT_ALERT_INVENTORY.md:39 now points to tests/test_frontend_dependency_guards.py:1486; Docs Phase 1 gates pass
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2371#discussion_r3918818444 -> 604ef0e50b8a48cd8fea3faf9e4cda4bb1bd2a49

Disposition: FIXED
Commit: c39ab21fb98495fc5a24bda87fbf2992795615cb
Evidence: tests/test_frontend_dependency_guards.py:1544 and tests/test_frontend_dependency_guards.py:2842 require each root lock dependency map to exactly match its same-root tracked manifest and reject an invented Browserslist root demand; the focused suite passes.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2371#discussion_r3919022426 -> c39ab21fb98495fc5a24bda87fbf2992795615cb

Disposition: FIXED
Commit: c39ab21fb98495fc5a24bda87fbf2992795615cb
Evidence: tests/test_frontend_dependency_guards.py:1657 and tests/test_frontend_dependency_guards.py:2865 admit only lockfileVersion 3 and reject the version-2 compatibility-tree ambiguity; the focused suite passes.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2371#discussion_r3919022436 -> c39ab21fb98495fc5a24bda87fbf2992795615cb

Disposition: FIXED
Commit: c39ab21fb98495fc5a24bda87fbf2992795615cb
Evidence: tests/test_frontend_dependency_guards.py:1458 and tests/test_frontend_dependency_guards.py:3051 load every governed npm JSON surface with duplicate-member rejection and exercise a duplicate packages-key control; the focused suite passes.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2371#discussion_r3919022439 -> c39ab21fb98495fc5a24bda87fbf2992795615cb

Disposition: FIXED
Commit: c39ab21fb98495fc5a24bda87fbf2992795615cb
Evidence: tests/test_frontend_dependency_guards.py:3267 derives the applicable Browserslist advisory set by evaluating the governed base version against every reconciled affected range and requires exact equality; all boundary controls pass.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2371#discussion_r3919022444 -> c39ab21fb98495fc5a24bda87fbf2992795615cb

Disposition: FIXED
Commit: d1341f488c1262f889a89f820623d1b3ca92595b
Evidence: docs/security/FRONTEND_BROWSERSLIST_REMEDIATION_CLASS.md:724-780; exact base, prior candidate, current default JSON, MODERATE, and HIGH commands are separate and carry their real exit/output claims
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2371#discussion_r3919121658 -> d1341f488c1262f889a89f820623d1b3ca92595b

Disposition: FIXED
Commit: 61897ef2a05dd4f621e961b69ff054588177987b
Evidence: frontend/package-lock.json:8938 and tests/test_frontend_dependency_guards.py:214; qs is an exact authorized batch target, resolves 6.16.0, and is included in the permanent conjunctive postcondition
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2371#discussion_r3919121667 -> 61897ef2a05dd4f621e961b69ff054588177987b

Disposition: FIXED
Commit: 5c164929833b17935a5e67cba12d51ce8b4d5557
Evidence: docs/security/FRONTEND_BROWSERSLIST_REMEDIATION_CLASS.md:28-45; the owner binds synchronized base 863d16ea and reachable dependency/resolver material 6897a711
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2371#discussion_r3919201730 -> 5c164929833b17935a5e67cba12d51ce8b4d5557

Disposition: FIXED
Commit: 939a5be9f8ccdbe4c8dbca8c8d9b8787bee786f1
Evidence: tests/test_frontend_dependency_guards.py:3503 and tests/test_frontend_dependency_guards.py:3508; declared count, raw list length, dictionary cardinality, and exact advisory identities must all agree before projection
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2371#discussion_r3919201734 -> 939a5be9f8ccdbe4c8dbca8c8d9b8787bee786f1

Disposition: FIXED
Commit: 683bab5a34e06982e3b2ffcfb0d2ba12abf919be
Evidence: tests/test_frontend_dependency_guards.py:1609 and tests/test_frontend_dependency_guards.py:3215 reject true or malformed inBundle metadata for both authorized targets; the complete focused suite reports 233 passed.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2371#discussion_r3933716314 -> 683bab5a34e06982e3b2ffcfb0d2ba12abf919be

Disposition: FIXED
Commit: 683bab5a34e06982e3b2ffcfb0d2ba12abf919be
Evidence: docs/security/FRONTEND_BROWSERSLIST_REMEDIATION_CLASS.md:837 and docs/security/FRONTEND_BROWSERSLIST_REMEDIATION_CLASS.md:840 run through the repository frontend wrapper, pin the frontend prefix, and install before npm explain; Docs Phase 1 passes.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2371#discussion_r3933716321 -> 683bab5a34e06982e3b2ffcfb0d2ba12abf919be

Disposition: FIXED
Commit: e8b30562978614708f7c02b15ed79b9eb2bea0dc
Evidence: tests/test_frontend_dependency_guards.py:3434 binds the retained receipt to the exact externally confirmed operator_authorization value recorded at docs/security/FRONTEND_BROWSERSLIST_REMEDIATION_CLASS.md:103; both receipt controls and all 233 focused tests pass.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2371#discussion_r3936817069 -> e8b30562978614708f7c02b15ed79b9eb2bea0dc

Disposition: FIXED
Commit: 2288c20266d19427febb6f6789dcba880c21b411
Evidence: tests/test_frontend_dependency_guards.py:3500 and tests/test_frontend_dependency_guards.py:3625 bind the exact 13-record metadata projection and record schema; tests/test_frontend_dependency_guards.py:3639 and tests/test_frontend_dependency_guards.py:3648 enforce CVE, severity, and canonical timestamp semantics; all 233 focused tests pass.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2371#discussion_r3937722710 -> 2288c20266d19427febb6f6789dcba880c21b411

Disposition: FIXED
Commit: 54662fd8f83f19dcf9b89dfe509ee0912893a82b
Evidence: tests/test_frontend_dependency_guards.py:3665 requires the exact four-key schema for every retained vulnerability row; all 24 rows and the complete 233-test focused suite pass.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2371#discussion_r3937949484 -> 54662fd8f83f19dcf9b89dfe509ee0912893a82b

Disposition: FIXED
Commit: 54662fd8f83f19dcf9b89dfe509ee0912893a82b
Evidence: tests/test_frontend_dependency_guards.py:3700 requires non-boolean integer exit codes and nonnegative exact-integer severity metrics while the existing whole-root equality retains exact keys and values; the focused suite passes.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2371#discussion_r3937949489 -> 54662fd8f83f19dcf9b89dfe509ee0912893a82b

Disposition: FIXED
Commit: 54662fd8f83f19dcf9b89dfe509ee0912893a82b
Evidence: tests/test_frontend_dependency_guards.py:3677 validates every retained first_patched_version through the existing exact stable npm SemVer parser before exact range/version projection; the focused suite passes.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2371#discussion_r3937949495 -> 54662fd8f83f19dcf9b89dfe509ee0912893a82b

Disposition: FIXED
Commit: 63acf11e2765c5aed9c055d91aa735d9166be494
Evidence: tests/test_frontend_dependency_guards.py:1667 rejects true or malformed hasShrinkwrap on every lock record before executable absence, while tests/test_frontend_dependency_guards.py:2759 covers missing, exact-false, true, and non-boolean non-target carriers for both target/absence directions; all 233 focused tests pass.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2371#discussion_r3938084880 -> 63acf11e2765c5aed9c055d91aa735d9166be494

Disposition: FIXED
Commit: 63acf11e2765c5aed9c055d91aa735d9166be494
Evidence: tests/test_frontend_dependency_guards.py:3633 admits each batch target receipt through the existing exact-object helper with exactly the eight query, cutoff, pagination, count, observation, and records fields; all receipt controls pass.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2371#discussion_r3938084884 -> 63acf11e2765c5aed9c055d91aa735d9166be494

Disposition: FIXED
Commit: 3b34b8a4282566304ae04dc533f4312e91277d37
Evidence: tests/test_frontend_dependency_guards.py:3538 closes scanner_snapshot with _require_exact_object to exactly base_sha, observed_at, roots, terminal, and vulnerable_dependency_identities. The immutable scanner and batch digests are unchanged; the full 236-control focused suite passes.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2371#discussion_r3938280292 -> 3b34b8a4282566304ae04dc533f4312e91277d37

Disposition: FIXED
Commit: 3b34b8a4282566304ae04dc533f4312e91277d37
Evidence: tests/test_frontend_dependency_guards.py:1434 validates peer metadata object/field shape and exact optional booleans for every manifest and lock record; :1547 enforces root parity; :2782 proves optional true absence, required false/empty rejection, and malformed truthiness rejection for both identities. All-record :1674 inflation checks also reject shrinkwrap/bundled metadata before absence; 236 focused controls pass.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2371#discussion_r3938280296 -> 3b34b8a4282566304ae04dc533f4312e91277d37

Disposition: FIXED
Commit: 3b34b8a4282566304ae04dc533f4312e91277d37
Evidence: docs/security/FRONTEND_BROWSERSLIST_REMEDIATION_CLASS.md:861 preserves the historical receipt and records a newly executed four-root audit recipe over immutable base/head bytes: Node24.18.1/npm11.16.0, env-i whitelist, empty user/global configs, official npmjs registry, four includes, omit=[], workspaces/global=false. Raw results are base root0/frontend1 with exactly browserslist+qs and the same four applicable GHSA/ranges, candidate both0. This corroborates but does not recreate historical environment or widen authorization.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2371#discussion_r3938280301 -> 3b34b8a4282566304ae04dc533f4312e91277d37

Disposition: FIXED
Commit: 937db0926f257684cc57ef39b1dcf78589643aeb
Evidence: tests/test_frontend_dependency_guards.py:1490 and tests/test_frontend_dependency_guards.py:2752; all Sourcery actionable selector-demand feedback is fixed and the focused suite reports 173 passed
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2371#pullrequestreview-5086600531 -> 937db0926f257684cc57ef39b1dcf78589643aeb

Disposition: FIXED
Commit: 79a2dc7b059bf4530a4ec910743571167da84fda
Evidence: docs/security/FRONTEND_BROWSERSLIST_REMEDIATION_CLASS.md:197; CodeRabbit replay feedback is fixed by exact-base git-show reconstruction
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2371#pullrequestreview-5086658854 -> 79a2dc7b059bf4530a4ec910743571167da84fda

Disposition: FIXED
Commit: 47fea5211b835a8ed5c0cfad4dc207d130b3900b
Evidence: tests/test_frontend_dependency_guards.py:569 and tests/test_frontend_dependency_guards.py:2776; the top-level Codex review actionable is fixed by reachable Node ancestor resolution
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2371#pullrequestreview-5087247194 -> 47fea5211b835a8ed5c0cfad4dc207d130b3900b

Disposition: FIXED
Commit: 684409902cf3a05ff1badbac3b27fac6fd758c1e
Evidence: tests/test_frontend_dependency_guards.py:469, tests/test_frontend_dependency_guards.py:1478, and tests/test_frontend_dependency_guards.py:2799; all material actionables in this Codex review are fixed, while its stale-seal child is independently mapped to b6450b4c661512184334c9daf52ff57b3cf30115
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2371#pullrequestreview-5087511818 -> 684409902cf3a05ff1badbac3b27fac6fd758c1e

Disposition: FIXED
Commit: 684409902cf3a05ff1badbac3b27fac6fd758c1e
Evidence: tests/test_frontend_dependency_guards.py:1481 and tests/test_frontend_dependency_guards.py:2840; the renamed-demand actionable in this Codex review is fixed and the focused suite reports 179 passed
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2371#pullrequestreview-5087647678 -> 684409902cf3a05ff1badbac3b27fac6fd758c1e

Disposition: FIXED
Commit: 0bd2df4dbb8f004114b28e9fe14fbf0fa6232542
Evidence: tests/test_frontend_dependency_guards.py:1475 and tests/test_frontend_dependency_guards.py:2815; the dot-root actionable in this CodeRabbit review is fixed and the focused suite reports 180 passed
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2371#pullrequestreview-5087872989 -> 0bd2df4dbb8f004114b28e9fe14fbf0fa6232542

Disposition: FIXED
Commit: 792bcc8bd06719c1e5c71b2a15802f2b0468a912
Evidence: tests/test_frontend_dependency_guards.py:1274 and tests/test_frontend_dependency_guards.py:2836; the malformed-manifest actionable in this Codex review is fixed
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2371#pullrequestreview-5087928515 -> 792bcc8bd06719c1e5c71b2a15802f2b0468a912

Disposition: FIXED
Commit: 1694db0a6d367f58380e6f623e363c5a73ca96e2
Evidence: all actionables in this Codex review are mapped to 792bcc8bd06719c1e5c71b2a15802f2b0468a912 and the final anchor correction 1694db0a6d367f58380e6f623e363c5a73ca96e2
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2371#pullrequestreview-5088237740 -> 1694db0a6d367f58380e6f623e363c5a73ca96e2

Disposition: FIXED
Commit: d2b34cfbd301ad3dc9c4a854732ee8d9ad9aa6e1
Evidence: the base-sync seal review is closed by reachable base/material rebinding in d2b34cfbd301ad3dc9c4a854732ee8d9ad9aa6e1 and the regenerated current mapping seal
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2371#pullrequestreview-5088421876 -> d2b34cfbd301ad3dc9c4a854732ee8d9ad9aa6e1

Disposition: FIXED
Commit: d2b34cfbd301ad3dc9c4a854732ee8d9ad9aa6e1
Evidence: all owner-evidence actionables in this Codex review are fixed by f159534e0160bff57ec94985b51191d309f6bb32 and final owner rebinding d2b34cfbd301ad3dc9c4a854732ee8d9ad9aa6e1
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2371#pullrequestreview-5088834566 -> d2b34cfbd301ad3dc9c4a854732ee8d9ad9aa6e1

Disposition: FIXED
Commit: 4aa1f47c65407e5e37e5c4cde1d94da9f5ac08ad
Evidence: the recursive-workspace actionable in this Codex review is fixed by the closed workspace recognizer and focused suite 194 passed
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2371#pullrequestreview-5088988308 -> 4aa1f47c65407e5e37e5c4cde1d94da9f5ac08ad

Disposition: FIXED
Commit: 08c1e90e47dcf35bcfd41e36b981fe8400718ae1
Evidence: all material actionables in this Codex review are fixed by 4aa1f47c65407e5e37e5c4cde1d94da9f5ac08ad and final Git-source closure 08c1e90e47dcf35bcfd41e36b981fe8400718ae1
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2371#pullrequestreview-5089333086 -> 08c1e90e47dcf35bcfd41e36b981fe8400718ae1

Disposition: FIXED
Commit: 08c1e90e47dcf35bcfd41e36b981fe8400718ae1
Evidence: the boolean bundle actionable in this Codex review is fixed; its synthetic-squash child is independently dispositioned NOT-A-BUG
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2371#pullrequestreview-5089597982 -> 08c1e90e47dcf35bcfd41e36b981fe8400718ae1

Disposition: FIXED
Commit: 08c1e90e47dcf35bcfd41e36b981fe8400718ae1
Evidence: the Git-source actionable in this Codex review is fixed; its two synthetic-squash children are independently dispositioned NOT-A-BUG
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2371#pullrequestreview-5091067124 -> 08c1e90e47dcf35bcfd41e36b981fe8400718ae1

Disposition: FIXED
Commit: 3b34e69d02fa3a936e3e2f81078af05b328dec30
Evidence: all material actionables are closed by delegated-recognizer commit a51a14f9f5c986f8e9a676f5d1add97746252a39 and exact evidence correction 3b34e69d02fa3a936e3e2f81078af05b328dec30; focused file 177 passed
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2371#pullrequestreview-5091244039 -> 3b34e69d02fa3a936e3e2f81078af05b328dec30

Disposition: FIXED
Commit: a51a14f9f5c986f8e9a676f5d1add97746252a39
Evidence: both material actionables in this Codex review are closed by the single installed-npm source classifier and npm Arborist virtual-graph mechanism; focused file 177 passed
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2371#pullrequestreview-5091591215 -> a51a14f9f5c986f8e9a676f5d1add97746252a39

Disposition: FIXED
Commit: 604ef0e50b8a48cd8fea3faf9e4cda4bb1bd2a49
Evidence: the inventory-anchor actionable is fixed by 604ef0e50b8a48cd8fea3faf9e4cda4bb1bd2a49; the optional-edge suggestion is independently dispositioned NOT-A-BUG under canonical npm optional semantics
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2371#pullrequestreview-5095276115 -> 604ef0e50b8a48cd8fea3faf9e4cda4bb1bd2a49

Disposition: FIXED
Commit: 683bab5a34e06982e3b2ffcfb0d2ba12abf919be
Evidence: tests/test_frontend_dependency_guards.py:1609 and docs/security/FRONTEND_BROWSERSLIST_REMEDIATION_CLASS.md:837 close the bundled-record and reproducible-verification actionables; the synthetic-ref inline root has its separate evidence-backed NOT-A-BUG disposition.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2371#pullrequestreview-5112607476 -> 683bab5a34e06982e3b2ffcfb0d2ba12abf919be

Disposition: FIXED
Commit: e8b30562978614708f7c02b15ed79b9eb2bea0dc
Evidence: tests/test_frontend_dependency_guards.py:3434 closes the review's sole authorization-binding actionable; docs/security/FRONTEND_BROWSERSLIST_REMEDIATION_CLASS.md:462 retains the corrected duplicate-key evidence anchor and Docs Phase 1 passes.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2371#pullrequestreview-5116543068 -> e8b30562978614708f7c02b15ed79b9eb2bea0dc

Disposition: FIXED
Commit: 2288c20266d19427febb6f6789dcba880c21b411
Evidence: tests/test_frontend_dependency_guards.py:3500-3659 closes the review's sole retained-advisory metadata actionable with exact keys, exact per-GHSA tuples, closed severity/CVE formats, and calendar-valid UTC ordering; the focused suite and Docs Phase 1 pass.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2371#pullrequestreview-5117578783 -> 2288c20266d19427febb6f6789dcba880c21b411

Disposition: FIXED
Commit: 54662fd8f83f19dcf9b89dfe509ee0912893a82b
Evidence: tests/test_frontend_dependency_guards.py:3665-3704 closes the review's three row-schema, exact-version, and scanner-metric type actionables with one generic receipt hardening; all 233 focused tests and Docs Phase 1 pass.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2371#pullrequestreview-5117933693 -> 54662fd8f83f19dcf9b89dfe509ee0912893a82b

Disposition: FIXED
Commit: 63acf11e2765c5aed9c055d91aa735d9166be494
Evidence: tests/test_frontend_dependency_guards.py:1667 and tests/test_frontend_dependency_guards.py:3633 close the review's real shrinkwrap-inflation and target-receipt schema actionables; its synthetic reviewed-ref root has a separate evidence-backed NOT-A-BUG disposition.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2371#pullrequestreview-5118091280 -> 63acf11e2765c5aed9c055d91aa735d9166be494

Disposition: FIXED
Commit: 3b34b8a4282566304ae04dc533f4312e91277d37
Evidence: tests/test_frontend_dependency_guards.py:1434, :1674, :3538 and docs/security/FRONTEND_BROWSERSLIST_REMEDIATION_CLASS.md:861 collectively close all three actionable review roots: exact scanner schema, optional peer truthiness/root parity, and controlled registry/include/omit audit evidence. Original receipt/digests remain immutable. Published bundle inflation is also rejected without a new graph parser. Full236/Docs/preflight/consistency/make validate-changed and bounded role reviews pass.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2371#pullrequestreview-5118307578 -> 3b34b8a4282566304ae04dc533f4312e91277d37

Disposition: NOT-A-BUG
Evidence: Authenticated live head 05c9710a46b982ce1a7fbb437c25e57cfaf244bc contains reachable material 08c1e90e47dcf35bcfd41e36b981fe8400718ae1; the cited f49aa935 is not the live pre-merge PR graph.
Reason: Pre-merge owner evidence binds the authenticated live branch; a future squash SHA belongs to post-merge proof.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2371#discussion_r3913842480

Disposition: NOT-A-BUG
Evidence: Authenticated live head 05c9710a46b982ce1a7fbb437c25e57cfaf244bc contains reachable material 08c1e90e47dcf35bcfd41e36b981fe8400718ae1; the cited 2ff819b896509597f42a530da40c7540decf306b is a synthetic prospective squash projection.
Reason: The current provider-neutral seal is bound to the live branch graph; no pre-merge squash commit exists.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2371#discussion_r3914064044

Disposition: NOT-A-BUG
Evidence: Authenticated live head 05c9710a46b982ce1a7fbb437c25e57cfaf244bc contains reachable material 08c1e90e47dcf35bcfd41e36b981fe8400718ae1; the cited 0b13e6df4e25fde327b189366748fa2e4c370aa4 is not the live PR head.
Reason: The transition owner correctly binds reachable branch material; the eventual squash SHA is post-merge evidence.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2371#discussion_r3915247238

Disposition: NOT-A-BUG
Evidence: git merge-base --is-ancestor 937db0926f257684cc57ef39b1dcf78589643aeb 05c9710a46b982ce1a7fbb437c25e57cfaf244bc exits 0, and the other mapped proof commits are likewise reachable; 0b13e6df4e25fde327b189366748fa2e4c370aa4 is synthetic.
Reason: Existing FIXED proofs are reachable in the authenticated live PR graph and must not be rewritten around a prospective squash projection.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2371#discussion_r3915247253

Disposition: NOT-A-BUG
Evidence: npm 11.16.0 accepts a missing optional dependency as a non-required edge; the joint delegated-recognizer baseline requires no missing or invalid required edge and P separately checks every installed raw Browserslist occurrence
Reason: A missing optional record is neither an installed occurrence nor a required edge; strengthening optional into required would reject valid npm executable absence and restore the deleted handwritten graph interpreter
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2371#discussion_r3918818438

Disposition: NOT-A-BUG
Evidence: tests/test_frontend_dependency_guards.py:1642 and tests/test_frontend_dependency_guards.py:2977; the authorized transitive batch rejects every direct or aliased target owner while permitting future executable absence after complete npm admission
Reason: A future direct Browserslist owner would be a separately authorized topology and transition-evidence change; accepting it inside this transitive-only guard would silently widen the current authority class.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2371#discussion_r3919121643

Disposition: NOT-A-BUG
Evidence: The cited 40fdb2c34912e551f6f71a9ba5940f10b2f2ab6b is absent from local Git, returns HTTP 422 from the authenticated GitHub Commit API, and is absent from the complete live PR commit graph; live head 7b0c112a26f730abc509d9dc9ac932741d964937 retains reachable transition material 6897a711cb8d92864ec0cfd7a1c9d68e7dff1a21, while the current seal independently binds real live material.
Reason: The root's claimed finding identity, a real reviewed 40fdb2c side-history commit, is false; earlier seals became historical after later real material and the mandatory current-material reseal handles that independent closeout obligation.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2371#discussion_r3919201720

Disposition: NOT-A-BUG
Evidence: The cited 6989e33f467c3f47c88b2236129b013222b72d80 is absent from local Git, returns HTTP 422 from the authenticated GitHub Commit API, and is absent from the complete live PR commit graph; docs/security/FRONTEND_BROWSERSLIST_REMEDIATION_CLASS.md:40 retains real transition material 6897a711cb8d92864ec0cfd7a1c9d68e7dff1a21 reachable from live head 7b0c112a26f730abc509d9dc9ac932741d964937.
Reason: A synthetic reviewer projection has no repository or ancestry authority and cannot replace the authenticated live PR graph or real transition owner.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2371#discussion_r3933716308

Disposition: NOT-A-BUG
Evidence: The cited 6b5d8654bfd1a08e2eda2ac83f7f9b405c6d920c is absent from local Git (cat-file exit 128), returns HTTP 422 from the authenticated Commit API, and is absent from the complete live PR graph; real e8b30562978614708f7c02b15ed79b9eb2bea0dc and transition 6897a711cb8d92864ec0cfd7a1c9d68e7dff1a21 are ancestors of authenticated material. The older e8-bound seal is an invalidated historical receipt, strict closeout remains fail-closed, and no READY claim relies on it; final closeout independently binds the real final material.
Reason: The root treats a synthetic reviewed ref as a concrete side-history commit and an intentionally invalidated historical seal as current authority. The authenticated PR graph is authoritative; one final reseal after active remediation is the pre-existing lifecycle requirement, so no stale seal is accepted and no actionable is waived.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2371#discussion_r3938084873

## Review Material Seal
<!-- PULSEPLATE_PR_REVIEW_SEAL_V1_BEGIN -->
<!-- pragma: allowlist nextline secret -->
{"authority":"human_asserted_content_receipt","code_review":{"blocking":false,"material_digest":"sha256:eaf411fe26cf0c00e3469a5452201eb552bd25fe02d552e6d77ebfef74a67084","material_head_sha":"06f90fbd5bcd91b97637f61dd27573b5215c31ac","output_required":false,"review_claim":"none"},"codex_security":{"base_revision":"08e267473458156362bcc166c3d577e8f460c9e7","blocking":false,"head_revision":"06f90fbd5bcd91b97637f61dd27573b5215c31ac","material_digest":"sha256:eaf411fe26cf0c00e3469a5452201eb552bd25fe02d552e6d77ebfef74a67084","no_findings_claim":false,"output_required":false,"scan_claim":"none"},"material":{"base_ref_oid":"08e267473458156362bcc166c3d577e8f460c9e7","digest":"sha256:eaf411fe26cf0c00e3469a5452201eb552bd25fe02d552e6d77ebfef74a67084","material_head_sha":"06f90fbd5bcd91b97637f61dd27573b5215c31ac","merge_base_sha":"08e267473458156362bcc166c3d577e8f460c9e7","policy_version":"pulseplate.material-classification/v1"},"pr_number":2371,"repository":"Katsiarynakavaleuskaya/PulsePlate","schema_version":"pulseplate.pr-review-seal/v1","self_review":{"actionable_findings_count":0,"authority":"repo_native_pulseplate_pr_review_advisory","blocking":false,"findings_count":1,"material_digest":"sha256:eaf411fe26cf0c00e3469a5452201eb552bd25fe02d552e6d77ebfef74a67084","material_head_sha":"06f90fbd5bcd91b97637f61dd27573b5215c31ac","report_payload":{"actionable_findings_count":0,"base_ref_oid":"08e267473458156362bcc166c3d577e8f460c9e7","calibration":{"case_labels":["large-diff-risk"],"false_positive_controls":["clean context must produce zero findings","benign fixed-mapping presence must not become a governance finding","warnings and governance uncertainty remain actionable findings, not diagnostic notes","review-source degradation is status/warning only unless an explicit blocking source finding exists","large diff risk is review-planning evidence, not a merge-readiness claim"],"posting_eligible":false,"posting_gate":"GitHub posting remains out of scope until a dedicated calibrated posting PR.","rubric_version":"pr4-2026-04-28"},"coordinator_packet":{"path":"artifacts/orchestration/task_packets/132db9936aa1.json","role_order":["agent-coordinator","architecture-specialist","security-auditor","qa-engineer-agent","bug-hunter","data-scientist-agent"],"task_packet_id":"132db9936aa1"},"decision_log":["This report is advisory and side-effect free.","This report does not post GitHub comments, resolve review threads, merge PRs, or claim merge readiness.","External CodeRabbit, Sourcery, and Cubic statuses remain separate PR governance signals."],"deferred_followups":[],"findings":[{"category":"tests","diagnostic_code":"large_diff_review_risk","disposition_candidate":"NOT-A-BUG","evidence":"Diff contains 2897 changed lines, above review-risk threshold 800.","file":"docs/roadmap/BACKLOG_LEDGER.md","gate_to_run":"make validate-changed","line":null,"role_agent":"bug-hunter","severity":"note","suggested_fix":"Confirm PR split rationale and targeted deterministic gates before opening review."}],"findings_count":1,"gate_plan":["python3 scripts/orchestration/check_preflight.py","python3 scripts/orchestration/check_agent_consistency.py","python3 -m pytest tests/test_pr_review_report.py tests/test_pr_review_context.py -q","make test-fast","make validate-changed"],"generated_at_utc":"2026-09-06T16:52:34Z","material_digest":"sha256:eaf411fe26cf0c00e3469a5452201eb552bd25fe02d552e6d77ebfef74a67084","material_head_sha":"06f90fbd5bcd91b97637f61dd27573b5215c31ac","merge_base_sha":"08e267473458156362bcc166c3d577e8f460c9e7","mode":"dry-run-report","review_source_status":[{"blocking":false,"evidence":"gh api repos/<repo>/pulls/<pr>","fallback_required":false,"reason":"","source":"github_pr_metadata","source_degraded":false,"status":"available"},{"blocking":false,"evidence":"08e267473458156362bcc166c3d577e8f460c9e7..06f90fbd5bcd91b97637f61dd27573b5215c31ac","fallback_required":false,"reason":"","source":"git_diff","source_degraded":false,"status":"available"},{"blocking":false,"evidence":"docs/review/PR_2371_FIXED_MAPPING.md","fallback_required":false,"reason":"","source":"fixed_mapping_artifact","source_degraded":false,"status":"available"}],"role_review":[{"role_agent":"agent-coordinator","summary":"agent-coordinator has no deterministic findings from the supplied context."},{"role_agent":"architecture-specialist","summary":"architecture-specialist has no deterministic findings from the supplied context."},{"role_agent":"security-auditor","summary":"security-auditor has no deterministic findings from the supplied context."},{"role_agent":"qa-engineer-agent","summary":"qa-engineer-agent has no deterministic findings from the supplied context."},{"role_agent":"bug-hunter","summary":"bug-hunter flagged 1 advisory finding(s) for human review."},{"role_agent":"data-scientist-agent","summary":"data-scientist-agent has no scoring calibration changes in this dry-run report."}],"schema_version":"2.0.0","scope_reviewed":{"changed_files":[".secrets.baseline","docs/security/DEPENDABOT_ALERT_INVENTORY.md","docs/security/FRONTEND_BROWSERSLIST_REMEDIATION_CLASS.md","frontend/package-lock.json","tests/test_frontend_dependency_guards.py"],"diff_summary":{"additions":2836,"changed_lines":2897,"deletions":61,"files":5},"fixed_mapping_errors":[],"omitted_surfaces":["GitHub posting","PR thread resolution","merge readiness claims"],"pr_metadata_available":true,"scoped_agents_md":["AGENTS.md","frontend/AGENTS.md","tests/AGENTS.md"]},"warnings":[]},"report_sha256":"sha256:cf87bbcd106268c45f18634bcee1797b2634acc111ed23d5acad3ee04108c4b2","review_claim":"none","review_tool":"pulseplate-pr-review","schema_version":"pulseplate.self-review-advisory/v1","status":"advisory_report_attached"}}
<!-- PULSEPLATE_PR_REVIEW_SEAL_V1_END -->
