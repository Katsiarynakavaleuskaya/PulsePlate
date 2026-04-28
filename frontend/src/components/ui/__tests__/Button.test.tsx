/** @vitest-environment jsdom */
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { Button, buttonClasses } from '../Button';

describe('Button', () => {
  it('renders the destructive variant with the shared alert styling', () => {
    render(<Button variant="destructive">Critical Alert State</Button>);

    const button = screen.getByRole('button', { name: 'Critical Alert State' });

    expect(button).toHaveClass(
      'border',
      'border-[var(--color-destructive-border)]',
      'bg-[var(--color-destructive-bg)]',
      'text-[var(--color-destructive-foreground)]',
    );
  });

  it('renders primary md by default', () => {
    render(<Button>Save</Button>);
    const button = screen.getByRole('button', { name: 'Save' });
    expect(button).toHaveClass('bg-[var(--color-primary)]', 'min-h-[44px]');
  });

  it('applies success and warning variant classes via buttonClasses', () => {
    expect(buttonClasses({ variant: 'success' })).toContain('bg-[var(--color-success)]');
    expect(buttonClasses({ variant: 'warning' })).toContain('bg-[var(--color-warning)]');
    expect(buttonClasses({ variant: 'destructive' })).toContain(
      'border-[var(--color-destructive-border)]',
    );
  });

  it('applies size classes', () => {
    expect(buttonClasses({ size: 'sm' })).toContain('min-h-[40px]');
    expect(buttonClasses({ size: 'lg' })).toContain('min-h-[48px]');
  });

  it('merges fullWidth and className', () => {
    const merged = buttonClasses({ fullWidth: true, className: 'extra' });
    expect(merged).toContain('w-full');
    expect(merged).toContain('extra');
  });

  it('sets loading state, aria-busy, and disables the button', () => {
    render(
      <Button loading loadingLabel="Please wait">
        Submit
      </Button>
    );
    const button = screen.getByRole('button', { name: 'Please wait' });
    expect(button).toHaveAttribute('aria-busy', 'true');
    expect(button).toBeDisabled();
    expect(button).not.toHaveTextContent('Submit');
  });

  it('does not set aria-busy when not loading', () => {
    render(<Button>Submit</Button>);
    const button = screen.getByRole('button', { name: 'Submit' });
    expect(button).not.toHaveAttribute('aria-busy');
  });

  it('uses custom loadingLabel', () => {
    render(
      <Button loading loadingLabel="Syncing…">
        Done
      </Button>
    );
    expect(screen.getByRole('button', { name: 'Syncing…' })).toBeInTheDocument();
  });

  it('does not let caller disabled=false override loading disabled semantics', () => {
    render(
      <Button loading disabled={false}>
        X
      </Button>
    );
    expect(screen.getByRole('button')).toBeDisabled();
  });
});
