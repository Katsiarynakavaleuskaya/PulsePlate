# ios prototype v2 source

This folder contains the MCP capture source for the first `ios prototype v2`
slice.

Screens:

- `onboarding-welcome.html` -> `iOS_Onboarding_01_Welcome`
- `onboarding-value-usage.html` -> `iOS_Onboarding_02_Value_Usage`
- `home.html` -> `iOS_Home`
- `paywall-pro-vip.html` -> `iOS_Paywall_Pro_VIP`
- `weekly-plan-reader.html` -> `iOS_WeeklyPlan_Reader`
- `shopping-list.html` -> `iOS_ShoppingList`
- `bmi.html` -> `iOS_BMI`
- `profile.html` -> `iOS_Profile`
- `plate.html` -> `iOS_Plate`
- `progress.html` -> `iOS_Progress`

Rules for capture:

- capture each file separately
- do not capture the index page as a product frame
- keep one stable frame per screen
- use `styles.css` as the shared visual baseline

Generated Figma artifact:

- file name: `ios prototype v2`
- file key: `AhyS6u4dZXMRHVUDO3Cfn6`
- URL: `https://www.figma.com/design/AhyS6u4dZXMRHVUDO3Cfn6`

Current canonical screen map:

- `iOS_Onboarding_01_Welcome` -> `25:2`
- `iOS_Onboarding_02_Value_Usage` -> `20:2`
- `iOS_Home` -> `11:2`
- `iOS_Paywall_Pro_VIP` -> `17:2`
- `iOS_WeeklyPlan_Reader` -> `15:2`
- `iOS_ShoppingList` -> `18:2`
- `iOS_Profile` -> `13:2`
- `iOS_BMI` -> `24:2`
- `iOS_Plate` -> `31:2`
- `iOS_Progress` -> `29:2`

Follow-up artifacts:

- reconciliation: `docs/figma/FIGMA_IOS_PROTOTYPE_V2_RECONCILIATION.md`
- Code Connect readiness:
  `docs/figma/FIGMA_IOS_PROTOTYPE_V2_CODE_CONNECT_READINESS.md`

Note:

- Figma MCP HTML capture auto-generated frame names as `Main Content (...)`.
- Treat the canonical screen ID + `nodeId` mapping above as the implementation-safe reference.
- On March 12, 2026 the `BMI + Onboarding` slice was re-captured into the same
  file after dedicated polish passes; the older node IDs (`1:2`, `3:2`,
  `8:2`, `23:2`, `22:2`, `21:2`) remain historical only and should not be used
  as the latest handoff reference.
- On March 12, 2026 the `Plate + Progress` parity slice was added with
  `iOS_Plate -> 31:2` and `iOS_Progress -> 29:2`; intermediate plate recaptures
  (`26:2`, `30:2`) remain historical only and should not be used as the latest
  handoff reference.
