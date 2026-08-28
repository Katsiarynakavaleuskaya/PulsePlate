/** @vitest-environment jsdom */
import '../../test/setup';
import '../../i18n';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, test } from 'vitest';
import PremiumGate from '../PremiumGate';

function renderWithRouter(element: JSX.Element): ReturnType<typeof render> {
  return render(<MemoryRouter>{element}</MemoryRouter>);
}

describe('PremiumGate', () => {
  test('shows children directly when premium', () => {
    render(
      <PremiumGate isPremium>
        <div data-testid="content">Premium content</div>
      </PremiumGate>
    );

    expect(screen.getByTestId('content')).toBeInTheDocument();
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  test('keeps the preview inert and opens the shared information dialog', async () => {
    renderWithRouter(
      <PremiumGate isPremium={false}>
        <button data-testid="content" type="button">Gated content</button>
      </PremiumGate>
    );

    const preview = screen.getByTestId('content').parentElement;
    expect(
      preview?.hasAttribute('inert') || preview?.getAttribute('aria-hidden') === 'true'
    ).toBe(true);

    const trigger = screen.getByRole('button', {
      name: 'Learn about PulsePlate for Apple devices',
    });
    expect(trigger).toHaveAttribute('aria-haspopup', 'dialog');
    fireEvent.click(trigger);

    expect(
      screen.getByRole('dialog', { name: 'PulsePlate for Apple devices' })
    ).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByRole('link', { name: 'Try the free BMI calculator' })).toHaveFocus();
    });
  });

  test('restores trigger focus after Escape or Not now', async () => {
    renderWithRouter(
      <PremiumGate isPremium={false}>
        <div>Gated content</div>
      </PremiumGate>
    );

    const trigger = screen.getByRole('button', {
      name: 'Learn about PulsePlate for Apple devices',
    });
    fireEvent.click(trigger);
    fireEvent.keyDown(screen.getByRole('dialog'), { key: 'Escape' });

    await waitFor(() => expect(trigger).toHaveFocus());

    fireEvent.click(trigger);
    fireEvent.click(screen.getByRole('button', { name: 'Not now' }));
    await waitFor(() => expect(trigger).toHaveFocus());
  });

  test('accepts old source metadata without giving it visible or action authority', () => {
    renderWithRouter(
      <PremiumGate
        isPremium={false}
        paywallSource="pro_daily_plate"
        source="plate_page"
        triggerReason="upgrade_for_export"
      >
        <div>Gated content</div>
      </PremiumGate>
    );

    fireEvent.click(
      screen.getByRole('button', { name: 'Learn about PulsePlate for Apple devices' })
    );
    expect(document.body).not.toHaveTextContent(/plate_page|pro_daily_plate|upgrade_for_export/i);
    expect(screen.queryByRole('button', { name: /buy|upgrade|subscribe|trial|restore/i })).not.toBeInTheDocument();
  });
});
