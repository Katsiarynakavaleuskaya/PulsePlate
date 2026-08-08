<!-- markdownlint-disable MD013 MD024 MD031 MD032 -->

# npm `image-size` transitive removal remediation class

## Authority and bounded claim

This document is the sole evidence owner for one application-dependency
remediation class:

- `D`: `npm:image-size`;
- ecosystem: `npm`;
- `S`: the five repository npm manifest/lock surfaces enumerated below;
- `R`: removal, with one operator-intent transition (`I_R`);
- `P`: executable absence of `npm:image-size` from every governed head surface;
- `F_cutoff`: the two `image-size` advisories returned by the recorded npm audit.

The remediation removes a tracked, local PPTX generator whose sole direct
carrier was root `pptxgenjs`. It does not replace `image-size`, suppress an
advisory, lower scanner severity, weaken a workflow, or claim remediation of a
second dependency identity. The DOCX business-collateral builder and all
PulsePlate application runtime paths remain intact.

## Frozen material and complete surface universe `S`

The exact base is commit
`ad179450108ab352fe31e6687a33185b99b52127`. The guard independently enumerates
tracked npm surfaces at that Git object and Git-indexed npm surfaces in the head
checkout. Both enumerations must equal this exact non-empty set:

1. `package.json`;
2. `package-lock.json`;
3. `frontend/package.json`;
4. `frontend/package-lock.json`;
5. `scripts/business_collateral/package.json`.

| Surface | Base SHA-256 | Head SHA-256 | `image-size` reconciliation |
| --- | --- | --- | --- |
| `package.json` | `1da85e56a5cdcc39fdf1136548aa2815b357bed5f9ccd85399e42c9cbd867ca5` | `9bcbc2307471c1eb4be4c87cffeb88587339e911e6a4898d5c9234fff7b0766c` | no direct/alias occurrence; sole carrier declaration removed |
| `package-lock.json` | `6828456d38086a1924cc0e3c54b4a6d1b001acc686c4cfb07691319ee3759759` | `a5b8a5dc65fdcd5b91af5f5a34a55c46ad9f3f2e8df4cb5d909368b62c1800f9` | base `node_modules/image-size@1.2.1`; head executable absence |
| `frontend/package.json` | `97bd09c0eec4fd15a582dd6a3fc96f02b29610e7955166796421f3cea703f309` | same | negative control; executable absence at base and head |
| `frontend/package-lock.json` | `41d793fe5905be75656cffc03fd03f9c8371ecf1f8f60aa8ee979e789efe5885` | same | negative control; executable absence at base and head |
| `scripts/business_collateral/package.json` | `8005a3491db7d92f36ac66369861589f9c47123d3a7c71e643fc2c06168cd45a` | same | negative control; executable absence at base and head |

The only comparable base occurrence is the lockfile-v3 package record
`node_modules/image-size@1.2.1`, resolved from
`https://registry.npmjs.org/image-size/-/image-size-1.2.1.tgz`. Its only root
carrier is `pptxgenjs@4.0.1`. Dependency-edge semver text is resolver input, not
an additional installed occurrence.

## Candidate inventory `F_cutoff` and applicable subset `A`

The authoritative scanner input is
`npm audit --package-lock-only --json` against the public npm registry using
Node `v24.18.1` and npm `11.16.0`. The exact-base snapshot cutoff is
`2026-08-08T14:01:33Z`. It returned exactly two advisory records for
`npm:image-size`:

