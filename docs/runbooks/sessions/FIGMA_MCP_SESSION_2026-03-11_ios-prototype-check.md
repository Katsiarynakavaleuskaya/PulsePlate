# Figma MCP Session Evidence

## Session Metadata

- Date: 2026-03-11
- Operator: Codex agent + user session
- Branch: `worktree/figma-ios-proto-pr`
- Local source root: `worktrees/figma_ios_proto_pr`
- Target Figma source URL: existing file discovery (`existingFile`) + Design file verification
- Target node/frame:
  - Design spec root: `umcCk7TtO760DJ3N6M7mvh` / `96:33`
  - Raw iOS prototype root: `hr71gseIO7EY0SnHFXMVs9` / `0:1`

## Preconditions Check

- `FIGMA_OAUTH_TOKEN` present: yes (authenticated `whoami` response)
- Token length check passed: not logged in this evidence file (security-safe policy)
- Figma MCP server visible in runtime: yes
- Figma tools callable: yes

## Execution

### Request 1 (identity/auth)

- Tool: `mcp__figma__whoami`
- Result:
  - email: `lexakm532@gmail.com`
  - handle: `Katsiaryna Kavaleuskaya`
  - plan: `Катерина's team` (`pro`, seat `Full`)

### Request 2 (Design file metadata)

- Tool: `mcp__figma__get_metadata`
- Arguments:
  - `fileKey=umcCk7TtO760DJ3N6M7mvh`
  - `nodeId=96:33`
- Result:
  - success
  - returned Design spec/index frame metadata
  - confirms Figma Design file access is live in this runtime

### Request 3 (Code Connect capability check)

- Tool: `mcp__figma__get_code_connect_suggestions`
- Arguments:
  - `fileKey=umcCk7TtO760DJ3N6M7mvh`
  - `nodeId=96:33`
- Result:
  - blocked
  - response: `You need a Developer seat in an Organization or Enterprise plan to access Code Connect. Contact a Figma admin to upgrade.`
  - debug UUID: `a5ea7af3-2aea-44bc-8bf4-6ffad206ff47`

### Request 4 (design push discovery)

- Tool: `mcp__figma__generate_figma_design`
- Arguments:
  - discovery mode (no `outputMode`)
- Result:
  - success
  - returned `newFile`, `existingFile`, and `clipboard`
  - returned recent `existingFile` candidates:
    - `ios prototype` (`hr71gseIO7EY0SnHFXMVs9`)
    - `PulsePlate Design System` (`umcCk7TtO760DJ3N6M7mvh`)

### Request 5 (raw iOS prototype intake)

- Tool: `mcp__figma__get_metadata`
- Arguments:
  - `fileKey=hr71gseIO7EY0SnHFXMVs9`
  - `nodeId=0:1`
- Result:
  - success
  - file root is `Page 1`
  - top frame is `2:2` (`Container`, `375x812`)
  - visible content is a welcome/onboarding screen with:
    - `Пропустить`
    - `Добро пожаловать в PulsePlate`
    - `Продолжить`

### Request 6 (raw iOS prototype screenshot)

- Tool: `mcp__figma__get_screenshot`
- Arguments:
  - `fileKey=hr71gseIO7EY0SnHFXMVs9`
  - `nodeId=0:1`
- Result:
  - success
  - screenshot confirms the prototype currently contains at least one imported onboarding screen

## Validation

- MCP auth status: pass
- Figma Design metadata fetch: pass
- Design push discovery: pass
- Raw iOS prototype discovery: pass
- Code Connect activation: blocked by workspace seat/plan

## Raw Evidence

- Call: `whoami`
  - Output: authenticated workspace payload returned
  - Exit: success

- Call: `get_metadata(fileKey="umcCk7TtO760DJ3N6M7mvh", nodeId="96:33")`
  - Output: Design spec/index frame metadata returned
  - Exit: success

- Call: `get_code_connect_suggestions(fileKey="umcCk7TtO760DJ3N6M7mvh", nodeId="96:33")`
  - Output: plan/seat block message returned
  - Exit: blocked by workspace capability

- Call: `generate_figma_design()`
  - Output: discovery payload returned `newFile`, `existingFile`, `clipboard`
  - Exit: success

- Call: `get_metadata(fileKey="hr71gseIO7EY0SnHFXMVs9", nodeId="0:1")`
  - Output: root onboarding metadata returned
  - Exit: success

## Known Limits / Next Action

- Code Connect remains blocked until the workspace has a Developer seat in an
  Organization or Enterprise plan.
- The raw `ios prototype` file is useful as intake/reference, but it is not yet
  a stable implementation source:
  - screen captures may be duplicated when long scrolling pages were imported
  - node-stable screen/frame boundaries are not yet registered in repo docs
