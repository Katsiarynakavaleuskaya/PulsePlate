import type { JSX } from 'react';
import type { Meta, StoryObj } from '@storybook/react';
import { MemoryRouter } from 'react-router-dom';
import '../i18n';
import { DesignSystemCanvas, PanelShell } from '../components/design-system/shared';
import Progress from './Progress';

const meta: Meta<typeof Progress> = {
  title: 'PulsePlate/Parity Pack/Progress',
  component: Progress,
  render: (): JSX.Element => (
    <MemoryRouter initialEntries={['/progress']}>
      <DesignSystemCanvas>
        <PanelShell
          title="Web progress baseline"
          subtitle="Representative parity-pack review surface for the web.progress page using the repo-native static chart baseline."
          className="overflow-hidden"
        >
          <div className="min-h-[780px] rounded-3xl border border-white/10 bg-[var(--color-bg)]">
            <Progress />
          </div>
        </PanelShell>
      </DesignSystemCanvas>
    </MemoryRouter>
  ),
  parameters: {
    layout: 'fullscreen',
  },
};

export default meta;
type Story = StoryObj<typeof Progress>;

export const Default: Story = {};
