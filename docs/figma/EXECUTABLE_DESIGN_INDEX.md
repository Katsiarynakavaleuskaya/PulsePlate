<!-- markdownlint-disable MD013 -->
# Executable Design Index (PulsePlate H+P+Pr)

**Date:** 2026-02-24
**Scope:** Home + Plate + Progress (iOS + Web)
**Status:** Active

## Purpose

This index maps design documentation to executable Figma MCP instructions and tracks execution status for each screen.

## Quick Start

```bash
# List available screens
python scripts/design/generate_figma_instructions.py --list-screens

# Validate an instruction
python scripts/design/execute_design.py --screen ios.home --validate-only

# Execute a design
python scripts/design/execute_design.py --screen ios.home --execute

# Execute and emit governed HTML preview from pulseplate_canvas_v1
python scripts/design/execute_design.py --screen ios.home --execute --emit-preview

# Or render preview directly from manifest/canvas artifact
python scripts/design/html_preview.py --screen ios.home

# Verify all designs
python scripts/design/verify_design.py --all
```

## Screen Inventory

### iOS Screens

| Screen | CTAs | Instruction | Status | Figma Page | Last Executed |
|--------|------|-------------|--------|------------|---------------|
| ios.home | 5 | `instructions/ios_home.json` | TODO | `10_iOS_Home` | - |
| ios.plate | 3 | `instructions/ios_plate.json` | TODO | `11_iOS_Plate` | - |
| ios.progress | 2 | `instructions/ios_progress.json` | TODO | `12_iOS_Progress` | - |

### Web Screens

| Screen | CTAs | Instruction | Status | Figma Page | Last Executed |
|--------|------|-------------|--------|------------|---------------|
| web.home | 4 | `instructions/web_home.json` | TODO | `20_Web_Parity` | - |
| web.plate | 3 | `instructions/web_plate.json` | TODO | `20_Web_Parity` | - |
| web.progress | 1 | `instructions/web_progress.json` | TODO | `20_Web_Parity` | - |

**Status Legend:**
- `TODO`: Instruction created, awaiting execution
- `EXECUTING`: Currently being executed via MCP
- `SIMULATED`: Simulated execution (MCP not connected)
- `COMPLETED`: Successfully created in Figma
- `FAILED`: Execution failed (see logs)

## CTA Summary by Screen

### ios.home (5 CTAs)

| CTA Key | Label | Variant | Status |
|---------|-------|---------|--------|
| ios.home.bmi_calculator | BMI Calculator | V1 | Implemented |
| ios.home.profile_setup | Profile Setup | V1 | Implemented |
| ios.home.open_plate | Open Plate | V1 | Implemented |
| ios.home.weekly_plan_reader | Weekly Plan Reader | V3 | Blocked by flag |
| ios.home.shopping_list_generator | Shopping List Generator | V3 | Blocked by flag |

### ios.plate (3 CTAs)

| CTA Key | Label | Variant | Status |
|---------|-------|---------|--------|
| ios.plate.add_meal | Add Meal | V1 | Partial |
| ios.plate.view_details | View Details | V3 | Partial |
| ios.plate.issue_action_dynamic | Dynamic Issue Action | V1 | Implemented |

### ios.progress (2 CTAs)

| CTA Key | Label | Variant | Status |
|---------|-------|---------|--------|
| ios.progress.refresh | Refresh | V1 | Implemented |
| ios.progress.issue_action_dynamic | Dynamic Issue Action | V1 | Implemented |

### web.home (4 CTAs)

| CTA Key | Label | Variant | Status |
|---------|-------|---------|--------|
| web.home.open_setup | Open setup | V1 | Implemented |
| web.home.open_plate | Open plate | V3 | Implemented |
| web.home.open_progress | Open progress | V3 | Implemented |
| web.home.open_pro | Open Pro | V2 | Implemented |

### web.plate (3 CTAs)

| CTA Key | Label | Variant | Status |
|---------|-------|---------|--------|
| web.plate.open_setup | Open setup | V1 | Implemented |
| web.plate.open_progress | Open progress | V3 | Implemented |
| web.plate.premium_gate_cta | Unlock Premium | V2 | Implemented |

