/** @vitest-environment jsdom */
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { Checkbox } from '../Checkbox';

describe('Checkbox', () => {
  it('toggles when the label is clicked', async () => {
    const handleChange = vi.fn();
    const user = userEvent.setup();

    render(
      <label>
        <Checkbox checked={false} onChange={handleChange} />
        <span>Weekly planning summary</span>
      </label>
    );

    await user.click(screen.getByText('Weekly planning summary'));
    expect(handleChange).toHaveBeenCalled();
  });

  it('exposes invalid state for wrapper-owned errors', () => {
    render(<Checkbox aria-label="Weekly planning summary" checked={false} invalid readOnly />);
    expect(screen.getByRole('checkbox')).toHaveAttribute('aria-invalid', 'true');
  });
});
