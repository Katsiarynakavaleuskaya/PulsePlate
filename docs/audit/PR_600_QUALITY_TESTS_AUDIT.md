# PR-600 — Quality/Tests Audit (Backend xfail/skip + iOS UI/Animation tests)

**Date:** 26 января 2026 года
**Owner:** @katsiaryna_kavaleuskaya
**Scope anchor:** `docs/roadmap/BACKLOG_LEDGER.md` (P1/P2 items)

## Context / Ledger links (in-scope)

- **P1 (backend/tests):** “Fix test skips/xfails (batch)”
  - `tests/test_bmi_visualization.py:523` — xfail
  - `tests/test_app_branching_and_errors.py:185` — xfail
  - `tests/test_repo_policy_guards.py:85` — skip
- **iOS:** “Stabilize/restore PlateViewTests and UI tests in CI (iOS)”
- **iOS:** “Stabilize AnimationTests.swift (iOS)”

## 0) Scope / Non-goals

### Scope

- **Backend:** inventory + root-cause evidence for the ledger P1 `xfail/skip` list; determine feasibility of removing markers without scope creep.
- **iOS:** inventory + root-cause evidence for `PulsePlateUITests` being skipped in CI, `PlateViewTests` instability, and `AnimationTests.swift` exclusion via `membershipExceptions`.

### Non-goals

- No product changes, contracts, UI/UX, paywall.
- No “replace xfail with skip” or “skip more tests”.
- No remediation changes in this PR (audit-only).

---

## A) Backend: xfail/skip inventory (P1)

### A1) Сколько xfail/skip сейчас и где именно?

**Evidence — inventory scan (raw):**

```bash
rg -n "xfail|pytest\.mark\.xfail|pytestmark = pytest\.mark\.skip|@pytest\.mark\.skip|pytest\.skip\(" tests/
```

**Observed output (excerpt; includes P1 anchors):**

```text
tests/test_bmi_visualization.py
523:    @pytest.mark.xfail(

tests/test_app_branching_and_errors.py
185:@pytest.mark.xfail(

tests/test_repo_policy_guards.py
85:@pytest.mark.skip(reason="TODO: Many legacy tests use sys.modules - cleanup in follow-up PR")
```

**Evidence — “first fail” smoke (requested by audit checklist):**

```bash
pytest -q --disable-warnings --maxfail=1
```

**Observed output (excerpt; shows skipped `s` and xfail `x` markers):**

```text
....................ss......ss.......................................... [  6%]
.......................................................................x [  7%]
...................................................................sssss [ 99%]
sss..............................................................        [100%]
```

**Observed exit code:** `0` (command succeeded).

**Evidence — report reasons for the P1 files:**

```bash
pytest -q -rsk -rsx tests/test_bmi_visualization.py tests/test_app_branching_and_errors.py tests/test_repo_policy_guards.py
```

**Observed output (raw):**

```text
.................x.....................x..........s..........            [100%]
=========================== short test summary info ============================
SKIPPED [1] tests/test_repo_policy_guards.py:85: TODO: Many legacy tests use sys.modules - cleanup in follow-up PR
XFAIL tests/test_bmi_visualization.py::TestBMIVisualizationAPI::test_bmi_visualization_endpoint_with_api_key - Test isolation issue in full suite - passes individually. TODO: Fix test isolation or use dependency override for API key
XFAIL tests/test_app_branching_and_errors.py::test_no_calculate_all_bmr - calculate_all_bmr may not be None after reload; patching not supported in this environment. TODO: Fix module reload/patching or use dependency override
```

**Decision:** ✅ Inventory complete (P1 markers enumerated with file:line + pytest reason).

---

### A2) Каждый xfail/skip — это flake, arch-debt, dead test, или invalid test?

**Important note:**
Both `xfail(strict=True)` cases below are not masking flakes but **mask deterministic failures** when
executed with `--runxfail`. This means current CI green does **not** reflect correctness.

#### A2.1 `tests/test_bmi_visualization.py::TestBMIVisualizationAPI::test_bmi_visualization_endpoint_with_api_key`

- **Marker type:** `xfail(strict=True)`
- **Hypothesis (from marker text):** “passes individually”, test isolation / API key override needed

**Evidence — minimal repro without xfail behavior:**

```bash
pytest -q --runxfail tests/test_bmi_visualization.py::TestBMIVisualizationAPI::test_bmi_visualization_endpoint_with_api_key
```

**Observed output (raw):**