| Advisory | Affected range | Base applicability | Universal head evidence |
| --- | --- | --- | --- |
| [`GHSA-w3rx-r6r6-pgpr`](https://github.com/advisories/GHSA-w3rx-r6r6-pgpr) | `<=2.0.2` | Applicable: governed `1.2.1` is affected | executable absence on all five surfaces |
| [`GHSA-5p2g-fcmc-qvqq`](https://github.com/advisories/GHSA-5p2g-fcmc-qvqq) | `<=2.0.2` | Applicable: governed `1.2.1` is affected | executable absence on all five surfaces |

Therefore the derived non-empty applicable subset is exactly:

```text
A = {
  GHSA-5p2g-fcmc-qvqq,
  GHSA-w3rx-r6r6-pgpr
}
```

The base audit exited `1` and reported three high-severity dependency keys:
`image-size`, its direct carrier `pptxgenjs`, and unrelated `nanoid`. After the
removal, the same audit command still exits `1` and reports only `nanoid`.
Consequently, this evidence proves removal of `D`; it does not claim that the
entire root npm audit is clean and does not absorb `nanoid` into this class.

## One removal intent `I_R` and deterministic solver closure `C_R`

The sole dependency-intent transition is:

```text
I_R = delete package.json /dependencies/pptxgenjs (^4.0.1)
```

This is one authored removal operation with one semantic intent: eliminate the
unused local PPTX execution carrier so `npm:image-size` is no longer
executable. Retiring the associated npm command, tracked builder, dead parser,
PPTX-only test, and active builder documentation closes that same local
execution path; none is a second dependency transition or replacement.

The canonical replay command was run twice in separate disposable directories
copied from the exact base:

```text
npm uninstall pptxgenjs --package-lock-only --ignore-scripts --no-audit --no-fund
```

Both runs used Node `v24.18.1` and npm `11.16.0` and produced identical bytes:

- replay `package.json` SHA-256:
  `3ef9e27d3f400a259ccccaacae1e703345298ba587cce2742d85f8be56c0e97e`;
- replay `package-lock.json` SHA-256:
  `a5b8a5dc65fdcd5b91af5f5a34a55c46ad9f3f2e8df4cb5d909368b62c1800f9`.

The worktree lockfile is byte-identical to both replay lockfiles. Its complete
JSON delta is the following mechanically coupled `C_R` and nothing else:

- remove root lock dependency edge `pptxgenjs`;
- remove `node_modules/pptxgenjs`;
- remove `node_modules/image-size`;
- remove `node_modules/https` and `node_modules/queue`;
- remove `node_modules/pptxgenjs/node_modules/@types/node` and its nested
  `undici-types`.

The guard compares the full base/head dependency JSON delta, proves every
admitted `C_R` path exists in the exact base and is absent from head, and fails
on any replacement, manual, unrelated, unclassified, or unreplayable
transition. No lockfile line was edited manually.

## Postcondition `P` and executable closure

`tests/test_root_npm_dependency_guards.py` enforces all of the following:

- exact independent base-Git-object/head-index enumeration of `S`, excluding
  ignored or untracked scratch manifests;
- the single base occurrence and its comparable version/provenance;
- exact derivation of both members of `A` from `F_cutoff`;
- executable absence of `image-size` on every head surface;
- byte-identical negative-control surfaces;
- the sole manifest `I_R` and exact replay-proven lockfile `C_R`;
- rejection of direct declarations, npm aliases, renamed lock entries,
  registry-resolution aliases, replacements on admitted removal paths,
  malformed scalar lock package entries, and unrelated lockfile deltas;
- absence of the PPTX npm command, tracked builder, and dead `parseDeckSpec`
  export while the DOCX-only aggregate command remains available.

Executable evidence anchors for this exact material are:

- exact base, `S`, and `F_cutoff`: `tests/test_root_npm_dependency_guards.py:27`,
  `tests/test_root_npm_dependency_guards.py:28`, and
  `tests/test_root_npm_dependency_guards.py:37`;
- tracked head inventory and ignored/untracked scratch negative control:
  `tests/test_root_npm_dependency_guards.py:145` and
  `tests/test_root_npm_dependency_guards.py:664`;
- `I_R`, `C_R`, applicable-set derivation, and `P`:
  `tests/test_root_npm_dependency_guards.py:296`,
  `tests/test_root_npm_dependency_guards.py:304`, and
  `tests/test_root_npm_dependency_guards.py:352`;
- exact base/head reconciliation entrypoint:
  `tests/test_root_npm_dependency_guards.py:512`;
- replacement-as-removal and malformed-entry negative controls:
  `tests/test_root_npm_dependency_guards.py:599`,
  `tests/test_root_npm_dependency_guards.py:614`,
  `tests/test_root_npm_dependency_guards.py:629`, and
  `tests/test_root_npm_dependency_guards.py:642`;
- retained DOCX command and absence of a pitch command in the bounded script
  object: `package.json:13` and `package.json:14`;
- root dependency object after carrier removal: `package.json:31`;
- retained proposal-only loader exports:
  `scripts/business_collateral/content_loader.js:120`;
- retained DOCX builder behavior test:
  `tests/test_business_collateral_builders.py:90`;
- preserved canonical business/content and owner/cadence truths:
  `docs/audience_pack/B2B_PITCH_DECK_SPEC.md:3` and
  `docs/audience_pack/LIVING_DOCUMENT_PROTOCOL.md:3`.

The canonical pitch-deck specification and living-document protocol are
deliberately preserved byte-for-byte:

- `docs/audience_pack/B2B_PITCH_DECK_SPEC.md` Git blob
  `3227fa0e16b4949ceb889b9f08657bc546f02217`;
- `docs/audience_pack/LIVING_DOCUMENT_PROTOCOL.md` Git blob
  `5fd7869a8864fe6ff6fb3bcca841d17eea535ae1`.

No generated DOCX/PPTX artifacts belong to this remediation. A rollback must
not silently restore the vulnerable carrier graph. Restoring automated PPTX
generation would require a separate reviewed dependency lane with a safe,
fully reconciled graph; the retained markdown specification remains available
for that future decision.
