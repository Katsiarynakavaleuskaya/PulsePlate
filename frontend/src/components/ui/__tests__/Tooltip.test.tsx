/** @vitest-environment jsdom */
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { Button } from '../Button';
import { Tooltip } from '../Tooltip';

describe('Tooltip', () => {
  it('is hidden by default and shows on hover', async () => {
    const user = userEvent.setup();

    render(
      <Tooltip content="Supportive helper copy">
        <Button size="sm">Why this matters</Button>
      </Tooltip>
    );

    expect(screen.queryByRole('tooltip')).not.toBeInTheDocument();
    await user.hover(screen.getByRole('button', { name: 'Why this matters' }));
    expect(screen.getByRole('tooltip')).toBeInTheDocument();
  });

  it('shows on keyboard focus and hides on blur', async () => {
    const user = userEvent.setup();

    render(
      <Tooltip content="Supportive helper copy">
        <Button size="sm">Why this matters</Button>
      </Tooltip>
    );

    await user.tab();
    expect(screen.getByRole('tooltip')).toBeInTheDocument();

    await user.tab();
    expect(screen.queryByRole('tooltip')).not.toBeInTheDocument();
  });
});
