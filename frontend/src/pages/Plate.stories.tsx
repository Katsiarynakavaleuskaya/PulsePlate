import type { JSX } from 'react';
import type { Meta, StoryObj } from '@storybook/react';
import '../i18n';
import { PlateStoryHarness, type PlateSessionState } from './Plate.storySupport';
import Plate from './Plate';

const meta = {
  title: 'PulsePlate/Parity Pack/Plate',
  component: Plate,
  render: (): JSX.Element => <Plate />,
  decorators: [
    (Story, context): JSX.Element => (
      <PlateStoryHarness sessionState={(context.parameters.sessionState as PlateSessionState | undefined) ?? 'pro'}>
        <Story />
      </PlateStoryHarness>
    ),
  ],
  parameters: {
    layout: 'fullscreen',
    sessionState: 'pro',
  },
} satisfies Meta<typeof Plate>;

export default meta;
type Story = StoryObj<typeof meta>;

export const ProUnlocked: Story = {};
