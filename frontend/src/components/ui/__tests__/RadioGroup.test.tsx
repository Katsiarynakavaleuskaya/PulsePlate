/** @vitest-environment jsdom */
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { RadioGroup, RadioGroupOption } from '../RadioGroup';

describe('RadioGroup', () => {
  it('changes selected option', async () => {
    const handleChange = vi.fn();
    const user = userEvent.setup();

    render(
      <RadioGroup legend="Coaching tone">
        <RadioGroupOption
          checked={true}
          label="Calm"
          name="coaching-tone"
          value="calm"
          onChange={handleChange}
        />
        <RadioGroupOption
          checked={false}
          label="Motivated"
          name="coaching-tone"
          value="motivated"
          onChange={handleChange}
        />
      </RadioGroup>
    );

    expect(screen.getByRole('group', { name: 'Coaching tone' })).toBeInTheDocument();
    await user.click(screen.getByRole('radio', { name: 'Motivated' }));
    expect(handleChange).toHaveBeenCalled();
  });

  it('renders group errors', () => {
    render(
      <RadioGroup error="Choose one coaching tone." legend="Coaching tone">
        <RadioGroupOption checked={true} label="Calm" name="coaching-tone" value="calm" onChange={() => {}} />
      </RadioGroup>
    );

    expect(screen.getByRole('group')).toHaveAccessibleDescription('Choose one coaching tone.');
    expect(screen.getByRole('group').getAttribute('aria-describedby')).not.toMatch(/\s/);
    expect(screen.getByText('Choose one coaching tone.')).toHaveAttribute('role', 'alert');
  });
});