```text
F                                                                        [100%]
=================================== FAILURES ===================================
_____ TestBMIVisualizationAPI.test_bmi_visualization_endpoint_with_api_key _____
tests/test_bmi_visualization.py:566: in test_bmi_visualization_endpoint_with_api_key
    assert (
E   AssertionError: Expected 200, got 404. Response: {"detail":"Not Found"}
E   assert 404 == 200
E    +  where 404 = <Response [404 Not Found]>.status_code
=========================== short test summary info ============================
FAILED tests/test_bmi_visualization.py::TestBMIVisualizationAPI::test_bmi_visualization_endpoint_with_api_key
```

**Classification:** **Invalid test / contract mismatch** (404 indicates endpoint isn’t mounted in this test app config).
This is **not** a “flake”: it is a deterministic failure when evaluated as a normal test.
This is not a missing assertion but a **route wiring mismatch** between the test app fixture and the
actual mounted FastAPI router set.

**Decision:** ✅ Classified; remediation required.

#### A2.2 `tests/test_app_branching_and_errors.py::test_no_calculate_all_bmr`

- **Marker type:** `xfail(strict=True)`
- **Hypothesis (from marker text):** module reload/patching environment mismatch

**Evidence — minimal repro without xfail behavior:**

```bash
pytest -q --runxfail tests/test_app_branching_and_errors.py::test_no_calculate_all_bmr
```

**Observed output (raw):**

```text
F                                                                        [100%]
=================================== FAILURES ===================================
__________________________ test_no_calculate_all_bmr ___________________________
tests/test_app_branching_and_errors.py:203: in test_no_calculate_all_bmr
    assert (
E   AssertionError: calculate_all_bmr is not None after reload; patching not supported in this environment
E   assert <function calculate_all_bmr at 0x10cbc42c0> is None
E    +  where <function calculate_all_bmr at 0x10cbc42c0> = <module 'app' from '/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/app/__init__.py'>.calculate_all_bmr
=========================== short test summary info ============================
FAILED tests/test_app_branching_and_errors.py::test_no_calculate_all_bmr - As...
```

**Classification:** **Invalid test / environment-dependent assumption**. It expects `importlib.reload(app)` to drop symbols (set to `None`) after optional modules are “disabled”, but in this environment it remains defined.

**Decision:** ✅ Classified; remediation required.

#### A2.3 `tests/test_repo_policy_guards.py::test_no_sys_modules_mutation_in_repo`

- **Marker type:** `skip`

**Observed reason (raw):**

```text
SKIPPED [1] tests/test_repo_policy_guards.py:85: TODO: Many legacy tests use sys.modules - cleanup in follow-up PR
```

**Classification:** **Arch/process debt**: guard exists but is intentionally disabled to avoid failing due to legacy patterns.

**Decision:** ✅ Classified; remediation required (and scope must be handled carefully).

---

### A3) Можно ли снять маркер без расширения scope?

**Finding:** Both P1 `xfail` markers currently mask deterministic failures when run with `--runxfail`.

**Decision:** ✅ “Fix feasible in 1 PR” (test-only PR, no product changes)
but **each** needs an explicit choice:

- `test_bmi_visualization_endpoint_with_api_key`: update test to the actually mounted route/app config or adjust app fixture so `/api/v1/bmi/visualize` is available under tests (without introducing new runtime behavior).
- `test_no_calculate_all_bmr`: rework the test to assert behavior that is stable under current import hygiene constraints (no brittle module reload assumptions), or delete as invalid if it no longer reflects supported behavior.

If either requires broad refactor of app bootstrap/import mechanics → it must become **a separate ledger plan**, not PR-Q1.

---

## B) iOS: UI tests (PlateViewTests + PulsePlateUITests)

### B1) Почему UI tests сейчас выключены в CI?

**Evidence — CI workflow uses `-skip-testing:PulsePlateUITests`:**

From `.github/workflows/ci.yml`:

```text
cmd = [
  "xcodebuild", "test-without-building",
  "-project", "PulsePlate.xcodeproj",
  "-scheme", "PulsePlate",
  "-skip-testing:PulsePlateUITests",
  ...
]
```

**Evidence — local `make ios-test` also skips UI tests:**

From `Makefile`:

```text
ios-test:
  cd ios && xcodebuild test \
    -project PulsePlate.xcodeproj \
    -scheme PulsePlate \
    -skip-testing:PulsePlateUITests \
    -only-testing:PulsePlateTests/ThinClientGuardsTests \
    -only-testing:PulsePlateTests/BMIServiceTests \
    ...
```

