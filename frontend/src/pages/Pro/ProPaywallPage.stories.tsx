import type { Meta, StoryObj } from '@storybook/react';
import '../../i18n';
import ProPaywallPage from './ProPaywallPage';
import { ProPaywallStorySurface } from '../../stories/storybookParitySupport';

const meta = {
  title: 'PulsePlate/Parity Pack/Pro Paywall',
  component: ProPaywallPage,
  render: () => <ProPaywallStorySurface />,
  parameters: {
    layout: 'fullscreen',
  },
} satisfies Meta<typeof ProPaywallPage>;

export default meta;
type Story = StoryObj<typeof meta>;

export const DirectProEntry: Story = {};
