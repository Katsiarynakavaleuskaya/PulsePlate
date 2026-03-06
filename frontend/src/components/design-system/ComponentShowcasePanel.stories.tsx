import { useState } from 'react';
import type { Meta, StoryObj } from '@storybook/react';
import { ComponentShowcasePanel } from './ExperiencePanels';
import { DesignSystemCanvas } from './shared';

const meta: Meta<typeof ComponentShowcasePanel> = {
  title: 'PulsePlate/Components/ComponentShowcasePanel',
  component: ComponentShowcasePanel,
  render: () => {
    const Showcase = () => {
      const [notificationsEnabled, setNotificationsEnabled] = useState(true);

      return (
        <DesignSystemCanvas>
          <ComponentShowcasePanel
            notificationsEnabled={notificationsEnabled}
            onNotificationsChange={setNotificationsEnabled}
          />
        </DesignSystemCanvas>
      );
    };

    return <Showcase />;
  },
};

export default meta;
type Story = StoryObj<typeof ComponentShowcasePanel>;

export const Default: Story = {};
