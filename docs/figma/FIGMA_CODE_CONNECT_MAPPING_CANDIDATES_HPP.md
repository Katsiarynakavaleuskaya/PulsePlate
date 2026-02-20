<!-- markdownlint-disable MD013 -->
# Figma Code Connect Mapping Candidates (H+P+Pr)

**Date:** February 19, 2026
**Scope:** 23 CTA IDs from `docs/design/PULSEPLATE_BUTTON_ACTION_PROMPT_MATRIX.md`
**Context version:** 2026-02-19 / commit `5d05beae`

Status policy for this revision: rows stay `blocked_by_design_url` when the Design file key is missing; once the Design URL exists but node IDs are missing, use `blocked_by_node_id_capture` (`missing_node_id`); rows with verified node capture are marked `validated`.

| Button/CTA ID | Platform | Screen | Existing Site Surface (file:line) | Candidate Component/Entry | Code Connect Label | Design File Key | Node ID | Status | Gap/Refactor Needed | Owner |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `web.home.open_setup` | Web | Home | `frontend/src/pages/Home.tsx:34` | Inline `Link` in Home quick actions (`to="/setup"`) | React | `umcCk7TtO760DJ3N6M7mvh` | `1:72` | validated | Extract reusable quick-action CTA component for stable mapping | FE |
| `web.home.open_plate` | Web | Home | `frontend/src/pages/Home.tsx:37` | Inline `Link` in Home quick actions (`to="/plate"`) | React | TBD | TBD | blocked_by_design_url | Add lock-aware variant style and extract component | FE |
| `web.home.open_progress` | Web | Home | `frontend/src/pages/Home.tsx:40` | Inline `Link` in Home quick actions (`to="/progress"`) | React | TBD | TBD | blocked_by_design_url | Consolidate auth-required CTA visual contract | FE |
| `web.home.open_pro` | Web | Home | `frontend/src/pages/Home.tsx:43` | Inline `Link` in Home quick actions (`to="/pro"`) | React | TBD | TBD | blocked_by_design_url | Align with paywall CTA hierarchy and shared component | FE |
| `web.plate.open_setup` | Web | Plate | `frontend/src/pages/Plate.tsx:37` | Inline `Link` inside premium-gated controls | React | TBD | TBD | blocked_by_design_url | Extract gated CTA pair component | FE |
| `web.plate.open_progress` | Web | Plate | `frontend/src/pages/Plate.tsx:40` | Inline `Link` inside premium-gated controls | React | TBD | TBD | blocked_by_design_url | Same as above, shared secondary variant needed | FE |
| `web.plate.premium_gate_cta` | Web | Plate | `frontend/src/components/PremiumGate.tsx:47` | PremiumGate unlock button entry | React | `umcCk7TtO760DJ3N6M7mvh` | TBD | blocked_by_node_id_capture | Real purchase hook still pending; map after stable CTA API | FE + Product |
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
| `web.paywall.modal.cta` | Web (linked flow) | Paywall Modal | `frontend/src/components/Paywall/BeforeAfter.tsx:136` | Primary purchase CTA in modal | React | TBD | TBD | blocked_by_design_url | Purchase integration incomplete; keep status partial | FE + Product |
| `web.paywall.modal.cancel` | Web (linked flow) | Paywall Modal | `frontend/src/components/Paywall/BeforeAfter.tsx:158` | Cancel CTA in modal footer | React | TBD | TBD | blocked_by_design_url | Stable component exists, map once Design nodes available | FE |
| `web.setup.submit_calculate` | Web (linked flow) | Nutrition Setup Form | `frontend/src/pages/NutritionSetup/SetupForm.tsx:164` | Submit CTA in setup form | React | TBD | TBD | blocked_by_design_url | Extract form primary CTA wrapper for stable naming | FE |
| `web.setup.result.retry` | Web (linked flow) | Nutrition Setup Result | `frontend/src/pages/NutritionSetup/ResultView.tsx:71` | Retry CTA in error result view | React | TBD | TBD | blocked_by_design_url | Standardize error-state CTA pair component | FE |
| `web.setup.result.edit` | Web (linked flow) | Nutrition Setup Result | `frontend/src/pages/NutritionSetup/ResultView.tsx:78` | Edit CTA in result error/header actions | React | TBD | TBD | blocked_by_design_url | Two entry points; unify as one mapped component variant | FE |

## Notes

- Mapping coverage is complete for all 23 CTA IDs in H+P+Pr scope (evidence: `docs/figma/FIGMA_CODE_CONNECT_MAPPING_CANDIDATES_HPP.md:12`).
- Candidate rows intentionally avoid fake node IDs (evidence: `docs/figma/FIGMA_CODE_CONNECT_MAPPING_CANDIDATES_HPP.md:13`).
- 2026-02-19 browser capture validated `web.home.open_setup` as `1:72` in file `umcCk7TtO760DJ3N6M7mvh`; `Find (All pages)` returned no results for `web.plate.premium_gate_cta`, `web.progress.export_pdf`, `ios.plate.issue_action_dynamic` (evidence: `docs/figma/FIGMA_DESIGN_URL_NODEID_CAPTURE_HPP.md:72`, `docs/figma/FIGMA_DESIGN_URL_NODEID_CAPTURE_HPP.md:77`).
- Clear note: For `web.plate.premium_gate_cta`, `web.progress.export_pdf`, and `ios.plate.issue_action_dynamic`, the Design URL exists but node IDs are missing in the design file (evidence: `docs/figma/FIGMA_DESIGN_URL_NODEID_CAPTURE_HPP.md:79`).
- Activation starts after missing node IDs are added in Design and capture is completed (evidence: `docs/figma/FIGMA_DESIGN_URL_NODEID_CAPTURE_HPP.md:83`).

## Next action for designer

Provide node IDs (selection URLs) in Design file `umcCk7TtO760DJ3N6M7mvh` for:

- `web.plate.premium_gate_cta`
- `web.progress.export_pdf`
- `ios.plate.issue_action_dynamic`
<!-- markdownlint-enable MD013 -->
