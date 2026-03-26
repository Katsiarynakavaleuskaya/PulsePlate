import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
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

    expect(screen.getByRole('main', { name: 'onboarding.welcome.mainA11y' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'onboarding.welcome.skip' })).toHaveAttribute('href', '/setup');
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

  it('updates preview goal selection state when another goal is chosen', async () => {
    const user = userEvent.setup();

    render(
      <MemoryRouter>
        <WelcomeGateV1 initialScreen={3} />
      </MemoryRouter>
    );

    const firstGoal = screen.getByRole('button', { name: 'onboarding.welcome.screen3.goals.1' });
    const thirdGoal = screen.getByRole('button', { name: 'onboarding.welcome.screen3.goals.3' });

    expect(firstGoal).toHaveAttribute('aria-pressed', 'true');
    expect(thirdGoal).toHaveAttribute('aria-pressed', 'false');

    await user.click(thirdGoal);

    expect(firstGoal).toHaveAttribute('aria-pressed', 'false');
    expect(thirdGoal).toHaveAttribute('aria-pressed', 'true');
  });
});
