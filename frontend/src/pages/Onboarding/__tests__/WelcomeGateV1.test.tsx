import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';
import WelcomeGateV1 from '../WelcomeGateV1';

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

describe('WelcomeGateV1', () => {
  it('renders the multi-step onboarding preview and primary CTA', () => {
    render(
      <MemoryRouter>
        <WelcomeGateV1 />
      </MemoryRouter>
    );

    expect(screen.getByRole('main', { name: 'Welcome Gate v1 preview' })).toBeInTheDocument();
    expect(screen.getByText('onboarding.welcome.skip')).toBeInTheDocument();
    expect(screen.getByText('onboarding.welcome.screen1.title')).toBeInTheDocument();
    expect(screen.getByText('onboarding.welcome.screen1.cardTitle')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'onboarding.welcome.cta.start' })).toBeInTheDocument();
    expect(screen.getByText('onboarding.welcome.preview.panelTitle')).toBeInTheDocument();
  });

  it('can open the goal-selection step directly for review', () => {
    render(
      <MemoryRouter>
        <WelcomeGateV1 initialScreen={3} />
      </MemoryRouter>
    );

    expect(screen.getByText('onboarding.welcome.screen3.title')).toBeInTheDocument();
    expect(screen.getByText('onboarding.welcome.screen3.goals.1')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'onboarding.welcome.cta.finish' })).toHaveAttribute('href', '/setup');
  });
});
