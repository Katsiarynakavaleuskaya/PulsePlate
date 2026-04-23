/** @vitest-environment jsdom */
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { Tabs, TabsList, TabsPanel, TabsPanels, TabsTrigger } from '../Tabs';

describe('Tabs', () => {
  it('switches panels on click', async () => {
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

    expect(screen.getByText('Overview panel')).toBeInTheDocument();
    await user.click(screen.getByRole('tab', { name: 'States' }));
    expect(screen.getByText('States panel')).toBeInTheDocument();
  });

  it('supports keyboard navigation', async () => {
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
    await user.keyboard('{ArrowRight}');

    expect(screen.getByRole('tab', { name: 'States' })).toHaveAttribute('aria-selected', 'true');
  });
});
