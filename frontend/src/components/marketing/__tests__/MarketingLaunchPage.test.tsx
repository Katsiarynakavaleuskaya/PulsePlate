/** @vitest-environment jsdom */
import { readFileSync, readdirSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe } from 'jest-axe';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';
import PulsePlateMarketingPage from '../../../pages/Marketing/PulsePlateMarketingPage';
import {
  FITCHEF_DEMO_INITIAL_STATE,
  FitChefValueDemo,
  fitChefValueDemoReducer,
} from '../FitChefValueDemo';
import type { FitChefDemoEvent, FitChefDemoState } from '../FitChefValueDemo';

const currentDirectory = dirname(fileURLToPath(import.meta.url));
const componentPath = resolve(currentDirectory, '../FitChefValueDemo.tsx');
const marketingComponentsDirectory = resolve(currentDirectory, '..');
const frontendSourceDirectory = resolve(currentDirectory, '../../..');
const storybookConfigDirectory = resolve(currentDirectory, '../../../../.storybook');
const marketingPagePath = resolve(
  currentDirectory,
  '../../../pages/Marketing/PulsePlateMarketingPage.tsx',
);
const routesPath = resolve(currentDirectory, '../../../config/routes.ts');
const marketingStylesPath = resolve(currentDirectory, '../marketing.css');

const excludedSourceDirectories = new Set(['__tests__', '__snapshots__', 'evidence']);

function collectTypeScriptSources(
  directory: string,
  { excludeStories }: { excludeStories: boolean },
): string[] {
  return readdirSync(directory, { withFileTypes: true })
    .flatMap((entry) => {
      const path = resolve(directory, entry.name);

      if (entry.isDirectory()) {
        return excludedSourceDirectories.has(entry.name)
          ? []
          : collectTypeScriptSources(path, { excludeStories });
      }

      if (!entry.isFile() || !/\.(ts|tsx)$/.test(entry.name)) {
        return [];
      }
      if (/\.(test|spec)\.(ts|tsx)$/.test(entry.name)) {
        return [];
      }
      if (excludeStories && /\.stories\.(ts|tsx)$/.test(entry.name)) {
        return [];
      }

      return [path];
    })
    .sort();
}

const marketingProductionModulePaths = collectTypeScriptSources(marketingComponentsDirectory, {
  excludeStories: true,
});
const marketingRuntimeSourcePaths = Array.from(
  new Set([...marketingProductionModulePaths, marketingPagePath, routesPath]),
).sort();
const frontendTypeScriptSources = collectTypeScriptSources(frontendSourceDirectory, {
  excludeStories: false,
});
const storybookSourcePaths = Array.from(
  new Set([
    ...collectTypeScriptSources(storybookConfigDirectory, { excludeStories: false }),
    ...frontendTypeScriptSources.filter(
      (path) => /\.stories\.(ts|tsx)$/.test(path) || path.includes('/src/stories/'),
    ),
  ]),
).sort();
const h2CensusSourcePaths = Array.from(
  new Set([...marketingRuntimeSourcePaths, ...storybookSourcePaths]),
).sort();

const renderMarketingPage = (): ReturnType<typeof render> =>
  render(
    <MemoryRouter>
      <PulsePlateMarketingPage />
    </MemoryRouter>,
  );

