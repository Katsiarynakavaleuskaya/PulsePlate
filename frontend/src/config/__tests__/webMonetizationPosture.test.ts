import { existsSync, readFileSync, readdirSync } from 'node:fs';
import { relative, resolve, sep } from 'node:path';
import { describe, expect, it } from 'vitest';

const frontendRoot = resolve(__dirname, '../../..');
const repoRoot = resolve(frontendRoot, '..');

const CURRENT_WEB_MONETIZATION_POSTURE = 'free-informational-apple-product' as const;

const completeMatrixIdentities = [
  'web.home.open_setup',
  'web.home.open_plate',
  'web.home.open_progress',
  'web.home.open_pro',
  'web.home.fitchef_show_next_step',
  'web.home.fitchef_confirm_pointer',
  'web.home.fitchef_dismiss_pointer',
  'web.plate.open_setup',
  'web.plate.open_progress',
  'web.plate.premium_gate_cta',
  'web.progress.export_pdf',
  'ios.home.bmi_calculator',
  'ios.home.profile_setup',
  'ios.home.open_plate',
  'ios.home.weekly_plan_reader',
  'ios.home.shopping_list_generator',
  'ios.plate.add_meal',
  'ios.plate.view_details',
  'ios.plate.issue_action_dynamic',
  'ios.progress.refresh',
  'ios.progress.issue_action_dynamic',
  'web.apple_product_info.free_bmi',
  'web.apple_product_info.marketing',
  'web.apple_product_info.dismiss',
  'web.setup.submit_calculate',
  'web.setup.result.retry',
  'web.setup.result.edit',
] as const;

const fitChefSupportChoiceIdentities = new Set<string>([
  'web.home.fitchef_show_next_step',
  'web.home.fitchef_confirm_pointer',
  'web.home.fitchef_dismiss_pointer',
]);

const designExecutionIdentities = completeMatrixIdentities.filter(
  (identity) => !fitChefSupportChoiceIdentities.has(identity),
);

const informationOnlyWebStates = [
  'default',
  'hover',
  'pressed',
  'focus-visible',
  'disabled',
] as const;

const informationStateDeclaration =
  'Exact Web information state set: `default`, `hover`, `pressed`, `focus-visible`, `disabled`.';

const informationStateDeclarationPaths = [
  'docs/design/PULSEPLATE_BUTTON_ACTION_PROMPT_MATRIX.md',
  'docs/design/PULSEPLATE_BUTTON_VISUAL_SYSTEM_TRENDS_AND_FORECAST.md',
  'docs/figma/EXECUTABLE_DESIGN_INDEX.md',
  'docs/figma/PULSEPLATE_FIGMA_AI_GOVERNANCE_INDEX.md',
  'docs/figma/PULSEPLATE_FIGMA_DESIGN_SPECIFICATION.md',
  'docs/sora/PULSEPLATE_SORA_BUTTON_VARIANTS_HPP.md',
  'docs/sora/prompts/hpp/p0_visibility/premium_gate_value_frame__plate_pro__v1.0.md',
] as const;

const authoritativeDesignPaths = [
  'docs/design/PULSEPLATE_BUTTON_VISUAL_SYSTEM_TRENDS_AND_FORECAST.md',
  'docs/design/VISUAL_IMPLEMENTATION_MAP.md',
  'docs/figma/EXECUTABLE_DESIGN_INDEX.md',
  'docs/figma/FIGMA_CODE_CONNECT_MAPPING_CANDIDATES_HPP.md',
  'docs/figma/PULSEPLATE_FIGMA_AI_GOVERNANCE_INDEX.md',
  'docs/figma/PULSEPLATE_FIGMA_DESIGN_SPECIFICATION.md',
  'docs/sora/PULSEPLATE_SORA_BUTTON_VARIANTS_HPP.md',
  'docs/sora/prompts/hpp/p0_visibility/premium_gate_value_frame__plate_pro__v1.0.md',
  'scripts/design/generate_figma_instructions.py',
  'scripts/design/instructions/web_home.json',
  'scripts/design/instructions/web_plate.json',
] as const;

const reconciledAuthorityPaths = [
  'docs/design/VISUAL_PR_DESCRIPTION_TEMPLATES.md',
  'docs/product/FREE_PRO_SOFT_PAYWALL.md',
  'docs/analytics/ANALYTICS_INDEX.md',
  'docs/analytics/METRICS_CATALOG.md',
  'docs/analytics/DASHBOARD_BASELINE_REQUIREMENTS.md',
  'docs/analytics/EXPERIMENTATION_FRAMEWORK.md',
  'docs/analytics/EXPERIMENT_REGISTRY.md',
  'frontend/src/lib/telemetry.md',
] as const;

const publicWebMeasurementAuthorityPaths = [
  'docs/analytics/ANALYTICS_INDEX.md',
  'docs/analytics/METRICS_CATALOG.md',
  'docs/analytics/DASHBOARD_BASELINE_REQUIREMENTS.md',
  'frontend/src/lib/telemetry.md',
] as const;

const rejectedPaywallExperimentIds = ['EXP-PWL-001', 'EXP-PWL-002', 'EXP-PWL-003'] as const;

