import type { Meta, StoryObj } from '@storybook/react';
import { MemoryRouter } from 'react-router-dom';
import '../../i18n';
import WelcomeGateV1 from './WelcomeGateV1';

const meta: Meta<typeof WelcomeGateV1> = {
  title: 'PulsePlate/Onboarding/Welcome Gate v1',
  component: WelcomeGateV1,
  decorators: [
    (Story) => (
      <MemoryRouter>
        <Story />
      </MemoryRouter>
    ),
  ],
  parameters: {
    layout: 'fullscreen',
  },
};

export default meta;
type Story = StoryObj<typeof WelcomeGateV1>;

export const Step1: Story = {
  args: {
    initialScreen: 1,
  },
};

export const Step2: Story = {
  args: {
    initialScreen: 2,
  },
};

export const Step3: Story = {
  args: {
    initialScreen: 3,
  },
};