afterEach((): void => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

const demoStates = {
  idle: FITCHEF_DEMO_INITIAL_STATE,
  selectedToday: { status: 'selected', choice: 'today' },
  selectedWeek: { status: 'selected', choice: 'week' },
  revealedToday: { status: 'revealed', choice: 'today' },
  revealedWeek: { status: 'revealed', choice: 'week' },
} satisfies Record<string, FitChefDemoState>;

const demoEvents = {
  selectToday: { type: 'select', choice: 'today' },
  selectWeek: { type: 'select', choice: 'week' },
  confirm: { type: 'confirm' },
  reset: { type: 'reset' },
} satisfies Record<string, FitChefDemoEvent>;

type DemoStateName = keyof typeof demoStates;
type DemoEventName = keyof typeof demoEvents;
type ReferenceExpectation = 'same' | 'new' | 'initial';

const transitionTable: ReadonlyArray<{
  from: DemoStateName;
  event: DemoEventName;
  to: DemoStateName;
  reference: ReferenceExpectation;
}> = [
  { from: 'idle', event: 'selectToday', to: 'selectedToday', reference: 'new' },
  { from: 'idle', event: 'selectWeek', to: 'selectedWeek', reference: 'new' },
  { from: 'idle', event: 'confirm', to: 'idle', reference: 'same' },
  { from: 'idle', event: 'reset', to: 'idle', reference: 'same' },

  { from: 'selectedToday', event: 'selectToday', to: 'selectedToday', reference: 'same' },
  { from: 'selectedToday', event: 'selectWeek', to: 'selectedWeek', reference: 'new' },
  { from: 'selectedToday', event: 'confirm', to: 'revealedToday', reference: 'new' },
  { from: 'selectedToday', event: 'reset', to: 'idle', reference: 'initial' },

  { from: 'selectedWeek', event: 'selectToday', to: 'selectedToday', reference: 'new' },
  { from: 'selectedWeek', event: 'selectWeek', to: 'selectedWeek', reference: 'same' },
  { from: 'selectedWeek', event: 'confirm', to: 'revealedWeek', reference: 'new' },
  { from: 'selectedWeek', event: 'reset', to: 'idle', reference: 'initial' },

  { from: 'revealedToday', event: 'selectToday', to: 'revealedToday', reference: 'same' },
  { from: 'revealedToday', event: 'selectWeek', to: 'selectedWeek', reference: 'new' },
  { from: 'revealedToday', event: 'confirm', to: 'revealedToday', reference: 'same' },
  { from: 'revealedToday', event: 'reset', to: 'idle', reference: 'initial' },

  { from: 'revealedWeek', event: 'selectToday', to: 'selectedToday', reference: 'new' },
  { from: 'revealedWeek', event: 'selectWeek', to: 'revealedWeek', reference: 'same' },
  { from: 'revealedWeek', event: 'confirm', to: 'revealedWeek', reference: 'same' },
  { from: 'revealedWeek', event: 'reset', to: 'idle', reference: 'initial' },
];

describe('FitChef demo reducer', (): void => {
  it('exhaustively covers all five states by all four valid events', (): void => {
    expect(transitionTable).toHaveLength(20);
    expect(new Set(transitionTable.map(({ from, event }) => `${from}:${event}`)).size).toBe(20);

    transitionTable.forEach(({ from, event, to, reference }) => {
      const sourceState = demoStates[from];
      const result = fitChefValueDemoReducer(sourceState, demoEvents[event]);

      expect(result).toEqual(demoStates[to]);
      if (reference === 'same') {
        expect(result).toBe(sourceState);
      } else if (reference === 'initial') {
        expect(result).toBe(FITCHEF_DEMO_INITIAL_STATE);
        expect(result).not.toBe(sourceState);
      } else {
        expect(result).not.toBe(sourceState);
      }
    });
  });

  it('fails closed for malformed and unknown event families from every state', (): void => {
    const malformedEvents: unknown[] = [
      undefined,
      null,
      false,
      0,
      '',
      [],
      {},
      { choice: 'today' },
      { type: null },
      { type: 'select' },
      { type: 'select', choice: null },
      { type: 'select', choice: 'month' },
      { type: 'open' },
      Symbol('unknown-event'),
    ];

    Object.values(demoStates).forEach((state) => {
      malformedEvents.forEach((event) => {
        expect(fitChefValueDemoReducer(state, event)).toBe(state);
      });
    });
  });
});

describe('FitChefValueDemo', (): void => {
  it('renders every approved copy item and both confirmed correspondences inside the demo', async () => {
    const user = userEvent.setup();
    const { container } = render(<FitChefValueDemo />);
    const demoSection = container.querySelector('#fitchef-demo');

    if (!(demoSection instanceof HTMLElement)) {
      throw new Error('FitChef demo section not found');
    }

    const demo = within(demoSection);

    expect(
      demo.getByRole('heading', {
        level: 2,
        name: 'See how FitChef helps you choose where to start',
      }),
    ).toBeVisible();
    expect(demo.getByText('Where would you like to start?')).toBeVisible();
    expect(demo.getByText('FitChef shows both options. The choice is yours.')).toBeVisible();
    expect(demo.getByText('Today')).toBeVisible();
    expect(demo.getByText('Start with the plan for today.')).toBeVisible();
    expect(demo.getByText('This week')).toBeVisible();
    expect(demo.getByText('Look at the next seven days.')).toBeVisible();
    expect(
      demo.getByText(
        'For now, you’re only choosing where to start. Nothing will open, be saved, or change.',
      ),
    ).toBeVisible();
    expect(demo.getByText('For everyday planning — not medical advice.')).toBeVisible();
    expect(
      demo.getByText(
        'This is a prepared website example. It does not run AI, use personal data, open anything, or change a plan.',
      ),
    ).toBeVisible();

    const confirm = demo.getByRole('button', { name: 'Confirm choice' });
    const notNow = demo.getByRole('button', { name: 'Not now' });
    expect(confirm).toBeDisabled();
    expect(confirm).toHaveClass('ppm-fitchef-confirm');
    expect(notNow).toBeEnabled();
    expect(notNow).toHaveClass('ppm-fitchef-secondary');
    expect(demo.queryByRole('heading', { name: 'A place to begin' })).not.toBeInTheDocument();
    expect(demoSection.querySelectorAll('a')).toHaveLength(0);

    await user.click(demo.getByRole('radio', { name: /Today/ }));
    expect(confirm).toBeEnabled();
    expect(demo.queryByRole('heading', { name: 'A place to begin' })).not.toBeInTheDocument();
    await user.click(confirm);

    expect(demo.getByRole('heading', { name: 'A place to begin' })).toBeVisible();
    expect(demo.getByText('For today, FitChef would point to Daily Plate.')).toBeVisible();
    expect(demo.getByRole('status')).toHaveAttribute('aria-live', 'polite');
    expect(demo.getByRole('status').querySelector('a, button')).toBeNull();

    await user.click(demo.getByRole('radio', { name: /This week/ }));
    expect(demo.queryByText('For today, FitChef would point to Daily Plate.')).not.toBeInTheDocument();
    expect(demo.queryByRole('heading', { name: 'A place to begin' })).not.toBeInTheDocument();
    await user.click(confirm);

    expect(demo.getByRole('heading', { name: 'A place to begin' })).toBeVisible();
    expect(
      demo.getByText('For this week, FitChef would point to Weekly Planning.'),
    ).toBeVisible();
    expect(demoSection.querySelectorAll('a')).toHaveLength(0);
  });

  it('clears a revealed result immediately when the choice changes', async () => {
    const user = userEvent.setup();
    render(<FitChefValueDemo />);

    await user.click(screen.getByRole('radio', { name: /Today/ }));
    await user.click(screen.getByRole('button', { name: 'Confirm choice' }));
    expect(screen.getByText('For today, FitChef would point to Daily Plate.')).toBeVisible();

    await user.click(screen.getByRole('radio', { name: /This week/ }));

    expect(screen.queryByText('For today, FitChef would point to Daily Plate.')).not.toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: 'A place to begin' })).not.toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Confirm choice' }));
    expect(
      screen.getByText('For this week, FitChef would point to Weekly Planning.'),
    ).toBeVisible();
  });

  it('resets from every interactive state and remounts in idle', async () => {
    const user = userEvent.setup();
    const firstRender = render(<FitChefValueDemo />);
    const notNow = screen.getByRole('button', { name: 'Not now' });

    expect(notNow).toBeEnabled();
    await user.click(notNow);
    await user.click(screen.getByRole('radio', { name: /Today/ }));
    await user.click(notNow);
    screen.getAllByRole('radio').forEach((radio) => expect(radio).not.toBeChecked());

    await user.click(screen.getByRole('radio', { name: /This week/ }));
    await user.click(screen.getByRole('button', { name: 'Confirm choice' }));
    await user.click(notNow);
    expect(screen.queryByRole('heading', { name: 'A place to begin' })).not.toBeInTheDocument();

    firstRender.unmount();
    render(<FitChefValueDemo />);

    expect(screen.getByRole('button', { name: 'Confirm choice' })).toBeDisabled();
    screen.getAllByRole('radio').forEach((radio) => expect(radio).not.toBeChecked());
  });

  it('supports the native keyboard path and exposes non-color selection state', async () => {
    const user = userEvent.setup();
    render(<FitChefValueDemo />);

    const today = screen.getByRole('radio', { name: /Today/ });
    const week = screen.getByRole('radio', { name: /This week/ });

    await user.tab();
    expect(today).toHaveFocus();
    await user.keyboard('[Space]');
    expect(today).toBeChecked();
    expect(today).toHaveAttribute('aria-checked', 'true');
    expect(today.closest('label')).toHaveClass('ppm-fitchef-option--selected');

    await user.keyboard('[ArrowRight]');
    expect(week).toHaveFocus();
    expect(week).toBeChecked();
    expect(week).toHaveAttribute('aria-checked', 'true');
    expect(today).toHaveAttribute('aria-checked', 'false');

    await user.tab();
    expect(screen.getByRole('button', { name: 'Confirm choice' })).toHaveFocus();
    await user.keyboard('[Enter]');
    expect(
      screen.getByText('For this week, FitChef would point to Weekly Planning.'),
    ).toBeVisible();
  });

  it('has no demo-local network, storage, cookie, or beacon side effects', async () => {
    const user = userEvent.setup();
    const fetchSpy = vi.fn();
    const xhrSpy = vi.fn();
    const webSocketSpy = vi.fn();
    const indexedDbOpenSpy = vi.fn();
    const indexedDbDeleteSpy = vi.fn();
    const beaconSpy = vi.fn();
    const storageGetSpy = vi.spyOn(Storage.prototype, 'getItem');
    const storageSetSpy = vi.spyOn(Storage.prototype, 'setItem');
    const storageRemoveSpy = vi.spyOn(Storage.prototype, 'removeItem');
    const storageClearSpy = vi.spyOn(Storage.prototype, 'clear');
    const cookieBefore = document.cookie;
    const beaconDescriptor = Object.getOwnPropertyDescriptor(navigator, 'sendBeacon');

    vi.stubGlobal('fetch', fetchSpy);
    vi.stubGlobal('XMLHttpRequest', xhrSpy);
    vi.stubGlobal('WebSocket', webSocketSpy);
    vi.stubGlobal('indexedDB', {
      open: indexedDbOpenSpy,
      deleteDatabase: indexedDbDeleteSpy,
    });
    Object.defineProperty(navigator, 'sendBeacon', {
      configurable: true,
      value: beaconSpy,
    });

    try {
      render(<FitChefValueDemo />);
      await user.click(screen.getByRole('radio', { name: /Today/ }));
      await user.click(screen.getByRole('button', { name: 'Confirm choice' }));
      await user.click(screen.getByRole('radio', { name: /This week/ }));
      await user.click(screen.getByRole('button', { name: 'Confirm choice' }));
      await user.click(screen.getByRole('button', { name: 'Not now' }));

      expect(fetchSpy).not.toHaveBeenCalled();
      expect(xhrSpy).not.toHaveBeenCalled();
      expect(webSocketSpy).not.toHaveBeenCalled();
      expect(beaconSpy).not.toHaveBeenCalled();
      expect(indexedDbOpenSpy).not.toHaveBeenCalled();
      expect(indexedDbDeleteSpy).not.toHaveBeenCalled();
      expect(storageGetSpy).not.toHaveBeenCalled();
      expect(storageSetSpy).not.toHaveBeenCalled();
      expect(storageRemoveSpy).not.toHaveBeenCalled();
      expect(storageClearSpy).not.toHaveBeenCalled();
      expect(document.cookie).toBe(cookieBefore);
    } finally {
      if (beaconDescriptor) {
        Object.defineProperty(navigator, 'sendBeacon', beaconDescriptor);
      } else {
        Reflect.deleteProperty(navigator, 'sendBeacon');
      }
    }
  });

  it('passes targeted accessibility checks', async () => {
    const { container } = render(<FitChefValueDemo />);

    expect(await axe(container)).toHaveNoViolations();
  });

  it('passes targeted accessibility checks after a result is revealed', async () => {
    const user = userEvent.setup();
    const { container } = render(<FitChefValueDemo />);

    await user.click(screen.getByRole('radio', { name: /Today/ }));
    await user.click(screen.getByRole('button', { name: 'Confirm choice' }));
    expect(screen.getByText('For today, FitChef would point to Daily Plate.')).toBeVisible();

    expect(await axe(container)).toHaveNoViolations();
  });

  it('keeps imports and runtime constructs inside the static preview boundary', () => {
    const source = readFileSync(componentPath, 'utf8');
    const importSpecifiers = Array.from(source.matchAll(/from\s+['"]([^'"]+)['"]/g), (match) =>
      match[1],
    );

    expect(new Set(importSpecifiers)).toEqual(
      new Set([
        'react',
        '../../assets/brand/fitchef-onboarding-welcome-v1.png',
        '../ui/Button',
        '../ui/Card',
        '../ui/RadioGroup',
        './MarketingPrimitives',
      ]),
    );
    expect(source).not.toMatch(
      /\b(useEffect|fetch|XMLHttpRequest|WebSocket|sendBeacon|localStorage|sessionStorage|indexedDB|setTimeout|setInterval|Promise)\b/,
    );
    expect(source).not.toMatch(/\bimport\s*\(/);
    expect(source).not.toMatch(/\b(gtag|dataLayer|PaymentRequest|cookieStore)\b|document\.cookie/);
    expect(source).not.toMatch(/\b(location|history)\b/);
    expect(importSpecifiers.join('\n')).not.toMatch(
      /api|auth|analytics|storage|payment|outcome|provider|rag|llm|SupportChoiceCard/i,
    );
  });

  it('keeps comparison candidates out of the complete finite marketing and Storybook census', () => {
    const marketingRuntimeGraph = marketingRuntimeSourcePaths
      .map((path) => readFileSync(path, 'utf8'))
      .join('\n');
    const storybookGraph = storybookSourcePaths
      .map((path) => readFileSync(path, 'utf8'))
      .join('\n');
    const completeCensusGraph = h2CensusSourcePaths
      .map((path) => readFileSync(path, 'utf8'))
      .join('\n');
    const comparisonTogglePattern =
      /(?:fitchef|marketing)[^\n]{0,120}(?:candidate[_-]?y|guided[_-]?reveal|variant[_-]?h2)|(?:candidate[_-]?y|guided[_-]?reveal|variant[_-]?h2)[^\n]{0,120}(?:fitchef|marketing)/i;

    expect(marketingProductionModulePaths).toContain(componentPath);
    expect(marketingRuntimeSourcePaths).toEqual(
      expect.arrayContaining([componentPath, marketingPagePath, routesPath]),
    );
    expect(storybookSourcePaths.length).toBeGreaterThan(2);
    expect(completeCensusGraph).not.toMatch(/Candidate Y|Guided Reveal|FitChefValueDemoH2/i);
    expect(completeCensusGraph).not.toMatch(comparisonTogglePattern);
    expect(marketingRuntimeGraph).not.toMatch(/searchParams|URLSearchParams/);
    expect(storybookGraph).not.toMatch(comparisonTogglePattern);
  });

  it('declares focus, reduced-motion, touch-target, and narrow-layout safeguards', () => {
    const styles = readFileSync(marketingStylesPath, 'utf8');

    expect(styles).toMatch(/\.ppm-fitchef-option:has\(input:focus-visible\)/);
    expect(styles).toMatch(/\.ppm-fitchef-option input:focus-visible/);
    expect(styles).toMatch(/min-height:\s*var\(--spacing-touch-large\)/);
    expect(styles).toMatch(/@media \(prefers-reduced-motion: reduce\)/);
    expect(styles).toMatch(/overflow-wrap:\s*anywhere/);
    expect(styles).toMatch(/@media \(max-width: 768px\)/);
    expect(styles).toMatch(
      /\.ppm-page \.ppm-btn--primary\s*\{[^}]*background:\s*var\(--color-blue-600\)/s,
    );
    expect(styles).toMatch(
      /\.ppm-page \.ppm-fitchef-confirm\s*\{[^}]*background:\s*var\(--color-blue-600\)/s,
    );
    expect(styles).toMatch(
      /\.ppm-page \.ppm-fitchef-secondary\s*\{[^}]*background:\s*rgba\(255, 255, 255, 0\.05\)/s,
    );
    expect(styles).toMatch(/\.ppm-step-grid\s*\{[^}]*repeat\(4, minmax\(0, 1fr\)\)/s);
    expect(styles).toMatch(/\.ppm-step-card\s*\{[^}]*height:\s*100%/s);
    expect(styles).not.toContain('color: var(--ppm-slate-500)');
  });

  it('keeps the finite retired-phrase list out of the complete production marketing census', () => {
    const completeMarketingCopy = marketingRuntimeSourcePaths
      .map((path) => readFileSync(path, 'utf8'))
      .join('\n');
    const normalizedCompleteMarketingCopy = completeMarketingCopy
      .toLowerCase()
      .replaceAll('’', "'");
    const finiteRetiredGenericPhrases = [
      'at your own pace',
      'what feels useful',
      'starting point',
      "what we're building",
      'friendly look',
      'choose at your pace',
      'clear words about',
    ];

    finiteRetiredGenericPhrases.forEach((phrase) => {
      expect(normalizedCompleteMarketingCopy).not.toContain(phrase);
    });
    expect(completeMarketingCopy).not.toMatch(
      /product direction|availability claim|unverified Store link/i,
    );
  });
});

