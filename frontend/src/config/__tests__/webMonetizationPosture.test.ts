import { existsSync, readFileSync, readdirSync } from 'node:fs';
import { relative, resolve, sep } from 'node:path';
import { describe, expect, it } from 'vitest';

const frontendRoot = resolve(__dirname, '../../..');

const CURRENT_WEB_MONETIZATION_POSTURE = 'free-informational-apple-product' as const;

const correctedBoundaryPaths = [
  'src/components/AppleProductInfoDialog.tsx',
  'src/components/PremiumGate.tsx',
  'src/components/SoftPaywallHook/SoftPaywallHook.tsx',
  'src/components/VipGate.tsx',
  'src/components/index.ts',
  'src/components/marketing/TiersSection.tsx',
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
