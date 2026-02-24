<!-- markdownlint-disable MD013 -->
# Figma AI Instruction Format (Canonical)

**Date:** 2026-02-24
**Scope:** PulsePlate design execution via Figma MCP
**Status:** Active

## 1) Purpose

This document defines the canonical format for Figma AI instructions used by design agents to create actual screen designs via MCP.

## 2) Instruction Schema

### 2.1 Root Structure

```json
{
  "screen_id": "string",
  "page": "string",
  "platform": "string",
  "dimensions": {
    "width": "number",
    "height": "number"
  },
  "background_token": "string",
  "governance_checks": ["array of strings"],
  "context_version": "string",
  "instructions": ["array of instruction objects"]
}
```

### 2.2 Field Definitions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `screen_id` | string | Yes | Screen identifier (e.g., `ios.home`, `web.plate`) |
| `page` | string | Yes | Figma page name from governance index |
| `platform` | string | Yes | `iOS` or `Web` |
| `dimensions` | object | Yes | Screen dimensions in pixels |
| `background_token` | string | Yes | Design token for background color |
| `governance_checks` | array | Yes | List of validation checks to run |
| `context_version` | string | No | Git commit hash or date of context |
| `instructions` | array | Yes | Ordered list of design instructions |

### 2.3 Page Mapping

| Screen ID | Figma Page |
|-----------|------------|
| `ios.home` | `10_iOS_Home` |
| `ios.plate` | `11_iOS_Plate` |
| `ios.progress` | `12_iOS_Progress` |
| `web.home` | `20_Web_Parity` |
| `web.plate` | `20_Web_Parity` |
| `web.progress` | `20_Web_Parity` |

### 2.4 Dimension Presets

| Platform | Width | Height | Device Reference |
|----------|-------|--------|------------------|
| iOS | 390 | 844 | iPhone 14 Pro |
| Web | 1440 | 900 | Desktop |

## 3) Instruction Types

### 3.1 Create Frame

Creates the main screen frame.

```json
{
  "type": "create_frame",
  "name": "iOS Home Screen",
  "dimensions": {
    "width": 390,
    "height": 844
  },
  "background": "Color.navy"
}
```

**Fields:**
- `type`: Always `create_frame`
- `name`: Human-readable frame name
- `dimensions`: Frame size in pixels
- `background`: Design token for fill color

### 3.2 Create Button

Creates a CTA button component.

```json
{
  "type": "create_button",
  "name": "BMI Calculator",
  "cta_key": "ios.home.bmi_calculator",
  "style": "primary",
  "variant": "V1",
  "placement_zone": "I_HOME_QUICK_ACTIONS",
  "figma_node_id": "PP/iOS/Home/QuickActions/BMI/Row/Default (TBD)",
  "prompt_stub": "stub://icon-nav/bmi",
  "states": ["default", "hover", "disabled", "loading", "error"]
}
```

**Fields:**
- `type`: Always `create_button`
- `name`: Button label text
- `cta_key`: CTA ID from button matrix
- `style`: `primary`, `secondary`, or `utility`
- `variant`: Visual variant (`V1`, `V2`, `V3`)
- `placement_zone`: Layout zone identifier
- `figma_node_id`: Target Figma node path (per naming convention)
- `prompt_stub`: Sora prompt reference
- `states`: List of interaction states to create

### 3.3 Create Text

Creates a text element.

```json
{
  "type": "create_text",
  "name": "Screen Title",
  "content": "Home",
  "typography_token": "--font-heading-lg",
  "color_token": "--pp-navy",
  "position": {
    "x": 24,
    "y": 60
  }
}
```

### 3.4 Create Image

Creates an image/asset placeholder.

```json
{
  "type": "create_image",
  "name": "Hero Image",
  "asset_ref": "assets/brand/hero.png",
  "dimensions": {
    "width": 342,
    "height": 200
  },
  "position": {
    "x": 24,
    "y": 100
  }
}
```

## 4) Naming Convention

All Figma nodes must follow this naming pattern:

```text
PP/<Platform>/<Screen>/<Component>/<State>
```

**Examples:**
- `PP/iOS/Home/QuickActions/BMI/Row/Default`
- `PP/Web/Home/QuickActions/OpenSetup/Button/Hover`
- `PP/iOS/Plate/BottomBar/AddMeal/Button/Loading`

