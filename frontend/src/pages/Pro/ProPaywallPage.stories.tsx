import type { Meta, StoryObj } from '@storybook/react';
import '../../i18n';
import ProPaywallPage from './ProPaywallPage';
import { ProProductInfoStorySurface } from '../../stories/storybookParitySupport';

const meta = {
  title: 'PulsePlate/Parity Pack/Apple Product Information',
  component: ProPaywallPage,
  render: () => <ProProductInfoStorySurface />,
  parameters: {
    layout: 'fullscreen',
  },
} satisfies Meta<typeof ProPaywallPage>;

export default meta;
type Story = StoryObj<typeof meta>;

export const DirectCompatibilityEntry: Story = {};
