import type { ComponentProps, JSX } from 'react';
import type { Meta, StoryObj } from '@storybook/react';
import { MemoryRouter } from 'react-router-dom';
import { DesignSystemCanvas, PanelShell } from '../design-system/shared';
import { HomeOpenSetupCta } from './HomeOpenSetupCta';

const meta: Meta<typeof HomeOpenSetupCta> = {
  title: 'PulsePlate/Patterns/HomeOpenSetupCta',
  component: HomeOpenSetupCta,
  render: (args: ComponentProps<typeof HomeOpenSetupCta>): JSX.Element => (
    <MemoryRouter>
      <DesignSystemCanvas>
        <PanelShell
          title="Web home primary CTA"
          subtitle="Pilot review surface for web.home.open_setup with repo-native routing and token styling."
        >
          <HomeOpenSetupCta {...args} />
        </PanelShell>
      </DesignSystemCanvas>
    </MemoryRouter>
  ),
};

export default meta;
type Story = StoryObj<typeof HomeOpenSetupCta>;

export const Default: Story = {};
