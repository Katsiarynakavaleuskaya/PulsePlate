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
  (identity) => !fitChefSupportChoiceIdentities.has(identity)
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

const productionUiRoots = [
  'src/components',
  'src/features',
  'src/hooks',
  'src/pages',
] as const;

const productionUiEntries = ['src/App.tsx', 'src/main.tsx', 'src/config/routes.ts'] as const;

const knownExecutableCarriers = [
  {
    id: 'retired_before_after_import',
    pattern: /from\s+['"][^'"]*Paywall\/BeforeAfter['"]|<BeforeAfter\b/,
  },
  {
    id: 'retired_purchase_helper',
    pattern: /from\s+['"][^'"]*lib\/paywallPurchase['"]|\bpurchasePremium\s*\(/,
  },
  { id: 'purchase_callback', pattern: /\bonPurchase\s*=/ },
  { id: 'upgrade_telemetry_call', pattern: /\.\s*upgradeClicked\s*\(/ },
  { id: 'trial_telemetry_call', pattern: /\.\s*trialStarted\s*\(/ },
  { id: 'paywall_exposure_call', pattern: /\blogPaywallExposure\s*\(/ },
  {
    id: 'live_paywall_telemetry_call',
    pattern: /\btrackHppPaywallOpenFromLive\s*\(/,
  },
  {
    id: 'acquisition_event_emission',
    pattern: /\blog\s*\(\s*Events\.(?:PURCHASE_ATTEMPT|PURCHASE_SUCCESS|PURCHASE_FAILURE|RESTORE_SUCCESS)\b/,
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
    (match) => match[1]
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
  prompt_stub?: string;
  figma_node_id?: string;
  states?: string[];
}

interface GeneratedScreenInstruction {
  screen_id: string;
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

function executableCarrierIds(source: string): string[] {
  return knownExecutableCarriers
    .filter(({ pattern }) => pattern.test(source))
    .map(({ id }) => id);
}

describe(`current Web monetization posture: ${CURRENT_WEB_MONETIZATION_POSTURE}`, () => {
  it('keeps /pro as a public compatibility route owned by the information-only page', () => {
    const routes = readFrontend('src/config/routes.ts');

    expect(routes).toContain("{ path: '/pro', label: 'Pro', requiresAuth: false, component: ProPaywallPage");
  });

  it('has no retired purchase helper or dialog in the production graph', () => {
    for (const path of retiredPurchasePaths) {
      expect(existsSync(resolve(frontendRoot, path)), `${path} must stay retired`).toBe(false);
    }

    for (const path of correctedBoundaryPaths) {
      const source = readFrontend(path);
      expect(executableCarrierIds(source), `${path} must stay information-only`).toEqual([]);
    }
  });

  it('mechanically censuses current production UI owners for known acquisition carriers', () => {
    const paths = productionUiSourcePaths();

    expect(paths).toContain('src/pages/Pro/ProPaywallPage.tsx');
    expect(paths).toContain('src/components/SoftPaywallHook/SoftPaywallHook.tsx');
    expect(paths).not.toContain('src/config/__tests__/webMonetizationPosture.test.ts');

    for (const path of paths) {
      expect(executableCarrierIds(readFrontend(path)), `${path} has an acquisition carrier`).toEqual(
        []
      );
    }
  });

  it('detects executable carriers without treating inert contract identifiers as actions', () => {
    expect(executableCarrierIds("track.upgradeClicked('home', 'cta')")).toContain(
      'upgrade_telemetry_call'
    );
    expect(executableCarrierIds("import { purchasePremium } from '../lib/paywallPurchase'")).toContain(
      'retired_purchase_helper'
    );
    expect(
      executableCarrierIds(
        "type EventName = 'purchase_attempt'; const endpoint = '/api/v1/payments/verify';"
      )
    ).toEqual([]);
    expect(executableCarrierIds('trackHppPaywallOpenFromLive(payload)')).toContain(
      'live_paywall_telemetry_call'
    );
  });

  it('derives the exact complete matrix and design-execution identity sets', () => {
    const matrixSource = readRepo('docs/design/PULSEPLATE_BUTTON_ACTION_PROMPT_MATRIX.md');
    const matrixIdentities = matrixRowIdentities(matrixSource);

    expect(new Set(matrixIdentities).size).toBe(matrixIdentities.length);
    expect(matrixIdentities).toHaveLength(completeMatrixIdentities.length);
    expect(sortedUnique(matrixIdentities)).toEqual(sortedUnique(completeMatrixIdentities));
    expect(designExecutionIdentities).toHaveLength(
      completeMatrixIdentities.length - fitChefSupportChoiceIdentities.size
    );
  });

  it('keeps every finite design registry aligned to the derived non-FitChef subset', () => {
    const expected = sortedUnique(designExecutionIdentities);

    for (const [path, [start, end]] of Object.entries(designRegistrySections)) {
      const registry = sectionBetween(readRepo(path), start, end);
      expect(sortedUnique(registryRowIdentities(registry)), `${path} identity drift`).toEqual(
        expected
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
        `${path} information-state vocabulary drift`
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
    expect(plateRow).toContain('Learn about PulsePlate for Apple devices');
    expect(plateRow).toContain('Open the information-only Apple product handoff');
    expect(plateRow).toContain('PP/Web/Plate/PremiumGate/AppleProductInfo/Button/Default (TBD)');
    expect(plateRow).toContain('stub://cta/information/apple-product');
    expect(matrix).toContain('Their substrings grant no');
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

    const homeInformation = homeButtons.find((button) => button.cta_key === 'web.home.open_pro');
    const plateInformation = plateButtons.find(
      (button) => button.cta_key === 'web.plate.premium_gate_cta'
    );
    expect(homeInformation).toMatchObject({
      name: 'Learn about PulsePlate for Apple devices',
      style: 'secondary',
      variant: 'V3',
      prompt_stub: 'stub://cta/information/apple-product',
      figma_node_id: 'PP/Web/Home/GuidedPlanning/AppleProductInfo/Button/Default (TBD)',
      states: [...informationOnlyWebStates],
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
    expect(pythonCtaStates(generator, 'web.home.open_pro')).toEqual(informationOnlyWebStates);
    expect(pythonCtaStates(generator, 'web.plate.premium_gate_cta')).toEqual(
      informationOnlyWebStates
    );
    expect(generator).not.toContain('ui_label="Open Pro"');
    expect(generator).not.toContain('ui_label="Unlock Premium"');
    expect(generator).not.toContain('stub://cta/paywall-unlock');

    const premiumGate = readFrontend('src/components/PremiumGate.tsx');
    expect(premiumGate).toMatch(
      /buttonClasses\(\{\s*variant:\s*'secondary',\s*className:\s*'mt-3'\s*\}\)/
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

  it('keeps the same Apple-device information propositions in EN, RU, and ES', () => {
    const locales = ['en', 'ru', 'es'].map((locale) =>
      JSON.parse(readFrontend(`src/locales/${locale}.json`)) as {
        appleProduct: Record<string, string>;
      }
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
