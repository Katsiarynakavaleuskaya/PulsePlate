# Memory Capsule: iOS CI destination must be UDID-only

**Topic:** Deterministic iOS simulator destination in CI
**Type:** Hard rule + debugging pointers
**Last updated:** 24 September 2026

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

## Current pointer

CAB-05 uses the `xcode-27` image with exact Xcode 27.0, iOS 27.0 SDK and simulator runtime. The CI-selected destination remains UDID-only. A missing exact toolchain or runtime fails the job; historical Xcode 26 results do not establish current-head readiness. This capsule is a navigation aid, not CI evidence.

---

## Links (canonical)

- `AGENTS.md` → “iOS CI destination policy (canonical)” and “Xcode version pinning”
- `ios/AGENTS.md` → current selection, runtime, and boot contracts
- `.github/workflows/ci.yml` → executable unit/UI evidence
- `.github/workflows/ios-appstore-assets.yml` → App Store screenshot selection