- Next action:
  - normalize the raw iOS prototype into one stable frame per screen
  - record current `fileKey` + `nodeId` pairs for the iOS onboarding/paywall flow
  - keep the prototype file `reference_only` until normalization is complete

## Security Check

- Token value leaked: no
- Sensitive data in logs/comments: no

## Follow-ups

- Update runtime matrix with current 2026-03-11 capability evidence
- Add backlog item for raw iOS prototype normalization
- Do not claim Code Connect activation until both seat/plan and node capture blockers are cleared

---

# Follow-up Execution: `ios prototype v2`

## Session Metadata

- Date: 2026-03-12
- Operator: Codex agent + user session
- Branch: `worktree/figma-ios-proto-pr`
- Local capture source root:
  - `docs/figma/ios_prototype_v2/`
- New Figma file:
  - file name: `ios prototype v2`
  - file key: `AhyS6u4dZXMRHVUDO3Cfn6`
  - URL: `https://www.figma.com/design/AhyS6u4dZXMRHVUDO3Cfn6`

## Source Precedence Used

1. `PulsePlate Design System` as visual/system source of truth
2. raw `ios prototype` as mood/composition base
3. web prototype and button matrix as CTA completeness reference

## Execution

### Request 7 (new standalone file)

- Tool: `mcp__figma__generate_figma_design`
- Arguments:
  - `outputMode=newFile`
  - `planKey=team::1545433342866560049`
  - `fileName=ios prototype v2`
- Result:
  - success
  - generated first-page capture pipeline
  - completed file key: `AhyS6u4dZXMRHVUDO3Cfn6`

### Request 8 (first screen capture)

- Source URL:
  - `http://127.0.0.1:4173/onboarding-welcome.html`
- Capture selector:
  - `.screen`
- Result:
  - success
  - created top-level frame `1:2`

### Request 9 (second screen capture)

- Source URL:
  - `http://127.0.0.1:4173/onboarding-value-usage.html`
- Capture selector:
  - `.screen`
- Result:
  - success
  - created top-level frame `3:2`

### Request 10 (third screen capture)

- Source URL:
  - `http://127.0.0.1:4173/home.html`
- Capture selector:
  - `.screen`
- Result:
  - success
  - created top-level frame `4:2`

### Request 11 (fourth screen capture)

- Source URL:
  - `http://127.0.0.1:4173/paywall-pro-vip.html`
- Capture selector:
  - `.screen`
- Result:
  - success
  - created top-level frame `2:2`

### Request 12 (metadata verification)

- Tool: `mcp__figma__get_metadata`
- Arguments:
  - `fileKey=AhyS6u4dZXMRHVUDO3Cfn6`
  - `nodeId=0:1`
- Result:
  - success
  - confirmed four top-level frames in one page
  - no duplicated scroll-import slices

### Request 13 (screenshot verification)

- Tool: `mcp__figma__get_screenshot`
- Arguments:
  - `fileKey=AhyS6u4dZXMRHVUDO3Cfn6`
  - `nodeId=0:1`
  - `nodeId=4:2`
- Result:
  - success
  - screenshot verifies onboarding, value, paywall, and home screens exist in one clean v2 file
  - home screen verifies required CTA matrix is present

## Stable Screen Map

| Canonical screen ID | Figma nodeId | Imported frame name | Source basis |
| --- | --- | --- | --- |
| `iOS_Onboarding_01_Welcome` | `1:2` | `Main Content (iOS Onboarding Welcome)` | iOS prototype mood + Design System typography |
| `iOS_Onboarding_02_Value_Usage` | `3:2` | `Main Content (iOS Onboarding Value Usage)` | web onboarding structure + iOS-native rewrite |
| `iOS_Home` | `4:2` | `Main Content (iOS Home)` | Design System + iOS Home CTA matrix |
| `iOS_Paywall_Pro_VIP` | `2:2` | `Main Content (iOS Paywall Pro VIP)` | Paywall tier reconciliation from repo SoT |

## Structural QA

- One stable frame per screen: pass
- Standalone new file instead of adding to raw prototype: pass
- Required home quick actions present:
  - `BMI Calculator`
  - `Profile Setup`
  - `Open Plate`
- Required pro-tools present:
  - `Недельный план`
  - `Список покупок`
- PRO + VIP comparison on paywall: pass
- FitChef support-brand label on home: pass
- Duplicate long-scroll capture artifacts: not observed in v2 metadata/screenshot review

## Known Limits

- Figma MCP HTML capture imported frame names as `Main Content (...)` rather than the exact canonical screen IDs.
- To keep the file implementation-safe anyway, this session records a stable canonical screen map:
  - canonical screen ID -> `nodeId` -> imported frame name
- Code Connect remains blocked by workspace seat/plan and was not used.

## Implementation Status

- `ios prototype v2` can now be treated as the current implementation reference for the first core-funnel slice.
- raw `ios prototype` remains `reference_only`.
