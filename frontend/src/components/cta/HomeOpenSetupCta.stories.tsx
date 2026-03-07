import type { Meta, StoryObj } from '@storybook/react';
import { MemoryRouter } from 'react-router-dom';
import { DesignSystemCanvas, PanelShell } from '../design-system/shared';
import { HomeOpenSetupCta } from './HomeOpenSetupCta';

const meta: Meta<typeof HomeOpenSetupCta> = {
  title: 'PulsePlate/Patterns/HomeOpenSetupCta',
  component: HomeOpenSetupCta,
  render: () => (
    <MemoryRouter>
      <DesignSystemCanvas>
        <PanelShell
          title="Web home primary CTA"
          subtitle="Pilot review surface for web.home.open_setup with repo-native routing and token styling."
        >
          <HomeOpenSetupCta />
        </PanelShell>
      </DesignSystemCanvas>
    </MemoryRouter>
  ),
};

export default meta;
type Story = StoryObj<typeof HomeOpenSetupCta>;

export const Default: Story = {};