### web.progress (1 CTA)

| CTA Key | Label | Variant | Status |
|---------|-------|---------|--------|
| web.progress.export_pdf | Export PDF | V3 | Implemented |

## Execution Workflow

### 1. Pre-Execution

```bash
# Refresh context
git diff --name-only origin/main...HEAD -- docs/figma docs/design frontend/src/styles

# Validate instruction
python scripts/design/execute_design.py --screen <screen_id> --validate-only
```

### 2. Execution

```bash
# Execute design via MCP
python scripts/design/execute_design.py --screen <screen_id> --execute
```

### 3. Post-Execution

```bash
# Verify results
python scripts/design/verify_design.py --screen <screen_id>

# Generate or refresh HTML preview
python scripts/design/execute_design.py --screen <screen_id> --execute --emit-preview

# Check manifest
cat docs/design/figma-manifest.json | jq '.exports'

# Review logs
ls -la docs/figma/execution_logs/
```

## File Locations

### Instruction Templates

```text
scripts/design/instructions/
├── ios_home.json
├── ios_plate.json
├── ios_progress.json
├── web_home.json
├── web_plate.json
└── web_progress.json
```

### Execution Scripts

```text
scripts/design/
├── generate_figma_instructions.py  # Generate instructions from docs
├── execute_design.py               # Execute via MCP
├── html_preview.py                 # Derived HTML/browser preview lane
└── verify_design.py                # Verify created designs
```

### Documentation

```text
docs/figma/
├── FIGMA_AI_INSTRUCTION_FORMAT.md  # Instruction format spec
├── MCP_SETUP_GUIDE.md              # MCP setup instructions
├── EXECUTABLE_DESIGN_INDEX.md     # This file
└── execution_logs/                 # Execution audit logs
```

## Governance Validation

Each instruction includes these governance checks:

1. **verify_token_usage** - All colors use design tokens
2. **verify_hpp_compliance** - Follows H+P+Pr visual guidelines
3. **verify_cta_registry_match** - All CTAs exist in button matrix

## Figma Page Structure

Target Figma file must have these pages (per governance index):

```text
00_Foundation_Tokens
01_Components
10_iOS_Home
11_iOS_Plate
12_iOS_Progress
20_Web_Parity
```

## Make Targets

```bash
# Validate a design instruction
make design-validate SCREEN=ios.home

# Execute a design
make design-execute SCREEN=ios.home

# Verify all designs
make design-verify

# Render derived HTML preview
make design-preview SCREEN=ios.home
```

## Canonical References

- **Button Matrix:** `docs/design/PULSEPLATE_BUTTON_ACTION_PROMPT_MATRIX.md`
- **Visual Guidelines:** `docs/design/PULSEPLATE_LUXURY_WEB_IOS_VISUAL_GUIDELINES.md`
- **Figma Governance:** `docs/figma/PULSEPLATE_FIGMA_AI_GOVERNANCE_INDEX.md`
- **Implementation Runbook:** `docs/figma/FIGMA_IMPLEMENTATION_RUNBOOK.md`
- **Token SoT:** `frontend/src/styles/tokens.css`
- **Manifest:** `docs/design/figma-manifest.json`

## Execution Priority

Recommended order:

1. **ios.home** - Pilot screen (5 CTAs, most representative)
2. **ios.plate** - Medium complexity (3 CTAs)
3. **ios.progress** - Simple (2 CTAs)
4. **web.home** - Web parity (4 CTAs)
5. **web.plate** - Web parity (3 CTAs)
6. **web.progress** - Simple (1 CTA)

## Notes

- Actual MCP execution requires Figma MCP connection (see MCP_SETUP_GUIDE.md)
- Without MCP connection, execution is simulated
- Manifest tracks both simulated and actual executions
- HTML preview is derived from `pulseplate_canvas_v1` and remains read-only
- Audit logs preserved in `docs/figma/execution_logs/`
<!-- markdownlint-enable MD013 -->
