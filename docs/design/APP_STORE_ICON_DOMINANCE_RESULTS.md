# App Store Icon Dominance Results

Version: v1.0
Test Date: <YYYY-MM-DD>
Branch: <branch-name>
Operator: <name>
Protocol: `docs/design/APP_STORE_ICON_DOMINANCE_TEST_PROTOCOL.md`
Blueprint Source: `docs/design/EMBLEM_BLUEPRINT_CONCEPTS_v1.md`
Figma Design URL:
Figma File Key:
Figma Node ID:

---

## Candidates

| ID | Concept Name | Source Doc | Build Version |
| --- | --- | --- | --- |
| A | Pulse Hearth Monogram | `docs/design/EMBLEM_BLUEPRINT_CONCEPTS_v1.md` | `v1_build` |
| B | Plate Compass | `docs/design/EMBLEM_BLUEPRINT_CONCEPTS_v1.md` | `v1_build` |
| C | FitChef Orbit Crest | `docs/design/EMBLEM_BLUEPRINT_CONCEPTS_v1.md` | `v1_build` |

---

## 1) Size x Mode Matrix

### Recognition (< 1s silhouette test)

| Variant | 60 Light | 60 Dark | 60 Mono | 120 Light | 120 Dark | 120 Mono | 1024 Light | 1024 Dark | 1024 Mono |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | pass/fail | pass/fail | pass/fail | pass/fail | pass/fail | pass/fail | pass/fail | pass/fail | pass/fail |
| B | pass/fail | pass/fail | pass/fail | pass/fail | pass/fail | pass/fail | pass/fail | pass/fail | pass/fail |
| C | pass/fail | pass/fail | pass/fail | pass/fail | pass/fail | pass/fail | pass/fail | pass/fail | pass/fail |

---

## 2) Automated Stress Tests

### Blur 4px

| Variant | Result | Severity |
| --- | --- | --- |
| A | pass/fail | L1/L2/L3/L4 |
| B | pass/fail | L1/L2/L3/L4 |
| C | pass/fail | L1/L2/L3/L4 |

### Grayscale

| Variant | Result | Severity |
| --- | --- | --- |
| A | pass/fail | L1/L2/L3/L4 |
| B | pass/fail | L1/L2/L3/L4 |
| C | pass/fail | L1/L2/L3/L4 |

### Invert Stability

| Variant | Result | Severity |
| --- | --- | --- |
| A | pass/fail | L1/L2/L3/L4 |
| B | pass/fail | L1/L2/L3/L4 |
| C | pass/fail | L1/L2/L3/L4 |

### Downscale 10%

| Variant | Result | Severity |
| --- | --- | --- |
| A | pass/fail | L1/L2/L3/L4 |
| B | pass/fail | L1/L2/L3/L4 |
| C | pass/fail | L1/L2/L3/L4 |

---

## 3) L3 Shadow / Background Noise Stress

| Variant | Blends into grid? | Misinterpreted symbol? | Peripheral collapse? | Severity |
| --- | --- | --- | --- | --- |
| A | yes/no | yes/no | yes/no | L1/L2/L3/L4 |
| B | yes/no | yes/no | yes/no | L1/L2/L3/L4 |
| C | yes/no | yes/no | yes/no | L1/L2/L3/L4 |

---

## 4) Token Parity

| Variant | Canonical tokens only? | Hex drift? | Severity |
| --- | --- | --- | --- |
| A | yes/no | yes/no | L1/L2/L3/L4 |
| B | yes/no | yes/no | L1/L2/L3/L4 |
| C | yes/no | yes/no | L1/L2/L3/L4 |

---

## 5) Automatic Blockers

If any of the following occurs, release is blocked:

- any L4
- any L3 in size/mode matrix
- any L3 in shadow stress
- palette drift outside canonical tokens
- medical or semantic ambiguity under invert or grayscale

### Blocker Decision

- [ ] NO blockers found (`PASS`)
- [ ] Blocker found (`FAIL`, release blocked)

---

## 6) Winner Decision

### Eligible Candidates (no L3/L4)

- [ ] A
- [ ] B
- [ ] C

### Winner

Selected: <A/B/C>
Reason (objective, test-based only):

- strongest blur dominance
- stable grayscale semantics
- highest silhouette clarity at 60px
- no L2 issues

---

## 7) Contract Lock

Winner becomes:

`PulsePlate App Icon Core v1.0`

Lock artifact (mandatory):

- `docs/design/EMBLEM_CORE_v1.0_LOCK.md`
- Locked Master SVG:
- Locked Master PNG 1024:
- Dual-master parity: pass/fail

All future variants must:

- inherit geometry base
- preserve silhouette discipline
- maintain token lock
- pass full dominance protocol

---

## 8) Archived Candidates

Non-winners are archived as:

- `<Concept>__v0.9__archived`

They may not re-enter testing without geometry revision and version bump.
