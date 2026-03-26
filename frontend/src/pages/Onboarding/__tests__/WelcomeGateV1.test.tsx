import { cleanup, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeAll, describe, expect, it } from 'vitest';
import '../../../i18n';
import i18n from '../../../i18n';
import WelcomeGateV1 from '../WelcomeGateV1';

async function waitForI18n(): Promise<void> {
  if (i18n.isInitialized) {
    return;
  }

  await new Promise<void>((resolve, reject) => {
    const timeout = setTimeout(() => {
      reject(new Error('i18n initialization timeout'));
    }, 5000);

    const handler = (): void => {
      i18n.off('initialized', handler);
      clearTimeout(timeout);
      resolve();
    };

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

function getWelcomeCopy(language: 'en' | 'ru' | 'es') {
  const t = i18n.getFixedT(language);

  return {
    body: t('onboarding.welcome.screen1.body'),
    cta: t('onboarding.welcome.cta.start'),
    mainA11y: t('onboarding.welcome.mainA11y'),
    panelFlowValue: t('onboarding.welcome.preview.panelFlowValue'),
    panelPolicyValue: t('onboarding.welcome.preview.panelPolicyValue'),
    panelTitle: t('onboarding.welcome.preview.panelTitle'),
    step: t('onboarding.welcome.stepA11y', { current: 1, total: 1 }),
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
    expect(screen.getByRole('link', { name: copy.cta })).toHaveAttribute('href', '/setup');
    expect(screen.getByText(copy.step)).toBeInTheDocument();
    expect(screen.getByText(copy.panelTitle)).toBeInTheDocument();
    expect(screen.getByAltText('FitChef onboarding welcome scene')).toBeInTheDocument();
  });

  it('renders preview-only metadata and skip link without persistence controls', async () => {
    const copy = getWelcomeCopy('en');

    await renderWelcomeGate('en');

    expect(screen.getByRole('main', { name: copy.mainA11y })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Skip' })).toHaveAttribute('href', '/setup');
    expect(screen.getByText((content) => content.includes(copy.panelFlowValue))).toBeInTheDocument();
    expect(screen.getByText((content) => content.includes(copy.panelPolicyValue))).toBeInTheDocument();
  });
});