const designRegistrySections = {
  'docs/design/PULSEPLATE_BUTTON_VISUAL_SYSTEM_TRENDS_AND_FORECAST.md': [
    '## 8) Per-Button Visual Table',
    '## 9) Execution Queue',
  ],
  'docs/figma/EXECUTABLE_DESIGN_INDEX.md': ['## CTA Summary by Screen', '## Execution Workflow'],
  'docs/figma/FIGMA_CODE_CONNECT_MAPPING_CANDIDATES_HPP.md': ['| Button/CTA ID', '## Notes'],
  'docs/figma/PULSEPLATE_FIGMA_AI_GOVERNANCE_INDEX.md': [
    '## 4) CTA Registry Index',
    '## 5) Prompt Stub Index',
  ],
  'docs/figma/PULSEPLATE_FIGMA_DESIGN_SPECIFICATION.md': [
    '## 7. Button & CTA Specification',
    '## 8. Accessibility Requirements',
  ],
  'docs/sora/PULSEPLATE_SORA_BUTTON_VARIANTS_HPP.md': [
    '## 6) CTA Prompt ID Index',
    '## 7) Execution Rules',
  ],
} as const;

const correctedBoundaryPaths = [
  'src/components/AppleProductInfoDialog.tsx',
  'src/components/PremiumGate.tsx',
  'src/components/SoftPaywallHook/SoftPaywallHook.tsx',
  'src/components/VipGate.tsx',
  'src/components/index.ts',
  'src/components/marketing/TiersSection.tsx',
  'src/features/progress/LiveProgressIndicator.tsx',
  'src/pages/Home.tsx',
  'src/pages/Pro/ProPaywallPage.tsx',
  'src/stories/storybookParitySupport.tsx',
] as const;

const retiredPurchasePaths = [
  'src/components/Paywall/BeforeAfter.tsx',
  'src/lib/paywallPurchase.ts',
] as const;

const productionUiRoots = ['src/components', 'src/features', 'src/hooks', 'src/pages'] as const;

const productionUiEntries = ['src/App.tsx', 'src/main.tsx', 'src/config/routes.ts'] as const;

