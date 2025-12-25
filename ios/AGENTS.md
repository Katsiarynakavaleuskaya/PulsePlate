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
- Backend `app` facade is stable: FastAPI instance is defined in backend
  (`app.app` == `legacy_app.app`). Missing endpoints on iOS usually indicate
  backend feature flags or environment issues, not iOS routing bugs.

## Backend coordination (important)

- Some backend endpoints (e.g. export / premium features) may be gated by
  feature flags evaluated at backend import time.
- If an endpoint unexpectedly returns 404/422 on iOS:
  1) Verify the endpoint exists in backend OpenAPI.
  2) Check backend environment (TESTING / DEBUG / feature flags).
  3) Do NOT assume the issue is in iOS networking until backend routing is confirmed.
