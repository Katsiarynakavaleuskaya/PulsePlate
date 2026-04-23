/** @vitest-environment jsdom */
import '@testing-library/jest-dom/vitest';
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { Badge } from '../Badge';
import { Hero } from '../Hero';
import { ProgressIndicator } from '../ProgressIndicator';
import { StatsCard } from '../StatsCard';
import { Stepper } from '../Stepper';

describe('governed specialized families', () => {
  it('renders premium badge styling without route-specific wrapper logic', () => {
    render(<Badge tone="premium">VIP</Badge>);

    const badge = screen.getByText('VIP');
    expect(badge.className).toMatch(/pp-gold/);
    expect(badge.className).toMatch(/color-primary-foreground/);
  });

  it('keeps warning badge styling on semantic warning tokens', () => {
    render(<Badge tone="warning">Needs review</Badge>);

    const badge = screen.getByText('Needs review');
    expect(badge.className).toMatch(/color-warning/);
    expect(badge.className).not.toMatch(/pp-gold/);
  });

  it('renders progress indicator with timestamp and action slot', () => {
    render(
      <ProgressIndicator
        action={<button type="button">Open progress</button>}
        description="Shared progress anatomy"
        label="Live updates on"
        state="live"
        timestampAriaLabel="Live event timestamp"
        timestampLabel="7:00 PM"
      />
    );

    expect(screen.getByText('Live updates on')).toBeInTheDocument();
    expect(screen.getByLabelText('Live event timestamp')).toHaveTextContent('7:00 PM');
    expect(screen.getByRole('button', { name: 'Open progress' })).toBeInTheDocument();
  });

  it('keeps warning progress state on semantic warning tokens', () => {
    const { container } = render(
      <ProgressIndicator
        description="Needs setup review"
        label="Needs attention"
        state="warning"
      />
    );

    const dot = container.querySelector('span[aria-hidden="true"]');
    expect(dot?.className).toMatch(/color-warning/);
    expect(dot?.className).not.toMatch(/color-error/);
  });

  it('renders hero shell with chips', () => {
    render(
      <Hero
        chips={<span>Session Connected</span>}
        description="Quick actions and premium guidance."
        eyebrow="Calm control panel"
        title="PulsePlate Home"
      />
    );

    expect(screen.getByRole('heading', { level: 1, name: 'PulsePlate Home' })).toBeInTheDocument();
    expect(screen.getByText('Session Connected')).toBeInTheDocument();
  });

  it('renders stats card value and detail', () => {
    render(<StatsCard detail="Secure session status" label="Connection" value="Connected" />);

    expect(screen.getByText('Connection')).toBeInTheDocument();
    expect(screen.getByText('Connected')).toBeInTheDocument();
    expect(screen.getByText('Secure session status')).toBeInTheDocument();
  });

  it('marks the current step explicitly in the governed setup flow', () => {
    render(
      <Stepper
        currentStep={1}
        steps={[
          { id: 'profile', label: 'Profile', description: 'Capture your nutrition inputs' },
          { id: 'results', label: 'Results', description: 'Review macros and targets' },
        ]}
      />
    );

    expect(screen.getByText('Step 2 of 2')).toBeInTheDocument();
    expect(screen.getByRole('listitem', { current: 'step' })).toHaveTextContent('Results');
  });
});
