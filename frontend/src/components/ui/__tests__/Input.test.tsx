/** @vitest-environment jsdom */
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { Input, inputClasses } from '../Input';

describe('Input', () => {
  it('renders text md by default', () => {
    render(<Input aria-label="Name" placeholder="Placeholder" />);

    const input = screen.getByRole('textbox', { name: 'Name' });

    expect(input).toHaveClass('w-full');
    expect(input).toHaveClass('min-h-[44px]');
    expect(input).toHaveClass('border-[var(--color-border)]');
    expect(input).not.toHaveAttribute('aria-invalid');
  });

  it('supports sm md lg size classes', () => {
    expect(inputClasses({ size: 'sm' })).toContain('min-h-[40px]');
    expect(inputClasses({ size: 'md' })).toContain('min-h-[44px]');
    expect(inputClasses({ size: 'lg' })).toContain('min-h-[48px]');
  });

  it('supports filled value through native input props', () => {
    render(<Input aria-label="Calories" readOnly value="1800" />);

    expect(screen.getByDisplayValue('1800')).toBeInTheDocument();
  });

  it('supports number search and password types through native input props', () => {
    render(
      <div>
        <Input aria-label="Calories" type="number" />
        <Input aria-label="Food search" type="search" />
        <Input aria-label="API key" type="password" />
      </div>
    );

    expect(screen.getByLabelText('Calories')).toHaveAttribute('type', 'number');
    expect(screen.getByLabelText('Food search')).toHaveAttribute('type', 'search');
    expect(screen.getByLabelText('API key')).toHaveAttribute('type', 'password');
  });

  it('maps invalid prop to aria-invalid and error border', () => {
    render(<Input aria-label="Weight" invalid />);

    const input = screen.getByRole('textbox', { name: 'Weight' });

    expect(input).toHaveAttribute('aria-invalid', 'true');
    expect(input).toHaveClass('border-[var(--color-error)]');
  });

  it('maps aria-invalid string values to invalid state', () => {
    render(<Input aria-invalid="grammar" aria-label="Notes" />);

    const input = screen.getByRole('textbox', { name: 'Notes' });

    expect(input).toHaveAttribute('aria-invalid', 'grammar');
    expect(input).toHaveClass('border-[var(--color-error)]');
  });

  it('supports disabled state', () => {
    render(<Input aria-label="Disabled field" disabled />);

    expect(screen.getByRole('textbox', { name: 'Disabled field' })).toBeDisabled();
  });

  it('supports loading as disabled and busy', () => {
    render(<Input aria-label="Async field" loading />);

    const input = screen.getByRole('textbox', { name: 'Async field' });

    expect(input).toBeDisabled();
    expect(input).toHaveAttribute('aria-busy', 'true');
  });

  it('does not let disabled=false override loading disabled semantics', () => {
    render(<Input aria-label="Async field" loading disabled={false} />);

    expect(screen.getByRole('textbox', { name: 'Async field' })).toBeDisabled();
  });

  it('does not set aria-busy when not loading', () => {
    render(<Input aria-label="Idle field" />);

    expect(screen.getByRole('textbox', { name: 'Idle field' })).not.toHaveAttribute('aria-busy');
  });

  it('supports non-full-width composition', () => {
    const classes = inputClasses({
      fullWidth: false,
      className: 'custom-input',
    });

    expect(classes).not.toContain('w-full');
    expect(classes).toContain('custom-input');
  });
});