// Finite raw-source syntax fragments only. One-hop aliases/destructuring are intentionally
// outside this guard; a materially novel carrier requires stop/rescope. String/comment matches
// fail closed conservatively and are not evidence that an event executed.
const knownDirectAcquisitionSyntaxFragments = [
  {
    id: 'retired_before_after_import',
    pattern: /from\s+['"][^'"]*Paywall\/BeforeAfter['"]|<BeforeAfter\b/,
  },
  {
    id: 'retired_purchase_helper',
    pattern: /from\s+['"][^'"]*lib\/paywallPurchase['"]|\bpurchasePremium\s*\(/,
  },
  { id: 'purchase_callback', pattern: /\bonPurchase\s*=/ },
  {
    id: 'paywall_view_telemetry_call',
    pattern: /(?:\.\s*paywallViewed|\[\s*['"]paywallViewed['"]\s*\])\s*(?:\?\.\s*)?\(/,
  },
  {
    id: 'paywall_dismiss_telemetry_call',
    pattern: /(?:\.\s*paywallDismissed|\[\s*['"]paywallDismissed['"]\s*\])\s*(?:\?\.\s*)?\(/,
  },
  {
    id: 'paywall_cta_telemetry_call',
    pattern: /(?:\.\s*paywallCtaClicked|\[\s*['"]paywallCtaClicked['"]\s*\])\s*(?:\?\.\s*)?\(/,
  },
  {
    id: 'upgrade_telemetry_call',
    pattern: /(?:\.\s*upgradeClicked|\[\s*['"]upgradeClicked['"]\s*\])\s*(?:\?\.\s*)?\(/,
  },
  {
    id: 'trial_telemetry_call',
    pattern: /(?:\.\s*trialStarted|\[\s*['"]trialStarted['"]\s*\])\s*(?:\?\.\s*)?\(/,
  },
  {
    id: 'direct_acquisition_event_call',
    pattern:
      /\b(?:trackEvent|trackVipEvent)\s*(?:\?\.\s*)?\(\s*EventType\.(?:PAYWALL_VIEWED|PAYWALL_CTA_CLICKED|TRIAL_STARTED|VIP_PAYWALL_VIEWED|VIP_PAYWALL_DISMISSED|VIP_UPGRADE_CLICKED)\b/,
  },
  { id: 'paywall_exposure_call', pattern: /\blogPaywallExposure\s*\(/ },
  {
    id: 'live_paywall_telemetry_call',
    pattern: /\btrackHppPaywallOpenFromLive\s*\(/,
  },
  {
    id: 'acquisition_event_emission',
    pattern:
      /\blog\s*\(\s*Events\.(?:PURCHASE_ATTEMPT|PURCHASE_SUCCESS|PURCHASE_FAILURE|RESTORE_SUCCESS)\b/,
  },
  { id: 'legacy_purchase_test_id', pattern: /data-testid=['"]paywall-cta['"]/ },
  {
    id: 'unverified_store_action',
    pattern: /(?:href|to)\s*=\s*['"](?:https:\/\/apps\.apple\.com|itms-apps:)/,
  },
] as const;

function readFrontend(relativePath: string): string {
  return readFileSync(resolve(frontendRoot, relativePath), 'utf8');
}

function readRepo(relativePath: string): string {
  return readFileSync(resolve(repoRoot, relativePath), 'utf8');
}

function sectionBetween(source: string, start: string, end: string): string {
  const startIndex = source.indexOf(start);
  const endIndex = source.indexOf(end, startIndex + start.length);
  expect(startIndex, `missing start marker: ${start}`).toBeGreaterThanOrEqual(0);
  expect(endIndex, `missing end marker: ${end}`).toBeGreaterThan(startIndex);
  return source.slice(startIndex, endIndex);
}

function sectionFrom(source: string, start: string): string {
  const startIndex = source.indexOf(start);
  expect(startIndex, `missing start marker: ${start}`).toBeGreaterThanOrEqual(0);
  return source.slice(startIndex);
}

function registryRowIdentities(source: string): string[] {
  return source.split('\n').flatMap((line) => {
    if (!/^\s*(?:\||-\s)/.test(line)) {
      return [];
    }
    const match = line.match(/\b((?:web|ios)\.[a-z0-9_.]+)\b/);
    if (!match || match[1].split('.').length < 3) {
      return [];
    }
    return [match[1]];
  });
}

function matrixRowIdentities(source: string): string[] {
  const matrix = sectionBetween(source, '## 4) Button Interaction Matrix', '## 5) Prompt Stub');
  return [...matrix.matchAll(/^\|[^|\n]*\|[^|\n]*\|\s*`((?:web|ios)\.[a-z0-9_.]+)`\s*\|/gm)].map(
    (match) => match[1],
  );
}

function sortedUnique(values: readonly string[]): string[] {
  return [...new Set(values)].sort();
}

interface GeneratedButtonInstruction {
  type: string;
  name?: string;
  cta_key?: string;
  style?: string;
  variant?: string;
  placement_zone?: string;
  prompt_stub?: string;
  figma_node_id?: string;
  states?: string[];
  section_id?: string;
  component_id?: string;
  parent_component_id?: string | null;
  hierarchy_level?: number;
}

interface GeneratedSection {
  section_id: string;
  name: string;
  role: string;
  component_ids: string[];
}

interface GeneratedHierarchyNode {
  component_id: string;
  canonical_component: string;
  section_id: string;
  parent_component_id: string | null;
  hierarchy_level: number;
  semantic_role: string;
  source_ref: string;
}

interface GeneratedScreenInstruction {
  screen_id: string;
  sections: GeneratedSection[];
  component_hierarchy: GeneratedHierarchyNode[];
  instructions: GeneratedButtonInstruction[];
}

function readGeneratedInstruction(relativePath: string): GeneratedScreenInstruction {
  return JSON.parse(readRepo(relativePath)) as GeneratedScreenInstruction;
}

function generatedButtons(instruction: GeneratedScreenInstruction): GeneratedButtonInstruction[] {
  return instruction.instructions.filter((item) => item.type === 'create_button');
}

function pythonCtaRegistryBlock(source: string, ctaId: string): string {
  const startMarker = `"${ctaId}": CTASpec(`;
  const startIndex = source.indexOf(startMarker);
  const endIndex = source.indexOf('\n    ),', startIndex + startMarker.length);
  expect(startIndex, `missing generator CTA: ${ctaId}`).toBeGreaterThanOrEqual(0);
  expect(endIndex, `unterminated generator CTA: ${ctaId}`).toBeGreaterThan(startIndex);
  return source.slice(startIndex, endIndex);
}

function pythonCtaStates(source: string, ctaId: string): string[] {
  const block = pythonCtaRegistryBlock(source, ctaId);
  const statesMatch = block.match(/states=\[([^\]]+)]/);
  expect(statesMatch, `missing explicit generator states: ${ctaId}`).toBeTruthy();
  return [...(statesMatch?.[1] ?? '').matchAll(/"([^"]+)"/g)].map((match) => match[1]);
}

function pythonCtaPlacementOverrideBlock(source: string, ctaId: string): string {
  const registryStart = source.indexOf('CTA_PLACEMENT_OVERRIDES:');
  const startMarker = `"${ctaId}": {`;
  const startIndex = source.indexOf(startMarker, registryStart);
  const endIndex = source.indexOf('\n    },', startIndex + startMarker.length);
  expect(registryStart, 'missing finite placement override registry').toBeGreaterThanOrEqual(0);
  expect(startIndex, `missing placement override: ${ctaId}`).toBeGreaterThanOrEqual(0);
  expect(endIndex, `unterminated placement override: ${ctaId}`).toBeGreaterThan(startIndex);
  return source.slice(startIndex, endIndex);
}

function pythonOverrideString(block: string, field: string): string {
  const match = block.match(new RegExp(`"${field}": "([^"]+)"`));
  expect(match, `missing placement override field: ${field}`).toBeTruthy();
  return match?.[1] ?? '';
}

function pythonOverrideInteger(block: string, field: string): number {
  const match = block.match(new RegExp(`"${field}": (\\d+)`));
  expect(match, `missing placement override field: ${field}`).toBeTruthy();
  return Number(match?.[1]);
}

function collectTypeScriptFiles(relativeRoot: string): string[] {
  const absoluteRoot = resolve(frontendRoot, relativeRoot);
  const files: string[] = [];

  for (const entry of readdirSync(absoluteRoot, { withFileTypes: true })) {
    const relativeEntry = `${relativeRoot}/${entry.name}`;
    if (entry.isDirectory()) {
      if (entry.name !== '__tests__') {
        files.push(...collectTypeScriptFiles(relativeEntry));
      }
      continue;
    }

    if (
      entry.isFile() &&
      /\.(?:ts|tsx)$/.test(entry.name) &&
      !/\.(?:test|stories)\.(?:ts|tsx)$/.test(entry.name)
    ) {
      files.push(relative(frontendRoot, resolve(frontendRoot, relativeEntry)));
    }
  }

  return files;
}

function productionUiSourcePaths(): string[] {
  return [
    ...productionUiEntries,
    ...productionUiRoots.flatMap((root) => collectTypeScriptFiles(root)),
  ]
    .map((path) => path.split(sep).join('/'))
    .sort();
}

function knownDirectAcquisitionSyntaxFragmentIds(source: string): string[] {
  return knownDirectAcquisitionSyntaxFragments
    .filter(({ pattern }) => pattern.test(source))
    .map(({ id }) => id);
}

describe(`current Web monetization posture: ${CURRENT_WEB_MONETIZATION_POSTURE}`, () => {
  it('keeps /pro as a public compatibility route owned by the information-only page', () => {
    const routes = readFrontend('src/config/routes.ts');

    expect(routes).toContain(
      "{ path: '/pro', label: 'Pro', requiresAuth: false, component: ProPaywallPage",
    );
  });

  it('has no retired purchase helper or dialog in the production graph', () => {
    for (const path of retiredPurchasePaths) {
      expect(existsSync(resolve(frontendRoot, path)), `${path} must stay retired`).toBe(false);
    }

    for (const path of correctedBoundaryPaths) {
      const source = readFrontend(path);
      expect(
        knownDirectAcquisitionSyntaxFragmentIds(source),
        `${path} contains a known direct acquisition syntax fragment`,
      ).toEqual([]);
    }
  });

  it('censuses production UI for the finite known direct acquisition syntax fragments', () => {
    const paths = productionUiSourcePaths();

    expect(paths).toContain('src/pages/Pro/ProPaywallPage.tsx');
    expect(paths).toContain('src/components/SoftPaywallHook/SoftPaywallHook.tsx');
    expect(paths).not.toContain('src/config/__tests__/webMonetizationPosture.test.ts');

    for (const path of paths) {
      expect(
        knownDirectAcquisitionSyntaxFragmentIds(readFrontend(path)),
        `${path} contains a known direct acquisition syntax fragment`,
      ).toEqual([]);
    }
  });

  it('detects known direct syntax fragments without treating inert references as calls', () => {
    const directSyntaxCases = [
      ["track.paywallViewed('bmi', 'soft_hook')", 'paywall_view_telemetry_call'],
      ["track?.paywallViewed('bmi', 'soft_hook')", 'paywall_view_telemetry_call'],
      ["vipTelemetry.paywallDismissed('plate', 'close')", 'paywall_dismiss_telemetry_call'],
      ["track.paywallDismissed?.('plate', 'close')", 'paywall_dismiss_telemetry_call'],
      [
        "growthTelemetry.paywallCtaClicked('home', 'learn_more', 'free')",
        'paywall_cta_telemetry_call',
      ],
      [
        "growthTelemetry['paywallCtaClicked']('home', 'learn_more', 'free')",
        'paywall_cta_telemetry_call',
      ],
      ["track.upgradeClicked('home', 'cta')", 'upgrade_telemetry_call'],
      ["vipTelemetry?.['upgradeClicked']?.('home', 'cta')", 'upgrade_telemetry_call'],
      ["growthTelemetry.trialStarted('marketing', 'pro')", 'trial_telemetry_call'],
      ['growthTelemetry["trialStarted"]("marketing", "pro")', 'trial_telemetry_call'],
      ['trackEvent(EventType.PAYWALL_VIEWED, payload)', 'direct_acquisition_event_call'],
      ['trackEvent?.(EventType.PAYWALL_VIEWED, payload)', 'direct_acquisition_event_call'],
      ['trackVipEvent(EventType.PAYWALL_CTA_CLICKED, payload)', 'direct_acquisition_event_call'],
      ['trackEvent(EventType.TRIAL_STARTED, payload)', 'direct_acquisition_event_call'],
      ['trackVipEvent(EventType.VIP_PAYWALL_VIEWED, payload)', 'direct_acquisition_event_call'],
      ['trackEvent(EventType.VIP_PAYWALL_DISMISSED, payload)', 'direct_acquisition_event_call'],
      [
        'telemetry.trackEvent(\n  EventType.VIP_UPGRADE_CLICKED,\n  payload\n)',
        'direct_acquisition_event_call',
      ],
      ['trackVipEvent?.(EventType.VIP_UPGRADE_CLICKED, payload)', 'direct_acquisition_event_call'],
      ["const example = 'track.paywallViewed()';", 'paywall_view_telemetry_call'],
      ['// growthTelemetry["trialStarted"]()', 'trial_telemetry_call'],
      ["import { purchasePremium } from '../lib/paywallPurchase'", 'retired_purchase_helper'],
      ['trackHppPaywallOpenFromLive(payload)', 'live_paywall_telemetry_call'],
    ] as const;

    for (const [source, fragmentId] of directSyntaxCases) {
      expect(knownDirectAcquisitionSyntaxFragmentIds(source), source).toContain(fragmentId);
    }

    const inertCases = [
      "type EventName = 'purchase_attempt'; const endpoint = '/api/v1/payments/verify';",
      'const eventType = EventType.PAYWALL_VIEWED;',
      'type Payload = PaywallViewedPayload;',
      'const schema = EVENT_REGISTRY[EventType.TRIAL_STARTED];',
      'const helper = growthTelemetry.paywallViewed;',
      "const bracketHelper = growthTelemetry['paywallViewed'];",
      'const optionalHelper = track?.paywallDismissed;',
      'const emitter = trackEvent; const eventType = EventType.VIP_PAYWALL_VIEWED;',
      'trackEvent(EventType.VIP_MODULE_VIEWED, payload);',
      'trackEvent(EventType.VIP_FEATURE_CLICKED, payload);',
      'trackVipEvent(EventType.VIP_GATE_INTERACTED, payload);',
      'trackVipEvent(EventType.VIP_BADGE_VIEWED, payload);',
    ] as const;

    for (const source of inertCases) {
      expect(knownDirectAcquisitionSyntaxFragmentIds(source), source).toEqual([]);
    }
  });

  it('derives the exact complete matrix and design-execution identity sets', () => {
    const matrixSource = readRepo('docs/design/PULSEPLATE_BUTTON_ACTION_PROMPT_MATRIX.md');
    const matrixIdentities = matrixRowIdentities(matrixSource);

    expect(new Set(matrixIdentities).size).toBe(matrixIdentities.length);
    expect(matrixIdentities).toHaveLength(completeMatrixIdentities.length);
    expect(sortedUnique(matrixIdentities)).toEqual(sortedUnique(completeMatrixIdentities));
    expect(designExecutionIdentities).toHaveLength(
      completeMatrixIdentities.length - fitChefSupportChoiceIdentities.size,
    );
  });

  it('keeps every finite design registry aligned to the derived non-FitChef subset', () => {
    const expected = sortedUnique(designExecutionIdentities);

    for (const [path, [start, end]] of Object.entries(designRegistrySections)) {
      const registry = sectionBetween(readRepo(path), start, end);
      expect(sortedUnique(registryRowIdentities(registry)), `${path} identity drift`).toEqual(
        expected,
      );
    }
  });

  it('keeps the exact authoritative design chain information-only and self-contained', () => {
    const designSources = authoritativeDesignPaths.map((path) => {
      expect(existsSync(resolve(repoRoot, path)), `${path} must exist`).toBe(true);
      return readRepo(path);
    });
    const designBundle = designSources.join('\n');

    for (const retiredCarrier of [
      'web.home.apple_product_info',
      'web.plate.apple_product_info',
      'web.paywall.modal.cta',
      'web.paywall.modal.cancel',
      'stub://cta/paywall-unlock',
      'BeforeAfter',
      'Unlock Premium',
      'purchaseDisabled',
      'frontend/src/components/__tests__/AppleProductInfoDialog.test.tsx',
    ]) {
      expect(designBundle, `${retiredCarrier} must stay retired`).not.toContain(retiredCarrier);
    }

    for (const path of informationStateDeclarationPaths) {
      expect(
        readRepo(path).replace(/\s+/g, ' '),
        `${path} information-state vocabulary drift`,
      ).toContain(informationStateDeclaration);
    }

    const matrix = readRepo('docs/design/PULSEPLATE_BUTTON_ACTION_PROMPT_MATRIX.md');
    const homeRow = matrix.split('\n').find((line) => line.includes('| `web.home.open_pro` |'));
    const plateRow = matrix
      .split('\n')
      .find((line) => line.includes('| `web.plate.premium_gate_cta` |'));
    expect(homeRow).toContain('Learn about PulsePlate for Apple devices');
    expect(homeRow).toContain('Open the information-only Apple product handoff');
    expect(homeRow).toContain('/marketing');
    expect(homeRow).toContain('PP/Web/Home/GuidedPlanning/AppleProductInfo/Button/Default (TBD)');
    expect(homeRow).toContain('stub://cta/information/apple-product');
    expect(homeRow).toContain('Guided Planning → Next action');
    expect(plateRow).toContain('Learn about PulsePlate for Apple devices');
    expect(plateRow).toContain('Open the information-only Apple product handoff');
    expect(plateRow).toContain('PP/Web/Plate/PremiumGate/AppleProductInfo/Button/Default (TBD)');
    expect(plateRow).toContain('stub://cta/information/apple-product');
    expect(matrix).toContain('Their substrings grant no');
    expect(matrix).toContain('| `web.home.open_pro` | `V3` | `W_HOME_GUIDED_PLANNING_ACTIONS` |');

    const visualForecast = readRepo(
      'docs/design/PULSEPLATE_BUTTON_VISUAL_SYSTEM_TRENDS_AND_FORECAST.md',
    );
    const figmaSpecification = readRepo('docs/figma/PULSEPLATE_FIGMA_DESIGN_SPECIFICATION.md');
    expect(visualForecast).toContain(
      '| `W_HOME_GUIDED_PLANNING_ACTIONS` | Home Guided Planning → Next action |',
    );
    expect(visualForecast).toContain(
      '| Web | Home | `web.home.open_pro` | `W_HOME_GUIDED_PLANNING_ACTIONS` |',
    );
    expect(figmaSpecification).toContain(
      'Guided Planning → Next action (`W_HOME_GUIDED_PLANNING_ACTIONS`)',
    );
  });

  it('keeps generated Home and Plate instructions on the exact safe projections', () => {
    const home = readGeneratedInstruction('scripts/design/instructions/web_home.json');
    const plate = readGeneratedInstruction('scripts/design/instructions/web_plate.json');
    const homeButtons = generatedButtons(home);
    const plateButtons = generatedButtons(plate);
    const expectedHomeKeys = [
      'web.home.open_setup',
      'web.home.open_plate',
      'web.home.open_progress',
      'web.home.open_pro',
    ];
    const expectedPlateKeys = [
      'web.plate.open_setup',
      'web.plate.open_progress',
      'web.plate.premium_gate_cta',
    ];

    expect(homeButtons.map((button) => button.cta_key)).toEqual(expectedHomeKeys);
    expect(plateButtons.map((button) => button.cta_key)).toEqual(expectedPlateKeys);

    expect(home.sections.map((section) => section.section_id)).toEqual([
      'hero-band',
      'quick-actions',
      'guided-planning',
      'footer-nav',
    ]);
    expect(plate.sections.some((section) => section.section_id === 'guided-planning')).toBe(false);
    expect(home.sections.find((section) => section.section_id === 'quick-actions')).toMatchObject({
      component_ids: [
        'web-home-actions',
        'node:web.home.open_setup',
        'node:web.home.open_plate',
        'node:web.home.open_progress',
      ],
    });
    expect(home.sections.find((section) => section.section_id === 'guided-planning')).toEqual({
      section_id: 'guided-planning',
      name: 'Guided Planning → Next action',
      role: 'supporting_action',
      component_ids: ['web-home-guided-planning-actions', 'node:web.home.open_pro'],
    });

    expect(
      home.component_hierarchy.find(
        (node) => node.component_id === 'web-home-guided-planning-actions',
      ),
    ).toEqual({
      component_id: 'web-home-guided-planning-actions',
      canonical_component: 'card',
      section_id: 'guided-planning',
      parent_component_id: 'web-home-shell',
      hierarchy_level: 1,
      semantic_role: 'supporting_action_cluster',
      source_ref: 'override:web.home:guided-planning-actions',
    });
    expect(
      home.component_hierarchy.find((node) => node.component_id === 'node:web.home.open_pro'),
    ).toMatchObject({
      section_id: 'guided-planning',
      parent_component_id: 'web-home-guided-planning-actions',
      hierarchy_level: 2,
    });

    const homeInformation = homeButtons.find((button) => button.cta_key === 'web.home.open_pro');
    const plateInformation = plateButtons.find(
      (button) => button.cta_key === 'web.plate.premium_gate_cta',
    );
    expect(homeInformation).toMatchObject({
      name: 'Learn about PulsePlate for Apple devices',
      style: 'secondary',
      variant: 'V3',
      placement_zone: 'W_HOME_GUIDED_PLANNING_ACTIONS',
      prompt_stub: 'stub://cta/information/apple-product',
      figma_node_id: 'PP/Web/Home/GuidedPlanning/AppleProductInfo/Button/Default (TBD)',
      states: [...informationOnlyWebStates],
      section_id: 'guided-planning',
      component_id: 'node:web.home.open_pro',
      parent_component_id: 'web-home-guided-planning-actions',
      hierarchy_level: 2,
    });
    expect(plateInformation).toMatchObject({
      name: 'Learn about PulsePlate for Apple devices',
      style: 'secondary',
      variant: 'V3',
      prompt_stub: 'stub://cta/information/apple-product',
      figma_node_id: 'PP/Web/Plate/PremiumGate/AppleProductInfo/Button/Default (TBD)',
      states: [...informationOnlyWebStates],
    });

    const generator = readRepo('scripts/design/generate_figma_instructions.py');
    const placementOverrideRegistry = sectionBetween(
      generator,
      'CTA_PLACEMENT_OVERRIDES:',
      '# Screen dimension presets',
    );
    expect(
      [...placementOverrideRegistry.matchAll(/^    "([^"]+)": \{$/gm)].map((match) => match[1]),
    ).toEqual(['web.home.open_pro']);
    const homePlacementOverride = pythonCtaPlacementOverrideBlock(generator, 'web.home.open_pro');
    expect(pythonOverrideString(homePlacementOverride, 'screen_id')).toBe('web.home');
    expect(pythonOverrideString(homePlacementOverride, 'section_id')).toBe('guided-planning');
    expect(pythonOverrideString(homePlacementOverride, 'section_name')).toBe(
      home.sections.find((section) => section.section_id === 'guided-planning')?.name,
    );
    expect(pythonOverrideString(homePlacementOverride, 'section_role')).toBe(
      home.sections.find((section) => section.section_id === 'guided-planning')?.role,
    );
    expect(pythonOverrideString(homePlacementOverride, 'insert_before_section_id')).toBe(
      'footer-nav',
    );
    expect(pythonOverrideString(homePlacementOverride, 'parent_component_id')).toBe(
      'web-home-guided-planning-actions',
    );
    expect(pythonOverrideString(homePlacementOverride, 'parent_parent_component_id')).toBe(
      'web-home-shell',
    );
    expect(pythonOverrideInteger(homePlacementOverride, 'parent_hierarchy_level')).toBe(1);
    expect(pythonOverrideString(homePlacementOverride, 'parent_semantic_role')).toBe(
      'supporting_action_cluster',
    );
    expect(pythonOverrideInteger(homePlacementOverride, 'cta_hierarchy_level')).toBe(2);
    expect(pythonOverrideString(homePlacementOverride, 'placement_zone')).toBe(
      homeInformation?.placement_zone,
    );
    expect(pythonCtaRegistryBlock(generator, 'web.home.open_pro')).toContain(
      'placement_zone=CTA_PLACEMENT_OVERRIDES["web.home.open_pro"]["placement_zone"]',
    );
    expect(pythonCtaStates(generator, 'web.home.open_pro')).toEqual(informationOnlyWebStates);
    expect(pythonCtaStates(generator, 'web.plate.premium_gate_cta')).toEqual(
      informationOnlyWebStates,
    );
    expect(generator).not.toContain('ui_label="Open Pro"');
    expect(generator).not.toContain('ui_label="Unlock Premium"');
    expect(generator).not.toContain('stub://cta/paywall-unlock');

    const premiumGate = readFrontend('src/components/PremiumGate.tsx');
    expect(premiumGate).toMatch(
      /buttonClasses\(\{\s*variant:\s*'secondary',\s*className:\s*'mt-3'\s*\}\)/,
    );
  });

  it('keeps LiveProgressIndicator on ordinary CTA telemetry for information routes', () => {
    const liveIndicator = readFrontend('src/features/progress/LiveProgressIndicator.tsx');

    expect(liveIndicator).not.toContain('trackHppPaywallOpenFromLive');
    expect(liveIndicator).not.toContain('isPaywallCta');
    expect(liveIndicator).not.toContain('/paywall');
    expect(liveIndicator).toContain('trackHppCtaClick(basePayload)');
  });

  it('limits corrected Web actions to free BMI, marketing information, and dismissal', () => {
    const home = readFrontend('src/pages/Home.tsx');
    const teaser = readFrontend('src/components/SoftPaywallHook/SoftPaywallHook.tsx');
    const tiers = readFrontend('src/components/marketing/TiersSection.tsx');
    const proPage = readFrontend('src/pages/Pro/ProPaywallPage.tsx');
    const dialog = readFrontend('src/components/AppleProductInfoDialog.tsx');

    expect(home).not.toContain('to="/pro"');
    expect(teaser).not.toContain("navigate('/pro'");
    expect(tiers).not.toContain("ctaTo: '/pro'");
    expect(proPage).not.toContain('useLocation');

    expect([teaser, tiers, proPage, dialog].join('\n')).toContain('/bmi');
    expect([home, teaser, proPage, dialog].join('\n')).toContain('/marketing');
  });

  it('closes the barrel and Storybook graph over the information component', () => {
    const barrel = readFrontend('src/components/index.ts');
    const storySupport = readFrontend('src/stories/storybookParitySupport.tsx');

    expect(barrel).toContain("from './AppleProductInfoDialog'");
    expect(barrel).not.toContain("from './Paywall/BeforeAfter'");
    expect(storySupport).not.toContain('INTERNAL_PAYWALL_EVENTS_PATH');
    expect(storySupport).not.toContain('PaywallDialogStorySurface');
  });

  it('keeps the exact eight-file authority reconciliation closed and present', () => {
    expect(reconciledAuthorityPaths).toHaveLength(8);
    expect(new Set(reconciledAuthorityPaths).size).toBe(8);

    for (const path of reconciledAuthorityPaths) {
      expect(existsSync(resolve(repoRoot, path)), `${path} must exist`).toBe(true);
    }
  });

  it('keeps visual Template 03 on existing information-only owners and actions', () => {
    const templates = readRepo('docs/design/VISUAL_PR_DESCRIPTION_TEMPLATES.md');
    const template03 = sectionBetween(templates, '## Template 03:', '## Template 04:');

    for (const required of [
      'frontend/src/components/PremiumGate.tsx',
      'frontend/src/components/AppleProductInfoDialog.tsx',
      'Compatibility prompt-pack reference (not runtime authority)',
      'This website is free to use.',
      'We’re designing more advanced FitChef features for PulsePlate on Apple devices.',
      'Purchases are not offered on this website.',
      'We’ll add a verified App Store link when public availability is confirmed.',
      '`Try the free BMI calculator` → `/bmi`',
      '`Learn about PulsePlate for Apple devices` → `/marketing`',
      'Not now',
      'Reuse the existing components, assets, tokens, and visual rules',
    ]) {
      expect(template03).toContain(required);
    }

    for (const retired of ['BeforeAfter', 'Plate/Pro conversion surfaces', 'Unlock Premium']) {
      expect(template03).not.toContain(retired);
    }
  });

  it('keeps the compatibility product doc subordinate to current Web contracts', () => {
    const productDoc = readRepo('docs/product/FREE_PRO_SOFT_PAYWALL.md');
    const currentContract = sectionBetween(
      productDoc,
      '## Current public Web contract',
      '## Canonical sources',
    );
    const canonicalSources = sectionBetween(
      productDoc,
      '## Canonical sources',
      '## Compatibility data boundary',
    );
    const compatibilityBoundary = sectionFrom(productDoc, '## Compatibility data boundary');

    for (const required of [
      'This website is free to use.',
      'PulsePlate on Apple devices.',
      'Purchases are not offered on this website.',
      '`Try the free BMI calculator` → `/bmi`',
      '`Learn about PulsePlate for Apple devices` → `/marketing`',
      'Not now',
    ]) {
      expect(currentContract).toContain(required);
    }
    for (const compatibilityOnlyField of ['limitations', 'next_step', 'ctaAction']) {
      expect(currentContract).not.toContain(compatibilityOnlyField);
    }
    expect(canonicalSources).toContain('docs/contracts/soft_paywall.md');
    expect(canonicalSources).toContain('docs/contracts/PRODUCT_TIER_MAP.md');
    expect(canonicalSources).toContain('appleProduct.*');
    expect(canonicalSources).toContain('availability.pro_available');
    expect(compatibilityBoundary).toContain('`message`, `target`, `limitations`, and');
    expect(compatibilityBoundary).toContain('`next_step`');
    expect(compatibilityBoundary).toContain('cannot author public-Web');
    expect(compatibilityBoundary).toContain('it is not');
    expect(compatibilityBoundary).toContain('proof that a Web purchase');

    for (const compatibilityField of ['limitations', 'next_step']) {
      const fieldPattern = new RegExp(`\\b${compatibilityField}\\b`, 'g');
      expect(
        productDoc.match(fieldPattern),
        `${compatibilityField} full-doc cardinality`,
      ).toHaveLength(1);
      expect(
        compatibilityBoundary.match(fieldPattern),
        `${compatibilityField} compatibility-section cardinality`,
      ).toHaveLength(1);
    }
    expect(productDoc).not.toContain('ctaAction');

    const normalizedProductDoc = productDoc.toLowerCase();
    for (const retiredProposition of [
      'this result is preliminary.',
      'explore extended insights',
      'you understand your risk level.',
      'want to turn this into a personalized nutrition plan?',
      'health risk',
      'extended assessment',
      'personalized nutrition plan',
      'ctaaction',
      'interface softpaywallprops',
      'frontend renders soft paywall based on',
    ]) {
      expect(normalizedProductDoc).not.toContain(retiredProposition);
    }
  });

  it('keeps current public-Web paywall and trial measurement explicitly unavailable', () => {
    for (const path of publicWebMeasurementAuthorityPaths) {
      const source = readRepo(path);
      expect(source, `${path} availability marker drift`).toContain(
        'Current public-Web paywall/trial measurement: **UNAVAILABLE / NOT EMITTED**.',
      );
      expect(source, `${path} outage distinction drift`).toContain(
        'This is the intended current posture, not an outage.',
      );
      expect(source, `${path} measured-zero distinction drift`).toContain(
        'It must not be represented as `0`, `0%`, or any other zero-valued metric.',
      );
      expect(source, `${path} cross-channel boundary drift`).toContain(
        'Apple-device, backend, billing, or subscription observations must not fill a',
      );
      expect(source, `${path} unique-user boundary drift`).toContain(
        'Repeated event rows do not establish unique-user counts.',
      );
    }

    const catalog = readRepo('docs/analytics/METRICS_CATALOG.md');
    expect(catalog.match(/^## Event taxonomy \(growth funnel \+ coaching\)$/gm)).toHaveLength(1);
    const trialToPaid = sectionBetween(catalog, '## Trial -> Paid conversion', '## Retention D30');
    const softPaywall = sectionBetween(catalog, '## Soft paywall view rate', '## Trial start rate');
    const trialStart = sectionBetween(catalog, '## Trial start rate', '## Retention D7');

    for (const metricSection of [trialToPaid, softPaywall, trialStart]) {
      expect(metricSection).toContain('**UNAVAILABLE / NOT EMITTED**');
      expect(metricSection).toContain('not computed');
      expect(metricSection).toContain('distinct_');
    }
  });

  it('keeps public-Web paywall experiments not admitted and historical only', () => {
    const framework = readRepo('docs/analytics/EXPERIMENTATION_FRAMEWORK.md');
    const paywallAdmission = sectionBetween(
      framework,
      '## Public Web paywall experiments: NOT ADMITTED',
      '## Onboarding Optimization Loop',
    );

    expect(paywallAdmission).toContain('did not run and produced no result');
    expect(paywallAdmission).toContain('new external product,');
    expect(paywallAdmission).toContain('legal, and architecture admission');
    expect(framework).not.toMatch(/EXP-PWL-\d{3}/);
    for (const retiredBaseline of ['~15%', '~8%', '~35%']) {
      expect(framework).not.toContain(retiredBaseline);
    }

    const registry = readRepo('docs/analytics/EXPERIMENT_REGISTRY.md');
    const active = sectionBetween(
      registry,
      '## Active Experiments',
      '## Rejected / Not Admitted Experiments',
    );
    const rejected = sectionBetween(
      registry,
      '## Rejected / Not Admitted Experiments',
      '## Completed Experiments',
    );

    expect(rejected).toContain('did not run and produced no result');
    for (const experimentId of rejectedPaywallExperimentIds) {
      expect(active).not.toContain(experimentId);
      expect(rejected.match(new RegExp(experimentId, 'g'))).toHaveLength(1);
      expect(registry.match(new RegExp(experimentId, 'g'))).toHaveLength(1);
      expect(rejected).toMatch(
        new RegExp(
          `${experimentId}[^\\n]+REJECTED / NOT ADMITTED[^\\n]+Did not run[^\\n]+No result`,
        ),
      );
    }
  });

  it('keeps telemetry documentation at compatibility evidence levels', () => {
    const telemetryDoc = readRepo('frontend/src/lib/telemetry.md');
    const normalizedTelemetryDoc = telemetryDoc.toLowerCase();
    const evidenceLevels = sectionBetween(
      telemetryDoc,
      '## Evidence levels',
      '## Current public-Web applicability',
    );
    const featureFlagBoundary = sectionBetween(
      telemetryDoc,
      '## Feature-flag boundary',
      '## Data and privacy claims',
    );

    for (const level of [
      '**Defined**',
      '**Callable**',
      '**Test-called**',
      '**Production-called**',
      '**Delivered**',
      '**Stored**',
      '**Queryable**',
    ]) {
      expect(evidenceLevels).toContain(level);
    }
    expect(featureFlagBoundary).toContain('only permits an explicit existing caller');
    expect(featureFlagBoundary).toContain('does not mount a hook');

    for (const executableExample of [
      'vipTelemetry.paywallViewed(',
      'vipTelemetry.upgradeClicked(',
      'growthTelemetry.trialStarted(',
      '```typescript',
    ]) {
      expect(telemetryDoc).not.toContain(executableExample);
    }
    for (const unsupportedClaimSeed of [
      'automatically tracks',
      'automatically emits',
      'automatically emitted',
      'tracks automatically',
      'auto-tracking',
      'emits on mount',
      'emitted on mount',
      'tracks on mount',
    ]) {
      expect(normalizedTelemetryDoc).not.toContain(unsupportedClaimSeed);
    }
    expect(normalizedTelemetryDoc).toContain('current ui does not invoke');
    expect(normalizedTelemetryDoc).toContain('does not mount a hook');
    expect(normalizedTelemetryDoc).toContain('unavailable / not emitted');
  });

  it('keeps the same Apple-device information propositions in EN, RU, and ES', () => {
    const locales = ['en', 'ru', 'es'].map(
      (locale) =>
        JSON.parse(readFrontend(`src/locales/${locale}.json`)) as {
          appleProduct: Record<string, string>;
        },
    );
    const expectedKeys = [
      'title',
      'websiteFree',
      'fitChefDirection',
      'noWebPurchases',
      'storeLinkLater',
      'tryFreeBmi',
      'learnMore',
      'notNow',
      'close',
      'softHeading',
    ];

    for (const locale of locales) {
      expect(Object.keys(locale.appleProduct).sort()).toEqual(expectedKeys.sort());
      for (const value of Object.values(locale.appleProduct)) {
        expect(value.trim()).not.toBe('');
      }
    }
  });
});
