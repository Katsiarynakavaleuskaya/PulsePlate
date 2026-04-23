/** @vitest-environment jsdom */
import { render, screen, waitFor } from '@testing-library/react';
import { act } from 'react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { Tabs, TabsList, TabsPanel, TabsPanels, TabsTrigger } from '../Tabs';

describe('Tabs', (): void => {
  it('switches panels on click', async (): Promise<void> => {
    const user = userEvent.setup();

    render(
      <Tabs>
        <TabsList>
          <TabsTrigger>Overview</TabsTrigger>
          <TabsTrigger>States</TabsTrigger>
        </TabsList>
        <TabsPanels>
          <TabsPanel>
            <p>Overview panel</p>
          </TabsPanel>
          <TabsPanel>
            <p>States panel</p>
          </TabsPanel>
        </TabsPanels>
      </Tabs>
    );

    const overviewTab = screen.getByRole('tab', { name: 'Overview' });
    const statesTab = screen.getByRole('tab', { name: 'States' });

    expect(overviewTab).toHaveAttribute('aria-selected', 'true');
    expect(statesTab).toHaveAttribute('aria-selected', 'false');
    expect(screen.getByText('Overview panel')).toBeInTheDocument();
    await user.click(screen.getByRole('tab', { name: 'States' }));
    expect(overviewTab).toHaveAttribute('aria-selected', 'false');
    expect(statesTab).toHaveAttribute('aria-selected', 'true');
    expect(screen.getByText('States panel')).toBeInTheDocument();
  });

  it('supports keyboard navigation', async (): Promise<void> => {
    const user = userEvent.setup();

    render(
      <Tabs>
        <TabsList>
          <TabsTrigger>Overview</TabsTrigger>
          <TabsTrigger>States</TabsTrigger>
        </TabsList>
        <TabsPanels>
          <TabsPanel>
            <p>Overview panel</p>
          </TabsPanel>
          <TabsPanel>
            <p>States panel</p>
          </TabsPanel>
        </TabsPanels>
      </Tabs>
    );

    const firstTab = screen.getByRole('tab', { name: 'Overview' });
    firstTab.focus();
    await act(async () => {
      await user.keyboard('{ArrowRight}');
    });

    await waitFor(() => {
      expect(screen.getByRole('tab', { name: 'States' })).toHaveAttribute('aria-selected', 'true');
    });
  });
});
