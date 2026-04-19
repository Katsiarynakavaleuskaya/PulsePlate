import { afterEach, describe, expect, it } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import '../../i18n';
import Plate from '../Plate';
import { PlateStoryHarness } from '../Plate.storySupport';

describe('Plate story harness parity', () => {
  const originalFetch = global.fetch.bind(global);

  afterEach(() => {
    global.fetch = originalFetch;
  });

  it('renders the canonical parity-pack story with unlocked premium controls', async () => {
    render(
      <PlateStoryHarness sessionState="pro">
        <Plate />
      </PlateStoryHarness>
    );

    await waitFor(() => {
      expect(screen.getByText('Premium Nutrition Controls')).toBeInTheDocument();
    });

    expect(screen.getByRole('link', { name: 'Configure Setup' })).toHaveAttribute('href', '/setup');
    expect(screen.getByRole('link', { name: 'View Progress' })).toHaveAttribute('href', '/progress');
  });
});
