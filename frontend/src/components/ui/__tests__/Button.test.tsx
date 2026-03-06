import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { Button } from '../Button';

describe('Button', () => {
  it('renders the destructive variant with the shared alert styling', () => {
    render(<Button variant="destructive">Critical Alert State</Button>);

    const button = screen.getByRole('button', { name: 'Critical Alert State' });

    expect(button).toHaveClass(
      'border',
      'border-[rgba(255,93,93,0.18)]',
      'bg-[rgba(255,93,93,0.1)]',
      'text-[var(--pp-red)]',
    );
  });
});
