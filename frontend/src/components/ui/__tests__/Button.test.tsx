import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { Button } from '../Button';

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
});
