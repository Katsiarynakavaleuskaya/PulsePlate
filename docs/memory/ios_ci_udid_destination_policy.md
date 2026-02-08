# Memory Capsule: iOS CI destination must be UDID-only

**Topic:** Deterministic iOS simulator destination in CI
**Type:** Hard rule + debugging pointers
**Last updated:** 8 February 2026

---

## What

In CI, `xcodebuild` destination must be **UDID-only**:

- `platform=iOS Simulator,id=<UDID>`

Using `OS=latest` is forbidden in CI destination strings.

---

## Why

UDID-only eliminates nondeterminism and runner drift:

- “latest” ambiguity across GitHub runners
- name/OS version mismatches
- ineligible simulator destinations

---

## Invariants (SoT)

- iOS destination policy header: `AGENTS.md:1350`
- UDID-only requirement: `AGENTS.md:1352`
- `OS=latest` forbidden: `AGENTS.md:1353`
- “No return to OS=latest” hard rule: `AGENTS.md:1361`
- Boot requirement remediation: `AGENTS.md:1362`

---

## Links (canonical)

- `AGENTS.md` → “iOS CI destination policy (canonical)”
- iOS agent scope: `ios/AGENTS.md`