**Evidence — local run of current iOS unit test subset (raw excerpts):**

```text
Command line invocation:
    ... xcodebuild test ... "-skip-testing:PulsePlateUITests" "-only-testing:PulsePlateTests/ThinClientGuardsTests" ...
...
Test Suite 'Selected tests' passed ...
     Executed 15 tests, with 0 failures (0 unexpected) ...
** TEST SUCCEEDED **
```

**Evidence — attempt to run a single UI test (no skip):**

```bash
xcodebuild test \
  -project PulsePlate.xcodeproj \
  -scheme PulsePlate \
  -destination "platform=iOS Simulator,name=iPhone 16e,OS=latest" \
  -only-testing:PulsePlateUITests/PulsePlateUITests/testExample
```

**Observed output (raw; failure class):**

```text
Simulator device failed to launch com.pulseplate.PulsePlateUITests.xctrunner.
Domain: FBSOpenApplicationServiceErrorDomain
Code: 1
Failure Reason: The request was denied by service delegate (SBMainWorkspace) for reason: Busy ("Application failed preflight checks").
...
** TEST FAILED **
```

**Decision:** ✅ Причина зафиксирована: **UI test runner fails to launch** on simulator (`FBSOpenApplicationServiceErrorDomain` / “Busy”, preflight checks).
Classification: **infra-level / runner launch failure**, not UI logic regression.

---

### B2) PlateViewTests: это флейк или реально сломан тест/код?

**Evidence — targeted run (only PlateViewTests):**

```bash
xcodebuild test \
  -project PulsePlate.xcodeproj \
  -scheme PulsePlate \
  -destination "platform=iOS Simulator,name=iPhone 16e,OS=latest" \
  -only-testing:PulsePlateTests/PlateViewTests
```

**Observed output (raw; key lines):**

```text
Test Case '-[PulsePlateTests.PlateViewTests testNutritionSegmentDataMapping]' started.
PulsePlate(...) malloc: *** error for object 0x26254e760: pointer being freed was not allocated
PulsePlate(...) malloc: *** set a breakpoint in malloc_error_break to debug
Restarting after unexpected exit, crash, or test timeout; summary will include totals from previous launches.
...
** TEST FAILED **
```

**Decision:** ✅ Это **реально сломано/нестабильно** (crash-level), не “просто флейк таймингов”.

---

### B3) Условия возврата UI tests в CI (DoD-гейт)

**Decision (TO-BE / DoD):**

- **Local determinism:** 3–5 последовательных запусков `xcodebuild test` для выбранного UI test subset (как минимум `testExample`) **без** `FBSOpenApplication... Busy` / preflight failures.
- **CI toggles:** убрать `-skip-testing:PulsePlateUITests` из:
  - `.github/workflows/ci.yml`
  - `Makefile` (или оставить только для локального удобства, но тогда CI must run UI tests)
- **CI scope:** добавить хотя бы 1 “smoke” UI test в CI (или целевой subset), чтобы “зелёный” включал UI layer signal.

---

## C) iOS: AnimationTests.swift (membershipExceptions / compile debt)

### C1) Почему AnimationTests исключён (membershipExceptions)?

**Evidence — pbxproj excludes AnimationTests.swift from PulsePlateTests:**

```text
PBXFileSystemSynchronizedBuildFileExceptionSet ... target = ... PulsePlateTests ...
membershipExceptions = (
    AnimationTests.swift,
    __CIAnchorTests.swift,
);
```

**Evidence — trying to run `ProgressAnimationTests` executes 0 tests (raw):**

```text
Test Suite 'PulsePlateTests.xctest' passed ...
     Executed 0 tests, with 0 failures (0 unexpected) in 0.000 ...
** TEST SUCCEEDED **
```

**Additional context:** `AnimatedTransition.swift` currently defines the types referenced by `AnimationTests.swift` (`AnimatedProgressRing`, `PulsingView`, `ShimmerEffect`, `SlideInTransition`, `FadeTransition`), so the original “missing types” rationale may be outdated — but exclusion still means the suite provides **zero protection** today.

**Decision:** ✅ Exclusion mechanism confirmed; suite is effectively not running.

---

### C2) Риск “мертвого теста”

**Finding:** Since `AnimationTests.swift` is excluded, it cannot fail in CI and does not protect product behavior.
This is a **quality mask** even if the tests are still valuable conceptually.
Risk: **false sense of coverage** — suite exists in repo but provides zero signal in CI.