**Platform values:** `iOS`, `Web`
**Screen values:** `Home`, `Plate`, `Progress`
**State values:** `Default`, `Hover`, `Pressed`, `Disabled`, `Loading`, `Error`

## 5) Design Token References

### 5.1 Color Tokens

**Web (CSS Custom Properties):**
- `--pp-navy` (`#0F172A`)
- `--pp-blue` (`#339FFF`)
- `--pp-green` (`#20C997`)
- `--pp-red` (`#FF5D5D`)
- `--pp-gold` (`#D4AF37`)

**iOS (Color Assets):**
- `Color.navy`
- `Color.appPrimary`
- `Color.success`
- `Color.heart`

### 5.2 Typography Tokens

- `--font-heading-xl`: 32px, 700 weight
- `--font-heading-lg`: 24px, 700 weight
- `--font-body-lg`: 18px, 400 weight
- `--font-body-md`: 16px, 400 weight
- `--font-label-sm`: 14px, 500 weight

### 5.3 Spacing Tokens

- `--spacing-xs`: 4px
- `--spacing-sm`: 8px
- `--spacing-md`: 16px
- `--spacing-lg`: 24px
- `--spacing-xl`: 32px

## 6) Governance Checks

Each instruction set must specify which governance checks to run:

| Check | Description |
|-------|-------------|
| `verify_token_usage` | All colors/typography use design tokens |
| `verify_hpp_compliance` | Follows H+P+Pr visual guidelines |
| `verify_cta_registry_match` | All CTAs exist in button matrix |
| `verify_naming_convention` | Node names follow PP/ pattern |
| `verify_accessibility` | WCAG AA contrast requirements |

## 7) Button States

All buttons must have these states defined:

1. **default**: Normal resting state
2. **hover**: Mouse hover (web) or highlighted (iOS)
3. **pressed**: Active click/tap state
4. **disabled**: Non-interactive state
5. **loading**: In-progress state
6. **error**: Error recovery state

## 8) Variant System

Visual variants from `PULSEPLATE_BUTTON_VISUAL_SYSTEM_TRENDS_AND_FORECAST.md`:

| Variant | Purpose | Visual Weight |
|---------|---------|---------------|
| `V1` | Primary action | High emphasis, filled |
| `V2` | Premium/Pro action | Medium emphasis, accent |
| `V3` | Secondary action | Low emphasis, outlined |

## 9) Execution Flow

1. **Load instruction JSON** from `scripts/design/instructions/`
2. **Validate** against governance checks
3. **Execute** via Figma MCP tools
4. **Capture** created node IDs
5. **Update** `figma-manifest.json` with results
6. **Log** execution in audit trail

## 10) Example: Complete iOS Home Instruction

```json
{
  "screen_id": "ios.home",
  "page": "10_iOS_Home",
  "platform": "iOS",
  "dimensions": {"width": 390, "height": 844},
  "background_token": "Color.navy",
  "governance_checks": [
    "verify_token_usage",
    "verify_hpp_compliance",
    "verify_cta_registry_match"
  ],
  "instructions": [
    {
      "type": "create_frame",
      "name": "iOS Home Screen",
      "dimensions": {"width": 390, "height": 844},
      "background": "Color.navy"
    },
    {
      "type": "create_button",
      "name": "BMI Calculator",
      "cta_key": "ios.home.bmi_calculator",
      "style": "primary",
      "variant": "V1",
      "placement_zone": "I_HOME_QUICK_ACTIONS",
      "figma_node_id": "PP/iOS/Home/QuickActions/BMI/Row/Default (TBD)",
      "prompt_stub": "stub://icon-nav/bmi",
      "states": ["default", "hover", "disabled", "loading", "error"]
    }
  ]
}
```

## 11) Canonical References

- **Button Matrix:** `docs/design/PULSEPLATE_BUTTON_ACTION_PROMPT_MATRIX.md`
- **Visual Guidelines:** `docs/design/PULSEPLATE_LUXURY_WEB_IOS_VISUAL_GUIDELINES.md`
- **Figma Governance:** `docs/figma/PULSEPLATE_FIGMA_AI_GOVERNANCE_INDEX.md`
- **Token SoT:** `frontend/src/styles/tokens.css`, `ios/PulsePlate/DesignSystem/`
- **Instruction Templates:** `scripts/design/instructions/`
- **Generator Script:** `scripts/design/generate_figma_instructions.py`
<!-- markdownlint-enable MD013 -->
