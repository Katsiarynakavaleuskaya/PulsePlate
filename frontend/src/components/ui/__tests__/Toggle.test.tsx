import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { vi } from 'vitest';
import { Toggle } from '../Toggle';

describe('Toggle', () => {
  it('renders with label and description', () => {
    render(
      <Toggle
        label="Test Toggle"
        description="This is a test toggle"
        checked={false}
        onChange={() => {}}
      />
    );

    expect(screen.getByText('Test Toggle')).toBeInTheDocument();
    expect(screen.getByText('This is a test toggle')).toBeInTheDocument();
  });

  it('calls onChange when clicked', () => {
    const mockOnChange = vi.fn();
    render(
      <Toggle
        label="Test Toggle"
        checked={false}
        onChange={mockOnChange}
      />
    );

    const toggle = screen.getByRole('switch');
    fireEvent.click(toggle);

    expect(mockOnChange).toHaveBeenCalledWith(true);
  });

  it('reflects checked state', () => {
    const { rerender } = render(
      <Toggle
        label="Test Toggle"
        checked={false}
        onChange={() => {}}
      />
    );

    let toggle = screen.getByRole('switch');
    expect(toggle).toHaveAttribute('aria-checked', 'false');

    rerender(
      <Toggle
        label="Test Toggle"
        checked={true}
        onChange={() => {}}
      />
    );

    toggle = screen.getByRole('switch');
    expect(toggle).toHaveAttribute('aria-checked', 'true');
  });

  it('is disabled when disabled prop is true', () => {
    const mockOnChange = vi.fn();
    render(
      <Toggle
        label="Test Toggle"
        checked={false}
        onChange={mockOnChange}
        disabled={true}
      />
    );

    const toggle = screen.getByRole('switch');
    expect(toggle).toBeDisabled();

    fireEvent.click(toggle);
    expect(mockOnChange).not.toHaveBeenCalled();
  });

  it('has proper accessibility attributes', () => {
    render(
      <Toggle
        label="Test Toggle"
        checked={true}
        onChange={() => {}}
      />
    );

    const toggle = screen.getByRole('switch');
    const label = screen.getByLabelText('Test Toggle');

    expect(toggle).toHaveAttribute('aria-checked', 'true');
    expect(label).toBeInTheDocument();
  });
});
