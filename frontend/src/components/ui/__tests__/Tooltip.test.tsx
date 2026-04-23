/** @vitest-environment jsdom */
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { Button } from '../Button';
import { Tooltip } from '../Tooltip';

describe('Tooltip', (): void => {
  it('is hidden by default and shows on hover', async (): Promise<void> => {
    const user = userEvent.setup();

    render(
      <Tooltip content="Supportive helper copy">
        <Button size="sm">Why this matters</Button>
      </Tooltip>
    );

    expect(screen.getByRole('tooltip')).toHaveClass('sr-only');
    await user.hover(screen.getByRole('button', { name: 'Why this matters' }));
    expect(screen.getByRole('tooltip')).not.toHaveClass('sr-only');
  });

  it('shows on keyboard focus and hides on blur', async (): Promise<void> => {
    const user = userEvent.setup();

    render(
      <Tooltip content="Supportive helper copy">
        <Button size="sm">Why this matters</Button>
      </Tooltip>
    );

    await user.tab();
    expect(screen.getByRole('tooltip')).not.toHaveClass('sr-only');

    await user.tab();
    await waitFor(() => {
      expect(screen.getByRole('tooltip')).toHaveClass('sr-only');
    });
  });

  it('preserves existing aria-describedby references', async (): Promise<void> => {
    const user = userEvent.setup();

    render(
      <Tooltip content="Supportive helper copy">
        <button aria-describedby="existing-help" type="button">
          Why this matters
        </button>
      </Tooltip>
    );

    await user.hover(screen.getByRole('button', { name: 'Why this matters' }));

    const describedBy = screen.getByRole('button', { name: 'Why this matters' }).getAttribute('aria-describedby');
    expect(describedBy).toContain('existing-help');
    expect(describedBy).toContain(screen.getByRole('tooltip').id);
  });
});
