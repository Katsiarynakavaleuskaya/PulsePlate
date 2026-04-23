/** @vitest-environment jsdom */
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeAll, describe, expect, it, vi } from 'vitest';
import {
  DropdownMenu,
  DropdownMenuItem,
  DropdownMenuLinkItem,
  DropdownMenuItems,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '../DropdownMenu';

beforeAll(() => {
  class ResizeObserverMock {
    observe() {}
    unobserve() {}
    disconnect() {}
  }

  vi.stubGlobal('ResizeObserver', ResizeObserverMock);
});

describe('DropdownMenu', () => {
  it('opens, selects an item, and closes', async () => {
    const user = userEvent.setup();
    const handleSelect = vi.fn();

    render(
      <DropdownMenu>
        <DropdownMenuTrigger>More actions</DropdownMenuTrigger>
        <DropdownMenuItems>
          <DropdownMenuItem onClick={handleSelect}>Duplicate</DropdownMenuItem>
          <DropdownMenuSeparator />
          <DropdownMenuItem destructive>Remove</DropdownMenuItem>
        </DropdownMenuItems>
      </DropdownMenu>
    );

    await user.click(screen.getByRole('button', { name: /more actions/i }));
    await user.click(screen.getByRole('menuitem', { name: 'Duplicate' }));

    expect(handleSelect).toHaveBeenCalledTimes(1);
    await waitFor(() => {
      expect(screen.queryByRole('menu')).not.toBeInTheDocument();
    });
  });

  it('closes on escape', async () => {
    const user = userEvent.setup();

    render(
      <DropdownMenu>
        <DropdownMenuTrigger>More actions</DropdownMenuTrigger>
        <DropdownMenuItems>
          <DropdownMenuItem>Duplicate</DropdownMenuItem>
        </DropdownMenuItems>
      </DropdownMenu>
    );

    await user.click(screen.getByRole('button', { name: /more actions/i }));
    expect(screen.getByRole('menu')).toBeInTheDocument();

    await user.keyboard('{Escape}');
    await waitFor(() => {
      expect(screen.queryByRole('menu')).not.toBeInTheDocument();
    });
  });

  it('supports link menu items without nesting anchors inside buttons', async () => {
    const user = userEvent.setup();

    render(
      <DropdownMenu>
        <DropdownMenuTrigger>More actions</DropdownMenuTrigger>
        <DropdownMenuItems>
          <DropdownMenuLinkItem href="/weekly-plan">Open weekly plan</DropdownMenuLinkItem>
        </DropdownMenuItems>
      </DropdownMenu>
    );

    await user.click(screen.getByRole('button', { name: /more actions/i }));

    expect(screen.getByRole('menuitem', { name: 'Open weekly plan' })).toHaveAttribute('href', '/weekly-plan');
    expect(screen.getByRole('menuitem', { name: 'Open weekly plan' }).tagName).toBe('A');
  });
});
