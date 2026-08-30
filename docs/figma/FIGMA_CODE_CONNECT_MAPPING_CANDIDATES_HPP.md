<!-- markdownlint-disable MD013 -->
# Figma Code Connect Mapping Candidates (H+P+Pr)

**Date:** March 7, 2026
**Scope:** 24 design-execution CTA IDs from `docs/design/PULSEPLATE_BUTTON_ACTION_PROMPT_MATRIX.md`; the three separately governed FitChef SupportChoice IDs are excluded
**Context version:** 2026-03-07 / commit `dff20399`

Status policy for this revision: rows stay `blocked_by_design_url` when the Design file key is missing; once the Design URL exists but node IDs are missing, use `blocked_by_node_id_capture` (`missing_node_id`); rows with previously captured but no longer resolvable node IDs are `stale`; rows with verified current node capture are marked `validated`.

| Button/CTA ID | Platform | Screen | Existing Site Surface (file:line) | Candidate Component/Entry | Code Connect Label | Design File Key | Node ID | Status | Gap/Refactor Needed | Owner |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `web.home.open_setup` | Web | Home | `frontend/src/pages/Home.tsx:34` | Inline `Link` in Home quick actions (`to="/setup"`) | React | `umcCk7TtO760DJ3N6M7mvh` | `1:72` (stale) | stale | Re-capture current CTA node; 2026-03-07 MCP reports `1:72` invalid | FE |
| `web.home.open_plate` | Web | Home | `frontend/src/pages/Home.tsx:37` | Inline `Link` in Home quick actions (`to="/plate"`) | React | TBD | TBD | blocked_by_design_url | Add lock-aware variant style and extract component | FE |
| `web.home.open_progress` | Web | Home | `frontend/src/pages/Home.tsx:40` | Inline `Link` in Home quick actions (`to="/progress"`) | React | TBD | TBD | blocked_by_design_url | Consolidate auth-required CTA visual contract | FE |
| `web.home.open_pro` | Web | Home | `frontend/src/pages/Home.tsx:487` | Information-only `Link` to `/marketing` | React | TBD | TBD | blocked_by_design_url | Preserve stable ID while mapping `PP/Web/Home/GuidedPlanning/AppleProductInfo/Button/Default (TBD)` and the label `Learn about PulsePlate for Apple devices` | FE |
| `web.plate.open_setup` | Web | Plate | `frontend/src/pages/Plate.tsx:37` | Inline `Link` inside premium-gated controls | React | TBD | TBD | blocked_by_design_url | Extract gated CTA pair component | FE |
| `web.plate.open_progress` | Web | Plate | `frontend/src/pages/Plate.tsx:40` | Inline `Link` inside premium-gated controls | React | TBD | TBD | blocked_by_design_url | Same as above, shared secondary variant needed | FE |
| `web.plate.premium_gate_cta` | Web | Plate | `frontend/src/components/PremiumGate.tsx:53` | Information-only trigger for the existing `AppleProductInfoDialog` | React | `umcCk7TtO760DJ3N6M7mvh` | TBD | blocked_by_node_id_capture | Preserve stable ID while mapping `PP/Web/Plate/PremiumGate/AppleProductInfo/Button/Default (TBD)` and the label `Learn about PulsePlate for Apple devices` | FE |
| `web.progress.export_pdf` | Web | Progress | `frontend/src/features/progress/ProgressCharts.tsx:120` | Export utility button in ProgressCharts | React | `umcCk7TtO760DJ3N6M7mvh` | TBD | blocked_by_node_id_capture | Refactor to shared utility button for consistent mapping | FE |
| `ios.home.bmi_calculator` | iOS | Home | `ios/PulsePlate/Views/HomeView.swift:57` | `NavigationLink` row entry to `BMICalculatorScreen()` | SwiftUI | TBD | TBD | blocked_by_design_url | Define reusable quick-action row component for iOS maps | iOS |
| `ios.home.profile_setup` | iOS | Home | `ios/PulsePlate/Views/HomeView.swift:67` | `NavigationLink` row entry to `ProfileView()` | SwiftUI | TBD | TBD | blocked_by_design_url | Same quick-action row extraction as above | iOS |
| `ios.home.open_plate` | iOS | Home | `ios/PulsePlate/Views/HomeView.swift:77` | `NavigationLink` row entry to `PlateViewPP()` | SwiftUI | TBD | TBD | blocked_by_design_url | Normalize row variants and states before mapping | iOS |
| `ios.home.weekly_plan_reader` | iOS | Home | `ios/PulsePlate/Views/HomeView.swift:96` | Flagged `NavigationLink` to weekly reader screen | SwiftUI | TBD | TBD | blocked_by_design_url | Feature-flagged; map once release state is stable | iOS |
| `ios.home.shopping_list_generator` | iOS | Home | `ios/PulsePlate/Views/HomeView.swift:106` | Flagged `NavigationLink` to shopping list screen | SwiftUI | TBD | TBD | blocked_by_design_url | Backend and release coupling incomplete | iOS |
| `ios.plate.add_meal` | iOS | Plate | `ios/PulsePlate/Views/PlateView.swift:159` | Bottom bar button (`showMealEntry = true`) | SwiftUI | TBD | TBD | blocked_by_design_url | Destination placeholder; runtime completion required | iOS |
| `ios.plate.view_details` | iOS | Plate | `ios/PulsePlate/Views/PlateView.swift:164` | Bottom bar button (`showNutritionDetails = true`) | SwiftUI | TBD | TBD | blocked_by_design_url | Destination placeholder; runtime completion required | iOS |
| `ios.plate.issue_action_dynamic` | iOS | Plate | `ios/PulsePlate/Views/PlateView.swift:205` | Dynamic issue action button in `PlateIssueView` | SwiftUI | `umcCk7TtO760DJ3N6M7mvh` | TBD | blocked_by_node_id_capture | Need stable issue-action component abstraction | iOS |
| `ios.progress.refresh` | iOS | Progress | `ios/PulsePlate/Views/ProgressView.swift:50` | Refresh button in no-data state | SwiftUI | TBD | TBD | blocked_by_design_url | Promote shared recovery CTA style for mapping | iOS |
| `ios.progress.issue_action_dynamic` | iOS | Progress | `ios/PulsePlate/Views/ProgressView.swift:182` | Dynamic issue action button by issue classifier | SwiftUI | TBD | TBD | blocked_by_design_url | Mirror Plate issue-action component contract | iOS |
| `web.apple_product_info.free_bmi` | Web (linked flow) | Apple Product Information | `frontend/src/components/AppleProductInfoDialog.tsx:50` | Internal `Link` to `/bmi` | React | TBD | TBD | blocked_by_design_url | Map the existing primary free-tool action; no new component family | FE |
| `web.apple_product_info.marketing` | Web (linked flow) | Apple Product Information | `frontend/src/components/AppleProductInfoDialog.tsx:57` | Internal `Link` to `/marketing` | React | TBD | TBD | blocked_by_design_url | Map the existing secondary information action; no Store destination | FE |
| `web.apple_product_info.dismiss` | Web (linked flow) | Apple Product Information | `frontend/src/components/AppleProductInfoDialog.tsx:67` | Existing dialog dismissal action | React | TBD | TBD | blocked_by_design_url | Map the existing ghost action with focus-return semantics | FE |
| `web.setup.submit_calculate` | Web (linked flow) | Nutrition Setup Form | `frontend/src/pages/NutritionSetup/SetupForm.tsx:164` | Submit CTA in setup form | React | TBD | TBD | blocked_by_design_url | Extract form primary CTA wrapper for stable naming | FE |
| `web.setup.result.retry` | Web (linked flow) | Nutrition Setup Result | `frontend/src/pages/NutritionSetup/ResultView.tsx:71` | Retry CTA in error result view | React | TBD | TBD | blocked_by_design_url | Standardize error-state CTA pair component | FE |
| `web.setup.result.edit` | Web (linked flow) | Nutrition Setup Result | `frontend/src/pages/NutritionSetup/ResultView.tsx:78` | Edit CTA in result error/header actions | React | TBD | TBD | blocked_by_design_url | Two entry points; unify as one mapped component variant | FE |

