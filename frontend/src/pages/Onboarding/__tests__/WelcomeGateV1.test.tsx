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
  it('renders the pulse membrane preview content and CTA', () => {
    render(
      <MemoryRouter>
        <WelcomeGateV1 />
      </MemoryRouter>
    );

    expect(screen.getByRole('main', { name: 'Welcome Gate v1 preview' })).toBeInTheDocument();
    expect(screen.getByText('onboarding.welcome.preview.systemTitle')).toBeInTheDocument();
    expect(screen.getByText('onboarding.welcome.screen1.title')).toBeInTheDocument();
    expect(screen.getByText('onboarding.welcome.screen1.body')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'onboarding.welcome.cta.start' })).toHaveAttribute('href', '/setup');
    expect(screen.getByText('onboarding.welcome.preview.panelTitle')).toBeInTheDocument();
    expect(screen.getByText('has_seen_welcome_v1')).toBeInTheDocument();
  });
});
