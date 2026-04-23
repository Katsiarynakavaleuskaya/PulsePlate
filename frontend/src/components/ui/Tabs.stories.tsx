import type { Meta, StoryObj } from '@storybook/react';
import { Tabs, TabsList, TabsPanel, TabsPanels, TabsTrigger } from './Tabs';

const meta: Meta<typeof Tabs> = {
  title: 'HPP/Tabs',
  component: Tabs,
};

export default meta;
type Story = StoryObj<typeof Tabs>;

export const Default: Story = {
  render: () => (
    <Tabs>
      <TabsList>
        <TabsTrigger>Overview</TabsTrigger>
        <TabsTrigger>States</TabsTrigger>
        <TabsTrigger>Implementation notes</TabsTrigger>
      </TabsList>
      <TabsPanels>
        <TabsPanel>
          <p className="text-sm">Shared primitives are part of the canonical review lane.</p>
        </TabsPanel>
        <TabsPanel>
          <p className="text-sm">Focus, disabled, error, and long-copy states belong in the primitive contract.</p>
        </TabsPanel>
        <TabsPanel>
          <p className="text-sm">Use Headless UI for tabs, not a second navigation primitive.</p>
        </TabsPanel>
      </TabsPanels>
    </Tabs>
  ),
};

export const WithDisabledTab: Story = {
  render: () => (
    <Tabs>
      <TabsList>
        <TabsTrigger>Overview</TabsTrigger>
        <TabsTrigger>States</TabsTrigger>
        <TabsTrigger disabled>Deferred follow-up</TabsTrigger>
      </TabsList>
      <TabsPanels>
        <TabsPanel>
          <p className="text-sm">Shared primitives are part of the canonical review lane.</p>
        </TabsPanel>
        <TabsPanel>
          <p className="text-sm">Focus, disabled, error, and long-copy states belong in the primitive contract.</p>
        </TabsPanel>
        <TabsPanel>
          <p className="text-sm">Reserved for later slices.</p>
        </TabsPanel>
      </TabsPanels>
    </Tabs>
  ),
};

export const LongLabels: Story = {
  render: () => (
    <Tabs>
      <TabsList>
        <TabsTrigger>Overview for the governed design runtime review surface</TabsTrigger>
        <TabsTrigger>States for the governed design runtime review surface</TabsTrigger>
        <TabsTrigger>Implementation notes for the governed design runtime review surface</TabsTrigger>
      </TabsList>
      <TabsPanels>
        <TabsPanel>
          <p className="text-sm">Shared primitives are part of the canonical review lane.</p>
        </TabsPanel>
        <TabsPanel>
          <p className="text-sm">Focus, disabled, error, and long-copy states belong in the primitive contract.</p>
        </TabsPanel>
        <TabsPanel>
          <p className="text-sm">Use Headless UI for tabs, not a second navigation primitive.</p>
        </TabsPanel>
      </TabsPanels>
    </Tabs>
  ),
};