**Decision:** ✅ Remediation must choose **one** strategy (per ledger):
1) Rewrite (under available public/internal components)
2) Separate test target
3) Delete as dead test code (with explicit justification)

---

## D) CI trust: “зелёный” значит “можно мержить”

### D1) Есть ли “обходы”, которые маскируют качество?

**Evidence — iOS UI tests bypass:**

- `.github/workflows/ci.yml`: `-skip-testing:PulsePlateUITests`
- `Makefile`: `ios-test` includes `-skip-testing:PulsePlateUITests`

**Evidence — backend quality masks (P1):**

- `tests/test_bmi_visualization.py:523` — `@pytest.mark.xfail(strict=True, ...)`
- `tests/test_app_branching_and_errors.py:185` — `@pytest.mark.xfail(strict=True, ...)`
- `tests/test_repo_policy_guards.py:85` — `@pytest.mark.skip(...)`

**Evidence — workflow-level `continue-on-error` present (mostly cache-related):**

```text
.github/workflows/ci.yml
127: continue-on-error: true
152: continue-on-error: true
229: continue-on-error: true  # GitHub Actions cache service may be unavailable
...
```

**Decision:** ✅ Обходы инвентаризированы.
**Quality-blocking masks:** `xfail/skip` (backend) + `-skip-testing:PulsePlateUITests` + excluded `AnimationTests.swift`.
**Non-quality masks:** cache steps marked `continue-on-error` (acceptable if limited to caching infra).

---

## E) AGENTS.md / Process updates

### E1) Нужно ли обновлять AGENTS.md после аудита?

**Finding:** `ios/AGENTS.md` already documents that UI tests are excluded and links the backlog item.
This audit adds concrete failure signatures:

- UI tests runner launch fails: `FBSOpenApplicationServiceErrorDomain` / “Busy” / preflight checks
- PlateViewTests crash-level `malloc: pointer being freed was not allocated`

**Decision:** ✅ **No update required** (policy already captured).
Optional follow-up: add these “known failure signatures” to `ios/AGENTS.md` *only if they remain recurrent across multiple runs/hosts*.

---

## Verdict

**Remediation required.**
Current “green” is partially **masked** by expected-failure markers and disabled iOS suites.

### AS-IS → TO-BE (audit table)

| Area | AS-IS | Evidence | TO-BE |
|---|---|---|---|
| Backend xfail | 2 tests are `xfail(strict=True)` | `pytest -q -rsx -rsk ...` + `--runxfail` failures (404 / reload assumption) | Remove markers by making tests valid/stable or deleting invalid tests |
| Backend guard skip | `test_no_sys_modules_mutation_in_repo` is skipped | skip reason in pytest summary | Either restore guard + clean offenders, or replace with scoped/structured guard plan |
| iOS UI tests | Skipped in CI and in `make ios-test` | `-skip-testing:PulsePlateUITests` in CI & Makefile; runner fails to launch | Re-enable at least 1 UI smoke test in CI; ensure deterministic launch |
| iOS PlateViewTests | Present but unstable/crash | malloc crash + “TEST FAILED” | Stabilize/rewrite; then include into CI run set |
| iOS AnimationTests | Excluded via `membershipExceptions` | pbxproj entry + 0 tests executed when targeted | Choose (rewrite/separate/delete) and restore deterministic signal |

---

## Proposed remediation split (next PRs after audit)

### PR-Q1 — Backend: remove P1 xfail/skip (test-only)

- Remove/replace **two** xfail tests by making them valid under current app wiring.
- Address the skipped repo guard plan (either re-enable with a safe approach or explicitly defer with a new ledger item + DoD).

### PR-Q2 — iOS: stabilize `PlateViewTests` + restore UI tests to CI

- Fix crash-level instability in PlateViewTests.
- Fix UI test runner launch flakiness (`Busy` / preflight), then remove `-skip-testing:PulsePlateUITests` in CI.

### PR-Q3 — iOS: resolve `AnimationTests.swift` exclusion

- Choose one strategy: rewrite / separate target / delete as dead.
- Reintroduce deterministic coverage signal (no “0 tests executed”).

---

## Deferred / Follow-ups

- Any fix that requires changes to app bootstrap/import architecture (beyond test-layer) must be tracked as a **separate ledger item** with explicit DoD, not pulled into PR-Q1.
