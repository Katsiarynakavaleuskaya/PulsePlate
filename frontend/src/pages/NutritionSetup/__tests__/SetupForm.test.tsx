import { describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import SetupForm from '../SetupForm';
import { SettingsProvider } from '../../../lib/settings';

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

describe('SetupForm', () => {
  it('normalizes comma decimals before submit', async () => {
    const onSubmit = vi.fn();
    const user = userEvent.setup();

    render(
      <SettingsProvider>
        <SetupForm onSubmit={onSubmit} />
      </SettingsProvider>
    );

    await user.clear(screen.getByPlaceholderText('30'));
    await user.type(screen.getByPlaceholderText('30'), '30,9');
    await user.clear(screen.getByPlaceholderText('170'));
    await user.type(screen.getByPlaceholderText('170'), '170,5');
    await user.clear(screen.getByPlaceholderText('65'));
    await user.type(screen.getByPlaceholderText('65'), '65,4');
    await user.click(screen.getByRole('button', { name: 'nutritionSetup.calculateButton' }));

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith(
        expect.objectContaining({
          age: 30,
          height_cm: 170.5,
          weight_kg: 65.4,
        })
      );
    });
  });
});
