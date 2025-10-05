/** @vitest-environment jsdom */
import { render, screen, fireEvent } from '@testing-library/react';
import { vi } from 'vitest';
import Toggle from '../Toggle';

describe('Toggle', () => {
  it('has proper accessibility attributes', () => {
    render(
      <Toggle
        label="Test Toggle"
        checked={true}
        onChange={() => {}}
      />
    );

    const toggle = screen.getByRole('switch');
    expect(toggle).toHaveAttribute('aria-checked', 'true');
    expect(toggle).toHaveAttribute('aria-labelledby');
  });

  it('toggles state when clicked', () => {
    const handleChange = vi.fn();
    render(
      <Toggle
        label="Test Toggle"
        checked={false}
        onChange={handleChange}
      />
    );

    const toggle = screen.getByRole('switch');
    fireEvent.click(toggle);

    expect(handleChange).toHaveBeenCalledWith(true);
  });

  it('does not toggle when disabled', () => {
    const handleChange = vi.fn();
    render(
      <Toggle
        label="Test Toggle"
        checked={false}
        onChange={handleChange}
        disabled={true}
      />
    );

    const toggle = screen.getByRole('switch');
    fireEvent.click(toggle);

    expect(handleChange).not.toHaveBeenCalled();
  });

  it('does not toggle when disabled via label click', () => {
    const handleChange = vi.fn();
    render(
      <Toggle
        label="Test Toggle"
        checked={false}
        onChange={handleChange}
        disabled={true}
      />
    );

    const label = screen.getByText('Test Toggle');
    fireEvent.click(label);

    expect(handleChange).not.toHaveBeenCalled();
  });
});
