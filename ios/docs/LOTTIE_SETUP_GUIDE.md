# Lottie setup and asset integrity

SwiftPM only; no CocoaPods, helper scripts, Xcode-click setup, or runtime fetches.

## Swift Package Manager

Repository declarations are the source of truth; do not edit dependency requirements through the Xcode UI.

Keep the canonical URL and exact requirement identical in all three declarations.

### Generate lockfiles

Run from `ios/`:

```bash
swift package resolve
xcodebuild -resolvePackageDependencies \
  -project PulsePlate.xcodeproj \
  -scheme PulsePlate
```

Never edit generated locks; require semantic URL/version/revision parity.

```
https://github.com/airbnb/lottie-ios
```

From the repository root:

```bash
. scripts/hooks/repo_python.sh
VENV_PYTHON="$(resolve_repo_python "$PWD")"
"$VENV_PYTHON" -m pytest -q tests/test_ios_lottie_contract.py
```

`lottie-spm` requires a separate PR.

## Local animation assets

Only provenance-reviewed `.json` animations may be added under
`PulsePlate/Resources/Lottie`.

- Keep the assets local and include them in the application bundle.
- Add typed catalog cases only for existing basenames.
- Verify catalog, bundle membership, and parsing with the contract XCTest.

No placeholders or runtime fetches.

## Runtime usage

```swift
import Lottie

struct LottieUsageExample: View {
    var body: some View {
        LottieAnimationView(asset: .blink)
    }
}
```

Load from `Bundle.main`; Reduce Motion/load failure uses `Image("FitChef")`.
Non-UI tests cover catalog, bundle, parsing, and playback policy.

## Validation

Run the semantic Python guard, resolve both lockfiles, and run the canonical
project-based iOS test targets. The lockfiles must agree on normalized URL,
version, and revision.

If package resolution or bundle validation fails, regenerate both lockfiles and
rerun the semantic guard. Do not repair generated lockfiles by hand.
