import { cleanup, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest';
import '../../../i18n';
import i18n from '../../../i18n';
import WelcomeGateV1 from '../WelcomeGateV1';
import {
  WELCOME_GATE_V1_PREVIEW_LOCALES,
  WELCOME_GATE_V1_PREVIEW_STEP,
  WELCOME_GATE_V1_PREVIEW_STEP_COUNT,
  WELCOME_GATE_V1_SETUP_TARGET,
} from '../welcomeGateV1Policy';

async function waitForI18n(): Promise<void> {
  if (i18n.isInitialized) {
    return;
  }

  await new Promise<void>((resolve, reject) => {
    let timeout: ReturnType<typeof setTimeout>;
    const handler = (): void => {
      i18n.off('initialized', handler);
      clearTimeout(timeout);
      resolve();
    };
    timeout = setTimeout(() => {
      i18n.off('initialized', handler);
      reject(new Error('i18n initialization timeout'));
    }, 5000);

    i18n.on('initialized', handler);

    if (i18n.isInitialized) {
      handler();
    }
  });
}

beforeAll(async () => {
  await waitForI18n();
});

afterEach(async () => {
  cleanup();
  vi.restoreAllMocks();
  await i18n.changeLanguage('en');
});

async function renderWelcomeGate(language: 'en' | 'ru' | 'es'): Promise<void> {
  await i18n.changeLanguage(language);

  render(
    <MemoryRouter>
      <WelcomeGateV1 />
    </MemoryRouter>
  );
}

type WelcomeCopy = {
  body: string;
  cta: string;
  heroAlt: string;
  mainA11y: string;
  panelFlowValue: string;
  panelTargetValue: string;
  panelBlockedValue: string;
  panelPolicyValue: string;
  panelTitle: string;
  step: string;
  title: string;
};

function getWelcomeCopy(language: 'en' | 'ru' | 'es'): WelcomeCopy {
  const t = i18n.getFixedT(language);

  return {
    body: t('onboarding.welcome.screen1.body'),
    cta: t('onboarding.welcome.cta.start'),
    heroAlt: t('onboarding.welcome.heroAlt'),
    mainA11y: t('onboarding.welcome.mainA11y'),
    panelFlowValue: t('onboarding.welcome.preview.panelFlowValue'),
    panelTargetValue: t('onboarding.welcome.preview.panelTargetValue'),
    panelBlockedValue: t('onboarding.welcome.preview.panelBlockedValue'),
    panelPolicyValue: t('onboarding.welcome.preview.panelPolicyValue'),
    panelTitle: t('onboarding.welcome.preview.panelTitle'),
    step: t('onboarding.welcome.stepA11y', {
      current: WELCOME_GATE_V1_PREVIEW_STEP,
      total: WELCOME_GATE_V1_PREVIEW_STEP_COUNT,
    }),
    title: t('onboarding.welcome.screen1.title'),
  };
}

describe('WelcomeGateV1', () => {
  it.each(['en', 'ru', 'es'] as const)('renders localized screen-1-only preview for %s', async (language) => {
    const copy = getWelcomeCopy(language);

    await renderWelcomeGate(language);

    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 1, name: copy.title })).toBeInTheDocument();
    });

    expect(screen.getByRole('main', { name: copy.mainA11y })).toBeInTheDocument();
    expect(screen.getByText(copy.body)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: copy.cta })).toHaveAttribute('href', WELCOME_GATE_V1_SETUP_TARGET);
    expect(screen.getByText(copy.step)).toBeInTheDocument();
    expect(screen.getByText(copy.panelTitle)).toBeInTheDocument();
    expect(screen.getByText((content) => content.includes(copy.panelTargetValue))).toBeInTheDocument();
    expect(screen.getByText((content) => content.includes(copy.panelBlockedValue))).toBeInTheDocument();
    expect(screen.getByAltText(copy.heroAlt)).toBeInTheDocument();
  });

  it('renders preview-only metadata and skip link without persistence controls', async () => {
    const copy = getWelcomeCopy('en');
    const persistenceKey = 'has_seen_welcome_v1';
    const setItemSpy = vi.spyOn(Storage.prototype, 'setItem');

    await renderWelcomeGate('en');

    expect(screen.getByRole('main', { name: copy.mainA11y })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Skip' })).toHaveAttribute('href', WELCOME_GATE_V1_SETUP_TARGET);
    expect(screen.getByText((content) => content.includes(copy.panelFlowValue))).toBeInTheDocument();
    expect(screen.getByText((content) => content.includes(copy.panelTargetValue))).toBeInTheDocument();
    expect(screen.getByText((content) => content.includes(copy.panelPolicyValue))).toBeInTheDocument();
    expect(screen.getByText((content) => content.includes(copy.panelBlockedValue))).toBeInTheDocument();
    expect(
      screen.getByText((content) => content.includes(WELCOME_GATE_V1_PREVIEW_LOCALES.join(' / ')))
    ).toBeInTheDocument();
    expect(setItemSpy.mock.calls.some(([key]) => key === persistenceKey)).toBe(false);
  });
});
