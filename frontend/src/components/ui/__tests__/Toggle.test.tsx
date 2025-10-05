/** @vitest-environment jsdom */
import { render, screen } from '@testing-library/react';
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
    expect(toggle).toHaveAttribute('aria-label', 'Test Toggle');
  });
});
