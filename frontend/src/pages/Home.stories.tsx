import type { Meta, StoryObj } from '@storybook/react';
import '../i18n';
import Home from './Home';
import { HomeStorySurface, type StorySessionState } from '../stories/storybookParitySupport';

const resolveSessionState = (value: unknown): StorySessionState => {
  if (value === 'guest' || value === 'free' || value === 'pro') {
    return value;
  }
  return 'pro';
};

const meta = {
  title: 'PulsePlate/Parity Pack/Home',
  component: Home,
  render: (_args, context) => (
    <HomeStorySurface sessionState={resolveSessionState(context.parameters.sessionState)} />
  ),
  parameters: {
    layout: 'fullscreen',
    sessionState: 'pro',
  },
} satisfies Meta<typeof Home>;

export default meta;
type Story = StoryObj<typeof meta>;

export const PremiumAiReady: Story = {};

export const FreeUpgrade: Story = {
  parameters: {
    sessionState: 'free',
  },
};

export const GuestConnect: Story = {
  parameters: {
    sessionState: 'guest',
  },
};
