# Agent instructions (scope: ios/ and subdirectories)

## Scope and layout
- This AGENTS.md applies to: `ios/` and below.
- Key paths: `PulsePlate.xcworkspace`, `PulsePlate.xcodeproj`, `PulsePlate/`.

## Commands
- Open the app in Xcode: `PulsePlate.xcworkspace`.
- Tests: run from Xcode (Unit/UI test targets) or `xcodebuild` if needed.

## Conventions
- Mobile client uses the same REST `/api/v1/*` endpoints and auth flow as web.
- Keep API changes synchronized with backend schema updates.
