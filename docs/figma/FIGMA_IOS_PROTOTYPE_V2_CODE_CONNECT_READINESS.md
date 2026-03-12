# iOS Prototype v2 Code Connect Readiness

## Scope

This checklist prepares `ios prototype v2` for future Figma Code Connect
activation once the workspace has a Code Connect-capable seat.

Target design artifact:

- file name: `ios prototype v2`
- file key: `AhyS6u4dZXMRHVUDO3Cfn6`
- URL: `https://www.figma.com/design/AhyS6u4dZXMRHVUDO3Cfn6`

Current workspace blocker:

- `get_code_connect_suggestions(...)` remains blocked with:
  `You need a Developer seat in an Organization or Enterprise plan to access Code Connect. Contact a Figma admin to upgrade.`
- canonical evidence:
  `docs/runbooks/sessions/FIGMA_MCP_SESSION_2026-03-11_ios-prototype-check.md`

## Activation-ready node inventory

| Canonical screen ID | nodeId | Proposed label | Activation status |
| --- | --- | --- | --- |
| `iOS_Onboarding_01_Welcome` | `25:2` | `SwiftUI` | ready_for_suggestions |
| `iOS_Onboarding_02_Value_Usage` | `20:2` | `SwiftUI` | ready_for_suggestions |
| `iOS_Home` | `11:2` | `SwiftUI` | ready_for_suggestions |
| `iOS_Paywall_Pro_VIP` | `17:2` | `SwiftUI` | ready_for_suggestions |
| `iOS_ShoppingList` | `18:2` | `SwiftUI` | ready_for_suggestions |
| `iOS_WeeklyPlan_Reader` | `15:2` | `SwiftUI` | ready_for_suggestions |
| `iOS_Profile` | `13:2` | `SwiftUI` | ready_for_suggestions |
| `iOS_BMI` | `24:2` | `SwiftUI` | ready_for_suggestions |

## Preconditions

1. Seat/plan blocker is cleared:
   `mcp__figma__whoami` + `mcp__figma__get_code_connect_suggestions` no longer
   return a seat/plan error.
2. `ios prototype v2` remains the canonical implementation-safe source.
3. Runtime references stay current for the iOS mapping lane:
   - `ios/PulsePlate/Welcome/WelcomeGateView.swift`
   - `ios/PulsePlate/Welcome/WelcomeFlowView.swift`
   - `ios/PulsePlate/Views/HomeView.swift`
   - `ios/PulsePlate/Screens/PaywallScreen.swift`
   - `ios/PulsePlate/Views/WeeklyPlan/WeeklyPlanReaderView.swift`
   - `ios/PulsePlate/Screens/ShoppingListReaderScreen.swift`
   - `ios/PulsePlate/Views/ProfileView.swift`
   - `ios/PulsePlate/Screens/BMICalculatorScreen.swift`

## Activation checklist

1. Confirm seat capability:
   - run `mcp__figma__whoami`
   - run `mcp__figma__get_code_connect_suggestions(fileKey="AhyS6u4dZXMRHVUDO3Cfn6", nodeId="25:2")`
   - continue only if the response is not plan-blocked
2. Verify node accessibility for all eight screens:
   - run `mcp__figma__get_metadata(fileKey, nodeId)` for each node in the
     inventory table
3. Generate Code Connect suggestions for each screen:
   - `mcp__figma__get_code_connect_suggestions(fileKey, nodeId, clientFrameworks="swiftui", clientLanguages="swift")`
4. Review suggestion quality against runtime source-of-truth:
   - `Onboarding 01 Welcome` -> primary `WelcomeFlowView.swift`; supporting
     `WelcomeGateView.swift`
   - `Onboarding 02 Value / Usage` -> primary `WelcomeFlowView.swift`
   - `Home` -> primary `HomeView.swift`
   - `Paywall` -> primary `PaywallScreen.swift`
   - `Shopping List` -> primary `ShoppingListReaderScreen.swift`
   - `Weekly Plan` -> primary `WeeklyPlanReaderView.swift`
   - `Profile` -> primary `ProfileView.swift`
   - `BMI` -> primary `BMICalculatorScreen.swift`
5. Persist approved mappings:
   - use `mcp__figma__send_code_connect_mappings(...)` for batched saves
   - use `mcp__figma__add_code_connect_map(...)` only if an explicit manual map
     is needed after review
6. Verify persisted mappings:
   - run `mcp__figma__get_code_connect_map(fileKey, nodeId, codeConnectLabel="SwiftUI")`
7. Record evidence:
   - create a new dated session log under `docs/runbooks/sessions/`, for
     example `FIGMA_MCP_SESSION_<YYYY-MM-DD>_ios-prototype-check.md`
   - keep `docs/runbooks/sessions/FIGMA_MCP_SESSION_2026-03-11_ios-prototype-check.md`
     as the blocker-era baseline reference
   - update `docs/figma/FIGMA_IOS_PROTOTYPE_V2_RECONCILIATION.md` with a
     cross-link to both the new activation log and the March 11 blocker-era
     evidence
   - if mappings are activated in a PR, mirror results in
     `docs/review/PR_<N>_FIXED_MAPPING.md`
   - update the PR body mirror with:
      - `## Discussion Thread Pass`
      - `- [x] Discussion-thread pass completed`
      - `- [x] Fixed in commit mapping completed`
      - `### Fixed in Commit Mapping`
      - `## Merge Readiness`
   - ensure the canonical artifact keeps the same two `## Discussion Thread Pass`
     checkboxes checked as `[x]`
   - keep the artifact and PR body mirror aligned before claiming merge
     checklist completion

## Acceptance criteria

- The seat/plan blocker is gone for at least one validation call.
- Every `ios prototype v2` node in the inventory resolves via `get_metadata`.
- `get_code_connect_suggestions(...)` returns suggestions for all intended
  screens instead of a workspace-plan block.
- Saved mappings can be verified with `get_code_connect_map(...)`.
- Mapping evidence includes `fileKey`, `nodeId`, `label`, `primary runtime
  source path`, optional `supporting runtime paths[]`, and timestamp.

## Decision log

- Use `ios prototype v2`, not the raw `ios prototype`, as the future mapping
  source.
- Keep the mapping lane focused on `SwiftUI`; do not mix web and iOS labels in
  this file.
- Do not claim Code Connect activation before the seat/plan blocker is actually
  cleared in MCP.
