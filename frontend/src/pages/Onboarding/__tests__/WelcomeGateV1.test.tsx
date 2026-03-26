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

describe('WelcomeGateV1', () => {
  it.each([
    {
      language: 'en' as const,
      title: 'PulsePlate — your nutrition on track',
      body: 'Set your goals once. Your plan and progress stay aligned.',
      cta: 'Get started',
      step: 'Step 1 of 1',
    },
    {
      language: 'ru' as const,
      title: 'PulsePlate — питание под контролем',
      body: 'Настрой цели один раз. План и прогресс будут согласованы.',
      cta: 'Начать',
      step: 'Шаг 1 из 1',
    },
    {
      language: 'es' as const,
      title: 'PulsePlate — tu nutrición bajo control',
      body: 'Configura tus objetivos una vez. Plan y progreso en sintonía.',
      cta: 'Empezar',
      step: 'Paso 1 de 1',
    },
  ])('renders localized screen-1-only preview for $language', async ({ language, title, body, cta, step }) => {
    await renderWelcomeGate(language);

    await waitFor(() => {
      expect(screen.getByText(title)).toBeInTheDocument();
    });

    expect(screen.getByText(body)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: cta })).toHaveAttribute('href', '/setup');
    expect(screen.getByLabelText(step)).toBeInTheDocument();
    expect(screen.getByText('WELCOME GATE / v1')).toBeInTheDocument();
    expect(screen.getByAltText('FitChef onboarding welcome scene')).toBeInTheDocument();
  });

  it('renders preview-only metadata and skip link without persistence controls', async () => {
    await renderWelcomeGate('en');

    expect(screen.getByRole('main', { name: 'Welcome gate preview' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Skip' })).toHaveAttribute('href', '/setup');
    expect(screen.getByText(/screen 1 preview -> setup/i)).toBeInTheDocument();
    expect(screen.getByText(/preview only, no persistence/i)).toBeInTheDocument();
  });
});