describe('PulsePlateMarketingPage', (): void => {
  it('mounts one shared FitChef demo under one document heading', () => {
    renderMarketingPage();

    expect(screen.getByTestId('marketing-page')).toBeInTheDocument();
    expect(screen.getAllByRole('heading', { level: 1 })).toHaveLength(1);
    expect(
      screen.getByRole('heading', {
        level: 1,
        name: 'Check your BMI and see how FitChef works',
      }),
    ).toBeVisible();
    expect(screen.getAllByTestId('fitchef-value-demo')).toHaveLength(1);
  });

  it('binds exact concrete copy to the intended semantic elements and multiplicity', () => {
    const { container } = renderMarketingPage();
    const requiredElement = (selector: string): HTMLElement => {
      const element = container.querySelector(selector);

      if (!(element instanceof HTMLElement)) {
        throw new Error(`Marketing element not found: ${selector}`);
      }

      return element;
    };
    const exactText = (element: Element | null, context: string): string => {
      if (!element) {
        throw new Error(`Marketing copy element not found: ${context}`);
      }

      return (element.textContent ?? '').replace(/\s+/g, ' ').trim();
    };
    const exactTexts = (root: ParentNode, selector: string): string[] =>
      Array.from(root.querySelectorAll(selector), (element) => exactText(element, selector));

    const hero = requiredElement('#top');
    expect(exactText(hero.querySelector('.ppm-hero-copy > .ppm-eyebrow'), 'hero eyebrow')).toBe(
      'Free on the web',
    );
    expect(exactText(within(hero).getByRole('heading', { level: 1 }), 'hero h1')).toBe(
      'Check your BMI and see how FitChef works',
    );
    expect(exactText(hero.querySelector('.ppm-hero-body'), 'hero body')).toBe(
      'Use the free BMI calculator, or choose Today or This week in the FitChef preview to see whether it points to Daily Plate or Weekly Planning.',
    );
    expect(exactTexts(hero, '.ppm-actions .ppm-btn')).toEqual([
      'See how FitChef works',
      'Try the free BMI calculator',
    ]);
    expect(exactTexts(hero, '.ppm-pill-row > .ppm-pill')).toEqual([
      'Free website',
      'No purchases here',
      'Prepared FitChef preview',
    ]);
    expect(exactTexts(hero, '.ppm-action-card .ppm-action-text')).toEqual([
      'Daily Plate',
      'Free BMI calculator',
      'FitChef choice',
      'Weekly Planning',
    ]);
    expect(exactTexts(hero, '.ppm-action-card .ppm-action-helper')).toEqual([
      'For today',
      'On this website',
      'Today or this week',
      'For seven days',
    ]);
    expect(exactTexts(hero, '.ppm-stat-card .ppm-stat-label')).toEqual([
      'Website',
      'FitChef',
      'Today',
      'This week',
    ]);
    expect(exactTexts(hero, '.ppm-stat-card .ppm-stat-value')).toEqual([
      'Free BMI calculator',
      'Today or this week',
      'Daily Plate',
      'Weekly Planning',
    ]);
    expect(exactText(hero.querySelector('.ppm-fitchef-copy'), 'hero FitChef description')).toBe(
      'A short preview of how FitChef connects a choice to a planning view.',
    );
    expect(exactTexts(hero, '.ppm-preview > .ppm-preview-row > .ppm-pill')).toEqual([
      'Prepared example',
      'Nothing is saved',
    ]);
    expect(
      exactText(
        hero.querySelector('.ppm-subsection > .ppm-preview-row .ppm-subsection-title'),
        'hero choice subsection title',
      ),
    ).toBe('Try the two choices');
    expect(
      exactText(
        hero.querySelector('.ppm-subsection > .ppm-preview-row .ppm-subsection-meta'),
        'hero choice subsection meta',
      ),
    ).toBe('Today or this week');
    expect(
      exactText(hero.querySelector('.ppm-insight-card .ppm-subsection-title'), 'hero result title'),
    ).toBe('FitChef result');
    expect(exactText(hero.querySelector('.ppm-insight-card .ppm-pill'), 'hero result badge')).toBe(
      'Prepared example',
    );
    expect(
      exactText(hero.querySelector('.ppm-insight-card .ppm-insight-body'), 'hero result body'),
    ).toBe('Today points to Daily Plate. This week points to Weekly Planning.');
    expect(
      exactText(hero.querySelector('.ppm-insight-card .ppm-insight-note'), 'hero result note'),
    ).toBe('This preview uses no personal data.');

    const statusCards = requiredElement('.ppm-status-grid').querySelectorAll('.ppm-band-card');
    expect(Array.from(statusCards, (card) => ({
      title: exactText(card.querySelector('.ppm-band-card-title'), 'status title'),
      label: exactText(card.querySelector('.ppm-supporting'), 'status label'),
      body: exactText(card.querySelector('.ppm-band-card-copy'), 'status body'),
    }))).toEqual([
      {
        title: 'Use the BMI calculator',
        label: 'Free website',
        body: 'Check BMI with the free tool on this website.',
      },
      {
        title: 'Choose Today or This week',
        label: 'FitChef preview',
        body: 'Both choices stay visible until you confirm.',
      },
      {
        title: 'PulsePlate for Apple devices',
        label: 'Apple devices',
        body: 'Read about the broader FitChef experience planned beyond the free website.',
      },
    ]);

    const how = requiredElement('#how-it-works');
    expect(exactText(within(how).getByRole('heading', { level: 2 }), 'how h2')).toBe(
      'Use the calculator, then try FitChef',
    );
    expect(exactText(how.querySelector('.ppm-header > .ppm-description'), 'how description')).toBe(
      'Check BMI, choose Today or This week, and see the result in the same card.',
    );
    expect(Array.from(how.querySelectorAll('.ppm-step-card'), (card) => ({
      number: exactText(card.querySelector('.ppm-step-number'), 'step number'),
      title: exactText(card.querySelector('.ppm-step-title'), 'step title'),
      body: exactText(card.querySelector('.ppm-step-copy'), 'step body'),
    }))).toEqual([
      {
        number: '01',
        title: 'Open the free BMI calculator',
        body: 'View your BMI result on the website.',
      },
      {
        number: '02',
        title: 'Choose Today or This week',
        body: 'Both choices stay visible in the FitChef preview.',
      },
      {
        number: '03',
        title: 'See the result',
        body: 'The confirmed result stays in the preview card.',
      },
      {
        number: '04',
        title: 'Read about PulsePlate for Apple devices',
        body: 'Learn where the more advanced FitChef experience is planned.',
      },
    ]);

    const core = requiredElement('#core-surfaces');
    expect(exactText(within(core).getByRole('heading', { level: 2 }), 'core h2')).toBe(
      'Daily Plate and Weekly Planning',
    );
    expect(exactText(core.querySelector('.ppm-header > .ppm-description'), 'core description')).toBe(
      'These are the two planning areas named by the FitChef preview.',
    );
    expect(Array.from(core.querySelectorAll('.ppm-surface-card'), (card) => ({
      title: exactText(card.querySelector('.ppm-surface-title'), 'surface title'),
      label: exactText(card.querySelector('.ppm-pill'), 'surface label'),
      body: exactText(card.querySelector('.ppm-surface-copy'), 'surface body'),
    }))).toEqual([
      {
        title: 'Free BMI calculator',
        label: 'Free web tool',
        body: 'Use the calculator on this website.',
      },
      {
        title: 'FitChef preview',
        label: 'Prepared example',
        body: 'Choose Today or This week, then confirm.',
      },
      {
        title: 'Daily Plate',
        label: 'Today',
        body: 'A day-focused area for planning meals.',
      },
      {
        title: 'Weekly Planning',
        label: 'This week',
        body: 'A seven-day area for looking ahead.',
      },
      {
        title: 'PulsePlate for Apple devices',
        label: 'Apple devices',
        body: 'A broader daily and weekly experience is being designed beyond this free website.',
      },
    ]);

    const trust = requiredElement('#trust-scope');
    expect(exactText(trust.querySelector('.ppm-header > .ppm-description'), 'trust description')).toBe(
      'Learn what the free website offers, how the FitChef preview works, and what is planned for Apple devices.',
    );
    expect(Array.from(trust.querySelectorAll('.ppm-faq-item'), (item) => ({
      question: exactText(item.querySelector('.ppm-faq-title'), 'trust FAQ question'),
      answer: exactText(item.querySelector('.ppm-faq-copy'), 'trust FAQ answer'),
    }))).toEqual([
      {
        question: 'What can I use on this website?',
        answer:
          'You can use the free BMI calculator and try the prepared FitChef preview without a purchase step.',
      },
      {
        question: 'Does the FitChef preview run AI?',
        answer: 'No. It uses one fixed result for each of the two choices.',
      },
      {
        question: 'Where are more advanced FitChef ideas planned?',
        answer:
          'PulsePlate is being designed for Apple devices. This page does not claim current App Store availability.',
      },
    ]);

    const finalCta = requiredElement('#final-cta');
    expect(exactText(within(finalCta).getByRole('heading', { level: 2 }), 'final CTA h2')).toBe(
      'Try the BMI calculator or FitChef preview',
    );
    expect(exactText(finalCta.querySelector('.ppm-description'), 'final CTA body')).toBe(
      'Both are free to use on this website.',
    );
    expect(exactTexts(finalCta, '.ppm-cta-actions .ppm-btn')).toEqual([
      'Try free BMI',
      'Return to the FitChef preview',
    ]);

    const footer = requiredElement('footer');
    expect(exactText(footer.querySelector('.ppm-footer-copy > .ppm-description'), 'footer body')).toBe(
      'Use the free BMI calculator or choose Today or This week in the FitChef preview.',
    );
    expect(exactText(footer.querySelector('.ppm-footer-note'), 'footer wellness line')).toBe(
      'Everyday wellness planning — not medical advice.',
    );
  });

  it('uses only the free BMI and FitChef-preview acquisition destinations', () => {
    const { container } = renderMarketingPage();
    const hrefs = Array.from(container.querySelectorAll<HTMLAnchorElement>('a[href]'), (link) =>
      link.getAttribute('href'),
    );

    expect(screen.getByRole('link', { name: 'See how FitChef works' })).toHaveAttribute(
      'href',
      '#fitchef-demo',
    );
    const freeBmiLinks = screen.getAllByRole('link', { name: 'Try the free BMI calculator' });
    expect(freeBmiLinks).toHaveLength(2);
    freeBmiLinks.forEach((link) => expect(link).toHaveAttribute('href', '/bmi'));
    expect(screen.getByRole('link', { name: 'Try free BMI' })).toHaveAttribute('href', '/bmi');
    expect(screen.getByRole('link', { name: 'Return to the FitChef preview' })).toHaveAttribute(
      'href',
      '#fitchef-demo',
    );
    ['/app', '/pro', '/enter-key', '/welcome-gate-v1'].forEach((forbiddenHref) => {
      expect(hrefs).not.toContain(forbiddenHref);
    });
    within(container).queryAllByRole('button').forEach((button) =>
      expect(button).not.toHaveTextContent(/buy|subscribe|upgrade|trial|restore|download|payment/i),
    );
    within(container).queryAllByRole('link').forEach((link) =>
      expect(link).not.toHaveTextContent(/buy|subscribe|upgrade|trial|restore|download|payment/i),
    );
  });

  it('keeps the free-Web and prepared-example boundary explicit without internal language', () => {
    const { container } = renderMarketingPage();
    const visibleCopy = container.textContent ?? '';

    expect(visibleCopy).toContain('This website is free to use. Purchases are not offered here.');
    expect(visibleCopy).toContain(
      'This is a prepared website example. It does not run AI, use personal data, open anything, or change a plan.',
    );
    expect(visibleCopy).not.toMatch(
      /\b(structure|structuring|daily_structure|weekly_structure|target_surface|authority|pipeline|best|personalized|generated for you|Pro|VIP)\b/i,
    );
    expect(visibleCopy).not.toMatch(/available now|live now|browser upgrade|AI[- ]powered|AI coaching/i);
    expect(container.querySelector('a[href^="https://apps.apple.com"], a[href^="itms-apps:"]')).toBeNull();
    expect(visibleCopy).not.toMatch(/\$\d|price|trial|eligibility/i);
  });
});
