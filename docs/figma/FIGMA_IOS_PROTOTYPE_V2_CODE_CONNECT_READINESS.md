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
| `iOS_Onboarding_01_Welcome` | `1:2` | `SwiftUI` | ready_for_suggestions |
| `iOS_Onboarding_02_Value_Usage` | `3:2` | `SwiftUI` | ready_for_suggestions |
| `iOS_Home` | `4:2` | `SwiftUI` | ready_for_suggestions |
| `iOS_Paywall_Pro_VIP` | `2:2` | `SwiftUI` | ready_for_suggestions |
| `iOS_ShoppingList` | `5:2` | `SwiftUI` | ready_for_suggestions |
| `iOS_WeeklyPlan_Reader` | `6:2` | `SwiftUI` | ready_for_suggestions |
| `iOS_Profile` | `7:2` | `SwiftUI` | ready_for_suggestions |
| `iOS_BMI` | `8:2` | `SwiftUI` | ready_for_suggestions |

## Preconditions

1. Seat/plan blocker is cleared:
   `mcp__figma__whoami` + `mcp__figma__get_code_connect_suggestions` no longer
   return a seat/plan error.
2. `ios prototype v2` remains the canonical implementation-safe source.
3. Runtime references stay current for the iOS mapping lane:
   - `ios/PulsePlate/Views/HomeView.swift`
   - `ios/PulsePlate/Screens/PaywallScreen.swift`
   - `ios/PulsePlate/Views/WeeklyPlan/WeeklyPlanReaderView.swift`
   - `ios/PulsePlate/Screens/ShoppingListReaderScreen.swift`
   - `ios/PulsePlate/Views/Profile/ProfileView.swift`
   - `ios/PulsePlate/Views/BMICalculatorView.swift`

## Activation checklist

1. Confirm seat capability:
   - run `mcp__figma__whoami`
   - run `mcp__figma__get_code_connect_suggestions(fileKey="AhyS6u4dZXMRHVUDO3Cfn6", nodeId="4:2")`
   - continue only if the response is not plan-blocked
2. Verify node accessibility for all eight screens:
   - run `mcp__figma__get_metadata(fileKey, nodeId)` for each node in the
     inventory table
3. Generate Code Connect suggestions for each screen:
   - `mcp__figma__get_code_connect_suggestions(fileKey, nodeId, clientFrameworks="swiftui", clientLanguages="swift")`
4. Review suggestion quality against runtime source-of-truth:
   - `Home` -> `HomeView.swift`
   - `Paywall` -> `PaywallScreen.swift`
   - `Weekly Plan` -> `WeeklyPlanReaderView.swift`
   - `Shopping List` -> `ShoppingListReaderScreen.swift`
   - `Profile` -> `ProfileView.swift`
   - `BMI` -> `BMICalculatorView.swift`
5. Persist approved mappings:
   - use `mcp__figma__send_code_connect_mappings(...)` for batched saves
   - use `mcp__figma__add_code_connect_map(...)` only if an explicit manual map
     is needed after review
6. Verify persisted mappings:
   - run `mcp__figma__get_code_connect_map(fileKey, nodeId, codeConnectLabel="SwiftUI")`
7. Record evidence:
   - update `docs/runbooks/sessions/FIGMA_MCP_SESSION_2026-03-11_ios-prototype-check.md`
   - update `docs/figma/FIGMA_IOS_PROTOTYPE_V2_RECONCILIATION.md`
   - if mappings are activated in a PR, mirror results in
     `docs/review/PR_<N>_FIXED_MAPPING.md`
   - update the PR body mirror with:
     - `## Discussion Thread Pass`
     - `### Fixed in Commit Mapping`
     - `## Merge Readiness`
   - keep the artifact and PR body mirror aligned before claiming merge
     checklist completion

## Acceptance criteria

- The seat/plan blocker is gone for at least one validation call.
- Every `ios prototype v2` node in the inventory resolves via `get_metadata`.
- `get_code_connect_suggestions(...)` returns suggestions for all intended
  screens instead of a workspace-plan block.
- Saved mappings can be verified with `get_code_connect_map(...)`.
- Mapping evidence includes `fileKey`, `nodeId`, `label`, runtime source path,
  and timestamp.

## Decision log

- Use `ios prototype v2`, not the raw `ios prototype`, as the future mapping
  source.
- Keep the mapping lane focused on `SwiftUI`; do not mix web and iOS labels in
  this file.
- Do not claim Code Connect activation before the seat/plan blocker is actually
  cleared in MCP.
