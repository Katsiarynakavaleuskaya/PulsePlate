/** @vitest-environment jsdom */
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterAll, beforeAll, describe, expect, it, vi } from 'vitest';
import {
  DropdownMenu,
  DropdownMenuItem,
  DropdownMenuLinkItem,
  DropdownMenuItems,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '../DropdownMenu';

beforeAll((): void => {
  class ResizeObserverMock {
    observe(): void {}
    unobserve(): void {}
    disconnect(): void {}
  }

  vi.stubGlobal('ResizeObserver', ResizeObserverMock);
});

afterAll((): void => {
  vi.unstubAllGlobals();
});

describe('DropdownMenu', (): void => {
  it('opens, selects an item, and closes', async (): Promise<void> => {
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

  it('closes on escape', async (): Promise<void> => {
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

  it('supports link menu items without nesting anchors inside buttons', async (): Promise<void> => {
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

  it('applies active styling to button and link menu items', async (): Promise<void> => {
    const user = userEvent.setup();

    render(
      <DropdownMenu>
        <DropdownMenuTrigger>More actions</DropdownMenuTrigger>
        <DropdownMenuItems>
          <DropdownMenuItem>Duplicate</DropdownMenuItem>
          <DropdownMenuLinkItem href="/weekly-plan">Open weekly plan</DropdownMenuLinkItem>
        </DropdownMenuItems>
      </DropdownMenu>
    );

    await user.click(screen.getByRole('button', { name: /more actions/i }));

    await user.keyboard('{ArrowDown}');

    const buttonItem = screen.getByRole('menuitem', { name: 'Duplicate' });
    await waitFor(() => {
      expect(buttonItem).toHaveClass('bg-[var(--color-surface-muted)]');
    });

    await user.keyboard('{ArrowDown}');

    const linkItem = screen.getByRole('menuitem', { name: 'Open weekly plan' });
    await waitFor(() => {
      expect(linkItem).toHaveClass('bg-[var(--color-surface-muted)]');
    });
  });
});