## Notes

- Mapping coverage is complete for the 24-ID design-execution subset. It is derived from the complete 27-ID matrix by excluding only `web.home.fitchef_show_next_step`, `web.home.fitchef_confirm_pointer`, and `web.home.fitchef_dismiss_pointer`, whose design evidence remains in `SupportChoiceCard.stories.tsx`.
- Candidate rows intentionally avoid fake node IDs (evidence: `docs/figma/FIGMA_CODE_CONNECT_MAPPING_CANDIDATES_HPP.md:13`).
- Design file key `umcCk7TtO760DJ3N6M7mvh` is current; MCP `get_metadata(nodeId=\"96:33\")` resolves the spec/index frame, which confirms Design access but not CTA-level capture.
- Prior browser capture for `web.home.open_setup` (`1:72`) is now stale; MCP `get_metadata(nodeId=\"1:72\")` returns `invalid`.
- `web.plate.premium_gate_cta`, `web.progress.export_pdf`, and `ios.plate.issue_action_dynamic` still lack node capture in the Design file.
- Stable identifiers `web.home.open_pro` and `web.plate.premium_gate_cta` are compatibility metadata only. Their names grant no route, label, payment, entitlement, telemetry, Store, or prompt authority; the information-only row fields above are authoritative.
- Workspace-level activation remains blocked because `get_code_connect_suggestions(...)` currently requires a Developer seat in an Organization or Enterprise plan.

## Next action for designer

Provide current node IDs (selection URLs) in Design file `umcCk7TtO760DJ3N6M7mvh` for:

- `web.home.open_setup`
- `web.plate.premium_gate_cta` (information-only Apple-product trigger)
- `web.progress.export_pdf`
- `ios.plate.issue_action_dynamic`
<!-- markdownlint-enable MD013 -->
